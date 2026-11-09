from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from .archival import download_plotly_archive, run_archival_research
from .config import load_config
from .data_import import import_mtf_csv
from .monitor import monitor_forever, run_cycle
from .mtf_config import load_mtf_config
from .mtf_research import run_mtf_research
from .paper import DEFAULT_DB, PaperBook, update_paper
from .research import run_research


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex Algo araştırma ve paper-test komutları")
    commands = parser.add_subparsers(dest="command", required=True)

    research = commands.add_parser(
        "research", help="Tüm strateji/enstrüman backtest matrisini çalıştır"
    )
    research.add_argument("--refresh", action="store_true", help="Yerel veri önbelleğini yenile")
    research.add_argument("--symbols", nargs="*", help="İsteğe bağlı sembol filtresi")

    paper_init = commands.add_parser("paper-init", help="Ortak 10.000 $ paper veritabanını oluştur")
    paper_init.add_argument("--db", type=Path, default=DEFAULT_DB)

    paper_update = commands.add_parser(
        "paper-update", help="Veriyi yenile ve paper portföyünü dengele"
    )
    paper_update.add_argument(
        "--cached", action="store_true", help="Ağ yerine mevcut veri önbelleğini kullan"
    )

    status = commands.add_parser("paper-status", help="Son paper durumunu JSON olarak göster")
    status.add_argument("--db", type=Path, default=DEFAULT_DB)

    monitor = commands.add_parser(
        "monitor", help="Araştırma ve paper zincirini belirli aralıkla güvenle yeniden dene"
    )
    monitor.add_argument("--interval-minutes", type=float, default=30.0)
    monitor.add_argument("--once", action="store_true", help="Tek kontrol yapıp çık")

    archive = commands.add_parser(
        "archive-research",
        help="MIT lisanslı 2013-2018 ABD arşiviyle ayrı bir ön eleme çalıştır",
    )
    archive.add_argument(
        "--broad",
        action="store_true",
        help="Üç seçili hisse yerine en az 1000 barı olan tüm arşiv hisselerini test et",
    )

    mtf = commands.add_parser(
        "mtf-research",
        help="1W→1D veya 1D+4H→1H çoklu-zaman araştırma matrisini çalıştır",
    )
    mtf.add_argument("--mode", choices=["daily", "hourly", "all"], default="all")
    mtf.add_argument("--refresh", action="store_true")
    mtf.add_argument("--markets", nargs="*", help="BIST30 ABD25 KRIPTO25 EMTIA filtresi")
    mtf.add_argument("--symbols", nargs="*", help="İsteğe bağlı sembol filtresi")

    importer = commands.add_parser(
        "mtf-import", help="Yerel bir OHLCV CSV dosyasını doğrulayıp MTF önbelleğine al"
    )
    importer.add_argument("--file", type=Path, required=True)
    importer.add_argument("--symbol", required=True, help="MTF evrenindeki sembol")
    importer.add_argument("--interval", choices=["1d", "1h"], required=True)
    importer.add_argument("--timestamp-column")
    importer.add_argument(
        "--timezone",
        default="UTC",
        help="Saat dilimsiz zaman damgalarının IANA dilimi (örn. Europe/Istanbul)",
    )
    importer.add_argument("--replace", action="store_true")
    return parser


def _paper_status(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"status": "not_initialized", "database": str(path)}
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        latest = connection.execute(
            "SELECT * FROM equity ORDER BY observed_at DESC LIMIT 1"
        ).fetchone()
        position_count = connection.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        trade_count = connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    return {
        "status": "ready",
        "database": str(path),
        "latest": dict(latest) if latest else None,
        "positions": position_count,
        "trades": trade_count,
    }


def main() -> None:
    arguments = _parser().parse_args()
    config = load_config()
    if arguments.command == "research":
        _, summary = run_research(
            config,
            symbols=set(arguments.symbols) if arguments.symbols else None,
            refresh=arguments.refresh,
        )
        print(summary.to_string(index=False) if not summary.empty else "Sonuç üretilemedi.")
    elif arguments.command == "paper-init":
        PaperBook(
            path=arguments.db,
            initial_capital=config.initial_capital,
            paper_days=config.paper_days,
        )
        print(json.dumps(_paper_status(arguments.db), ensure_ascii=False, indent=2))
    elif arguments.command == "paper-update":
        book = update_paper(config, refresh=not arguments.cached)
        print(json.dumps(_paper_status(book.path), ensure_ascii=False, indent=2))
    elif arguments.command == "paper-status":
        print(json.dumps(_paper_status(arguments.db), ensure_ascii=False, indent=2))
    elif arguments.command == "monitor":
        if arguments.once:
            successful = run_cycle()
            print(json.dumps({"successful": successful}, ensure_ascii=False))
        else:
            monitor_forever(arguments.interval_minutes)
    elif arguments.command == "archive-research":
        if arguments.broad:
            frames = download_plotly_archive(None, minimum_bars=1_000, persist_frames=False)
            _, summary = run_archival_research(config, frames, file_prefix="archival_breadth")
        else:
            _, summary = run_archival_research(config, download_plotly_archive())
        print(summary.to_string(index=False))
    elif arguments.command == "mtf-research":
        mtf_config = load_mtf_config()
        modes = ("daily", "hourly") if arguments.mode == "all" else (arguments.mode,)
        for mode in modes:
            _, summary, _ = run_mtf_research(
                mtf_config,
                mode=mode,
                markets=set(arguments.markets) if arguments.markets else None,
                symbols=set(arguments.symbols) if arguments.symbols else None,
                refresh=arguments.refresh,
            )
            print(f"\n[{mode}]\n{summary.to_string(index=False)}")
    elif arguments.command == "mtf-import":
        record = import_mtf_csv(
            load_mtf_config(),
            arguments.file,
            symbol=arguments.symbol,
            interval=arguments.interval,
            timestamp_column=arguments.timestamp_column,
            timezone=arguments.timezone,
            replace=arguments.replace,
        )
        print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
