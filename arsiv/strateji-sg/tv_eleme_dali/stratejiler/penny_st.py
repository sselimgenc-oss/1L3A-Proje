"""High Activity Penny Stock V6 (NfihxKxr): Supertrend(2.0, 10) yön dönüşünde + hacim>1.2×SMA20 + SMA50 filtresi → long/short; %10 hedef, %5 stop; Supertrend tersine dönünce kapat."""
import numpy as np
from tv import gost
ISIM = "Penny Stock Supertrend V6"; PINE_ID = "NfihxKxr"
PARAM = dict(atr=10, carpan=2.0, hacim=1.2, sma=50, tp=10.0, sl=5.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, atr, carpan, hacim, sma, tp, sl):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    st, d = gost.supertrend(h, l, c, gost.atr(h, l, c, int(atr)), carpan, (h+l)/2); pd_ = gost.sh(d)
    ok = v > gost.sma(v, 20)*hacim; m = gost.sma(c, int(sma))
    with np.errstate(invalid="ignore"):
        b = (d < 0) & (pd_ >= 0) & ok & (c > m); s = (d > 0) & (pd_ <= 0) & ok & (c < m)
    return dict(sig=gost.flipsig(b, s), xl=d > 0, xs=d < 0, slp=sl/100, tpp=tp/100)
