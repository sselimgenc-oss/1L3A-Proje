"""MACD + 1G Stokastik (BtDUET5k, Skyrexio): MACD(12,26,9) sinyali yukarı keser, GÜNLÜK Stoch %K > %D ve K<80 → long; çıkış: giriş−1.75 ATR stop ya da (giriş+2.25 ATR aşılırsa) kapanış EMA20 altına inince. Günlük değerler bir önceki KAPANMIŞ gündür (lookahead yok)."""
import numpy as np
from tv import gost
ISIM = "MACD + günlük Stokastik (Skyrexio)"; PINE_ID = "BtDUET5k"
PARAM = dict(stoch=14, k_ust=80.0, iz_ema=20, sl=1.75, act=2.25)
TF = "45m"; EVREN = ["kripto"]; YON = 1
NEDEN = "PDF: BTCUSDT 45 dk (15 dk'dan türetilir); günlük stokastik önceki gün kapanışından."
def sinyal(df, stoch, k_ust, iz_ema, sl, act):
    h, l, c = df.h.values, df.l.values, df.c.values
    m = gost.ema(c, 12) - gost.ema(c, 26); sg = gost.ema(m, 9); te = gost.ema(c, int(iz_ema)); a = gost.atr(h, l, c, 14)
    def stk(d):
        k = gost.sma(gost.stoch(d.c.values, d.h.values, d.l.values, int(stoch)), 1); return np.c_[k, gost.sma(k, 3)]
    K = gost.htf(df, "1D", lambda d: stk(d)[:, 0]); D = gost.htf(df, "1D", lambda d: stk(d)[:, 1])
    with np.errstate(all="ignore"):
        s = gost.crossover(np.nan_to_num(m), np.nan_to_num(sg)) & (K > D) & (K < k_ust)
    return dict(sig=s.astype(float), sld=sl*a, acd=act*a, xla=c < te)
