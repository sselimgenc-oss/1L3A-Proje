"""BB Power Oscillator + Squeeze Release (M6uONKNI): Bollinger üstü/altı taşma gücü osilatörü (bull/bear, 14 mum) 50'yi yukarı keserse (sıkışma sonrası 10 mum içinde) long/short; stop 1.4 ATR(30), hedef 1.5R, 0.75R'de başa-baş + ATR(1.5) izleyen stop, 50 mumda çıkış."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "BB Power Oscillator + Squeeze"; PINE_ID = "M6uONKNI"
PARAM = dict(bb=14, bb_c=1.0, esik=50.0, sq=20, sq_bb=2.0, sq_kc=1.5, pencere=10, atr=30, atr_c=1.4, rr=1.5, be=0.75, iz=1.5, tutma=50)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; saatlik."
@njit(cache=True)
def _osc(s, up, lo, n):
    m = len(s); bu = np.zeros(m); be = np.zeros(m)
    for t in range(n-1, m):
        a = b = da = db = 0.0
        for i in range(n):
            x = s[t-i]; u = up[t-i]; l = lo[t-i]
            a += max(x-u, 0.0); b += max(l-x, 0.0); da += abs(x-u); db += abs(l-x)
        bu[t] = a/da*100 if da != 0 else 0.0; be[t] = b/db*100 if db != 0 else 0.0
    return bu, be
def sinyal(df, bb, bb_c, esik, sq, sq_bb, sq_kc, pencere, atr, atr_c, rr, be, iz, tutma):
    h, l, c = df.h.values, df.l.values, df.c.values; n = len(c)
    e = gost.ema(c, int(bb)); sd = gost.stdev(c, int(bb))*bb_c; bu, br = _osc(np.nan_to_num(c), np.nan_to_num(e+sd), np.nan_to_num(e-sd), int(bb))
    b0 = gost.sma(c, int(sq)); dv = sq_bb*gost.stdev(c, int(sq)); kb = gost.ema(c, int(sq)); kd = gost.ema(gost.tr(h, l, c), int(sq))
    with np.errstate(invalid="ignore"):
        on = (b0-dv > kb-kd*sq_kc) & (b0+dv < kb+kd*sq_kc); rel = (~on) & np.r_[False, on[:-1]]
    bs = gost.barssince(rel); ok = bs <= pencere; a = gost.atr(h, l, c, int(atr)); ix = np.arange(n) >= max(bb, sq)+2
    f = np.full(n, esik)
    lg = gost.crossover(bu, f) & ok & ix; sh = gost.crossover(br, f) & ok & ix
    d = a*atr_c
    return dict(sig=gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0), sld=d, tpd=d*rr, taa=d*be, toa=a*iz, tbe=1, maxhold=int(tutma))
