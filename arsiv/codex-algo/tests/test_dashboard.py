from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from codex_algo.dashboard import PAGES, _paper_statistics, _periodic_returns, _scorecard


def test_dashboard_renders_with_empty_research_results() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path).run(timeout=15)
    assert not app.exception
    assert app.title[0].value == "Codex Algo — Bağımsız Paper Test"
    assert tuple(app.sidebar.radio[0].options) == PAGES


def test_every_dashboard_page_renders() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path).run(timeout=15)
    for page in PAGES:
        app.sidebar.radio[0].set_value(page)
        app.run(timeout=15)
        assert not app.exception, page


def test_hosted_dashboard_fails_closed_without_password(monkeypatch) -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    monkeypatch.setenv("CODEX_ALGO_HOSTED", "1")
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    app = AppTest.from_file(app_path).run(timeout=15)
    assert not app.exception
    assert any("erişim kapatıldı" in error.value for error in app.error)


def test_hosted_dashboard_accepts_unicode_password(monkeypatch) -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    monkeypatch.setenv("CODEX_ALGO_HOSTED", "1")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "güvenli-şifre")
    app = AppTest.from_file(app_path).run(timeout=15)
    app.text_input[0].set_value("güvenli-şifre")
    app.button[0].click()
    app.run(timeout=15)
    assert not app.exception
    assert any(title.value == "Codex Algo — Bağımsız Paper Test" for title in app.title)


def test_scorecard_marks_small_samples_as_accumulating() -> None:
    summary = pd.DataFrame(
        {
            "strategy": ["test"],
            "strategy_name": ["Test"],
            "profitable_share": [0.75],
            "median_oos_return": [0.10],
            "median_profit_factor": [1.5],
            "worst_drawdown": [-0.10],
            "instruments": [8],
            "median_trades": [10],
        }
    )
    card = _scorecard(summary)
    assert card.iloc[0]["Güven"] == "veri birikiyor"
    assert pd.isna(card.iloc[0]["Genel"])


def test_periodic_returns_use_equity_observations() -> None:
    equity = pd.DataFrame(
        {
            "observed_at": ["2026-10-10T12:00:00Z", "2026-10-11T12:00:00Z"],
            "equity": [10_000.0, 10_100.0],
        }
    )
    result = _periodic_returns(equity, "Günlük")
    assert result.iloc[-1]["Getiri"] == pytest.approx(0.01)


def test_daily_returns_respect_istanbul_midnight() -> None:
    equity = pd.DataFrame(
        {
            "observed_at": ["2026-10-10T20:30:00Z", "2026-10-10T21:30:00Z"],
            "equity": [10_000.0, 10_100.0],
        }
    )
    result = _periodic_returns(equity, "Günlük")
    assert result["Dönem"].tolist() == ["10.10.2026", "11.10.2026"]
    assert result.iloc[-1]["Getiri"] == pytest.approx(0.01)


def test_paper_statistics_use_closed_slices() -> None:
    equity = pd.DataFrame(
        {
            "observed_at": pd.date_range("2026-01-01", periods=12, freq="D", tz="UTC"),
            "equity": [10_000 + value for value in range(0, 120, 10)],
        }
    )
    closed = pd.DataFrame({"net_pnl": [100.0, -50.0, 25.0]})
    result = _paper_statistics(equity, closed)
    assert result["win_rate"] == pytest.approx(2 / 3)
    assert result["profit_factor"] == pytest.approx(2.5)
    assert result["expectancy"] == pytest.approx(25.0)
