"""Pine ta.* eşdeğeri göstergeler (numba). NaN yayılımı Pine gibi: ilk geçerli pencere dolana dek NaN."""
import numpy as np
from numba import njit

@njit(cache=True)
def sma(x, n):
    o = np.full(len(x), np.nan); s = 0.0; k = 0
    for i in range(len(x)):
        if np.isnan(x[i]): s = 0.0; k = 0; continue
        s += x[i]; k += 1
        if k > n: s -= x[i-n]; k = n
        if k == n: o[i] = s/n
    return o

@njit(cache=True)
def ema(x, n):
    o = np.full(len(x), np.nan); a = 2.0/(n+1); k = 0; s = 0.0; prev = np.nan
    for i in range(len(x)):
        if np.isnan(x[i]): continue
        if np.isnan(prev):
            s += x[i]; k += 1
            if k == n: prev = s/n; o[i] = prev
        else:
            prev = a*x[i] + (1-a)*prev; o[i] = prev
    return o

@njit(cache=True)
def rma(x, n):
    o = np.full(len(x), np.nan); a = 1.0/n; k = 0; s = 0.0; prev = np.nan
    for i in range(len(x)):
        if np.isnan(x[i]): continue
        if np.isnan(prev):
            s += x[i]; k += 1
            if k == n: prev = s/n; o[i] = prev
        else:
            prev = a*x[i] + (1-a)*prev; o[i] = prev
    return o

@njit(cache=True)
def wma(x, n):
    o = np.full(len(x), np.nan); d = n*(n+1)/2.0
    for i in range(n-1, len(x)):
        s = 0.0; bad = False
        for j in range(n):
            v = x[i-j]
            if np.isnan(v): bad = True; break
            s += v*(n-j)
        if not bad: o[i] = s/d
    return o

def hma(x, n):
    w = wma(2*wma(x, n//2) - wma(x, n), int(round(np.sqrt(n))))
    return w

@njit(cache=True)
def shift(x, k):
    o = np.full(len(x), np.nan)
    if k >= 0:
        o[k:] = x[:len(x)-k] if k > 0 else x
    return o

@njit(cache=True)
def tr(h, l, c):
    o = np.empty(len(h)); o[0] = h[0]-l[0]
    for i in range(1, len(h)):
        o[i] = max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1]))
    return o

def atr(h, l, c, n): return rma(tr(h, l, c), n)

@njit(cache=True)
def rsi(x, n):
    up = np.full(len(x), np.nan); dn = np.full(len(x), np.nan)
    for i in range(1, len(x)):
        d = x[i]-x[i-1]
        if np.isnan(d): continue
        up[i] = max(d, 0.0); dn[i] = max(-d, 0.0)
    a = rma(up, n); b = rma(dn, n); o = np.full(len(x), np.nan)
    for i in range(len(x)):
        if np.isnan(a[i]) or np.isnan(b[i]): continue
        o[i] = 100.0 if b[i] == 0 else 100.0 - 100.0/(1.0 + a[i]/b[i])
    return o

@njit(cache=True)
def stdev(x, n):
    o = np.full(len(x), np.nan)
    for i in range(n-1, len(x)):
        m = 0.0; bad = False
        for j in range(n):
            v = x[i-j]
            if np.isnan(v): bad = True; break
            m += v
        if bad: continue
        m /= n; s = 0.0
        for j in range(n): s += (x[i-j]-m)**2
        o[i] = np.sqrt(s/n)
    return o

@njit(cache=True)
def highest(x, n):
    o = np.full(len(x), np.nan)
    for i in range(n-1, len(x)):
        m = -np.inf; bad = False
        for j in range(n):
            if np.isnan(x[i-j]): bad = True; break
            if x[i-j] > m: m = x[i-j]
        if not bad: o[i] = m
    return o

