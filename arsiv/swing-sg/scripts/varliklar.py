"""Sistemde işlem görecek varlık evreni."""

# Piyasa değerine göre ilk 25 kripto (stablecoin'ler hariç), Binance USDT pariteleri
KRIPTO = [
    "BTC", "ETH", "XRP", "BNB", "SOL", "DOGE", "TRX", "ADA", "LINK", "AVAX",
    "XLM", "SUI", "BCH", "HBAR", "LTC", "TON", "DOT", "SHIB", "UNI", "NEAR",
    "APT", "AAVE", "ICP", "ETC", "PEPE",
]

# Magnificent 7
MAG7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

# BIST 30'un piyasa değerine göre en büyük 10 hissesi (Yahoo: .IS)
BIST10 = ["ASELS", "GARAN", "KCHOL", "THYAO", "BIMAS", "AKBNK", "ISCTR", "TUPRS", "FROTO", "YKBNK"]

# Emtia: altın ve WTI ham petrol vadeli
EMTIA = {"ALTIN": "GC=F", "PETROL": "CL=F"}


def tum_varliklar():
    """(dosya_adi, sinif) listesi."""
    out = [(f"{k}USDT", "kripto") for k in KRIPTO]
    out += [(s, "mag7") for s in MAG7]
    out += [(f"{s}.IS", "bist") for s in BIST10]
    out += [(k, "emtia") for k in EMTIA]
    return out
