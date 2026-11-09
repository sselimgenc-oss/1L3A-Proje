"""Enstrüman listeleri ve maliyet varsayımları."""

# İlk 20 kripto (stablecoin'ler hariç, Binance spot USDT pariteleri).
CRYPTO = [
    "BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "SOLUSDT",
    "TRXUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT",
    "SUIUSDT", "XLMUSDT", "TONUSDT", "HBARUSDT", "BCHUSDT",
    "LTCUSDT", "DOTUSDT", "SHIBUSDT", "UNIUSDT", "NEARUSDT",
]

# Magnificent 7
MAG7 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]

# BIST30'un piyasa değeri en büyük 10 hissesi (Yahoo: .IS)
BIST10 = [
    "ASELS.IS", "GARAN.IS", "THYAO.IS", "KCHOL.IS", "AKBNK.IS",
    "ISCTR.IS", "BIMAS.IS", "TUPRS.IS", "FROTO.IS", "ENKAI.IS",
]

# Altın ve petrol (Yahoo sürekli vadeli)
COMMODITIES = ["GC=F", "CL=F", "BZ=F"]

GROUPS = {
    "crypto": CRYPTO,
    "mag7": MAG7,
    "bist": BIST10,
    "commodity": COMMODITIES,
}

# Tek yön (giriş VEYA çıkış) maliyeti, fiyatın oranı olarak: komisyon + kayma/spread.
COST_PER_SIDE = {
    "crypto": 0.0005 + 0.0001,     # Binance USDT-M vadeli taker %0.05 + kayma
    "mag7": 0.0001 + 0.0001,       # komisyonsuz broker + spread/kayma
    "bist": 0.0004 + 0.0003,       # aracı kurum komisyonu + spread
    "commodity": 0.0001 + 0.0001,  # vadeli kontrat komisyonu + 1 tik kayma
}


def group_of(symbol: str) -> str:
    for g, syms in GROUPS.items():
        if symbol in syms:
            return g
    raise KeyError(symbol)
