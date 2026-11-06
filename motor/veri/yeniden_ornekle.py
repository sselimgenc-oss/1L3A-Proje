"""Mumları üst zaman dilimine birleştirme (UTC sınırlarına hizalı)."""
from __future__ import annotations

import pandas as pd

from motor.veri.depo import aralik_suresi


def yeniden_ornekle(df: pd.DataFrame, hedef: str, kaynak: str = "5m",
                    eksikleri_at: bool = False) -> pd.DataFrame:
    """OHLCV'yi `kaynak` aralığından `hedef` aralığına birleştirir.

    Çıktı sözleşmedeki sütunlara ek olarak `eksik` (bool) sütunu taşır: periyottaki
    kaynak mum sayısı beklenenden azsa True (ör. 1h için 12'den az 5m mum).
    Hiç mumu olmayan periyotlar çıktıda yer almaz. eksikleri_at=True ise eksik
    periyotlar atılır.
    """
    kaynak_s, hedef_s = aralik_suresi(kaynak), aralik_suresi(hedef)
    if hedef_s < kaynak_s or hedef_s % kaynak_s != pd.Timedelta(0):
        raise ValueError(f"{kaynak} -> {hedef} birleştirilemez")
    beklenen = int(hedef_s / kaynak_s)
    g = df.groupby(df.index.floor(hedef_s))
    cikti = pd.DataFrame({
        "acilis": g["acilis"].first(),
        "yuksek": g["yuksek"].max(),
        "dusuk": g["dusuk"].min(),
        "kapanis": g["kapanis"].last(),
        "hacim": g["hacim"].sum(),
        "quote_hacim": g["quote_hacim"].sum(),
        "islem_sayisi": g["islem_sayisi"].sum().astype("int64"),
    })
    cikti["eksik"] = g["acilis"].count() < beklenen
    cikti.index.name = "zaman"
    if eksikleri_at:
        cikti = cikti[~cikti["eksik"]].drop(columns="eksik")
    return cikti
