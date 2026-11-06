"""Surgical Sweep (25Ffpyo0): 5/5 onaylı tepe/dip seviyelerinin hacimli (>1.2×SMA20) süpürülüp geri kapanması (önceki mum seviyeyi aştı ve üstte kapattı, bu mum altında kapattı) → short; dip için long. Hafta içi; ters sinyalde dön."""
import numpy as np
from tv import gost
from tv.stratejiler.fractal_sky import _pivots
ISIM = "Surgical Sweep"; PINE_ID = "25Ffpyo0"
PARAM = dict(geri=5, hacim=1.2)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş, hafta içi süzgeci var; saatlik."
def sinyal(df, geri, hacim):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values; n = len(c)
    ph = _pivots(h, int(geri), int(geri), True); pl = _pivots(l, int(geri), int(geri), False)
    res = np.full(n, np.nan); sup = np.full(n, np.nan); r = s = np.nan
    for i in range(n):
        if not np.isnan(ph[i]): r = ph[i]
        if not np.isnan(pl[i]): s = pl[i]
        res[i] = r; sup[i] = s
    hv = v > gost.sma(v, 20)*hacim; wd = df.index.dayofweek.values < 5
    with np.errstate(invalid="ignore"):
        sell = (gost.sh(h) > res) & (gost.sh(c) > res) & (c < res) & hv & wd
        buy = (gost.sh(l) < sup) & (gost.sh(c) < sup) & (c > sup) & hv & wd
    return dict(sig=gost.flipsig(buy, sell))
