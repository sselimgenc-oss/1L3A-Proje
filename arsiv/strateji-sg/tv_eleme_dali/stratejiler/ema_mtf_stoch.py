"""EMA Trend + MTF Stochastic (o9dV6uWc): EMA38>EMA62 trendinde, üst zaman dilimi (4s) Stoch K 50'yi yukarı keserken ve yerel K>D → long (aşağı için tersi); stop 1.5 ATR, 1.5R'den sonra ATR izleyen stop, üst TF D çizgisi 80'i aşağı keserse / trend dönerse / 60 mumda çık. (1R'de başa-baş stopu modellenmedi.)"""
import numpy as np
from tv import gost
ISIM = "EMA Trend + MTF Stochastic"; PINE_ID = "o9dV6uWc"
PARAM = dict(ef=38, es=62, ln=11, ust=80, alt=20, atr=14, sl=1.5, tr_r=1.5, tr_m=1.5)
TF = "1h"; EVREN = ["kripto", "abd", "emtia"]
NEDEN = "Betikte 1s→4s üst zaman dilimi eşlemesi var; saatlik grafik."
def _st(d, ln):
    k = gost.sma(gost.stoch(d.c.values, d.h.values, d.l.values, int(ln)), 3); dd = gost.sma(k, 3)
    return np.c_[gost.linreg(k, int(ln), 0), gost.linreg(dd, int(ln), 0)]
def sinyal(df, ef, es, ln, ust, alt, atr, sl, tr_r, tr_m):
    h, l, c = df.h.values, df.l.values, df.c.values; n = len(c)
    k = gost.sma(gost.stoch(c, h, l, int(ln)), 3); d = gost.sma(k, 3)
    mk = gost.htf(df, "4h", lambda x: _st(x, ln)[:, 0]); md = gost.htf(df, "4h", lambda x: _st(x, ln)[:, 1])
    up = gost.ema(c, int(ef)) > gost.ema(c, int(es)); dn = gost.ema(c, int(ef)) < gost.ema(c, int(es)); a = gost.atr(h, l, c, int(atr))
    f50 = np.full(n, 50.0)
    with np.errstate(invalid="ignore"):
        lg = gost.crossover(np.nan_to_num(mk), f50) & (k > 50) & (k > gost.sh(k)) & (k > d) & (mk > md) & up
        sh = gost.crossunder(np.nan_to_num(md), f50) & (k < 50) & (k < gost.sh(k)) & (k < d) & (mk < md) & dn
        xl = gost.crossunder(np.nan_to_num(md), np.full(n, float(ust))) | dn; xs = gost.crossover(np.nan_to_num(mk), np.full(n, float(alt))) | up
    return dict(sig=gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0), sld=a*sl, xl=xl, xs=xs, taa=a*sl*tr_r, toa=a*tr_m, maxhold=60)
