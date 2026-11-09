from __future__ import annotations

import json

import pandas as pd
import pytest

from codex_algo import data_import
from codex_algo.data import DataError
from codex_algo.mtf_config import MTFAsset, MTFConfig


def _config() -> MTFConfig:
    return MTFConfig(
        "2020-01-01",
        (MTFAsset("TEST", "Test", "ABD25", "yahoo", 5.0),),
    )


def _write_daily_csv(path, periods: int = 10) -> None:
    dates = pd.date_range("2019-12-29", periods=periods, freq="D")
    close = pd.Series(range(100, 100 + periods), dtype=float)
    pd.DataFrame(
        {
            "Date": dates,
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": 1_000,
        }
    ).to_csv(path, index=False)


def test_import_validates_trims_and_records_provenance(tmp_path, monkeypatch) -> None:
    source = tmp_path / "vendor.csv"
    target = tmp_path / "cache" / "test.csv"
    provenance = tmp_path / "state" / "provenance.json"
    _write_daily_csv(source)
    monkeypatch.setattr(data_import, "cache_path", lambda instrument: target)
    monkeypatch.setattr(data_import, "ROOT", tmp_path)

    record = data_import.import_mtf_csv(
        _config(),
        source,
        symbol="test",
        interval="1d",
        provenance_path=provenance,
    )

    cached = pd.read_csv(target, parse_dates=["timestamp"])
    assert cached["timestamp"].min() >= pd.Timestamp("2020-01-01", tz="UTC")
    assert record["rows_before_2020_discarded"] == 3
    assert record["source_sha256"]
    assert json.loads(provenance.read_text())[0]["symbol"] == "TEST"


def test_import_refuses_to_replace_existing_cache(tmp_path, monkeypatch) -> None:
    source = tmp_path / "vendor.csv"
    target = tmp_path / "cache.csv"
    _write_daily_csv(source)
    target.write_text("existing")
    monkeypatch.setattr(data_import, "cache_path", lambda instrument: target)
    monkeypatch.setattr(data_import, "ROOT", tmp_path)

    with pytest.raises(DataError, match="--replace"):
        data_import.import_mtf_csv(
            _config(),
            source,
            symbol="TEST",
            interval="1d",
            provenance_path=tmp_path / "provenance.json",
        )


def test_import_rejects_invalid_candle(tmp_path, monkeypatch) -> None:
    source = tmp_path / "invalid.csv"
    _write_daily_csv(source)
    raw = pd.read_csv(source)
    raw.loc[0, "High"] = raw.loc[0, "Low"] - 1
    raw.to_csv(source, index=False)
    monkeypatch.setattr(data_import, "cache_path", lambda instrument: tmp_path / "cache.csv")
    monkeypatch.setattr(data_import, "ROOT", tmp_path)

    with pytest.raises(DataError, match="OHLC fiyat ilişkisi"):
        data_import.import_mtf_csv(
            _config(),
            source,
            symbol="TEST",
            interval="1d",
            provenance_path=tmp_path / "provenance.json",
        )
