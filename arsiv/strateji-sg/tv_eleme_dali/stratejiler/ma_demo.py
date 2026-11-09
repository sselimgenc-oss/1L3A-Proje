"""TradingView örnek betiklerinin ortak sinyali (IHVPG6TS, jjhUHcje, xAEG4ZJG, Ip667jzb varsayılan MA kesişimi): SMA(14) SMA(28)'i yukarı keserse long, aşağı keserse short (hep piyasada). Örnek betiklerin asıl konusu emir mekaniği (SL/TP/zaman aralığı); sinyal bu demo kesişimidir."""
import numpy as np
from tv import gost
ISIM = "SMA 14/28 kesişimi (TV demo sinyali)"; PINE_ID = "IHVPG6TS"
PARAM = dict(hizli=14, yavas=28)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Örnek betik, zaman dilimi yok; günlük, tüm pazarlar."
def sinyal(df, hizli, yavas):
    c = df.c.values; f, s = gost.sma(c, int(hizli)), gost.sma(c, int(yavas)); ok = ~np.isnan(s)
    return dict(sig=gost.flipsig(gost.crossover(np.nan_to_num(f), np.nan_to_num(s)) & ok, gost.crossunder(np.nan_to_num(f), np.nan_to_num(s)) & ok))
