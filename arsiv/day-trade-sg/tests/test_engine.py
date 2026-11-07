"""Motorun mekanik doğruluk testleri (sentetik veri; performans iddiası DEĞİLDİR)."""
import numpy as np
import pandas as pd

from daytrade.backtest import simulate
from daytrade.features import align_htf, build
from daytrade.data import resample
from daytrade.strategies import STRATEGIES, Signals
from daytrade.universe import crypto, us_stock


def _rw(n, freq="15min", start="2025-01-01", seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.002, n))
    l = np.minimum(o, c) * (1 - rng.uniform(0, 0.002, n))
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c,
                         "volume": rng.uniform(1, 2, n)}, idx)


def test_htf_alignment_no_lookahead():
    h1 = _rw(100, "1h")
    t = pd.DatetimeIndex([h1.index[5] + pd.Timedelta(minutes=59),
                          h1.index[5] + pd.Timedelta(minutes=60)])
    a = align_htf(h1[["close"]], "1h", t)
    assert a["close"].iloc[0] == h1["close"].iloc[4]   # 5. mum henüz kapanmadı
    assert a["close"].iloc[1] == h1["close"].iloc[5]   # kapandı → kullanılabilir


def _frame(bars):
    idx = pd.date_range("2025-01-01", periods=len(bars), freq="15min", tz="UTC")
    df = pd.DataFrame(bars, columns=["open", "high", "low", "close"], index=idx)
    df["atr"] = 1.0
    df["last_bar"] = False
    df.iloc[-1, df.columns.get_loc("last_bar")] = True
    df["day"] = "d"
    return df


def _sig(df, long_at, stop, **ex):
    L = pd.Series(False, df.index)
    L.iloc[long_at] = True
    z = pd.Series(np.nan, df.index)
    return Signals(L, pd.Series(False, df.index), pd.Series(stop, df.index), z, ex)


def test_stop_first_when_both_hit():
    df = _frame([[100, 100, 100, 100], [100, 103, 98, 101], [101, 101, 101, 101]])
    tr = simulate(df, _sig(df, 0, 99.0, target_R=2.0), 0.0)
    assert len(tr) == 1 and tr["reason"][0] == "stop" and np.isclose(tr["R"][0], -1)


def test_partial_then_target():
    df = _frame([[100, 100, 100, 100], [100, 101.2, 99.5, 101], [101, 102.5, 100.5, 102],
                 [102, 102, 102, 102]])
    tr = simulate(df, _sig(df, 0, 99.0, partial_R=1.0, partial_frac=0.5, target_R=2.0), 0.0)
    assert tr["reason"][0] == "target" and np.isclose(tr["R"][0], 1.5)


def test_eod_exit_and_cost():
    df = _frame([[100, 100, 100, 100], [100, 100.5, 99.5, 100.2], [100.2, 100.6, 100, 100.5]])
    tr = simulate(df, _sig(df, 0, 99.0), 0.001)
    expected = (100.5 - 100 - 0.001 * 200.5) / 1.0
    assert tr["reason"][0] == "eod" and np.isclose(tr["R"][0], expected)


def test_strategies_run_on_synthetic():
    for inst in (crypto("BTC"), us_stock("AAPL")):
        e = _rw(6000)
        if inst.asset_class == "us_stock":
            loc = e.index.tz_convert(inst.tz)
            tod = loc.hour * 60 + loc.minute
            e = e[(tod >= 570) & (tod < 960) & (loc.dayofweek < 5)]
        h1 = resample(e, "1h")
        df = build(inst, e, h1, resample(h1, "4h"), "15m")
        for name, (fn, _) in STRATEGIES.items():
            tr = simulate(df, fn(df), inst.cost_pct)
            assert set(tr.columns) >= {"R", "reason"}
            if len(tr):
                # hiçbir işlem seans gününü aşmamalı
                d_in = tr["entry_time"].dt.tz_convert(inst.tz).dt.date
                d_out = tr["exit_time"].dt.tz_convert(inst.tz).dt.date
                assert (d_in == d_out).all(), name
