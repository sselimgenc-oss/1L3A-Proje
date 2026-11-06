"""Stochastic + RSI Double Strategy (IGJPEi7L, ChartArt): %K/%D kesişimi aşırı bölgede + RSI eşik kesişimi; long ve short."""
import numpy as np
from tv import gost
ISIM = "Stochastic + RSI (ChartArt)"; PINE_ID = "IGJPEi7L"
PARAM = dict(stoch=14, asiri_alim=80, asiri_satim=20, k=3, d=3, rsi=14, rsi_ust=70, rsi_alt=30)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük (klasik 2015 betiği)."
def sinyal(df, stoch, asiri_alim, asiri_satim, k, d, rsi, rsi_ust, rsi_alt):
    h, l, c = df.h.values, df.l.values, df.c.values
    K = gost.sma(gost.stoch(c, h, l, int(stoch)), int(k)); D = gost.sma(K, int(d)); r = gost.rsi(c, int(rsi))
    ok = ~np.isnan(K) & ~np.isnan(D)
    lc = gost.crossover(K, D) & (K < asiri_satim) & gost.crossover(r, np.full(len(c), float(rsi_alt))) & ok
    sc = gost.crossunder(K, D) & (K > asiri_alim) & gost.crossunder(r, np.full(len(c), float(rsi_ust))) & ok
    return dict(sig=gost.flipsig(lc, sc))
