"""Crypto momentum strategy (9cxy1Yu9): sıkışma-momentum eğimi (val−val[2]) yukarı döner + fiyat>EMA50 + EMA eğimi>0 + kripto piyasası (BTC; CRYPTOCAP:TOTAL yerine) EMA50 üstünde ve yükseliyor → long; eğim aşağı dönünce çıkış."""
import numpy as np
from tv import gost, veri
ISIM = "Kripto momentum (squeeze eğimi)"; PINE_ID = "9cxy1Yu9"
PARAM = dict(bb=20, kc=20, kc_c=1.5, ema=50)
TF = "1d"; EVREN = ["kripto"]; YON = 1
NEDEN = "Betik kripto için; kripto günlük. Piyasa filtresi için TOTAL verisi yok → BTC vekil."
_BTC = {}
def sinyal(df, bb, kc, kc_c, ema):
    h, l, c = df.h.values, df.l.values, df.c.values
    if "b" not in _BTC: _BTC["b"] = veri.al("BTC", "1d")
    m = _BTC["b"].c.reindex(df.index, method="ffill").values
    me = gost.ema(m, int(ema)); mslope = me - gost.sh(me, 1)
    e = gost.ema(c, int(ema)); es = e - gost.sh(e, 1)
    val = gost.linreg(c - ((gost.highest(h, int(kc)) + gost.lowest(l, int(kc)))/2 + gost.sma(c, int(kc)))/2, int(kc), 0)
    sl = val - gost.sh(val, 2)
    with np.errstate(all="ignore"):
        sg = np.sign(sl)
        co = gost.crossover(np.nan_to_num(sg), np.zeros(len(c))); cu = gost.crossunder(np.nan_to_num(sg), np.zeros(len(c)))
        ent = co & (c > e) & (es > 0) & (m > me) & (mslope > 0)
    return dict(sig=ent.astype(float), xl=cu)
