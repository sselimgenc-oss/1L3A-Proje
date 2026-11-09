from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = Path(os.environ.get("CODEX_ALGO_RUNTIME_DIR", ROOT)).expanduser().resolve()
STATE_DIR = RUNTIME_ROOT / "state"
DATA_DIR = RUNTIME_ROOT / "data"
DEFAULT_CONFIG = ROOT / "config" / "universe.json"


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    market: str
    source: str
    interval: str
    periods_per_year: int
    cost_bps: float


@dataclass(frozen=True)
class PaperSlot:
    strategy: str
    symbol: str


@dataclass(frozen=True)
class AppConfig:
    initial_capital: float
    paper_days: int
    history_start: str
    instruments: tuple[Instrument, ...]
    paper_slots: tuple[PaperSlot, ...]

    def instrument(self, symbol: str) -> Instrument:
        for item in self.instruments:
            if item.symbol == symbol:
                return item
        raise KeyError(f"Bilinmeyen sembol: {symbol}")


def load_config(path: Path = DEFAULT_CONFIG) -> AppConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AppConfig(
        initial_capital=float(payload["initial_capital"]),
        paper_days=int(payload["paper_days"]),
        history_start=str(payload["history_start"]),
        instruments=tuple(Instrument(**row) for row in payload["instruments"]),
        paper_slots=tuple(PaperSlot(**row) for row in payload["paper_slots"]),
    )
