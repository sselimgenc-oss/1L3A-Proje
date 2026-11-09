"""Momentum Exhaustion Breakout (gqaZYhUN): 20 bar zirve kırılımı + hacim 1.5× + EMA20>EMA50 + RSI ivmesi → long; düşüş trendinde zayıf RSI ile kırılım → 'fade' short. ATR×1.5 stop + ATR×1.5 izleyen stop."""
import numpy as np
from tv import gost
ISIM = "Momentum Exhaustion Breakout"; PINE_ID = "gqaZYhUN"
PARAM = dict(n=20, vol=20, vol_c=1.5, ema_h=20, ema_y=50, rsi=14, roc=5, rsi_esik=55.0, atr=14, stop=1.5, iz=1.5)
TF = "1h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 1 saatlik."
def sinyal(df, n, vol, vol_c, ema_h, ema_y, rsi, roc, rsi_esik, atr, stop, iz):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    ef, es = gost.ema(c, int(ema_h)), gost.ema(c, int(ema_y)); up, dn = ef > es, ef < es
    ph = gost.highest(gost.sh(h, 1), int(n)) if False else gost.sh(gost.highest(h, int(n)), 1)
    vx = v > gost.sma(v, int(vol))*vol_c
    r = gost.rsi(c, int(rsi)); rroc = r - gost.sh(r, int(roc)); prk = gost.sh(gost.highest(r, int(n)), 1)
    with np.errstate(invalid="ignore"):
        bo = (h > ph) & vx
        ls = bo & up & (rroc > 0) & (r > rsi_esik); fs = bo & dn & ((r < prk) | (rroc < 0))
    a = gost.atr(h, l, c, int(atr))
    return dict(sig=gost.flipsig(ls, fs), sld=a*stop, taa=a*iz, toa=a*iz)
