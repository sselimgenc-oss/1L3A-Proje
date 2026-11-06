"""Universal Aggressive Trend MACD v3.3 (UVosPbFA): MACD(14,39,9) kesişimi 10 mum içinde 'taze' (ya da 5 mumluk zirve kırılımı devam girişi) + EMA99 trend & eğim + ADX(11)>20 + hacim>0.6×SMA22 → giriş (3 mum bekleme); acil stop 2.5 ATR; peak kâr ≥%0.5 olunca kârın %3'ünden fazlası geri verilirse çık (izleyen TP). process_orders_on_close."""
import numpy as np
from tv import gost
ISIM = "Universal Aggressive Trend MACD v3.3"; PINE_ID = "UVosPbFA"
PARAM = dict(hizli=14, yavas=39, sinyal=9, gecerli=10, devam=5, ema=99, egim=3, adx=11, adx_esik=20.0, vol=22, vol_c=0.6, atr=18, acil=2.5, tp_min=0.50, geri=3.0)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş (Almanca arayüz, 'Kerzen'); saatlik."
def sinyal(df, hizli, yavas, sinyal, gecerli, devam, ema, egim, adx, adx_esik, vol, vol_c, atr, acil, tp_min, geri):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    m = gost.ema(c, int(hizli)) - gost.ema(c, int(yavas)); s = gost.ema(m, int(sinyal)); hist = m - s
    bu = gost.crossover(np.nan_to_num(m), np.nan_to_num(s)); be = gost.crossunder(np.nan_to_num(m), np.nan_to_num(s)); bb, sb = gost.barssince(bu), gost.barssince(be)
    t = gost.ema(c, int(ema)); _, _, ad = gost.dmi(h, l, c, int(adx), int(adx)); a = gost.atr(h, l, c, int(atr)); hb = gost.sh(gost.highest(h, int(devam))); lb = gost.sh(gost.lowest(l, int(devam)))
    with np.errstate(invalid="ignore"):
        ok = (ad > adx_esik) & (v > gost.sma(v, int(vol))*vol_c)
        lt = (c > t) & (t > gost.sh(t, int(egim))); st = (c < t) & (t < gost.sh(t, int(egim)))
        lf = ((bb <= gecerli) & (m > s)) | ((m > s) & (hist > 0) & (c > hb)); sf = ((sb <= gecerli) & (m < s)) | ((m < s) & (hist < 0) & (c < lb))
        lg = ok & lt & lf; sh = ok & st & sf
    sg = gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0)
    return dict(sig=sg, sld=a*acil, tra=tp_min/100, tgv=geri/100, poc=True)
