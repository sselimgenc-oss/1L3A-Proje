"""v2 S4 ayı rejimi (ON_KAYIT_V2 6.1, "S4 tanımı"). Saf işlevler; veri okuma çağıran tarafta (geliştirme dönemi, 1d).

Endeks: stratejinin beyan ettiği evrenin 1d kapanışlarından günlük basit getiri; o gün verisi olan üyelerin eşit ağırlıklı
ortalaması (seans boşluğu için en çok S4_DOLDURMA_GUN gün ileri doldurma); endeks = birikimli çarpım, başlangıç 1.
Gün d AYI GÜNÜDÜR <=> endeks(d-1) < endeksin d-1'de biten S4_SMA_GUN günlük basit ortalaması. İlk S4_SMA_GUN gün tanımsız =
ayı değil. Etiket yalnız d-1 ve öncesini kullanır (d günü fiyatı etiketi değiştirmez).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.arastirma.v2 import sabit


def endeks_kur(kapanislar: dict) -> pd.Series:
    """kapanislar: {sembol: UTC günlük kapanış Series (indeks gün)}. -> endeks Series (gün indeksli, ilk değer 1.0)."""
    if not kapanislar:
        raise ValueError("endeks için kapanış serisi yok")
    gunler = pd.date_range(min(s.index.min() for s in kapanislar.values()).floor("D"),
                           max(s.index.max() for s in kapanislar.values()).floor("D"), freq="D", tz="UTC")
    kolonlar = {}
    for ad in sorted(kapanislar):
        s = kapanislar[ad].copy()
        s.index = pd.DatetimeIndex(s.index).floor("D")
        s = s.groupby(level=0).last().astype(float)
        bas, bit = s.index.min(), s.index.max()
        dolu = s.reindex(gunler).ffill(limit=sabit.S4_DOLDURMA_GUN)       # yalnız GEÇMİŞTEN doldurma; en çok 5 gün
        dolu[(gunler < bas) | (gunler > bit + pd.Timedelta(days=sabit.S4_DOLDURMA_GUN))] = np.nan
        kolonlar[ad] = dolu
    tablo = pd.DataFrame(kolonlar, index=gunler)
    getiri = tablo / tablo.shift(1) - 1.0                                   # NaN: o gün verisi olmayan üye
    ort = getiri.mean(axis=1, skipna=True).fillna(0.0)                      # üyesi olmayan gün: getiri 0
    return (1.0 + ort).cumprod().rename("endeks")


def ayi_gunleri(endeks: pd.Series) -> pd.Series:
    """bool Series (aynı indeks): gün d ayı günü mü. d günü endeks değeri KULLANILMAZ (shift)."""
    sma = endeks.rolling(sabit.S4_SMA_GUN).mean()
    onceki, onceki_sma = endeks.shift(1), sma.shift(1)
    return (onceki < onceki_sma).fillna(False).astype(bool)


def giris_ayi_mi(ayi: pd.Series, giris_zamanlari) -> np.ndarray:
    """İşlem GİRİŞ gününe göre ayı ataması (UTC günü). Seri dışı günler ayı değil."""
    gun = pd.DatetimeIndex(giris_zamanlari).tz_convert("UTC").floor("D")
    return ayi.reindex(gun).fillna(False).to_numpy(dtype=bool)
