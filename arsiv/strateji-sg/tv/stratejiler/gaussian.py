"""Gaussian Channel Strategy (erJi1tWf): 4 kutuplu Gaussian filtre (periyot 144) ve filtrelenmiş TR bandı; fiyat orta çizgiyi yukarı keserse long, aşağı keserse short (3 bar geç giriş penceresi)."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Gaussian Channel"; PINE_ID = "erJi1tWf"
PARAM = dict(kutup=4, periyot=144, carpan=1.414, geriye=3)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar. Bant çizgileri yalnız görsel (sinyal orta çizgi)."
@njit(cache=True)
def _pole(x, alpha, N):
    n = len(x); f = np.zeros((n, 10)); xx = 1.0 - alpha
    m2 = np.array([0,0,1,3,6,10,15,21,28,36.]); m3 = np.array([0,0,0,1,4,10,20,35,56,84.]); m4 = np.array([0,0,0,0,1,5,15,35,70,126.])
    m5 = np.array([0,0,0,0,0,1,6,21,56,126.]); m6 = np.array([0,0,0,0,0,0,1,7,28,84.]); m7 = np.array([0,0,0,0,0,0,0,1,8,36.])
    m8 = np.array([0,0,0,0,0,0,0,0,1,9.]); m9 = np.array([0,0,0,0,0,0,0,0,0,1.])
    out = np.zeros(n)
    for i in range(n):
        s = x[i] if not np.isnan(x[i]) else 0.0
        v = alpha**N*s
        if i >= 1: v += N*xx*f[i-1, N]
        if N >= 2 and i >= 2: v -= m2[N]*xx**2*f[i-2, N]
        if N >= 3 and i >= 3: v += m3[N]*xx**3*f[i-3, N]
        if N >= 4 and i >= 4: v -= m4[N]*xx**4*f[i-4, N]
        if N >= 5 and i >= 5: v += m5[N]*xx**5*f[i-5, N]
        if N >= 6 and i >= 6: v -= m6[N]*xx**6*f[i-6, N]
        if N >= 7 and i >= 7: v += m7[N]*xx**7*f[i-7, N]
        if N >= 8 and i >= 8: v -= m8[N]*xx**8*f[i-8, N]
        if N == 9 and i >= 9: v += m9[N]*xx**9*f[i-9, N]
        f[i, N] = v; out[i] = v
    return out
def sinyal(df, kutup, periyot, carpan, geriye):
    h, l, c = df.h.values, df.l.values, df.c.values; src = (h+l+c)/3
    N = int(kutup); per = int(periyot)
    beta = (1 - np.cos(4*np.arcsin(1)/per))/(1.414**(2/N) - 1); alpha = -beta + np.sqrt(beta*beta + 2*beta)
    filt = _pole(src, alpha, N)
    up = gost.crossover(src, filt); dn = gost.crossunder(src, filt)
    ls = gost.barssince(up); ss = gost.barssince(dn)
    lc = up | ((src > filt) & (ls <= geriye)); sc = dn | ((src < filt) & (ss <= geriye))
    warm = np.arange(len(c)) > per*2
    return dict(sig=gost.flipsig(lc & warm, sc & warm))
