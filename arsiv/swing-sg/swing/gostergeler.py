"""Teknik göstergeler (dokümanlarda geçen standart tanımlar)."""
import numpy as np
import pandas as pd


def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def sma(s, n):
    return s.rolling(n, min_periods=n).mean()


def rsi(close, n=14):
    """Wilder RSI."""
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100)


def atr(df, n=14):
    pc = df["Close"].shift()
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - pc).abs(), (df["Low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def macd(close, f=12, s=26, sig=9):
    m = ema(close, f) - ema(close, s)
    sg = m.ewm(span=sig, adjust=False).mean()
    return m, sg, m - sg


def stokastik(df, n=14, k=3, d=3):
    ll = df["Low"].rolling(n).min()
    hh = df["High"].rolling(n).max()
    raw = 100 * (df["Close"] - ll) / (hh - ll).replace(0, np.nan)
    K = raw.rolling(k).mean()
    return K, K.rolling(d).mean()


def bollinger(close, n=20, k=2.0):
    m = sma(close, n)
    sd = close.rolling(n).std()
    return m, m + k * sd, m - k * sd


def heikin_ashi(df):
    ha_c = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_o = ha_c.copy()
    o, c = df["Open"].values, ha_c.values
    out = np.empty(len(df))
    out[0] = (o[0] + df["Close"].values[0]) / 2
    for i in range(1, len(df)):
        out[i] = (out[i - 1] + c[i - 1]) / 2
    ha_o[:] = out
    return ha_o, ha_c


def chaikin_mf(df, n=20):
    rng = (df["High"] - df["Low"]).replace(0, np.nan)
    mfm = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / rng
    mfv = mfm.fillna(0) * df["Volume"]
    return mfv.rolling(n).sum() / df["Volume"].rolling(n).sum().replace(0, np.nan)


def adx(df, n=14):
    up = df["High"].diff()
    dn = -df["Low"].diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n)
    pdi = 100 * pd.Series(pdm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    ndi = 100 * pd.Series(ndm, index=df.index).ewm(alpha=1 / n, adjust=False).mean() / a
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean(), pdi, ndi
