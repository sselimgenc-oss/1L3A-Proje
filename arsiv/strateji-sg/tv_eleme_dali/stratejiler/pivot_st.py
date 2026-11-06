"""Pivot Point SuperTrend (DwdC6FT4): pivot merkez çizgisi ± ATR×3 bantları; trend dönüşünde yön değiştir."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Pivot Point SuperTrend"; PINE_ID = "DwdC6FT4"
PARAM = dict(pivot=2, faktor=3.0, atr=10)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük. Pivot onayı prd bar sonra gelir (repaint yok: yalnız geçmiş)."
@njit(cache=True)
def _pp(h, l, c, a, prd, factor):
    n = len(c); center = np.nan; tup = np.full(n, np.nan); tdn = np.full(n, np.nan); trend = np.ones(n)
    for i in range(n):
        j = i - prd
        if j >= prd and not np.isnan(a[i]):
            ph = True; pl = True
            for k in range(j-prd, j+prd+1):
                if k != j:
                    if h[k] >= h[j]: ph = False
                    if l[k] <= l[j]: pl = False
            lp = h[j] if ph else (l[j] if pl else np.nan)
            if not np.isnan(lp): center = lp if np.isnan(center) else (center*2 + lp)/3
        if np.isnan(center) or np.isnan(a[i]): continue
        up = center - factor*a[i]; dn = center + factor*a[i]
        pu = tup[i-1] if i > 0 and not np.isnan(tup[i-1]) else up
        pd_ = tdn[i-1] if i > 0 and not np.isnan(tdn[i-1]) else dn
        tup[i] = max(up, pu) if (i > 0 and c[i-1] > pu) else up
        tdn[i] = min(dn, pd_) if (i > 0 and c[i-1] < pd_) else dn
        if c[i] > pd_: trend[i] = 1
        elif c[i] < pu: trend[i] = -1
        else: trend[i] = trend[i-1]
    return trend
def sinyal(df, pivot, faktor, atr):
    h, l, c = df.h.values, df.l.values, df.c.values
    t = _pp(h, l, c, gost.atr(h, l, c, int(atr)), int(pivot), faktor)
    p = gost.sh(t, 1)
    return dict(sig=gost.flipsig((t == 1) & (p == -1), (t == -1) & (p == 1)))
