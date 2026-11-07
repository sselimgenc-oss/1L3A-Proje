"""Veri indirme: Binance (kripto) ve Yahoo Finance (hisse, BIST, emtia).

Çıktı: data/<interval>/<sembol>.csv  (sütunlar: time[UTC], open, high, low, close, volume)
Kullanım:
    python -m src.data --groups crypto mag7 bist commodity
"""
import argparse
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from src.config import GROUPS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

BINANCE_HOSTS = ["https://data-api.binance.vision", "https://api.binance.com"]
YAHOO_HOSTS = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}


def _get(url, params=None, retries=4):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            if r.status_code == 200:
                return r
            last = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            if r.status_code in (403, 404):
                break
        except requests.RequestException as e:  # ağ hatası
            last = e
        time.sleep(2 ** i)
    raise last


def binance_klines(symbol, interval, days):
    """Binance spot klines, en eskiden yeniye sayfalı indirme."""
    end = int(time.time() * 1000)
    start = end - days * 86400 * 1000
    rows, cur = [], start
    host = None
    for h in BINANCE_HOSTS:
        try:
            _get(f"{h}/api/v3/ping")
            host = h
            break
        except Exception:
            continue
    if host is None:
        raise RuntimeError("Binance erişilemiyor (ağ politikası?)")
    while cur < end:
        r = _get(f"{host}/api/v3/klines",
                 {"symbol": symbol, "interval": interval, "startTime": cur, "limit": 1000})
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        cur = batch[-1][0] + 1
        if len(batch) < 1000:
            break
        time.sleep(0.15)
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume",
                                     "ct", "qv", "n", "tb", "tq", "ig"])
    df["time"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df[["time", "open", "high", "low", "close", "volume"]].astype(
        {"open": float, "high": float, "low": float, "close": float, "volume": float})
    return df.drop_duplicates("time").reset_index(drop=True)


def yahoo_chart(symbol, interval, range_):
    """Yahoo Finance v8 chart API. 5m: en fazla 60g, 1h: en fazla 730g."""
    last = None
    for h in YAHOO_HOSTS:
        try:
            r = _get(f"{h}/v8/finance/chart/{symbol}",
                     {"interval": interval, "range": range_, "includePrePost": "false"})
            res = r.json()["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            df = pd.DataFrame({
                "time": pd.to_datetime(res["timestamp"], unit="s", utc=True),
                "open": q["open"], "high": q["high"], "low": q["low"],
                "close": q["close"], "volume": q["volume"],
            }).dropna(subset=["open", "high", "low", "close"])
            return df.drop_duplicates("time").reset_index(drop=True)
        except Exception as e:
            last = e
    try:  # yedek: yfinance kütüphanesi
        import yfinance as yf
        d = yf.download(symbol, interval=interval, period=range_, progress=False, auto_adjust=False)
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d = d.rename(columns=str.lower).reset_index()
        d = d.rename(columns={d.columns[0]: "time"})
        d["time"] = pd.to_datetime(d["time"], utc=True)
        return d[["time", "open", "high", "low", "close", "volume"]].dropna()
    except Exception as e:
        raise RuntimeError(f"Yahoo erişilemiyor: {last} / {e}")


def save(df, interval, symbol):
    d = os.path.join(DATA_DIR, interval)
    os.makedirs(d, exist_ok=True)
    df.to_csv(os.path.join(d, symbol.replace("=", "_").replace("^", "") + ".csv"), index=False)


def load(symbol, interval):
    p = os.path.join(DATA_DIR, interval, symbol.replace("=", "_").replace("^", "") + ".csv")
    df = pd.read_csv(p, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def fetch_symbol(symbol, group, crypto_days=365):
    if group == "crypto":
        m5 = binance_klines(symbol, "5m", crypto_days)
        h1 = binance_klines(symbol, "1h", crypto_days + 30)
    else:
        m5 = yahoo_chart(symbol, "5m", "60d")
        h1 = yahoo_chart(symbol, "1h", "730d")
    save(m5, "5m", symbol)
    save(h1, "1h", symbol)
    return len(m5), len(h1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="+", default=list(GROUPS))
    ap.add_argument("--crypto-days", type=int, default=365)
    a = ap.parse_args()
    fails = []
    for g in a.groups:
        for s in GROUPS[g]:
            try:
                n5, n1 = fetch_symbol(s, g, a.crypto_days)
                print(f"OK  {g:9s} {s:10s} 5m={n5} 1h={n1}", flush=True)
            except Exception as e:
                fails.append(s)
                print(f"ERR {g:9s} {s:10s} {e}", flush=True)
    print(f"bitti {datetime.now(timezone.utc):%Y-%m-%d %H:%M} hatalı: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
