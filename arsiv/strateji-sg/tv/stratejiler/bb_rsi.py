"""Bollinger + RSI Double Strategy (uCV8I4xA, ChartArt): RSI(6) 50'yi + fiyat alt bandı (BB200) yukarı keserse long; RSI 50'yi + fiyat üst bandı aşağı keserse short."""
import numpy as np
from tv import gost
ISIM = "Bollinger + RSI (ChartArt)"; PINE_ID = "uCV8I4xA"
PARAM = dict(rsi=6, bb=200, bb_carpan=2.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük (klasik 2016 betiği)."
def sinyal(df, rsi, bb, bb_carpan):
    c = df.c.values; r = gost.rsi(c, int(rsi)); b = gost.sma(c, int(bb)); d = bb_carpan*gost.stdev(c, int(bb))
    up, lo = b + d, b - d; f50 = np.full(len(c), 50.0); ok = ~np.isnan(lo) & ~np.isnan(r)
    lc = gost.crossover(np.nan_to_num(r), f50) & gost.crossover(c, np.nan_to_num(lo)) & ok
    sc = gost.crossunder(np.nan_to_num(r), f50) & gost.crossunder(c, np.nan_to_num(up)) & ok
    return dict(sig=gost.flipsig(lc, sc))
