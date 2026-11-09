"""PMax (nHGK4Qtp, KivancOzbilgic): EMA(hl2,10) ± ATR(10)×3 ile PMax çizgisi; EMA, PMax'ı yukarı keserse long, aşağı keserse short."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "PMax (Kivanc)"; PINE_ID = "nHGK4Qtp"
PARAM = dict(uzunluk=10, atr=10, carpan=3.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar. MA türü varsayılan EMA."
@njit(cache=True)
def _pmax(ma, atr, mult):
    n = len(ma); ls = np.full(n, np.nan); ss = np.full(n, np.nan); d = np.ones(n); o = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(ma[i]) or np.isnan(atr[i]): continue
        l_ = ma[i] - mult*atr[i]; s_ = ma[i] + mult*atr[i]
        if i > 0 and not np.isnan(ls[i-1]):
            lp, sp = ls[i-1], ss[i-1]
            if ma[i] > lp: l_ = max(l_, lp)
            if ma[i] < sp: s_ = min(s_, sp)
            d[i] = d[i-1]
            if d[i] == -1 and ma[i] > sp: d[i] = 1
            elif d[i] == 1 and ma[i] < lp: d[i] = -1
        ls[i] = l_; ss[i] = s_
        o[i] = l_ if d[i] == 1 else s_
    return o
def sinyal(df, uzunluk, atr, carpan):
    h, l, c = df.h.values, df.l.values, df.c.values
    ma = gost.ema((h+l)/2, int(uzunluk)); pm = _pmax(ma, gost.atr(h, l, c, int(atr)), carpan)
    ok = ~np.isnan(pm); m0 = np.nan_to_num(ma); p0 = np.nan_to_num(pm)
    return dict(sig=gost.flipsig(gost.crossover(m0, p0) & ok, gost.crossunder(m0, p0) & ok))
