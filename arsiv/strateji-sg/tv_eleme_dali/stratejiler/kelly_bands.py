"""Built-in Kelly (bFXf4IXh): EMA(20) ± 1×ATR(10) bandı; kapanış üst bandı yukarı keserse barın tepesi+1 tick'te stop-al (aşağı için tersi); TP/SL kapalı. (Kelly boyutlandırma çevrilmedi; standart boyut.)"""
import numpy as np
from tv import gost
ISIM = "Kelly demo bant kırılımı"; PINE_ID = "bFXf4IXh"
PARAM = dict(uzun=20, atr=10, carpan=1.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Örnek betik; zaman dilimi yok; günlük, tüm pazarlar."
def sinyal(df, uzun, atr, carpan):
    h, l, c = df.h.values, df.l.values, df.c.values; e = gost.ema(c, int(uzun)); a = gost.atr(h, l, c, int(atr)); up, lo = e+a*carpan, e-a*carpan
    cu = gost.crossover(c, np.nan_to_num(up)) & ~np.isnan(up); cd = gost.crossunder(c, np.nan_to_num(lo)) & ~np.isnan(lo)
    return dict(sig=gost.flipsig(cu, cd), sep=np.where(cu, h, np.where(cd, l, np.nan)))
