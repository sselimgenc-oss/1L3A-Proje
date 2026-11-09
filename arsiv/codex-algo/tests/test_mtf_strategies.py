from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from codex_algo.mtf_strategies import (
    MTF_REGISTRY,
    _resample_completed,
    generate_mtf_signal,
)


def _prices(periods: int, frequency: str) -> pd.DataFrame:
    rng = np.random.default_rng(2026)
    index = pd.date_range("2020-01-01", periods=periods, freq=frequency, tz="UTC")
    close = pd.Series(100 * np.exp(np.cumsum(0.0002 + rng.normal(0, 0.01, periods))), index=index)
    open_ = close.shift(1).fillna(close.iloc[0])
    return pd.DataFrame(
        {
            "open": open_,
            "high": pd.concat([open_, close], axis=1).max(axis=1) * 1.004,
            "low": pd.concat([open_, close], axis=1).min(axis=1) * 0.996,
            "close": close,
            "volume": rng.integers(10_000, 100_000, periods).astype(float),
        }
    )


@pytest.fixture(scope="module")
def daily_prices() -> pd.DataFrame:
    return _prices(1_500, "D")


@pytest.fixture(scope="module")
def hourly_prices() -> pd.DataFrame:
    return _prices(24 * 500, "h")


@pytest.mark.parametrize("strategy_id", sorted(MTF_REGISTRY))
def test_mtf_strategies_return_binary_signal(
    strategy_id: str, daily_prices: pd.DataFrame, hourly_prices: pd.DataFrame
) -> None:
    frame = daily_prices if strategy_id.startswith("wd_") else hourly_prices
    signal = generate_mtf_signal(strategy_id, frame)
    assert signal.index.equals(frame.index)
    assert set(signal.unique()) <= {0, 1}
    assert signal.notna().all()


def test_four_hour_bar_is_not_visible_before_completion() -> None:
    frame = _prices(5, "h")
    frame.loc[frame.index[-1], "close"] = 10_000
    frame.loc[frame.index[-1], "high"] = 10_001
    completed = _resample_completed(frame, "4h")
    assert list(completed.index) == [frame.index[-1]]
    assert completed.iloc[0]["close"] == frame.iloc[-2]["close"]


@pytest.mark.parametrize("strategy_id", sorted(MTF_REGISTRY))
def test_future_bar_change_does_not_rewrite_mtf_history(
    strategy_id: str, daily_prices: pd.DataFrame, hourly_prices: pd.DataFrame
) -> None:
    frame = (daily_prices if strategy_id.startswith("wd_") else hourly_prices).copy()
    original = generate_mtf_signal(strategy_id, frame)
    frame.loc[frame.index[-1], ["open", "high", "low", "close", "volume"]] *= 3
    revised = generate_mtf_signal(strategy_id, frame)
    pd.testing.assert_series_equal(original.iloc[:-1], revised.iloc[:-1])
