"""RSI-Uyarlamalı T3 + Squeeze Momentum (7UNWrm2O, PakunFX): T3 (uzunluk RSI'ye göre 5–50 arası değişir) yukarı/aşağı dönerken sıkışma açık ve momentum işareti uyumluysa long/short; hep piyasada. (BB sapması Pine'daki gibi KC çarpanıyla.)"""
import numpy as np
from numba import njit
from tv import gost
ISIM = "RSI-Adaptive T3 + Squeeze Momentum"; PINE_ID = "7UNWrm2O"
PARAM = dict(rsi=14, min_len=5, max_len=50, v=0.7, bb=27, kc=20, kc_c=1.5)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
@njit(cache=True)
def _ema_v(s, L):
    n = len(s); o = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(s[i]): continue
        al = 2.0/(L[i]+1.0)
        if i == 0 or np.isnan(o[i-1]): o[i] = s[i]
        else: o[i] = al*s[i] + (1-al)*o[i-1]
    return o
def sinyal(df, rsi, min_len, max_len, v, bb, kc, kc_c):
    h, l, c = df.h.values, df.l.values, df.c.values
    r = gost.rsi(c, int(rsi)); L = np.round(min_len + (max_len-min_len)*(1 - r/100.0)); L = np.where(np.isnan(L), max_len, L)
    e1 = _ema_v(c, L); e2 = _ema_v(e1, L); e3 = _ema_v(e2, L); e4 = _ema_v(e3, L); e5 = _ema_v(e4, L); e6 = _ema_v(e5, L)
    c1 = -v**3; c2 = 3*v**2 + 3*v**3; c3 = -6*v**2 - 3*v - 3*v**3; c4 = 1 + 3*v + v**3 + 3*v**2
    t3 = c1*e6 + c2*e5 + c3*e4 + c4*e3
    basis = gost.sma(c, int(bb)); dev = kc_c*gost.stdev(c, int(bb)); ub, lb = basis+dev, basis-dev
    ma = gost.sma(c, int(kc)); rg = gost.sma(gost.tr(h, l, c), int(kc)); uk, lk = ma+rg*kc_c, ma-rg*kc_c
    off = (lb < lk) & (ub > uk)
    mid = (gost.highest(h, int(kc)) + gost.lowest(l, int(kc)))/2
    val = gost.linreg(c - (mid + gost.sma(c, int(kc)))/2, int(kc), 0)
    t3p = gost.sh(t3)
    with np.errstate(invalid="ignore"):
        lc = gost.crossover(np.nan_to_num(t3), np.nan_to_num(t3p)) & (val > 0) & off
        sc = gost.crossunder(np.nan_to_num(t3), np.nan_to_num(t3p)) & (val < 0) & off
    return dict(sig=gost.flipsig(lc, sc))
