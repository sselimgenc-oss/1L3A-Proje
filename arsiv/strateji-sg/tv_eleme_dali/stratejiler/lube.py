"""LUBE (i9tJOtjl): 'sürtünme' = son 500 mumdan kaçının aralığı bugünkü kapanışı içeriyor (ağırlıklı); sürtünme düşükken (alt eşik, 5 mum gecikmeli) FIR eğimine göre long/short; sürtünme orta eşiği aşınca çık. 20 mum ısınma."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "LUBE (sürtünme)"; PINE_ID = "i9tJOtjl"
PARAM = dict(geri=500, fl=50.0, tl=-10.0, aralik=100)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
@njit(cache=True)
def _fr(h, l, c, B):
    n = len(c); f = np.zeros(n)
    for t in range(n):
        s = 0.0
        for i in range(1, B+1):
            if t-i >= 0 and h[t-i] >= c[t] and l[t-i] <= c[t]: s += (1.0+B)/(i+B)
        f[t] = s
    return f
def sinyal(df, geri, fl, tl, aralik):
    h, l, c = df.h.values, df.l.values, df.c.values; fr = _fr(h, l, c, int(geri)); f = fl/100; t = tl/100
    lo, hi = gost.lowest(fr, int(aralik)), gost.highest(fr, int(aralik)); mid = lo*(1-f)+hi*f; lo2 = lo*(1-t)+hi*t
    fir = (4*c + 3*gost.nz(gost.sh(c, 1)) + 2*gost.nz(gost.sh(c, 2)) + gost.nz(gost.sh(c, 3)))/10; tr = np.where(fir > gost.sh(fir), 1, -1)
    m5, l5 = gost.sh(mid, 5), gost.sh(lo2, 5); bars = np.arange(len(c)) + 1
    with np.errstate(invalid="ignore"):
        lg = (fr < l5) & (tr == 1) & (bars > 20); sh = (fr < l5) & (tr == -1) & (bars > 20); end = fr > m5
    return dict(sig=gost.flipsig(lg, sh), xl=sh | end, xs=lg | end)