@njit(cache=True)
def lowest(x, n):
    o = np.full(len(x), np.nan)
    for i in range(n-1, len(x)):
        m = np.inf; bad = False
        for j in range(n):
            if np.isnan(x[i-j]): bad = True; break
            if x[i-j] < m: m = x[i-j]
        if not bad: o[i] = m
    return o

@njit(cache=True)
def stoch(c, h, l, n):
    hh = highest(h, n); ll = lowest(l, n); o = np.full(len(c), np.nan)
    for i in range(len(c)):
        if not np.isnan(hh[i]):
            d = hh[i]-ll[i]
            o[i] = 100.0*(c[i]-ll[i])/d if d > 0 else 0.0
    return o

@njit(cache=True)
def linreg(x, n, off):
    o = np.full(len(x), np.nan)
    sx = n*(n-1)/2.0; sxx = (n-1)*n*(2*n-1)/6.0
    for i in range(n-1, len(x)):
        sy = 0.0; sxy = 0.0
        for j in range(n):
            y = x[i-n+1+j]; sy += y; sxy += j*y
        b = (n*sxy - sx*sy)/(n*sxx - sx*sx); a = (sy - b*sx)/n
        o[i] = a + b*(n-1-off)
    return o

@njit(cache=True)
def supertrend(h, l, c, a, mult, src):
    """Pine ta.supertrend: (çizgi, yön); yön=-1 yükseliş, +1 düşüş."""
    n = len(c); st = np.full(n, np.nan); d = np.ones(n)
    lo = np.full(n, np.nan); up = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(a[i]): continue
        lb = src[i]-mult*a[i]; ub = src[i]+mult*a[i]
        if i > 0 and not np.isnan(lo[i-1]):
            pl = lo[i-1]; pu = up[i-1]
            lb = lb if (lb > pl or c[i-1] < pl) else pl
            ub = ub if (ub < pu or c[i-1] > pu) else pu
            if st[i-1] == pu: d[i] = -1.0 if c[i] > ub else 1.0
            else: d[i] = 1.0 if c[i] < lb else -1.0
        lo[i] = lb; up[i] = ub
        st[i] = lb if d[i] == -1.0 else ub
    return st, d

@njit(cache=True)
def st_kivanc(c, src, a, mult):
    """KivancOzbilgic SuperTrend: trend dizisi (+1/-1)."""
    n = len(c); tr_ = np.ones(n); up = np.full(n, np.nan); dn = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(a[i]): continue
        u = src[i]-mult*a[i]; w = src[i]+mult*a[i]
        u1 = up[i-1] if i > 0 and not np.isnan(up[i-1]) else u
        w1 = dn[i-1] if i > 0 and not np.isnan(dn[i-1]) else w
        if i > 0 and c[i-1] > u1: u = max(u, u1)
        if i > 0 and c[i-1] < w1: w = min(w, w1)
        up[i] = u; dn[i] = w
        t = tr_[i-1] if i > 0 else 1.0
        if t == -1 and c[i] > w1: t = 1.0
        elif t == 1 and c[i] < u1: t = -1.0
        tr_[i] = t
    return tr_

@njit(cache=True)
def crossover(a, b):
    o = np.zeros(len(a), np.bool_)
    for i in range(1, len(a)):
        o[i] = a[i] > b[i] and a[i-1] <= b[i-1]
    return o

@njit(cache=True)
def crossunder(a, b):
    o = np.zeros(len(a), np.bool_)
    for i in range(1, len(a)):
        o[i] = a[i] < b[i] and a[i-1] >= b[i-1]
    return o

def mfi(h, l, c, v, n):
    p = (h+l+c)/3.0; f = p*v
    pos = np.where(np.r_[False, np.diff(p) > 0], f, 0.0); neg = np.where(np.r_[False, np.diff(p) < 0], f, 0.0)
    s1 = sma(pos, n)*n; s2 = sma(neg, n)*n
    with np.errstate(all="ignore"):
        return 100.0 - 100.0/(1.0 + s1/s2)

def nz(x, v=0.0): return np.where(np.isnan(x), v, x)

