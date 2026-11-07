from __future__ import annotations

import json

import pandas as pd

from codex_algo import monitor


def test_monitor_cycle_records_provider_failure_and_returns(tmp_path, monkeypatch) -> None:
    status_path = tmp_path / "monitor_status.json"
    monkeypatch.setattr(monitor, "load_config", lambda: object())
    monkeypatch.setattr(monitor, "load_mtf_config", lambda: object())

    def fail(*args, **kwargs):
        raise RuntimeError("provider blocked")

    monkeypatch.setattr(monitor, "run_research", fail)
    monkeypatch.setattr(monitor, "run_mtf_research", fail)

    assert monitor.run_cycle(status_path) is False
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["status"] == "waiting"
    assert status["error"] == "provider blocked"
    assert status["stages"]["research"]["status"] == "waiting"
    assert status["stages"]["mtf_daily"]["status"] == "waiting"
    assert status["stages"]["mtf_hourly"]["status"] == "waiting"
    assert status["stages"]["paper"]["status"] == "skipped"


def test_monitor_cycle_runs_paper_after_eligibility_filter(tmp_path, monkeypatch) -> None:
    status_path = tmp_path / "monitor_status.json"
    book = type("Book", (), {"path": tmp_path / "paper.sqlite3"})()
    summary = pd.DataFrame({"strategy": ["compression_breakout"], "paper_eligible": [True]})
    monkeypatch.setattr(monitor, "load_config", lambda: object())
    monkeypatch.setattr(monitor, "load_mtf_config", lambda: object())
    monkeypatch.setattr(
        monitor, "run_research", lambda *args, **kwargs: (pd.DataFrame([{}]), summary)
    )
    monkeypatch.setattr(
        monitor,
        "run_mtf_research",
        lambda *args, **kwargs: (pd.DataFrame([{}]), pd.DataFrame(), pd.DataFrame()),
    )
    monkeypatch.setattr(monitor, "update_paper", lambda *args, **kwargs: book)
    monkeypatch.setattr(monitor, "update_mtf_paper", lambda *args, **kwargs: book)

    assert monitor.run_cycle(status_path) is True
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["status"] == "completed"
    assert status["stages"]["research"]["eligible_strategies"] == ["compression_breakout"]
    assert status["stages"]["paper"]["status"] == "completed"


def test_monitor_records_config_failure_instead_of_crashing(tmp_path, monkeypatch) -> None:
    status_path = tmp_path / "monitor_status.json"
    monkeypatch.setattr(
        monitor, "load_config", lambda: (_ for _ in ()).throw(ValueError("bad config"))
    )
    monkeypatch.setattr(monitor, "load_mtf_config", lambda: object())
    monkeypatch.setattr(
        monitor,
        "run_mtf_research",
        lambda *args, **kwargs: (pd.DataFrame([{}]), pd.DataFrame(), pd.DataFrame()),
    )

    assert monitor.run_cycle(status_path) is False
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["stages"]["config"]["status"] == "waiting"
    assert status["stages"]["research"]["status"] == "skipped"
