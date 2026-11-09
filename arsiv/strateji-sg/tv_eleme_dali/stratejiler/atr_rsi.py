"""ATR_RSI v2 (mqh6UJ9p, liwei666): ATR>ATR-SMA(45), ATR-SMA/fiyat %0.3–0.7 aralığında ve RSI(15) >60 → long, <40 → short; stop = pozisyon tepesinden/dibinden %1.5 izleyen, hedef long +%3 / short −%6. (Pine'daki close±5 limit giriş piyasa girişi olarak alındı.)"""
import numpy as np
from tv import gost
ISIM = "ATR_RSI v2"; PINE_ID = "mqh6UJ9p"
PARAM = dict(atr=26, atr_ma=45, rsi=15, rsi_giris=10.0, norm_alt=0.3, norm_ust=0.7, iz=1.5)
TF = "15m"; EVREN = ["kripto"]
NEDEN = "PDF: BTCUSDT.P 15 dk → kripto 15dk."
def sinyal(df, atr, atr_ma, rsi, rsi_giris, norm_alt, norm_ust, iz):
    h, l, c = df.h.values, df.l.values, df.c.values
    a = gost.atr(h, l, c, int(atr)); am = gost.sma(a, int(atr_ma)); r = gost.rsi(c, int(rsi)); nm = am/c*100
    with np.errstate(invalid="ignore"):
        ok = (nm >= norm_alt) & (nm <= norm_ust) & (a > am)
        le = ok & (r > 50+rsi_giris); se = ok & (r < 50-rsi_giris)
    return dict(sig=gost.flipsig(le, se) * np.where(le | se, 1, 0), tpd=np.where(le, 0.03*c, 0.06*c), sld=iz/100*c, tra=0.0, tro=iz/100.0, trd=0)
