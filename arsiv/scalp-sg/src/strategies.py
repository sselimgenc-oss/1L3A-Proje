"""H1 yön + M5 giriş scalp stratejileri (bkz. analiz/ortak_strateji_analizi.md).

Her strateji, M5 DataFrame'i üzerinde şu sütunları üretir:
    sig    : +1 al / -1 sat / 0  (bar kapanışında oluşur, bir sonraki bar açılışında girilir)
    stop   : zarar durdur fiyatı (sinyal anında)
    tgt_dyn: dinamik hedef fiyatı (yoksa NaN) — S2'de Bollinger orta bandı
"""
import numpy as np
import pandas as pd

from src import indicators as ta


def merge_h1(m5, h1, h1_cols):
    """Yalnızca KAPANMIŞ H1 barlarını M5'e taşır (ileriye bakma yok)."""
    h = h1[["time"] + h1_cols].copy()
    h["avail"] = h["time"] + pd.Timedelta(hours=1)
    h = h.drop(columns="time")
    m = m5.copy()
    m["close_time"] = m["time"] + pd.Timedelta(minutes=5)
    m = pd.merge_asof(m.sort_values("close_time"), h.sort_values("avail"),
                      left_on="close_time", right_on="avail", direction="backward")
    return m.drop(columns=["avail"])


def h1_trend(h1, fast, slow):
    h = h1.copy()
    h["h_ef"] = ta.ema(h["close"], fast)
    h["h_es"] = ta.ema(h["close"], slow)
    up = (h["h_ef"] > h["h_es"]) & (h["close"] > h["h_es"])
    dn = (h["h_ef"] < h["h_es"]) & (h["close"] < h["h_es"])
    h["h_dir"] = np.where(up, 1, np.where(dn, -1, 0))
    h["h_green"] = np.sign(h["close"] - h["open"])
    h["h_slope"] = np.sign(h["h_es"] - h["h_es"].shift(3))
    return h


# ---------------------------------------------------------------- S1
S1_DEFAULT = dict(h_fast=8, h_slow=34, e_fast=8, e_pull=21, st_k=5, st_d=3, st_lvl=30,
                  look=6, swing=6, atr_n=14, rr=1.5, be=0.0, max_bars=36)


def s1_pullback(m5, h1, p):
    p = {**S1_DEFAULT, **p}
    h = h1_trend(h1, p["h_fast"], p["h_slow"])
    m = merge_h1(m5, h, ["h_dir"])
    c = m["close"]
    ef = ta.ema(c, p["e_fast"])
    ep = ta.ema(c, p["e_pull"])
    k, d = ta.stoch(m, p["st_k"], p["st_d"], 3)
    a = ta.atr(m, p["atr_n"])
    L = p["look"]
    # Geri çekilme: son L bar içinde fiyat EMA_pull'a değmiş ve stokastik aşırı bölgede
    pulled_dn = (m["low"] <= ep).astype(int).rolling(L).max() > 0
    pulled_up = (m["high"] >= ep).astype(int).rolling(L).max() > 0
    os_ = (k < p["st_lvl"]).astype(int).rolling(L).max() > 0
    ob_ = (k > 100 - p["st_lvl"]).astype(int).rolling(L).max() > 0
    kx_up = (k > d) & (k.shift() <= d.shift())
    kx_dn = (k < d) & (k.shift() >= d.shift())
    long_ = (m["h_dir"] == 1) & pulled_dn & os_ & (c > ef) & kx_up & (c > m["open"])
    short = (m["h_dir"] == -1) & pulled_up & ob_ & (c < ef) & kx_dn & (c < m["open"])
    sw_lo = m["low"].rolling(p["swing"]).min() - 0.1 * a
    sw_hi = m["high"].rolling(p["swing"]).max() + 0.1 * a
    m["sig"] = np.where(long_, 1, np.where(short, -1, 0))
    m["stop"] = np.where(long_, np.minimum(sw_lo, c - 0.5 * a),
                         np.where(short, np.maximum(sw_hi, c + 0.5 * a), np.nan))
    m["tgt_dyn"] = np.nan
    m["atr"] = a
    return m, p


