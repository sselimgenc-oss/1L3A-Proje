"""Walk-forward: kayan pencerelerde eğitimde en iyi parametreyi seç, testte (OOS) uygula.

Pencere i: eğitim [e0, e0+N), test [e0+N, e0+N+M); sonraki pencere M gün ileri kayar.
Test pencereleri birbirini kesmez ve boşluksuz uç uca gelir. İlk eğitim, ısınma (warm-up)
payı kadar mum SONRA başlar; her koşuda eğitim/test başlangıcından önceki `isinma_mum` mum
yalnızca gösterge ısınması için verilir, o bölgede işlem açılmaz.
"""
from dataclasses import replace
from itertools import product

import numpy as np
import pandas as pd

from motor.backtest import metrikler as mtr
from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.temel import Strateji


def pencereler_uret(baslangic: pd.Timestamp, bitis: pd.Timestamp, egitim_gun: int, test_gun: int):
    """[(egitim_bas, egitim_bit, test_bas, test_bit), ...]; bitişler hariç."""
    out = []
    e0 = baslangic
    egitim, test = pd.Timedelta(days=egitim_gun), pd.Timedelta(days=test_gun)
    while e0 + egitim + test <= bitis:
        out.append((e0, e0 + egitim, e0 + egitim, e0 + egitim + test))
        e0 = e0 + test
    return out


def _skor(metrik: dict, hedef: str, min_islem: int) -> float:
    if metrik["islem_sayisi"] < min_islem:
        return -np.inf
    v = metrik.get(hedef, np.nan)
    if v is None or np.isnan(v):
        return -np.inf
    return float(v)


def walk_forward(strateji: Strateji, mumlar: pd.DataFrame, ayarlar: MotorAyarlari = None,
                 funding: pd.DataFrame = None, egitim_gun: int = 180, test_gun: int = 30,
                 hedef: str = "profit_factor", min_islem: int = 30, isinma_mum: int = 300) -> dict:
    ayarlar = ayarlar or MotorAyarlari()
    izgara = strateji.parametre_izgarasi
    adlar = list(izgara)
    kombinasyonlar = [dict(zip(adlar, v)) for v in product(*izgara.values())] or [{}]

    def kos(bas, bit, baslangic_sermaye, **param):
        ilk = mumlar.index.searchsorted(bas)
        dilim = mumlar.iloc[max(ilk - isinma_mum, 0):mumlar.index.searchsorted(bit)]
        fd = funding.loc[(funding.index >= dilim.index[0]) & (funding.index < bit)] if funding is not None else None
        s = backtest(dilim, strateji.yeni(**param), replace(ayarlar, baslangic_sermaye=baslangic_sermaye),
                     fd, islem_baslangic=bas)
        s.ozsermaye = s.ozsermaye[s.ozsermaye.index >= bas]
        s.limit_olaylari = [o for o in s.limit_olaylari if o["zaman"] >= bas]
        return s

    pencereler = pencereler_uret(mumlar.index[min(isinma_mum, len(mumlar) - 1)], mumlar.index[-1] + pd.Timedelta(1, "ns"),
                                 egitim_gun, test_gun)
    rapor, islemler, egriler, limit_olaylari = [], [], [], []
    sermaye = float(ayarlar.baslangic_sermaye)
    for e0, e1, t0, t1 in pencereler:
        en_iyi, en_skor = None, -np.inf
        for param in kombinasyonlar:
            s = kos(e0, e1, ayarlar.baslangic_sermaye, **param)
            skor = _skor(mtr.hesapla(s.islemler, s.ozsermaye, s.baslangic_sermaye), hedef, min_islem)
            if skor > en_skor:
                en_iyi, en_skor = param, skor
        kayit = {"egitim_bas": e0, "egitim_bit": e1, "test_bas": t0, "test_bit": t1,
                 "secilen": en_iyi, "egitim_skor": en_skor if en_iyi is not None else None}
        if en_iyi is not None:
            s = kos(t0, t1, sermaye, **en_iyi)
            sermaye = float(s.ozsermaye.iloc[-1])
            islemler.append(s.islemler[s.islemler["giris_zamani"] >= t0])
            egriler.append(s.ozsermaye)
            kayit["limit_olay_sayisi"] = len(s.limit_olaylari)
            limit_olaylari.extend(s.limit_olaylari)
        rapor.append(kayit)

    islem_df = pd.concat(islemler, ignore_index=True) if islemler else pd.DataFrame()
    egri = pd.concat(egriler) if egriler else pd.Series(dtype=float)
    sonuc = {"pencereler": rapor, "islemler": islem_df, "ozsermaye": egri,
             "limit_olaylari": limit_olaylari, "limit_modu": ayarlar.limit_modu}
    sonuc["metrikler"] = (mtr.hesapla(islem_df, egri, ayarlar.baslangic_sermaye)
                          if len(egri) > 1 else {})
    return sonuc
