from __future__ import annotations

import numpy as np
import pandas as pd

from codex_algo import research
from codex_algo.config import AppConfig, Instrument


def test_research_matrix_writes_outputs_without_network(tmp_path, monkeypatch) -> None:
    rng = np.random.default_rng(7)
    index = pd.date_range("2020-01-01", periods=800, freq="D", tz="UTC")
    close = pd.Series(
        100 * np.exp(np.cumsum(0.0005 + rng.normal(0, 0.01, len(index)))), index=index
    )
    open_ = close.shift(1).fillna(close.iloc[0])
    frame = pd.DataFrame(
        {
            "open": open_,
            "high": pd.concat([open_, close], axis=1).max(axis=1) * 1.005,
            "low": pd.concat([open_, close], axis=1).min(axis=1) * 0.995,
            "close": close,
            "volume": 10_000.0,
        }
    )
    config = AppConfig(
        initial_capital=10_000,
        paper_days=60,
        history_start="2020-01-01",
        instruments=(Instrument("TEST", "Test", "Test", "mock", "1d", 252, 5.0),),
        paper_slots=(),
    )
    monkeypatch.setattr(research, "STATE_DIR", tmp_path)
    monkeypatch.setattr(research, "fetch_history", lambda *args, **kwargs: frame)

    results, summary = research.run_research(config)

    assert len(results) == 9
    assert len(summary) == 9
    assert (tmp_path / "backtests.csv").exists()
    assert (tmp_path / "strategy_summary.csv").exists()
    assert (tmp_path / "research_health.json").exists()
