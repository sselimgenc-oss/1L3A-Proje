"""Fib Confluence Scanner (rKsnPJbJ): 20/50/100 mumluk aralıkların 15 fib seviyesinden en az biri kapanışa %0.5 yakınsa + EMA50 trend süzgeci → trend yönünde giriş; %1.5 stop, 2R hedef. (Pratikte seviyeler fiyatı sık kapsadığından filtre hafif.)"""
import numpy as np
from tv import gost
ISIM = "Fib Confluence Scanner"; PINE_ID = "rKsnPJbJ"
PARAM = dict(a=20, b=50, c_=100, tol=0.5, min_c=1, ema=50, sl=1.5, rr=2.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, a, b, c_, tol, min_c, ema, sl, rr):
    h, l, c = df.h.values, df.l.values, df.c.values; cnt = np.zeros(len(c))
    for L in (a, b, c_):
        hi, lo = gost.highest(h, int(L)), gost.lowest(l, int(L)); rg = hi-lo
        for f in (0.236, 0.382, 0.5, 0.618, 0.786):
            with np.errstate(invalid="ignore"): cnt += (np.abs(c-(hi-f*rg))/c <= tol/100).astype(float)
    e = gost.ema(c, int(ema))
    with np.errstate(invalid="ignore"): lg = (cnt >= min_c) & (c > e); sh = (cnt >= min_c) & (c < e)
    return dict(sig=gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0), slp=sl/100, tpp=sl/100*rr)
