"""Smart Trend Strategy julzALGO (Sg2qyDDe): KAMA→Kalman filtreli trend yönü (yükselen/düşen), 10/10 pivot yapı kırılımları (BOS: trend yönünde, CHoCH: ters yöne kırılım; kapanışla); trend dönüşü ya da BOS/CHoCH, ters yönde 10 mum içinde BOS/CHoCH ile birlikteyse giriş (kapanışta); stop 3 ATR, hedef long 2R / short 1R; ters sinyalde kapat. process_orders_on_close."""
import numpy as np
from numba import njit
from tv import gost
from tv.stratejiler.fractal_sky import _pivots
ISIM = "Smart Trend (KAMA+Kalman+BOS/CHoCH)"; PINE_ID = "Sg2qyDDe"
PARAM = dict(er=20, hizli=5, yavas=30, q=0.0001, r=0.01, piv=10, sync=10, atr=14, atr_c=3.0, rr_l=2.0, rr_s=1.0)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş (7 günlük pencere = gün içi/saatlik); saatlik."
@njit(cache=True)
def _core(c, ph, pl, a, er_len, fs, ss, q, r, sync, atr_c, rr_l, rr_s):
    n = len(c); sig = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan)
    kama = np.nan; kal = np.nan; p = 1.0; trend = 0; ptr = 0; lh = np.nan; ll = np.nan; ht = False; lt = False; st = 0
    lbf = lbs = -10**9; lbb = lbc = -10**9; sbf = sbs = -10**9; sbb = sbc = -10**9
    for i in range(n):
        if i >= er_len:
            ch = abs(c[i]-c[i-er_len]); vol = 0.0
            for j in range(er_len): vol += abs(c[i-j]-c[i-j-1]) if i-j-1 >= 0 else 0.0
            er = ch/vol if vol != 0 else 0.0
        else: er = 0.0
        sc = (er*(fs-ss)+ss)**2
        kama = c[i] if np.isnan(kama) else kama + sc*(c[i]-kama)
        p += q; k = p/(p+r)
        pk = kal
        kal = kama if np.isnan(kal) else kal + k*(kama-kal); p = (1-k)*p
        pt = trend
        if not np.isnan(pk): trend = 1 if kal > pk else (-1 if kal < pk else trend)
        bf = trend == 1 and pt != 1; sf = trend == -1 and pt != -1
        if not np.isnan(ph[i]): lh = ph[i]; ht = False
        if not np.isnan(pl[i]): ll = pl[i]; lt = False
        bb = (not np.isnan(lh)) and (not ht) and c[i] > lh and i > 0 and c[i-1] <= lh
        sb = (not np.isnan(ll)) and (not lt) and c[i] < ll and i > 0 and c[i-1] >= ll
        bc = bb and st == -1; sc_ = sb and st == 1; bbos = bb and not bc; sbos = sb and not sc_
        if bb: ht = True; st = 1
        if sb: lt = True; st = -1
        if bf: lbf = i
        if sf: sbf = i
        if bbos: lbb = i
        if sbos: sbb = i
        if bc: lbc = i
        if sc_: sbc = i
        rbb = abs(lbf-lbb) <= sync; rsb = abs(sbf-sbb) <= sync; rbc = abs(lbf-lbc) <= sync; rsc = abs(sbf-sbc) <= sync
        lok = rbb or rbc; sok = rsb or rsc
        if np.isnan(a[i]): continue
        if trend == 1 and lok and (bf or bbos or bc):
            risk = a[i]*atr_c
            sig[i] = 1.0; sl[i] = c[i]-risk; tp[i] = c[i]+risk*rr_l
        elif trend == -1 and sok and (sf or sbos or sc_):
            risk = a[i]*atr_c
            sig[i] = -1.0; sl[i] = c[i]+risk; tp[i] = c[i]-risk*rr_s
    return sig, sl, tp
def sinyal(df, er, hizli, yavas, q, r, piv, sync, atr, atr_c, rr_l, rr_s):
    h, l, c = df.h.values, df.l.values, df.c.values; P = int(piv); a = gost.atr(h, l, c, int(atr))
    sg, sl, tp = _core(c, _pivots(h, P, P, True), _pivots(l, P, P, False), a, int(er), 2.0/(hizli+1), 2.0/(yavas+1), q, r, int(sync), atr_c, rr_l, rr_s)
    return dict(sig=sg, sl=sl, tp=tp, xl=sg < 0, xs=sg > 0, poc=True)
