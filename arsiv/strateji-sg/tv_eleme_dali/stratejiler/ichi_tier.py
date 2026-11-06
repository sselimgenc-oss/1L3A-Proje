"""Ichimoku Confluence (xx3enmiW): Tenkan/Kijun yukarı kesişimi güçlü ya da nötr (bulutun üstünde/içinde), günlük HTF Tenkan>Kijun onayı → long; stop 1.5 ATR, hedef 3 ATR; aşağı kesişim (her kademe) çıkış. Yalnız long (varsayılan)."""
import numpy as np
from tv import gost
ISIM = "Ichimoku Confluence (kademeli)"; PINE_ID = "xx3enmiW"
PARAM = dict(tenkan=9, kijun=26, senkou=52, kayma=26, atr=14, sl=1.5, tp=3.0)
TF = "4h"; EVREN = ["kripto", "abd", "emtia"]; YON = 1
NEDEN = "Zaman dilimi belirtilmemiş; 4 saatlik (HTF günlük)."
def sinyal(df, tenkan, kijun, senkou, kayma, atr, sl, tp):
    h, l, c = df.h.values, df.l.values, df.c.values; dn = lambda x, y, n: (gost.highest(x, int(n)) + gost.lowest(y, int(n)))/2
    tk, kj = dn(h, l, tenkan), dn(h, l, kijun); sa, sb = (tk+kj)/2, dn(h, l, senkou); ca, cb = gost.sh(sa, int(kayma)-1), gost.sh(sb, int(kayma)-1)
    top, bot = np.maximum(ca, cb), np.minimum(ca, cb); a = gost.atr(h, l, c, int(atr))
    ht = gost.htf(df, "1D", lambda d: (gost.highest(d.h.values, int(tenkan)) + gost.lowest(d.l.values, int(tenkan)))/2)
    hk = gost.htf(df, "1D", lambda d: (gost.highest(d.h.values, int(kijun)) + gost.lowest(d.l.values, int(kijun)))/2)
    bull = gost.crossover(np.nan_to_num(tk), np.nan_to_num(kj)); bear = gost.crossunder(np.nan_to_num(tk), np.nan_to_num(kj))
    with np.errstate(invalid="ignore"):
        strong = bull & (tk > top); neutral = bull & (tk <= top) & (tk >= bot)
        lg = (strong | neutral) & (ht > hk)
    return dict(sig=lg.astype(float), xl=bear, sl=c - a*sl, tp=c + a*tp)
