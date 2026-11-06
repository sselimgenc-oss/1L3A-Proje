"""Simülatör kurallarının birim testleri: python -m pytest -q tests"""
import numpy as np
import pandas as pd
import pytest
from algo.backtest import simulate


def frame(rows):
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="1h", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def sig(n, at=0, s=1):
    a = np.zeros(n); a[at] = s; return a


def test_entry_next_open_and_stop_first():
    # sinyal bar0 kapanışı -> giriş bar1 açılışı (100). bar1 hem hedefi (110) hem stopu (95) görür -> STOP
    df = frame([(100, 100, 100, 100), (100, 111, 94, 100), (100, 100, 100, 100)])
    t = simulate(df, side=sig(3), sl_dist=5.0, tp2_R=2.0, cost=0.0)
    assert t.loc[0, "entry"] == 100 and t.loc[0, "reason"] == 1
    assert t.loc[0, "R_gross"] == pytest.approx(-1.0)


def test_gap_through_stop_exits_at_open():
    df = frame([(100, 100, 100, 100), (100, 101, 99, 100), (90, 91, 88, 89)])
    t = simulate(df, side=sig(3), sl_dist=5.0, cost=0.0)
    assert t.loc[0, "R_gross"] == pytest.approx(-2.0)  # 90'dan çıkış: (90-100)/5


def test_partial_take_profit_and_breakeven():
    # %50 1R'de (105) kapanır, stop başabaşa çekilir, sonra başabaştan çıkılır -> toplam +0.5R
    df = frame([(100, 100, 100, 100), (100, 106, 100, 105), (105, 105, 99, 100), (100, 100, 100, 100)])
    t = simulate(df, side=sig(4), sl_dist=5.0, tp1_R=1.0, tp1_frac=0.5, be_R=1.0, cost=0.0)
    assert t.loc[0, "R_gross"] == pytest.approx(0.5)
    assert t.loc[0, "R"] > 0


def test_short_symmetry():
    df = frame([(100, 100, 100, 100), (100, 100, 89, 90), (90, 90, 90, 90)])
    t = simulate(df, side=sig(3, s=-1), sl_dist=5.0, tp2_R=2.0, cost=0.0)
    assert t.loc[0, "reason"] == 2 and t.loc[0, "R_gross"] == pytest.approx(2.0)


def test_costs_and_funding_reduce_R():
    df = frame([(100, 100, 100, 100)] + [(100, 100, 100, 100)] * 5)
    fund = np.zeros(6); fund[2] = 0.001  # long funding öder
    t = simulate(df, side=sig(6), sl_dist=5.0, max_bars=3, cost=0.0007, funding=fund)
    # maliyet: 2*0.0007/0.05 = 0.028R, funding: 0.001/0.05 = 0.02R
    assert t.loc[0, "R"] == pytest.approx(-0.048, abs=1e-9)


def test_funding_scales_with_remaining_after_partial():
    df = frame([(100, 100, 100, 100), (100, 105, 100, 104), (104, 104, 104, 104), (104, 104, 104, 104)])
    fund = np.zeros(4); fund[2] = 0.001
    t = simulate(df, side=sig(4), sl_dist=5.0, tp1_R=1.0, tp1_frac=0.5, max_bars=2, cost=0.0, funding=fund)
    # bar2'de yalnızca %50 pozisyon kalmıştır -> funding 0.5*0.001/0.05 = 0.01R
    assert t.loc[0, "R_gross"] - t.loc[0, "R"] == pytest.approx(0.01)


def test_exit_signal_exits_next_open():
    df = frame([(100, 100, 100, 100), (100, 101, 99, 100), (102, 102, 102, 102), (103, 103, 103, 103)])
    ex = np.array([False, True, False, False])
    t = simulate(df, side=sig(4), sl_dist=5.0, exit_long=ex, cost=0.0)
    assert t.loc[0, "exit_i"] == 2 and t.loc[0, "R_gross"] == pytest.approx(0.4)


def test_loss_delay_blocks_reentry():
    rows = [(100, 100, 100, 100), (100, 100, 90, 90)] + [(90, 90, 90, 90)] * 6
    side = np.zeros(8); side[0] = 1; side[2] = 1; side[6] = 1
    t0 = simulate(frame(rows), side=side, sl_dist=5.0, max_bars=1, cost=0.0)
    t1 = simulate(frame(rows), side=side, sl_dist=5.0, max_bars=1, cost=0.0, loss_delay=3)
    assert len(t1) < len(t0)
