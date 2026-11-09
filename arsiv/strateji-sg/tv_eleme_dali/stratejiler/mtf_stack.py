"""MTF Momentum Stack + Stochastic (8Ti8z8QO): 15dk/1s/4s RSI skorları (RSI>55 → +1, <45 → −1) aynı yöndeyse (3/−3) ve 15dk Stoch K/D kesişimi (+ 4s Stoch K>D, linreg yumuşatmalı) → giriş; stop 1.5 ATR, hedef 3 ATR; skor ters dönünce çık. (pyramiding=3 ek girişleri tek giriş olarak alındı.) Üst TF değerleri son kapanmış mumdan (lookahead yok)."""
import numpy as np
from tv import gost
ISIM = "MTF Momentum Stack"; PINE_ID = "8Ti8z8QO"
PARAM = dict(rsi=14, bant=5.0, sto=11, sl=1.5, tp=3.0, lr=11)
TF = "15m"; EVREN = ["kripto"]
NEDEN = "Betikte TF1=15 dk (grafik), TF2=1s, TF3=4s; 15 dk kripto."
def _score(d, rsi, bant):
    r = gost.rsi(d.c.values, int(rsi)); return np.where(r > 50+bant, 1.0, np.where(r < 50-bant, -1.0, 0.0))
def sinyal(df, rsi, bant, sto, sl, tp, lr):
    h, l, c = df.h.values, df.l.values, df.c.values
    s1 = _score(df, rsi, bant); s2 = np.nan_to_num(gost.htf(df, "1h", lambda d: _score(d, rsi, bant))); s3 = np.nan_to_num(gost.htf(df, "4h", lambda d: _score(d, rsi, bant))); al = s1+s2+s3
    k = gost.sma(gost.stoch(c, h, l, int(sto)), 3); d = gost.sma(k, 3)
    def kd(x, j): kk = gost.sma(gost.stoch(x.c.values, x.h.values, x.l.values, int(sto)), 3); return kk if j == 0 else gost.sma(kk, 3)
    mk = gost.linreg(gost.htf(df, "4h", lambda x: kd(x, 0)), int(lr), 0); md = gost.linreg(gost.htf(df, "4h", lambda x: kd(x, 1)), int(lr), 0)
    kn, dn = np.nan_to_num(k), np.nan_to_num(d); a = gost.atr(h, l, c, 14)
    with np.errstate(invalid="ignore"):
        lg = (al == 3) & gost.crossover(kn, dn) & (k < 80) & (mk > md); sh = (al == -3) & gost.crossunder(kn, dn) & (k > 20) & (mk < md)
    return dict(sig=gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0), sld=a*sl, tpd=a*tp, xl=al == -3, xs=al == 3, poc=True)
