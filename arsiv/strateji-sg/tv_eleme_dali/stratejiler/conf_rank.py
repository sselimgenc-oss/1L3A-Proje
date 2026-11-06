"""Confluence Rank Trend (LcA4mcE6): trend (EMA55/233), RSI momentum, verimlilik oranı, oynaklık yüzdeliği ve göreli hacimden 0–100 skor; skor ≥85'e yeni çıkınca giriş (long/short), 3 ATR izleyen stop, skor <35 olunca çık."""
import numpy as np
from tv import gost
ISIM = "Confluence Rank Trend"; PINE_ID = "LcA4mcE6"
PARAM = dict(hizli=55, yavas=233, rsi=14, er_len=20, er_full=0.40, pct_len=200, vol_lo=20.0, vol_hi=85.0, vol_len=20, giris=85.0, cikis=35.0, atr=14, stop=3.0)
TF = "1d"; EVREN = ["kripto", "abd", "bist", "emtia"]
NEDEN = "Zaman dilimi belirtilmemiş; günlük, tüm pazarlar."
def cl(x): return np.clip(x, 0.0, 1.0)
def sinyal(df, hizli, yavas, rsi, er_len, er_full, pct_len, vol_lo, vol_hi, vol_len, giris, cikis, atr, stop):
    o, h, l, c, v = df.o.values, df.h.values, df.l.values, df.c.values, df.v.values; n = len(c)
    ef, es = gost.ema(c, int(hizli)), gost.ema(c, int(yavas)); r = gost.rsi(c, int(rsi)); chg = c - gost.sh(c, int(er_len))
    path = gost.rsum(np.r_[0.0, np.abs(np.diff(c))], int(er_len)); a = gost.atr(h, l, c, int(atr)); ap = np.nan_to_num(gost.percentrank(a, int(pct_len)), nan=50.0)
    vm = gost.sma(v, int(vol_len)); hv = np.nan_to_num(vm) > 0; rv = np.where(hv, v/np.where(vm == 0, 1, vm), 0.0)
    with np.errstate(all="ignore"):
        er = np.where(path > 0, np.abs(chg)/path, 0.0)
        tL = (c > es)*10.0 + (ef > es)*10.0; tS = (c < es)*10.0 + (ef < es)*10.0
        mL = 20*cl((r-50)/20); mS = 20*cl((50-r)/20); eL = np.where(chg > 0, 20*cl(er/er_full), 0.0); eS = np.where(chg < 0, 20*cl(er/er_full), 0.0)
        vr = np.where(ap < vol_lo, 20*ap/vol_lo, np.where(ap > vol_hi, 20*cl((100-ap)/(100-vol_hi)), 20.0))
        pL = np.where(~hv, 10.0, np.where(c > o, 20*cl(rv-0.5), 0.0)); pS = np.where(~hv, 10.0, np.where(c < o, 20*cl(rv-0.5), 0.0))
        sL = np.nan_to_num(tL+mL+eL+vr+pL); sS = np.nan_to_num(tS+mS+eS+vr+pS)
    warm = np.arange(n) > max(yavas, pct_len)
    lg = warm & (sL >= giris) & (gost.sh(sL) < giris); sh = warm & (sS >= giris) & (gost.sh(sS) < giris) & ~lg
    sd = stop*a
    return dict(sig=gost.flipsig(lg, sh)*np.where(lg | sh, 1, 0), dyl=c-sd, dys=c+sd, xl=sL < cikis, xs=sS < cikis)
