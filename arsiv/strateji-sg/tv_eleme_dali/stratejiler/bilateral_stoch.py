"""Bilateral Stochastic Oscillator (NJb4BQ5n, alexgrover): TMA(100) önfiltreli 'bull/bear' çifti; bull, bear'ı yukarı keserse long, aşağı keserse short; long bull<sinyal kesişimiyle, short bear<sinyal kesişimiyle kapanır. Martingale çarpanı varsayılan 1.0 (kapalı) alındı. Pine'daki strategy.order net-pozisyon mantığı çevirmede basitleştirildi (ters sinyalde dön)."""
import numpy as np
from tv import gost
ISIM = "Bilateral Stochastic (Alexgrover)"; PINE_ID = "NJb4BQ5n"
PARAM = dict(uzun=100, sinyal=20)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "PDF: EURUSD 15 dk; forex verisi yok → saatlik kripto/ABD/emtia."
def sinyal(df, uzun, sinyal):
    c = df.c.values; n = int(uzun)
    src = gost.sma(gost.sma(c, n), n); a = gost.highest(src, n); b = gost.lowest(src, n); r = gost.sma(a-b, n)
    with np.errstate(all="ignore"):
        bull = src/r - b/r; bear = np.abs(src/r - a/r); sg = gost.sma(np.maximum(bull, bear), int(sinyal))
    bu, be = np.nan_to_num(bull), np.nan_to_num(bear); ok = ~np.isnan(bull)
    le = gost.crossover(bu, be) & ok; se = gost.crossunder(bu, be) & ok
    xl = gost.crossunder(bu, np.nan_to_num(sg)) & ok; xs = gost.crossunder(be, np.nan_to_num(sg)) & ok
    return dict(sig=gost.flipsig(le, se), xl=xl, xs=xs)
