"""Örnek portföy stratejisi (YALNIZ motoru sınamak için; gerçek strateji değildir).

"Son `getiri_n` mumda en çok yükselen K sembolü eşit ağırlıkla long; her periyotta (D/W/M) yeniden dengele;
stop = kapanış - atr_k * ATR (iz süren, yalnız sıkılaşır)."

Kurallar
  - Yeniden dengeleme satırı: yeni bir takvim periyodunun (gün/hafta/ay) İLK ortak-eksen satırı (periyot değişimi
    önceki satıra göre bilinir -> nedensel). Bu satırın kapanışında hesaplanır, sonraki açılışta dolar.
    İlk geçerli satır (tüm göstergeler dolu) de bir yeniden dengelemedir.
  - Seçim: getiri_n mumluk getirisi hesaplanabilen semboller arasından en yüksek K; yalnız getirisi > 0 olanlar
    (min_getiri) seçilir, kalanı nakit. Ağırlık 1/K (seçilen sayıdan bağımsız: K'dan az seçilirse brüt < 1).
  - Seçilmeyenler 0 hedeflenir (kapatılır). Zararda büyütme motorda yasaktır.
  - getiri mumları ve ATR sembolün KENDİ mumlarından ve ileri doldurulmuş kapanıştan (yalnız geçmiş) hesaplanır.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.portfoy.temel import PortfoyStratejisi, atr_tablosu, kapanis_tablosu, ortak_eksen


class EnGucluKSembol(PortfoyStratejisi):
    ad = "ornek__en-guclu-k"
    varsayilan_parametreler = {"getiri_n": 30, "k": 2, "takvim": "M", "atr_k": 3.0, "atr_periyot": 14,
                               "min_getiri": 0.0}
    parametre_izgarasi = {"getiri_n": [20, 30, 60], "k": [1, 2], "atr_k": [2.0, 3.0]}

    def _periyot(self, eksen: pd.DatetimeIndex) -> pd.Series:
        takvim = self.parametreler["takvim"]
        if takvim == "D":
            return pd.Series(eksen.floor("D"), index=eksen)
        if takvim == "W":
            return pd.Series(eksen.tz_localize(None).to_period("W").start_time, index=eksen)
        if takvim == "M":
            return pd.Series(eksen.tz_localize(None).to_period("M").start_time, index=eksen)
        raise ValueError("takvim D, W veya M olmalı")

    def hedefler(self, veriler: dict) -> pd.DataFrame:
        p = self.parametreler
        kap = kapanis_tablosu(veriler)
        atr = atr_tablosu(veriler, p["atr_periyot"])
        getiri = kap / kap.shift(p["getiri_n"]) - 1.0
        gecerli = getiri.notna() & atr.notna()
        yeniden = self._periyot(kap.index).ne(self._periyot(kap.index).shift(1))
        ilk = gecerli.any(axis=1) & ~gecerli.any(axis=1).shift(1, fill_value=False)
        tetik = (yeniden | ilk) & gecerli.any(axis=1)
        h = pd.DataFrame(np.nan, index=kap.index, columns=kap.columns)
        for t in kap.index[tetik.to_numpy()]:
            g = getiri.loc[t].where(gecerli.loc[t])
            sec = g[g > p["min_getiri"]].nlargest(p["k"]).index
            h.loc[t, :] = 0.0
            h.loc[t, sec] = 1.0 / p["k"]
        return h

    def stoplar(self, veriler: dict, hedefler: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = kapanis_tablosu(veriler)
        atr = atr_tablosu(veriler, p["atr_periyot"])
        tutulan = hedefler.ffill().fillna(0.0).reindex(columns=kap.columns) > 0     # nedensel: yalnız geçmiş hedefler
        stop = (kap - p["atr_k"] * atr).where(tutulan)
        return stop
