"""Double CCI + Hull MA (3fea8k4Z, Skyrexio): yüksek, HMA(34) üstüne çıkar, kapanış > HMA, CCI25>0 ve CCI50>0 → long; çıkış: giriş−1.75 ATR stop ya da (giriş+2.25 ATR aşılırsa) kapanış EMA20 altına inince. Yalnız long."""
import numpy as np
from tv import gost
from tv.stratejiler.triple_cci import cci
ISIM = "Double CCI + HMA (Skyrexio)"; PINE_ID = "3fea8k4Z"
PARAM = dict(cci_h=25, cci_y=50, hma=34, iz_ema=20, sl=1.75, act=2.25)
TF = "2h"; EVREN = ["kripto"]; YON = 1
NEDEN = "PDF: BTCUSDT 2 saat."
def sinyal(df, cci_h, cci_y, hma, iz_ema, sl, act):
    h, l, c = df.h.values, df.l.values, df.c.values
    tp = (h+l+c)/3; f = cci(tp, int(cci_h)); s = cci(tp, int(cci_y)); te = gost.ema(c, int(iz_ema)); a = gost.atr(h, l, c, 14)
    hm = gost.wma(2*gost.wma(c, int(hma)//2) - gost.wma(c, int(hma)), int(np.floor(np.sqrt(hma))))
    with np.errstate(all="ignore"):
        sg = gost.crossover(h, np.nan_to_num(hm, nan=1e18)) & (c > hm) & (f > 0) & (s > 0)
    return dict(sig=sg.astype(float), sld=sl*a, acd=act*a, xla=c < te)
