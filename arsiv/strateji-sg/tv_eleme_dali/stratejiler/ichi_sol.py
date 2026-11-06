"""TRADLEWARE Ichimoku TK-Cross + MFI SOL (71yKm18B): Tenkan(20) Kijun(60)'ı yukarı keser + kapanış bulut üstü (120 Senkou B, kaydırılmış) + MFI>50 → long; çıkış kapanış<Kijun; stop = bulut tabanı."""
import numpy as np
from tv import gost
ISIM = "TRADLEWARE Ichimoku TK + MFI"; PINE_ID = "71yKm18B"
PARAM = dict(tenkan=20, kijun=60, senkou_b=120, mfi=14, mfi_min=50.0)
TF = "4h"; EVREN = ["kripto"]; YON = 1
NEDEN = "Açıklamada 'SOL 4h' geçiyor; 4 saatlik kripto."
def sinyal(df, tenkan, kijun, senkou_b, mfi, mfi_min):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values; mid = lambda n: (gost.highest(h, int(n)) + gost.lowest(l, int(n)))/2
    tk, kj = mid(tenkan), mid(kijun); la, lb = (tk+kj)/2, mid(senkou_b); d = int(kijun)
    top = np.maximum(gost.sh(la, d), gost.sh(lb, d)); bot = np.minimum(gost.sh(la, d), gost.sh(lb, d)); m = gost.mfi(h, l, c, v, int(mfi))
    with np.errstate(invalid="ignore"):
        lg = gost.crossover(np.nan_to_num(tk), np.nan_to_num(kj)) & (c > top) & (m > mfi_min)
    return dict(sig=lg.astype(float), xl=c < kj, dyl=bot)
