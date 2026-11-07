from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyInfo:
    strategy_id: str
    name: str
    pdf_candidate: str
    family: str
    rationale: str
    caveat: str


EXCLUDED_CLAUDE_STRATEGIES = (
    "Hybrid Breakout (hezSShJr)",
    "Squeeze Momentum (G40dtEbK, LazyBear)",
    "MACD ReLoaded (VO6DY8s1)",
)


STRATEGIES = (
    StrategyInfo(
        strategy_id="compression_breakout",
        name="Sıkışma Kırılımı — Codex",
        pdf_candidate="Compression Breakout System (97gxVA5b)",
        family="Trend / kırılım",
        rationale="PDF'de AAPL üzerinde uzun dönem, ayrık örneklem ve birden çok hissede sonuç verilmiş.",
        caveat="Özgün Pine kaynağı doğrulanamadı; bu uygulama açıklanmış aileden türetilen Codex kuralıdır.",
    ),
    StrategyInfo(
        strategy_id="channel_reversion",
        name="Kanal Ortalamaya Dönüş — Codex",
        pdf_candidate="Channel Reversion System (XRZCjbFr)",
        family="Ortalamaya dönüş",
        rationale="PDF'de QQQ ve SPY için uzun dönem sonuç ve sınırlı düşüş bildirilmiş.",
        caveat="Özgün Pine kaynağı doğrulanamadı; göstergeler ve eşikler açık Codex uyarlamasıdır.",
    ),
    StrategyInfo(
        strategy_id="supertrend_regime",
        name="SuperTrend Rejim — Codex",
        pdf_candidate="SuperTrend Regime Confluence (mpjNqADq)",
        family="Trend / rejim",
        rationale="PDF'de 2020–2026 BTC örneği, işlem sayısı ve kâr faktörü birlikte verilmiş.",
        caveat="Yazarın bildirilen düşüşü %20 eşiğini aşıyor; yalnız araştırma ve paper-test adayıdır.",
    ),
    StrategyInfo(
        strategy_id="fractal_breakout",
        name="Fraktal Kırılım — Codex",
        pdf_candidate="Fractal Breakout Trend Following Strategy (IqUET4xO)",
        family="Trend / kanal kırılımı",
        rationale="PDF'de BTC 4 saatlik örnekte PF 1,95 ve %8,3 düşüş bildirilmiş; yalın kurala çevrilebilir.",
        caveat="Özgün Pine kaynağı doğrulanamadı; günlük ve uzun-yönlü Codex uyarlamasıdır.",
    ),
    StrategyInfo(
        strategy_id="macd_sma200",
        name="MACD + SMA200 — Codex",
        pdf_candidate="MACD + SMA 200 Strategy (yMCa3XZD)",
        family="Trend / momentum",
        rationale="Popülerlik listesinde 31,6 bin beğeni ve çok uzun endeks örnekleri var; kural adı şeffaf.",
        caveat="Claude'un MACD ReLoaded modeli değildir. PDF'deki yüksek PF iddiası maliyet ve dönem farkları nedeniyle doğrulanmalıdır.",
    ),
    StrategyInfo(
        strategy_id="ao_ac_zones",
        name="AO/AC Bölgeleri — Codex",
        pdf_candidate="AO/AC Trading Zones Strategy (Tkrjao7P)",
        family="Momentum",
        rationale="PDF'de 278 işlem, PF 2,20 ve %5,4 düşüş birlikte bildiriliyor; göstergeler standart formüllü.",
        caveat="Yazar örneği yalnız BTC ve yaklaşık iki yıllık dönem; günlük çoklu-piyasa genellemesi ayrıca test edilmelidir.",
    ),
    StrategyInfo(
        strategy_id="kst_momentum",
        name="KST Momentum — Codex",
        pdf_candidate="KST Strategy",
        family="Momentum / trend",
        rationale="PDF'de 120 işlem, PF 1,75 ve %9,1 düşüş birlikte bildirilmiş.",
        caveat="Özgün Pine kuralı doğrulanamadı; standart Pring KST ve EMA200 kullanan Codex uyarlamasıdır.",
    ),
    StrategyInfo(
        strategy_id="triple_cci_mfi",
        name="Triple CCI + MFI — Codex",
        pdf_candidate="Triple CCI + MFI Strategy",
        family="Momentum / para akışı",
        rationale="PDF'de 108 işlem, PF 2,01 ve %7,8 düşüş bildirilmiş; göstergeler yeniden üretilebilir.",
        caveat="Yazar örneği yalnız BTC 2 saat; 20/40/80 CCI ve MFI eşikleri Codex tarafından sabitlenmiştir.",
    ),
    StrategyInfo(
        strategy_id="double_cci_hma",
        name="Double CCI + HMA — Codex",
        pdf_candidate="Double CCI + HMA Strategy",
        family="Momentum / trend",
        rationale="PDF'de 104 işlem, PF 2,31 ve %9,6 düşüş bildirilmiş.",
        caveat="Özgün Pine kaynağı doğrulanamadı; 20/50 CCI ve HMA55 kullanan Codex uyarlamasıdır.",
    ),
)


def strategy_info(strategy_id: str) -> StrategyInfo:
    for item in STRATEGIES:
        if item.strategy_id == strategy_id:
            return item
    raise KeyError(f"Bilinmeyen strateji: {strategy_id}")
