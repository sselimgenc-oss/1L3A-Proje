"""Hacim Onaylı Destek/Direnç Kırılımı (CItvSvqk): 10/10 pivot direnci hacim 1.5×ort. + EMA200 üstünde yukarı kırılırsa long (destek aşağı kırılırsa short); stop = kırılan destek − 0.25 ATR, hedef ATR×3."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Hacim onaylı S/R kırılımı"; PINE_ID = "CItvSvqk"
PARAM = dict(pivot=10, vol=20, vol_c=1.5, ema=200, atr=14, stop_atr=1.5, hedef=3.0, tampon=0.25)
TF = "4h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik. Pivotlar 10 bar sonra onaylanır (repaint yok)."
@njit(cache=True)
def _sr(h, l, k):
    n = len(h); res = np.full(n, np.nan); sup = np.full(n, np.nan); r = np.nan; s = np.nan
    for i in range(n):
        j = i - k
        if j >= k:
            ph = True; pl = True
            for m in range(j-k, j+k+1):
                if m != j:
                    if h[m] >= h[j]: ph = False
                    if l[m] <= l[j]: pl = False
            if ph: r = h[j]
            if pl: s = l[j]
        res[i] = r; sup[i] = s
    return res, sup
def sinyal(df, pivot, vol, vol_c, ema, atr, stop_atr, hedef, tampon):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    r, s = _sr(h, l, int(pivot)); vs = v > gost.sma(v, int(vol))*vol_c; e = gost.ema(c, int(ema)); a = gost.atr(h, l, c, int(atr))
    with np.errstate(invalid="ignore"):
        lb = gost.crossover(c, np.nan_to_num(r, nan=1e18)) & vs & (c > e) & ~np.isnan(r)
        sb = gost.crossunder(c, np.nan_to_num(s, nan=-1e18)) & vs & (c < e) & ~np.isnan(s)
        sl = np.where(lb, np.where(np.isnan(s), c - a*stop_atr, s - a*tampon), np.where(sb, np.where(np.isnan(r), c + a*stop_atr, r + a*tampon), np.nan))
    return dict(sig=gost.flipsig(lb, sb), sl=sl, tpd=a*hedef)
