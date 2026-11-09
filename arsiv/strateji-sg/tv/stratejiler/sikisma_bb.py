"""Bollinger Squeeze Breakout + Volume (N1OCoFkf): BB genişliği 50 bar ortalamasının %80'inin altındaydı + üst/alt banda kırılım + hacim>ort → giriş; ATR×1.5 stop, ATR×3 hedef."""
import numpy as np
from tv import gost
ISIM = "BB sıkışma kırılımı + hacim"; PINE_ID = "N1OCoFkf"
PARAM = dict(bb=20, carpan=2.0, sikisma=50, esik=0.8, vol=20, atr=14, stop=1.5, hedef=3.0)
TF = "1h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 1 saatlik, tüm pazarlar."
def sinyal(df, bb, carpan, sikisma, esik, vol, atr, stop, hedef):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    m = gost.sma(c, int(bb)); d = carpan*gost.stdev(c, int(bb)); u, lo = m+d, m-d
    w = (u-lo)/m; sq = w < gost.sma(w, int(sikisma))*esik; was = gost.sh(sq.astype(float)) == 1
    vp = v > gost.sma(v, int(vol)); a = gost.atr(h, l, c, int(atr))
    lc = was & gost.crossover(c, np.nan_to_num(u, nan=1e18)) & vp; sc = was & gost.crossunder(c, np.nan_to_num(lo, nan=-1e18)) & vp
    return dict(sig=gost.flipsig(lc, sc), sld=a*stop, tpd=a*hedef)
