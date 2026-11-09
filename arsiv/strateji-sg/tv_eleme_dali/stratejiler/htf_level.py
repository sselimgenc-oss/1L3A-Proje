"""HTF Level Breakout (PdJvHIfQ): önceki günün (HTF `high[1]/low[1]`, lookahead_on ama ofsetli → geçerli) tepe/dibi seviye olur; fiyat seviyeye dokununca o mumun ucu 'S1' sayılır, sonraki bir mum seviyenin ve S1'in ötesinde kapanırsa kırılım yönünde giriş; stop son 5/5 pivot dibi/tepesi, hedef 2R. Günde bir seviye kümesi."""
import numpy as np
from tv import gost
from tv.stratejiler.fractal_sky import _pivots
ISIM = "HTF Level Breakout"; PINE_ID = "PdJvHIfQ"
PARAM = dict(piv=5, rr=2.0)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "HTF=günlük, betik gün içi grafikte çalışır; saatlik."
def sinyal(df, piv, rr):
    h, l, c = df.h.values, df.l.values, df.c.values; n = len(c); P = int(piv)
    ph = _pivots(h, P, P, True); pl = _pivots(l, P, P, False); gun = df.index.normalize().values
    dh = df.groupby(df.index.normalize()).h.max(); dl = df.groupby(df.index.normalize()).l.min()
    ph_prev = dict(zip(dh.index.values[1:], dh.values[:-1])); pl_prev = dict(zip(dl.index.values[1:], dl.values[:-1]))
    sig = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan)
    lh = ll = np.nan; lvh = lvl = np.nan; ha = la = False; s1h = s1l = np.nan; sh_set = sl_set = False; pg = None
    for i in range(n):
        if not np.isnan(ph[i]): lh = ph[i]
        if not np.isnan(pl[i]): ll = pl[i]
        if gun[i] != pg:
            pg = gun[i]
            if pg in ph_prev: lvh, lvl = ph_prev[pg], pl_prev[pg]; ha = la = True; sh_set = sl_set = False; s1h = s1l = np.nan
        if ha and not np.isnan(lvh):
            if h[i] >= lvh and not sh_set: s1h = h[i]; sh_set = True; la = False
            if sh_set and c[i] > lvh and c[i] > s1h and not np.isnan(ll):
                sig[i] = 1.0; sl[i] = ll; tp[i] = c[i] + (c[i]-ll)*rr; ha = False
        if la and not np.isnan(lvl):
            if l[i] <= lvl and not sl_set: s1l = l[i]; sl_set = True; ha = False
            if sl_set and c[i] < lvl and c[i] < s1l and not np.isnan(lh):
                sig[i] = -1.0; sl[i] = lh; tp[i] = c[i] - (lh-c[i])*rr; la = False
    return dict(sig=sig, sl=sl, tp=tp)
