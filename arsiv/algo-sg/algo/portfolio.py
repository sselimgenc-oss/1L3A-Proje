"""Olay tabanlı portföy simülasyonu: eşzamanlı pozisyon sınırı, işlem başına sabit risk,
kaldıraç sınırı. Pozisyon büyüklüğü girişteki öz sermayeye göre belirlenir."""
import heapq
import numpy as np
import pandas as pd


def simulate_portfolio(trades, risk=0.005, max_open=10, max_lev_total=5.0, start_equity=1.0, return_details=False):
    """Açık pozisyonlar (reason 4/5) slot ve kaldıraç kullanır ama gerçekleşen öz sermayeye eklenmez."""
    t = trades.sort_values("entry_time").reset_index(drop=True)
    eq = start_equity
    open_heap = []  # (exit_time, idx, lev, pnl_usd, sym, is_open)
    open_syms = set()
    lev_used = 0.0
    curve = []
    taken = np.zeros(len(t), bool)
    eq_entry = np.full(len(t), np.nan); lev_arr = np.full(len(t), np.nan); pnl_arr = np.full(len(t), np.nan)
    is_open_col = t["reason"].isin([4, 5]).values if "reason" in t else np.zeros(len(t), bool)
    for i, r in t.iterrows():
        while open_heap and open_heap[0][0] <= r.entry_time:
            xt, j, lev, pnl, sym, op = heapq.heappop(open_heap)
            if not op:
                eq += pnl
            lev_used -= lev; open_syms.discard(sym)
            curve.append((xt, eq))
        if len(open_heap) >= max_open or r.sym in open_syms:
            continue
        lev = risk / r.sl_pct
        if lev_used + lev > max_lev_total:
            lev = max_lev_total - lev_used
            if lev <= 0.05:
                continue
        scale = lev / (risk / r.sl_pct)
        pnl = eq * risk * r.R * scale
        heapq.heappush(open_heap, (r.exit_time, i, lev, pnl, r.sym, bool(is_open_col[i])))
        open_syms.add(r.sym); lev_used += lev; taken[i] = True
        eq_entry[i] = eq; lev_arr[i] = lev; pnl_arr[i] = pnl
    while open_heap:
        xt, j, lev, pnl, sym, op = heapq.heappop(open_heap)
        if not op:
            eq += pnl
        curve.append((xt, eq))
    if curve:
        c = pd.Series([v for _, v in curve], index=pd.DatetimeIndex([k for k, _ in curve])).groupby(level=0).last()
    else:
        c = pd.Series([start_equity], index=pd.DatetimeIndex([t["entry_time"].min() if len(t) else pd.Timestamp.now(tz="UTC")]))
    out = t.assign(eq_entry=eq_entry, notional_frac=lev_arr, pnl_usd=pnl_arr, is_open=is_open_col)[taken]
    return c, out


def curve_stats(c, start_equity=1.0):
    daily = c.resample("1D").last().ffill()
    daily = pd.concat([pd.Series([start_equity], index=[daily.index[0] - pd.Timedelta("1D")]), daily])
    rets = daily.pct_change().dropna()
    years = (daily.index[-1] - daily.index[0]).days / 365.25
    dd = (daily / daily.cummax() - 1).min()
    cagr = (daily.iloc[-1] / start_equity) ** (1 / years) - 1
    sharpe = rets.mean() / rets.std() * np.sqrt(365) if rets.std() > 0 else np.nan
    yearly = daily.resample("YE").last().pct_change()
    yearly.iloc[0] = daily.resample("YE").last().iloc[0] / start_equity - 1
    return dict(cagr=round(cagr * 100, 1), max_dd=round(dd * 100, 1), sharpe=round(sharpe, 2),
                mar=round(cagr / abs(dd), 2) if dd < 0 else np.nan,
                yearly={str(k.year): round(v * 100, 1) for k, v in yearly.items()})


def mtm_drawdown(taken, risk, closes):
    """Açık pozisyonları saatlik kapanışla değerleyen (mark-to-market) yaklaşık düşüş.

    Basitleştirme: sabit risk (bileşiksiz), kısmi kâr alımları çıkışa kadar yok sayılır;
    çıkış saatinde gerçekleşen R kullanılır. closes: {sym: pd.Series(1h close)}.
    """
    step = min(pd.Series(c.index).diff().min() for c in closes.values() if len(c) > 1)  # veri sıklığı (1h / 1D)
    idx = pd.date_range(min(c.index[0] for c in closes.values()), max(c.index[-1] for c in closes.values()), freq=step)
    pos = {s: np.searchsorted(idx.values, c.index.values[0]) for s, c in closes.items()}
    path = np.zeros(len(idx) + 1)
    real = np.zeros(len(idx) + 1)
    for r in taken.itertuples():
        c = closes[r.sym].values
        e, x = int(r.entry_i), int(r.exit_i)
        unr = r.side * (c[e:x] - r.entry) / (r.sl_pct * r.entry) - r.R_gross + r.R  # maliyet yaklaşık dahil
        o = pos[r.sym]
        path[o + e:o + x] += unr
        real[o + x] += r.R
    cum = np.cumsum(real)[:-1] + path[:-1]
    eq = 1 + risk * cum
    dd = (eq / np.maximum.accumulate(eq) - 1).min()
    return float(dd), pd.Series(eq, index=idx)
