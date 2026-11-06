"""Moving Average Crossover (Ip667jzb): dinamik EMA(5; kaynak: trend üstündeyse düşük, değilse yüksek) SMA(10)'u yukarı keserken Fast≥Slow≥Trend(SMA13) ise long, aşağı keserken Fast≤Slow≤Trend ise short; ters kesişimde kapat. Süzgeçler/SL/TP varsayılanda kapalı."""
import numpy as np
from tv import gost
ISIM = "Moving Average Crossover (dinamik EMA)"; PINE_ID = "Ip667jzb"
PARAM = dict(hizli=5, yavas=10, trend=13)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, hizli, yavas, trend):
    h, l, c = df.h.values, df.l.values, df.c.values; t = gost.sma(c, int(trend)); f = gost.ema(np.where(c > t, l, h), int(hizli)); s = gost.sma(c, int(yavas))
    fn, sn = np.nan_to_num(f), np.nan_to_num(s); up, dn = gost.crossover(fn, sn), gost.crossunder(fn, sn)
    with np.errstate(invalid="ignore"): lg = up & (f >= s) & (s >= t); sh = dn & (f <= s) & (s <= t)
    return dict(sig=gost.flipsig(lg, sh), xl=dn, xs=up)
