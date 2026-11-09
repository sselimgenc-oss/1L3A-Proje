"""Numba tabanlı 1h işlem simülatörü ve performans metrikleri.

Kurallar (muhafazakâr):
- Sinyal i. mumun kapanışında oluşur, giriş i+1. mumun açılışından yapılır.
- Aynı mumda hem stop hem hedef görülürse önce STOP varsayılır.
- Açılış stop seviyesinin ötesinde gelirse (gap) çıkış açılış fiyatından olur.
- Stop/iz süren stop güncellemeleri mum kapanışında yapılır, sonraki mumdan itibaren geçerlidir.
- Komisyon+kayma her işlem tarafı için COST oranında, funding saatlik olarak uygulanır.
"""
import numpy as np
import pandas as pd
from numba import njit

COST = 0.0007  # taraf başına: 0.05% taker + 0.02% kayma


@njit(cache=True)
def _simulate(o, h, l, c, side, sl_dist, tp1_R, tp1_frac, tp2_R, be_R, trail_atr, trail_k, trail_start_R,
              exl, exs, max_bars, funding, cost, loss_delay, skip_after_win):
    n = len(o)
    out = np.empty((n, 11))  # entry_i, exit_i, side, entry, R_gross, R_net, sl_pct, reason, stop, remaining, exit_px
    # reason: 1=stop, 2=hedef, 3=çıkış sinyali/süre, 4=AÇIK (son kapanışla değerlendi)
    k = 0
    i = 0
    blocked_until = -1   # Davey: kayıp sonrası bekleme
    last_win = False     # Pruitt/Turtle LTLF: son işlem kazandıysa sıradaki sinyali atla
    while i < n - 1:
        s = side[i]
        if s == 0 or not (sl_dist[i] > 0) or i < blocked_until:
            i += 1
            continue
        if skip_after_win and last_win:
            last_win = False
            i += 1
            continue
        e_i = i + 1
        entry = o[e_i]
        risk = sl_dist[i]
        stop = entry - s * risk
        t1 = entry + s * risk * tp1_R[i] if tp1_frac[i] > 0 else np.nan
        t2 = entry + s * risk * tp2_R[i]
        remaining = 1.0
        realized = 0.0  # R cinsinden, ağırlıklı
        fund = 0.0
        tp1_done = tp1_frac[i] <= 0
        best = entry
        reason = 0
        j = e_i
        exit_i = -1
        px = entry
        while j < n:
            fund += funding[j] * s * remaining  # pozitif funding long için maliyet; kalan pozisyon kadar
            # --- çıkış kontrolleri (bar içi) ---
            if s == 1:
                if l[j] <= stop:
                    px = min(stop, o[j])
                    realized += remaining * (px - entry) / risk
                    remaining = 0.0; reason = 1; exit_i = j; break
                if (not tp1_done) and h[j] >= t1:
                    px = max(t1, o[j])
                    realized += tp1_frac[i] * (px - entry) / risk
                    remaining -= tp1_frac[i]; tp1_done = True
                if h[j] >= t2:
                    px = max(t2, o[j])
                    realized += remaining * (px - entry) / risk
                    remaining = 0.0; reason = 2; exit_i = j; break
            else:
                if h[j] >= stop:
                    px = max(stop, o[j])
                    realized += remaining * (entry - px) / risk
                    remaining = 0.0; reason = 1; exit_i = j; break
                if (not tp1_done) and l[j] <= t1:
                    px = min(t1, o[j])
                    realized += tp1_frac[i] * (entry - px) / risk
                    remaining -= tp1_frac[i]; tp1_done = True
                if l[j] <= t2:
                    px = min(t2, o[j])
                    realized += remaining * (entry - px) / risk
                    remaining = 0.0; reason = 2; exit_i = j; break
            # --- kapanışta çıkış sinyali / süre ---
            sig_exit = (s == 1 and exl[j]) or (s == -1 and exs[j]) or (j - e_i + 1 >= max_bars)
            if sig_exit or j == n - 1:
                if j + 1 < n:
                    px = o[j + 1]; exit_i = j + 1
                else:
                    px = c[j]; exit_i = j
                open_rem = remaining
                realized += remaining * s * (px - entry) / risk
                remaining = 0.0
                if sig_exit and j + 1 < n:
                    reason = 3
                elif sig_exit:
                    reason = 5  # son mumda çıkış sinyali: bir sonraki açılışta kapanacak
                    remaining = open_rem
                else:
                    reason = 4  # pozisyon hâlâ açık
                    remaining = open_rem
                break
            # --- kapanışta stop güncelle ---
            if s == 1:
                best = max(best, h[j])
            else:
                best = min(best, l[j])
            mfe_R = s * (best - entry) / risk
            if be_R > 0 and mfe_R >= be_R:
                be = entry + s * entry * cost * 2
                stop = max(stop, be) if s == 1 else min(stop, be)
            if trail_k > 0 and mfe_R >= trail_start_R:
                ts = best - s * trail_k * trail_atr[j]
                stop = max(stop, ts) if s == 1 else min(stop, ts)
            j += 1
        if exit_i < 0:
            break
        sl_pct = risk / entry
        cost_R = 2 * cost / sl_pct
        fund_R = fund / sl_pct
        out[k, 0] = e_i; out[k, 1] = exit_i; out[k, 2] = s; out[k, 3] = entry
        out[k, 4] = realized; out[k, 5] = realized - cost_R - fund_R; out[k, 6] = sl_pct; out[k, 7] = reason
        out[k, 8] = stop; out[k, 9] = remaining; out[k, 10] = px
        k += 1
        net = realized - cost_R - fund_R
        last_win = net > 0
        if net <= 0 and loss_delay > 0:
            blocked_until = exit_i + loss_delay
        i = exit_i  # çıkış mumunun kapanışından itibaren yeni sinyal alınabilir
    return out[:k]


