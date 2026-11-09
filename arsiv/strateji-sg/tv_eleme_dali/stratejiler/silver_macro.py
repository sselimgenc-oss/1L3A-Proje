"""Silver Always Long + Macro Exit + Flush Protection v2 (mzv5SGie): gümüşte hep long; çıkış: kapanış EMA150 altı, ya da ABD 10Y faizi EMA50'nin %1.35 üstünde + 20 günlük tepe kırılımı (3 mum üst üste), ya da ani düşüş (1g −%4.5 / 2g −%8 / ATR şoku); yeniden giriş: faiz sakin, düşüş sonrası EMA75 üstü + oynaklık sakin. Kapanışta işlem (process_orders_on_close)."""
import numpy as np, pandas as pd
from tv import gost, veri
ISIM = "Silver Always Long + Macro Exit"; PINE_ID = "mzv5SGie"
PARAM = dict(yavas=150, toparlan=75, tnx_ema=50, tnx_brk=20, tnx_pct=1.35, tnx_bar=3, sakin_bar=1, f1=4.5, f2=8.0, atr=14, sok=1.8, sogu=3, vol_sakin=2)
TF = "1d"; SEMBOL = ["GUMUS", "ALTIN"]; YON = 1
NEDEN = "Gümüş günlük; ABD 10Y (^TNX) Yahoo."
_V = {}
def _persist(x, k):
    return gost.rsum(x.astype(float), int(k)) >= k
def sinyal(df, yavas, toparlan, tnx_ema, tnx_brk, tnx_pct, tnx_bar, sakin_bar, f1, f2, atr, sok, sogu, vol_sakin):
    if "t" not in _V: _V["t"] = veri.al("US10Y", "1d")
    t = _V["t"]; t = t[~t.index.normalize().duplicated()]; t.index = t.index.normalize()
    ix = df.index.normalize(); tc = t.c.reindex(ix, method="ffill").values; th = t.h.reindex(ix, method="ffill").values
    h, l, c, o = df.h.values, df.l.values, df.c.values, df.o.values; n = len(c)
    es = gost.ema(c, int(yavas)); er = gost.ema(c, int(toparlan)); trend_exit = c < es
    te = gost.ema(tc, int(tnx_ema)); hp = gost.highest(gost.sh(th), int(tnx_brk))
    with np.errstate(all="ignore"):
        pct = (tc-te)/te*100; stress = (tc > te) & (pct > tnx_pct) & (tc > hp); calm = ~((tc > te) & (pct > tnx_pct))
        d1 = np.r_[np.nan, c[1:]/c[:-1]-1]*100; d1s = gost.sh(d1, 1); d2 = (c/gost.sh(c, 2)-1)*100
        a = gost.atr(h, l, c, int(atr)); ap = a/c*100; rp = (h-l)/c*100
        flush = (gost.sh(c)/gost.sh(c, 2)-1)*100 <= -f1
    oneday = (gost.sh(c)/gost.sh(c, 2)-1)*100 <= -f1; twoday = (gost.sh(c, 1)/gost.sh(c, 3)-1)*100 <= -f2
    shock = (rp > ap*sok) & (c < o)
    fl = np.nan_to_num((oneday | twoday | shock).astype(float)) > 0
    bs = gost.barssince(fl); recent = bs <= sogu; vcalm = rp <= ap*sok; vpers = _persist(np.nan_to_num(vcalm.astype(float)) > 0, vol_sakin)
    ready = (~recent) | ((c > er) & vpers)
    persist_stress = _persist(np.nan_to_num(stress.astype(float)) > 0, tnx_bar); calmp = _persist(np.nan_to_num(calm.astype(float)) > 0, sakin_bar)
    ex = trend_exit | persist_stress | fl
    buy = (~trend_exit) & calmp & ready
    return dict(sig=gost.durum(buy, ex), xl=ex, poc=True)
