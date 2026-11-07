from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from .catalog import EXCLUDED_CLAUDE_STRATEGIES, STRATEGIES
from .config import ROOT, STATE_DIR, load_config
from .mtf_strategies import MTF_STRATEGIES
from .paper import DEFAULT_DB, DEFAULT_MTF_DAILY_DB, DEFAULT_MTF_HOURLY_DB

PAGES = (
    "Özet",
    "Karne",
    "Grafikler",
    "Takvim",
    "Açık pozisyonlar",
    "İşlem geçmişi",
    "İstatistik",
    "Stratejiler",
    "Koç",
    "Öğrenme",
    "Rapor",
    "Dönemsel getiri",
    "Risk",
)
ISTANBUL_TIMEZONE = "Europe/Istanbul"


def _query(path: Path, query: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    with sqlite3.connect(path) as connection:
        return pd.read_sql_query(query, connection)


def _paper_snapshot(path: Path) -> dict[str, pd.DataFrame]:
    tables = {
        "equity": "SELECT * FROM equity ORDER BY observed_at",
        "positions": "SELECT * FROM positions ORDER BY market, symbol",
        "trades": "SELECT * FROM trades ORDER BY id DESC",
        "closed_trades": "SELECT * FROM closed_trades ORDER BY id DESC",
        "signals": "SELECT * FROM signals ORDER BY observed_at DESC",
        "metadata": "SELECT key, value FROM metadata",
    }
    if not path.exists():
        return {name: pd.DataFrame() for name in tables}
    with sqlite3.connect(path) as connection:
        connection.execute("BEGIN")
        snapshot: dict[str, pd.DataFrame] = {}
        for name, query in tables.items():
            try:
                snapshot[name] = pd.read_sql_query(query, connection)
            except (pd.errors.DatabaseError, sqlite3.DatabaseError):
                snapshot[name] = pd.DataFrame()
        connection.commit()
    return snapshot


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _account_status(path: Path, label: str) -> dict[str, object]:
    snapshot = _paper_snapshot(path)
    equity = snapshot["equity"]
    positions = snapshot["positions"]
    trades = snapshot["trades"]
    return {
        "Hesap": label,
        "Durum": "çalışıyor" if not equity.empty else "veri/aday bekliyor",
        "Değer": float(equity.iloc[-1]["equity"]) if not equity.empty else 10_000.0,
        "Açık": len(positions),
        "Hareket": len(trades),
    }


def _percent(value: float) -> str:
    return f"{value * 100:,.2f}%"


def _to_istanbul(value: object) -> str:
    try:
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        return timestamp.tz_convert(ISTANBUL_TIMEZONE).strftime("%d.%m.%Y %H:%M")
    except (TypeError, ValueError):
        return "—"


def _periodic_returns(equity: pd.DataFrame, frequency: str) -> pd.DataFrame:
    if equity.empty or not {"observed_at", "equity"}.issubset(equity.columns):
        return pd.DataFrame(columns=["Dönem", "Getiri"])
    frame = equity.loc[:, ["observed_at", "equity"]].copy()
    frame["observed_at"] = pd.to_datetime(frame["observed_at"], utc=True, errors="coerce")
    frame["equity"] = pd.to_numeric(frame["equity"], errors="coerce")
    frame = frame.dropna().set_index("observed_at").sort_index()
    if frame.empty:
        return pd.DataFrame(columns=["Dönem", "Getiri"])
    frame.index = frame.index.tz_convert(ISTANBUL_TIMEZONE)
    rule = {"Günlük": "D", "Haftalık": "W-SUN", "Aylık": "ME"}[frequency]
    closes = frame["equity"].resample(rule).last().dropna()
    returns = closes.pct_change().fillna(closes.iloc[0] / closes.iloc[0] - 1)
    return pd.DataFrame(
        {
            "Dönem": returns.index.strftime("%d.%m.%Y"),
            "Getiri": returns.to_numpy(),
        }
    )


def _scorecard(summary: pd.DataFrame) -> pd.DataFrame:
    required = {
        "strategy",
        "profitable_share",
        "median_oos_return",
        "median_profit_factor",
        "worst_drawdown",
        "instruments",
        "median_trades",
    }
    if summary.empty or not required.issubset(summary.columns):
        return pd.DataFrame()
    result = pd.DataFrame()
    result["Strateji"] = summary.get("strategy_name", summary["strategy"]).fillna(
        summary["strategy"]
    )
    oos = pd.to_numeric(summary["median_oos_return"], errors="coerce").fillna(0.0)
    profit_factor = pd.to_numeric(summary["median_profit_factor"], errors="coerce").fillna(0.0)
    drawdown = pd.to_numeric(summary["worst_drawdown"], errors="coerce").fillna(-1.0)
    trades = pd.to_numeric(summary["median_trades"], errors="coerce").fillna(0.0)
    instruments = pd.to_numeric(summary["instruments"], errors="coerce").fillna(0.0)
    breadth = pd.to_numeric(summary["profitable_share"], errors="coerce").fillna(0.0)
    result["Getiri"] = (oos * 50).clip(0, 10)
    result["Risk"] = (10 + drawdown * 25).clip(0, 10)
    result["Beklenti"] = ((profit_factor - 1) * 10).clip(0, 10)
    result["Örneklem"] = (trades / 30 * 10).clip(0, 10)
    result["Enstrüman kapsamı"] = (instruments / 20 * 10).clip(0, 10)
    result["Kârlı piyasa payı"] = (breadth * 10).clip(0, 10)
    grade_columns = [
        "Getiri",
        "Risk",
        "Beklenti",
        "Örneklem",
        "Enstrüman kapsamı",
        "Kârlı piyasa payı",
    ]
    result["Genel"] = result[grade_columns].mean(axis=1) * 10
    result["Güven"] = trades.map(lambda value: "ölçülebilir" if value >= 15 else "veri birikiyor")
    result.loc[trades < 15, "Genel"] = pd.NA
    numeric = [*grade_columns, "Genel"]
    result[numeric] = result[numeric].round(1)
    return result.sort_values(["Genel", "Strateji"], ascending=[False, True])


def _require_authentication() -> None:
    expected = os.environ.get("DASHBOARD_PASSWORD")
    hosted = os.environ.get("CODEX_ALGO_HOSTED") == "1"
    if not expected:
        if hosted:
            st.error("Güvenli pano parolası yapılandırılmadı; erişim kapatıldı.")
            st.stop()
        return
    if st.session_state.get("authenticated"):
        with st.sidebar:
            if st.button("Çıkış", use_container_width=True):
                st.session_state["authenticated"] = False
                st.rerun()
        return

    st.title("Codex Algo")
    st.caption("Özel araştırma ve paper-test panosu")
    with st.form("login"):
        password = st.text_input("Pano parolası", type="password")
        submitted = st.form_submit_button("Giriş", use_container_width=True)
    if submitted and secrets.compare_digest(password.encode("utf-8"), expected.encode("utf-8")):
        st.session_state["authenticated"] = True
        st.rerun()
    if submitted:
        st.error("Parola hatalı.")
    st.stop()


def _apply_style() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] { background: #0b111b; }
        [data-testid="stHeader"] { background: rgba(11,17,27,.88); }
        [data-testid="stMetric"] {
            background: #151e2c; border: 1px solid #27364b; border-radius: 12px;
            padding: 14px 16px;
        }
        [data-testid="stMetricValue"] { color: #eef5ff; }
        [data-testid="stSidebar"] { background: #111927; }
        [data-testid="stAlert"] { border-radius: 10px; }
        @media (max-width: 700px) {
            .block-container { padding: 1rem .75rem 4rem; }
            [data-testid="stMetric"] { padding: 10px 12px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar(meta: dict[str, str], monitor: dict[str, object]) -> str:
    with st.sidebar:
        st.title("Codex Test Panel")
        st.caption("Bağımsız paper araştırması · gerçek emir yok")
        page = st.radio("Sayfa", PAGES, label_visibility="collapsed")
        st.divider()
        updated_at = monitor.get("finished_at") or monitor.get("started_at")
        st.caption(f"Son kontrol: {_to_istanbul(updated_at)}")
        if "start_at" in meta and "end_at" in meta:
            start = pd.Timestamp(meta["start_at"])
            end = pd.Timestamp(meta["end_at"])
            now = pd.Timestamp.now(tz="UTC")
            if start.tzinfo is None:
                start = start.tz_localize("UTC")
            if end.tzinfo is None:
                end = end.tz_localize("UTC")
            duration = max((end - start).total_seconds(), 1)
            progress = min(max((now - start).total_seconds() / duration, 0.0), 1.0)
            st.caption(f"Paper dönemi: {_to_istanbul(start)} → {_to_istanbul(end)}")
            st.progress(progress)
        else:
            st.caption("60 günlük dönem ilk uygun paper güncellemesinde başlayacak.")
    return page


def _header(
    initial_capital: float,
    equity: pd.DataFrame,
    positions: pd.DataFrame,
    trades: pd.DataFrame,
) -> tuple[float, float, float, float]:
    if equity.empty:
        latest_equity = initial_capital
        latest_drawdown = 0.0
        cash = initial_capital
        last_return = 0.0
    else:
        latest = equity.iloc[-1]
        latest_equity = float(latest["equity"])
        latest_drawdown = float(latest["drawdown"])
        cash = float(latest["cash"])
        prior = float(equity.iloc[-2]["equity"]) if len(equity) > 1 else latest_equity
        last_return = latest_equity / prior - 1 if prior else 0.0
    columns = st.columns(5)
    columns[0].metric("Toplam değer", f"${latest_equity:,.2f}")
    columns[1].metric("Toplam getiri", _percent(latest_equity / initial_capital - 1))
    columns[2].metric("Son ölçüm", _percent(last_return))
    columns[3].metric("Açık pozisyon", len(positions))
    columns[4].metric("Paper hareketi", len(trades))
    return latest_equity, latest_drawdown, cash, last_return


def _integrity_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("Sinyal kapanışta, uygulama sonraki barda", "Kod + otomatik test kuralı"),
            ("Piyasa bazlı komisyon ve kayma", "Kod + otomatik test kuralı"),
            ("%70 eğitim / %30 dönem dışı", "Kod + otomatik test kuralı"),
            ("İki kat maliyet stresi", "Kod + otomatik test kuralı"),
            ("Tamamlanmamış üst zaman mumu görünmez", "Kod + otomatik test kuralı"),
            ("Sabit güncel evrende survivorship", "Uyarı"),
            ("Yahoo 1 saat 2020 kapsamı", "Eksik veri reddedilir"),
        ],
        columns=["Kontrol", "Durum"],
    )


def _render_summary(
    equity: pd.DataFrame,
    positions: pd.DataFrame,
    trades: pd.DataFrame,
    summary: pd.DataFrame,
    monitor: dict[str, object],
) -> None:
    st.subheader("Son durum")
    if monitor.get("status") == "waiting":
        st.error(f"Veri/araştırma beklemede: {monitor.get('error', 'ayrıntı yok')}")
    elif monitor.get("status") == "completed":
        st.success("Araştırma ve paper zinciri son kontrolde tamamlandı.")
    else:
        st.info("Kontrol durumu henüz oluşmadı.")
    if equity.empty:
        st.info("Paper portföyü başlamadı; doğrulanmış uygun strateji ve veri bekleniyor.")
    else:
        chart = equity.copy()
        chart["observed_at"] = pd.to_datetime(chart["observed_at"], utc=True)
        st.line_chart(chart.set_index("observed_at")[["equity"]])
    st.subheader("Son hareketler")
    if trades.empty:
        st.caption("Henüz paper işlemi yok.")
    else:
        st.dataframe(trades.head(20), use_container_width=True, hide_index=True)
    st.subheader("Araştırma adayları")
    if summary.empty:
        st.caption("2020+ araştırma özeti henüz üretilemedi.")
    else:
        columns = [
            column
            for column in (
                "strategy_name",
                "profitable_share",
                "median_oos_return",
                "median_profit_factor",
                "median_sharpe",
                "worst_drawdown",
                "paper_eligible",
            )
            if column in summary.columns
        ]
        st.dataframe(summary.loc[:, columns], use_container_width=True, hide_index=True)
    if not positions.empty:
        st.caption(f"{len(positions)} açık pozisyon merkezi paper defterinden okunuyor.")
    st.subheader("Bağımsız paper hesapları")
    accounts = pd.DataFrame(
        [
            _account_status(DEFAULT_DB, "Tek zaman"),
            _account_status(DEFAULT_MTF_DAILY_DB, "1W→1D"),
            _account_status(DEFAULT_MTF_HOURLY_DB, "1D+4H→1H"),
        ]
    )
    st.dataframe(accounts, use_container_width=True, hide_index=True)


def _render_scorecard(summary: pd.DataFrame) -> None:
    st.subheader("Strateji karnesi")
    st.caption(
        "Altı not 0–10, genel puan 0–100'dür. Getiri=pozitif medyan OOS; "
        "Risk=maksimum düşüş; Beklenti=PF; Örneklem=işlem; Enstrüman kapsamı=test sayısı; "
        "Kârlı piyasa payı=pozitif sonuç genişliği. 15 medyan işlemin altında genel puan gizlenir."
    )
    scorecard = _scorecard(summary)
    if scorecard.empty:
        st.info("Karne için 2020+ sonuç ve yeterli işlem henüz yok.")
    else:
        st.dataframe(scorecard, use_container_width=True, hide_index=True)
    st.subheader("Backtest bütünlüğü")
    st.dataframe(_integrity_table(), use_container_width=True, hide_index=True)


def _render_graphs(equity: pd.DataFrame) -> None:
    st.subheader("Sermaye ve düşüş")
    if equity.empty:
        st.info("Paper eğrisi henüz oluşmadı. Örnek veya sentetik eğri gösterilmiyor.")
        return
    chart = equity.copy()
    chart["observed_at"] = pd.to_datetime(chart["observed_at"], utc=True)
    chart = chart.set_index("observed_at")
    st.line_chart(chart[["equity"]])
    st.line_chart(chart[["drawdown"]])
    st.caption(
        "BTC, S&P 500, Nasdaq-100 ve BIST 100 kıyasları yalnız aynı tarih kapsamındaki "
        "doğrulanmış benchmark verisi geldiğinde eklenecek."
    )


def _render_calendar(equity: pd.DataFrame, trades: pd.DataFrame) -> None:
    st.subheader("Takvim")
    daily = _periodic_returns(equity, "Günlük")
    if daily.empty:
        st.info("Takvim için günlük paper özsermayesi henüz yok.")
        return
    daily["Getiri"] = daily["Getiri"].map(_percent)
    st.dataframe(daily.iloc[::-1], use_container_width=True, hide_index=True)
    if not trades.empty and "executed_at" in trades:
        shown = trades.copy()
        shown["Gün"] = (
            pd.to_datetime(shown["executed_at"], utc=True)
            .dt.tz_convert(ISTANBUL_TIMEZONE)
            .dt.strftime("%d.%m.%Y")
        )
        st.subheader("Günlük işlemler")
        st.dataframe(shown, use_container_width=True, hide_index=True)


def _render_positions(positions: pd.DataFrame) -> None:
    st.subheader("Açık pozisyonlar")
    if positions.empty:
        st.info("Açık paper pozisyonu yok.")
        return
    shown = positions.copy()
    shown["position_value"] = shown["quantity"] * shown["last_price"]
    shown["unrealized_pnl"] = shown["quantity"] * (shown["last_price"] - shown["average_price"])
    left, right = st.columns(2)
    with left:
        st.caption("Piyasa bazında pozisyon değeri")
        st.bar_chart(shown.groupby("market")["position_value"].sum())
    with right:
        st.caption("Anlık kâr/zarar")
        st.bar_chart(shown.set_index("symbol")["unrealized_pnl"])
    st.dataframe(shown, use_container_width=True, hide_index=True)


def _render_trades(trades: pd.DataFrame) -> None:
    st.subheader("Emir/hareket geçmişi")
    if trades.empty:
        st.info("Henüz paper işlem kaydı yok.")
        return
    markets = ["Tümü", *sorted(trades["market"].dropna().astype(str).unique())]
    selected = st.selectbox("Piyasa", markets)
    shown = trades if selected == "Tümü" else trades[trades["market"] == selected]
    st.dataframe(shown, use_container_width=True, hide_index=True)
    st.caption(
        "Her satır bir alış/satış hareketidir; kapanan round-trip işlem veya kazanma oranı değildir."
    )


def _paper_statistics(equity: pd.DataFrame, closed: pd.DataFrame) -> dict[str, float]:
    result = {
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "expectancy": 0.0,
        "sharpe": 0.0,
    }
    if not closed.empty and "net_pnl" in closed:
        pnl = pd.to_numeric(closed["net_pnl"], errors="coerce").dropna()
        if not pnl.empty:
            wins = float(pnl[pnl > 0].sum())
            losses = float(-pnl[pnl < 0].sum())
            result["win_rate"] = float((pnl > 0).mean())
            result["profit_factor"] = wins / losses if losses else (float("inf") if wins else 0.0)
            result["expectancy"] = float(pnl.mean())
    periodic = _periodic_returns(equity, "Günlük")
    if len(periodic) >= 10:
        returns = pd.to_numeric(periodic["Getiri"], errors="coerce").dropna()
        volatility = float(returns.std(ddof=0))
        if volatility > 0:
            result["sharpe"] = float(returns.mean() / volatility * (365**0.5))
    return result


def _render_statistics(
    initial_capital: float,
    equity: pd.DataFrame,
    trades: pd.DataFrame,
    closed: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    st.subheader("Paper istatistikleri")
    if equity.empty:
        st.info("Gerçekleşmiş paper istatistiği henüz yok.")
    else:
        latest = equity.iloc[-1]
        columns = st.columns(4)
        columns[0].metric("Net değişim", f"${float(latest['equity']) - initial_capital:,.2f}")
        columns[1].metric("Özsermaye", f"${float(latest['equity']):,.2f}")
        columns[2].metric("Maks. düşüş", _percent(float(equity["drawdown"].min())))
        columns[3].metric("Hareket kaydı", len(trades))
        statistics = _paper_statistics(equity, closed)
        detail = st.columns(4)
        detail[0].metric("Kapanan parça", len(closed))
        detail[1].metric("Kazanma oranı", _percent(statistics["win_rate"]))
        detail[2].metric("Kâr faktörü", f"{statistics['profit_factor']:.2f}")
        detail[3].metric("Günlük Sharpe", f"{statistics['sharpe']:.2f}")
        st.caption(f"Kapanan parça başına beklenti: ${statistics['expectancy']:,.2f}")
    st.subheader("Backtest istatistikleri")
    if summary.empty:
        st.caption("2020+ istatistik matrisi veri bekliyor.")
    else:
        st.dataframe(summary, use_container_width=True, hide_index=True)


def _render_strategies(signals: pd.DataFrame) -> None:
    st.subheader("Tek-zaman Codex stratejileri")
    catalog = pd.DataFrame(
        [
            {
                "Kod": item.strategy_id,
                "Strateji": item.name,
                "PDF adayı": item.pdf_candidate,
                "Aile": item.family,
                "Neden aday": item.rationale,
                "Sınırlama": item.caveat,
            }
            for item in STRATEGIES
        ]
    )
    st.dataframe(catalog, use_container_width=True, hide_index=True)
    st.warning("Claude kapsamı dışında bırakılanlar: " + "; ".join(EXCLUDED_CLAUDE_STRATEGIES))
    st.subheader("Çoklu-zaman stratejileri")
    mtf_catalog = pd.DataFrame(
        [
            {
                "Kod": item.strategy_id,
                "Strateji": item.name,
                "Mimari": item.architecture,
                "Aile": item.family,
                "Kural": item.rule_summary,
                "PDF temeli": item.pdf_basis,
            }
            for item in MTF_STRATEGIES
        ]
    )
    st.dataframe(mtf_catalog, use_container_width=True, hide_index=True)
    for mode, label in (("daily", "1W→1D"), ("hourly", "1D+4H→1H")):
        market_summary = _read_csv(STATE_DIR / f"mtf_{mode}_market_summary.csv")
        st.subheader(f"{label} piyasa × strateji matrisi")
        if market_summary.empty:
            st.caption("Veri bekliyor.")
        elif {"market", "strategy_name", "median_oos_return"}.issubset(market_summary.columns):
            matrix = market_summary.pivot(
                index="strategy_name", columns="market", values="median_oos_return"
            )
            st.dataframe(matrix.style.format("{:.2%}"), use_container_width=True)
    st.subheader("MTF paper hesapları")
    st.dataframe(
        pd.DataFrame(
            [
                _account_status(DEFAULT_MTF_DAILY_DB, "1W→1D"),
                _account_status(DEFAULT_MTF_HOURLY_DB, "1D+4H→1H"),
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    if not signals.empty:
        st.subheader("Son sinyaller")
        st.dataframe(signals.head(100), use_container_width=True, hide_index=True)


def _render_coach(summary: pd.DataFrame, monitor: dict[str, object]) -> None:
    st.subheader("Koç: öncelikli bulgular")
    st.caption(
        "Kurala dayalıdır; test sırasında strateji kuralını değiştirmez. Bulgular örneklem ve "
        "güven etiketiyle gösterilir."
    )
    findings: list[tuple[str, str, str]] = []
    if monitor.get("status") == "waiting":
        findings.append(("Veri zinciri beklemede", str(monitor.get("error", "")), "yüksek"))
    if summary.empty:
        findings.append(
            ("Performans yorumu ertelendi", "2020+ sonuç ve yeterli işlem yok.", "yüksek")
        )
    else:
        for row in summary.to_dict("records"):
            trades = float(row.get("median_trades", 0) or 0)
            oos = float(row.get("median_oos_return", 0) or 0)
            if trades < 15:
                findings.append(
                    (str(row.get("strategy_name", row.get("strategy"))), "Veri birikiyor.", "düşük")
                )
            elif oos <= 0:
                findings.append(
                    (
                        str(row.get("strategy_name", row.get("strategy"))),
                        "Medyan dönem-dışı getiri pozitif değil.",
                        "orta",
                    )
                )
    for title, detail, confidence in findings:
        with st.container(border=True):
            st.markdown(f"**{title}** · güven: `{confidence}`")
            st.write(detail)
    st.subheader("Ne olurdu? strateji çıkarma simülatörü")
    st.info(
        "Paper işlemleri oluşunca, açık pozisyonları değiştirmeden geçmiş katkı simüle edilecek."
    )


def _render_learning() -> None:
    st.subheader("Öğrenme — gölge mod")
    st.caption(
        "Gölge filtre paper kararını değiştirmez. Yalnız ileriye dönük tahmin kaydı tutar; "
        "sonuç kapandıktan sonra isabet ölçülür."
    )
    st.info("En az beş önceki kapanan işlem oluşmadan model 'öğreniyor' durumunda kalacak.")
    candidates = _read_csv(ROOT / "config" / "pdf_candidates.csv")
    if not candidates.empty:
        tier = st.selectbox("PDF aday önceliği", ["Tümü", "A", "B", "C"])
        shown = candidates if tier == "Tümü" else candidates[candidates["tier"] == tier]
        st.dataframe(shown, use_container_width=True, hide_index=True)
    archival = _read_csv(STATE_DIR / "archival_breadth_summary.csv")
    if not archival.empty:
        st.subheader("Arşiv genişlik ön elemesi")
        st.warning("2013–2018 arşiv sonucu güncel paper sonucu değildir.")
        st.dataframe(archival, use_container_width=True, hide_index=True)


def _render_report(
    initial_capital: float,
    equity: pd.DataFrame,
    positions: pd.DataFrame,
    trades: pd.DataFrame,
    closed: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    st.subheader("Dönem raporu")
    if equity.empty:
        st.info("Paper dönemi başlamadığı için gerçekleşmiş performans raporu yok.")
    else:
        latest = float(equity.iloc[-1]["equity"])
        columns = st.columns(4)
        columns[0].metric("Toplam değer", f"${latest:,.2f}")
        columns[1].metric("Toplam getiri", _percent(latest / initial_capital - 1))
        columns[2].metric("Hareket kaydı", len(trades))
        columns[3].metric("Açık pozisyon", len(positions))
    st.subheader("Kontrol listesi")
    checklist = pd.DataFrame(
        [
            ("30+ kapanan parça", "Geçti" if len(closed) >= 30 else f"{len(closed)}/30"),
            ("60+ gün", "Hesaplanıyor" if not equity.empty else "Veri yok"),
            (
                "Düşüş <%10",
                "Geçti"
                if not equity.empty and float(equity["drawdown"].min()) > -0.10
                else "Bekliyor",
            ),
            ("Beklenti konisi içinde", "Henüz hesaplanamıyor"),
            ("PSR >%95", "Henüz hesaplanamıyor"),
        ],
        columns=["Ölçüt", "Durum"],
    )
    st.dataframe(checklist, use_container_width=True, hide_index=True)
    st.subheader("İndirilebilir çıktılar")
    downloads = {
        "Strateji özeti": STATE_DIR / "strategy_summary.csv",
        "MTF günlük özeti": STATE_DIR / "mtf_daily_summary.csv",
        "MTF saatlik özeti": STATE_DIR / "mtf_hourly_summary.csv",
    }
    if not summary.empty:
        downloads["Mevcut rapor görünümü"] = STATE_DIR / "strategy_summary.csv"
    for label, path in downloads.items():
        if path.exists() and path.stat().st_size:
            st.download_button(label, path.read_bytes(), file_name=path.name)


def _render_periodic(equity: pd.DataFrame) -> None:
    st.subheader("Dönemsel getiri")
    frequency = st.segmented_control("Dönem", ["Günlük", "Haftalık", "Aylık"], default="Günlük")
    table = _periodic_returns(equity, frequency or "Günlük")
    if table.empty:
        st.info("Dönemsel paper getirisi henüz oluşmadı.")
        return
    shown = table.copy()
    shown["Getiri"] = shown["Getiri"].map(_percent)
    st.dataframe(shown.iloc[::-1], use_container_width=True, hide_index=True)


def _render_risk(
    initial_capital: float,
    latest_equity: float,
    drawdown: float,
    positions: pd.DataFrame,
    monitor: dict[str, object],
) -> None:
    st.subheader("Risk")
    if drawdown <= -0.15:
        st.error("−%15 risk freni aktif; yeni paper riski açılmamalı.")
    else:
        st.success(f"Risk freni pasif · mevcut düşüş {_percent(drawdown)}")
    if not positions.empty:
        shown = positions.copy()
        shown["value"] = shown["quantity"] * shown["last_price"]
        concentration = shown.groupby("symbol", as_index=False).agg(
            strateji_sayisi=("strategy", "nunique"), toplam_tutar=("value", "sum")
        )
        concentration["sermaye_payi"] = concentration["toplam_tutar"] / max(latest_equity, 1e-9)
        concentration["durum"] = concentration.apply(
            lambda row: (
                "yoğunlaşma"
                if row["strateji_sayisi"] >= 3 or row["sermaye_payi"] >= 0.10
                else "izleniyor"
            ),
            axis=1,
        )
        st.subheader("Aynı varlıkta yoğunlaşma")
        st.dataframe(concentration, use_container_width=True, hide_index=True)
    else:
        st.info("Yoğunlaşma hesabı için açık pozisyon yok.")
    st.subheader("Veri ve worker sağlığı")
    stages = monitor.get("stages", {})
    if isinstance(stages, dict) and stages:
        rows = [
            {"Aşama": name, **details}
            for name, details in stages.items()
            if isinstance(details, dict)
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    elif monitor:
        st.json(monitor)
    else:
        st.caption("Worker sağlık kaydı yok.")
    for mode in ("daily", "hourly"):
        health = _read_json(STATE_DIR / f"mtf_{mode}_health.json")
        if health:
            errors = health.get("errors", [])
            st.write(
                f"MTF {mode}: {health.get('tested_instruments', 0)} enstrüman test edildi, "
                f"{len(errors) if isinstance(errors, list) else 0} veri hatası."
            )
    st.subheader("Provenans")
    provenance_files = (
        "import_provenance.json",
        "archival_provenance.json",
        "archival_breadth_provenance.json",
    )
    found = False
    for filename in provenance_files:
        path = STATE_DIR / filename
        if path.exists():
            found = True
            with st.expander(filename):
                st.json(json.loads(path.read_text(encoding="utf-8")))
    if not found:
        st.caption("Kaynak/provenans kaydı henüz yok.")
    st.info(
        "Kaldıraç düşüş olasılığı ve strateji korelasyonu yeterli ortak paper günü oluşmadan "
        "hesaplanmayacak."
    )


def render() -> None:
    st.set_page_config(page_title="Codex Algo", page_icon="📈", layout="wide")
    _apply_style()
    _require_authentication()
    config = load_config()

    paper = _paper_snapshot(DEFAULT_DB)
    equity = paper["equity"]
    positions = paper["positions"]
    trades = paper["trades"]
    closed = paper["closed_trades"]
    signals = paper["signals"]
    metadata = paper["metadata"]
    meta = dict(zip(metadata.get("key", []), metadata.get("value", []), strict=True))
    monitor = _read_json(STATE_DIR / "monitor_status.json")
    summary = _read_csv(STATE_DIR / "strategy_summary.csv")

    page = _sidebar(meta, monitor)
    st.title("Codex Algo — Bağımsız Paper Test")
    st.caption(
        "PC–mobil senkron barındırmaya hazır; gerçek emir göndermez ve yatırım tavsiyesi değildir."
    )
    latest_equity, latest_drawdown, _, _ = _header(
        config.initial_capital, equity, positions, trades
    )
    if latest_drawdown <= -0.15:
        st.error("Risk freni: hesap düşüşü −%15 veya altında.")
    st.divider()

    if page == "Özet":
        _render_summary(equity, positions, trades, summary, monitor)
    elif page == "Karne":
        _render_scorecard(summary)
    elif page == "Grafikler":
        _render_graphs(equity)
    elif page == "Takvim":
        _render_calendar(equity, trades)
    elif page == "Açık pozisyonlar":
        _render_positions(positions)
    elif page == "İşlem geçmişi":
        _render_trades(trades)
    elif page == "İstatistik":
        _render_statistics(config.initial_capital, equity, trades, closed, summary)
    elif page == "Stratejiler":
        _render_strategies(signals)
    elif page == "Koç":
        _render_coach(summary, monitor)
    elif page == "Öğrenme":
        _render_learning()
    elif page == "Rapor":
        _render_report(config.initial_capital, equity, positions, trades, closed, summary)
    elif page == "Dönemsel getiri":
        _render_periodic(equity)
    elif page == "Risk":
        _render_risk(config.initial_capital, latest_equity, latest_drawdown, positions, monitor)

    st.caption(
        f"Son pano üretimi: {_to_istanbul(datetime.now(UTC))} · İşlemler yalnız paper modundadır."
    )
