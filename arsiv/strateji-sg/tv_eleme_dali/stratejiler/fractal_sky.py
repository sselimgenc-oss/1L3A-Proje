"""Fractal Breakout Trend Following (IqUET4xO, Skyrexio): Bill Williams yukarı fraktalı (pivothigh 2/2, 2 mum gecikmeli onay) Alligator dişi (SMMA8[5]) üstündeyse ve ATR yüzdelik ortalaması ≤ 50 ise fraktal seviyesine stop-giriş (long); stop = max(giriş−%3, aktif aşağı fraktal). Yalnız long."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Fractal Breakout (Skyrexio)"; PINE_ID = "IqUET4xO"
PARAM = dict(atr_esik=50, atr_per=5, stop=3.0)
TF = "4h"; EVREN = ["kripto"]; YON = 1
NEDEN = "PDF: BTCUSDT 4 saat."
@njit(cache=True)
def _seviye(h, l, teeth, ph, pl):
    n = len(h); upL = np.full(n, np.nan); upA = np.full(n, np.nan); dnL = np.full(n, np.nan); dnA = np.full(n, np.nan)
    for i in range(n):
        if i > 0: upL[i] = upL[i-1]; dnL[i] = dnL[i-1]; dnA[i] = dnA[i-1]
        if not np.isnan(ph[i]): upL[i] = ph[i]
        elif i > 0 and not np.isnan(upL[i-1]) and h[i] > upL[i-1] and h[i-1] <= upL[i-1]: upL[i] = np.nan
        if not np.isnan(upL[i]) and not np.isnan(teeth[i]) and upL[i] >= teeth[i]: upA[i] = upL[i]
        if not np.isnan(pl[i]): dnL[i] = pl[i]
        if not np.isnan(dnL[i]) and not np.isnan(teeth[i]) and dnL[i] <= teeth[i]: dnA[i] = dnL[i]
    return upL, upA, dnL, dnA
def _pivots(x, left, right, high=True):
    n = len(x); o = np.full(n, np.nan)
    for i in range(left+right, n):
        j = i-right; w = x[j-left:j+right+1]
        if (high and x[j] == w.max() and (w == x[j]).sum() == 1) or ((not high) and x[j] == w.min() and (w == x[j]).sum() == 1): o[i] = x[j]
    return o
def sinyal(df, atr_esik, atr_per, stop):
    h, l, c = df.h.values, df.l.values, df.c.values
    teeth = gost.sh(gost.rma((h+l)/2, 8), 5)
    ph = _pivots(h, 2, 2, True); pl = _pivots(l, 2, 2, False)
    upL, upA, dnL, dnA = _seviye(h, l, teeth, ph, pl)
    pr = gost.percentrank(gost.atr(h, l, c, 13), 52); avg = gost.sma(np.nan_to_num(pr), int(atr_per))
    with np.errstate(invalid="ignore"):
        lc = ~np.isnan(upA) & (avg <= atr_esik)
    return dict(sig=lc.astype(float), sep=np.where(lc, upA, np.nan), slp=stop/100, dyl=dnA)
