"""RSI-Gauss-Velocity (T5kd1bJ2): 4 kutuplu Gauss filtresi (per=144) yeşilse (yükseliyor), kapanış üst band (filtre + 1.414×filtrelenmiş TR) üstünde ve Stoch(RSI) K>D ise long; çıkış: kapanış üst bandın altına keser ya da eğim tükenmesi (kârdayken). Yalnız long."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "RSI-Gauss-Velocity"; PINE_ID = "T5kd1bJ2"
PARAM = dict(rsi=14, stoch=14, kutup=4, per=144, carpan=1.414, egim=20)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]; YON = 1
NEDEN = "Yazar 2014'ten başlıyor, sembol belirtmemiş (BTC/ETH hedefi); günlük, tüm pazarlar."
@njit(cache=True)
def _gf(s, a, N):
    n = len(s); f = np.zeros(n); x = 1.0 - a
    m2 = 6.0 if N == 4 else (3.0 if N == 3 else (1.0 if N == 2 else 0.0)); m3 = 4.0 if N == 4 else (1.0 if N == 3 else 0.0); m4 = 1.0 if N == 4 else 0.0
    for i in range(n):
        v = a**N * (s[i] if not np.isnan(s[i]) else 0.0)
        v += N*x*(f[i-1] if i >= 1 else 0.0)
        if N >= 2: v -= m2*x**2*(f[i-2] if i >= 2 else 0.0)
        if N >= 3: v += m3*x**3*(f[i-3] if i >= 3 else 0.0)
        if N >= 4: v -= m4*x**4*(f[i-4] if i >= 4 else 0.0)
        f[i] = v
    return f
@njit(cache=True)
def _dur(lc, o, c, hb, exh):
    n = len(c); sig = np.zeros(n); xl = np.zeros(n, np.bool_); pos = False; ep = 0.0
    for i in range(1, n):
        was = pos
        if pos:
            cross = c[i] < hb[i] and c[i-1] >= hb[i-1]
            ex = cross or (exh[i] and c[i] > ep and (c[i] < hb[i] or c[i] < hb[i-1]))
            if ex: xl[i] = True; pos = False
        if (not was) and lc[i] and i+1 < n: sig[i] = 1.0; pos = True; ep = o[i+1]
    return sig, xl
def sinyal(df, rsi, stoch, kutup, per, carpan, egim):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values
    r = gost.rsi(c, int(rsi)); k = gost.sma(gost.stoch(r, r, r, int(stoch)), 3); d = gost.sma(k, 3)
    N = int(kutup); beta = (1 - np.cos(2*np.pi/per))/(1.414**(2.0/N) - 1); alpha = -beta + np.sqrt(beta**2 + 2*beta)
    fn = _gf((h+l+c)/3, alpha, N); ft = _gf(gost.tr(h, l, c), alpha, N); hb = fn + ft*carpan
    sl = fn - gost.sh(fn); sm = gost.sma(sl, int(egim)); sd = gost.stdev(sl, int(egim)); exh = sl < (sm - sd)
    with np.errstate(invalid="ignore"):
        lc = (fn > gost.sh(fn)) & (c > hb) & (k > d)
    sig, xl = _dur(np.nan_to_num(lc.astype(float)) > 0, o, c, hb, np.nan_to_num(exh.astype(float)) > 0)
    return dict(sig=sig, xl=xl)
