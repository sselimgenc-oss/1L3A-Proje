"""Vix FIX / StochRSI (TDxSLJRA, timj): Williams VIX Fix filtreli dip dönüşü → long; stokastik aşırı alım kesişiminde çıkış. Yalnız long. (Pine'daki pyramiding=9 tek pozisyona indirildi.)"""
import numpy as np
from tv import gost
ISIM = "Vix Fix + StochRSI"; PINE_ID = "TDxSLJRA"
PARAM = dict(pd=22, bbl=20, carpan=2.0, lb=50, yuzdelik=0.85, uzun_gb=40, orta_gb=14, guc=3, stoch=14, asiri_alim=80)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]; YON = 1
NEDEN = "Zaman dilimi belirtilmemiş; günlük, yalnız long (dip alma)."
def sinyal(df, pd, bbl, carpan, lb, yuzdelik, uzun_gb, orta_gb, guc, stoch, asiri_alim):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values
    hc = gost.highest(c, int(pd)); wvf = (hc - l)/hc*100
    sd = carpan*gost.stdev(wvf, int(bbl)); mid = gost.sma(wvf, int(bbl)); ub = mid + sd
    rh = gost.highest(wvf, int(lb))*yuzdelik
    with np.errstate(invalid="ignore"):
        up = (l > gost.sh(l)) & (c > gost.sh(h)); upa = (c > gost.sh(c)) & (c > gost.sh(o))
        filt = ((gost.sh(wvf) >= gost.sh(ub)) | (gost.sh(wvf) >= gost.sh(rh))) & (wvf < ub) & (wvf < rh)
        filta = ((gost.sh(wvf) >= gost.sh(ub)) | (gost.sh(wvf) >= gost.sh(rh))) & ~((wvf < ub) & (wvf < rh))
        cond = (c > gost.sh(c, int(guc))) & ((c < gost.sh(c, int(uzun_gb))) | (c < gost.sh(c, int(orta_gb))))
        a3 = up & cond & filt; a4 = upa & cond & filta
        K = gost.sma(gost.stoch(c, h, l, int(stoch)), 3); D = gost.sma(K, 3)
        ob = gost.crossover(K, D) & (K > asiri_alim)
    return dict(sig=(a3 | a4).astype(float), xl=ob)
