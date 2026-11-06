"""Yahoo Finance'ten günlük (2019-06 ->) ve saatlik (son ~730 gün) veri: Magnificent 7, BIST seçili hisseler, altın, Brent."""
import time
from pathlib import Path
import pandas as pd
import yfinance as yf

SEMBOLLER = {
    "mag7": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    "bist": ["AKBNK.IS", "BIMAS.IS", "EREGL.IS", "FROTO.IS", "KCHOL.IS", "SISE.IS", "TUPRS.IS", "THYAO.IS",
             "TRALT.IS", "KOZAL.IS", "ASELS.IS", "EKGYO.IS"],
    "emtia": ["GC=F", "BZ=F"],
    "endeks": ["XU100.IS", "^NDX", "^GSPC", "USDTRY=X"],
}
KOK = Path("veri_dis"); (KOK / "1d").mkdir(parents=True, exist_ok=True); (KOK / "1h").mkdir(parents=True, exist_ok=True)


def al(sym, **kw):
    for i in range(4):
        try:
            d = yf.Ticker(sym).history(auto_adjust=True, **kw)
            if len(d):
                return d
        except Exception as e:  # noqa: BLE001
            print("hata", sym, e)
        time.sleep(3 * (i + 1))
    return None


ozet = []
for grup, liste in SEMBOLLER.items():
    for s in liste:
        ad = s.replace("=", "_").replace("^", "")
        g = al(s, start="2019-06-01", interval="1d")
        h = al(s, period="729d", interval="1h")
        for d, kls in ((g, "1d"), (h, "1h")):
            if d is not None:
                d = d[["Open", "High", "Low", "Close", "Volume"]]
                d.index = d.index.tz_convert("UTC").tz_localize(None) if d.index.tz is not None else d.index
                d.to_csv(KOK / kls / f"{ad}.csv")
        ozet.append(dict(grup=grup, sembol=s, gunluk=0 if g is None else len(g), gunluk_bas=None if g is None else str(g.index[0])[:10],
                         saatlik=0 if h is None else len(h), saatlik_bas=None if h is None else str(h.index[0])[:16]))
        print(ozet[-1], flush=True)
pd.DataFrame(ozet).to_csv(KOK / "ozet.csv", index=False)
