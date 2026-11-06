"""Elliott Wave Impulse Strategy (rvBgD3aP): ZigZag (pivothigh/low 5 sol/1 sağ; sağ mum onaylı, repaint yok) son pivotlarından 5 dalgalı itki (reversal) ya da dalga-4 geri çekilişi (wave 5) tespit edilirse zigzag yön değiştirdiğinde giriş; stop son pivot ∓0.2 ATR, hedef (reversal: itkının %50'si; wave 5: dalga 1 boyu), R/R≥1, itki ≥1.5 ATR, 100 mum zaman stopu."""
import numpy as np
from tv import gost
from tv.stratejiler.fractal_sky import _pivots
ISIM = "Elliott Wave Impulse"; PINE_ID = "rvBgD3aP"
PARAM = dict(zz=5, tgt=0.5, w5=1.0, min4=0.236, max4=0.618, min_imp=1.5, buf=0.2, min_rr=1.0, tutma=100)
TF = "4h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik."
def _imp(p, d):
    p0, p1, p2, p3, p4, p5 = p
    if d == 1: w1, w3, w5 = p1-p0, p3-p2, p5-p4; return w3 != min(w1, w3, w5) and p5 > p3 and p2 > p0 and p4 > p1
    w1, w3, w5 = p0-p1, p2-p3, p4-p5; return w3 != min(w1, w3, w5) and p3 > p5 and p0 > p2 and p1 > p4
def sinyal(df, zz, tgt, w5, min4, max4, min_imp, buf, min_rr, tutma):
    h, l, c = df.h.values, df.l.values, df.c.values; n = len(c); a = gost.atr(h, l, c, 14)
    ph = _pivots(h, int(zz), 1, True); pl = _pivots(l, int(zz), 1, False)
    zy = []; zdir = 0; sig = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan)
    for i in range(n):
        fl = False
        if not np.isnan(ph[i]):
            if zdir < 1: zy.insert(0, ph[i]); zdir = 1; fl = True
            elif ph[i] > zy[0]: zy[0] = ph[i]
        if not np.isnan(pl[i]):
            if zdir > -1: zy.insert(0, pl[i]); zdir = -1; fl = True
            elif pl[i] < zy[0]: zy[0] = pl[i]
        if len(zy) > 8: zy.pop()
        if not fl or i < 50 or np.isnan(a[i]): continue
        sd = 0; stp = tg = imp = np.nan
        if len(zy) >= 7:
            d = 1 if zdir == -1 else -1; p = [zy[6], zy[5], zy[4], zy[3], zy[2], zy[1]]
            if _imp(p, d):
                diff = abs(p[5]-p[0]); sd = -1 if d == 1 else 1; stp = p[5] + buf*a[i] if d == 1 else p[5] - buf*a[i]; tg = p[5] + (-1 if d == 1 else 1)*diff*tgt; imp = diff
        if sd == 0 and len(zy) >= 5:
            d = 1 if zdir == -1 else -1; p4, p3, p2, p1, p0 = zy[0], zy[1], zy[2], zy[3], zy[4]
            if d == 1: w1, w3 = p1-p0, p3-p2; ret = (p3-p4)/w3 if w3 > 0 else np.nan; ok = w3 > w1 and w1 > 0 and p2 > p0 and p4 > p1 and not np.isnan(ret) and min4 <= ret <= max4
            else: w1, w3 = p0-p1, p2-p3; ret = (p4-p3)/w3 if w3 > 0 else np.nan; ok = w3 > w1 and w1 > 0 and p0 > p2 and p1 > p4 and not np.isnan(ret) and min4 <= ret <= max4
            if ok: sd = d; stp = p4 - buf*a[i] if d == 1 else p4 + buf*a[i]; tg = p4 + w1*w5 if d == 1 else p4 - w1*w5; imp = w3
        if sd == 0: continue
        risk = (stp-c[i]) if sd == -1 else (c[i]-stp); rew = (c[i]-tg) if sd == -1 else (tg-c[i])
        rr = rew/risk if risk > 0 and rew > 0 else 0.0
        if imp >= min_imp*a[i] and rr >= min_rr: sig[i] = float(sd); sl[i] = stp; tp[i] = tg
    return dict(sig=sig, sl=sl, tp=tp, maxhold=int(tutma))
