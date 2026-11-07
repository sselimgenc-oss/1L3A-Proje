from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .config import ROOT, STATE_DIR, Instrument
from .data import DataError, cache_path, validate_ohlcv
from .mtf_config import MTFConfig

DEFAULT_PROVENANCE = STATE_DIR / "import_provenance.json"
TIMESTAMP_ALIASES = ("timestamp", "datetime", "date", "time", "open_time")


def _normalise_column(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _timestamp_column(raw: pd.DataFrame, requested: str | None) -> object:
    columns = {_normalise_column(column): column for column in raw.columns}
    if requested:
        key = _normalise_column(requested)
        if key not in columns:
            raise DataError(f"Zaman sütunu bulunamadı: {requested}")
        return columns[key]
    for alias in TIMESTAMP_ALIASES:
        if alias in columns:
            return columns[alias]
    raise DataError("Zaman sütunu bulunamadı; timestamp/date/datetime/time/open_time bekleniyor.")


def _parse_timestamps(values: pd.Series, timezone: str) -> pd.DatetimeIndex:
    if pd.api.types.is_numeric_dtype(values):
        numeric = pd.to_numeric(values, errors="coerce")
        median = numeric.dropna().abs().median()
        if pd.isna(median):
            parsed = pd.to_datetime(values, errors="coerce", utc=True)
        elif median >= 100_000_000_000:
            parsed = pd.to_datetime(numeric, unit="ms", errors="coerce", utc=True)
        elif median >= 1_000_000_000:
            parsed = pd.to_datetime(numeric, unit="s", errors="coerce", utc=True)
        else:
            raise DataError("Sayısal zaman damgası Unix saniye veya milisaniye olmalı.")
        return pd.DatetimeIndex(parsed)

    parsed = pd.to_datetime(values, errors="coerce")
    try:
        current_timezone = parsed.dt.tz
    except AttributeError as error:
        raise DataError("Zaman sütunu tarih/saat olarak ayrıştırılamadı.") from error
    if current_timezone is None:
        try:
            parsed = parsed.dt.tz_localize(
                timezone, ambiguous="NaT", nonexistent="shift_forward"
            ).dt.tz_convert("UTC")
        except (TypeError, ValueError) as error:
            raise DataError(f"Geçersiz veya uyumsuz saat dilimi: {timezone}") from error
    else:
        parsed = parsed.dt.tz_convert("UTC")
    return pd.DatetimeIndex(parsed)


def read_ohlcv_csv(
    path: Path,
    *,
    timestamp_column: str | None = None,
    timezone: str = "UTC",
) -> pd.DataFrame:
    if not path.is_file():
        raise DataError(f"CSV dosyası bulunamadı: {path}")
    raw = pd.read_csv(path)
    time_column = _timestamp_column(raw, timestamp_column)
    normalised = {_normalise_column(column): column for column in raw.columns}
    missing = [
        column for column in ("open", "high", "low", "close", "volume") if column not in normalised
    ]
    if missing:
        raise DataError(f"OHLCV sütunları eksik: {missing}")

    frame = pd.DataFrame(
        {
            column: raw[normalised[column]].to_numpy()
            for column in ("open", "high", "low", "close", "volume")
        },
        index=_parse_timestamps(raw[time_column], timezone),
    )
    frame = frame.loc[~frame.index.isna()]
    return validate_ohlcv(frame)


def _validate_interval(frame: pd.DataFrame, interval: str) -> None:
    if len(frame) < 2:
        raise DataError("Zaman aralığını doğrulamak için en az iki bar gerekli.")
    median_seconds = frame.index.to_series().diff().dropna().dt.total_seconds().median()
    if interval == "1d" and not 18 * 3600 <= median_seconds <= 4 * 24 * 3600:
        raise DataError("CSV günlük frekansta görünmüyor.")
    if interval == "1h" and not 30 * 60 <= median_seconds <= 2 * 3600:
        raise DataError("CSV saatlik frekansta görünmüyor.")


def _asset_instrument(config: MTFConfig, symbol: str, interval: str) -> Instrument:
    matches = [asset for asset in config.assets if asset.symbol.casefold() == symbol.casefold()]
    if not matches:
        raise DataError(f"Sembol MTF evreninde yok: {symbol}")
    return matches[0].instrument(interval)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _append_provenance(record: dict[str, Any], path: Path) -> None:
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise DataError(f"Kaynak kaydı okunamadı: {path}") from error
        if not isinstance(payload, list):
            raise DataError(f"Kaynak kaydı liste biçiminde değil: {path}")
    else:
        payload = []
    payload.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def import_mtf_csv(
    config: MTFConfig,
    source_file: Path,
    *,
    symbol: str,
    interval: str,
    timestamp_column: str | None = None,
    timezone: str = "UTC",
    replace: bool = False,
    provenance_path: Path | None = None,
) -> dict[str, Any]:
    """Validate a vendor CSV and copy it into this repository's MTF cache."""
    if interval not in {"1d", "1h"}:
        raise DataError("İçe aktarma aralığı 1d veya 1h olmalı.")
    instrument = _asset_instrument(config, symbol, interval)
    frame = read_ohlcv_csv(
        source_file,
        timestamp_column=timestamp_column,
        timezone=timezone,
    )
    requested_start = pd.Timestamp(config.history_start, tz="UTC")
    rows_before_start = int((frame.index < requested_start).sum())
    frame = frame.loc[frame.index >= requested_start]
    if frame.empty:
        raise DataError(f"CSV {config.history_start} sonrasında veri içermiyor.")
    _validate_interval(frame, interval)

    target = cache_path(instrument)
    try:
        target.resolve().relative_to(ROOT.resolve())
    except ValueError as error:
        raise DataError("Hedef codex-algo çalışma alanının dışında.") from error
    if target.exists() and not replace:
        raise DataError(f"Önbellek zaten var: {target}; değiştirmek için --replace kullanın.")

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".importing")
    frame.to_csv(temporary, index_label="timestamp")
    temporary.replace(target)

    record: dict[str, Any] = {
        "imported_at": datetime.now(UTC).isoformat(),
        "symbol": instrument.symbol,
        "market": instrument.market,
        "interval": interval,
        "provider_cache_key": instrument.source,
        "source_file": str(source_file.resolve()),
        "source_sha256": _sha256(source_file),
        "cache_file": str(target.relative_to(ROOT)),
        "rows": len(frame),
        "rows_before_2020_discarded": rows_before_start,
        "start": frame.index.min().isoformat(),
        "end": frame.index.max().isoformat(),
        "requested_start": config.history_start,
        "starts_after_requested_date": bool(frame.index.min() > requested_start),
        "timezone_input": timezone,
    }
    _append_provenance(record, provenance_path or DEFAULT_PROVENANCE)
    return record
