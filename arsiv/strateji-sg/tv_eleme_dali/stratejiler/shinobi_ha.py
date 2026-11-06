"""Shinobi HA v3 (CtFpKECD): Heikin Ashi desenı — iki tam gövdeli (fitilsiz) HA mumu ardından, ondan büyük doji mum + SuperTrend(3.44) yönü + ADX≥22 + yapı filtresi (swing dipleri yükseliyor) + hacim ≥ EMA20 + 17:00–20:00 (Budapeşte) seansı; stop HA dibi/tepesi, hedef 1R. (Seans UTC 15–18 alınır.)"""
import numpy as np
from tv import gost
from tv.stratejiler.fractal_sky import _pivots
ISIM = "Shinobi HA v3"; PINE_ID = "CtFpKECD"
PARAM = dict(atr=15, st=3.44, adx=22.0, doji=0.20, fitil=0.03, dm=0.3, rr=1.0, swing=5)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Seans süzgeçli gün içi (Macar yazar); saatlik."
def sinyal(df, atr, st, adx, doji, fitil, dm, rr, swing):
    o, h, l, c, v = df.o.values, df.h.values, df.l.values, df.c.values, df.v.values; n = len(c)
    hc = (o+h+l+c)/4; ho = np.empty(n); ho[0] = (o[0]+c[0])/2
    for i in range(1, n): ho[i] = (ho[i-1]+hc[i-1])/2
    hh, hl = np.maximum(h, np.maximum(ho, hc)), np.minimum(l, np.minimum(ho, hc))
    s_, d = gost.supertrend(h, l, c, gost.atr(h, l, c, int(atr)), st, (h+l)/2); _, _, ad = gost.dmi(h, l, c, 14, 14)
    tot = hh-hl; body = np.abs(hc-ho); up = hh-np.maximum(hc, ho); lw = np.minimum(hc, ho)-hl
    with np.errstate(all="ignore"):
        nuw = np.where(tot > 0, up/tot <= fitil, True); nlw = np.where(tot > 0, lw/tot <= fitil, True)
        isd = (np.where(tot > 0, body/tot, 1.0) <= doji) & (up >= body*dm) & (lw >= body*dm)
    bull = hc >= ho; bear = hc < ho; S = lambda x, k: gost.sh(x.astype(float), k) > 0
    size = tot > gost.sh(tot)
    sell_setup = S(bull, 2) & S(nlw, 2) & S(bull, 1) & S(nlw, 1) & isd & size; buy_setup = S(bear, 2) & S(nuw, 2) & S(bear, 1) & S(nuw, 1) & isd & size
    ph = _pivots(hh, int(swing), int(swing), True); pl = _pivots(hl, int(swing), int(swing), False)
    sh_, sl_ = np.full(n, np.nan), np.full(n, np.nan); a1 = a2 = b1 = b2 = np.nan
    for i in range(n):
        if not np.isnan(ph[i]): a2, a1 = a1, ph[i]
        if not np.isnan(pl[i]): b2, b1 = b1, pl[i]
        sh_[i] = (np.isnan(b2) or b1 > b2); sl_[i] = (np.isnan(a2) or a1 < a2)
    hr = df.index.hour.values; sess = (hr >= 15) & (hr < 18); vok = v >= gost.ema(v, 20)
    with np.errstate(invalid="ignore"):
        lg = buy_setup & (d < 0) & (ad >= adx) & (sh_ > 0) & sess & vok; sh = sell_setup & (d > 0) & (ad >= adx) & (sl_ > 0) & sess & vok
    slv = np.where(lg, hl, np.where(sh, hh, np.nan))
    return dict(sig=gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0), sl=slv, tp=np.where(lg, c+(c-hl)*rr, np.where(sh, c-(hh-c)*rr, np.nan)), poc=True)
