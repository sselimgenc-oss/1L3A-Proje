from __future__ import annotations

import json
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests

from .backtest import evaluate_benchmark, evaluate_candidate
from .catalog import STRATEGIES
from .config import DATA_DIR, STATE_DIR, AppConfig
from .data import validate_ohlcv
from .strategies import generate_signal

ARCHIVE_URL = "https://raw.githubusercontent.com/plotly/datasets/master/all_stocks_5yr.csv"
ARCHIVE_LICENSE = "MIT; Copyright (c) 2019-2024 Plotly Technologies Inc."
ARCHIVE_DIR = DATA_DIR / "archive"
DEFAULT_SYMBOLS = ("AAPL", "MSFT", "NVDA")


def download_plotly_archive(
    symbols: tuple[str, ...] | None = DEFAULT_SYMBOLS,
    *,
    minimum_bars: int = 1,
    persist_frames: bool = True,
) -> dict[str, pd.DataFrame]:
    response = requests.get(
        ARCHIVE_URL,
        timeout=90,
        headers={"User-Agent": "codex-algo-archival-research/0.1"},
    )
    response.raise_for_status()
    raw = pd.read_csv(BytesIO(response.content))
    required = {"date", "open", "high", "low", "close", "volume", "Name"}
    if not required.issubset(raw.columns):
        raise RuntimeError("Plotly arşiv şeması beklenen OHLCV alanlarını içermiyor.")

    selected_symbols = symbols or tuple(sorted(raw["Name"].dropna().astype(str).unique()))
    frames: dict[str, pd.DataFrame] = {}
    if persist_frames:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for symbol in selected_symbols:
        selected = raw.loc[
            raw["Name"] == symbol, ["date", "open", "high", "low", "close", "volume"]
        ]
        if selected.empty:
            raise RuntimeError(f"Plotly arşivinde sembol bulunamadı: {symbol}")
        frame = selected.set_index("date")
        frame.index.name = "timestamp"
        frame = validate_ohlcv(frame)
        if len(frame) < minimum_bars:
            continue
        if persist_frames:
            frame.to_csv(ARCHIVE_DIR / f"plotly-{symbol}.csv", index_label="timestamp")
        frames[symbol] = frame
    return frames


def run_archival_research(
    config: AppConfig,
    frames: dict[str, pd.DataFrame],
    *,
    state_dir: Path = STATE_DIR,
    file_prefix: str = "archival",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    for symbol, frame in frames.items():
        try:
            instrument = config.instrument(symbol)
            cost_bps = instrument.cost_bps
            periods_per_year = instrument.periods_per_year
            market = instrument.market
        except KeyError:
            cost_bps = 6.0
            periods_per_year = 252
            market = "ABD arşiv genişliği"
        benchmark = evaluate_benchmark(
            frame,
            initial_capital=config.initial_capital,
            cost_bps=cost_bps,
            periods_per_year=periods_per_year,
        )
        for strategy in STRATEGIES:
            metrics = evaluate_candidate(
                frame,
                generate_signal(strategy.strategy_id, frame),
                initial_capital=config.initial_capital,
                cost_bps=cost_bps,
                periods_per_year=periods_per_year,
            )
            row = {
                "strategy": strategy.strategy_id,
                "strategy_name": strategy.name,
                "symbol": symbol,
                "market": market,
                "start": frame.index.min().isoformat(),
                "end": frame.index.max().isoformat(),
                "dataset": "Plotly all_stocks_5yr",
                **metrics,
                **benchmark,
            }
            row["excess_return"] = float(row["total_return"]) - benchmark["benchmark_return"]
            row["oos_excess_return"] = float(row["oos_return"]) - benchmark["benchmark_oos_return"]
            rows.append(row)

    results = pd.DataFrame(rows)
    summary = summarize_archival_results(results)

    state_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(state_dir / f"{file_prefix}_backtests.csv", index=False)
    summary.to_csv(state_dir / f"{file_prefix}_summary.csv", index=False)
    provenance = {
        "created_at": datetime.now(UTC).isoformat(),
        "source": ARCHIVE_URL,
        "license": ARCHIVE_LICENSE,
        "symbols": sorted(frames),
        "symbol_count": len(frames),
        "universe_bias": (
            "Arşiv bileşenleri ve eksik kısa tarihli hisseler hayatta kalma/seçim yanlılığı "
            "oluşturabilir."
        ),
        "warning": (
            "2013-2018 tarihli arşiv yalnız ön eleme içindir; güncel doğrulama veya "
            "paper-test uygunluğu sağlamaz."
        ),
    }
    (state_dir / f"{file_prefix}_provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return results, summary


def summarize_archival_results(results: pd.DataFrame) -> pd.DataFrame:
    summary = (
        results.groupby(["strategy", "strategy_name"], as_index=False)
        .agg(
            instruments=("symbol", "count"),
            median_trades=("trades", "median"),
            minimum_trades=("trades", "min"),
            profitable_share=("total_return", lambda values: float((values > 0).mean())),
            pass_share=("profitability_passes", "mean"),
            median_return=("total_return", "median"),
            median_oos_return=("oos_return", "median"),
            median_excess_return=("excess_return", "median"),
            median_oos_excess_return=("oos_excess_return", "median"),
            median_profit_factor=("profit_factor", "median"),
            median_sharpe=("sharpe", "median"),
            median_drawdown=("max_drawdown", "median"),
            p10_drawdown=("max_drawdown", lambda values: float(values.quantile(0.10))),
            worst_drawdown=("max_drawdown", "min"),
            stress_positive_share=("stress_return", lambda values: float((values > 0).mean())),
        )
        .sort_values(
            ["pass_share", "median_oos_return", "median_return"],
            ascending=False,
        )
    )
    summary["preliminary_status"] = "do_not_advance"
    broad = summary["instruments"] >= 30
    broad_core = (
        broad
        & (summary["profitable_share"] >= 0.60)
        & (summary["stress_positive_share"] >= 0.55)
        & (summary["median_oos_return"] > 0)
        & (summary["median_profit_factor"] >= 1.10)
    )
    summary.loc[broad_core, "preliminary_status"] = "watch_low_confidence"
    summary.loc[broad_core & (summary["median_trades"] >= 15), "preliminary_status"] = "advance"
    broad_secondary = (
        broad
        & (summary["profitable_share"] >= 0.55)
        & (summary["stress_positive_share"] >= 0.50)
        & (summary["median_oos_return"] > 0)
        & (summary["median_profit_factor"] >= 1.10)
    )
    summary.loc[broad_secondary & ~broad_core, "preliminary_status"] = "watch_weak_breadth"

    small = ~broad
    durable_small = (
        small
        & (summary["profitable_share"] >= 2 / 3)
        & (summary["median_oos_return"] > 0)
        & (summary["stress_positive_share"] >= 2 / 3)
        & (summary["worst_drawdown"] >= -0.35)
    )
    summary.loc[durable_small, "preliminary_status"] = "watch_low_confidence"
    summary.loc[durable_small & (summary["pass_share"] >= 2 / 3), "preliminary_status"] = "advance"
    summary.loc[
        small
        & (summary["profitable_share"] >= 2 / 3)
        & (summary["median_oos_return"] > 0)
        & (summary["stress_positive_share"] >= 2 / 3)
        & (summary["worst_drawdown"] < -0.35),
        "preliminary_status",
    ] = "watch_drawdown"
    return summary
