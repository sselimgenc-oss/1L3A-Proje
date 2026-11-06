"""MACD + Stochastic Double Strategy (G5ro3y87, ChartArt): %K/%D kesişimi aşırı bölgede + MACD histogram sıfır kesişimi."""
import numpy as np
from tv import gost
ISIM = "MACD + Stochastic (ChartArt)"; PINE_ID = "G5ro3y87"
PARAM = dict(hizli=12, yavas=26, sinyal=9, stoch=14, asiri=71, k=3, d=2)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük (klasik 2016 betiği)."
def sinyal(df, hizli, yavas, sinyal, stoch, asiri, k, d):
    h, l, c = df.h.values, df.l.values, df.c.values
    macd = gost.ema(c, int(hizli)) - gost.ema(c, int(yavas)); delta = macd - gost.ema(macd, int(sinyal))
    K = gost.sma(gost.stoch(c, h, l, int(stoch)), int(k)); D = gost.sma(K, int(d)); z = np.zeros(len(c))
    ok = ~np.isnan(K) & ~np.isnan(D) & ~np.isnan(delta)
    lc = gost.crossover(K, D) & (K < 100-asiri) & gost.crossover(np.nan_to_num(delta), z) & ok
    sc = gost.crossunder(K, D) & (K > asiri) & gost.crossunder(np.nan_to_num(delta), z) & ok
    return dict(sig=gost.flipsig(lc, sc))
