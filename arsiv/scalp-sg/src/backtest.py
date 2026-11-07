"""Bar tabanlı backtest motoru (numba).

Kurallar:
- Sinyal bar kapanışında; giriş bir sonraki barın AÇILIŞINDA.
- Aynı barda hem stop hem hedef görülürse STOP kabul edilir (muhafazakâr).
- Seans arası boşlukta (> gap_min dakika) pozisyon son barın kapanışında kapatılır (gece taşıma yok).
- Maliyet: her yönde fiyatın `cost` oranı (komisyon + kayma); stop çıkışlarında ek `stop_slip`·ATR kayma.
- Sembol başına aynı anda tek pozisyon.
"""
import numpy as np
import pandas as pd
from numba import njit


@njit(cache=True)
def _simulate(o, h, l, c, sig, stop, tgt_dyn, atr, gap_after, rr, be, max_bars, cost, min_risk_cost, stop_slip):
    n = len(o)
    out = np.full((n, 6), np.nan)  # entry_idx, exit_idx, dir, entry, exit, R
    k = 0
    i = 0
    while i < n - 1:
        s = sig[i]
        if s == 0 or gap_after[i]:
            i += 1
            continue
        j = i + 1
        e = o[j]
        st = stop[i]
        risk = (e - st) * s
        if not (risk > 0) or risk < min_risk_cost * cost * e:
            i += 1
            continue
        tp = e + s * rr * risk if rr > 0 else np.nan
        cur_st = st
        moved = False
        ex = np.nan
        x = j
        while True:
            # bar x içinde
            hit_st = (l[x] <= cur_st) if s > 0 else (h[x] >= cur_st)
            if hit_st:
                # boşlukla açılış stopun ötesindeyse açılıştan dolum
                ex = min(o[x], cur_st) if s > 0 else max(o[x], cur_st)
                ex -= s * stop_slip * atr[i]  # stop emri kayması (bar içi sıçrama)
                break
            tlev = tp
            td = tgt_dyn[x - 1]
            if not np.isnan(td):
                if np.isnan(tlev):
                    tlev = td
                else:
                    tlev = min(tlev, td) if s > 0 else max(tlev, td)
            if not np.isnan(tlev):
                if (s > 0 and h[x] >= tlev) or (s < 0 and l[x] <= tlev):
                    ex = max(o[x], tlev) if s > 0 else min(o[x], tlev)
                    break
            if be > 0 and not moved:
                fav = (h[x] - e) if s > 0 else (e - l[x])
                if fav >= be * risk:
                    cur_st = e
                    moved = True
            if x - j + 1 >= max_bars or gap_after[x] or x == n - 1:
                ex = c[x]
                break
            x += 1
        net = s * (ex - e) - cost * (e + ex)
        out[k, 0] = j
        out[k, 1] = x
        out[k, 2] = s
        out[k, 3] = e
        out[k, 4] = ex
        out[k, 5] = net / risk
        k += 1
        i = x + 1 if x > i else i + 1
    return out[:k]


def run(m, p, cost, gap_min=30, min_risk_cost=3.0, stop_slip=0.05):
    t = m["time"]
    gap_after = (t.shift(-1) - t).dt.total_seconds().fillna(0).values > gap_min * 60
    res = _simulate(m["open"].values.astype(np.float64), m["high"].values.astype(np.float64),
                    m["low"].values.astype(np.float64), m["close"].values.astype(np.float64),
                    m["sig"].values.astype(np.int64), m["stop"].values.astype(np.float64),
                    m["tgt_dyn"].values.astype(np.float64), m["atr"].values.astype(np.float64), gap_after,
                    float(p.get("rr", 0.0)), float(p.get("be", 0.0)), int(p.get("max_bars", 24)),
                    float(cost), float(min_risk_cost), float(stop_slip))
    tr = pd.DataFrame(res, columns=["ei", "xi", "dir", "entry", "exit", "R"])
    if len(tr):
        tr["time"] = t.iloc[tr["ei"].astype(int).values].reset_index(drop=True)
        tr["bars"] = tr["xi"] - tr["ei"] + 1
    return tr


def stats(tr):
    if len(tr) == 0:
        return dict(n=0, win=np.nan, pf=np.nan, avgR=np.nan, totR=0.0, maxdd=0.0)
    R = tr["R"].values
    pos, neg = R[R > 0].sum(), -R[R < 0].sum()
    eq = np.cumsum(R)
    dd = np.max(np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq) if len(eq) else 0
    return dict(n=len(R), win=float((R > 0).mean()), pf=float(pos / neg) if neg > 0 else np.inf,
                avgR=float(R.mean()), totR=float(R.sum()), maxdd=float(dd))
