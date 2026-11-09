"""McGinley T3 Flow Campaign (Hrc7Gfqe): McGinley Dynamic(65) ± 1.2×ATR(28) kilitli 'flow trail'; trail 2 mum öncesinin üstüne/altına geçince long/short (ters sinyalde dön); kampanya hedefleri: birim=max(|kapanış−trail|, 0.25 ATR200); %30/%30/%40 kademeli TP1/TP2/TP3 = 1R/2R/3R (3 bacak); stop varsayılanda sadece görsel (canlı değil)."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "McGinley Flow Campaign"; PINE_ID = "Hrc7Gfqe"
PARAM = dict(mcg=65, atr_len=28, atr_c=1.2, hedef_c=1.0, rr1=1.0, rr2=2.0, rr3=3.0)
TF = "4h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik."
@njit(cache=True)
def _mcg(s, n):
    o = np.full(len(s), np.nan)
    for i in range(len(s)):
        if i == 0 or np.isnan(o[i-1]): o[i] = s[i]; continue
        r = s[i]/o[i-1]; r = 1.0 if r <= 0 else r
        o[i] = o[i-1] + (s[i]-o[i-1])/(n*r**4)
    return o
@njit(cache=True)
def _trail(b, dist):
    n = len(b); f = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(b[i]) or np.isnan(dist[i]): continue
        f[i] = f[i-1] if i > 0 and not np.isnan(f[i-1]) else b[i]
        if b[i]-dist[i] > f[i]: f[i] = b[i]-dist[i]
        if b[i]+dist[i] < f[i]: f[i] = b[i]+dist[i]
    return f
def sinyal(df, mcg, atr_len, atr_c, hedef_c, rr1, rr2, rr3):
    h, l, c = df.h.values, df.l.values, df.c.values; ft = _trail(_mcg(c, float(mcg)), gost.atr(h, l, c, int(atr_len))*atr_c); f2 = gost.sh(ft, 2)
    with np.errstate(invalid="ignore"):
        up = gost.crossover(np.nan_to_num(ft), np.nan_to_num(f2)) & ~np.isnan(f2); dn = gost.crossunder(np.nan_to_num(ft), np.nan_to_num(f2)) & ~np.isnan(f2)
    unit = np.maximum(np.abs(c-ft), gost.atr(h, l, c, 200)*0.25)*hedef_c; sg = gost.flipsig(up, dn)*np.where(up | dn, 1, 0)
    B = []
    for pay, rr in ((0.3, rr1), (0.3, rr2), (0.4, rr3)):
        B.append(dict(sig=sg, tpd=unit*rr, olcek=pay))
    return dict(bacaklar=B)
