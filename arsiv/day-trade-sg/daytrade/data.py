"""Veri çekme ve önbellek.

Kaynaklar:
- Kripto: Binance herkese açık piyasa verisi (data-api.binance.vision, anahtar
  gerektirmez, sayfalama ile yıllarca geriye 5dk/15dk/1s/4s mum verir).
- Hisse (ABD, BIST), altın (GC=F), petrol (CL=F): Yahoo Finance (yfinance).
  Yahoo kısıtı: 5dk/15dk en fazla son 60 gün, 1s en fazla son 730 gün.

Tüm zaman damgaları UTC, indeks = mum AÇILIŞ zamanı.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import requests

from .universe import Instrument

CACHE = Path(os.environ.get("DAYTRADE_CACHE",
                          Path(__file__).resolve().parent.parent / "data" / "cache"))
BINANCE_HOSTS = ["https://data-api.binance.vision", "https://api.binance.com"]
TF_MINUTES = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
COLS = ["open", "high", "low", "close", "volume"]


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (day-trade-sg research)"
    return s


def cache_path(inst: Instrument, tf: str) -> Path:
    return CACHE / inst.source / f"{inst.symbol.replace('=', '_')}_{tf}.pkl"


def load(inst: Instrument, tf: str) -> pd.DataFrame | None:
    p = cache_path(inst, tf)
    if not p.exists():
        return None
    df = pd.read_pickle(p)
    df.index = pd.to_datetime(df.index, utc=True)
    return df


def save(inst: Instrument, tf: str, df: pd.DataFrame) -> None:
    p = cache_path(inst, tf)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(p)


def fetch_binance(symbol: str, tf: str, start: pd.Timestamp, end: pd.Timestamp | None = None,
                  session: requests.Session | None = None) -> pd.DataFrame:
    session = session or _session()
    end = end or pd.Timestamp.now(tz="UTC")
    start_ms, end_ms = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
    rows, err = [], None
    for host in BINANCE_HOSTS:
        rows, cur = [], start_ms
        try:
            while cur < end_ms:
                r = session.get(f"{host}/api/v3/klines", timeout=30, params={
                    "symbol": symbol, "interval": tf, "startTime": cur,
                    "endTime": end_ms, "limit": 1000})
                if r.status_code == 429:
                    time.sleep(5)
                    continue
                r.raise_for_status()
                batch = r.json()
                if not batch:
                    break
                rows.extend(batch)
                cur = batch[-1][0] + TF_MINUTES[tf] * 60_000
                time.sleep(0.05)
            break
        except requests.RequestException as e:  # bir sonraki sunucuyu dene
            err = e
            continue
    if not rows and err:
        raise err
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "volume",
                                     "ct", "qv", "n", "tb", "tq", "x"])
    df.index = pd.to_datetime(df["t"], unit="ms", utc=True)
    df = df[COLS].astype(float)
    return df[~df.index.duplicated()].sort_index()


YAHOO_HOSTS = ["https://query1.finance.yahoo.com", "https://query2.finance.yahoo.com"]


def fetch_binance_arsiv(symbol: str, tf: str, start: pd.Timestamp, end: pd.Timestamp,
                        session: requests.Session | None = None) -> pd.DataFrame:
    """data.binance.vision aylık kline arşivleri (delist edilmiş semboller dahil).
    Zaman damgaları 2025'ten itibaren mikrosaniye olabilir."""
    import io
    import zipfile

    session = session or _session()
    parts = []
    for m in pd.period_range(start.tz_convert(None).to_period("M"), end.tz_convert(None).to_period("M"), freq="M"):
        url = (f"https://data.binance.vision/data/spot/monthly/klines/{symbol}/{tf}/"
               f"{symbol}-{tf}-{m.strftime('%Y-%m')}.zip")
        r = session.get(url, timeout=60)
        if r.status_code != 200:
            continue
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            raw = pd.read_csv(z.open(z.namelist()[0]), header=None)
        if not str(raw.iloc[0, 0]).isdigit():   # başlık satırı varsa at
            raw = raw.iloc[1:]
        parts.append(raw)
    if not parts:
        return pd.DataFrame(columns=COLS)
    raw = pd.concat(parts)
    t = raw[0].astype("int64")
    t = t.where(t < 10**14, t // 1000)          # mikrosaniye → milisaniye
    df = pd.DataFrame({c: raw[i].astype(float).to_numpy() for i, c in enumerate(COLS, 1)},
                      index=pd.to_datetime(t.to_numpy(), unit="ms", utc=True))
    df = df[(df.index >= start) & (df.index < end)]
    return df[~df.index.duplicated()].sort_index()


def fetch_yahoo(symbol: str, tf: str, session: requests.Session | None = None) -> pd.DataFrame:
    """Yahoo chart API (v8) doğrudan; yfinance gerektirmez."""
    if tf == "4h":  # Yahoo 4s vermez; 1s'ten üretilir
        return resample(fetch_yahoo(symbol, "1h", session), "4h")
    session = session or _session()
    rng = {"5m": "60d", "15m": "60d", "1h": "730d", "1d": "5y"}[tf]
    err = None
    for host in YAHOO_HOSTS:
        try:
            r = session.get(f"{host}/v8/finance/chart/{symbol}", timeout=30, params={
                "range": rng, "interval": tf, "includePrePost": "false"})
            r.raise_for_status()
            res = r.json()["chart"]["result"][0]
            break
        except (requests.RequestException, KeyError, TypeError, IndexError) as e:
            err = e
    else:
        raise RuntimeError(f"Yahoo {symbol} {tf}: {err}")
    ts = res.get("timestamp") or []
    if not ts:
        return pd.DataFrame(columns=COLS)
    q = res["indicators"]["quote"][0]
    df = pd.DataFrame({c: q.get(c) for c in COLS},
                      index=pd.to_datetime(ts, unit="s", utc=True)).astype(float)
    df = df.dropna(subset=["open", "high", "low", "close"])
    df["volume"] = df["volume"].fillna(0)
    df = df[(df["high"] > 0) & (df["low"] > 0)]
    # Seans kapanışındaki hacimsiz "anlık" mumu at
    df = df[~((df["volume"] == 0) & (df["high"] == df["low"]))]
    if tf in ("5m", "15m"):  # mum açılışına hizala (Yahoo bazen son mumu anlık verir)
        df = df[df.index == df.index.floor(f"{TF_MINUTES[tf]}min")]
    return df[~df.index.duplicated()].sort_index()


def resample(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    rule = {"5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "1d": "1D"}[tf]
    out = df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return out.dropna(subset=["open"])


def update(inst: Instrument, tf: str, days: int = 365) -> pd.DataFrame:
    """Önbelleği günceller (eksik kısmı çeker, eskiyle birleştirir)."""
    old = load(inst, tf)
    if inst.source == "binance":
        start = (old.index[-1] if old is not None and len(old)
                 else pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days))
        new = fetch_binance(inst.symbol, tf, start)
    else:
        new = fetch_yahoo(inst.symbol, tf)
    df = new if old is None else pd.concat([old, new])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    # Henüz kapanmamış son mumu at
    now = pd.Timestamp.now(tz="UTC")
    df = df[df.index + pd.Timedelta(minutes=TF_MINUTES[tf]) <= now]
    save(inst, tf, df)
    return df


def check_connectivity() -> dict[str, bool]:
    s = _session()
    out = {}
    for name, url in {
        "binance": "https://data-api.binance.vision/api/v3/ping",
        "yahoo": "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=1d&interval=1h",
        "coingecko": "https://api.coingecko.com/api/v3/ping",
    }.items():
        try:
            out[name] = s.get(url, timeout=15).status_code == 200
        except requests.RequestException:
            out[name] = False
    return out
