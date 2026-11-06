"""AlphaTrend Strategy (3wdQu7P3): ATR(SMA 14)×1, MFI(14)>=50'ye göre izleyen çizgi; AT, AT[2]'yi keserse yön değiştir."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "AlphaTrend"; PINE_ID = "3wdQu7P3"
PARAM = dict(carpan=1.0, periyot=14)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Yazar BTCUSDT günlük test etmiş; günlük, tüm pazarlar."
@njit(cache=True)
def _at(up, dn, cond):
    n = len(up); a = np.zeros(n)
    for i in range(1, n):
        p = a[i-1]
        if cond[i]: a[i] = p if up[i] < p else up[i]
        else: a[i] = p if dn[i] > p else dn[i]
    return a
def sinyal(df, carpan, periyot):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    p = int(periyot); atr = gost.sma(gost.tr(h, l, c), p)
    m = gost.mfi(h, l, c, v, p)
    cond = np.where(np.isnan(m), gost.rsi(c, p) >= 50, m >= 50) if np.isnan(m).all() else np.nan_to_num(m, nan=0) >= 50
    at = _at(l - atr*carpan, h + atr*carpan, cond)
    a2 = gost.sh(at, 2)
    return dict(sig=gost.flipsig(gost.crossover(at, np.nan_to_num(a2)), gost.crossunder(at, np.nan_to_num(a2))))
