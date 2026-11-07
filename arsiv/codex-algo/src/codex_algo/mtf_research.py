from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from .backtest import evaluate_benchmark, evaluate_candidate
from .config import STATE_DIR
from .data import DataError, fetch_history
from .mtf_config import MTFConfig
from .mtf_strategies import MTF_STRATEGIES, generate_mtf_signal


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


def _summarize(results: pd.DataFrame, groups: list[str]) -> pd.DataFrame:
    summary = (
        results.groupby(groups, as_index=False)
        .agg(
            instruments=("symbol", "count"),
            markets=("market", "nunique"),
            profitable_share=("total_return", lambda values: float((values > 0).mean())),
            profitability_pass_share=("profitability_passes", "mean"),
            stress_positive_share=("stress_return", lambda values: float((values > 0).mean())),
            median_return=("total_return", "median"),
            median_oos_return=("oos_return", "median"),
            median_excess_return=("excess_return", "median"),
            median_oos_excess_return=("oos_excess_return", "median"),
            median_profit_factor=("profit_factor", "median"),
            median_sharpe=("sharpe", "median"),
            median_trades=("trades", "median"),
            median_drawdown=("max_drawdown", "median"),
            worst_drawdown=("max_drawdown", "min"),
        )
        .sort_values(
            ["profitability_pass_share", "profitable_share", "median_oos_return"],
            ascending=False,
        )
    )
    summary["research_priority"] = (
        (summary["instruments"] >= 5)
        & (summary["profitable_share"] >= 0.55)
        & (summary["stress_positive_share"] >= 0.55)
        & (summary["median_oos_return"] > 0)
        & (summary["worst_drawdown"] >= -0.40)
    )
    return summary


def run_mtf_research(
    config: MTFConfig,
    *,
    mode: str,
    markets: set[str] | None = None,
    symbols: set[str] | None = None,
    refresh: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if mode not in {"daily", "hourly"}:
        raise ValueError("MTF modu daily veya hourly olmalı.")
    interval = "1d" if mode == "daily" else "1h"
    minimum_bars = 400 if mode == "daily" else 2_000
    strategies = tuple(item for item in MTF_STRATEGIES if item.base_interval == interval)
    rows: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []

    for asset in config.assets:
        if markets and asset.market not in markets:
            continue
        if symbols and asset.symbol not in symbols:
            continue
        instrument = asset.instrument(interval)
        try:
            frame = fetch_history(instrument, config.history_start, refresh=refresh)
            if len(frame) < minimum_bars:
                raise DataError(
                    f"{asset.symbol} {interval} için yalnız {len(frame)} bar var; "
                    f"en az {minimum_bars} gerekli."
                )
            if (
                mode == "hourly"
                and asset.source == "yahoo"
                and frame.index.min() > pd.Timestamp("2020-01-10", tz="UTC")
            ):
                raise DataError(
                    "Yahoo 1 saatlik geçmişi 01.01.2020'ye ulaşmıyor; kısaltılmış test kabul edilmedi."
                )
        except Exception as error:  # noqa: BLE001 - one provider must not stop the matrix.
            errors.append(
                {
                    "symbol": asset.symbol,
                    "market": asset.market,
                    "interval": interval,
                    "error": str(error),
                }
            )
            continue

        benchmark = evaluate_benchmark(
            frame,
            initial_capital=10_000,
            cost_bps=asset.cost_bps,
            periods_per_year=instrument.periods_per_year,
        )
        for strategy in strategies:
            metrics = evaluate_candidate(
                frame,
                generate_mtf_signal(strategy.strategy_id, frame),
                initial_capital=10_000,
                cost_bps=asset.cost_bps,
                periods_per_year=instrument.periods_per_year,
            )
            row: dict[str, object] = {
                "strategy": strategy.strategy_id,
                "strategy_name": strategy.name,
                "architecture": strategy.architecture,
                "symbol": asset.symbol,
                "asset_name": asset.name,
                "market": asset.market,
                "interval": interval,
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
        market_summary = pd.DataFrame()
    else:
        base_groups = ["strategy", "strategy_name", "architecture"]
        summary = _summarize(results, base_groups)
        market_summary = _summarize(results, [*base_groups, "market"])

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv_atomic(results, STATE_DIR / f"mtf_{mode}_backtests.csv")
    _write_csv_atomic(summary, STATE_DIR / f"mtf_{mode}_summary.csv")
    _write_csv_atomic(market_summary, STATE_DIR / f"mtf_{mode}_market_summary.csv")
    health = {
        "updated_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "requested_start": config.history_start,
        "tested_rows": len(results),
        "tested_instruments": int(results["symbol"].nunique()) if not results.empty else 0,
        "errors": errors,
        "limitations": [
            "Evren güncel/sabit bileşenlerle geriye test edildiği için hayatta kalma yanlılığı taşır.",
            "Yahoo ücretsiz 1 saatlik geçmiş 2020'ye ulaşmazsa hisse/BIST/emtia testi reddedilir.",
            "Emtialar vadeli kontrat yerine işlem gören ETF vekilleriyle temsil edilir.",
        ],
    }
    _write_json_atomic(health, STATE_DIR / f"mtf_{mode}_health.json")
    if results.empty:
        raise DataError(
            f"{mode} MTF matrisi için veri alınamadı; ayrıntı state/mtf_{mode}_health.json içinde."
        )
    return results, summary, market_summary
