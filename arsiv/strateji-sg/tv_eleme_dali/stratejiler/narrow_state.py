"""Yuri Garcia Narrow State (x39mKkAp): EMA20 ile SMA200 arası ≤%1.5 (dar durum) iken trend yönünde 'fil' mum (gövde>1.5 ATR) ya da dönüş mumu (kırmızı sonrası yeşil kapanış>önceki tepe) → giriş; stop 2 ATR, hedef 2R."""
import numpy as np
from tv import gost
ISIM = "Narrow State (Yuri Garcia)"; PINE_ID = "x39mKkAp"
PARAM = dict(atr=14, atr_c=2.0, rrr=2.0, ema=20, sma=200, fil=1.5, mesafe=1.5)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, atr, atr_c, rrr, ema, sma, fil, mesafe):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values
    a = gost.atr(h, l, c, int(atr)); e = gost.ema(c, int(ema)); s = gost.sma(c, int(sma)); narrow = np.abs(e-s)/s*100 <= mesafe
    bull = (c > s) & (e > s); bear = (c < s) & (e < s); el = np.abs(c-o) > a*fil
    po, pc, ph, pl = gost.sh(o), gost.sh(c), gost.sh(h), gost.sh(l)
    with np.errstate(invalid="ignore"):
        lg = ((el & (c > o) & bull) | (bull & (pc < po) & (c > o) & (c > ph))) & narrow
        sh = ((el & (c < o) & bear) | (bear & (pc > po) & (c < o) & (c < pl))) & narrow
    return dict(sig=gost.flipsig(lg, sh), sl=np.where(lg, c-a*atr_c, np.where(sh, c+a*atr_c, np.nan)), tp=np.where(lg, c+a*atr_c*rrr, np.where(sh, c-a*atr_c*rrr, np.nan)))
