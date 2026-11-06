"""3% max drawdown (nRklAGPI): QQQ'da long-only makro sistem. Giriş: SPY dibi 4 gün üst üste EMA21 üstü, QQQ dibi EMA10/21 üstü, son 3 gün üst üste düşüş yok, SPY ADX(13)>16 — ya da BTC yükseliş + SPY>SMA7 yardımı; SPY son 116 mumda ATH yapmışsa. Çıkış: zarardaki işlemde QQQ<EMA21 ve SPY<SMA7; kârdaki işlemde (SPY SMA7<SMA107[1] ve zayıf) ya da (%3.5 stop altı + SMA50 altı). (Betikteki çöküş-bekleme mantığı, eşik %20 yüzde değil oran olarak yazıldığından hiç tetiklenmez; çıkarıldı.)"""
import numpy as np, pandas as pd
from numba import njit
from tv import gost, veri
ISIM = "QQQ makro (SPY+BTC)"; PINE_ID = "nRklAGPI"
PARAM = dict(ath_bar=116, sl=3.5)
TF = "1d"; SEMBOL = ["QQQ"]; YON = 1
NEDEN = "Betik QQQ günlük (SPY, BTC, SPX ADX dış veri); SPX yerine SPY."
_V = {}
@njit(cache=True)
def _dur(enh, ex_fast, ex_norm_a, ex_norm_b, qc, ql, q50, ath_ok, o, sl, n):
    sig = np.zeros(n); xl = np.zeros(n, np.bool_); pos = False; qe = np.nan; stp = np.nan
    for i in range(n-1):
        was = pos
        if pos:
            lose = qc[i] < qe; win = qc[i] >= qe
            stop_hit = ql[i] < stp; init = stop_hit and ql[i] < q50[i]
            e = (lose and ex_fast[i]) or (win and (ex_norm_a[i] or init))
            if e: xl[i] = True; pos = False
        if (not was) and enh[i] and ath_ok[i]:
            sig[i] = 1.0; pos = True; qe = qc[i+1]; stp = qe*(1-sl/100)
    return sig, xl
def sinyal(df, ath_bar, sl):
    if "s" not in _V: _V["s"] = veri.al("SPY", "1d"); _V["b"] = veri.al("BTC", "1d")
    ix = df.index.normalize()
    def al(d, col):
        x = d[col].copy(); x.index = x.index.normalize(); x = x[~x.index.duplicated()]; return x.reindex(ix, method="ffill").values
    sc, sl_, sh_ = al(_V["s"], "c"), al(_V["s"], "l"), al(_V["s"], "h"); bc = al(_V["b"], "c"); bl = al(_V["b"], "l")
    qc, ql, c = df.c.values, df.l.values, df.c.values; n = len(c)
    s7, s107, s21, s200 = gost.sma(sc, 7), gost.sma(sc, 107), gost.ema(sc, 21), gost.ema(sc, 200)
    q10, q21, q50 = gost.ema(qc, 10), gost.ema(qc, 21), gost.sma(qc, 50)
    b10, b21 = gost.ema(bc, 10), gost.ema(bc, 21)
    _, _, adx = gost.dmi(sh_, sl_, sc, 13, 13)
    with np.errstate(invalid="ignore"):
        btc_bull = (b10 > b21) & (bl > b21) & (bc > gost.sh(bc)); assist = btc_bull & (sc > s7)
        spx4 = (sl_ > s21) & (gost.sh(sl_, 1) > gost.sh(s21, 1)) & (gost.sh(sl_, 2) > gost.sh(s21, 2)) & (gost.sh(sl_, 3) > gost.sh(s21, 3))
        lowq = (ql > q10) & (ql > q21); notweak = ~((qc < gost.sh(qc, 1)) & (qc < gost.sh(qc, 2)) & (qc < gost.sh(qc, 3)))
        cond = spx4 & lowq & notweak & (adx > 16); enh = cond | assist
        ex_fast = (qc < q21) & (sc < s7)
        trend = (s7 < gost.sh(s107, 1)) & (sc < s7) & (qc < q21)
    ath = np.maximum.accumulate(np.nan_to_num(sc)); bars = np.zeros(n); k = 0
    for i in range(n):
        k = 0 if sc[i] >= ath[i] else k+1; bars[i] = k
    ath_ok = ~(bars >= ath_bar)
    sg, xl = _dur(np.nan_to_num(enh.astype(float)) > 0, np.nan_to_num(ex_fast.astype(float)) > 0, np.nan_to_num(trend.astype(float)) > 0, np.zeros(n, bool), qc, ql, np.nan_to_num(q50, nan=-1.0), ath_ok, df.o.values, float(sl), n)
    return dict(sig=sg, xl=xl)
