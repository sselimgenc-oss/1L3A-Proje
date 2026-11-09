"""Glow Ribbon Flip (OUOx3rYT): EMA21 ± 2×ATR(10) izleyen bantlar (SuperTrend benzeri); yön dönüşünde (flip) ve trend içinde EMA'yı yeniden aşınca (pullback) giriş; stop = ilgili bant, hedef 2R."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Glow Ribbon Flip"; PINE_ID = "OUOx3rYT"
PARAM = dict(ema=21, atr=10, carpan=2.0, tp_r=2.0)
TF = "4h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik."
@njit(cache=True)
def _bant(c, basis, a, mult):
    n = len(c); lo = np.full(n, np.nan); hi = np.full(n, np.nan); d = np.zeros(n)
    for i in range(n):
        if np.isnan(basis[i]) or np.isnan(a[i]): continue
        ln = basis[i]-mult*a[i]; hn = basis[i]+mult*a[i]; pl = lo[i-1] if i > 0 else np.nan; ph = hi[i-1] if i > 0 else np.nan
        lo[i] = ln if (np.isnan(pl) or ln > pl or c[i-1] < pl) else pl
        hi[i] = hn if (np.isnan(ph) or hn < ph or c[i-1] > ph) else ph
        pd = d[i-1] if i > 0 else 0.0
        if pd == 0: d[i] = 1.0 if c[i] > basis[i] else -1.0
        elif pd == 1 and not np.isnan(pl) and c[i] < pl: d[i] = -1.0
        elif pd == -1 and not np.isnan(ph) and c[i] > ph: d[i] = 1.0
        else: d[i] = pd
    return lo, hi, d
def sinyal(df, ema, atr, carpan, tp_r):
    h, l, c = df.h.values, df.l.values, df.c.values
    b = gost.ema(c, int(ema)); a = gost.atr(h, l, c, int(atr)); lo, hi, d = _bant(c, b, a, carpan); pd = gost.sh(d)
    pb = gost.sh(c)
    with np.errstate(invalid="ignore"):
        fb = (d == 1) & (pd != 1); fs = (d == -1) & (pd != -1)
        pbu = (d == 1) & (pd == 1) & (c > b) & (pb <= gost.sh(b)); pbs = (d == -1) & (pd == -1) & (c < b) & (pb >= gost.sh(b))
        lg = fb | pbu; sh = fs | pbs; st = np.where(d == 1, lo, hi); dist = np.abs(c-st)
    return dict(sig=gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0), sl=np.where(lg, lo, np.where(sh, hi, np.nan)), tpd=dist*tp_r, dyl=np.where(d == 1, lo, np.nan), dys=np.where(d == -1, hi, np.nan))
