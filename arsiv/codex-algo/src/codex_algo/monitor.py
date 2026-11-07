from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .config import STATE_DIR, load_config
from .mtf_config import load_mtf_config
from .mtf_research import run_mtf_research
from .paper import update_mtf_paper, update_paper
from .research import run_research

DEFAULT_STATUS = STATE_DIR / "monitor_status.json"


def _write_status(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def run_cycle(status_path: Path = DEFAULT_STATUS) -> bool:
    """Run the mechanical research-to-paper pipeline once, recording failures safely."""
    started = datetime.now(UTC)
    payload: dict[str, object] = {
        "started_at": started.isoformat(),
        "status": "running",
    }
    _write_status(status_path, payload)
    stages: dict[str, dict[str, object]] = {}
    errors: list[str] = []
    config = None
    mtf_config = None
    try:
        config = load_config()
        stages["config"] = {"status": "completed"}
    except Exception as error:  # noqa: BLE001 - status must retain setup failures.
        errors.append(str(error))
        stages["config"] = {"status": "waiting", "error": str(error)}
    try:
        mtf_config = load_mtf_config()
        stages["mtf_config"] = {"status": "completed"}
    except Exception as error:  # noqa: BLE001 - standard research can still run.
        errors.append(str(error))
        stages["mtf_config"] = {"status": "waiting", "error": str(error)}
    standard_ready = False

    if config is not None:
        try:
            results, summary = run_research(config, refresh=True)
            eligible = summary.loc[summary["paper_eligible"], "strategy"].astype(str).tolist()
            stages["research"] = {
                "status": "completed",
                "backtest_rows": len(results),
                "eligible_strategies": eligible,
            }
            standard_ready = True
        except Exception as error:  # noqa: BLE001 - other stages must still be attempted.
            errors.append(str(error))
            stages["research"] = {"status": "waiting", "error": str(error)}
    else:
        stages["research"] = {"status": "skipped", "reason": "Standart config yüklenemedi."}

    for mode in ("daily", "hourly"):
        if mtf_config is None:
            stages[f"mtf_{mode}"] = {"status": "skipped", "reason": "MTF config yüklenemedi."}
            continue
        try:
            # A verified local import must not be overwritten by a provider's shorter history.
            mtf_results, _, _ = run_mtf_research(mtf_config, mode=mode, refresh=True)
            stages[f"mtf_{mode}"] = {
                "status": "completed",
                "backtest_rows": len(mtf_results),
            }
            try:
                mtf_book = update_mtf_paper(mtf_config, mode=mode, refresh=False)
                stages[f"mtf_{mode}_paper"] = {
                    "status": "completed",
                    "database": str(mtf_book.path),
                }
            except Exception as error:  # noqa: BLE001 - the other account remains independent.
                errors.append(str(error))
                stages[f"mtf_{mode}_paper"] = {"status": "waiting", "error": str(error)}
        except Exception as error:  # noqa: BLE001 - modes are independent.
            errors.append(str(error))
            stages[f"mtf_{mode}"] = {"status": "waiting", "error": str(error)}
            stages[f"mtf_{mode}_paper"] = {
                "status": "skipped",
                "reason": "MTF araştırması tamamlanmadı.",
            }

    if standard_ready:
        try:
            book = update_paper(config, refresh=False)
            stages["paper"] = {"status": "completed", "database": str(book.path)}
        except Exception as error:  # noqa: BLE001 - status must preserve the failure.
            errors.append(str(error))
            stages["paper"] = {"status": "waiting", "error": str(error)}
    else:
        stages["paper"] = {
            "status": "skipped",
            "reason": "Standart araştırma tamamlanmadan paper portföyü güncellenmedi.",
        }

    success = not errors
    if success:
        payload.update(
            {
                "status": "completed",
                "finished_at": datetime.now(UTC).isoformat(),
                "stages": stages,
                "error": None,
            }
        )
    else:
        payload.update(
            {
                "status": "waiting",
                "finished_at": datetime.now(UTC).isoformat(),
                "stages": stages,
                "error": errors[0],
            }
        )
    _write_status(status_path, payload)
    return success


def monitor_forever(interval_minutes: float = 30.0, status_path: Path = DEFAULT_STATUS) -> None:
    if interval_minutes <= 0:
        raise ValueError("Kontrol aralığı sıfırdan büyük olmalı.")
    interval = timedelta(minutes=interval_minutes)
    while True:
        try:
            run_cycle(status_path)
        except Exception as error:  # noqa: BLE001 - hosted worker must remain alive.
            _write_status(
                status_path,
                {
                    "status": "waiting",
                    "finished_at": datetime.now(UTC).isoformat(),
                    "error": f"Beklenmeyen worker hatası: {error}",
                    "stages": {"worker": {"status": "waiting", "error": str(error)}},
                },
            )
        next_check = datetime.now(UTC) + interval
        current = json.loads(status_path.read_text(encoding="utf-8"))
        current["heartbeat_at"] = datetime.now(UTC).isoformat()
        current["next_check_at"] = next_check.isoformat()
        _write_status(status_path, current)
        time.sleep(interval.total_seconds())
