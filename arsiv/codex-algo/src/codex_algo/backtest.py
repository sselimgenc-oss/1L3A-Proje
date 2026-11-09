from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import validate_ohlcv


@dataclass(frozen=True)
class BacktestOutput:
    metrics: dict[str, float | int]
    equity: pd.DataFrame
    trades: pd.DataFrame


def evaluate_benchmark(
    frame: pd.DataFrame,
    *,
    initial_capital: float,
    cost_bps: float,
    periods_per_year: int,
    split_ratio: float = 0.70,
) -> dict[str, float]:
    """Long-only buy-and-hold reference using the same execution and cost model."""
    signal = pd.Series(1, index=frame.index, dtype="int64")
    split = max(1, min(len(frame) - 1, int(len(frame) * split_ratio)))
    full = run_backtest(
        frame,
        signal,
        initial_capital=initial_capital,
        cost_bps=cost_bps,
        periods_per_year=periods_per_year,
    )
    out_of_sample = run_backtest(
        frame.iloc[split:],
        signal.iloc[split:],
        initial_capital=initial_capital,
        cost_bps=cost_bps,
        periods_per_year=periods_per_year,
    )
    return {
        "benchmark_return": float(full.metrics["total_return"]),
        "benchmark_annual_return": float(full.metrics["annual_return"]),
        "benchmark_sharpe": float(full.metrics["sharpe"]),
        "benchmark_max_drawdown": float(full.metrics["max_drawdown"]),
        "benchmark_oos_return": float(out_of_sample.metrics["total_return"]),
    }


def _closed_trades(frame: pd.DataFrame, target: pd.Series, cost_bps: float) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    entry_time: pd.Timestamp | None = None
    entry_price: float | None = None
    previous = 0
    one_way_cost = cost_bps / 10_000

    for timestamp, current in target.items():
        current = int(current)
        price = float(frame.at[timestamp, "open"])
        if previous == 0 and current == 1:
            entry_time = timestamp
            entry_price = price
        elif previous == 1 and current == 0 and entry_time is not None and entry_price is not None:
            gross_return = price / entry_price - 1
            net_return = gross_return - 2 * one_way_cost
            rows.append(
                {
                    "entry_time": entry_time,
                    "exit_time": timestamp,
                    "entry_price": entry_price,
                    "exit_price": price,
                    "return": net_return,
                    "status": "closed",
                }
            )
            entry_time = None
            entry_price = None
        previous = current

    if previous == 1 and entry_time is not None and entry_price is not None:
        exit_price = float(frame["close"].iloc[-1])
        rows.append(
            {
                "entry_time": entry_time,
                "exit_time": frame.index[-1],
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return": exit_price / entry_price - 1 - one_way_cost,
                "status": "open",
            }
        )
    return pd.DataFrame(rows)


def run_backtest(
    frame: pd.DataFrame,
    signal: pd.Series,
    *,
    initial_capital: float = 10_000.0,
    cost_bps: float = 10.0,
    periods_per_year: int = 252,
) -> BacktestOutput:
    data = validate_ohlcv(frame)
    desired = signal.reindex(data.index).fillna(0).clip(0, 1).astype("int64")

    # Sinyal kapanışta oluşur; hedef pozisyon bir sonraki barın açılışında uygulanır.
    target = desired.shift(1).fillna(0).astype("int64")
    old_target = target.shift(1).fillna(0).astype("int64")
    previous_close = data["close"].shift(1)
    overnight_return = (data["open"] / previous_close - 1).fillna(0.0)
    intraday_return = (data["close"] / data["open"] - 1).fillna(0.0)
    gross_return = (1 + old_target * overnight_return) * (1 + target * intraday_return) - 1
    turnover = (target - old_target).abs()
    net_return = gross_return - turnover * (cost_bps / 10_000)
    net_return = net_return.clip(lower=-0.999999)
    equity = initial_capital * (1 + net_return).cumprod()
    peak = equity.cummax()
    drawdown = equity / peak - 1
    trades = _closed_trades(data, target, cost_bps)
    closed = trades[trades["status"] == "closed"] if not trades.empty else trades

    years = len(net_return) / periods_per_year
    annual_return = (equity.iloc[-1] / initial_capital) ** (1 / years) - 1 if years > 0 else 0.0
    volatility = float(net_return.std(ddof=0) * np.sqrt(periods_per_year))
    sharpe = (
        float(net_return.mean() / net_return.std(ddof=0) * np.sqrt(periods_per_year))
        if net_return.std(ddof=0) > 0
        else 0.0
    )
    if closed.empty:
        win_rate = 0.0
        profit_factor = 0.0
    else:
        trade_returns = closed["return"].astype(float)
        wins = float(trade_returns[trade_returns > 0].sum())
        losses = float(-trade_returns[trade_returns < 0].sum())
        win_rate = float((trade_returns > 0).mean())
        profit_factor = wins / losses if losses > 0 else (float("inf") if wins > 0 else 0.0)

    metrics: dict[str, float | int] = {
        "bars": len(data),
        "trades": len(closed),
        "total_return": float(equity.iloc[-1] / initial_capital - 1),
        "annual_return": float(annual_return),
        "annual_volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "win_rate": win_rate,
        "profit_factor": float(profit_factor),
        "exposure": float(target.mean()),
        "turnover": float(turnover.sum()),
    }
    curve = pd.DataFrame(
        {
            "return": net_return,
            "equity": equity,
            "drawdown": drawdown,
            "position": target,
        },
        index=data.index,
    )
    return BacktestOutput(metrics=metrics, equity=curve, trades=trades)


