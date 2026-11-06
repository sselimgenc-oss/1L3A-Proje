"""(v2) Geleneksel piyasa günlük verisi (yfinance, düzeltilmiş fiyat): Magnificent 7, BIST 30'un en büyük 10'u, altın, petrol.
Çıktı: data_gel/1d/<SEMBOL>.csv.gz (ts ms, open, high, low, close, volume, quote_volume)."""
import os, sys
import yfinance as yf
import pandas as pd

SEMBOLLER = {
    "mag7": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA"],
    "bist10": ["ASELS.IS", "THYAO.IS", "GARAN.IS", "KCHOL.IS", "AKBNK.IS", "BIMAS.IS", "ISCTR.IS", "TUPRS.IS", "YKBNK.IS", "FROTO.IS"],
    "emtia": ["GC=F", "CL=F", "BZ=F"],
    "kur": ["USDTRY=X"],  # BIST fiyatlarını dolara çevirmek için
}
out = os.path.join(sys.argv[1] if len(sys.argv) > 1 else "data_gel", "1d")
os.makedirs(out, exist_ok=True)
for grup, syms in SEMBOLLER.items():
    for s in syms:
        d = yf.download(s, start="2010-01-01", interval="1d", auto_adjust=True, progress=False, multi_level_index=False)
        if d.empty:
            print("BOŞ", s); continue
        d = d.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna(subset=["close"])
        d["quote_volume"] = d["volume"] * d["close"]
        d.insert(0, "ts", pd.DatetimeIndex(d.index).tz_localize(None).as_unit("ms").asi8)
        ad = s.replace(".IS", "_IS").replace("=F", "_F").replace("=X", "_X")
        d.to_csv(os.path.join(out, f"{ad}.csv.gz"), index=False)
        print(grup, s, len(d), d.index[0].date(), d.index[-1].date())
