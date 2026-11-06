"""Laguerre RSI (vWG3tMJh): Laguerre filtresi (alpha 0.2) yukarı/aşağı bileşenleri cu, cd: cu>cd kesişiminde long, cu<cd kesişiminde short; hep piyasada."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Laguerre RSI"; PINE_ID = "vWG3tMJh"
PARAM = dict(alpha=0.2)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
@njit(cache=True)
def _lg(c, a):
    n = len(c); g = 1-a; L0 = np.zeros(n); L1 = np.zeros(n); L2 = np.zeros(n); L3 = np.zeros(n); cu = np.zeros(n); cd = np.zeros(n)
    for i in range(n):
        p0 = L0[i-1] if i else 0.0; p1 = L1[i-1] if i else 0.0; p2 = L2[i-1] if i else 0.0; p3 = L3[i-1] if i else 0.0
        L0[i] = (1-g)*c[i] + g*p0; L1[i] = -g*L0[i] + p0 + g*p1; L2[i] = -g*L1[i] + p1 + g*p2; L3[i] = -g*L2[i] + p2 + g*p3
        cu[i] = (L0[i]-L1[i] if L0[i] > L1[i] else 0) + (L1[i]-L2[i] if L1[i] > L2[i] else 0) + (L2[i]-L3[i] if L2[i] > L3[i] else 0)
        cd[i] = (L1[i]-L0[i] if L0[i] < L1[i] else 0) + (L2[i]-L1[i] if L1[i] < L2[i] else 0) + (L3[i]-L2[i] if L2[i] < L3[i] else 0)
    return cu, cd
def sinyal(df, alpha):
    cu, cd = _lg(df.c.values, float(alpha)); return dict(sig=gost.flipsig(gost.crossover(cu, cd), gost.crossunder(cu, cd)))
