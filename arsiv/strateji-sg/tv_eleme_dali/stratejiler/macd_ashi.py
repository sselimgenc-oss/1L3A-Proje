"""MACD ASHI BARS SL-TP (YfPnKE22): Heikin Ashi kapanışı üzerinde DEMA(12)−DEMA(25) MACD'si, sinyal SMA15; delta sıfırı yukarı keserse long, aşağı keserse short (stop emri kapanış seviyesinde, bir mum geçerli); %10 hedef, %3 stop."""
import numpy as np
from tv import gost
ISIM = "MACD Heikin Ashi (SL-TP)"; PINE_ID = "YfPnKE22"
PARAM = dict(hizli=12, yavas=25, sinyal=15, tp=10.0, sl=3.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def sinyal(df, hizli, yavas, sinyal, tp, sl):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values; hc = (o+h+l+c)/4
    def dema(x, n): a = gost.sma(x, int(n)); return 2*a - gost.sma(a, int(n))
    m = dema(hc, hizli) - dema(hc, yavas); d = m - gost.sma(m, int(sinyal)); z = np.zeros(len(c)); dn = np.nan_to_num(d)
    lg, sh = gost.crossover(dn, z) & ~np.isnan(d), gost.crossunder(dn, z) & ~np.isnan(d)
    return dict(sig=gost.flipsig(lg, sh), sep=np.where(lg | sh, c, np.nan), slp=sl/100, tpp=tp/100)
