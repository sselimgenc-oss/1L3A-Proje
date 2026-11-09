from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from codex_algo import paper
from codex_algo.config import AppConfig, Instrument, PaperSlot
from codex_algo.mtf_config import MTFAsset, MTFConfig
from codex_algo.paper import PaperBook, SignalSnapshot, collect_mtf_snapshots, collect_snapshots


def snapshot(
    strategy: str,
    symbol: str,
    signal: int,
    price: float,
    bar_time: str = "2026-10-14T00:00:00+00:00",
) -> SignalSnapshot:
    return SignalSnapshot(
        strategy=strategy,
        symbol=symbol,
        market="Test",
        signal=signal,
        price=price,
        cost_bps=10,
        bar_time=bar_time,
    )


def test_shared_portfolio_rebalances_and_records_trades(tmp_path) -> None:
    path = tmp_path / "paper.sqlite3"
    book = PaperBook(path, initial_capital=10_000)
    book.rebalance(
        [snapshot("a", "AAA", 1, 100), snapshot("b", "BBB", 0, 50)],
        observed_at="2026-10-14T10:00:00+00:00",
    )
    with sqlite3.connect(path) as connection:
        quantity = connection.execute("SELECT quantity FROM positions").fetchone()[0]
        equity = connection.execute("SELECT equity FROM equity").fetchone()[0]
        trades = connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    assert quantity == pytest.approx(50)
    assert equity == pytest.approx(9_995)
    assert trades == 1

    book.rebalance(
        [
            snapshot("a", "AAA", 0, 110, "2026-10-15T00:00:00+00:00"),
            snapshot("b", "BBB", 0, 50, "2026-10-15T00:00:00+00:00"),
        ],
        observed_at="2026-10-15T10:00:00+00:00",
    )
    with sqlite3.connect(path) as connection:
        positions = connection.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        trades = connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    assert positions == 0
    assert trades == 2


def test_repeated_same_bar_is_idempotent(tmp_path) -> None:
    path = tmp_path / "paper.sqlite3"
    book = PaperBook(path, initial_capital=10_000)
    snapshots = [snapshot("a", "AAA", 1, 100), snapshot("b", "BBB", 0, 50)]
    book.rebalance(snapshots, observed_at="2026-10-14T10:00:00+00:00")
    book.rebalance(snapshots, observed_at="2026-10-14T11:00:00+00:00")
    with sqlite3.connect(path) as connection:
        equity_rows = connection.execute("SELECT COUNT(*) FROM equity").fetchone()[0]
        trade_rows = connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        period = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
    assert equity_rows == 1
    assert trade_rows == 1
    assert period["start_at"] == "2026-10-14T10:00:00+00:00"
    assert period["end_at"] == "2026-12-13T10:00:00+00:00"


def test_collect_snapshots_only_uses_research_eligible_strategies(tmp_path, monkeypatch) -> None:
    summary_path = tmp_path / "strategy_summary.csv"
    pd.DataFrame(
        {
            "strategy": ["compression_breakout", "channel_reversion"],
            "paper_eligible": [True, False],
        }
    ).to_csv(summary_path, index=False)
    index = pd.date_range("2026-01-01", periods=300, freq="D", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1_000.0,
        },
        index=index,
    )
    frame.loc[index[-1], "open"] = 123.0
    config = AppConfig(
        initial_capital=10_000,
        paper_days=60,
        history_start="2020-01-01",
        instruments=(Instrument("TEST", "Test", "Test", "mock", "1d", 252, 5.0),),
        paper_slots=(
            PaperSlot("compression_breakout", "TEST"),
            PaperSlot("channel_reversion", "TEST"),
        ),
    )
    monkeypatch.setattr(paper, "fetch_history", lambda *args, **kwargs: frame)
    monkeypatch.setattr(
        paper,
        "generate_signal",
        lambda *args, **kwargs: pd.Series([0] * 298 + [1, 0], index=index),
    )

    snapshots = collect_snapshots(config, refresh=False, summary_path=summary_path)

    assert [item.strategy for item in snapshots] == ["compression_breakout"]
    assert snapshots[0].signal == 1
    assert snapshots[0].price == 123.0


