"""Optimized Trend Tracker 'OTTEx' (HPbRZvsV): VAR(2) hareketli ortalaması ve %1.4 OTT bandı; fiyat OTT[2]'yi yukarı keserse long, VAR çizgisi OTT[2]'yi aşağı keserse short (hep piyasada). ycDUERPO ile aynı OTT hesabı, farklı varsayılanlar ve sinyal kaynağı (fiyat kesişimi)."""
import numpy as np
from tv import gost
from tv.stratejiler.ott import _ott
ISIM = "OTT Ex (OTTEx)"; PINE_ID = "HPbRZvsV"
PARAM = dict(periyot=2, yuzde=1.4)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, periyot, yuzde):
    c = df.c.values; var, o = _ott(c, float(periyot), yuzde); o2 = np.nan_to_num(gost.sh(o, 2))
    return dict(sig=gost.flipsig(gost.crossover(c, o2), gost.crossunder(var, o2)))
