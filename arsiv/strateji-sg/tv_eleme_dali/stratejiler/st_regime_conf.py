"""SuperTrend Regime Confluence (mpjNqADq): rejime göre (volatil/yatay/trend) uyarlanan çarpanlı SuperTrend(10, 3, hl2); yön dönüşünde 5 bileşenli skor (hacim, bant uzaklığı, EMA50 uyumu, rejim, önceki mesafe) ≥65 + EMA50 trend süzgeci + yatay rejim değil + hacim>SMA20 ise giriş (5 mum bekleme); stop 6 ATR, hedef 2.5R."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "SuperTrend Regime Confluence"; PINE_ID = "mpjNqADq"
PARAM = dict(atr=10, carpan=3.0, reg=40, adx=14, adx_esik=20.0, trend=50, vol=20, min_skor=65, sl=6.0, rr=2.5, bekle=5)
TF = "4h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik."
@njit(cache=True)
def _st(c, src, atr, ratio, adx, adx_esik, mult, adapt):
    n = len(c); band = np.full(n, np.nan); dr = np.ones(n); rg = np.ones(n)
    d = 1; b = np.nan
    for i in range(n):
        if np.isnan(atr[i]): continue
        r = 1
        if ratio[i] > 1.4: r = 2
        elif adx[i] < adx_esik and ratio[i] < 0.9: r = 0
        rg[i] = r
        m = mult
        if adapt:
            if r == 2: m = mult*(1.0+(ratio[i]-1.0)*0.4)
            elif r == 0: m = mult*0.85
        m = max(min(m, mult*2.0), mult*0.5)
        ub = src[i]+m*atr[i]; lb = src[i]-m*atr[i]
        pb = b if not np.isnan(b) else (lb if d == 1 else ub)
        if d == 1:
            b = max(lb, pb)
            if c[i] < b: d = -1; b = ub
        else:
            b = min(ub, pb)
            if c[i] > b: d = 1; b = lb
        band[i] = b; dr[i] = d
    return band, dr, rg
def sinyal(df, atr, carpan, reg, adx, adx_esik, trend, vol, min_skor, sl, rr, bekle):
    o, h, l, c, v = df.o.values, df.h.values, df.l.values, df.c.values, df.v.values; n = len(c); src = (h+l)/2
    a = gost.atr(h, l, c, int(atr)); am = gost.sma(a, int(reg)); _, _, ad = gost.dmi(h, l, c, int(adx), int(adx))
    with np.errstate(all="ignore"): ratio = np.where(am > 0, a/am, 1.0)
    band, dr, rg = _st(c, src, a, np.nan_to_num(ratio, nan=1.0), np.nan_to_num(ad, nan=50.0), adx_esik, carpan, True)
    t = gost.ema(c, int(trend)); vm = gost.sma(v, int(vol)); sa = np.where(np.isnan(a) | (a <= 0), 0.001, a)
    sig = np.zeros(n); sld = np.full(n, np.nan); last = -10**9
    for i in range(2, n):
        if dr[i] == dr[i-1] or np.isnan(band[i]) or np.isnan(t[i]) or np.isnan(vm[i]) or i-last <= bekle: continue
        bull = dr[i] == 1; vr = v[i]/vm[i] if vm[i] > 0 else 1.0
        s = 20 if vr >= 2.5 else 14 if vr >= 1.5 else 8 if vr >= 1.0 else 3
        disp = (c[i]-band[i]) if bull else (band[i]-c[i]); da = disp/sa[i]
        s += 25 if da >= 1.5 else 18 if da >= 0.8 else 12 if da >= 0.3 else 5 if da > 0 else 0
        al = (bull and c[i] > t[i]) or ((not bull) and c[i] < t[i]); ed = abs(c[i]-t[i])/sa[i]
        s += 20 if (al and ed > 0.5) else 14 if al else 8 if ed < 0.3 else 2
        s += 15 if rg[i] == 1 else 8 if rg[i] == 2 else 3
        pd = abs(c[i-1]-band[i-1])/sa[i] if not np.isnan(band[i-1]) else 0.0
        s += 20 if pd >= 2.0 else 14 if pd >= 1.0 else 8 if pd >= 0.5 else 3
        s = min(round(s), 100)
        if s >= min_skor and al and rg[i] != 0 and v[i] > vm[i]:
            sig[i] = 1.0 if bull else -1.0; sld[i] = a[i]*sl; last = i
    return dict(sig=sig, sld=sld, tpd=sld*rr, xl=sig < 0, xs=sig > 0)
