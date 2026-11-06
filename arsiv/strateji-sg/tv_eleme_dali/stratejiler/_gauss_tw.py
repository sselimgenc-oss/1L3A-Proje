"""TRADLEWARE Gaussian Channel + StochRSI (ortak çekirdek). Long: filtre yükseliyor, kapanış üst bandı aşıyor, StochRSI K>80 ya da <25, (200 SMA rejimi), (yeşil mum); çıkış: kapanış üst bandın altına iner ya da filtre düşer; stop = alt band."""
import numpy as np
from tv import gost
from tv.stratejiler.gaussian import _pole
def cekirdek(df, per, mult, rsi_ust, rsi_alt, rejim, yesil, kutup=4, buf=0.0, sma=200):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values; N = int(kutup)
    beta = (1 - np.cos(4*np.arcsin(1)/per))/(1.414**(2/N) - 1); alpha = -beta + np.sqrt(beta*beta + 2*beta)
    f = _pole((h+l+c)/3, alpha, N); ft = _pole(gost.tr(h, l, c), alpha, N); hb, lb = f+ft*mult, f-ft*mult
    r = gost.rsi(c, 14); k = gost.sma(gost.stoch(r, r, r, 14), 3); fp = gost.sh(f)
    with np.errstate(invalid="ignore"):
        lg = (f > fp) & (c > hb*(1+buf/100)) & ((k > rsi_ust) | (k < rsi_alt))
        if rejim: lg &= c > gost.sma(c, int(sma))
        if yesil: lg &= c > o
        warm = np.arange(len(c)) > per*2
        xl = (c < hb) | (f < fp)
    return dict(sig=(lg & warm).astype(float), xl=xl, dyl=lb)
