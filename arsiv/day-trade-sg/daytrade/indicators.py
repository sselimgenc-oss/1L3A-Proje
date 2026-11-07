"""Teknik göstergeler (kitaplardaki standart ayarlarla)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100.0).where(up.notna())


def stoch(df: pd.DataFrame, k: int = 14, smooth: int = 3, d: int = 3):
    lo = df["low"].rolling(k, min_periods=k).min()
    hi = df["high"].rolling(k, min_periods=k).max()
    raw = 100 * (df["close"] - lo) / (hi - lo).replace(0, np.nan)
    kk = raw.rolling(smooth, min_periods=smooth).mean()
    return kk, kk.rolling(d, min_periods=d).mean()


def macd(s: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9):
    line = ema(s, fast) - ema(s, slow)
    signal = ema(line, sig)
    return line, signal, line - signal


def momentum(s: pd.Series, n: int = 28) -> pd.Series:
    """Bernstein: MOM = kapanış / n önceki kapanış * 100."""
    return 100 * s / s.shift(n)


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n)
    pdi = 100 * pd.Series(plus, df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    mdi = 100 * pd.Series(minus, df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def session_vwap(df: pd.DataFrame, day: pd.Series) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3
    pv = (tp * df["volume"]).groupby(day.values).cumsum()
    vv = df["volume"].groupby(day.values).cumsum()
    v = pv / vv.replace(0, np.nan)
    return v.fillna(tp)  # hacim yoksa (ör. bazı endeks/emtia mumları) tipik fiyat


def daily_pivots(daily: pd.DataFrame) -> pd.DataFrame:
    """Önceki günün OHLC'sinden bugünün klasik pivot + CPR + Camarilla seviyeleri.

    `daily` indeksi seans günü; dönen tablo aynı indeksle BUGÜN için geçerli
    seviyeleri içerir (yani dünkü değerlerden hesaplanmış, kaydırılmış).
    """
    h, l, c = daily["high"].shift(), daily["low"].shift(), daily["close"].shift()
    p = (h + l + c) / 3
    bc = (h + l) / 2
    tc = 2 * p - bc
    rng = h - l
    out = pd.DataFrame({
        "P": p, "TC": np.maximum(tc, bc), "BC": np.minimum(tc, bc),
        "R1": 2 * p - l, "S1": 2 * p - h, "R2": p + rng, "S2": p - rng,
        "H3": c + 0.275 * rng, "L3": c - 0.275 * rng,
        "H4": c + 0.55 * rng, "L4": c - 0.55 * rng,
    }, index=daily.index)
    out["PDH"], out["PDL"], out["PDC"] = h, l, c
    rng_d = daily["high"] - daily["low"]
    # Dün bir "iç gün" müydü (önceki günün aralığı içinde) ve dar aralık (NR7) mıydı
    inside = (daily["high"] <= daily["high"].shift()) & (daily["low"] >= daily["low"].shift())
    out["inside_prev"] = inside.shift().fillna(False).astype(bool)
    out["nr7_prev"] = (rng_d <= rng_d.rolling(7, min_periods=7).min()).shift().fillna(False).astype(bool)
    out["cpr_width"] = (out["TC"] - out["BC"]) / out["P"]
    out["cpr_narrow"] = out["cpr_width"] < out["cpr_width"].rolling(20, min_periods=5).median()
    out["cpr_rising"] = out["BC"] > out["TC"].shift()   # "Daha yüksek değer" ilişkisi
    out["cpr_falling"] = out["TC"] < out["BC"].shift()  # "Daha düşük değer"
    return out