def test_rebalance_closes_positions_removed_from_candidate_set(tmp_path) -> None:
    path = tmp_path / "paper.sqlite3"
    book = PaperBook(path, initial_capital=10_000)
    book.rebalance(
        [snapshot("a", "AAA", 1, 100), snapshot("b", "BBB", 0, 50)],
        observed_at="2026-10-14T10:00:00+00:00",
    )
    book.rebalance(
        [snapshot("b", "BBB", 0, 50, "2026-10-15T00:00:00+00:00")],
        observed_at="2026-10-15T10:00:00+00:00",
    )
    with sqlite3.connect(path) as connection:
        positions = connection.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        last_reason = connection.execute(
            "SELECT reason FROM trades ORDER BY id DESC LIMIT 1"
        ).fetchone()[0]
        cash = float(
            connection.execute("SELECT value FROM metadata WHERE key='cash'").fetchone()[0]
        )
        closed = connection.execute("SELECT net_pnl FROM closed_trades").fetchone()[0]
    assert positions == 0
    assert last_reason == "Aday listesinden çıktı"
    assert cash >= 0
    assert closed == pytest.approx(-10.0)


def test_rebalance_caps_buys_at_available_cash(tmp_path) -> None:
    path = tmp_path / "paper.sqlite3"
    book = PaperBook(path, initial_capital=10_000)
    book.rebalance(
        [snapshot("a", "AAA", 1, 100), snapshot("b", "BBB", 1, 50)],
        observed_at="2026-10-14T10:00:00+00:00",
    )
    with sqlite3.connect(path) as connection:
        cash = float(
            connection.execute("SELECT value FROM metadata WHERE key='cash'").fetchone()[0]
        )
    assert cash >= -1e-9


def test_rebalance_uses_weighted_average_for_additional_buy(tmp_path) -> None:
    path = tmp_path / "paper.sqlite3"
    book = PaperBook(path, initial_capital=10_000)
    book.rebalance(
        [snapshot("a", "AAA", 1, 100), snapshot("b", "BBB", 0, 50)],
        observed_at="2026-10-14T10:00:00+00:00",
    )
    book.rebalance(
        [
            snapshot("a", "AAA", 1, 80, "2026-10-15T00:00:00+00:00"),
            snapshot("b", "BBB", 0, 50, "2026-10-15T00:00:00+00:00"),
        ],
        observed_at="2026-10-15T10:00:00+00:00",
    )
    with sqlite3.connect(path) as connection:
        average_price, quantity = connection.execute(
            "SELECT average_price, quantity FROM positions WHERE strategy='a' AND symbol='AAA'"
        ).fetchone()
    assert quantity > 50
    assert 80 < average_price < 101


def test_collect_snapshots_requires_completed_research(tmp_path) -> None:
    config = AppConfig(10_000, 60, "2020-01-01", (), ())
    with pytest.raises(RuntimeError, match="araştırma çalıştırılmalı"):
        collect_snapshots(config, summary_path=tmp_path / "missing.csv")


def test_collect_mtf_snapshots_uses_only_pair_level_eligible_rows(tmp_path, monkeypatch) -> None:
    results_path = tmp_path / "mtf_daily_backtests.csv"
    pd.DataFrame(
        {
            "strategy": ["weekly_daily_breakout", "weekly_daily_pullback"],
            "symbol": ["AAA", "AAA"],
            "profitability_passes": [True, False],
        }
    ).to_csv(results_path, index=False)
    index = pd.date_range("2020-01-01", periods=500, freq="D", tz="UTC")
    frame = pd.DataFrame(
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1_000},
        index=index,
    )
    frame.loc[index[-1], "open"] = 105.0
    config = MTFConfig("2020-01-01", (MTFAsset("AAA", "AAA", "TEST", "mock", 5.0),))
    monkeypatch.setattr(paper, "fetch_history", lambda *args, **kwargs: frame)
    monkeypatch.setattr(
        paper,
        "generate_mtf_signal",
        lambda *args, **kwargs: pd.Series([0] * 498 + [1, 0], index=index),
    )

    snapshots = collect_mtf_snapshots(
        config, mode="daily", refresh=False, results_path=results_path
    )
    assert [(item.strategy, item.symbol) for item in snapshots] == [
        ("weekly_daily_breakout", "AAA")
    ]
    assert snapshots[0].signal == 1
    assert snapshots[0].price == 105.0
