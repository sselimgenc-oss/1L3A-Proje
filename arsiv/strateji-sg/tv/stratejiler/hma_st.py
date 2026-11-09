"""HMA 50 + Supertrend Sniper (3SHJZytF): HMA yükselirken + supertrend yükselişte long; düşerken + düşüşte short; çelişki (choppy) → çıkış."""
import numpy as np
from tv import gost
ISIM = "HMA50 + Supertrend"; PINE_ID = "3SHJZytF"
PARAM = dict(hma=50, atr=10, carpan=3.0)
TF = "4h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik (Yahoo 1s 2 yıl, kripto 2019+)."
def sinyal(df, hma, atr, carpan):
    h, l, c = df.h.values, df.l.values, df.c.values
    hm = gost.hma(c, int(hma)); a = gost.atr(h, l, c, int(atr))
    _, d = gost.supertrend(h, l, c, a, carpan, (h+l)/2)
    ok = ~np.isnan(hm) & ~np.isnan(gost.sh(hm, 1))
    rs = ok & (hm > gost.sh(hm, 1)); fl = ok & (hm < gost.sh(hm, 1))
    bull = rs & (d == -1); bear = fl & (d == 1)
    chop = (rs & (d == 1)) | (fl & (d == -1))
    return dict(sig=gost.flipsig(bull, bear), xl=chop, xs=chop)
