"""Tomukas Elite SMC (83hmaEOQ): EMA200 trendi + ADX>20 + seans (08:00–17:00 UTC−4); 5/5 swing dibini süpürüp güçlü kapanış (likidite süpürme), karşı swing tepesinin kapanışla kırılması (MSS) ve oluşan FVG'ye geri çekilme → trend yönünde giriş; stop süpürme ucu, TP1 1R (%50), ardından kalan yarım başa-baş stop + ters süpürme/EMA200 kırılımında çıkış. İki bacak (%50/%50)."""
import numpy as np
from tv import gost
from tv.stratejiler.fractal_sky import _pivots
ISIM = "Tomukas Elite SMC"; PINE_ID = "83hmaEOQ"
PARAM = dict(ema=200, adx=14, adx_esik=20.0, sw=5, fvg_min=0.1, rr=1.0)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Seans süzgeçli gün içi (5 dk olabilir); saatlik uyarlama."
def sinyal(df, ema, adx, adx_esik, sw, fvg_min, rr):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values; n = len(c); e = gost.ema(c, int(ema)); _, _, ad = gost.dmi(h, l, c, int(adx), int(adx))
    ph = _pivots(h, int(sw), int(sw), True); pl = _pivots(l, int(sw), int(sw), False); hr = df.index.hour.values; sess = (hr >= 12) & (hr < 21)
    lph = lpl = np.nan; st = 0; ext = np.nan; mss = False; ft = fb = np.nan
    sig = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan); sta = np.zeros(n)
    for i in range(2, n):
        if not np.isnan(ph[i]): lph = ph[i]
        if not np.isnan(pl[i]): lpl = pl[i]
        bull_rej = (c[i] > (h[i]+l[i])/2) and ((c[i]-l[i]) > (h[i]-c[i])*1.5); bear_rej = (c[i] < (h[i]+l[i])/2) and ((h[i]-c[i]) > (c[i]-l[i])*1.5)
        swl = (not np.isnan(lpl)) and l[i] < lpl and c[i] > lpl and bull_rej; swh = (not np.isnan(lph)) and h[i] > lph and c[i] < lph and bear_rej
        if swl: st = 1; ext = l[i]
        if swh: st = -1; ext = h[i]
        if swl or swh: mss = False; ft = fb = np.nan
        if st == 1 and not mss and not np.isnan(lph) and c[i] > lph and lph > ext:
            mss = True
            if l[i] > h[i-2] and (l[i]-h[i-2])/h[i-2]*100 >= fvg_min: ft, fb = l[i], h[i-2]
        if st == -1 and not mss and not np.isnan(lpl) and c[i] < lpl and lpl < ext:
            mss = True
            if h[i] < l[i-2] and (l[i-2]-h[i])/h[i] * 100 >= fvg_min: ft, fb = l[i-2], h[i]
        ok = mss and not np.isnan(ft) and ad[i] > adx_esik and sess[i]
        tr = 1 if c[i] > e[i] else (-1 if c[i] < e[i] else 0)
        if ok and st == 1 and tr == 1 and l[i] <= ft and l[i] >= fb: sig[i] = 1.0; sl[i] = ext; tp[i] = c[i] + (c[i]-ext)*rr; ft = np.nan
        elif ok and st == -1 and tr == -1 and h[i] >= fb and h[i] <= ft: sig[i] = -1.0; sl[i] = ext; tp[i] = c[i] - (ext-c[i])*rr; ft = np.nan
        if not np.isnan(ft):
            if st == 1 and c[i] < fb: ft = fb = np.nan
            if st == -1 and c[i] > ft: ft = fb = np.nan
        sta[i] = st
    xln = (sta == -1) | (c < e); xsn = (sta == 1) | (c > e)
    return dict(bacaklar=[
        dict(sig=sig, sl=sl, tp=tp, olcek=0.5),
        dict(sig=sig, sl=sl, taa=np.where(sig != 0, np.abs(tp-c), np.nan), toa=np.where(sig != 0, 1e12, np.nan), tbe=1, xl=xln, xs=xsn, olcek=0.5)])
