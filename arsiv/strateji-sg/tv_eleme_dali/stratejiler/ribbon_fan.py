"""EMA Ribbon Fan Angle (X0F9OE4L): 5 EMA (8-55) yelpazesi açılırken + RSI + hacim filtresi; ATR×2 stop, 2R hedef, yelpaze kapanınca çıkış."""
import numpy as np
from tv import gost
ISIM = "EMA Ribbon Fan Angle"; PINE_ID = "X0F9OE4L"
PARAM = dict(egim=5, giris=0.8, cikis=0.2, rsi=14, vol=20, atr=14, atr_carpan=2.0, hedefR=2.0)
TF = "4h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Yazar zaman dilimi belirtmemiş; 4 saatlik."
def sinyal(df, egim, giris, cikis, rsi, vol, atr, atr_carpan, hedefR):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    e = [gost.ema(c, n) for n in (8, 13, 21, 34, 55)]
    k = int(egim); s = [(x - gost.sh(x, k))/gost.sh(x, k)*100 for x in e]
    allp = np.all([x > 0 for x in s], axis=0); alln = np.all([x < 0 for x in s], axis=0)
    incu = (s[0] > s[1]) & (s[1] > s[2]) & (s[2] > s[3]) & (s[3] > s[4]); incd = (s[0] < s[1]) & (s[1] < s[2]) & (s[2] < s[3]) & (s[3] < s[4])
    fs = s[0] - s[4]; r = gost.rsi(c, int(rsi)); vok = v > gost.sma(v, int(vol))*1.0
    lc = allp & incu & (fs > giris) & (r > 50) & (r < 70) & vok
    sc = alln & incd & (fs < -giris) & (r < 50) & (r > 30) & vok
    xl = (~incu) | (fs < cikis); xs = (~incd) | (fs > -cikis)
    sd = gost.atr(h, l, c, int(atr))*atr_carpan
    return dict(sig=gost.flipsig(lc, sc), xl=xl, xs=xs, sld=sd, tpd=sd*hedefR)
