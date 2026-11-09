"""Mean Reversion Setup LliterH (6XPbhz9C, SPX500): kapanış < 10 günlük tepe − 2.5×(25 günlük ort. aralık) ve IBS < 0.3 ve kapanış > SMA50 → long; sert stop kapanış ≤ giriş−2×ATR; bacak 1 (%50): kapanış > önceki tepe; bacak 2 (%50): izleyen stop (kapanış tepe − 1.5×ATR). İki bacak ayrı koşulur."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Mean Reversion IBS (SPX500)"; PINE_ID = "6XPbhz9C"
PARAM = dict(tepe=10, ort=25, carpan=2.5, ibs=0.3, rejim=50, atr=14, sert=2.0, iz=1.5)
TF = "1d"; EVREN = ["abd", "kripto", "emtia"]; YON = 1
NEDEN = "SPX500 günlük; hisse/endeks mantığı → ABD evreni, ayrıca kripto ve emtia."
@njit(cache=True)
def _dur(buy, h, c, atr, sert, iz, bacak):
    n = len(c); xl = np.zeros(n, np.bool_); rd = np.full(n, np.nan); pos = False; hs = 0.0; pk = 0.0
    for i in range(n):
        was = pos
        if pos:
            pk = max(pk, c[i]); tl = pk - iz*atr[i]
            hard = c[i] <= hs
            if hard: xl[i] = True; pos = False
            elif bacak == 1 and i > 0 and c[i] > h[i-1]: xl[i] = True; pos = False
            elif bacak == 2 and c[i] <= tl: xl[i] = True; pos = False
        if (not was) and buy[i] and not np.isnan(atr[i]):
            pos = True; hs = c[i] - sert*atr[i]; pk = c[i]; rd[i] = sert*atr[i]
    return xl, rd
def sinyal(df, tepe, ort, carpan, ibs, rejim, atr, sert, iz):
    h, l, c = df.h.values, df.l.values, df.c.values
    thr = gost.highest(h, int(tepe)) - carpan*gost.sma(h-l, int(ort))
    with np.errstate(all="ignore"):
        b = np.where(h == l, 0.0, (c-l)/(h-l)); reg = gost.sma(c, int(rejim)); a = gost.atr(h, l, c, int(atr))
        buy = (c < thr) & (b < ibs) & (c > reg)
    bac = []
    for k in (1, 2):
        xl, rd = _dur(buy, h, c, a, sert, iz, k)
        bac.append(dict(sig=np.where(buy & ~np.isnan(rd), 1.0, 0.0), xl=xl, rdd=rd, poc=True, olcek=0.5))
    return dict(bacaklar=bac)
