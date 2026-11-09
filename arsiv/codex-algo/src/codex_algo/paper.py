from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from .config import STATE_DIR, AppConfig
from .data import fetch_history
from .mtf_config import MTFConfig
from .mtf_strategies import generate_mtf_signal
from .strategies import generate_signal

DEFAULT_DB = STATE_DIR / "paper.sqlite3"
DEFAULT_MTF_DAILY_DB = STATE_DIR / "paper_mtf_daily.sqlite3"
DEFAULT_MTF_HOURLY_DB = STATE_DIR / "paper_mtf_hourly.sqlite3"
DEFAULT_SUMMARY = STATE_DIR / "strategy_summary.csv"


@dataclass(frozen=True)
class SignalSnapshot:
    strategy: str
    symbol: str
    market: str
    signal: int
    price: float
    cost_bps: float
    bar_time: str


SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS positions (
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    quantity REAL NOT NULL,
    average_price REAL NOT NULL,
    last_price REAL NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (strategy, symbol)
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    executed_at TEXT NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    action TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    fee REAL NOT NULL,
    reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS closed_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    closed_at TEXT NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    quantity REAL NOT NULL,
    entry_cost REAL NOT NULL,
    exit_price REAL NOT NULL,
    net_pnl REAL NOT NULL,
    net_return REAL NOT NULL,
    reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS signals (
    observed_at TEXT NOT NULL,
    bar_time TEXT NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    signal INTEGER NOT NULL,
    price REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS equity (
    observed_at TEXT PRIMARY KEY,
    equity REAL NOT NULL,
    cash REAL NOT NULL,
    gross_exposure REAL NOT NULL,
    drawdown REAL NOT NULL
);
"""


class PaperBook:
    def __init__(
        self,
        path: Path = DEFAULT_DB,
        initial_capital: float = 10_000.0,
        paper_days: int = 60,
    ) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            position_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(positions)")
            }
            if "cost_bps" not in position_columns:
                connection.execute(
                    "ALTER TABLE positions ADD COLUMN cost_bps REAL NOT NULL DEFAULT 0"
                )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(key, value) VALUES ('initial_capital', ?)",
                (str(initial_capital),),
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(key, value) VALUES ('cash', ?)",
                (str(initial_capital),),
            )
            connection.execute(
                "INSERT OR IGNORE INTO metadata(key, value) VALUES ('paper_days', ?)",
                (str(paper_days),),
            )

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _metadata_float(self, connection: sqlite3.Connection, key: str) -> float:
        row = connection.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise RuntimeError(f"Paper metadata eksik: {key}")
        return float(row["value"])

    def rebalance(self, snapshots: list[SignalSnapshot], observed_at: str | None = None) -> None:
        if not snapshots:
            raise ValueError("Paper güncellemesi için en az bir sinyal gerekir.")
        keys = [(item.strategy, item.symbol) for item in snapshots]
        if len(keys) != len(set(keys)):
            raise ValueError("Paper güncellemesinde aynı strateji/sembol birden fazla kez var.")
        observed_at = observed_at or datetime.now(UTC).isoformat()
        with self.connect() as connection:
            latest_bars = {
                (row["strategy"], row["symbol"]): row["bar_time"]
                for row in connection.execute(
                    """SELECT strategy, symbol, MAX(bar_time) AS bar_time
                    FROM signals GROUP BY strategy, symbol"""
                ).fetchall()
            }
            existing_rows = connection.execute("SELECT * FROM positions").fetchall()
            existing = {(row["strategy"], row["symbol"]): row for row in existing_rows}
            snapshot_keys = set(keys)
            stale_keys = set(existing) - snapshot_keys
            if not stale_keys and all(
                latest_bars.get((item.strategy, item.symbol)) == item.bar_time for item in snapshots
            ):
                return
            start_row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'start_at'"
            ).fetchone()
            if start_row is None:
                start_at = datetime.fromisoformat(observed_at)
                paper_days = int(self._metadata_float(connection, "paper_days"))
                connection.execute(
                    "INSERT INTO metadata(key, value) VALUES ('start_at', ?)",
                    (start_at.isoformat(),),
                )
                connection.execute(
                    "INSERT INTO metadata(key, value) VALUES ('end_at', ?)",
                    ((start_at + timedelta(days=paper_days)).isoformat(),),
                )
            cash = self._metadata_float(connection, "cash")
            prices = {(item.strategy, item.symbol): item.price for item in snapshots}
            marked_positions = sum(
                float(row["quantity"]) * prices.get(key, float(row["last_price"]))
                for key, row in existing.items()
            )
            equity_before = cash + marked_positions
            slot_value = equity_before / len(snapshots)
            historical_peak_row = connection.execute(
                "SELECT MAX(equity) AS peak FROM equity"
            ).fetchone()
            historical_peak = float(historical_peak_row["peak"] or equity_before)
            risk_halt = equity_before / max(historical_peak, equity_before) - 1 <= -0.15

            items = {(item.strategy, item.symbol): item for item in snapshots}
            target_quantities: dict[tuple[str, str], float] = {}
            for key, item in items.items():
                old_quantity = float(existing[key]["quantity"]) if key in existing else 0.0
                desired = (slot_value / item.price) if item.signal == 1 else 0.0
                # -%15 freninden sonra mevcut işlemler korunabilir ama yeni risk eklenmez.
                target_quantities[key] = min(desired, old_quantity) if risk_halt else desired

            # Önce satışlar yapılır. Aday listesinden çıkan pozisyonlar da eski fiyatıyla
            # kapatılır; böylece yeni adaylar aynı sermayeyi ikinci kez kullanamaz.
            working: dict[tuple[str, str], dict[str, float | str]] = {}
            for key in set(existing) | snapshot_keys:
                old = existing.get(key)
                item = items.get(key)
                old_quantity = float(old["quantity"]) if old else 0.0
                old_average = float(old["average_price"]) if old else 0.0
                price = item.price if item else float(old["last_price"])
                market = item.market if item else str(old["market"])
                cost_bps = item.cost_bps if item else float(old["cost_bps"])
                target = target_quantities.get(key, 0.0)
                sell_quantity = max(0.0, old_quantity - target)
                if sell_quantity > 1e-10:
                    fee = sell_quantity * price * cost_bps / 10_000
                    cash += sell_quantity * price - fee
                    net_exit_price = price * (1 - cost_bps / 10_000)
                    net_pnl = sell_quantity * (net_exit_price - old_average)
                    net_return = net_exit_price / old_average - 1 if old_average else 0.0
                    reason = (
                        "Aday listesinden çıktı" if key in stale_keys else "Model hedefi 0/azalt"
                    )
                    connection.execute(
                        """INSERT INTO trades(
                            executed_at, strategy, symbol, market, action, quantity, price, fee, reason
                        ) VALUES (?, ?, ?, ?, 'SAT', ?, ?, ?, ?)""",
                        (
                            observed_at,
                            key[0],
                            key[1],
                            market,
                            sell_quantity,
                            price,
                            fee,
                            reason,
                        ),
                    )
                    connection.execute(
                        """INSERT INTO closed_trades(
                            closed_at, strategy, symbol, market, quantity, entry_cost,
                            exit_price, net_pnl, net_return, reason
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            observed_at,
                            key[0],
                            key[1],
                            market,
                            sell_quantity,
                            old_average,
                            price,
                            net_pnl,
                            net_return,
                            reason,
                        ),
                    )
                working[key] = {
                    "quantity": old_quantity - sell_quantity,
                    "average_price": old_average,
                    "price": price,
                    "market": market,
                    "cost_bps": cost_bps,
                }

            # Satışlardan sonra alımlar nakit sınırıyla yapılır; ücretler nakdi negatife
            # düşüremez ve ek alış maliyeti ağırlıklı ortalamayla tutulur.
            for key, item in items.items():
                state = working[key]
                old_quantity = float(state["quantity"])
                wanted = max(0.0, target_quantities[key] - old_quantity)
                one_unit_cash = item.price * (1 + item.cost_bps / 10_000)
                buy_quantity = min(wanted, max(0.0, cash) / one_unit_cash)
                if buy_quantity > 1e-10:
                    fee = buy_quantity * item.price * item.cost_bps / 10_000
                    cash -= buy_quantity * item.price + fee
                    total_quantity = old_quantity + buy_quantity
                    old_cost = old_quantity * float(state["average_price"])
                    acquisition_cost = item.price * (1 + item.cost_bps / 10_000)
                    state["average_price"] = (
                        old_cost + buy_quantity * acquisition_cost
                    ) / total_quantity
                    state["quantity"] = total_quantity
                    connection.execute(
                        """INSERT INTO trades(
                            executed_at, strategy, symbol, market, action, quantity, price, fee, reason
                        ) VALUES (?, ?, ?, ?, 'AL', ?, ?, ?, ?)""",
                        (
                            observed_at,
                            item.strategy,
                            item.symbol,
                            item.market,
                            buy_quantity,
                            item.price,
                            fee,
                            "Risk freni" if risk_halt else "Model hedefi 1",
                        ),
                    )

            for key, state in working.items():
                quantity = float(state["quantity"])
                if quantity <= 1e-10:
                    connection.execute(
                        "DELETE FROM positions WHERE strategy = ? AND symbol = ?", key
                    )
                    continue
                connection.execute(
                    """INSERT INTO positions(
                        strategy, symbol, market, quantity, average_price, last_price, updated_at,
                        cost_bps
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(strategy, symbol) DO UPDATE SET
                        market=excluded.market, quantity=excluded.quantity,
                        average_price=excluded.average_price, last_price=excluded.last_price,
                        updated_at=excluded.updated_at, cost_bps=excluded.cost_bps""",
                    (
                        key[0],
                        key[1],
                        state["market"],
                        quantity,
                        state["average_price"],
                        state["price"],
                        observed_at,
                        state["cost_bps"],
                    ),
                )

            for item in snapshots:
                key = (item.strategy, item.symbol)
                if latest_bars.get(key) != item.bar_time:
                    connection.execute(
                        "INSERT INTO signals VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (
                            observed_at,
                            item.bar_time,
                            item.strategy,
                            item.symbol,
                            item.market,
                            item.signal,
                            item.price,
                        ),
                    )

            connection.execute(
                "INSERT INTO metadata(key, value) VALUES ('cash', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(cash),),
            )
            market_value = sum(
                row[0]
                for row in connection.execute(
                    "SELECT quantity * last_price FROM positions"
                ).fetchall()
            )
            current_equity = cash + float(market_value)
            peak = max(current_equity, historical_peak)
            drawdown = current_equity / peak - 1 if peak else 0.0
            connection.execute(
                "INSERT OR REPLACE INTO equity VALUES (?, ?, ?, ?, ?)",
                (observed_at, current_equity, cash, float(market_value), drawdown),
            )


