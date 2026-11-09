"""MACD Pullback Sniper (V87nRt9v): MACD sinyali yukarı keser + fiyat>EMA200 + MACD<0 + ADX>20 → long (short için tersi); stop 2 ATR, hedef 2R; ters MACD kesişiminde çıkış."""
import numpy as np
from tv import gost
ISIM = "MACD Pullback Sniper"; PINE_ID = "V87nRt9v"
PARAM = dict(hizli=12, yavas=26, sinyal=9, ema=200, adx=14, adx_min=20.0, atr=14, sl=2.0, rr=2.0)
TF = "4h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik (pullback sistemi), kripto/ABD/emtia."
def sinyal(df, hizli, yavas, sinyal, ema, adx, adx_min, atr, sl, rr):
    h, l, c = df.h.values, df.l.values, df.c.values
    m = gost.ema(c, int(hizli)) - gost.ema(c, int(yavas)); s = gost.ema(m, int(sinyal)); e = gost.ema(c, int(ema)); _, _, ad = gost.dmi(h, l, c, int(adx), int(adx)); a = gost.atr(h, l, c, int(atr))
    mn, sn = np.nan_to_num(m), np.nan_to_num(s); bc, sc = gost.crossover(mn, sn), gost.crossunder(mn, sn)
    with np.errstate(invalid="ignore"):
        lg = bc & (c > e) & (m < 0) & (ad > adx_min); sh = sc & (c < e) & (m > 0) & (ad > adx_min)
    return dict(sig=gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0), sld=a*sl, tpd=a*sl*rr, xl=sc & ~sh, xs=bc & ~lg)
