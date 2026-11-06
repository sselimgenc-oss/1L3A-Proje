"""Geniş evren verisi: data/genis. BIST fiyatları USD'ye çevrilir, sıfır/eksi fiyatlar (CL=F 2020-04-20) atılır."""
import os

import pandas as pd

KOK = os.path.join(os.path.dirname(__file__), "..")
GENIS = os.path.join(KOK, "data", "genis")

import sys  # noqa: E402
sys.path.insert(0, os.path.join(KOK, "scripts"))
from fetch_genis import BIST, EMTIA, US, dosya_adi  # noqa: E402

MALIYET = {"bist": 0.0015, "abd": 0.0005, "emtia": 0.0005, "kripto": 0.0010, "endeks": 0.0005}


def yukle(ticker, usd=None):
    yol = os.path.join(GENIS, dosya_adi(ticker) + ".csv")
    if not os.path.exists(yol):
        return None
    df = pd.read_csv(yol, parse_dates=["Date"]).set_index("Date").sort_index()
    df = df[~df.index.duplicated()]
    df = df[(df["Close"] > 0) & (df["Open"] > 0)][["Open", "High", "Low", "Close"]].astype(float)
    if usd is None:
        usd = ticker.endswith(".IS")
    if usd:
        kur = yukle("USDTRY=X", usd=False)["Close"].reindex(df.index, method="ffill")
        df = df.div(kur, axis=0).dropna()
    return df


def evren(ad):
    liste = {"bist": [b + ".IS" for b in BIST], "abd": US, "emtia": EMTIA}[ad]
    out = {}
    for t in liste:
        df = yukle(t)
        if df is not None and len(df) > 300:
            out[t] = df
    return out


def panel(dfs, kolon):
    return pd.DataFrame({t: d[kolon] for t, d in dfs.items()}).sort_index()
