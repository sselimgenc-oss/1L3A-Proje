"""Liquidity Sweep Reversal (GoeqO1ev): 7/7 onaylı swing tepe/dipleri 'likidite seviyesi' olur (≥0.25 ATR aralıklı, 150 mum ömürlü); mum seviyeyi iğneyle aşıp içeride kapanırsa (hacim>1.3×SMA20, iğne/gövde≥1.5) süpürme sayılır; ertesi mum onay (orta noktanın ötesinde kapanış) → ters yönde giriş; stop iğne∓1.2 ATR, hedef 1.5R, %50'de başa-baş. Seans 12:00–16:00 UTC. Pivot onayı 7 mum gecikmeli (repaint yok)."""
import numpy as np
from numba import njit
from tv import gost
from tv.stratejiler.fractal_sky import _pivots
ISIM = "Liquidity Sweep Reversal"; PINE_ID = "GoeqO1ev"
PARAM = dict(piv=7, yas=150, bosluk=0.25, sl=1.2, min_risk=0.5, rr=1.5, be=0.5, hacim=1.3, fitil=1.5)
TF = "1h"; EVREN = ["kripto", "emtia"]
NEDEN = "Seans penceresi 12:00–16:00 → saatlik; borsa saati UTC alındı (kripto/emtia)."
@njit(cache=True)
def _sim(o, h, l, c, v, vs, atr, ph, pl, sess, piv, yas, bosluk, sl_m, min_risk, rr, hacim, fitil):
    n = len(c); sig = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan)
    hp = np.zeros(512); hb = np.zeros(512, np.int64); hn = 0; lp = np.zeros(512); lb = np.zeros(512, np.int64); ln = 0
    pend = 0; pwick = 0.0; pmid = 0.0
    for i in range(n):
        a = atr[i]
        if np.isnan(a): continue
        if not np.isnan(ph[i]):
            ok = True
            for k in range(hn):
                if abs(hp[k]-ph[i]) < a*bosluk: ok = False
            if ok and hn < 512: hp[hn] = ph[i]; hb[hn] = i-piv; hn += 1
        if not np.isnan(pl[i]):
            ok = True
            for k in range(ln):
                if abs(lp[k]-pl[i]) < a*bosluk: ok = False
            if ok and ln < 512: lp[ln] = pl[i]; lb[ln] = i-piv; ln += 1
        body = abs(c[i]-o[i]); vok = v[i] > vs[i]*hacim
        sh = False; shw = np.nan; k = 0
        while k < hn:
            wick = h[i]-max(c[i], o[i]); wok = (body > 0 and wick/body >= fitil) or (body == 0 and wick > 0)
            if h[i] > hp[k] and c[i] < hp[k] and vok and wok:
                sh = True; shw = h[i] if np.isnan(shw) else max(shw, h[i]); hp[k] = hp[hn-1]; hb[k] = hb[hn-1]; hn -= 1
            elif i-hb[k] > yas: hp[k] = hp[hn-1]; hb[k] = hb[hn-1]; hn -= 1
            else: k += 1
        sl_ = False; slw = np.nan; k = 0
        while k < ln:
            wick = min(c[i], o[i])-l[i]; wok = (body > 0 and wick/body >= fitil) or (body == 0 and wick > 0)
            if l[i] < lp[k] and c[i] > lp[k] and vok and wok:
                sl_ = True; slw = l[i] if np.isnan(slw) else min(slw, l[i]); lp[k] = lp[ln-1]; lb[k] = lb[ln-1]; ln -= 1
            elif i-lb[k] > yas: lp[k] = lp[ln-1]; lb[k] = lb[ln-1]; ln -= 1
            else: k += 1
        dl = 0; ds = 0; wl = 0.0
        if pend == 1 and c[i] > pmid and sess[i]: dl = 1; wl = pwick
        elif pend == -1 and c[i] < pmid and sess[i]: ds = 1; wl = pwick
        pend = 0
        if sl_: pend = 1; pwick = slw; pmid = (slw+c[i])/2
        if sh: pend = -1; pwick = shw; pmid = (shw+c[i])/2
        if dl == 1:
            s = wl - a*sl_m; risk = c[i]-s
            if risk >= a*min_risk: sig[i] = 1.0; sl[i] = s; tp[i] = c[i]+risk*rr
        elif ds == 1:
            s = wl + a*sl_m; risk = s-c[i]
            if risk >= a*min_risk: sig[i] = -1.0; sl[i] = s; tp[i] = c[i]-risk*rr
    return sig, sl, tp
def sinyal(df, piv, yas, bosluk, sl, min_risk, rr, be, hacim, fitil):
    o, h, l, c, v = df.o.values, df.h.values, df.l.values, df.c.values, df.v.values; a = gost.atr(h, l, c, 14); hr = df.index.hour.values
    sg, s, t = _sim(o, h, l, c, v, gost.sma(v, 20), a, _pivots(h, int(piv), int(piv), True), _pivots(l, int(piv), int(piv), False), (hr >= 12) & (hr < 16), int(piv), int(yas), bosluk, sl, min_risk, rr, hacim, fitil)
    return dict(sig=sg, sl=s, tp=t, taa=np.where(sg != 0, np.abs(t-c)*be, np.nan), toa=np.where(sg != 0, 1e12, np.nan), tbe=1)
