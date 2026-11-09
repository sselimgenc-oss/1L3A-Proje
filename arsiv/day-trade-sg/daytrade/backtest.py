"""Olay tabanlı (mum mum) backtest motoru.

Kurallar:
- Sinyal i. mumun kapanışında oluşur, işlem (i+1). mumun AÇILIŞINDA açılır.
- Aynı mumda hem stop hem hedef/kısmi seviye görülürse önce STOP varsayılır (muhafazakâr).
- Açılış stopun ötesinde boşluk açarsa (gap) çıkış açılış fiyatından yapılır.
- Kısmi kâr: partial_R'de pozisyonun partial_frac'ı kapanır, stop başabaşa çekilir.
- İz süren stop (trail) ve kapanış çıkışı (close_exit) mum kapanışında güncellenir,
  bir sonraki mumdan itibaren geçerlidir.
- Seansın son mumunda tüm pozisyon kapanış fiyatından kapatılır (day trade).
- Maliyet: her yön için cost_pct · fiyat (komisyon + kayma).
Sonuç R cinsindendir (1R = giriş ile ilk stop arası risk).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .strategies import Signals


def simulate(df: pd.DataFrame, sig: Signals, cost_pct: float, symbol: str = "",
             strategy: str = "", mark_open: bool = False, max_cost_R: float = 0.2) -> pd.DataFrame:
    """mark_open=True (kağıt al-sat): veri sonunda açık pozisyon "acik" (son kapanıştan
    değerlenmiş), son mumda oluşan sinyal "bekleyen" kaydı olarak döner.
    max_cost_R: gidiş-dönüş maliyeti riskin bu oranını aşan işlemler açılmaz (stop çok
    darsa komisyon+kayma kârı yer; hedefe ulaşan işlem bile zarar yazar)."""
    ex = sig.exit
    pR = ex.get("partial_R")
    pf = ex.get("partial_frac", 0.5) if pR else 0.0
    tR = ex.get("target_R")
    trail_col, trail_atr = ex.get("trail"), ex.get("trail_atr", 0.0)
    close_col = ex.get("close_exit")
    max_per_day = ex.get("max_per_day", 99)
    tp_col = ex.get("tp")            # dinamik kâr-al seviyesi (önceki mum kapanışında bilinen)
    max_bars = ex.get("max_bars")    # en uzun tutma süresi (mum)

    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    atr = df["atr"].to_numpy(float)
    last = df["last_bar"].to_numpy(bool)
    day = pd.factorize(df["day"])[0]
    L = sig.long.to_numpy(bool)
    S = sig.short.to_numpy(bool)
    LS = sig.long_stop.to_numpy(float)
    SS = sig.short_stop.to_numpy(float)
    trail = df[trail_col].to_numpy(float) if trail_col else None
    cexit = df[close_col].to_numpy(float) if close_col else None
    tpv = df[tp_col].to_numpy(float) if tp_col else None
    idx = df.index

    trades = []
    pos = 0            # +1 long, -1 short, 0 flat
    entry = stop = risk = 0.0
    rem = 1.0
    booked = 0.0       # kısmi çıkışlardan gelen net R
    part_done = False
    ent_i = -1
    pending = 0
    pend_stop = 0.0
    day_count = {}

    def close_trade(i, price, reason):
        nonlocal pos, booked, rem
        pnl = pos * (price - entry) - cost_pct * (entry + price)
        tot = booked + rem * pnl / risk
        trades.append((symbol, strategy, idx[ent_i], idx[i], pos, entry, risk, tot,
                       reason, part_done))
        pos = 0

    n = len(df)
    for i in range(n):
        # 1) bekleyen girişi bu mumun açılışında gerçekleştir
        if pending and pos == 0:
            e = o[i]
            st = pend_stop
            if ((pending == 1 and e > st) or (pending == -1 and e < st)) and \
                    2 * cost_pct * e <= max_cost_R * abs(e - st):
                pos, entry, stop = pending, e, st
                risk = abs(e - st)
                rem, booked, part_done, ent_i = 1.0, 0.0, False, i
                day_count[day[i]] = day_count.get(day[i], 0) + 1
            pending = 0
        # 2) açık pozisyonu yönet
        if pos != 0:
            if pos == 1:
                if o[i] <= stop and i > ent_i:
                    close_trade(i, o[i], "gap_stop")
                elif l[i] <= stop:
                    close_trade(i, stop, "stop" if not part_done else "be_stop")
                else:
                    if pR and not part_done and h[i] >= entry + pR * risk:
                        px = entry + pR * risk
                        booked += pf * ((px - entry) - cost_pct * (entry + px)) / risk
                        rem -= pf
                        part_done = True
                        stop = max(stop, entry)
                        if c[i] <= entry:  # aynı mumda başabaşa geri döndü (muhafazakâr)
                            close_trade(i, entry, "be_stop")
                    if pos and tR and h[i] >= entry + tR * risk:
                        close_trade(i, entry + tR * risk, "target")
                    if pos and tpv is not None and i > ent_i and not np.isnan(tpv[i - 1]) \
                            and tpv[i - 1] > entry and h[i] >= tpv[i - 1]:
                        close_trade(i, max(o[i], tpv[i - 1]), "tp_level")
            else:
                if o[i] >= stop and i > ent_i:
                    close_trade(i, o[i], "gap_stop")
                elif h[i] >= stop:
                    close_trade(i, stop, "stop" if not part_done else "be_stop")
                else:
                    if pR and not part_done and l[i] <= entry - pR * risk:
                        px = entry - pR * risk
                        booked += pf * ((entry - px) - cost_pct * (entry + px)) / risk
                        rem -= pf
                        part_done = True
                        stop = min(stop, entry)
                        if c[i] >= entry:
                            close_trade(i, entry, "be_stop")
                    if pos and tR and l[i] <= entry - tR * risk:
                        close_trade(i, entry - tR * risk, "target")
                    if pos and tpv is not None and i > ent_i and not np.isnan(tpv[i - 1]) \
                            and tpv[i - 1] < entry and l[i] <= tpv[i - 1]:
                        close_trade(i, min(o[i], tpv[i - 1]), "tp_level")
            if pos != 0:
                if last[i]:
                    close_trade(i, c[i], "eod")
                elif max_bars and i - ent_i + 1 >= max_bars:
                    close_trade(i, c[i], "time")
                elif cexit is not None and ((pos == 1 and c[i] < cexit[i])
                                            or (pos == -1 and c[i] > cexit[i])):
                    close_trade(i, c[i], "ma_close")
                elif trail is not None and not np.isnan(trail[i]):
                    if pos == 1:
                        stop = max(stop, trail[i] - trail_atr * atr[i]) if part_done else stop
                    else:
                        stop = min(stop, trail[i] + trail_atr * atr[i]) if part_done else stop
        # 3) yeni sinyal (pozisyon yoksa)
        if pos == 0 and not last[i] and (i + 1 >= n or day[i + 1] == day[i]):
            if day_count.get(day[i], 0) >= max_per_day:
                continue
            if L[i] and not np.isnan(LS[i]):
                pending, pend_stop = 1, LS[i]
            elif S[i] and not np.isnan(SS[i]):
                pending, pend_stop = -1, SS[i]

    if mark_open and n:
        if pos != 0:
            close_trade(n - 1, c[n - 1], "acik")
        elif pending:
            st = pend_stop
            trades.append((symbol, strategy, idx[n - 1], idx[n - 1], pending, c[n - 1],
                           abs(c[n - 1] - st), 0.0, "bekleyen", False))
    cols = ["symbol", "strategy", "entry_time", "exit_time", "dir", "entry", "risk", "R",
            "reason", "partial"]
    return pd.DataFrame(trades, columns=cols)


def metrics(tr: pd.DataFrame) -> dict:
    if tr is None or len(tr) == 0:
        return dict(trades=0, win_rate=np.nan, pf=np.nan, exp_R=np.nan, total_R=0.0,
                    max_dd_R=0.0, avg_win=np.nan, avg_loss=np.nan)
    r = tr["R"].to_numpy()
    wins, losses = r[r > 0], r[r <= 0]
    gp, gl = wins.sum(), -losses.sum()
    eq = np.cumsum(r[np.argsort(tr["exit_time"].to_numpy())])
    dd = (np.maximum.accumulate(np.concatenate([[0], eq])) - np.concatenate([[0], eq])).max()
    return dict(trades=len(r), win_rate=len(wins) / len(r), pf=gp / gl if gl > 0 else np.inf,
                exp_R=r.mean(), total_R=r.sum(), max_dd_R=dd,
                avg_win=wins.mean() if len(wins) else np.nan,
                avg_loss=losses.mean() if len(losses) else np.nan)
