"""UT Bot v2 (lDGmh7ou): ATR(10)×1 izleyen stop; fiyat çizgiyi keserse yön değiştir."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "UT Bot v2"; PINE_ID = "lDGmh7ou"
PARAM = dict(carpan=1.0, atr=10)
TF = "4h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "UT Bot genelde saatlik/4 saatlikte kullanılır; 4 saatlik."
@njit(cache=True)
def _tsl(src, sl):
    n = len(src); t = np.zeros(n)
    for i in range(1, n):
        p = t[i-1]
        if np.isnan(sl[i]): t[i] = 0.0; continue
        if src[i] > p and src[i-1] > p: t[i] = max(p, src[i]-sl[i])
        elif src[i] < p and src[i-1] < p: t[i] = min(p, src[i]+sl[i]) if p != 0 else src[i]+sl[i]
        elif src[i] > p: t[i] = src[i]-sl[i]
        else: t[i] = src[i]+sl[i]
    return t
def sinyal(df, carpan, atr):
    h, l, c = df.h.values, df.l.values, df.c.values
    t = _tsl(c, gost.atr(h, l, c, int(atr))*carpan)
    return dict(sig=gost.flipsig(gost.crossover(c, t), gost.crossover(t, c)))
