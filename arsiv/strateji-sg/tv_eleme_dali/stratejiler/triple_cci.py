"""Triple CCI + MFI (PETNavGq, Skyrexio): hızlı CCI(14) 0'ı yukarı keser, kapanış > EMA50, CCI25>0, CCI50>0, MFI>50 → long; çıkış: giriş−1.75 ATR stop ya da (giriş+2.25 ATR aşılırsa) kapanış EMA20 altına inince. Yalnız long. (ATR giriş anındaki değerle sabit alındı.)"""
import numpy as np
from tv import gost
ISIM = "Triple CCI + MFI (Skyrexio)"; PINE_ID = "PETNavGq"
PARAM = dict(cci_h=14, cci_o=25, cci_y=50, mfi=14, ema=50, iz_ema=20, sl=1.75, act=2.25)
TF = "2h"; EVREN = ["kripto"]; YON = 1
NEDEN = "PDF: BTCUSDT 2 saat."
def cci(x, n):
    m = gost.sma(x, n)
    with np.errstate(all="ignore"):
        md = np.array([np.nan]*len(x)); 
        from numpy.lib.stride_tricks import sliding_window_view as sw
        if len(x) >= n:
            w = sw(x, n); md[n-1:] = np.abs(w - w.mean(axis=1, keepdims=True)).mean(axis=1)
        return (x-m)/(0.015*md)
def sinyal(df, cci_h, cci_o, cci_y, mfi, ema, iz_ema, sl, act):
    h, l, c, v = df.h.values, df.l.values, df.c.values, df.v.values
    tp = (h+l+c)/3; f = cci(tp, int(cci_h)); m = cci(tp, int(cci_o)); s = cci(tp, int(cci_y)); mf = gost.mfi(h, l, c, v, int(mfi))
    e = gost.ema(c, int(ema)); te = gost.ema(c, int(iz_ema)); a = gost.atr(h, l, c, 14)
    with np.errstate(all="ignore"):
        sg = gost.crossover(np.nan_to_num(f), np.zeros(len(c))) & (c > e) & (m > 0) & (s > 0) & (mf > 50)
        xla = c < te
    return dict(sig=sg.astype(float), sld=sl*a, acd=act*a, xla=xla)
