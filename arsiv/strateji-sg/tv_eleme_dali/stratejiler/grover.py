"""Grover Llorens Activator (VuYM89Tw): ATR(480)×14 izleyen çizgi, kesişimde yön değiştir."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Grover Llorens Activator"; PINE_ID = "VuYM89Tw"
PARAM = dict(uzunluk=480, carpan=14)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar (uzun ATR: günlükte ~2 yıl)."
@njit(cache=True)
def _ga(src, atr, length, mult):
    n = len(src); ts = np.full(n, np.nan); up = np.zeros(n, np.bool_); dn = np.zeros(n, np.bool_)
    val = 0.0; bars = 0.0
    ts[0] = src[0]
    for i in range(1, n):
        if np.isnan(atr[i]): ts[i] = src[i]; continue
        diff = src[i-1] - ts[i-1]; diff2 = src[i] - ts[i-1]
        # diff (Pine): src - nz(ts[1], src[1]); crossover(diff,0) bu bar vs önceki bar diff
        d_now = src[i] - ts[i-1]
        d_prev = (src[i-1] - ts[i-2]) if i > 1 else 0.0
        u = d_now > 0 and d_prev <= 0; d = d_now < 0 and d_prev >= 0
        up[i] = u; dn[i] = d
        if u or d: val = atr[i]/length; bars = 0.0
        else: bars += 1.0
        if u: ts[i] = ts[i-1] - atr[i]*mult
        elif d: ts[i] = ts[i-1] + atr[i]*mult
        else:
            sg = 1.0 if d_now > 0 else (-1.0 if d_now < 0 else 0.0)
            ts[i] = ts[i-1] + sg*val*bars
    return up, dn
def sinyal(df, uzunluk, carpan):
    h, l, c = df.h.values, df.l.values, df.c.values
    up, dn = _ga(c, gost.atr(h, l, c, int(uzunluk)), float(uzunluk), float(carpan))
    return dict(sig=gost.flipsig(up, dn))
