"""KST Strategy (Pv1GvUVs, Skyrexio): KST çizgisi sinyali yukarı keser, kapanış > LSMA(200) ve > Alligator çenesi (SMMA13[8]) ve Choppiness Index(14) < 50 → long; stop = sinyal mumu dibi − 1.5 ATR, hedef = kapanış + 3.5 ATR. Yalnız long."""
import numpy as np
from tv import gost
ISIM = "KST (Skyrexio)"; PINE_ID = "Pv1GvUVs"
PARAM = dict(lsma=200, chop=14, chop_esik=50.0, sl=1.5, tp=3.5)
TF = "1h"; EVREN = ["kripto"]; YON = 1
NEDEN = "PDF: BTCUSDT 1 saat."
def smma(x, n): return gost.rma(x, n)
def sinyal(df, lsma, chop, chop_esik, sl, tp):
    h, l, c = df.h.values, df.l.values, df.c.values
    def sr(rl, sn): 
        with np.errstate(all="ignore"): return gost.sma((c/gost.sh(c, rl)-1)*100, sn)
    kst = sr(10, 10) + 2*sr(15, 10) + 3*sr(20, 10) + 4*sr(30, 15); sg = gost.sma(kst, 9)
    jaw = gost.sh(smma((h+l)/2, 13), 8)
    a1 = np.r_[h[0]-l[0], np.maximum.reduce([h[1:]-l[1:], abs(h[1:]-c[:-1]), abs(l[1:]-c[:-1])])]
    with np.errstate(all="ignore"):
        ci = 100*np.log10(gost.rsum(a1, int(chop))/(gost.highest(h, int(chop))-gost.lowest(l, int(chop))))/np.log10(chop)
        flt = gost.linreg(c, int(lsma), 0)
        s = gost.crossover(np.nan_to_num(kst), np.nan_to_num(sg)) & (c > flt) & (c > jaw) & (ci < chop_esik)
    a = gost.atr(h, l, c, 14)
    return dict(sig=s.astype(float), sl=l - sl*a, tp=c + tp*a)
