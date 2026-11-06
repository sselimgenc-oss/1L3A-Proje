"""Vol-Target Trend Engine (2wyXTTMc): SMA200 üzerindeyse (rejim) hedef maruziyet = min(1, %45 / 20 günlük gerçekleşen oynaklık); rejim kapanınca tamamen çık. Yaklaşık çeviri: haftalık yeniden dengeleme YOK, rejim girişinde hedef maruziyet kadar boyutla alınır."""
import numpy as np
from tv import gost
ISIM = "Vol-Target Trend Engine"; PINE_ID = "2wyXTTMc"
PARAM = dict(vol_len=20, hedef=45.0, sma=200)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]; YON = 1
NEDEN = "Betik 'günlük' (252 gün yıllıklandırma); günlük, tüm pazarlar. Hisse/ETF mantığı."
def sinyal(df, vol_len, hedef, sma):
    c = df.c.values
    ret = np.r_[np.nan, c[1:]/c[:-1]-1]; rv = gost.stdev(ret, int(vol_len))*np.sqrt(252)*100
    t = gost.sma(c, int(sma)); reg = c > t
    frac = np.minimum(1.0, hedef/np.maximum(rv, 1.0))
    on = reg & ~np.r_[False, reg[:-1]]
    with np.errstate(invalid="ignore"):
        return dict(sig=on.astype(float), xl=~reg & ~np.isnan(t), szf=np.where(on, frac, np.nan), poc=True)
