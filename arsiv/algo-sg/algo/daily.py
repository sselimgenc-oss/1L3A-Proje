"""Günlük (1D) işlem + haftalık (1W) yön için veri ve özellik hattı.

- Günlük mumlar 1h Binance USDT-M verisinden UTC günlerine göre yeniden örneklenir.
- Haftalık mumlar Pazartesi 00:00 UTC başlangıçlıdır.
- Haftalık değerler bir günlük muma, o hafta KAPANDIKTAN sonra aktarılır (ileriye bakma yok):
  günlük mum (açılış t) t+1g'de kapanır; o anda kapanmış en son haftanın değeri kullanılır.
"""
import os
import warnings
import numpy as np
import pandas as pd
from . import data as D
from . import indicators as I

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)
MAIN_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache", "daily")


def _load_1h(sym, root):
    old = D.ROOT
    D.ROOT = root
    try:
        df = D.load_1h(sym)
        fund = D.funding_1h(sym, df.index)
    finally:
        D.ROOT = old
    return df, fund


def _resample(df, rule):
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "quote_volume": "sum"}
    return df.resample(rule, label="left", closed="left").agg(agg).dropna()


def _align(htf, rule_delta, index):
    """htf: üst ZD serisi (açılış zamanı indeksli). index: günlük açılış zamanları."""
    s = pd.Series(htf.values, index=htf.index + rule_delta)
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(index + pd.Timedelta("1D"), method="ffill").values


def _weekly_features(d):
    w = _resample(d, "W-MON")  # Pazartesi başlangıçlı haftalar (label=left)
    # W-MON kuralı haftaları Pazartesi biter şekilde etiketleyebilir; açılışı Pazartesi'ye sabitle
    w.index = w.index.normalize()
    if (w.index.dayofweek != 0).any():
        w = d.resample("W-SUN", label="right", closed="right").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum", "quote_volume": "sum"}).dropna()
        w.index = w.index - pd.Timedelta("6D")
    f = pd.DataFrame(index=w.index)
    c = w["close"]
    f["close"] = c; f["open"] = w["open"]; f["high"] = w["high"]; f["low"] = w["low"]
    for n in (5, 10, 20, 40):
        f[f"ema{n}"] = I.ema(c, n)
    f["sma30"] = I.sma(c, 30)
    f["rsi14"] = I.rsi(c, 14)
    f["atr14"] = I.atr(w, 14)
    m, s, h = I.macd(c)
    f["macd_hist"] = h
    f["macd_hist_up"] = (h > h.shift(1)).astype(float)
    f["ema13_up"] = (I.ema(c, 13) > I.ema(c, 13).shift(1)).astype(float)  # Elder "impulse" eğimi
    f["ema13"] = I.ema(c, 13)
    for n in (4, 10, 20):
        hi, lo = I.donchian(w, n)
        f[f"dcp_hi{n}"], f[f"dcp_lo{n}"] = hi.shift(1), lo.shift(1)
    f["ret4"] = c / c.shift(4) - 1
    f["ret12"] = c / c.shift(12) - 1
    f["adx14"], _, _ = I.adx(w, 14)
    return f


def build(sym, root=None, use_cache=True):
    root = root or D.ROOT
    tag = os.path.basename(root.rstrip("/"))
    os.makedirs(os.path.join(CACHE, tag), exist_ok=True)
    p = os.path.join(CACHE, tag, f"{sym}.pkl")
    if use_cache and os.path.exists(p):
        return pd.read_pickle(p)
    h1, fund = _load_1h(sym, root)
    d = _resample(h1, "1D")
    d = d[d.index + pd.Timedelta("1D") <= h1.index[-1] + pd.Timedelta("1h")]  # yarım kalan son günü at
    f = d.copy()
    c = d["close"]
    for n in (5, 10, 20, 50, 100, 200):
        f[f"ema{n}"] = I.ema(c, n)
    for n in (5, 10, 50, 200):
        f[f"sma{n}"] = I.sma(c, n)
    for n in (2, 3, 4, 14):
        f[f"rsi{n}"] = I.rsi(c, n)
    f["atr14"] = I.atr(d, 14); f["atr20"] = I.atr(d, 20)
    f["adx14"], _, _ = I.adx(d, 14)
    m, u, l = I.bollinger(c, 20, 2.0)
    f["bb_mid"], f["bb_up"], f["bb_lo"] = m, u, l
    for n in (5, 10, 20, 55):
        hi, lo = I.donchian(d, n)
        f[f"dcp_hi{n}"], f[f"dcp_lo{n}"] = hi.shift(1), lo.shift(1)
    f["ret1"] = c / c.shift(1) - 1
    f["ret3"] = c / c.shift(3) - 1
    f["vol_ratio"] = d["quote_volume"] / d["quote_volume"].rolling(20, min_periods=10).mean().shift(1)
    f["funding"] = pd.Series(fund, index=h1.index).resample("1D", label="left", closed="left").sum().reindex(d.index).fillna(0).values
    wf = _weekly_features(d)
    for col in wf.columns:
        f[f"w_{col}"] = _align(wf[col], pd.Timedelta("7D"), d.index)
    # BTC haftalık/günlük rejim (BTC her zaman ana veri klasöründen)
    if sym == "BTCUSDT" and root == MAIN_ROOT:
        b = f
    else:
        b = build("BTCUSDT", MAIN_ROOT, use_cache)
    b = b.reindex(f.index)
    for col in ("close", "ema50", "ema200", "w_close", "w_ema10", "w_ema20", "w_ema40", "w_macd_hist"):
        f[f"btc_{col}"] = b[col].values
    f.to_pickle(p)
    return f


def symbols(root=None):
    root = root or D.ROOT
    return sorted(x[:-7] for x in os.listdir(os.path.join(root, "1h")) if x.endswith(".csv.gz"))
