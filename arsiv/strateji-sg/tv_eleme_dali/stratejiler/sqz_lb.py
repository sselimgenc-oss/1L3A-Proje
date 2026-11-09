"""Strategy for Squeeze Momentum Indicator [LazyBear] (qp9BoNyS): sıkışma bitişinin ilk mumunda (renk aqua) momentum >0 ve yükseliyorsa (lime) long, <0 ve düşüyorsa (red) short; long momentum yeşile (>0, düşüyor) dönünce, short bordoya (<0, yükseliyor) dönünce kapanır. BB(14, 2), KC(16, 1.5). G40dtEbK'dan farklı parametre ve giriş/çıkış kuralları."""
import numpy as np
from tv import gost
ISIM = "Squeeze Momentum (LazyBear strateji, 14/16)"; PINE_ID = "qp9BoNyS"
PARAM = dict(bb=14, bb_c=2.0, kc=16, kc_c=1.5)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, bb, bb_c, kc, kc_c):
    h, l, c = df.h.values, df.l.values, df.c.values
    b = gost.sma(c, int(bb)); dv = bb_c*gost.stdev(c, int(bb)); ub, lb = b+dv, b-dv
    ma = gost.sma(c, int(kc)); rg = gost.sma(gost.tr(h, l, c), int(kc)); uk, lk = ma+rg*kc_c, ma-rg*kc_c
    on = (lb > lk) & (ub < uk); off = (lb < lk) & (ub > uk)
    val = gost.linreg(c - ((gost.highest(h, int(kc)) + gost.lowest(l, int(kc)))/2 + gost.sma(c, int(kc)))/2, int(kc), 0); p = gost.nz(gost.sh(val))
    with np.errstate(invalid="ignore"):
        lime = (val > 0) & (val > p); green = (val > 0) & ~(val > p); red = (val < 0) & (val < p); maroon = (val < 0) & ~(val < p)
        aqua = off; start = aqua & ~np.r_[False, aqua[:-1]]
    return dict(sig=gost.flipsig(start & lime, start & red), xl=green, xs=maroon)
