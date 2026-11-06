"""Squeeze Momentum (G40dtEbK, LazyBear+PineIndicators): sıkışma bitince momentum yükseliyorsa long (düşüyorsa short); momentum ters dönünce çıkış. (Pine'daki 8× kaldıraç yerine standart pozisyon boyu.)"""
import numpy as np
from tv import gost
ISIM = "Squeeze Momentum (LazyBear)"; PINE_ID = "G40dtEbK"
PARAM = dict(bb=20, bb_c=2.0, kc=20, kc_c=1.5, ema=100)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, bb, bb_c, kc, kc_c, ema):
    h, l, c = df.h.values, df.l.values, df.c.values
    b = gost.sma(c, int(bb)); dv = kc_c*gost.stdev(c, int(bb)); ub, lb = b+dv, b-dv
    ma = gost.sma(c, int(kc)); rg = gost.sma(gost.tr(h, l, c), int(kc)); uk, lk = ma+rg*kc_c, ma-rg*kc_c
    on = (lb > lk) & (ub < uk); off = (lb < lk) & (ub > uk)
    val = gost.linreg(c - ((gost.highest(h, int(kc)) + gost.lowest(l, int(kc)))/2 + gost.sma(c, int(kc)))/2, int(kc), 0)
    e = gost.ema(c, int(ema)); pv = gost.sh(val, 1); pon = gost.sh(on.astype(float)) == 1; poff = gost.sh(off.astype(float)) == 1
    lo100 = gost.sh(gost.lowest(np.nan_to_num(val), 100)); hi100 = gost.sh(gost.highest(np.nan_to_num(val), 100))
    ok = ~np.isnan(val) & ~np.isnan(pv)
    gray = ~on & off   # sqzOff (Pine'da gray = sqzOff değil noSqz değil: sqzOff)
    lc = gray & pon & (val > pv) & (val > lo100) & (c > gost.sh(c)) & (c > e) & ok
    sc = on & poff & (val < pv) & (val < hi100) & (c < gost.sh(c)) & (c < e) & ok
    return dict(sig=gost.flipsig(lc, sc), xl=(val < pv) & ok, xs=(val > pv) & ok)
