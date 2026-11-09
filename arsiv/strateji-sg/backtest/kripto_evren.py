"""Zaman noktasında geçerli (point-in-time) evren: her ay başında son 30 günlük USDT hacmine göre ilk N.
Hayatta kalma yanlılığını önlemek için borsadan çıkarılan semboller de dahildir."""
from pathlib import Path
import pandas as pd

KOK = Path(__file__).resolve().parent.parent / "data" / "kripto"
HARIC = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "BTCDOMUSDT", "DEFIUSDT", "BLUEBIRDUSDT",
         "FOOTBALLUSDT",
         # hisse / ETF / emtia vadelileri (kripto değil)
         "CRCLUSDT", "EWYUSDT", "INTCUSDT", "MSTRUSDT", "NVDAUSDT", "QQQUSDT", "SAMSUNGUSDT", "SKHYNIXUSDT",
         "SNDKUSDT", "SOXLUSDT", "SPCXUSDT", "TSLAUSDT", "MUUSDT", "CLUSDT", "BZUSDT", "COINUSDT", "HOODUSDT",
         "AAPLUSDT", "AMZNUSDT", "GOOGLUSDT", "METAUSDT", "MSFTUSDT", "SPYUSDT", "NATGASUSDT", "XPTUSDT", "XPDUSDT", "PAXGUSDT", "EURUSDT", "GBPUSDT", "XAUUSDT", "XAGUSDT", "USDEUSDT", "BTCSTUSDT"}
N = 40
MIN_GUN = 90


def evren(n=N):
    d = pd.read_pickle(KOK / "1d.pkl")
    qv = d.quote_volume.unstack(0).sort_index()
    qv = qv[[c for c in qv.columns if c not in HARIC]]
    gecmis = qv.notna().cumsum()
    hacim30 = qv.rolling(30, min_periods=20).sum()
    aylar = pd.date_range("2020-01-01", qv.index[-1], freq="MS")
    satir = {}
    for ay in aylar:
        gun = ay - pd.Timedelta(days=1)   # yalnızca ay başından ÖNCEKİ veri
        if gun not in hacim30.index:
            gun = hacim30.index[hacim30.index <= gun][-1] if (hacim30.index <= gun).any() else None
        if gun is None:
            continue
        h = hacim30.loc[gun]
        uygun = h[(gecmis.loc[gun] >= MIN_GUN) & h.notna()]
        satir[ay] = list(uygun.sort_values(ascending=False).index[:n])
    return satir


if __name__ == "__main__":
    e = evren()
    tum = sorted({s for v in e.values() for s in v})
    (KOK / "evren_semboller.txt").write_text("\n".join(tum))
    pd.Series(e).to_pickle(KOK / "evren.pkl")
    print(len(e), "ay,", len(tum), "farklı sembol")
    for ay in list(e)[::12]:
        print(ay.date(), len(e[ay]), e[ay][:12])
