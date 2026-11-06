"""Her sembol için 1h + hizalanmış 4h/1d özellik tablosu."""
import os
import warnings
import numpy as np
import pandas as pd
from . import data as D
from . import indicators as I

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache",
                     os.path.basename(D.ROOT.rstrip("/")) + ("_live" if D.LIVE else ""))


def _htf(df1h, rule, prefix):
    h = D.resample(df1h, rule)
    f = pd.DataFrame(index=h.index)
    c = h["close"]
    f["close"] = c
    f["high"] = h["high"]; f["low"] = h["low"]
    for n in (20, 50, 100, 200):
        f[f"ema{n}"] = I.ema(c, n)
    f["rsi14"] = I.rsi(c, 14)
    f["atr14"] = I.atr(h, 14)
    f["adx14"], f["pdi"], f["ndi"] = I.adx(h, 14)
    m, s, hist = I.macd(c)
    f["macd"] = m; f["macd_sig"] = s; f["macd_hist"] = hist
    f["dc_hi20"], f["dc_lo20"] = I.donchian(h, 20)
    f["dc_hi55"], f["dc_lo55"] = I.donchian(h, 55)
    for n in (10, 20, 55):  # önceki N mumun aralığı (kırılım testi için)
        hi, lo = I.donchian(h, n)
        f[f"dcp_hi{n}"], f[f"dcp_lo{n}"] = hi.shift(1), lo.shift(1)
    f["ema50_slope"] = f["ema50"].diff(3)
    f["ema20_slope"] = f["ema20"].diff(3)
    bm, bu, bl = I.bollinger(c, 20, 2)
    f["bb_mid"], f["bb_up"], f["bb_lo"] = bm, bu, bl
    bw = (bu - bl) / bm
    f["bbw_rank"] = bw.rolling(120, min_periods=60).rank(pct=True)
    f["bbw_rank_prev"] = f["bbw_rank"].shift(1)
    f["vol_ratio"] = h["quote_volume"] / h["quote_volume"].rolling(20, min_periods=10).mean().shift(1)
    f["ret1"] = c.pct_change()
    out = {}
    for col in f.columns:
        out[f"{prefix}_{col}"] = D.to_1h(f[col], rule, df1h.index)
    return out


def _btc_main():
    """BTC her zaman ana veri klasöründen (stres evreninde BTC yok)."""
    main = os.path.join(CACHE if D.LIVE else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache", "data"), "BTCUSDT.pkl")
    if os.path.exists(main):
        return pd.read_pickle(main)
    return build("BTCUSDT")


def build(sym, use_cache=True):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"{sym}.pkl")
    if use_cache and os.path.exists(p):
        return pd.read_pickle(p)
    df = D.load_1h(sym)
    c = df["close"]
    f = df.copy()
    for n in (10, 20, 50, 100, 200):
        f[f"ema{n}"] = I.ema(c, n)
    f["sma200"] = I.sma(c, 200)
    for n in (2, 3, 4, 7, 14):
        f[f"rsi{n}"] = I.rsi(c, n)
    f["atr14"] = I.atr(df, 14)
    f["adx14"], f["pdi"], f["ndi"] = I.adx(df, 14)
    for n, k in ((20, 2.0), (20, 2.5), (40, 2.0)):
        m, u, lo = I.bollinger(c, n, k)
        f[f"bb{n}_{k}_mid"], f[f"bb{n}_{k}_up"], f[f"bb{n}_{k}_lo"] = m, u, lo
    for n in (10, 20, 24, 48, 55):
        hi, lo = I.donchian(df, n)
        f[f"dc_hi{n}"], f[f"dc_lo{n}"] = hi, lo
    m, s, hist = I.macd(c)
    f["macd"], f["macd_sig"], f["macd_hist"] = m, s, hist
    f["vol_sma20"] = df["quote_volume"].rolling(20).mean()
    for k, v in _htf(df, "4h", "h4").items():
        f[k] = v
    for k, v in _htf(df, "1D", "d1").items():
        f[k] = v
    f["funding"] = D.funding_1h(sym, df.index)
    if sym != "BTCUSDT":
        b = _btc_main()
        b = b.reindex(f.index)
        for col in ("close", "d1_close", "d1_ema50", "d1_ema200", "d1_ema20_slope", "h4_close", "h4_ema20", "h4_ema50"):
            f[f"btc_{col}"] = b[col].values
    else:
        for col in ("close", "d1_close", "d1_ema50", "d1_ema200", "d1_ema20_slope", "h4_close", "h4_ema20", "h4_ema50"):
            f[f"btc_{col}"] = f[col].values
    f.to_pickle(p)
    return f
