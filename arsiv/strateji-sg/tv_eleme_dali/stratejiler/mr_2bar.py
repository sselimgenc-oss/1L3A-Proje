"""ONEUSDT MR1 (8I2576zL): 2 günlük (2 mumluk) düşüş -%5…-%7 aralığındayken, son 2 mumda kapanış yükselmemişse alış; ATR×11 izleyen stop; kapanış > önceki tepe ve açılış[1] <= kapanış[9] ise çıkış. Yalnız long."""
import numpy as np
from tv import gost
ISIM = "ONE MR1 (2 mum düşüş sonrası ortalamaya dönüş)"; PINE_ID = "8I2576zL"
PARAM = dict(atr=14, izle=11.0, alt=-7.0, ust=-5.0)
TF = "1d"; EVREN = ["kripto"]; YON = 1
NEDEN = "Zaman dilimi belirtilmemiş; yazar tek kripto (ONE) için yazdığından günlük + kripto evreni."
def sinyal(df, atr, izle, alt, ust):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values
    a = gost.atr(h, l, c, int(atr))
    def pc2(off):
        x = gost.sh(c, off); y = gost.sh(c, off+2)
        with np.errstate(all="ignore"): return (x-y)/y*100
    p3, p0 = pc2(3), pc2(0)
    sig = (p3 >= alt) & (p0 <= 0) & (p3 <= ust)
    cond = (c > gost.sh(h)) & (gost.sh(o) <= gost.sh(c, 9))
    return dict(sig=sig.astype(float), xl=cond, dyl=c-izle*a)
