"""KivancOzbilgic SuperTrend STRATEGY (P5Gu6F8k): ATR(10)×3, kaynak hl2, giriş = trend dönüşü, hep piyasada (long/short)."""
import numpy as np
from tv import gost
ISIM = "SuperTrend (Kivanc)"; PINE_ID = "P5Gu6F8k"
PARAM = dict(periyot=10, carpan=3.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Yazar zaman dilimi belirtmemiş; günlük, tüm pazarlar (trend takip her yerde anlamlı)."
def sinyal(df, periyot, carpan):
    h, l, c = df.h.values, df.l.values, df.c.values
    a = gost.atr(h, l, c, int(periyot)); t = gost.st_kivanc(c, (h+l)/2, a, carpan)
    sig = np.zeros(len(c)); 
    al = (t == 1) & (np.r_[1, t[:-1]] == -1); sat = (t == -1) & (np.r_[-1, t[:-1]] == 1)
    sig[al] = 1; sig[sat] = -1
    return dict(sig=sig)
