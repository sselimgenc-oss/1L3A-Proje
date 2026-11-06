"""RF-HA Trend Scalper (U0wTnRuE): Range Filter yönü + yumuşatılmış Heikin-Ashi yönü + (1s HTF HA yönü, `d[1]` = son kapanmış HTF mumu — lookahead YOK) aynı yöndeyse yeni durumda giriş (SMI anti-kovalama filtreli); 2.5 ATR izleyen stop, Range Filter tersine dönünce çık. (5 mumluk bekleme süresi modellenmedi.)"""
import numpy as np
from numba import njit
from tv import gost
ISIM = "RF-HA Trend Scalper"; PINE_ID = "U0wTnRuE"
PARAM = dict(rf_per=50, rf_c=2.0, pre=6, post=8, smi=8, s1=3, s2=3, smi_max=60.0, atr=14, iz=2.5)
TF = "15m"; EVREN = ["kripto"]
NEDEN = "Betikte 'scalper', HTF=60 dk → 15 dk grafik; kripto."
@njit(cache=True)
def _rf(c, smr):
    n = len(c); f = np.full(n, np.nan); d = np.zeros(n); dr = 0
    for i in range(n):
        pf = f[i-1] if i > 0 and not np.isnan(f[i-1]) else c[i]
        if np.isnan(smr[i]): f[i] = c[i]
        elif c[i] > pf: f[i] = max(pf, c[i]-smr[i])
        else: f[i] = min(pf, c[i]+smr[i])
        if f[i] > pf: dr = 1
        elif f[i] < pf: dr = -1
        d[i] = dr
    return d
def _ha(o, h, l, c, a, b):
    o1, h1, l1, c1 = gost.ema(o, a), gost.ema(h, a), gost.ema(l, a), gost.ema(c, a); hc = (o1+h1+l1+c1)/4; ho = np.full(len(c), np.nan)
    for i in range(len(c)):
        if np.isnan(hc[i]): continue
        ho[i] = (o1[i]+c1[i])/2 if i == 0 or np.isnan(ho[i-1]) else (ho[i-1]+hc[i-1])/2
    return gost.ema(ho, b), gost.ema(hc, b)
def sinyal(df, rf_per, rf_c, pre, post, smi, s1, s2, smi_max, atr, iz):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values; n = len(c)
    ar = gost.ema(np.r_[np.nan, np.abs(np.diff(c))], int(rf_per)); smr = gost.ema(ar, int(rf_per)*2-1)*rf_c; rd = _rf(c, smr)
    ho2, hc2 = _ha(o, h, l, c, int(pre), int(post)); hd = np.where(hc2 >= ho2, 1, -1)
    def dirf(d):
        a, b = _ha(d.o.values, d.h.values, d.l.values, d.c.values, int(pre), int(post)); return gost.sh(np.where(b >= a, 1.0, -1.0), 1)
    hd_htf = np.nan_to_num(gost.htf(df, "1h", dirf))
    hh, ll = gost.highest(h, int(smi)), gost.lowest(l, int(smi)); rdf = c-(hh+ll)/2; ardel = gost.ema(gost.ema(rdf, int(s1)), int(s2)); adf = gost.ema(gost.ema(hh-ll, int(s1)), int(s2))
    with np.errstate(all="ignore"): sm = np.where(adf != 0, ardel/(adf/2)*100, 0.0)
    st = np.where((rd == 1) & (hd == 1) & (hd_htf == 1), 1, np.where((rd == -1) & (hd == -1) & (hd_htf == -1), -1, 0)); ps = np.r_[0, st[:-1]]
    a = gost.atr(h, l, c, int(atr)); warm = (np.arange(n) > rf_per*4) & ~np.isnan(a) & ~np.isnan(smr)
    with np.errstate(invalid="ignore"):
        lg = warm & (st == 1) & (ps != 1) & (sm < smi_max); sh = warm & (st == -1) & (ps != -1) & (sm > -smi_max)
    return dict(sig=gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0), dyl=c-a*iz, dys=c+a*iz, xl=rd == -1, xs=rd == 1)