def _arr(x, n, dtype=np.float64):
    if np.isscalar(x):
        return np.full(n, x, dtype=dtype)
    return np.asarray(x, dtype=dtype)


def simulate(df, side, sl_dist, tp1_R=1.0, tp1_frac=0.0, tp2_R=np.inf, be_R=0.0, trail_atr=None, trail_k=0.0,
             trail_start_R=0.0, exit_long=None, exit_short=None, max_bars=10**9, funding=None, cost=COST,
             loss_delay=0, skip_after_win=False):
    n = len(df)
    o, h, l, c = (df[x].values.astype(np.float64) for x in ("open", "high", "low", "close"))
    side = np.nan_to_num(_arr(side, n)).astype(np.int64)
    sl = np.nan_to_num(_arr(sl_dist, n), nan=0.0)
    res = _simulate(o, h, l, c, side, sl, _arr(tp1_R, n), _arr(tp1_frac, n), _arr(tp2_R, n), float(be_R),
                    np.nan_to_num(_arr(trail_atr if trail_atr is not None else 0.0, n)), float(trail_k), float(trail_start_R),
                    _arr(exit_long if exit_long is not None else False, n, np.bool_),
                    _arr(exit_short if exit_short is not None else False, n, np.bool_),
                    int(max_bars), _arr(funding if funding is not None else 0.0, n), float(cost),
                    int(loss_delay), bool(skip_after_win))
    t = pd.DataFrame(res, columns=["entry_i", "exit_i", "side", "entry", "R_gross", "R", "sl_pct", "reason", "stop", "remaining", "exit_px"])
    if len(t):
        t["entry_time"] = df.index[t["entry_i"].astype(int)]
        t["exit_time"] = df.index[t["exit_i"].astype(int)]
    return t


def metrics(trades, risk=0.01, max_lev=5.0, start=None, end=None):
    """Portföy metrikleri. Her işlem öz sermayenin `risk` kadarını riske eder
    (kaldıraç max_lev ile sınırlı). Getiriler çıkış zamanına göre bileşiklenir."""
    t = trades
    if start is not None:
        t = t[t["entry_time"] >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        t = t[t["entry_time"] < pd.Timestamp(end, tz="UTC")]
    if len(t) == 0:
        return dict(trades=0)
    lev = risk / t["sl_pct"]
    scale = np.minimum(1.0, max_lev / lev)
    r_eff = t["R"] * scale
    ret = (r_eff * risk).values
    order = np.argsort(t["exit_time"].values, kind="stable")
    eq = np.cumprod(1 + ret[order])
    peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    dd = (eq / peak - 1).min()
    wins = t["R"] > 0
    gp = t.loc[wins, "R"].sum(); gl = -t.loc[~wins, "R"].sum()
    years = max((t["exit_time"].max() - t["entry_time"].min()).days / 365.25, 1e-9)
    daily = pd.Series(ret[order], index=t["exit_time"].values[order]).groupby(pd.Grouper(freq="1D")).sum()
    sharpe = daily.mean() / daily.std() * np.sqrt(365) if daily.std() > 0 else np.nan
    return dict(trades=int(len(t)), win_rate=round(float(wins.mean()) * 100, 2), pf=round(float(gp / gl) if gl > 0 else np.inf, 3),
                avg_R=round(float(t["R"].mean()), 3), total_R=round(float(t["R"].sum()), 1),
                cagr=round(float(eq[-1] ** (1 / years) - 1) * 100, 1), total_ret=round(float(eq[-1] - 1) * 100, 1),
                max_dd=round(float(dd) * 100, 1), sharpe=round(float(sharpe), 2),
                avg_bars=round(float((t["exit_i"] - t["entry_i"]).mean()), 1), longs=int((t["side"] > 0).sum()))
