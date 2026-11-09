"""Signal Engine Quantum Edge (n9ty3SVh): KivancOzbilgic tarzı SuperTrend (ATR 15, çarpan 9.1, kaynak hl2) yön değişiminde long/short; hep piyasada."""
import numpy as np
from tv import gost
ISIM = "Signal Engine Quantum Edge (SuperTrend 9.1)"; PINE_ID = "n9ty3SVh"
PARAM = dict(atr=15, carpan=9.1)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; çoklu TF tablosu var; günlük, tüm pazarlar."
def sinyal(df, atr, carpan):
    h, l, c = df.h.values, df.l.values, df.c.values
    t = gost.st_kivanc(c, (h+l)/2, gost.atr(h, l, c, int(atr)), carpan); p = np.r_[1, t[:-1]]
    return dict(sig=gost.flipsig((t == 1) & (p == -1), (t == -1) & (p == 1)))
