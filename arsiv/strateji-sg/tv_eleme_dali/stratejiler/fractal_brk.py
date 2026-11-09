"""Fractal Breakout (EjLwVtgp, ChartArt): son 3 fraktal tepe fiyatı ortalaması yükseliyor ve fiyat son fraktalı kırıyor → long; 3 bar içinde trend bozulursa çıkış. Yalnız long."""
import numpy as np
from tv import gost
ISIM = "Fractal Breakout (ChartArt)"; PINE_ID = "EjLwVtgp"
PARAM = dict(n_bar=3)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]; YON = 1
NEDEN = "Zaman dilimi belirtilmemiş; günlük (klasik 2016 betiği), yalnız long."
def _valuewhen(cond, x, occ):
    idx = np.flatnonzero(cond); o = np.full(len(x), np.nan)
    if len(idx) <= occ: return o
    # her bar için, o ana dek koşulun gerçekleştiği (occ+1)'inci sondan değer
    cnt = np.cumsum(cond)
    for k in range(occ, len(idx)):
        lo = idx[k]; hi = idx[k+1] if k+1 < len(idx) else len(x)
        o[lo:hi] = x[idx[k-occ]]
    return o
def sinyal(df, n_bar):
    h, l = df.h.values, df.l.values; p = (h+l)/2
    h2 = gost.sh(h, 2)
    ft = (h2 > gost.sh(h, 3)) & (h2 > gost.sh(h, 4)) & (h2 > gost.sh(h, 1)) & (h2 > h)
    fp = _valuewhen(ft, p, 1)
    avg = (gost.sh(fp, 1) + gost.sh(fp, 2) + gost.sh(fp, 3))/3
    tr_ = avg > gost.sh(avg, 1)
    brk = gost.sh(p, 1) > fp
    entry = tr_ & brk
    exit_ = gost.sh(tr_.astype(float), int(n_bar)).astype(bool) & ~tr_ & ~np.isnan(gost.sh(avg, int(n_bar)))
    return dict(sig=entry.astype(float), xl=exit_)
