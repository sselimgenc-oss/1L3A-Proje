"""Skyrexio 'MultiLayer' ailesi (HyzpDR9t, ErcSuPyN, Tkrjao7P) ortak çekirdeği: Bill Williams fraktal kırılımıyla trend (trend=1: yukarı fraktal aşıldı); trend içinde aynı sinyal tekrar ettikçe en çok 5 kademeli (entry1..5) EKLEME; trend dönüşünde (ya da Tkrjao7P'de stop seviyesi kırılınca) hepsi kapanır. Her kademe ayrı bacak olarak koşulur."""
import numpy as np
from numba import njit
from tv import gost
@njit(cache=True)
def _trend(h, l, ph, pl, teeth):
    n = len(h); tr = np.zeros(n); upL = np.nan; dnL = np.nan; upA = np.nan; dnA = np.nan; t = 0
    for i in range(n):
        hc = (not np.isnan(upA)) and i > 0 and h[i] > upA and h[i-1] <= upA   # crossover(high, upAct) önceki bar sonu değeriyle
        lc = (not np.isnan(dnA)) and i > 0 and l[i] < dnA and l[i-1] >= dnA
        if not np.isnan(ph[i]): upL = ph[i]
        if not np.isnan(pl[i]): dnL = pl[i]
        if (not np.isnan(upL)) and (not np.isnan(teeth[i])) and upL > teeth[i]: upA = upL
        if hc: t = 1; upA = np.nan; dnA = dnL
        if (not np.isnan(dnL)) and (not np.isnan(teeth[i])) and dnL < teeth[i]: dnA = dnL
        if lc: t = -1; dnA = np.nan; upA = upL
        if t == 1: upA = np.nan
        if t == -1: dnA = np.nan
        tr[i] = t
    return tr
@njit(cache=True)
def _kademe_stop(sig_raw, act_raw, diffneg, tr, K):
    # sig_raw: saucer/AC sinyali (kenar), act_raw[i]: aktivasyon seviyesi (nan olabilir) ; çıktılar kademe başına sig/sep
    n = len(tr); sg = np.zeros((K, n)); sp = np.full((K, n), np.nan); qty = 0
    for i in range(n):
        if i > 0 and tr[i] == -1 and tr[i-1] == 1: qty = 0
        if sig_raw[i] and not (i > 0 and sig_raw[i-1]): qty += 1
        if i > 0 and (not np.isnan(act_raw[i-1])) and diffneg[i] and np.isnan(act_raw[i]): qty -= 1
        if qty >= 1 and qty <= K and not np.isnan(act_raw[i]):
            sg[qty-1, i] = 1.0; sp[qty-1, i] = act_raw[i]
    return sg, sp
@njit(cache=True)
def _aktivasyon(sinyal0, h, diff, ao_ok):
    n = len(h); act = np.full(n, np.nan); sig = sinyal0.copy()
    for i in range(n):
        prev = act[i-1] if i > 0 else np.nan
        a = h[i] if sig[i] else prev
        if (not np.isnan(prev)) and h[i] < prev and diff[i] > 0: a = h[i]; sig[i] = True
        if ((not np.isnan(prev)) and h[i] > prev and not np.isnan(a)) or diff[i] < 0: a = np.nan
        act[i] = a
    return sig, act
def tabanlar(df, ema=100):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values; hl2 = (h+l)/2
    teeth = gost.sh(gost.rma(hl2, 8), 5)
    sm = gost.sma(hl2, 8); 
    ph = np.full(len(h), np.nan); pl = np.full(len(h), np.nan)
    from tv.stratejiler.fractal_sky import _pivots
    ph = _pivots(h, 2, 2, True); pl = _pivots(l, 2, 2, False)
    tr = _trend(h, l, ph, pl, teeth)
    ao = gost.sma(hl2, 5) - gost.sma(hl2, 34)
    return dict(o=o, h=h, l=l, c=c, hl2=hl2, teeth=teeth, tr=tr, ao=ao, ema=gost.ema(c, int(ema)))
def bacaklar_stop(df, sinyal_fn, ema=100, K=5):
    b = tabanlar(df, ema); ao = b["ao"]; ac = ao - gost.sma(ao, 5)
    sinyal0, diff = sinyal_fn(b, ac)
    sig, act = _aktivasyon(sinyal0, b["h"], diff, True)
    sg, sp = _kademe_stop(sig, act, np.nan_to_num(diff) < 0, b["tr"], K)
    xl = np.r_[False, (b["tr"][1:] == -1) & (b["tr"][:-1] == 1)]
    return [dict(sig=sg[k], sep=sp[k], xl=xl) for k in range(K)]
