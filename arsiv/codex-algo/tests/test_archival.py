from __future__ import annotations

import json

import numpy as np
import pandas as pd

from codex_algo.archival import run_archival_research
from codex_algo.config import AppConfig, Instrument


def test_archival_research_stays_separate_from_live_outputs(tmp_path) -> None:
    rng = np.random.default_rng(11)
    index = pd.date_range("2013-01-01", periods=800, freq="B", tz="UTC")
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0004, 0.012, len(index)))), index=index)
    open_ = close.shift(1).fillna(close.iloc[0])
    frame = pd.DataFrame(
        {
            "open": open_,
            "high": pd.concat([open_, close], axis=1).max(axis=1) * 1.005,
            "low": pd.concat([open_, close], axis=1).min(axis=1) * 0.995,
            "close": close,
            "volume": 1_000_000.0,
        }
    )
    config = AppConfig(
        10_000,
        60,
        "2013-01-01",
        (Instrument("AAPL", "Apple", "ABD", "yahoo", "1d", 252, 5.0),),
        (),
    )

    results, summary = run_archival_research(config, {"AAPL": frame}, state_dir=tmp_path)

    assert len(results) == 9
    assert len(summary) == 9
    assert "preliminary_status" in summary.columns
    assert (tmp_path / "archival_backtests.csv").exists()
    assert (tmp_path / "archival_summary.csv").exists()
    assert not (tmp_path / "strategy_summary.csv").exists()
    provenance = json.loads((tmp_path / "archival_provenance.json").read_text())
    assert provenance["symbols"] == ["AAPL"]
