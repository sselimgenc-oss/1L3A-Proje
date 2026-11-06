"""Multi-Factor Adaptive Z-Score (W67tJltC): ROC+RSI+hacim z-skorlarının uyarlamalı yumuşatılmış bileşiği sıfırı keserse giriş (ATR×2 stop), ters sıfır kesişiminde çıkış. process_orders_on_close=true."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Çok faktörlü Z-Score"; PINE_ID = "W67tJltC"
PARAM = dict(zper=100, roc=14, rsi=14, vol=20, w1=0.4, w2=0.3, w3=0.3, atr=14, atr_rank=100, min_y=2, max_y=15, stop=2.0)
TF = "4h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik."
@njit(cache=True)
def _yum(comp, rank, mn, mx):
    n = len(comp); o = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(comp[i]): continue
        r = 0.0 if np.isnan(rank[i]) else rank[i]
        L = max(round(mx - (mx-mn)*(r/100.0)), 1.0); al = 2.0/(L+1)
        o[i] = comp[i] if (i == 0 or np.isnan(o[i-1])) else o[i-1] + al*(comp[i]-o[i-1])
    return o
def _z(s, n):
    m = gost.sma(s, n); sd = gost.stdev(s, n)
    with np.errstate(all="ignore"): return np.where(sd > 0, (s-m)/sd, 0.0)
def sinyal(df, zper, roc, rsi, vol, w1, w2, w3, atr, atr_rank, min_y, max_y, stop):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values; n = int(zper)
    r = (c - gost.sh(c, int(roc)))/gost.sh(c, int(roc))*100; rs = gost.rsi(c, int(rsi)); vr = v/gost.sma(v, int(vol))
    ws = w1+w2+w3 or 1.0
    comp = (_z(r, n)*w1 + _z(rs, n)*w2 + _z(vr, n)*w3)/ws
    a = gost.atr(h, l, c, int(atr)); rank = gost.percentrank(a, int(atr_rank))
    sm = np.nan_to_num(_yum(comp, rank, float(min_y), float(max_y)), nan=0.0); z = np.zeros(len(c))
    ok = np.arange(len(c)) > n + atr_rank
    le = gost.crossover(sm, z) & ok; se = gost.crossunder(sm, z) & ok
    return dict(sig=gost.flipsig(le, se), xl=gost.crossunder(sm, z), xs=gost.crossover(sm, z), sld=a*stop, poc=True)