def sh(x, k=1):
    x = np.asarray(x, dtype=float)
    if k == 0: return x.copy()
    return np.r_[np.full(k, np.nan), x[:-k]]

@njit(cache=True)
def barssince(cond):
    o = np.full(len(cond), 1e9); k = 1e9
    for i in range(len(cond)):
        k = 0.0 if cond[i] else k + 1.0
        o[i] = k
    return o

def rising(x, n):
    r = np.ones(len(x), bool)
    for j in range(n): r &= sh(x, j) > sh(x, j+1)
    return r

def falling(x, n):
    r = np.ones(len(x), bool)
    for j in range(n): r &= sh(x, j) < sh(x, j+1)
    return r

def rsum(x, n):
    return sma(x, n)*n

def flipsig(long_cond, short_cond):
    s = np.zeros(len(long_cond)); s[np.asarray(short_cond, bool)] = -1; s[np.asarray(long_cond, bool)] = 1
    return s

def olay(cond_on, cond_off=None):
    """Olay dizisinden durum (state): on'da 1, off'ta 0 olacak şekilde tutar."""
    return None

def dmi(h, l, c, n, smooth):
    up = np.r_[0.0, np.diff(h)]; dn = -np.r_[0.0, np.diff(l)]
    pd_ = np.where((up > dn) & (up > 0), up, 0.0); md = np.where((dn > up) & (dn > 0), dn, 0.0)
    t = rma(tr(h, l, c), n)
    with np.errstate(all="ignore"):
        dip = 100*rma(pd_, n)/t; dim = 100*rma(md, n)/t
        dx = 100*np.abs(dip-dim)/(dip+dim)
    return dip, dim, rma(np.nan_to_num(dx, nan=0.0), smooth)

@njit(cache=True)
def supertrend_v(h, l, c, a, mult, src):
    """Seri çarpanlı ta.supertrend."""
    n = len(c); st = np.full(n, np.nan); d = np.ones(n)
    lo = np.full(n, np.nan); up = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(a[i]) or np.isnan(mult[i]): continue
        lb = src[i]-mult[i]*a[i]; ub = src[i]+mult[i]*a[i]
        if i > 0 and not np.isnan(lo[i-1]):
            pl = lo[i-1]; pu = up[i-1]
            lb = lb if (lb > pl or c[i-1] < pl) else pl
            ub = ub if (ub < pu or c[i-1] > pu) else pu
            if st[i-1] == pu: d[i] = -1.0 if c[i] > ub else 1.0
            else: d[i] = 1.0 if c[i] < lb else -1.0
        lo[i] = lb; up[i] = ub
        st[i] = lb if d[i] == -1.0 else ub
    return st, d

def percentrank(x, n):
    o = np.full(len(x), np.nan)
    for i in range(n, len(x)):
        w = x[i-n:i]
        o[i] = 100.0*np.sum(w <= x[i])/n
    return o

def htf(df, kural, fonk):
    """Üst zaman dilimi serisi: df'i `kural` (ör. '4h') ile yeniden örnekle, fonk(df4) -> dizi, son TAMAMLANMIŞ mumun değerini alt zaman dilimine yay (lookahead yok)."""
    import pandas as pd
    d = df.resample(kural).agg(dict(o="first", h="max", l="min", c="last", v="sum")).dropna()
    r = pd.Series(np.asarray(fonk(d), dtype=float), index=d.index).shift(1)
    return r.reindex(df.index, method="ffill").values


@njit(cache=True)
def durum(buy, xl):
    """Pine'da `not inPos` koşullu giriş: pozisyondayken (bar BAŞINDA) yeni sinyal yok sayılır; xl çıkışı aynı barda pozisyonu kapatır."""
    n = len(buy); sig = np.zeros(n); pos = False
    for i in range(n):
        was = pos
        if pos and xl[i]: pos = False
        if (not was) and buy[i]: sig[i] = 1.0; pos = True
    return sig
