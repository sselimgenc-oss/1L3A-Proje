"""Aurora KAMA Trend (kbYTJ8V2): KAMA(10) 3 bar yükselirse + fiyat>SMA200 → long (düşüşte short); sabit %4 stop, %6 izleyen (5 bar gecikmeli)."""
import numpy as np
from numba import njit
from tv import gost
ISIM = "Aurora KAMA Trend"; PINE_ID = "kbYTJ8V2"
PARAM = dict(er=10, hizli=2, yavas=30, kalicilik=3, sma=200, stop=4.0, iz=6.0)
TF = "4h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik. Girişler arası min. 5 bar kuralı uygulanmadı (motor yeniden girişi zaten stop sonrası bir sonraki sinyalde yapar)."
@njit(cache=True)
def _kama(x, n, f, s):
    o = np.full(len(x), np.nan); fs = 2.0/(f+1); ss = 2.0/(s+1)
    for i in range(n, len(x)):
        ch = abs(x[i]-x[i-n]); vol = 0.0
        for j in range(i-n+1, i+1): vol += abs(x[j]-x[j-1])
        er = ch/vol if vol != 0 else 0.0
        sc = (er*(fs-ss)+ss)**2
        o[i] = x[i] if np.isnan(o[i-1]) else o[i-1] + sc*(x[i]-o[i-1])
    return o
def sinyal(df, er, hizli, yavas, kalicilik, sma, stop, iz):
    c = df.c.values; k = _kama(c, int(er), int(hizli), int(yavas)); sm = gost.sma(c, int(sma))
    r = gost.rising(k, int(kalicilik)); f = gost.falling(k, int(kalicilik))
    return dict(sig=gost.flipsig(r & (c > sm), f & (c < sm)), slp=stop/100, tra=iz/100, tro=iz/100, trd=5)
