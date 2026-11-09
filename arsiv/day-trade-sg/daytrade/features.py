"""Giriş zaman dilimi tablosunu hazırlar: göstergeler + üst zaman dilimi (1s/4s)
özellikleri + seans bilgisi + günlük pivotlar.

Ön-bakış (look-ahead) önlemi: üst TF mumu yalnızca KAPANDIKTAN sonra kullanılır.
Giriş mumu kararı mumun kapanışında verilir, işlem bir sonraki mumun açılışında açılır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind
from .data import TF_MINUTES
from .universe import Instrument


def _hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def align_htf(htf: pd.DataFrame, tf: str, decision_times: pd.DatetimeIndex) -> pd.DataFrame:
    a = htf.copy()
    a.index = a.index + pd.Timedelta(minutes=TF_MINUTES[tf])  # kapanış = kullanılabilir an
    a = a[~a.index.duplicated(keep="last")].sort_index()
    left = pd.DataFrame({"t": decision_times})
    right = a.rename_axis("t").reset_index()
    m = pd.merge_asof(left, right, on="t", direction="backward")
    m.index = decision_times
    return m.drop(columns="t")


def htf_features(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    c = df["close"]
    _, _, hist = ind.macd(c)
    out = pd.DataFrame({
        "close": c, "ema20": ind.ema(c, 20), "ema50": ind.ema(c, 50),
        "ema200": ind.ema(c, 200), "sma100": ind.sma(c, 100), "macd_hist": hist,
        "adx": ind.adx(df, 14),
    }, index=df.index)
    # Lien "mükemmel düzen": SMA10 > 20 > 50 > 100 > 200 (düşüşte tersi), ADX > 20 ve yükselen
    s10, s20, s50, s200 = (ind.sma(c, n) for n in (10, 20, 50, 200))
    s100 = out["sma100"]
    out["po_up"] = (s10 > s20) & (s20 > s50) & (s50 > s100) & (s100 > s200)
    out["po_dn"] = (s10 < s20) & (s20 < s50) & (s50 < s100) & (s100 < s200)
    out["adx_up"] = out["adx"] > out["adx"].shift(3)
    # Bernstein hareketli ortalama kanalı (MAC): SMA10(yüksek), SMA8(düşük); MOM(28) ve SMA'sı
    out["mac_hi"] = ind.sma(df["high"], 10)
    out["mac_lo"] = ind.sma(df["low"], 8)
    mom = ind.momentum(c, 28)
    out["mom"], out["mom_ma"] = mom, ind.sma(mom, 28)
    out["low"], out["high"] = df["low"], df["high"]
    out["mac_up2"] = (df["low"] > out["mac_hi"]) & (df["low"].shift() > out["mac_hi"].shift())
    out["mac_dn2"] = (df["high"] < out["mac_lo"]) & (df["high"].shift() < out["mac_lo"].shift())
    return out.add_prefix(prefix)


def build(inst: Instrument, entry: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame,
          entry_tf: str) -> pd.DataFrame:
    df = entry.copy()
    c = df["close"]
    df["ema8"] = ind.ema(c, 8)
    df["ema20"] = ind.ema(c, 20)
    df["ema50"] = ind.ema(c, 50)
    df["sma100"] = ind.sma(c, 100)
    df["atr"] = ind.atr(df, 14)
    df["rsi9"] = ind.rsi(c, 9)
    df["rsi9_ma4"] = ind.sma(df["rsi9"], 4)
    df["stk"], df["std"] = ind.stoch(df, 14, 3, 3)
    df["macd"], df["macd_sig"], df["macd_hist"] = ind.macd(c)
    df["mom"] = ind.momentum(c, 28)
    df["mom_ma"] = ind.sma(df["mom"], 28)
    df["vol_ma"] = ind.sma(df["volume"], 20)
    bb_sd = c.rolling(20).std(ddof=0)
    df["bb_mid"] = ind.sma(c, 20)
    df["bb_up"] = df["bb_mid"] + 2 * bb_sd
    df["bb_lo"] = df["bb_mid"] - 2 * bb_sd

    # --- seans bilgisi (yerel saat) ---
    m = TF_MINUTES[entry_tf]
    local = df.index.tz_convert(inst.tz)
    tod = local.hour * 60 + local.minute
    s0, s1 = _hm(inst.session_start), _hm(inst.session_end)
    df["tod"] = tod
    df["in_session"] = (tod >= s0) & (tod + m <= max(s1, s0 + m))
    df["day"] = pd.Index(local.date)
    nxt_day = df["day"].shift(-1)
    nxt_in = df["in_session"].shift(-1, fill_value=False)
    df["last_bar"] = df["in_session"] & ((nxt_day != df["day"]) | ~nxt_in
                                         | (tod + 2 * m > s1))
    df["since_open"] = tod - s0

    # --- VWAP (seans bazlı) ---
    df["vwap"] = ind.session_vwap(df, df["day"].where(df["in_session"], None).astype(str))

    # --- üst zaman dilimleri ---
    decision = df.index + pd.Timedelta(minutes=m)
    df = df.join(align_htf(htf_features(h1, "h1_"), "1h", decision).set_axis(df.index))
    df = df.join(align_htf(htf_features(h4, "h4_"), "4h", decision).set_axis(df.index))

    # --- günlük OHLC (seans içi) ve pivotlar ---
    ses = df[df["in_session"]]
    daily = ses.groupby("day").agg(open=("open", "first"), high=("high", "max"),
                                   low=("low", "min"), close=("close", "last"))
    daily["atr_d"] = ind.atr(daily, 14).shift()  # dünkü değere kadar
    piv = ind.daily_pivots(daily).join(daily[["atr_d"]])
    df = df.join(piv, on="day")

    # --- gün içi: açılış, o ana kadarki tepe/dip (mevcut mum dahil), gap ---
    sd = df["day"].where(df["in_session"])
    df["dopen"] = df["open"].where(df["in_session"]).groupby(sd).transform("first")
    df["dhigh"] = df["high"].where(df["in_session"]).groupby(sd).cummax()
    df["dlow"] = df["low"].where(df["in_session"]).groupby(sd).cummin()
    df["gap_atr"] = (df["dopen"] - df["PDC"]) / df["atr_d"]

    # --- açılış aralığı (ORB) ---
    in_rng = df["in_session"] & (df["since_open"] >= 0) & (df["since_open"] < inst.orb_minutes)
    g = df[in_rng].groupby("day")
    rng = pd.DataFrame({"orb_hi": g["high"].max(), "orb_lo": g["low"].min(),
                        "orb_n": g["high"].count()})
    df = df.join(rng, on="day")
    df["orb_done"] = df["in_session"] & (df["since_open"] >= inst.orb_minutes)
    df["orb_ok"] = df["orb_n"] >= max(1, int(inst.orb_minutes / m * 0.8))
    df["orb_min"] = inst.orb_minutes
    df["asset_class"] = inst.asset_class
    df["cost_pct"] = inst.cost_pct
    return df.replace([np.inf, -np.inf], np.nan)
