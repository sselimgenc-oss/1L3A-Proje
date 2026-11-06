"""Hybrid Breakout (hezSShJr): 50>150>200 SMA yükselen trend + dar aralık (sıkışma) + hacim genişlemesi → son 3 barın zirvesinde stop-giriş; %8 stop, kâr al kademeleri (%10/%20/%30) tek ortalama hedef %20 olarak modellendi."""
import numpy as np
from tv import gost
ISIM = "Hybrid Breakout (trend+sıkışma)"; PINE_ID = "hezSShJr"
PARAM = dict(ma1=50, ma2=150, ma3=200, yukselis=20, aralik=3, geri=150, yuzdelik=40, kapanis_arl=4.0, vol=20, vol_c=1.2, kirilim=3, stop=8.0, hedef=20.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]; YON = 1
NEDEN = "Zaman dilimi belirtilmemiş; günlük (200 gün SMA, Minervini tarzı), yalnız long."
def sinyal(df, ma1, ma2, ma3, yukselis, aralik, geri, yuzdelik, kapanis_arl, vol, vol_c, kirilim, stop, hedef):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    m1, m2, m3 = gost.sma(c, int(ma1)), gost.sma(c, int(ma2)), gost.sma(c, int(ma3))
    with np.errstate(invalid="ignore"):
        bull = (c > m1) & (m1 > m2) & (m2 > m3) & (m3 > gost.sh(m3)) & (m3 > gost.sh(m3, int(yukselis))) & (m1 >= gost.sh(m1))
        hr, lr = gost.highest(h, int(aralik)), gost.lowest(l, int(aralik)); rp = (hr-lr)/hr*100
        hc, lc_ = gost.highest(c, int(aralik)), gost.lowest(c, int(aralik)); crp = (hc-lc_)/hc*100
        pr = gost.percentrank(rp, int(geri)); piv = (pr <= yuzdelik) | (crp <= kapanis_arl)
        vok = v > gost.sma(v, int(vol))*vol_c
    sig = bull & piv & vok
    rh = gost.sh(gost.highest(h, int(kirilim)), 1)
    return dict(sig=sig.astype(float), sep=np.where(sig, rh, np.nan), slp=stop/100, tpp=hedef/100)
