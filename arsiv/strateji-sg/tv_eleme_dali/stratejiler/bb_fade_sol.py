"""ITF26 B1 — BB Fade SOL 5m (pMOjQJwT): hafta içi 14:00–14:40 UTC penceresinde, gecikmeli (1 mum) Bollinger(20,2) bandına DOKUNAN ilk mumda band seviyesinde LİMİT emir (üst banda dokununca short, alt banda dokununca long); hedef orta band; stop yok; pencere sonunda (14:40) kapat."""
import numpy as np
from tv import gost
ISIM = "BB Fade SOL 5dk (14:00–14:40 UTC)"; PINE_ID = "pMOjQJwT"
PARAM = dict(bb=20, bb_c=2.0)
TF = "5m"; SEMBOL = ["SOL", "BTC", "ETH"]
NEDEN = "Başlık 5 dk SOL; 5 dk tarihçesi yalnız SOL/BTC/ETH için indirildi."
def sinyal(df, bb, bb_c):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values; n = len(c)
    b = gost.sma(c, int(bb)); d = gost.stdev(c, int(bb)); mid = gost.sh(b); up = mid + bb_c*gost.sh(d); lo = mid - bb_c*gost.sh(d)
    idx = df.index; hr = idx.hour.values; mn = idx.minute.values; wd = idx.dayofweek.values < 5
    inw = (hr == 14) & (mn <= 40) & wd; start = (hr == 14) & (mn == 0) & wd; end = (hr == 14) & (mn == 40) & wd
    sig = np.zeros(n); lep = np.full(n, np.nan); lepw = np.ones(n); tp = np.full(n, np.nan); xl = np.zeros(n, bool)
    placed = False; t_tp = np.nan
    for i in range(n):
        if start[i]: placed = False; t_tp = np.nan
        if inw[i] and not placed and not np.isnan(up[i]):
            if h[i] > up[i]: sig[i] = -1; lep[i] = up[i]; placed = True; t_tp = mid[i]
            elif l[i] < lo[i]: sig[i] = 1; lep[i] = lo[i]; placed = True; t_tp = mid[i]
            if placed:
                kalan = int(40 - mn[i]) // 5; lepw[i] = max(kalan, 1)
        if placed and inw[i]: tp[i] = t_tp
    return dict(sig=sig, lep=lep, lepw=lepw, tp=tp, xl=end, xs=end)