def _eligible_strategies(summary_path: Path = DEFAULT_SUMMARY) -> set[str]:
    if not summary_path.exists():
        raise RuntimeError(
            "Paper-test başlamadan önce araştırma çalıştırılmalı: "
            "state/strategy_summary.csv bulunamadı."
        )
    summary = pd.read_csv(summary_path)
    required = {"strategy", "paper_eligible"}
    if summary.empty or not required.issubset(summary.columns):
        raise RuntimeError("Araştırma özeti boş veya paper_eligible alanı içermiyor.")
    eligible = summary.loc[
        summary["paper_eligible"].astype(str).str.lower().isin({"true", "1"}), "strategy"
    ]
    selected = set(eligible.astype(str))
    if not selected:
        raise RuntimeError("Kârlılık ve dayanıklılık elemesini geçen paper-test adayı yok.")
    return selected


def collect_snapshots(
    config: AppConfig,
    *,
    refresh: bool = True,
    summary_path: Path = DEFAULT_SUMMARY,
) -> list[SignalSnapshot]:
    snapshots: list[SignalSnapshot] = []
    histories: dict[str, pd.DataFrame] = {}
    eligible = _eligible_strategies(summary_path)
    selected_slots = [slot for slot in config.paper_slots if slot.strategy in eligible]
    if not selected_slots:
        raise RuntimeError("Uygun stratejiler için yapılandırılmış paper-test dilimi yok.")
    for slot in selected_slots:
        instrument = config.instrument(slot.symbol)
        if slot.symbol not in histories:
            histories[slot.symbol] = fetch_history(
                instrument, config.history_start, refresh=refresh
            )
        frame = histories[slot.symbol]
        if len(frame) < 2:
            raise RuntimeError(
                f"{slot.symbol} için sinyal mumu ve sonraki işlem mumu birlikte bulunamadı."
            )
        signal = generate_signal(slot.strategy, frame)
        snapshots.append(
            SignalSnapshot(
                strategy=slot.strategy,
                symbol=slot.symbol,
                market=instrument.market,
                signal=int(signal.iloc[-2]),
                price=float(frame["open"].iloc[-1]),
                cost_bps=instrument.cost_bps,
                bar_time=frame.index[-1].isoformat(),
            )
        )
    return snapshots


