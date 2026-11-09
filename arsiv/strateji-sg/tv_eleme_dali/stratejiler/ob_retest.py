"""Volume Order Block Retest (ouvmvItR): gövde ≥0.8 ATR ve hacim ≥ SMA20 olan itki mumunun önceki mumu 'order block' bölgesi olur (en çok 15 bölge, 300 mum); fiyat bölgeyi ilk kez yeniden test edip yön mumu (yeşil/kırmızı) kapatırsa giriş; stop bölge ∓0.2 ATR, hedef 1.5R, 1R'de başa-baş, 60 mum zaman stopu. (Pozisyon doluyken bölge tüketimi 'flat' varsayımıyla modellendi.)"""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Volume Order Block Retest"; PINE_ID = "ouvmvItR"
PARAM = dict(atr=14, disp=0.8, vol=20, imp=1.0, maxz=15, yas=300, sl=0.2, rr=1.5, be=1.0, tutma=60)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; saatlik."
@njit(cache=True)
def _sim(o, h, l, c, v, a, vs, disp, imp, maxz, yas, sl_m, rr):
    n = len(c); sig = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan); rk = np.full(n, np.nan)
    zt = np.zeros(64); zb = np.zeros(64); zbull = np.zeros(64, np.bool_); zborn = np.zeros(64, np.int64); zused = np.zeros(64, np.bool_); zn = 0
    for i in range(2, n):
        if np.isnan(a[i-1]) or np.isnan(vs[i-1]) or np.isnan(a[i]): continue
        body = abs(c[i]-o[i]); big = body >= a[i-1]*disp and v[i] >= vs[i-1]*imp
        lsig = False; ssig = False; sb = 0.0; st = 0.0; k = zn-1
        while k >= 0:
            dead = (zbull[k] and c[i] < zb[k]) or ((not zbull[k]) and c[i] > zt[k]) or (i-zborn[k] > yas)
            if dead:
                for j in range(k, zn-1): zt[j] = zt[j+1]; zb[j] = zb[j+1]; zbull[j] = zbull[j+1]; zborn[j] = zborn[j+1]; zused[j] = zused[j+1]
                zn -= 1
            else:
                if h[i] >= zb[k] and l[i] <= zt[k] and not zused[k]:
                    if zbull[k] and c[i] > o[i] and c[i] > zb[k] and not lsig and not ssig: lsig = True; sb = zb[k]; zused[k] = True
                    elif (not zbull[k]) and c[i] < o[i] and c[i] < zt[k] and not lsig and not ssig: ssig = True; st = zt[k]; zused[k] = True
            k -= 1
        if lsig:
            s = sb - a[i]*sl_m; r = c[i]-s
            if r > 0: sig[i] = 1.0; sl[i] = s; tp[i] = c[i]+r*rr; rk[i] = r
        if ssig:
            s = st + a[i]*sl_m; r = s-c[i]
            if r > 0: sig[i] = -1.0; sl[i] = s; tp[i] = c[i]-r*rr; rk[i] = r
        if big and (c[i] > o[i] or c[i] < o[i]):
            bull = c[i] > o[i]; top = h[i-1]; bot = l[i-1]; ov = False
            for k in range(zn):
                if zbull[k] == bull and top >= zb[k] and bot <= zt[k]: ov = True
            if not ov:
                if zn >= maxz:
                    for j in range(zn-1): zt[j] = zt[j+1]; zb[j] = zb[j+1]; zbull[j] = zbull[j+1]; zborn[j] = zborn[j+1]; zused[j] = zused[j+1]
                    zn -= 1
                zt[zn] = top; zb[zn] = bot; zbull[zn] = bull; zborn[zn] = i; zused[zn] = False; zn += 1
    return sig, sl, tp, rk
def sinyal(df, atr, disp, vol, imp, maxz, yas, sl, rr, be, tutma):
    o, h, l, c, v = df.o.values, df.h.values, df.l.values, df.c.values, df.v.values; a = gost.atr(h, l, c, int(atr))
    sg, s, t, rk = _sim(o, h, l, c, v, a, gost.sma(v, int(vol)), disp, imp, int(maxz), int(yas), sl, rr)
    return dict(sig=sg, sl=s, tp=t, taa=rk*be, toa=np.where(sg != 0, 1e12, np.nan), tbe=1, maxhold=int(tutma))
