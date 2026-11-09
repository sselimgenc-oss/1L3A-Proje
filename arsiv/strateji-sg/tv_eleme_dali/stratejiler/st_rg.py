"""Supertrend RG with TP (DG9ePZuk): KivancOzbilgic SuperTrend(10, 3, hl2) yön değişimini bir mum gecikmeyle (signal[1]) uygular (long/short); %8 stop, +%2 tetikten sonra %2.5 izleyen mum-dibi stopu (izleyen stop yaklaşık: tepeden %2.5)."""
import numpy as np
from tv import gost
ISIM = "Supertrend RG with TP"; PINE_ID = "DG9ePZuk"
PARAM = dict(atr=10, carpan=3.0, sl=8.0, tetik=2.0, iz=2.5)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, atr, carpan, sl, tetik, iz):
    h, l, c = df.h.values, df.l.values, df.c.values
    t = gost.st_kivanc(c, (h+l)/2, gost.atr(h, l, c, int(atr)), carpan); p = np.r_[1, t[:-1]]
    b = gost.sh(((t == 1) & (p == -1)).astype(float)) > 0; s = gost.sh(((t == -1) & (p == 1)).astype(float)) > 0
    return dict(sig=gost.flipsig(b, s), slp=sl/100, tra=tetik/100, tro=iz/100, trd=0)