# ---------------------------------------------------------------- S2
S2_DEFAULT = dict(h_ema=50, bb_n=20, bb_k=2.0, rsi_n=5, rsi_lvl=30, look=3, adx_max=0,
                  atr_n=14, rr=0.0, mid_exit=1, be=0.0, max_bars=24, h_filter="slope")


def s2_meanrev(m5, h1, p):
    p = {**S2_DEFAULT, **p}
    h = h1.copy()
    h["h_e"] = ta.ema(h["close"], p["h_ema"])
    slope = np.sign(h["h_e"] - h["h_e"].shift(3))
    if p["h_filter"] == "slope":
        h["h_dir"] = np.where((h["close"] > h["h_e"]) & (slope > 0), 1,
                              np.where((h["close"] < h["h_e"]) & (slope < 0), -1, 0))
    else:
        h["h_dir"] = np.where(h["close"] > h["h_e"], 1, -1)
    m = merge_h1(m5, h, ["h_dir"])
    c = m["close"]
    mid, up, lo = ta.bollinger(c, p["bb_n"], p["bb_k"])
    r = ta.rsi(c, p["rsi_n"])
    a = ta.atr(m, p["atr_n"])
    L = p["look"]
    below = (c < lo).astype(int).rolling(L).max() > 0
    above = (c > up).astype(int).rolling(L).max() > 0
    r_up = (r > p["rsi_lvl"]) & (r.shift() <= p["rsi_lvl"])
    r_dn = (r < 100 - p["rsi_lvl"]) & (r.shift() >= 100 - p["rsi_lvl"])
    long_ = (m["h_dir"] == 1) & below & r_up & (c > lo) & (c < mid)
    short = (m["h_dir"] == -1) & above & r_dn & (c < up) & (c > mid)
    if p["adx_max"]:
        ok = ta.adx(m, 14) < p["adx_max"]
        long_ &= ok
        short &= ok
    lo_n = m["low"].rolling(L + 2).min() - 0.2 * a
    hi_n = m["high"].rolling(L + 2).max() + 0.2 * a
    m["sig"] = np.where(long_, 1, np.where(short, -1, 0))
    m["stop"] = np.where(long_, np.minimum(lo_n, c - 0.5 * a),
                         np.where(short, np.maximum(hi_n, c + 0.5 * a), np.nan))
    m["tgt_dyn"] = mid if p["mid_exit"] else np.nan
    m["atr"] = a
    return m, p


# ---------------------------------------------------------------- S3
S3_DEFAULT = dict(h_fast=8, h_slow=34, need_green=1, box=6, box_atr=1.2, ema_n=20, ema_tol=0.5,
                  atr_n=14, rr=1.5, be=0.0, max_bars=24)


def s3_breakout(m5, h1, p):
    p = {**S3_DEFAULT, **p}
    h = h1_trend(h1, p["h_fast"], p["h_slow"])
    m = merge_h1(m5, h, ["h_dir", "h_green"])
    c = m["close"]
    a = ta.atr(m, p["atr_n"])
    e = ta.ema(c, p["ema_n"])
    N = p["box"]
    bh = m["high"].shift().rolling(N).max()
    bl = m["low"].shift().rolling(N).min()
    tight = (bh - bl) <= p["box_atr"] * a.shift()
    near_up = bl <= e.shift() + p["ema_tol"] * a.shift()   # kutu EMA'ya yakın (trend tarafında)
    near_dn = bh >= e.shift() - p["ema_tol"] * a.shift()
    g_up = (m["h_green"] > 0) if p["need_green"] else True
    g_dn = (m["h_green"] < 0) if p["need_green"] else True
    long_ = (m["h_dir"] == 1) & g_up & tight & near_up & (c > bh) & (c > e)
    short = (m["h_dir"] == -1) & g_dn & tight & near_dn & (c < bl) & (c < e)
    m["sig"] = np.where(long_, 1, np.where(short, -1, 0))
    m["stop"] = np.where(long_, bl - 0.1 * a, np.where(short, bh + 0.1 * a, np.nan))
    m["tgt_dyn"] = np.nan
    m["atr"] = a
    return m, p


STRATEGIES = {"S1": s1_pullback, "S2": s2_meanrev, "S3": s3_breakout}
