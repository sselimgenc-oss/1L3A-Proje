"""Simple Harmonic Pattern (edChhkxo): 4 mumluk onaylı pivotlardan zigzag (aynı yönlü pivotta daha uç olan korunur); son 5 pivot X-A-B-C-D oranları Gartley/Bat/Butterfly/Crab'e 4 orandan en az 3'ü (±0.10) uyarsa, D pivotu onaylandığında (4 mum gecikmeli) desen yönünde giriş; stop X ∓ 0.25 ATR, hedef 2R (D'den). 5 mum bekleme. Pivotlar sonradan değişmez (repaint yok)."""
import numpy as np
from tv import gost
from tv.stratejiler.fractal_sky import _pivots
ISIM = "Simple Harmonic Pattern"; PINE_ID = "edChhkxo"
PARAM = dict(zig=4, tol=0.10, min_oran=3, atr=14, stop=0.25, rr=2.0, bekle=5)
TF = "4h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik."
def _in(v, lo, hi): return int(lo <= v <= hi)
def _skor(ab, bc, cd, xd, t):
    g = _in(ab, .618-t, .618+t) + _in(bc, .382-t, .886+t) + _in(cd, 1.13-t, 1.618+t) + _in(xd, .786-t, .786+t)
    b = _in(ab, .382-t, .5+t) + _in(bc, .382-t, .886+t) + _in(cd, 1.618-t, 2.618+t) + _in(xd, .886-t, .886+t)
    f = _in(ab, .786-t, .786+t) + _in(bc, .382-t, .886+t) + _in(cd, 1.618-t, 2.618+t) + _in(xd, 1.27-t, 1.618+t)
    c = _in(ab, .382-t, .618+t) + _in(bc, .382-t, .886+t) + _in(cd, 2.24-t, 3.618+t) + _in(xd, 1.618-t, 1.618+t)
    return max(g, b, f, c)
def sinyal(df, zig, tol, min_oran, atr, stop, rr, bekle):
    h, l, c = df.h.values, df.l.values, df.c.values; n = len(c); a = gost.atr(h, l, c, int(atr)); Z = int(zig)
    ph = _pivots(h, Z, Z, True); pl = _pivots(l, Z, Z, False)
    sig = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan); P = []; son = -10**9
    for i in range(n):
        yeni = False
        for v, d in ((ph[i], 1), (pl[i], -1)):
            if np.isnan(v): continue
            yeni = True
            if not P: P.append([v, d])
            elif P[-1][1] == d:
                if (d == 1 and v > P[-1][0]) or (d == -1 and v < P[-1][0]): P[-1][0] = v
            else: P.append([v, d])
            if len(P) > 20: P.pop(0)
        if not yeni or len(P) < 5: continue
        X, A, B, C, D = P[-5][0], P[-4][0], P[-3][0], P[-2][0], P[-1][0]; dd = P[-1][1]
        XA, AB, BC, CD, XD = abs(A-X), abs(B-A), abs(C-B), abs(D-C), abs(D-X)
        if not (XA > 0 and AB > 0 and BC > 0): continue
        if _skor(AB/XA, BC/AB, CD/BC, XD/XA, tol) < min_oran or i-son < bekle or np.isnan(a[i]): continue
        bull = dd == -1; s = X - stop*a[i] if bull else X + stop*a[i]; risk = abs(D-s)
        sig[i] = 1.0 if bull else -1.0; sl[i] = s; tp[i] = D + rr*risk if bull else D - rr*risk; son = i
    return dict(sig=sig, sl=sl, tp=tp)
