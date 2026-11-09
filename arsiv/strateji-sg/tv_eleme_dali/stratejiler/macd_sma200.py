"""MACD + SMA 200 (yMCa3XZD, ChartArt): SMA tabanlı MACD histogramı 0'ı keserse + MACD>0 + hızlı>yavaş + 26 bar önce kapanış>SMA200 → long (tersi short). Stop-emir girişi bir sonraki açılışta dolar."""
import numpy as np
from tv import gost
ISIM = "MACD + SMA200 (ChartArt)"; PINE_ID = "yMCa3XZD"
PARAM = dict(hizli=12, yavas=26, sinyal=9, cok_yavas=200)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Yazar SPX/DOWI günlük test etmiş; günlük, tüm pazarlar."
def sinyal(df, hizli, yavas, sinyal, cok_yavas):
    c = df.c.values; f = gost.sma(c, int(hizli)); s = gost.sma(c, int(yavas)); v = gost.sma(c, int(cok_yavas))
    macd = f - s; sg = gost.sma(macd, int(sinyal)); hist = macd - sg; z = np.zeros(len(c))
    ok = ~np.isnan(v) & ~np.isnan(hist)
    h0 = np.nan_to_num(hist)
    lc = gost.crossover(h0, z) & (macd > 0) & (f > s) & (gost.sh(c, int(yavas)) > v) & ok
    sc = gost.crossunder(h0, z) & (macd < 0) & (f < s) & (gost.sh(c, int(yavas)) < v) & ok
    return dict(sig=gost.flipsig(lc, sc))
