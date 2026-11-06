"""Sequence Snap (49jNhJXM): kırmızı ana mumdan sonra 5 ardışık yeşil mum (kapanışlar %0.05 toleransla artan, düşükler ana mum dibi üstünde) + RSI(14)>40 ve yükseliyor → long; stop ana mum dibi, hedef 1.5R. Yalnız long (short varsayılan kapalı)."""
import numpy as np
from tv import gost
ISIM = "Sequence Snap"; PINE_ID = "49jNhJXM"
PARAM = dict(n=5, tol=0.05, rsi=14, rsi_min=40.0, rr=1.5)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]; YON = 1
NEDEN = "Vadeli (marjin) gün içi; saatlik."
def sinyal(df, n, tol, rsi, rsi_min, rr):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values; N = int(n)
    r = gost.rsi(c, int(rsi)); ok = (gost.sh(c, N) < gost.sh(o, N)) & (r > rsi_min) & (r > gost.sh(r))
    for i in range(N):
        ok = ok & (gost.sh(c, i) > gost.sh(o, i)) & (gost.sh(l, i) > gost.sh(l, N))
        if i < N-1: ok = ok & (gost.sh(c, i) > gost.sh(c, i+1)*(1-tol/100))
    sl = gost.sh(l, N)
    with np.errstate(invalid="ignore"):
        return dict(sig=ok.astype(float), sl=sl, tp=c + (c-sl)*rr)
