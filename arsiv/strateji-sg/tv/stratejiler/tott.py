"""Twin OTT (eENf7NpJ): VAR hareketli ortalama(40), %1 OTT; MAvg, OTTup[2]'yi yukarı keserse long; OTTdn[2]'yi aşağı keserse short."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "TOTT (Kivanc)"; PINE_ID = "eENf7NpJ"
PARAM = dict(uzunluk=40, yuzde=1.0, katsayi=0.001)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
@njit(cache=True)
def var_ma(src, length):
    n = len(src); out = np.zeros(n); al = 2.0/(length+1)
    for i in range(n):
        if i < 1: out[i] = src[i]; continue
        up = 0.0; dn = 0.0
        for j in range(max(0, i-8), i+1):
            if j == 0: continue
            d = src[j]-src[j-1]
            if d > 0: up += d
            else: dn -= d
        cmo = (up-dn)/(up+dn) if (up+dn) != 0 else 0.0
        k = al*abs(cmo)
        out[i] = k*src[i] + (1-k)*out[i-1]
    return out
@njit(cache=True)
def ott(mav, percent):
    n = len(mav); ls = np.zeros(n); ss = np.zeros(n); d = np.ones(n); o = np.zeros(n)
    for i in range(n):
        f = mav[i]*percent*0.01
        ls[i] = mav[i]-f; ss[i] = mav[i]+f
        if i == 0: o[i] = mav[i]; continue
        lsp = ls[i-1]; ssp = ss[i-1]
        if mav[i] > lsp: ls[i] = max(ls[i], lsp)
        if mav[i] < ssp: ss[i] = min(ss[i], ssp)
        d[i] = d[i-1]
        if d[i] == -1 and mav[i] > ssp: d[i] = 1
        elif d[i] == 1 and mav[i] < lsp: d[i] = -1
        mt = ls[i] if d[i] == 1 else ss[i]
        o[i] = mt*(200+percent)/200 if mav[i] > mt else mt*(200-percent)/200
    return o
def sinyal(df, uzunluk, yuzde, katsayi):
    c = df.c.values; m = var_ma(c, int(uzunluk)); o = ott(m, yuzde)
    up = gost.sh(o*(1+katsayi), 2); dn = gost.sh(o*(1-katsayi), 2)
    up = np.nan_to_num(up, nan=1e18); dn = np.nan_to_num(dn, nan=-1e18)
    return dict(sig=gost.flipsig(gost.crossover(m, up), gost.crossunder(m, dn)))
