"""BCH Heikin Ashi RSI Fade Short (nuqVC5F7, 3Commas): RSI(100) > 46 ve en az 7 ardışık yükselen Heikin Ashi mumu → short; sabit %2.1 hedef, %2.5 stop (ortalama alım yok). Yalnız short."""
import numpy as np
from tv import gost
ISIM = "HA RSI Fade Short (3Commas)"; PINE_ID = "nuqVC5F7"
PARAM = dict(rsi=100, esik=46.0, seri=7, tp=2.1, sl=2.5)
TF = "15m"; EVREN = ["kripto"]; YON = -1
NEDEN = "PDF: BCHUSDT 15 dk."
def ha(o, h, l, c):
    hc = (o+h+l+c)/4; ho = np.empty(len(c)); ho[0] = (o[0]+c[0])/2
    for i in range(1, len(c)): ho[i] = (ho[i-1]+hc[i-1])/2
    return ho, hc
def sinyal(df, rsi, esik, seri, tp, sl):
    o, h, l, c = df.o.values, df.h.values, df.l.values, df.c.values
    ho, hc = ha(o, h, l, c); bull = hc > ho
    run = np.zeros(len(c)); k = 0
    for i in range(len(c)): k = k+1 if bull[i] else 0; run[i] = k
    r = gost.rsi(c, int(rsi))
    with np.errstate(invalid="ignore"): s = (r > esik) & (run >= seri)
    return dict(sig=-s.astype(float), slp=sl/100, tpp=tp/100)
