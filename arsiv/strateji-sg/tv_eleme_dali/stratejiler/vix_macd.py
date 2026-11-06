"""VIX MACD Long (mfw4fJST): VIX üzerinde MACD(12,26,9); MACD sinyal çizgisini aşağı keserse (korku azalıyor) long, yukarı keserse çık. Yalnız long. (Yazar Nikkei 225'te test etmiş; VIX Yahoo ^VIX günlük.)"""
import numpy as np, pandas as pd
from tv import gost, veri
ISIM = "VIX MACD Long"; PINE_ID = "mfw4fJST"
PARAM = dict(hizli=12, yavas=26, sinyal=9)
TF = "1d"; EVREN = ["endeks", "abd"]; YON = 1
NEDEN = "Günlük; endeks ETF ve ABD hisseleri (VIX ABD volatilitesi)."
_V = {}
def sinyal(df, hizli, yavas, sinyal):
    if "v" not in _V: _V["v"] = veri.al("VIX", "1d")
    v = _V["v"].c; v.index = v.index.normalize(); v = v[~v.index.duplicated()]
    x = v.reindex(df.index.normalize(), method="ffill").values
    m = gost.ema(x, int(hizli)) - gost.ema(x, int(yavas)); s = gost.ema(np.nan_to_num(m, nan=0.0), int(sinyal))
    ok = ~np.isnan(m)
    return dict(sig=(gost.crossunder(np.nan_to_num(m), s) & ok).astype(float), xl=gost.crossover(np.nan_to_num(m), s) & ok)
