"""[3Commas] Turtle Strategy (9qFCuXqF): 20 mumluk Donchian kırılımı (kapanış önceki 20 tepesini aşar ve 20 mum önceki 20-tepesinin de üstünde) → long; simetrik short; çıkış: 10 mumluk dip/tepe çıtasından yukarı doğru sıkılaşan izleyen stop (kapanış çıtayı keser). TP kapalı. calc_on_every_tick yalnız canlıda etkili."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Turtle (3Commas)"; PINE_ID = "9qFCuXqF"
PARAM = dict(kanal=20, ofset=20, cikis=10)
TF = "4h"; EVREN = ["kripto"]
NEDEN = "PDF: ETHUSDT 4 saat."
@njit(cache=True)
def _dur(bf, sf, bs, ss, up_ex, lo_ex, c):
    n = len(c); sig = np.zeros(n); xl = np.zeros(n, np.bool_); xs = np.zeros(n, np.bool_)
    inb = False; ins = False; lb = np.nan; ls = np.nan; plb = np.nan; pls = np.nan
    for i in range(1, n):
        buy = bf[i] and bs[i] and not inb
        sel = sf[i] and ss[i] and not ins
        if buy: inb = True
        if sel: ins = True
        plb = lb; pls = ls
        if inb: lb = lo_ex[i] if np.isnan(lb) else max(lb, lo_ex[i])
        if ins: ls = up_ex[i] if np.isnan(ls) else min(ls, up_ex[i])
        eb = inb and (not np.isnan(lb)) and (not np.isnan(plb)) and c[i] < lb and c[i-1] >= plb
        es = ins and (not np.isnan(ls)) and (not np.isnan(pls)) and c[i] > ls and c[i-1] <= pls
        if buy: sig[i] = 1.0
        if sel: sig[i] = -1.0
        if eb: xl[i] = True; inb = False; lb = np.nan
        if es: xs[i] = True; ins = False; ls = np.nan
    return sig, xl, xs
def sinyal(df, kanal, ofset, cikis):
    h, l, c = df.h.values, df.l.values, df.c.values
    uf, lf = gost.highest(h, int(kanal)), gost.lowest(l, int(kanal))
    us, ls_ = gost.sh(gost.highest(h, int(kanal)), int(ofset)), gost.sh(gost.lowest(l, int(kanal)), int(ofset))
    with np.errstate(invalid="ignore"):
        bf = gost.crossover(c, gost.sh(uf)); sf = gost.crossunder(c, gost.sh(lf))
        bs = c > gost.sh(us); ss = c < gost.sh(ls_)
    sig, xl, xs = _dur(bf, sf, bs, ss, gost.highest(h, int(cikis)), gost.lowest(l, int(cikis)), c)
    return dict(sig=sig, xl=xl, xs=xs)
