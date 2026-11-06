"""Squeeze Momentum on Reversal (Fckzv8iH): LazyBear momentumu (BB sapması KC çarpanıyla) sıfırın altındayken yukarı dönerse (|val|>0.0018) long, sıfırın üstündeyken aşağı dönerse short; hep piyasada."""
import numpy as np
from tv import gost
ISIM = "Squeeze Momentum Reversal"; PINE_ID = "Fckzv8iH"
PARAM = dict(bb=20, kc=20, kc_c=1.5, esik=0.0018)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, bb, kc, kc_c, esik):
    h, l, c = df.h.values, df.l.values, df.c.values
    ma = gost.sma(c, int(kc)); mid = (gost.highest(h, int(kc)) + gost.lowest(l, int(kc)))/2
    val = gost.linreg(c - (mid + ma)/2, int(kc), 0); p = gost.sh(val)
    with np.errstate(invalid="ignore"):
        s = (val > esik) & (val < p); lg = (val < -esik) & (val > p)
    return dict(sig=gost.flipsig(lg, s))
