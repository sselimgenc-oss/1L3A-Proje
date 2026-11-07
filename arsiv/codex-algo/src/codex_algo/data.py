from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

from .config import DATA_DIR, ROOT, STATE_DIR, Instrument

CACHE_DIR = DATA_DIR / "cache"
REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")
PROVIDER_RETRY_SECONDS = 60.0
_PROVIDER_RETRY_AT: dict[str, float] = {}


def _is_verified_import(path: Path) -> bool:
    provenance = STATE_DIR / "import_provenance.json"
    if not provenance.exists():
        return False
    try:
        payload = json.loads(provenance.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(payload, list):
        return False
    target = path.resolve()
    for record in payload:
        if not isinstance(record, dict) or not record.get("cache_file"):
            continue
        candidate = Path(str(record["cache_file"]))
        if not candidate.is_absolute():
            candidate = ROOT / candidate
        if candidate.resolve() == target:
            return True
    return False


class DataError(RuntimeError):
    pass


def cache_path(instrument: Instrument) -> Path:
    """Return the only supported on-disk OHLCV location for an instrument."""
    safe_symbol = instrument.symbol.replace("=", "_").replace(".", "_")
    return CACHE_DIR / f"{instrument.source}-{safe_symbol}-{instrument.interval}.csv"


def validate_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise DataError(f"OHLCV sütunları eksik: {sorted(missing)}")
    result = frame.loc[:, REQUIRED_COLUMNS].copy()
    result.index = pd.to_datetime(result.index, utc=True)
    result = result[~result.index.duplicated(keep="last")].sort_index()
    result = result.apply(pd.to_numeric, errors="coerce").dropna(
        subset=["open", "high", "low", "close"]
    )
    result["volume"] = result["volume"].fillna(0.0)
    if result.empty:
        raise DataError("Veri kümesi boş.")
    if (result[["open", "high", "low", "close"]] <= 0).any().any():
        raise DataError("Fiyat sütunlarında sıfır veya negatif değer var.")
    if (result["volume"] < 0).any():
        raise DataError("Hacim sütununda negatif değer var.")
    candle_top = result[["open", "close", "low"]].max(axis=1)
    candle_bottom = result[["open", "close", "high"]].min(axis=1)
    if (result["high"] < candle_top).any() or (result["low"] > candle_bottom).any():
        raise DataError("OHLC fiyat ilişkisi geçersiz: high/low mum aralığını kapsamıyor.")
    return result


def _fetch_yahoo(instrument: Instrument, start: str, end: str | None) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(
        instrument.symbol,
        start=start,
        end=end,
        interval=instrument.interval,
        # Split/dividend-adjusted OHLC keeps mechanical corporate actions from being
        # interpreted as strategy losses or breakouts.
        auto_adjust=True,
        actions=False,
        progress=False,
        threads=False,
        timeout=30,
    )
    if raw.empty:
        raise DataError(f"Yahoo veri döndürmedi: {instrument.symbol}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.columns = [str(column).lower().replace(" ", "_") for column in raw.columns]
    if "adj_close" in raw.columns and "close" not in raw.columns:
        raw["close"] = raw["adj_close"]
    return validate_ohlcv(raw)


def _fetch_binance(instrument: Instrument, start: str, end: str | None) -> pd.DataFrame:
    endpoint = "https://data-api.binance.vision/api/v3/klines"
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_timestamp = pd.Timestamp(end, tz="UTC") if end else pd.Timestamp.now(tz="UTC")
    end_ms = int(end_timestamp.timestamp() * 1000)
    rows: list[list[object]] = []
    session = requests.Session()
    session.headers.update({"User-Agent": "codex-algo-paper-research/0.1"})

    # 2020'den başlayan 1 saatlik kripto verisi yaklaşık 60 sayfa gerektirir.
    for _ in range(100):
        response = session.get(
            endpoint,
            params={
                "symbol": instrument.symbol,
                "interval": instrument.interval,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000,
            },
            timeout=30,
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        rows.extend(batch)
        next_start = int(batch[-1][0]) + 1
        if next_start <= start_ms or len(batch) < 1000:
            break
        start_ms = next_start
        time.sleep(0.05)
    else:
        raise DataError(f"Binance sayfalama sınırına ulaştı: {instrument.symbol}")

    if not rows:
        raise DataError(f"Binance veri döndürmedi: {instrument.symbol}")
    raw = pd.DataFrame(
        rows,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trade_count",
            "taker_base",
            "taker_quote",
            "ignore",
        ],
    ).set_index("timestamp")
    raw.index = pd.to_datetime(raw.index, unit="ms", utc=True)
    return validate_ohlcv(raw)


def fetch_history(
    instrument: Instrument,
    start: str,
    end: str | None = None,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    path = cache_path(instrument)
    if path.exists() and (not refresh or _is_verified_import(path)):
        cached = pd.read_csv(path, index_col="timestamp", parse_dates=["timestamp"])
        return validate_ohlcv(cached)

    retry_at = _PROVIDER_RETRY_AT.get(instrument.source, 0.0)
    remaining = retry_at - time.monotonic()
    if remaining > 0:
        raise DataError(
            f"{instrument.source} sağlayıcısı bağlantı hatasından sonra geçici olarak "
            f"beklemede ({remaining:.0f} sn)."
        )

    try:
        if instrument.source == "yahoo":
            frame = _fetch_yahoo(instrument, start, end)
        elif instrument.source == "binance":
            frame = _fetch_binance(instrument, start, end)
        else:
            raise DataError(f"Desteklenmeyen veri kaynağı: {instrument.source}")
    except Exception:
        _PROVIDER_RETRY_AT[instrument.source] = time.monotonic() + PROVIDER_RETRY_SECONDS
        raise
    _PROVIDER_RETRY_AT.pop(instrument.source, None)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index_label="timestamp")
    return frame
