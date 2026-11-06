"""Supertrend + Volatility Regime Switch (TbK1rB5B): ADX>25 'trend' (çarpan 1.75), ADX<20 'yatay' (çarpan 4.5, yeni giriş kapalı); dönüşte yön değiştir."""
import numpy as np
from tv import gost
ISIM = "Supertrend + rejim anahtarı"; PINE_ID = "TbK1rB5B"
PARAM = dict(adx=14, atr=10, siki=1.75, genis=4.5)
TF = "1h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 1 saatlik. Trailing/TP varsayılanı kapalı (yalnız dönüşle çıkış)."
def sinyal(df, adx, atr, siki, genis):
    h, l, c = df.h.values, df.l.values, df.c.values
    _, _, ax = gost.dmi(h, l, c, int(adx), int(adx))
    n = len(c); mult = np.full(n, siki); rej = 1.0; yatay = np.zeros(n, bool)
    for i in range(n):
        if ax[i] > 25: rej = 1.0
        elif ax[i] < 20: rej = 0.0
        mult[i] = siki if rej == 1.0 else genis; yatay[i] = (ax[i] < 20)
    a = gost.atr(h, l, c, int(atr)); _, d = gost.supertrend_v(h, l, c, a, mult, (h+l)/2)
    p = gost.sh(d, 1); izin = ~yatay
    return dict(sig=gost.flipsig((d == -1) & (p == 1) & izin, (d == 1) & (p == -1) & izin))
