"""İşlem evreni: ilk 25 kripto, Magnificent 7, BIST30'un en büyük 10'u, altın, petrol.

Her enstrüman için veri kaynağı, saat dilimi, seans saatleri ve işlem maliyeti
tanımlanır. Kripto listesi ve BIST sıralaması ağ erişimi varsa dinamik olarak
güncellenir (bkz. `refresh_crypto_top25`, `refresh_bist_top10`); yoksa aşağıdaki
sabit listeler kullanılır.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Instrument:
    symbol: str            # kaynaktaki sembol (BTCUSDT, AAPL, ASELS.IS, GC=F)
    asset_class: str       # crypto | us_stock | bist | commodity
    source: str            # binance | yahoo
    tz: str                # seans hesapları için yerel saat dilimi
    session_start: str     # "HH:MM" yerel
    session_end: str       # "HH:MM" yerel (bu saatte tüm pozisyonlar kapanır)
    orb_minutes: int       # açılış aralığı süresi (dakika)
    cost_pct: float        # tek yön komisyon + kayma (oran, 0.001 = %0,1)
    name: str = field(default="")


# Stablecoin ve sarılmış tokenlar hariç, piyasa değerine göre ilk 25 (Binance USDT
# paritesi olanlar). Ağ erişimi olduğunda CoinGecko'dan yenilenir.
CRYPTO_TOP25_FALLBACK = [  # CoinGecko ilk 25 (stablecoin hariç, Binance USDT), 2026-10-10
    "BTC", "ETH", "BNB", "XRP", "SOL", "TRX", "ZEC", "HYPE", "DOGE", "LINK",
    "ADA", "NEAR", "XLM", "BCH", "LTC", "UNI", "AVAX", "SUI", "GRAM", "HBAR",
    "QNT", "TAO", "SHIB", "ENA", "AAVE",
]

MAG7 = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]

# BIST30 bileşenleri (yaklaşık; endeks dönemsel değişir). Piyasa değerine göre ilk
# 10, ağ erişimi olduğunda Yahoo Finance marketCap ile yeniden sıralanır.
BIST30_APPROX = [
    "ASELS", "GARAN", "KCHOL", "THYAO", "AKBNK", "ENKAI", "ISCTR", "BIMAS",
    "TUPRS", "FROTO", "YKBNK", "TCELL", "SAHOL", "EREGL", "TTKOM", "SISE",
    "PGSUS", "TOASO", "KOZAL", "ASTOR", "AEFES", "ARCLK", "PETKM", "SASA",
    "HEKTS", "MGROS", "TAVHL", "ULKER", "OYAKC", "KRDMD",
]
BIST_TOP10_FALLBACK = BIST30_APPROX[:10]

COMMODITIES = {"GC=F": "Altın (COMEX)", "CL=F": "Ham petrol (WTI, NYMEX)", "SI=F": "Gümüş (COMEX)"}


def crypto(sym: str) -> Instrument:
    # Kripto 7/24: "gün" UTC 00:00'da başlar; aralık = Asya seansı (ilk 180 dk).
    return Instrument(f"{sym}USDT", "crypto", "binance", "UTC", "00:00", "24:00",
                      180, 0.0008, sym)


def us_stock(sym: str) -> Instrument:
    return Instrument(sym, "us_stock", "yahoo", "America/New_York", "09:30", "15:55",
                      30, 0.0003, sym)


def bist(sym: str) -> Instrument:
    return Instrument(f"{sym}.IS", "bist", "yahoo", "Europe/Istanbul", "10:00", "17:55",
                      30, 0.0006, sym)


def commodity(sym: str) -> Instrument:
    # Vadeli neredeyse 24 saat işlem görür; day trade için ABD gündüz seansı.
    return Instrument(sym, "commodity", "yahoo", "America/New_York", "09:00", "16:25",
                      30, 0.0003, COMMODITIES.get(sym, sym))


def build_universe(crypto_list=None, bist_list=None) -> list[Instrument]:
    crypto_list = crypto_list or CRYPTO_TOP25_FALLBACK
    bist_list = bist_list or BIST_TOP10_FALLBACK
    return ([crypto(s) for s in crypto_list] + [us_stock(s) for s in MAG7]
            + [bist(s) for s in bist_list] + [commodity(s) for s in COMMODITIES])


STABLE_OR_WRAPPED = {
    "USDT", "USDC", "USDE", "DAI", "FDUSD", "TUSD", "USDS", "PYUSD", "USD1", "BUSD",
    "WBTC", "WETH", "STETH", "WSTETH", "WEETH", "CBBTC", "WBETH", "RETH", "SUSDE",
    "BSC-USD", "USDTB", "LEO", "FIGR_HELOC", "BUIDL", "USYC", "XAUT", "PAXG",
}


def refresh_crypto_top25(session) -> list[str]:
    """CoinGecko piyasa değeri sıralamasından Binance'te USDT paritesi olan ilk 25."""
    r = session.get("https://api.coingecko.com/api/v3/coins/markets",
                    params={"vs_currency": "usd", "order": "market_cap_desc",
                            "per_page": 100, "page": 1}, timeout=30)
    r.raise_for_status()
    info = session.get("https://data-api.binance.vision/api/v3/exchangeInfo",
                       params={"permissions": "SPOT"}, timeout=30)
    info.raise_for_status()
    usdt = {s["baseAsset"] for s in info.json()["symbols"]
            if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"}
    out = []
    for c in r.json():
        sym = c["symbol"].upper()
        if sym in STABLE_OR_WRAPPED or sym not in usdt:
            continue
        out.append(sym)
        if len(out) == 25:
            break
    return out


def refresh_bist_top10(session=None) -> list[str]:
    """BIST30 listesini Yahoo marketCap'e göre sıralayıp ilk 10'u döndürür."""
    import requests

    session = session or requests.Session()
    session.headers.setdefault("User-Agent", "Mozilla/5.0")
    caps = {}
    for s in BIST30_APPROX:
        try:
            r = session.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}.IS",
                            params={"range": "5d", "interval": "1d"}, timeout=20)
            m = r.json()["chart"]["result"][0]["meta"]
            caps[s] = float(m.get("marketCap") or 0)
        except Exception:
            caps[s] = 0.0
    ranked = sorted(caps, key=caps.get, reverse=True)
    return ranked[:10] if caps.get(ranked[0], 0) > 0 else BIST_TOP10_FALLBACK
