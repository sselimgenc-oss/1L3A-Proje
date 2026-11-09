"""Portföy stratejisi arayüzü (karar 23).

Tek-grafik `Strateji`den farkı: aynı anda BİRDEN ÇOK sembolün verisini görür ve her sembol için HEDEF AĞIRLIK
üretir (rotasyon, kesitsel momentum, çift işlemi, ...).

  hedefler(veriler)         -> DataFrame: indeks = ORTAK ZAMAN EKSENİ (tüm sembol indekslerinin birleşimi, `ortak_eksen`),
                               sütun = sembol, değer = hedef ağırlık (-1..+1; +: long, -: short, 0: kapat),
                               NaN = değişiklik yok. NaN olmayan satır = o sembol için yeniden dengeleme emri.
                               Yeniden dengeleme takvimi (günlük/haftalık/aylık) böylece stratejinin kendisinde yaşar.
  stoplar(veriler, hedefler) -> DataFrame (aynı biçim): STOP FİYATI (mutlak fiyat). Hedefi sıfırdan farklı her satırda
                               stop ZORUNLU (yoksa motor ValueError verir). Hedefi NaN olan satırda dolu stop, açık
                               pozisyonun stopunu günceller (yalnız SIKILAŞTIRILIR; stop asla gevşemez; iz süren stop).

Zamanlama (tek-grafik motoruyla aynı): satır t'deki hedef/stop t barının KAPANIŞINDA bilinir; emir o sembolün
bir sonraki mumunun AÇILIŞINDA dolar. Sembol t'den sonra bir süre işlem görmüyorsa (hafta sonu, seans dışı) emir
ilk açık bara kayar. Satır t hesaplanırken yalnız zamanı <= t olan mumlar kullanılmalıdır (lookahead yasak).

Ortak zaman ekseninde sembolün mumu olmayan satırlarda strateji kendi verisini (ör. ileri doldurulmuş kapanış)
istediği gibi kullanır; motor yalnız DEĞERLEME için son bilinen fiyatı kullanır.

Sert limitler (SERT_LIMITLER) motorda uygulanır: hedef ağırlık işlem başı %1 risk, 3x brüt maruziyet, günlük %3 ve
%20 kill switch'e göre KÜÇÜLTÜLÜR/kapatılır; zarardaki pozisyon BÜYÜTÜLEMEZ (yalnız küçültülür/kapatılır).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as gst


def ortak_eksen(veriler: dict) -> pd.DatetimeIndex:
    """Sembol indekslerinin birleşimi (sıralı, tekrarsız, UTC). Adı `zaman`."""
    if not veriler:
        raise ValueError("veriler boş")
    idx = None
    for s, df in veriler.items():
        if not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
            raise ValueError(f"{s}: indeks UTC DatetimeIndex olmalı")
        idx = df.index if idx is None else idx.union(df.index)
    idx = idx.sort_values()
    idx.name = "zaman"
    return idx


def kapanis_tablosu(veriler: dict, ileri_doldur: bool = True) -> pd.DataFrame:
    """Ortak eksende sembol kapanışları. ileri_doldur=True: son bilinen kapanış (yalnız geçmiş -> lookahead yok)."""
    eksen = ortak_eksen(veriler)
    t = pd.DataFrame({s: df["kapanis"].reindex(eksen) for s, df in veriler.items()})
    return t.ffill() if ileri_doldur else t


def atr_tablosu(veriler: dict, periyot: int = 14, ileri_doldur: bool = True) -> pd.DataFrame:
    """Ortak eksende sembol ATR değerleri (sembolün KENDİ mumlarından hesaplanır, sonra eksene taşınır)."""
    eksen = ortak_eksen(veriler)
    t = pd.DataFrame({s: gst.atr(df["yuksek"], df["dusuk"], df["kapanis"], periyot).reindex(eksen)
                      for s, df in veriler.items()})
    return t.ffill() if ileri_doldur else t


class PortfoyStratejisi(ABC):
    ad: str = ""
    stil: str = "portfoy"
    varsayilan_parametreler: dict = {}
    parametre_izgarasi: dict = {}

    def __init__(self, **parametreler):
        bilinmeyen = set(parametreler) - set(self.varsayilan_parametreler)
        if bilinmeyen:
            raise ValueError(f"Bilinmeyen parametre: {sorted(bilinmeyen)}")
        self.parametreler = {**self.varsayilan_parametreler, **parametreler}

    def yeni(self, **parametreler) -> "PortfoyStratejisi":
        """Aynı yapılandırmada, bazı parametreleri değişmiş kopya (walk-forward için)."""
        return type(self)(**{**self.parametreler, **parametreler})

    @abstractmethod
    def hedefler(self, veriler: dict) -> pd.DataFrame:
        ...

    @abstractmethod
    def stoplar(self, veriler: dict, hedefler: pd.DataFrame) -> pd.DataFrame:
        ...

    def sinyaller(self, veriler: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
        """(hedefler, stoplar) — biçim doğrulanmış. Motor bunu çağırır."""
        eksen = ortak_eksen(veriler)
        h = self.hedefler(veriler)
        _bicim_dogrula(h, eksen, veriler, "hedefler")
        h = h.reindex(eksen)
        v = h.to_numpy(dtype=float)
        if np.any(np.abs(v[~np.isnan(v)]) > 1.0 + 1e-9):
            raise ValueError("hedef ağırlık -1..+1 aralığında olmalı")
        s = self.stoplar(veriler, h)
        _bicim_dogrula(s, eksen, veriler, "stoplar")
        return h, s.reindex(eksen)


def _bicim_dogrula(df, eksen, veriler, ad):
    if not isinstance(df, pd.DataFrame):
        raise ValueError(f"{ad}() DataFrame dönmeli")
    if not df.index.is_unique or not df.index.isin(eksen).all():
        raise ValueError(f"{ad}(): indeks ortak zaman ekseninin alt kümesi olmalı")
    bilinmeyen = [c for c in df.columns if c not in veriler]
    if bilinmeyen:
        raise ValueError(f"{ad}(): verisi olmayan sütunlar: {bilinmeyen}")
