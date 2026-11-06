"""DMI/ADX Trend Dashboard v3 (EcEYc8ap): +DI>−DI, ADX≥20, DI farkı>10, fiyat>EMA50 rejiminde EMA9'a geri çekilip yeniden üstüne çıkınca (pullback) long (short simetrik); başlangıç stop 2 ATR, chandelier izleyen stop (22 mum zirve − 3 ATR), DI ters kesişiminde çık. (ADX-azalma çıkışı ve 5 mum bekleme modellenmedi.)"""
import numpy as np
from numba import njit
from tv import gost
ISIM = "DMI/ADX Pullback v3"; PINE_ID = "EcEYc8ap"
PARAM = dict(di=14, adx_min=20.0, spread=10.0, ema=50, ema_h=9, atr=14, sl=2.0, ch_len=22, ch_c=3.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
@njit(cache=True)
def _pb(lr, sr, cu, cd):
    n = len(lr); sl = np.zeros(n); lp = False; sp = False
    for i in range(n):
        if lr[i] and cd[i]: lp = True
        if not lr[i]: lp = False
        if sr[i] and cu[i]: sp = True
        if not sr[i]: sp = False
        if lp and cu[i] and lr[i]: sl[i] = 1.0; lp = False
        elif sp and cd[i] and sr[i]: sl[i] = -1.0; sp = False
    return sl
def sinyal(df, di, adx_min, spread, ema, ema_h, atr, sl, ch_len, ch_c):
    h, l, c = df.h.values, df.l.values, df.c.values; dip, dim, ad = gost.dmi(h, l, c, int(di), int(di)); a = gost.atr(h, l, c, int(atr)); e = gost.ema(c, int(ema)); eh = gost.ema(c, int(ema_h))
    ok = (ad >= adx_min) & (np.abs(dip-dim) > spread)
    with np.errstate(invalid="ignore"): lr = (dip > dim) & ok & (c > e); sr = (dim > dip) & ok & (c < e)
    cu, cd = gost.crossover(c, np.nan_to_num(eh)), gost.crossunder(c, np.nan_to_num(eh))
    s = _pb(lr, sr, cu, cd)
    xl = gost.crossunder(np.nan_to_num(dip), np.nan_to_num(dim)); xs = gost.crossover(np.nan_to_num(dip), np.nan_to_num(dim))
    return dict(sig=s, sld=a*sl, dyl=gost.highest(h, int(ch_len)) - a*ch_c, dys=gost.lowest(l, int(ch_len)) + a*ch_c, xl=xl, xs=xs)
