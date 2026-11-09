"""Geniş evren verisi (trend/portföy stratejileri için): brainbrick-trades/Quant-Trading-Strategies
long-only testindeki evrenler. Çıktı: data/genis/<ticker>.csv (günlük OHLCV, 2014+)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from fetch_data import yahoo  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "genis")

BIST = ["AKBNK", "ARCLK", "ASELS", "BIMAS", "EKGYO", "ENKAI", "EREGL", "FROTO", "GARAN", "GUBRF",
        "HEKTS", "ISCTR", "KCHOL", "KRDMD", "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "TCELL",
        "THYAO", "TOASO", "TUPRS", "YKBNK", "TTKOM", "AEFES", "TAVHL", "MGROS", "ULKER", "VESTL"]
US = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "JPM", "V", "UNH", "XOM",
      "JNJ", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "PEP", "KO", "COST", "AVGO", "LLY", "WMT",
      "MCD", "CSCO", "ADBE", "CRM", "ORCL", "NFLX", "AMD", "INTC", "QCOM", "TXN", "BAC", "WFC",
      "GS", "CAT", "DE", "HON", "GE", "LMT", "NKE", "SBUX", "DIS", "T", "VZ", "PFE", "TMO"]
EMTIA = ["GC=F", "SI=F", "HG=F", "PL=F", "PA=F", "CL=F", "BZ=F", "NG=F", "HO=F", "RB=F",
         "ZC=F", "ZW=F", "ZS=F", "ZM=F", "ZL=F", "KE=F", "KC=F", "SB=F", "CC=F", "CT=F", "LE=F", "HE=F"]
# Emtia ETF'leri: vade geçişi maliyeti fiyata gömülü, gerçekten işlem görebilir (vadeli seri yerine)
EMTIA_ETF = ["GLD", "SLV", "PPLT", "PALL", "CPER", "USO", "BNO", "UNG", "UGA", "DBA", "CORN", "WEAT",
             "SOYB", "CANE", "DBB", "DBE", "DBC", "GSG"]
TEKLER = ["BTC-USD", "ETH-USD", "XU100.IS", "XU030.IS", "^GSPC", "^NDX", "USDTRY=X"]


def dosya_adi(t):
    return t.replace("^", "IDX_").replace("=", "_")


def main():
    os.makedirs(OUT, exist_ok=True)
    hatali = []
    for t in [b + ".IS" for b in BIST] + US + EMTIA + EMTIA_ETF + TEKLER:
        df = yahoo(t)
        if df is None or not len(df):
            hatali.append(t)
            continue
        df = df[df["Date"] >= "2014-01-01"]
        df.to_csv(os.path.join(OUT, dosya_adi(t) + ".csv"), index=False, float_format="%.10g")
        print(f"OK {t}: {len(df)}")
        time.sleep(0.3)
    print("Başarısız:", hatali)


if __name__ == "__main__":
    main()
