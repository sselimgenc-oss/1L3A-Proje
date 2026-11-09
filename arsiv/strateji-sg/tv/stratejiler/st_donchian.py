"""Supertrend Donchian Breakout (FDeprmix): Supertrend yükselişte + 4s HTF supertrend yükselişte + hacim 1.5×ort. → long (kırılım koşulu Pine'daki gibi close>alt kanal); ATR×2 stop, ATR×3 hedef, trend dönünce çıkış. Yalnız long."""
import numpy as np
from tv import gost
ISIM = "Supertrend + Donchian kırılımı"; PINE_ID = "FDeprmix"
PARAM = dict(faktor=3.0, atr=10, donchian=20, vol=20, vol_carpan=1.5, atr_risk=14, stop=2.0, hedef=3.0)
TF = "1h"; EVREN = ["kripto", "abd", "bist", "emtia"]; YON = 1
NEDEN = "Zaman dilimi belirtilmemiş; 1 saatlik (HTF 4s onayıyla uyumlu), yalnız long (Pine varsayılanı)."
def _stdir(d, faktor, atr):
    a = gost.atr(d.h.values, d.l.values, d.c.values, int(atr))
    return gost.supertrend(d.h.values, d.l.values, d.c.values, a, faktor, (d.h.values+d.l.values)/2)[1]
def sinyal(df, faktor, atr, donchian, vol, vol_carpan, atr_risk, stop, hedef):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    a = gost.atr(h, l, c, int(atr)); _, d = gost.supertrend(h, l, c, a, faktor, (h+l)/2); up = d < 0
    hd = gost.htf(df, "4h", lambda x: _stdir(x, faktor, atr)); hup = hd < 0
    lower = gost.sh(gost.lowest(l, int(donchian)), 1)
    vok = v > gost.sma(v, int(vol))*vol_carpan
    sig = (up & hup & (c > lower) & vok)
    ra = gost.atr(h, l, c, int(atr_risk))
    return dict(sig=sig.astype(float), xl=~up, sld=ra*stop, tpd=ra*hedef, poc=True)
