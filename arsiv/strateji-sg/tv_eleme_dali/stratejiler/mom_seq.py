"""Momentum Sequence [Herman] (mmrInMTp): kırmızı 'ana' mumun ardından 5 ardışık yeşil mum (her biri öncekinden yüksek kapanış, düşükleri ana mumun dibinin üstünde) → long; stop = ana mum dibi, hedef = 1.5R. Yalnız long (short varsayılan kapalı)."""
import numpy as np
from tv import gost
ISIM = "Momentum Sequence (Herman)"; PINE_ID = "mmrInMTp"
PARAM = dict(n=5, rr=1.5)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]; YON = 1
NEDEN = "Vadeli sözleşme (kontrat başı komisyon, marjin) için yazılmış gün içi; saatlik."
def sinyal(df, n, rr):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values; N = int(n); m = len(c)
    ok = gost.sh(c, N) < gost.sh(o, N)
    for i in range(N):
        ok = ok & (gost.sh(c, i) > gost.sh(o, i)) & (gost.sh(l, i) > gost.sh(l, N))
        if i < N-1: ok = ok & (gost.sh(c, i) > gost.sh(c, i+1))
    sl = gost.sh(l, N)
    with np.errstate(invalid="ignore"):
        return dict(sig=ok.astype(float), sl=sl, tp=c + (c-sl)*rr)
