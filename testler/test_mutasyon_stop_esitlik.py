"""Mutasyon testi (a): stop eşitlik sınırı. Mevcut anlam (motor/backtest/motor.py, mum içi stop kontrolü):
long: dusuk <= stop -> çıkış; short: yuksek >= stop -> çıkış (EŞİTLİK dahil). Açılış == stop ise 'stop_gap' (açılıştan dolum).
`<=` -> `<` mutasyonu bu testlerle yakalanır. Motor davranışı DEĞİŞTİRİLMEZ, yalnız kilitlenir."""
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from testler.test_bt_motor import Hazir, SIFIR, mumlar_yap, sinyal_yap

HAZIR = [(100, 100, 100, 100)]            # sinyal mumu; giriş bir sonraki açılışta (100)


def _kos(yon, stop, mum):
    df = mumlar_yap(HAZIR + [(100, 100.5, 99.5, 100), mum, (100, 100, 100, 100)])
    sig = sinyal_yap(df, {0: (yon, stop, float("nan"))})
    return backtest(df, Hazir(sig), MotorAyarlari(**SIFIR)).islemler


def test_long_dusuk_tam_stop_ise_cikar():
    t = _kos(1, 98.0, (100, 100.2, 98.0, 99.0)).iloc[0]       # low == stop
    assert t.cikis_nedeni == "stop" and t.cikis_fiyati == pytest.approx(98.0)


def test_long_dusuk_stoptan_bir_tik_ustte_cikmaz():
    islemler = _kos(1, 98.0, (100, 100.2, 98.01, 99.0))
    assert islemler.iloc[0].cikis_nedeni == "veri_sonu"


def test_short_yuksek_tam_stop_ise_cikar():
    t = _kos(-1, 102.0, (100, 102.0, 99.8, 101.0)).iloc[0]    # high == stop
    assert t.cikis_nedeni == "stop" and t.cikis_fiyati == pytest.approx(102.0)


def test_short_yuksek_stoptan_bir_tik_altta_cikmaz():
    islemler = _kos(-1, 102.0, (100, 101.99, 99.8, 101.0))
    assert islemler.iloc[0].cikis_nedeni == "veri_sonu"


def test_long_acilis_tam_stop_ise_stop_gap_acilistan():
    t = _kos(1, 98.0, (98.0, 99.0, 97.5, 98.5)).iloc[0]       # open == stop
    assert t.cikis_nedeni == "stop_gap" and t.cikis_fiyati == pytest.approx(98.0)


def test_short_acilis_tam_stop_ise_stop_gap_acilistan():
    t = _kos(-1, 102.0, (102.0, 102.5, 101.0, 101.5)).iloc[0]
    assert t.cikis_nedeni == "stop_gap" and t.cikis_fiyati == pytest.approx(102.0)