def evaluate_candidate(
    frame: pd.DataFrame,
    signal: pd.Series,
    *,
    initial_capital: float,
    cost_bps: float,
    periods_per_year: int,
    split_ratio: float = 0.70,
) -> dict[str, float | int | bool]:
    split = max(1, min(len(frame) - 1, int(len(frame) * split_ratio)))
    full = run_backtest(
        frame,
        signal,
        initial_capital=initial_capital,
        cost_bps=cost_bps,
        periods_per_year=periods_per_year,
    )
    training = run_backtest(
        frame.iloc[:split],
        signal.iloc[:split],
        initial_capital=initial_capital,
        cost_bps=cost_bps,
        periods_per_year=periods_per_year,
    )
    out_of_sample = run_backtest(
        frame.iloc[split:],
        signal.iloc[split:],
        initial_capital=initial_capital,
        cost_bps=cost_bps,
        periods_per_year=periods_per_year,
    )
    stress = run_backtest(
        frame,
        signal,
        initial_capital=initial_capital,
        cost_bps=cost_bps * 2,
        periods_per_year=periods_per_year,
    )
    result: dict[str, float | int | bool] = dict(full.metrics)
    result.update(
        {
            "training_sharpe": float(training.metrics["sharpe"]),
            "oos_sharpe": float(out_of_sample.metrics["sharpe"]),
            "oos_return": float(out_of_sample.metrics["total_return"]),
            "oos_annual_return": float(out_of_sample.metrics["annual_return"]),
            "stress_profit_factor": float(stress.metrics["profit_factor"]),
            "stress_return": float(stress.metrics["total_return"]),
        }
    )
    training_sharpe = float(training.metrics["sharpe"])
    oos_sharpe = float(out_of_sample.metrics["sharpe"])
    result["strict_passes"] = bool(
        int(full.metrics["trades"]) >= 30
        and float(full.metrics["max_drawdown"]) >= -0.20
        and float(full.metrics["profit_factor"]) >= 1.30
        and float(full.metrics["sharpe"]) >= 1.0
        and float(stress.metrics["profit_factor"]) >= 1.10
        and oos_sharpe >= max(0.0, training_sharpe * 0.50)
    )
    annual_return = float(full.metrics["annual_return"])
    max_drawdown = abs(float(full.metrics["max_drawdown"]))
    result["calmar"] = annual_return / max_drawdown if max_drawdown > 0 else 0.0
    result["profitability_passes"] = bool(
        int(full.metrics["trades"]) >= 15
        and float(full.metrics["total_return"]) > 0
        and float(full.metrics["max_drawdown"]) >= -0.35
        and float(full.metrics["profit_factor"]) >= 1.05
        and float(out_of_sample.metrics["total_return"]) > 0
        and float(stress.metrics["total_return"]) > 0
        and float(stress.metrics["profit_factor"]) >= 1.0
    )
    result["passes_gates"] = result["profitability_passes"]
    return result
