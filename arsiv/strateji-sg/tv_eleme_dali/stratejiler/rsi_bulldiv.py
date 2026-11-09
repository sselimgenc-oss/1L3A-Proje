"""RSI Bullish Divergence (Oversold) Breakout (Qg1Jra51): iki ardışık RSI dibi (5/5 pivot, ilk dip <30, ikincisi daha yüksek RSI ama fiyatta daha düşük dip, aralarında 5–60 mum) → RSI iki dip arasındaki RSI zirvesini yukarı kırarsa long; hedef iki dip arası fiyat zirvesi, stop 2. dibin altı. Yalnız long; her karar yalnız kapanmış mumlarla."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "RSI Bullish Divergence Breakout"; PINE_ID = "Qg1Jra51"
PARAM = dict(rsi=14, os=30.0, lbl=5, lbr=5, rmin=5, rmax=60, bekle=30)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]; YON = 1
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
@njit(cache=True)
def _left(r, p, lbl):
    if p - lbl < 0 or np.isnan(r[p-lbl]) or np.isnan(r[p]): return False
    for i in range(1, lbl+1):
        if r[p] >= r[p-i]: return False
    return True
@njit(cache=True)
def _right(r, p, k):
    if p < 0: return False
    for i in range(1, k+1):
        if r[p] >= r[p+i]: return False
    return True
@njit(cache=True)
def _try(r, h, l, pvb, pvr, pvl, p2, last, rmin, rmax, os):
    if pvb < 0 or p2 == last: return False, 0.0, 0.0
    gap = p2 - pvb
    if gap >= rmin and gap <= rmax and pvr < os and r[p2] > pvr and l[p2] < pvl:
        hh = r[pvb+1]; tt = h[pvb+1]
        for i in range(pvb+1, p2): hh = max(hh, r[i]); tt = max(tt, h[i])
        return True, hh, tt
    return False, 0.0, 0.0
@njit(cache=True)
def _sim(r, h, l, c, lbl, lbr, rmin, rmax, bekle, os):
    n = len(c); sig = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan)
    pvb = -1; pvr = 0.0; pvl = 0.0; act = False; p2 = -1; H = 0.0; T = 0.0; S = 0.0; rsi2 = 0.0; last = -1
    for t in range(n):
        if np.isnan(r[t]): continue
        if act and (r[t] < rsi2 or t - p2 > bekle): act = False
        pc = t - lbr
        if pc >= 0 and _left(r, pc, lbl) and _right(r, pc, lbr):
            ok, hh, tt = _try(r, h, l, pvb, pvr, pvl, pc, last, rmin, rmax, os)
            if ok:
                act = True; p2 = pc; H = hh; T = tt; rsi2 = r[pc]; last = pc; S = l[pc]
                for i in range(pc, t+1): S = min(S, l[i])
            pvb = pc; pvr = r[pc]; pvl = l[pc]
        if lbr > 1:
            for k in range(1, lbr):
                q = t - k
                if q >= 0 and _left(r, q, lbl) and _right(r, q, k):
                    ok, hh, tt = _try(r, h, l, pvb, pvr, pvl, q, last, rmin, rmax, os)
                    if ok:
                        act = True; p2 = q; H = hh; T = tt; rsi2 = r[q]; last = q; S = l[q]
                        for i in range(q, t+1): S = min(S, l[i])
                    break
        if act:
            S = min(S, l[t])
            if r[t] > H:
                s = S; tg = T
                if c[t] < tg and c[t] > s: sig[t] = 1.0; sl[t] = s; tp[t] = tg
                act = False
    return sig, sl, tp
def sinyal(df, rsi, os, lbl, lbr, rmin, rmax, bekle):
    h, l, c = df.h.values, df.l.values, df.c.values; r = gost.rsi(c, int(rsi))
    sg, s, t = _sim(r, h, l, c, int(lbl), int(lbr), int(rmin), int(rmax), int(bekle), float(os))
    return dict(sig=sg, sl=s, tp=t)
