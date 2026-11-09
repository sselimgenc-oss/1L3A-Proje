"""Advanced Ichimoku Clouds (uycyVpIq, Skyrexio): varsayılan: Tenkan/Kijun yukarı kesişimde (bulutun neresinde olursa olsun) long; 'Bearish Weak' çıkışı: aşağı kesişim Tenkan'ın HER İKİ bulut çizgisinin (kaydırılmış) üstündeyken gerçekleşirse çıkış. SL/TP yok. Yalnız long."""
import numpy as np
from tv import gost
ISIM = "Ichimoku (Skyrexio, varsayılan ayarlar)"; PINE_ID = "uycyVpIq"
PARAM = dict(tenkan=9, kijun=26, senkou_b=52, kayma=26)
TF = "4h"; EVREN = ["kripto"]; YON = 1
NEDEN = "Zaman dilimi belirtilmemiş; Skyrexio kripto stratejileri genelde saatlik/4 saatlik: 4 saat kripto."
def sinyal(df, tenkan, kijun, senkou_b, kayma):
    h, l = df.h.values, df.l.values
    dn = lambda n: (gost.highest(h, int(n)) + gost.lowest(l, int(n)))/2
    tk, kj = dn(tenkan), dn(kijun); sa = (tk+kj)/2; sb = dn(senkou_b); da, db = gost.sh(sa, int(kayma)-1), gost.sh(sb, int(kayma)-1)
    with np.errstate(invalid="ignore"):
        bull = gost.crossover(np.nan_to_num(tk), np.nan_to_num(kj)); bear = gost.crossunder(np.nan_to_num(tk), np.nan_to_num(kj))
        strong = bull & (tk > da) & (tk > db); neutral = bull & (((tk > da) & (tk < db)) | ((tk < da) & (tk > db))); weak = bull & (tk < da) & (tk < db)
        xweak = bear & (tk > da) & (tk > db)
    return dict(sig=(strong | neutral | weak).astype(float), xl=xweak)
