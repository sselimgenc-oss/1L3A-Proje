"""RSI Range Compression (dwgn7hrE): RSI aralığı son 100 barın alt %20 yüzdeliğine sıkışıp (5 bar bellek) RSI aralığın tepesini/dibini kırarsa EMA50 eğimi yönünde giriş; ATR×2 stop. (Pine'daki long hedefi hatalı: close + stopFiyatı×2 — birebir uygulandı, long'da hedef fiilen ~3×fiyat.)"""
import numpy as np
from tv import gost
ISIM = "RSI Range Compression"; PINE_ID = "dwgn7hrE"
PARAM = dict(rsi=14, sikisma=20, yuzdelik_pencere=100, esik=20.0, bellek=5, ema=50, egim=5, adx=14, adx_min=15.0, atr=14, stop=2.0, hedefR=2.0)
TF = "1h"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; 1 saatlik."
def sinyal(df, rsi, sikisma, yuzdelik_pencere, esik, bellek, ema, egim, adx, adx_min, atr, stop, hedefR):
    h, l, c = df.h.values, df.l.values, df.c.values
    r = gost.rsi(c, int(rsi)); rh = gost.highest(r, int(sikisma)); rl = gost.lowest(r, int(sikisma)); rr = rh - rl
    sq = gost.percentrank(rr, int(yuzdelik_pencere)) <= esik; bs = gost.barssince(np.nan_to_num(sq, nan=0).astype(bool))
    rec = bs <= bellek
    e = gost.ema(c, int(ema)); up = e > gost.sh(e, int(egim)); dn = e < gost.sh(e, int(egim))
    _, _, ax = gost.dmi(h, l, c, int(adx), int(adx)); ok = ax >= adx_min
    lt = gost.crossover(r, np.nan_to_num(gost.sh(rh))) & rec & up & ok
    st = gost.crossunder(r, np.nan_to_num(gost.sh(rl), nan=-1)) & rec & dn & ok
    a = gost.atr(h, l, c, int(atr)); sd = a*stop
    tp = np.where(lt, c + (c - sd)*hedefR, np.where(st, c - sd*hedefR, np.nan))
    return dict(sig=gost.flipsig(lt, st), sld=sd, tp=tp)
