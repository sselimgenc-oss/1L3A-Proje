"""Panel için karşılaştırma endeksleri: BTC, S&P 500, Nasdaq 100, BIST 100 günlük kapanışları.

Botlardan bağımsızdır; yalnız panelin "piyasayı yeniyor muyuz" karşılaştırması içindir.
Çıktı: <cikis>/kiyas.csv (tarih, BTC, SPX, NDX, XU100). Bir endeks indirilemezse sütunu boş kalır, diğerleri yazılır.
"""
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

ENDEKS = {"BTC": "BTC-USD", "SPX": "^GSPC", "NDX": "^NDX", "XU100": "XU100.IS"}
BASLANGIC = "2026-09-01"


def main(cikis):
    cikis = Path(cikis)
    cikis.mkdir(parents=True, exist_ok=True)
    seriler = {}
    for ad, kod in ENDEKS.items():
        try:
            d = yf.download(kod, start=BASLANGIC, interval="1d", progress=False, auto_adjust=True)
            c = d["Close"]
            c = c.iloc[:, 0] if isinstance(c, pd.DataFrame) else c
            c = c.dropna()
            if len(c):
                seriler[ad] = c.round(4)
            print(f"{ad}: {len(c)} gün, son {c.index[-1].date() if len(c) else '-'}")
        except Exception as e:  # tek endeksin hatası diğerlerini durdurmasın
            print(f"{ad}: indirilemedi ({e})")
    if not seriler:
        sys.exit("Hiçbir endeks indirilemedi")
    T = pd.DataFrame(seriler)
    T.index = pd.to_datetime(T.index).date
    T.index.name = "tarih"
    T.to_csv(cikis / "kiyas.csv")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "kiyas_durum")
