from __future__ import annotations

import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from codex_algo import data
from codex_algo.config import Instrument
from codex_algo.data import DataError


def _instrument(symbol: str) -> Instrument:
    return Instrument(symbol, symbol, "ABD25", "yahoo", "1d", 252, 5.0)


def test_provider_circuit_breaker_avoids_repeated_failed_requests(tmp_path, monkeypatch) -> None:
    calls = 0

    def fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise DataError("provider blocked")

    monkeypatch.setattr(data, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(data, "_fetch_yahoo", fail)
    monkeypatch.setattr(data.time, "monotonic", lambda: 1_000.0)
    data._PROVIDER_RETRY_AT.clear()

    with pytest.raises(DataError, match="provider blocked"):
        data.fetch_history(_instrument("AAPL"), "2020-01-01", refresh=True)
    with pytest.raises(DataError, match="geçici olarak"):
        data.fetch_history(_instrument("MSFT"), "2020-01-01", refresh=True)

    assert calls == 1
    data._PROVIDER_RETRY_AT.clear()


def test_yahoo_download_uses_adjusted_ohlc(monkeypatch) -> None:
    received: dict[str, object] = {}
    index = pd.date_range("2020-01-01", periods=2, freq="D", tz="UTC")
    frame = pd.DataFrame(
        {"Open": [1, 1], "High": [1, 1], "Low": [1, 1], "Close": [1, 1], "Volume": [1, 1]},
        index=index,
    )

    def download(*args, **kwargs):
        received.update(kwargs)
        return frame

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=download))
    data._fetch_yahoo(_instrument("AAPL"), "2020-01-01", None)
    assert received["auto_adjust"] is True


def test_refresh_preserves_verified_imported_cache(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "data" / "cache"
    cache_dir.mkdir(parents=True)
    monkeypatch.setattr(data, "ROOT", tmp_path)
    monkeypatch.setattr(data, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(data, "CACHE_DIR", cache_dir)
    instrument = _instrument("AAPL")
    path = data.cache_path(instrument)
    index = pd.date_range("2020-01-01", periods=2, freq="D", tz="UTC")
    pd.DataFrame({"open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}, index=index).to_csv(
        path, index_label="timestamp"
    )
    data.STATE_DIR.mkdir()
    (data.STATE_DIR / "import_provenance.json").write_text(
        '[{"cache_file":"data/cache/yahoo-AAPL-1d.csv"}]', encoding="utf-8"
    )
    monkeypatch.setattr(
        data,
        "_fetch_yahoo",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("provider called")),
    )
    result = data.fetch_history(instrument, "2020-01-01", refresh=True)
    assert len(result) == 2
