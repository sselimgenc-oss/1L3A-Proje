from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from codex_algo.strategies import REGISTRY, generate_signal


@pytest.fixture
def prices() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    index = pd.date_range("2018-01-01", periods=1200, freq="D", tz="UTC")
    returns = 0.0004 + 0.012 * rng.standard_normal(len(index))
    close = pd.Series(100 * np.exp(np.cumsum(returns)), index=index)
    open_ = close.shift(1).fillna(close.iloc[0]) * (1 + 0.002 * rng.standard_normal(len(index)))
    high = pd.concat([open_, close], axis=1).max(axis=1) * (1 + rng.uniform(0, 0.01, len(index)))
    low = pd.concat([open_, close], axis=1).min(axis=1) * (1 - rng.uniform(0, 0.01, len(index)))
    volume = pd.Series(rng.integers(1_000, 10_000, len(index)), index=index, dtype=float)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})


@pytest.mark.parametrize("strategy_id", sorted(REGISTRY))
def test_strategies_return_binary_aligned_signal(prices: pd.DataFrame, strategy_id: str) -> None:
    signal = generate_signal(strategy_id, prices)
    assert signal.index.equals(prices.index)
    assert set(signal.unique()) <= {0, 1}
    assert signal.notna().all()


@pytest.mark.parametrize("strategy_id", sorted(REGISTRY))
def test_future_bar_change_does_not_rewrite_history(prices: pd.DataFrame, strategy_id: str) -> None:
    original = generate_signal(strategy_id, prices)
    changed = prices.copy()
    changed.loc[changed.index[-1], ["open", "high", "low", "close", "volume"]] *= 2
    revised = generate_signal(strategy_id, changed)
    pd.testing.assert_series_equal(original.iloc[:-1], revised.iloc[:-1])
