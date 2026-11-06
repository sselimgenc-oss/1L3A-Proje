"""Ultimate Ichimoku Cloud (boHD0HzE): tenkan/kijun kesişimi + pozitif bulut + fiyat bulut üstünde + chikou + fiyat>tenkan → long (tersi short); kijun/tenkan ters kesişiminde çıkış. process_orders_on_close=true: emir sinyal mumunun kapanışında dolar."""
import numpy as np
from tv import gost
ISIM = "Ichimoku (Ultimate)"; PINE_ID = "boHD0HzE"
PARAM = dict(donusum=9, taban=26, bulut=52, kaydirma=26)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük (Ichimoku klasik)."
def _don(h, l, n): return (gost.lowest(l, n) + gost.highest(h, n))/2
def sinyal(df, donusum, taban, bulut, kaydirma):
    h, l, c = df.h.values, df.l.values, df.c.values; d = int(kaydirma)
    cv, bl = _don(h, l, int(donusum)), _don(h, l, int(taban)); sa = (cv + bl)/2; sb = _don(h, l, int(bulut))
    sa_, sb_ = gost.sh(sa, d-1), gost.sh(sb, d-1); chik = gost.sh(c, d+1)
    with np.errstate(invalid="ignore"):
        le = gost.crossover(np.nan_to_num(cv), np.nan_to_num(bl)) & (sa_ > sb_) & (c > sa_) & (c > sb_) & (c > chik) & (c > cv)
        se = gost.crossunder(np.nan_to_num(cv), np.nan_to_num(bl)) & (sa_ < sb_) & (c < sa_) & (c < sb_) & (c < chik) & (c < bl)
    xl = gost.crossunder(np.nan_to_num(cv), np.nan_to_num(bl)); xs = gost.crossover(np.nan_to_num(cv), np.nan_to_num(bl))
    return dict(sig=gost.flipsig(le, se), xl=xl, xs=xs, poc=True)
