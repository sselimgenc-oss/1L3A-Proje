"""Pivot Point SuperTrend 'PPS' (WpJ5ym7u): pivot merkezli (ağırlıklı ortalama) SuperTrend yön değişimi ya da (KivancST yön değişimi + kapanış SMA20 yönünde) → long/short; hep piyasada. Pivotlar 2 mum gecikmeli onaylı."""
import numpy as np
from numba import njit
from tv import gost
from tv.stratejiler.fractal_sky import _pivots
ISIM = "Pivot Point SuperTrend (PPS)"; PINE_ID = "WpJ5ym7u"
PARAM = dict(prd=2, carpan=3.0, atr_p=10, st_atr=10, st_c=3.0, ma=20)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
@njit(cache=True)
def _pp(c, up, dn, ph, pl):
    n = len(c); tr = np.zeros(n); center = np.nan; tu = np.full(n, np.nan); td = np.full(n, np.nan); t = 1
    ctr = np.full(n, np.nan)
    for i in range(n):
        lp = ph[i] if not np.isnan(ph[i]) else (pl[i] if not np.isnan(pl[i]) else np.nan)
        if not np.isnan(lp): center = lp if np.isnan(center) else (center*2+lp)/3
        ctr[i] = center
    return ctr
@njit(cache=True)
def _tr(c, up, dn):
    n = len(c); tu = np.full(n, np.nan); td = np.full(n, np.nan); tr = np.ones(n)
    for i in range(n):
        if np.isnan(up[i]) or np.isnan(dn[i]): continue
        pu = tu[i-1] if i > 0 else np.nan; pd = td[i-1] if i > 0 else np.nan
        tu[i] = max(up[i], pu) if (i > 0 and not np.isnan(pu) and c[i-1] > pu) else up[i]
        td[i] = min(dn[i], pd) if (i > 0 and not np.isnan(pd) and c[i-1] < pd) else dn[i]
        pdv = td[i-1] if i > 0 and not np.isnan(td[i-1]) else np.nan; puv = tu[i-1] if i > 0 and not np.isnan(tu[i-1]) else np.nan
        tr[i] = tr[i-1] if i > 0 else 1.0
        if not np.isnan(pdv) and c[i] > pdv: tr[i] = 1.0
        elif not np.isnan(puv) and c[i] < puv: tr[i] = -1.0
    return tr
def sinyal(df, prd, carpan, atr_p, st_atr, st_c, ma):
    h, l, c = df.h.values, df.l.values, df.c.values
    ctr = _pp(c, c, c, _pivots(h, int(prd), int(prd), True), _pivots(l, int(prd), int(prd), False)); a = gost.atr(h, l, c, int(atr_p))
    tr = _tr(c, ctr-carpan*a, ctr+carpan*a); ptr = np.r_[1, tr[:-1]]
    t = gost.st_kivanc(c, (h+l)/2, gost.atr(h, l, c, int(st_atr)), st_c); pt = np.r_[1, t[:-1]]; m = gost.sma(c, int(ma))
    with np.errstate(invalid="ignore"):
        lg = ((t == 1) & (pt == -1) & (c > m)) | ((tr == 1) & (ptr == -1)); sh = ((t == -1) & (pt == 1) & (c < m)) | ((tr == -1) & (ptr == 1))
    return dict(sig=gost.flipsig(lg, sh))
