"""Günlük OHLCV verilerini indirir ve data/raw/ altına CSV olarak kaydeder.

Kaynaklar:
- Kripto: Binance public market data (data-api.binance.vision), yedek: Yahoo Finance
- Hisse / emtia: Yahoo Finance (yfinance)
"""
import os
import sys
import time

import pandas as pd
import requests
import yfinance as yf

sys.path.insert(0, os.path.dirname(__file__))
from varliklar import KRIPTO, MAG7, BIST10, EMTIA  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
START = "2015-01-01"
BINANCE_HOSTS = ["https://data-api.binance.vision", "https://api.binance.com", "https://api.binance.us"]


def binance_klines(symbol):
    for host in BINANCE_HOSTS:
        rows, start = [], int(pd.Timestamp(START).timestamp() * 1000)
        try:
            while True:
                r = requests.get(f"{host}/api/v3/klines", params={
                    "symbol": symbol, "interval": "1d", "startTime": start, "limit": 1000}, timeout=30)
                if r.status_code != 200:
                    raise RuntimeError(f"{host} {r.status_code}")
                batch = r.json()
                if not batch:
                    break
                rows += batch
                start = batch[-1][0] + 86_400_000
                if len(batch) < 1000:
                    break
                time.sleep(0.2)
        except Exception as e:  # sonraki host'u dene
            print(f"  {symbol}: {e}")
            continue
        now_ms = int(time.time() * 1000)
        rows = [r for r in rows if r[6] < now_ms]  # henüz kapanmamış günlük mumu at
        if rows:
            df = pd.DataFrame(rows).iloc[:, :6]
            df.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
            df["Date"] = pd.to_datetime(df["Date"], unit="ms").dt.strftime("%Y-%m-%d")
            df[["Open", "High", "Low", "Close", "Volume"]] = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
            return df
    return None


def yahoo(ticker):
    for _ in range(3):
        try:
            df = yf.download(ticker, start=START, interval="1d", auto_adjust=True, progress=False, threads=False)
            if df is not None and len(df):
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.reset_index()[["Date", "Open", "High", "Low", "Close", "Volume"]]
                df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
                return df.dropna()
        except Exception as e:
            print(f"  {ticker}: {e}")
        time.sleep(3)
    return None


def save(df, name):
    if df is None or not len(df):
        print(f"BAŞARISIZ: {name}")
        return False
    df.to_csv(os.path.join(OUT, f"{name}.csv"), index=False, float_format="%.10g")
    print(f"OK {name}: {len(df)} satır {df['Date'].iloc[0]} -> {df['Date'].iloc[-1]}")
    return True


def main():
    os.makedirs(OUT, exist_ok=True)
    fails = []
    for k in KRIPTO:
        name = f"{k}USDT"
        df = binance_klines(name)
        if df is None:
            df = yahoo(f"{k}-USD")
        if not save(df, name):
            fails.append(name)
    for s in MAG7:
        if not save(yahoo(s), s):
            fails.append(s)
    for s in BIST10:
        if not save(yahoo(f"{s}.IS"), f"{s}.IS"):
            fails.append(s)
    for name, t in EMTIA.items():
        if not save(yahoo(t), name):
            fails.append(name)
    # Yardımcı seriler (işlem görmez): BIST getirilerini USD'ye çevirmek için kur
    os.makedirs(os.path.join(OUT, "..", "yardimci"), exist_ok=True)
    for name, t in {"USDTRY": "USDTRY=X", "NDX": "^NDX", "SPX": "^GSPC", "XU100": "XU100.IS"}.items():
        df = yahoo(t)
        if df is not None:
            df.to_csv(os.path.join(OUT, "..", "yardimci", f"{name}.csv"), index=False, float_format="%.10g")
            print(f"OK yardımcı {name}: {len(df)}")
        else:
            fails.append(name)
    print("Başarısız:", fails)


if __name__ == "__main__":
    main()
