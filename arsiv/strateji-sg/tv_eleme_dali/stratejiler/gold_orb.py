"""Gold NY ORB v19 (FJZvYKaB): 13:00 UTC saatinin aralığı (OR) → 14:00–16:30 UTC'de kapanış OR tepesini yukarı keserse (önceki kapanış altında/eşit), yeşil mum, hacim > 1.5×SMA20, OR ≤ 2.5 ATR, ATR ≤ 2×ATR-ort → long; stop = giriş−OR, hedef = giriş+2.5×OR; 20:00'de kapat. Günde en çok 1 işlem, yalnız long. Saatlik veriyle (15 dk yerine) uyarlandı."""
import numpy as np
from tv import gost
ISIM = "Gold NY ORB v19"; PINE_ID = "FJZvYKaB"
PARAM = dict(atr=14, or_atr=2.5, rejim=2.0, hacim=1.5, hedef=2.5)
TF = "1h"; EVREN = ["emtia"]; YON = 1
NEDEN = "PDF: XAUUSD 15 dk; Yahoo emtia 15 dk yalnız 60 gün → saatlik uyarlama (OR = 13:00 saat mumu, giriş penceresi 14:00–16:00 saat mumları)."
def sinyal(df, atr, or_atr, rejim, hacim, hedef):
    o, h, l, c, v = df.o.values, df.h.values, df.l.values, df.c.values, df.v.values; n = len(c)
    a = gost.atr(h, l, c, int(atr)); am = gost.sma(a, 20); va = gost.sma(v, 20)
    idx = df.index; hr = idx.hour.values; wd = idx.dayofweek.values < 5; gun = idx.normalize().values
    sig = np.zeros(n); sl = np.full(n, np.nan); tp = np.full(n, np.nan); xl = np.zeros(n, bool)
    oh = ol = np.nan; fired = False; ready = False; prev_gun = None
    for i in range(1, n):
        if gun[i] != prev_gun: oh = ol = np.nan; fired = False; ready = False; prev_gun = gun[i]
        if wd[i] and hr[i] == 13:
            oh = h[i] if np.isnan(oh) else max(oh, h[i]); ol = l[i] if np.isnan(ol) else min(ol, l[i])
        if (not (wd[i] and hr[i] == 13)) and (not np.isnan(oh)) and (not ready) and hr[i] >= 14: ready = True
        win = wd[i] and hr[i] >= 14 and hr[i] <= 16
        if ready and not np.isnan(oh) and win and not fired:
            rg = oh - ol
            if (rg <= a[i]*or_atr and a[i] <= am[i]*rejim and c[i] > oh and c[i-1] <= oh and c[i] > o[i] and v[i] > va[i]*hacim):
                sig[i] = 1.0; sl[i] = c[i] - rg; tp[i] = c[i] + rg*hedef; fired = True
        if wd[i] and hr[i] == 20: xl[i] = True
    return dict(sig=sig, sl=sl, tp=tp, xl=xl)
