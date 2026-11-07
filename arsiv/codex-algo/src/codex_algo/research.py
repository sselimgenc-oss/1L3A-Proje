from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .backtest import evaluate_benchmark, evaluate_candidate
from .catalog import STRATEGIES
from .config import STATE_DIR, AppConfig
from .data import DataError, fetch_history
from .strategies import generate_signal


def _write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def _write_json_atomic(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def run_research(
    config: AppConfig,
    *,
    symbols: set[str] | None = None,
    refresh: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    for instrument in config.instruments:
        if symbols and instrument.symbol not in symbols:
            continue
        try:
            frame = fetch_history(instrument, config.history_start, refresh=refresh)
        # Sağlayıcılar ortak bir hata tabanı kullanmıyor; sembol hatası matrisi durdurmamalı.
        except Exception as error:  # noqa: BLE001
            errors.append({"symbol": instrument.symbol, "error": str(error)})
            continue
        benchmark = evaluate_benchmark(
            frame,
            initial_capital=config.initial_capital,
            cost_bps=instrument.cost_bps,
            periods_per_year=instrument.periods_per_year,
        )
        for strategy in STRATEGIES:
            signal = generate_signal(strategy.strategy_id, frame)
            metrics = evaluate_candidate(
                frame,
                signal,
                initial_capital=config.initial_capital,
                cost_bps=instrument.cost_bps,
                periods_per_year=instrument.periods_per_year,
            )
            row = {
                "strategy": strategy.strategy_id,
                "strategy_name": strategy.name,
                "symbol": instrument.symbol,
                "market": instrument.market,
                "start": frame.index.min().isoformat(),
                "end": frame.index.max().isoformat(),
                **metrics,
                **benchmark,
            }
            row["excess_return"] = float(row["total_return"]) - benchmark["benchmark_return"]
            row["oos_excess_return"] = float(row["oos_return"]) - benchmark["benchmark_oos_return"]
            rows.append(row)

    results = pd.DataFrame(rows)
    if results.empty:
        summary = pd.DataFrame()
    else:
        summary = (
            results.groupby(["strategy", "strategy_name"], as_index=False)
            .agg(
                instruments=("symbol", "count"),
                profitable_share=("total_return", lambda values: float((values > 0).mean())),
                profitability_pass_share=("profitability_passes", "mean"),
                strict_pass_share=("strict_passes", "mean"),
                median_sharpe=("sharpe", "median"),
                median_profit_factor=("profit_factor", "median"),
                median_trades=("trades", "median"),
                median_return=("total_return", "median"),
                worst_drawdown=("max_drawdown", "min"),
                median_calmar=("calmar", "median"),
                median_oos_return=("oos_return", "median"),
                median_excess_return=("excess_return", "median"),
                median_oos_excess_return=("oos_excess_return", "median"),
                median_oos_sharpe=("oos_sharpe", "median"),
                stress_positive_share=("stress_return", lambda values: float((values > 0).mean())),
            )
            .sort_values(
                ["profitability_pass_share", "median_oos_return", "median_calmar"],
                ascending=False,
            )
        )
        summary["breadth_pass"] = summary["profitable_share"] >= 0.60
        summary["paper_eligible"] = (
            (summary["profitable_share"] >= 0.60)
            & (summary["stress_positive_share"] >= 0.60)
            & (summary["median_oos_return"] > 0)
            & (summary["worst_drawdown"] >= -0.35)
            & (summary["median_trades"] >= 5)
            & (summary["median_profit_factor"] > 1.0)
            & (summary["profitability_pass_share"] >= 0.25)
        )

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv_atomic(results, STATE_DIR / "backtests.csv")
    _write_csv_atomic(summary, STATE_DIR / "strategy_summary.csv")
    health = {
        "updated_at": datetime.now(UTC).isoformat(),
        "tested_rows": len(results),
        "data_errors": errors,
    }
    _write_json_atomic(health, STATE_DIR / "research_health.json")
    if errors and not rows:
        raise DataError(
            "Hiçbir piyasa verisi alınamadı; ayrıntı state/research_health.json içinde."
        )
    return results, summary
