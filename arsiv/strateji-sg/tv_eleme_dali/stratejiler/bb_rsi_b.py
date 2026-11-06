"""Bollinger + RSI Double (zopumZ8a, ChartArt): RSI(16) 45'i yukarı + kapanış BB(20,2) altını yukarı keserse long; RSI 55'i aşağı + kapanış üst bandı aşağı keserse short (stop emirleri bir mum geçerli → ertesi açılış); çıkış yalnız ters sinyal."""
import numpy as np
from tv import gost
ISIM = "Bollinger + RSI Double (ChartArt, RSI16)"; PINE_ID = "zopumZ8a"
PARAM = dict(rsi=16, deger=45.0, bb=20, bb_c=2.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Klasik ChartArt betiği; günlük, tüm pazarlar."
def sinyal(df, rsi, deger, bb, bb_c):
    c = df.c.values; r = np.nan_to_num(gost.rsi(c, int(rsi))); b = gost.sma(c, int(bb)); d = bb_c*gost.stdev(c, int(bb)); lo, up = np.nan_to_num(b-d), np.nan_to_num(b+d); n = len(c)
    lg = gost.crossover(r, np.full(n, deger)) & gost.crossover(c, lo); sh = gost.crossunder(r, np.full(n, 100-deger)) & gost.crossunder(c, up)
    return dict(sig=gost.flipsig(lg, sh))
