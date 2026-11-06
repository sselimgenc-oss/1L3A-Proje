"""BIST30→S&P ATR Momentum Rider (jd1KSVn7, newton61): HMA(8) > HMA(9) > HMA(20) rejimi yeni başlarsa (ve HMA20 eğimi ≥ −0.18 ATR/gün) long; rejim yeniden başlarsa pozisyon yenilenir; çıkış 'K1': MFE ≥ 1.5 ATR olduktan sonra tepeden %5.75 izleyen stop (girişten 4 mum sonra). Yalnız long."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "ATR Momentum Rider (HMA rejimi)"; PINE_ID = "jd1KSVn7"
PARAM = dict(f=8, m=9, s=20, atr=14, k1a=1.5, k1t=5.75, k1w=4)
TF = "1d"; EVREN = ["endeks", "abd", "bist", "emtia", "kripto"]; YON = 1
NEDEN = "PDF: endeks vadelileri, günlük → tüm pazarlar günlük."
@njit(cache=True)
def _dur(setup, o, h, c, a, k1a, k1t, k1w):
    n = len(c); sig = np.zeros(n); xl = np.zeros(n, np.bool_); pos = False; ep = 0.0; ea = 0.0; pk = 0.0; act = False; tr = np.nan; eb = 0
    for i in range(1, n-1):
        k1 = False
        if pos:
            pk = max(pk, h[i])
            if act:
                cand = pk*(1.0 - k1t/100.0); tr = cand if np.isnan(tr) else max(tr, cand)
                k1 = (i >= eb + k1w) and c[i] <= tr
            if (not act) and ea > 0 and (pk - ep)/ea >= k1a: act = True; tr = np.nan
        if setup[i]:
            if pos: xl[i] = True
            sig[i] = 1.0; pos = True; ep = o[i+1]; ea = a[i]; pk = h[i+1]; act = False; tr = np.nan; eb = i+1
        elif k1:
            xl[i] = True; pos = False
    return sig, xl
def sinyal(df, f, m, s, atr, k1a, k1t, k1w):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values
    hf, hm, hs = gost.hma(c, int(f)), gost.hma(c, int(m)), gost.hma(c, int(s)); a = gost.atr(h, l, c, int(atr))
    with np.errstate(all="ignore"):
        reg = (hf > hm) & (hm > hs); raw = reg & ~np.r_[False, reg[:-1]]
        slope = (hs - gost.sh(hs, 3))/3/a; ok = slope >= -0.18
        st = raw & ok
    sg, xl = _dur(np.nan_to_num(st.astype(float)) > 0, o, h, c, np.nan_to_num(a), k1a, k1t, int(k1w))
    return dict(sig=sg, xl=xl)
