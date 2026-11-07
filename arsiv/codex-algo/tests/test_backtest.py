from __future__ import annotations

import numpy as np
import pandas as pd

from codex_algo.backtest import evaluate_benchmark, run_backtest


def test_signal_is_executed_on_next_bar_open() -> None:
    index = pd.date_range("2025-01-01", periods=6, freq="D", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": [100, 100, 100, 110, 120, 120],
            "high": [101, 101, 111, 121, 121, 121],
            "low": [99, 99, 99, 109, 119, 119],
            "close": [100, 100, 110, 120, 120, 120],
            "volume": [1000] * 6,
        },
        index=index,
    )
    signal = pd.Series([0, 1, 1, 0, 0, 0], index=index)
    output = run_backtest(frame, signal, cost_bps=0, periods_per_year=252)
    assert output.equity.loc[index[1], "position"] == 0
    assert output.equity.loc[index[2], "position"] == 1
    assert output.equity.loc[index[4], "position"] == 0
    assert output.metrics["total_return"] > 0
    assert output.metrics["trades"] == 1


def test_costs_reduce_return() -> None:
    index = pd.date_range("2025-01-01", periods=8, freq="D", tz="UTC")
    frame = pd.DataFrame(
        {column: [100.0] * 8 for column in ["open", "high", "low", "close"]}, index=index
    )
    frame["volume"] = 1000.0
    signal = pd.Series([0, 1, 1, 0, 0, 1, 0, 0], index=index)
    free = run_backtest(frame, signal, cost_bps=0)
    costly = run_backtest(frame, signal, cost_bps=25)
    assert costly.metrics["total_return"] < free.metrics["total_return"]


def test_buy_hold_benchmark_uses_same_execution_model() -> None:
    index = pd.date_range("2020-01-01", periods=300, freq="D", tz="UTC")
    close = pd.Series(np.linspace(100, 200, len(index)), index=index)
    frame = pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "volume": 1_000.0}
    )
    metrics = evaluate_benchmark(frame, initial_capital=10_000, cost_bps=5, periods_per_year=365)
    assert metrics["benchmark_return"] > 0.9
    assert metrics["benchmark_oos_return"] > 0
