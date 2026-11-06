"""Daily Close Comparison (XK8XbDhT, ChartArt): son günün kapanışı bir öncekinden yüksekse long, düşükse short (eşik 0)."""
import numpy as np
from tv import gost
ISIM = "Günlük kapanış karşılaştırma"; PINE_ID = "XK8XbDhT"
PARAM = dict(esik=0.0001)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Betik günlük kapanışlara bakar; günlük. Eşik 0 yerine 0.0001 (sayısal ±%20 testi için sıfırdan farklı)."
def sinyal(df, esik):
    c = df.c.values; d = (c - gost.sh(c))/gost.sh(c)
    return dict(sig=gost.flipsig(d > esik, d < -esik))
