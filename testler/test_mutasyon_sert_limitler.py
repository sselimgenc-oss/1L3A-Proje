"""Mutasyon testi (b): SERT_LIMITLER değişmezliği ve belgelenen değerler (motor/risk/limitler.py; kullanıcı onaylı).
Değerleri değiştirmek kullanıcı kararıdır: bu test bilerek sabit sayıları yazar."""
import dataclasses

import pytest

from motor.risk import limitler
from motor.risk.limitler import SERT_LIMITLER, SertLimitler

BELGELI = {"islem_basi_max_risk_yuzde": 1.0, "gunluk_max_kayip_yuzde": 3.0, "max_kaldirac": 3.0,
           "kill_switch_dusus_yuzde": 20.0, "portfoy_toplam_risk_yuzde": 5.0}


def test_degerler_belgelenenle_ayni_ve_alan_kumesi_tam():
    assert {f.name for f in dataclasses.fields(SertLimitler)} == set(BELGELI)       # sessizce yeni/eksik alan yok
    for ad, deger in BELGELI.items():
        assert getattr(SERT_LIMITLER, ad) == deger, ad
    assert SertLimitler() == SERT_LIMITLER                                          # varsayılanlar = tekil örnek


@pytest.mark.parametrize("ad", sorted(BELGELI))
def test_calisma_aninda_degistirilemez(ad):
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(SERT_LIMITLER, ad, 99.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        delattr(SERT_LIMITLER, ad)
    assert getattr(SERT_LIMITLER, ad) == BELGELI[ad]


def test_sinif_donmus_ve_yeni_alan_eklenemez():
    assert SertLimitler.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        SERT_LIMITLER.yeni_alan = 1


def test_motorlar_ayni_tekil_ornegi_kullanir():
    from motor.backtest import motor as bm
    from motor.portfoy import motor as pm
    assert bm.SERT_LIMITLER is limitler.SERT_LIMITLER and pm.SERT_LIMITLER is limitler.SERT_LIMITLER


def test_ayar_sert_limiti_asamaz():
    import numpy as np
    from motor.backtest.motor import MotorAyarlari, backtest
    from testler.test_bt_motor import Hazir, SIFIR, mumlar_yap, sinyal_yap
    df = mumlar_yap([(100, 100, 100, 100)] * 4)
    sig = sinyal_yap(df, {0: (1, 99.9, np.nan)}, cikislar=[1])
    r = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR, kaldirac=50, risk_yuzde=9.0))
    assert r.islemler.iloc[0].miktar == pytest.approx(300.0)          # 3x * 10000 / 100; 50x değil
    assert any("sert limit" in u for u in r.uyarilar)
