"""Golden Vector Trend Orchestrator (dxhgQwyI): Supertrend(14,3.5) yönü + EMA200 + ADX>=25 + DI yönü; koşul oluşunca giriş, supertrend ters dönünce çıkış."""
import numpy as np
from tv import gost
ISIM = "GVTO Supertrend+EMA+ADX"; PINE_ID = "dxhgQwyI"
PARAM = dict(atr=14, carpan=3.5, ema=200, adx=14, adx_esik=25)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, atr, carpan, ema, adx, adx_esik):
    h, l, c = df.h.values, df.l.values, df.c.values
    a = gost.atr(h, l, c, int(atr)); _, d = gost.supertrend(h, l, c, a, carpan, (h+l)/2)
    e = gost.ema(c, int(ema)); dip, dim, ax = gost.dmi(h, l, c, int(adx), int(adx))
    lc = (d == -1) & (c > e) & (ax >= adx_esik) & (dip > dim); sc = (d == 1) & (c < e) & (ax >= adx_esik) & (dim > dip)
    lt = lc & ~np.r_[False, lc[:-1]]; st = sc & ~np.r_[False, sc[:-1]]
    return dict(sig=gost.flipsig(lt, st), xl=(d == 1), xs=(d == -1))
