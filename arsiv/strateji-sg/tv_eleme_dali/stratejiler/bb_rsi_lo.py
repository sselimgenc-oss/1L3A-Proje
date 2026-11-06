"""Bollinger + RSI Double, Long-Only v1.2 (HDSdFMa3, ChartArt): RSI(6) 50'yi yukarı keser ve kapanış BB(200,2) alt bandını yukarı keserse long (stop emri alt bantta → ertesi açılış); RSI 50'yi aşağı + kapanış üst bandı aşağı keserse kapat."""
import numpy as np
from tv import gost
ISIM = "Bollinger + RSI Long-Only (ChartArt v1.2)"; PINE_ID = "HDSdFMa3"
PARAM = dict(rsi=6, bb=200, bb_c=2.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]; YON = 1
NEDEN = "Klasik ChartArt betiği; günlük, tüm pazarlar."
def sinyal(df, rsi, bb, bb_c):
    c = df.c.values; r = np.nan_to_num(gost.rsi(c, int(rsi))); b = gost.sma(c, int(bb)); d = bb_c*gost.stdev(c, int(bb)); lo, up = np.nan_to_num(b-d), np.nan_to_num(b+d); f = np.full(len(c), 50.0)
    return dict(sig=(gost.crossover(r, f) & gost.crossover(c, lo)).astype(float), xl=gost.crossunder(r, f) & gost.crossunder(c, up))