def update_paper(config: AppConfig, *, refresh: bool = True) -> PaperBook:
    snapshots = collect_snapshots(config, refresh=refresh)
    book = PaperBook(initial_capital=config.initial_capital, paper_days=config.paper_days)
    book.rebalance(snapshots)
    return book


def collect_mtf_snapshots(
    config: MTFConfig,
    *,
    mode: str,
    refresh: bool = False,
    results_path: Path | None = None,
) -> list[SignalSnapshot]:
    if mode not in {"daily", "hourly"}:
        raise ValueError("MTF paper modu daily veya hourly olmalı.")
    interval = "1d" if mode == "daily" else "1h"
    path = results_path or STATE_DIR / f"mtf_{mode}_backtests.csv"
    if not path.exists():
        raise RuntimeError(f"MTF paper öncesi araştırma sonucu bulunamadı: {path}")
    results = pd.read_csv(path)
    required = {"strategy", "symbol", "profitability_passes"}
    if results.empty or not required.issubset(results.columns):
        raise RuntimeError("MTF araştırma sonucu boş veya uygunluk alanları eksik.")
    eligible = results[
        results["profitability_passes"].astype(str).str.lower().isin({"true", "1"})
    ].drop_duplicates(["strategy", "symbol"])
    if eligible.empty:
        raise RuntimeError(f"{mode} MTF için paper uygun strateji × varlık çifti yok.")

    assets = {asset.symbol: asset for asset in config.assets}
    histories: dict[str, pd.DataFrame] = {}
    snapshots: list[SignalSnapshot] = []
    for row in eligible.itertuples(index=False):
        symbol = str(row.symbol)
        strategy = str(row.strategy)
        if symbol not in assets:
            continue
        asset = assets[symbol]
        instrument = asset.instrument(interval)
        if symbol not in histories:
            histories[symbol] = fetch_history(instrument, config.history_start, refresh=refresh)
        frame = histories[symbol]
        if len(frame) < 2:
            raise RuntimeError(
                f"{symbol} {interval} için sinyal ve sonraki işlem mumu birlikte bulunamadı."
            )
        signal = generate_mtf_signal(strategy, frame)
        snapshots.append(
            SignalSnapshot(
                strategy=strategy,
                symbol=symbol,
                market=asset.market,
                signal=int(signal.iloc[-2]),
                price=float(frame["open"].iloc[-1]),
                cost_bps=asset.cost_bps,
                bar_time=frame.index[-1].isoformat(),
            )
        )
    if not snapshots:
        raise RuntimeError(f"{mode} MTF uygun çiftleri yapılandırılmış evrenle eşleşmedi.")
    return snapshots


def update_mtf_paper(
    config: MTFConfig,
    *,
    mode: str,
    refresh: bool = False,
    results_path: Path | None = None,
    database_path: Path | None = None,
) -> PaperBook:
    snapshots = collect_mtf_snapshots(
        config,
        mode=mode,
        refresh=refresh,
        results_path=results_path,
    )
    default_path = DEFAULT_MTF_DAILY_DB if mode == "daily" else DEFAULT_MTF_HOURLY_DB
    book = PaperBook(path=database_path or default_path, initial_capital=10_000, paper_days=60)
    book.rebalance(snapshots)
    return book
