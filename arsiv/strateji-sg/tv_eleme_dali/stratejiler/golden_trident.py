"""Golden Trident (Eq4kPrrJ): 30 mumluk tepe/dip yapısıyla yön (son tepe son dipten yeniyse yukarı); yön yukarı + kapanış > EMA200 + aralık > 0.8×ATR(20) olunca YENİ long tetiği; yön aşağı dönünce çık; 8×ATR felaket stopu. Yalnız long (altın)."""
import numpy as np
from tv import gost
ISIM = "Golden Trident (swing yönü)"; PINE_ID = "Eq4kPrrJ"
PARAM = dict(swing=30, ema=200, chop=20, chop_c=0.8, atr=14, stop=8.0)
TF = "1d"; SEMBOL = ["ALTIN", "GUMUS", "PETROL"]; YON = 1
NEDEN = "Başlık XAU; günlük emtia."
def sinyal(df, swing, ema, chop, chop_c, atr, stop):
    h, l, c = df.h.values, df.l.values, df.c.values; n = len(c); S = int(swing)
    hh, ll = gost.highest(h, S), gost.lowest(l, S); phL = -1; plL = -1; dr = np.zeros(n)
    for i in range(n):
        if not np.isnan(hh[i]) and h[i] >= hh[i]: phL = i
        if not np.isnan(ll[i]) and l[i] <= ll[i]: plL = i
        dr[i] = 1 if phL > plL else -1
    e = gost.ema(c, int(ema)); ac = gost.atr(h, l, c, int(chop)); a = gost.atr(h, l, c, int(atr))
    with np.errstate(invalid="ignore"):
        cond = (dr == 1) & (c > e) & ((gost.highest(h, int(chop)) - gost.lowest(l, int(chop))) > ac*chop_c)
    trig = cond & ~np.r_[False, cond[:-1]]
    return dict(sig=trig.astype(float), xl=dr == -1, sl=c - a*stop)
