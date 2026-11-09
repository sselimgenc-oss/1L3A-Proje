"""Hash Supertrend (6zYF9Xts, Hash Capital): ta.supertrend(3.11, 16) yön değişiminde long/short; hep piyasada. (Zaman süzgeci varsayılan kapalı.)"""
import numpy as np
from tv import gost
ISIM = "Hash Supertrend"; PINE_ID = "6zYF9Xts"
PARAM = dict(atr=16, carpan=3.11)
TF = "12h"; EVREN = ["kripto"]
NEDEN = "PDF: SOL 12 saat."
def sinyal(df, atr, carpan):
    h, l, c = df.h.values, df.l.values, df.c.values
    st, d = gost.supertrend(h, l, c, gost.atr(h, l, c, int(atr)), carpan, (h+l)/2)
    pd_ = gost.sh(d)
    with np.errstate(invalid="ignore"):
        return dict(sig=gost.flipsig((d < pd_), (d > pd_)))
