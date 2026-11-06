"""Stochastic Optimized Trend Tracker (cJhpIJ2w): VAR(stokastik %K(250), 50)+1000 serisine OTT(3, %0.618); seri OTT[2]'yi keserse yön değiştir."""
import numpy as np
from tv import gost
from tv.stratejiler.tott import var_ma, ott as _ott_f
ISIM = "Stochastic OTT (SOTT)"; PINE_ID = "cJhpIJ2w"
PARAM = dict(k_uzunluk=250, k_yumusat=50, ott_periyot=3, ott_yuzde=0.618)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük (250 barlık %K)."
def sinyal(df, k_uzunluk, k_yumusat, ott_periyot, ott_yuzde):
    h, l, c = df.h.values, df.l.values, df.c.values
    st = np.nan_to_num(gost.stoch(c, h, l, int(k_uzunluk)), nan=50.0)
    k = var_ma(st, int(k_yumusat)); src = k + 1000.0
    m = var_ma(src, int(ott_periyot)); o = _ott_f(m, ott_yuzde); o2 = np.nan_to_num(gost.sh(o, 2), nan=1e9)
    warm = np.arange(len(c)) > k_uzunluk + 5
    return dict(sig=gost.flipsig(gost.crossover(src, o2) & warm, gost.crossunder(src, o2) & warm))
