from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import ROOT, Instrument

DEFAULT_MTF_CONFIG = ROOT / "config" / "mtf_universe.json"


@dataclass(frozen=True)
class MTFAsset:
    symbol: str
    name: str
    market: str
    source: str
    cost_bps: float

    def instrument(self, interval: str) -> Instrument:
        if interval == "1d":
            periods = 365 if self.market == "KRIPTO25" else 252
        elif interval == "1h":
            periods = 365 * 24 if self.market == "KRIPTO25" else 252 * 7
        else:
            raise ValueError(f"Desteklenmeyen temel zaman dilimi: {interval}")
        return Instrument(
            symbol=self.symbol,
            name=self.name,
            market=self.market,
            source=self.source,
            interval=interval,
            periods_per_year=periods,
            cost_bps=self.cost_bps,
        )


@dataclass(frozen=True)
class MTFConfig:
    history_start: str
    assets: tuple[MTFAsset, ...]


def load_mtf_config(path: Path = DEFAULT_MTF_CONFIG) -> MTFConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return MTFConfig(
        history_start=str(payload["history_start"]),
        assets=tuple(MTFAsset(**row) for row in payload["assets"]),
    )
