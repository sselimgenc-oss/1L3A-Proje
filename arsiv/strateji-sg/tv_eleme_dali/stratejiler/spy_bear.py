"""SPY Bear Regime Short (bA9UFcgj): kapanış SMA250'nin %2+ altında, SMA5 üstünde ve RSI(3) 70'i yukarı keserse short; kapanış SMA5 altına inince ya da SMA250 üstüne çıkınca çıkış. Yalnız short."""
import numpy as np
from tv import gost
ISIM = "SPY Bear Regime Short"; PINE_ID = "bA9UFcgj"
PARAM = dict(uzun=250, kisa=5, rsi=3, esik=70.0, bosluk=2.0)
TF = "1d"; EVREN = ["endeks", "abd"]; YON = -1
NEDEN = "SPY günlük (1994-2025) → ABD endeks ETF'leri + ABD hisseleri, günlük."
def sinyal(df, uzun, kisa, rsi, esik, bosluk):
    c = df.c.values; ml = gost.sma(c, int(uzun)); ms = gost.sma(c, int(kisa)); r = gost.rsi(c, int(rsi))
    with np.errstate(invalid="ignore"):
        e = (c < ml) & (c > ms) & gost.crossover(np.nan_to_num(r), np.full(len(c), esik)) & (c <= ml*(1-bosluk/100))
        x = (c < ms) | (c > ml)
    return dict(sig=-e.astype(float), xs=x)
