"""PMax on RSI w/ T3 (ZLcmWQtj): RSI'nin (Wilder benzeri) Tillson T3'ü üzerine PMax (ATR yerine RSI-aralığı 'ATR'si ×3); T3, PMax'i yukarı keserse long, aşağı keserse short; hep piyasada."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "PMax on RSI (T3)"; PINE_ID = "ZLcmWQtj"
PARAM = dict(carpan=3.0, t3_len=8, t3_v=0.7, atr=10, rsi=14)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
@njit(cache=True)
def _ww(x, n):
    o = np.zeros(len(x)); a = 1.0/n
    for i in range(len(x)): o[i] = a*x[i] + (1-a)*(o[i-1] if i > 0 else 0.0)
    return o
@njit(cache=True)
def _pmax(m, atr, mult):
    n = len(m); pm = np.full(n, np.nan); ls = np.nan; ss = np.nan; d = 1
    for i in range(n):
        if np.isnan(m[i]) or np.isnan(atr[i]): continue
        l0 = m[i]-mult*atr[i]; s0 = m[i]+mult*atr[i]; pl = ls if not np.isnan(ls) else l0; ps = ss if not np.isnan(ss) else s0
        ls = max(l0, pl) if m[i] > pl else l0; ss = min(s0, ps) if m[i] < ps else s0
        if d == -1 and m[i] > ps: d = 1
        elif d == 1 and m[i] < pl: d = -1
        pm[i] = ls if d == 1 else ss
    return pm
def sinyal(df, carpan, t3_len, t3_v, atr, rsi):
    h, l, c = df.h.values, df.l.values, df.c.values; n = int(rsi); pc = gost.sh(c)
    with np.errstate(invalid="ignore"):
        up = np.where(c >= pc, c-pc, 0.0); dn = np.where(c < pc, pc-c, 0.0)
    up, dn = np.nan_to_num(up), np.nan_to_num(dn)
    au, ad = _ww(up, n), _ww(dn, n); sau, sad = gost.sma(up, n), gost.sma(dn, n)
    with np.errstate(all="ignore"):
        rs = au/ad; r = np.where(rs == -1, 0, 100-100/(1+rs))
        k1 = np.where(h > pc, h-pc, 0.0); k2 = np.where(h < pc, pc-h, 0.0); k3 = np.where(l > pc, l-pc, 0.0); k4 = np.where(l < pc, pc-l, 0.0)
        ruh = (sau*(n-1)+k1)/n; rdh = (sad*(n-1)+k2)/n; rul = (sau*(n-1)+k3)/n; rdl = (sad*(n-1)+k4)/n
        rh = 100-100/(1+ruh/rdh); rl = 100-100/(1+rul/rdl); rp = gost.sh(r)
        tr = np.maximum.reduce([rh-rl, np.abs(rh-rp), np.abs(rl-rp)])
    a = gost.sma(tr, int(atr)); L = int(t3_len)
    e1 = gost.ema(r, L); e2 = gost.ema(e1, L); e3 = gost.ema(e2, L); e4 = gost.ema(e3, L); e5 = gost.ema(e4, L); e6 = gost.ema(e5, L); v = t3_v
    t3 = -v**3*e6 + (3*v**2+3*v**3)*e5 + (-6*v**2-3*v-3*v**3)*e4 + (1+3*v+v**3+3*v**2)*e3
    pm = _pmax(t3, a, carpan)
    with np.errstate(invalid="ignore"):
        return dict(sig=gost.flipsig(gost.crossover(np.nan_to_num(t3), np.nan_to_num(pm)) & ~np.isnan(pm), gost.crossunder(np.nan_to_num(t3), np.nan_to_num(pm)) & ~np.isnan(pm)))
