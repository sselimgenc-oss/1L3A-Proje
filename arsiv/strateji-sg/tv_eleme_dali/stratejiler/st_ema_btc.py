"""BTCUSD Supertrend + EMA Trend Filter 1H (NgSIfKQx): Supertrend(10,1.8) dönüşü + EMA200 filtresi; ters dönüşte pozisyon kapanır."""
import numpy as np
from tv import gost
ISIM = "Supertrend + EMA200 (1s)"; PINE_ID = "NgSIfKQx"
PARAM = dict(atr=10, carpan=1.8, ema=200)
TF = "1h"; EVREN = ["kripto"]
NEDEN = "Yazar BTCUSD 1 saatlik için yazmış; kripto 1 saatlik (14 coin)."
def sinyal(df, atr, carpan, ema):
    h, l, c = df.h.values, df.l.values, df.c.values
    a = gost.atr(h, l, c, int(atr)); _, d = gost.supertrend(h, l, c, a, carpan, (h+l)/2)
    e = gost.ema(c, int(ema)); p = gost.sh(d, 1)
    bf = (d == -1) & (p == 1); sf = (d == 1) & (p == -1)
    return dict(sig=gost.flipsig(bf & (c > e), sf & (c < e)), xl=sf, xs=bf)
