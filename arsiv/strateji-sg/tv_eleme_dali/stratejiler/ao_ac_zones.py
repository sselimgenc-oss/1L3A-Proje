"""AO/AC Trading Zones (Tkrjao7P, Skyrexio): yeşil bar serisi (kapanış>Alligator dişi, AC ve AO yükseliyor, kapanış>EMA100) 2–6 mum sürerken ve kapanış önceki kapanıştan yüksekse piyasa girişi; açık pozisyon sayısına göre en çok 5 kademe ekleme (entry1..5); trend aşağı dönünce ya da yeşil serinin 5. barının dibi kırılınca hepsi kapanır."""
import numpy as np
from numba import njit
from tv import gost
from tv.stratejiler._skyr_kademe import tabanlar
ISIM = "AO/AC Trading Zones"; PINE_ID = "Tkrjao7P"
PARAM = dict(ema=100)
TF = "4h"; EVREN = ["kripto"]; YON = 1
NEDEN = "PDF: BTCUSDT 4 saat."
@njit(cache=True)
def _sim(c, l, cond, tr, K):
    n = len(c); sg = np.zeros((K, n)); xl = np.zeros(n, np.bool_); cnt = 0; g = 0; stp = np.nan
    for i in range(1, n):
        c0 = cnt
        g = g+1 if cond[i] else 0
        if g == 5: stp = l[i]
        if cnt == 0: stp = np.nan
        cc = (tr[i-1] == 1 and tr[i] == -1) or ((not np.isnan(stp)) and l[i] < stp)
        kapat = cnt > 0 and cc
        if kapat: xl[i] = True; cnt = 0; stp = np.nan
        if (not kapat) and c0 < K and c[i] > c[i-1] and g >= 2 and g < 7:
            sg[c0, i] = 1.0; cnt = c0 + 1
    return sg, xl
def sinyal(df, ema):
    b = tabanlar(df, ema); ao = b["ao"]; ac = ao - gost.sma(ao, 5); c = b["c"]
    with np.errstate(invalid="ignore"): cond = (c > b["teeth"]) & (ac > gost.sh(ac)) & (ao > gost.sh(ao)) & (c > b["ema"])
    sg, xl = _sim(c, b["l"], np.nan_to_num(cond.astype(float)) > 0, b["tr"], 5)
    return dict(bacaklar=[dict(sig=sg[k], xl=xl) for k in range(5)])
