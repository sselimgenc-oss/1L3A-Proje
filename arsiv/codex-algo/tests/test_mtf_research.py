from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from codex_algo import mtf_research
from codex_algo.data import DataError
from codex_algo.mtf_config import MTFAsset, MTFConfig, load_mtf_config


def _frame(start: str, periods: int, frequency: str) -> pd.DataFrame:
    rng = np.random.default_rng(9)
    index = pd.date_range(start, periods=periods, freq=frequency, tz="UTC")
    close = pd.Series(100 * np.exp(np.cumsum(0.0003 + rng.normal(0, 0.01, periods))), index=index)
    open_ = close.shift(1).fillna(close.iloc[0])
    return pd.DataFrame(
        {
            "open": open_,
            "high": pd.concat([open_, close], axis=1).max(axis=1) * 1.003,
            "low": pd.concat([open_, close], axis=1).min(axis=1) * 0.997,
            "close": close,
            "volume": 100_000.0,
        }
    )


def test_mtf_universe_has_requested_market_counts() -> None:
    config = load_mtf_config()
    counts = pd.Series([asset.market for asset in config.assets]).value_counts().to_dict()
    assert counts == {"BIST30": 30, "ABD25": 25, "KRIPTO25": 25, "EMTIA": 6}


def test_daily_mtf_research_writes_separate_outputs(tmp_path, monkeypatch) -> None:
    config = MTFConfig(
        "2020-01-01",
        (MTFAsset("TEST", "Test", "ABD25", "yahoo", 5.0),),
    )
    frame = _frame("2020-01-01", 1_500, "D")
    monkeypatch.setattr(mtf_research, "STATE_DIR", tmp_path)
    monkeypatch.setattr(mtf_research, "fetch_history", lambda *args, **kwargs: frame)

    results, summary, market_summary = mtf_research.run_mtf_research(config, mode="daily")

    assert len(results) == 4
    assert len(summary) == 4
    assert len(market_summary) == 4
    assert results["start"].str.startswith("2020-01-01").all()
    assert (tmp_path / "mtf_daily_backtests.csv").exists()
    assert (tmp_path / "mtf_daily_health.json").exists()


def test_hourly_yahoo_history_must_reach_2020(tmp_path, monkeypatch) -> None:
    config = MTFConfig(
        "2020-01-01",
        (MTFAsset("TEST", "Test", "ABD25", "yahoo", 5.0),),
    )
    recent = _frame("2024-01-01", 3_000, "h")
    monkeypatch.setattr(mtf_research, "STATE_DIR", tmp_path)
    monkeypatch.setattr(mtf_research, "fetch_history", lambda *args, **kwargs: recent)

    with pytest.raises(DataError, match="veri alınamadı"):
        mtf_research.run_mtf_research(config, mode="hourly")

    health = json.loads((tmp_path / "mtf_hourly_health.json").read_text())
    assert health["tested_rows"] == 0
    assert "01.01.2020" in health["errors"][0]["error"]
