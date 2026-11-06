"""HalfTrend Strategy (0vvrOpg1): amplitude 2, sapma 2; HalfTrend yön değiştirince long/short. Hint seans penceresi (09:20-15:20) ve gün sonu çıkışı uygulanmadı (NSE'ye özgü)."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "HalfTrend"; PINE_ID = "0vvrOpg1"
PARAM = dict(genlik=2, sapma=2)
TF = "1h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Yazar Hint gün içi (NSE) için yazmış; seans/gün sonu kuralı atılıp 1 saatlik, tüm pazarlarda test."
@njit(cache=True)
def _ht(h, l, c, ma_h, ma_l, hh, ll, amp):
    n = len(c); trend = np.zeros(n); nxt = 0; maxlow = l[0]; minhigh = h[0]; up = 0.0; dn = 0.0
    buy = np.zeros(n, np.bool_); sell = np.zeros(n, np.bool_); tr = 0
    for i in range(1, n):
        if np.isnan(ma_h[i]) or np.isnan(hh[i]): trend[i] = tr; continue
        if nxt == 1:
            maxlow = max(ll[i], maxlow)
            if ma_h[i] < maxlow and c[i] < l[i-1]:
                tr = 1; nxt = 0; minhigh = hh[i]
        else:
            minhigh = min(hh[i], minhigh)
            if ma_l[i] > minhigh and c[i] > h[i-1]:
                tr = 0; nxt = 1; maxlow = ll[i]
        if tr == 0:
            if trend[i-1] != 0 and i > amp + 1: buy[i] = True; up = dn
            else: up = max(maxlow, up) if up != 0 else maxlow
        else:
            if trend[i-1] != 1 and i > amp + 1: sell[i] = True; dn = up
            else: dn = min(minhigh, dn) if dn != 0 else minhigh
        trend[i] = tr
    return buy, sell
def sinyal(df, genlik, sapma):
    h, l, c = df.h.values, df.l.values, df.c.values; a = int(genlik)
    hh = np.full(len(c), np.nan); ll = np.full(len(c), np.nan)
    hmax = gost.highest(h, a); lmin = gost.lowest(l, a)
    b, s = _ht(h, l, c, gost.sma(h, a), gost.sma(l, a), hmax, lmin, a)
    return dict(sig=gost.flipsig(b, s))
