"""Channel Reversion System (XRZCjbFr): 50 günlük kanalın alt %25'ine inen fiyat (kapanış > SMA200) → long; kanal ortası hedef, kanal altı−ATR stop, SMA200 altı çıkış (hepsi kapanış bazlı, process_orders_on_close). Yalnız long."""
import numpy as np
from tv import gost
ISIM = "Channel Reversion System"; PINE_ID = "XRZCjbFr"
PARAM = dict(kanal=50, bolge=25.0, sma=200, atr=14, atr_c=1.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]; YON = 1
NEDEN = "Gün cinsinden kanal uzunluğu; günlük, tüm pazarlar."
def sinyal(df, kanal, bolge, sma, atr, atr_c):
    h, l, c = df.h.values, df.l.values, df.c.values
    up = gost.sh(gost.highest(h, int(kanal))); lo = gost.sh(gost.lowest(l, int(kanal))); mid = (up+lo)/2
    zone = lo + (up-lo)*bolge/100; a = gost.atr(h, l, c, int(atr)); t = gost.sma(c, int(sma))
    with np.errstate(invalid="ignore"):
        buy = (c > t) & (c <= zone)
        xl = (c >= mid) | (c < lo - a*atr_c) | (c < t)
    rd = c - (lo - a*atr_c); rd = np.where(rd > 0, rd, np.nan)
    return dict(sig=gost.durum(buy, xl), xl=xl, rdd=rd, poc=True)
