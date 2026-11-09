"""MA-CCI Trailing Long (d117dN6D, 3Commas): saatlik SMA(24) SMA(31)'i AŞAĞI keserken ve CCI(11) −80'i aşağı keserken (3 mum içinde ikisi de) long (aşırı satım alımı); stop %3.25, +%1.5'ten sonra %0.05 izleyen stop. Yalnız long."""
import numpy as np
from tv import gost
from tv.stratejiler.triple_cci import cci
ISIM = "MA-CCI Trailing Long (3Commas)"; PINE_ID = "d117dN6D"
PARAM = dict(hizli=24, yavas=31, cci=11, esik=-80.0, canli=3, sl=3.25, tp_akt=1.5, iz=0.05)
TF = "1h"; EVREN = ["kripto"]; YON = 1
NEDEN = "Betikte MA ve CCI zaman dilimi 60 dk; saatlik kripto."
def sinyal(df, hizli, yavas, cci, esik, canli, sl, tp_akt, iz):
    from tv.stratejiler.triple_cci import cci as cc
    c = df.c.values; f, s = gost.sma(c, int(hizli)), gost.sma(c, int(yavas)); x = cc(c, int(cci))
    ma = gost.crossunder(np.nan_to_num(f), np.nan_to_num(s)); cs = gost.crossunder(np.nan_to_num(x), np.full(len(c), esik))
    ba = gost.barssince(ma); bc = gost.barssince(cs)
    sg = (ba <= canli) & (bc <= canli) & (ma | cs)
    return dict(sig=sg.astype(float), slp=sl/100, tra=tp_akt/100, tro=iz/100, trd=0)
