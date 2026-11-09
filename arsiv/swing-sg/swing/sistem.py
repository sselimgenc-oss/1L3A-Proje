"""Seçili 3 stratejinin birleşik backtest raporu."""
import pandas as pd

from .ayarlar import MAX_AGIRLIK, MAX_POZ, RISK, SECILI, SINIFLAR
from .calistir import islemler, ozet, sinif_kirilim, yazdir, yillik_kirilim
from .motor import portfoy


def tum_islemler():
    return {k: islemler(k, p, SINIFLAR[k]) for k, p in SECILI.items()}


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    T = tum_islemler()
    for k, tr in T.items():
        yazdir(ozet(tr, k))
    hep = sum(T.values(), [])
    yazdir(ozet(hep, "BİRLEŞİK SİSTEM"))
    print(sinif_kirilim(hep).to_string(index=False))
    print(yillik_kirilim(hep).to_string(index=False))
    p = portfoy(hep, risk=RISK, max_poz=MAX_POZ, max_agirlik=MAX_AGIRLIK)
    e = p["egri"]
    yil = e.resample("YE").last()
    print((yil.pct_change().fillna(yil.iloc[0] / 100_000 - 1)).map("{:.1%}".format).to_string())
