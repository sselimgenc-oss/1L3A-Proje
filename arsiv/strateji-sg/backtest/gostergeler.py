"""Teknik göstergeler (numpy/pandas). Tüm fonksiyonlar numpy dizisi döndürür."""
import numpy as np
import pandas as pd


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def rma(x, n):
    """Wilder ortalaması (RSI/ATR/ADX için)."""
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = rma(np.where(d > 0, d, 0.0), n)
    dn = rma(np.where(d < 0, -d, 0.0), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = up / dn
    out = 100 - 100 / (1 + rs)
    out[dn == 0] = 100.0
    return out


def true_range(h, l, c):
    pc = np.roll(c, 1)
    pc[0] = c[0]
    return np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))


def atr(h, l, c, n=14):
    return rma(true_range(h, l, c), n)


def bollinger(c, n=20, k=2.0):
    s = pd.Series(c)
    m = s.rolling(n).mean()
    sd = s.rolling(n).std(ddof=0)
    return m.to_numpy(), (m + k * sd).to_numpy(), (m - k * sd).to_numpy()


def macd(c, f=12, s=26, sig=9):
    m = ema(c, f) - ema(c, s)
    sg = ema(m, sig)
    return m, sg, m - sg


def stochastic(h, l, c, k=5, d=3, smooth=3):
    hh = pd.Series(h).rolling(k).max()
    ll = pd.Series(l).rolling(k).min()
    raw = 100 * (pd.Series(c) - ll) / (hh - ll).replace(0, np.nan)
    kk = raw.rolling(smooth).mean()
    dd = kk.rolling(d).mean()
    return kk.to_numpy(), dd.to_numpy()


def adx(h, l, c, n=14):
    up = np.diff(h, prepend=h[0])
    dn = -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = rma(true_range(h, l, c), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100 * rma(pdm, n) / tr
        mdi = 100 * rma(mdm, n) / tr
        dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
    return rma(np.nan_to_num(dx), n), pdi, mdi


def supertrend(h, l, c, n=10, mult=3.0):
    a = atr(h, l, c, n)
    hl2 = (h + l) / 2
    ub = hl2 + mult * a
    lb = hl2 - mult * a
    fu, fl = ub.copy(), lb.copy()
    yon = np.ones(len(c))
    for i in range(1, len(c)):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if c[i] > fu[i - 1]:
            yon[i] = 1
        elif c[i] < fl[i - 1]:
            yon[i] = -1
        else:
            yon[i] = yon[i - 1]
    return yon, np.where(yon > 0, fl, fu)


def donchian(h, l, n):
    return (pd.Series(h).rolling(n).max().to_numpy(),
            pd.Series(l).rolling(n).min().to_numpy())


def htf_hizala(idx_ltf, df_htf, kolon_dizileri):
    """Üst zaman dilimi değerlerini, yalnızca KAPANMIŞ HTF barlarını kullanarak
    alt zaman dilimine hizalar (ileriye bakma yanlılığı yok).
    df_htf indexi bar AÇILIŞ zamanıdır; bar kapanışı = açılış + periyot."""
    per = df_htf.index.to_series().diff().mode().iloc[0]
    # HTF mumu, kapanış anı alt zaman dilimi mumunun KAPANIŞINA denk gelen mumda kullanılabilir (karar bar kapanışında
    # verilir). Eskiden bir mum daha bekleniyordu (1 mum gecikme, canlı sinyal betiğiyle tutarsızdı; Faz 9 denetimi).
    ltf = pd.Series(idx_ltf).diff().mode()
    ltf = ltf.iloc[0] if len(ltf) else pd.Timedelta(0)
    kapanis = df_htf.index + per - ltf
    out = {}
    for ad, dizi in kolon_dizileri.items():
        s = pd.Series(dizi, index=kapanis)
        s = s[~s.index.duplicated(keep="last")]
        out[ad] = s.reindex(idx_ltf, method="ffill").to_numpy()
    return out
