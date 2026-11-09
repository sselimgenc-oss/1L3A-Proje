"""MACD ReLoaded (VO6DY8s1): VAR hareketli ortalamalı MACD (12,26) − VAR(9) tetik; histogram sıfırı keserse yön değiştir."""
import numpy as np
from tv import gost
from tv.stratejiler.tott import var_ma
ISIM = "MACD ReLoaded (VAR)"; PINE_ID = "VO6DY8s1"
PARAM = dict(kisa=12, uzun=26, tetik=9)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar. MA türü varsayılan VAR."
def sinyal(df, kisa, uzun, tetik):
    c = df.c.values
    macd = var_ma(c, int(kisa)) - var_ma(c, int(uzun)); hist = macd - var_ma(macd, int(tetik))
    z = np.zeros(len(c))
    return dict(sig=gost.flipsig(gost.crossover(hist, z), gost.crossunder(hist, z)))
