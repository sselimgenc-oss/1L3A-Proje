from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from streamlit.web import cli as streamlit_cli

from .config import ROOT, RUNTIME_ROOT
from .monitor import monitor_forever


def _monitor(interval_minutes: float) -> None:
    monitor_forever(interval_minutes)


def main() -> None:
    os.environ["CODEX_ALGO_HOSTED"] = "1"
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    interval = float(os.environ.get("MONITOR_INTERVAL_MINUTES", "30"))
    if interval <= 0:
        raise ValueError("MONITOR_INTERVAL_MINUTES sıfırdan büyük olmalı.")
    worker = threading.Thread(
        target=_monitor,
        args=(interval,),
        name="codex-algo-monitor",
        daemon=True,
    )
    worker.start()

    port = os.environ.get("PORT", "8501")
    app_path = Path(ROOT, "app.py")
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address",
        "0.0.0.0",
        "--server.port",
        port,
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    raise SystemExit(streamlit_cli.main())


if __name__ == "__main__":
    main()
