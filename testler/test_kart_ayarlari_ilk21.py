"""İlk 21 ailenin kart ayarları: her biri kurulur, sinyaller() çalışır, backtest CikisYokHatasi vermez."""
import json

import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from testler.test_bt_strateji import rastgele_mumlar

AILELER = [
    "swing__ma-kesisim", "swing__macd-sinyal", "swing__ma-geri-cekilme", "swing__bant-donus",
    "swing__dar-aralik-kirilim", "swing__konsolidasyon-kirilim", "swing__cift-dip-tepe",
    "swing__fib-geri-cekilme", "swing__aralik-ticareti", "swing__mum-yutan-donus",
    "daytrade__pivot-seviye", "daytrade__konsolidasyon-kirilim", "daytrade__kirilim-geri-test",
    "daytrade__bb-sikisma-kirilim", "daytrade__vwap-donus", "daytrade__orb",
    "scalp__stokastik-donus", "scalp__ma-kesisim", "scalp__ma-geri-cekilme",
    "scalp__supertrend-psar", "scalp__konsolidasyon-kirilim",
]
KOMBO = [(a, k["kart_id"]) for a in AILELER for k in kayit.kart_ayarlari(a)]
MUMLAR = rastgele_mumlar(n=24 * 40, seed=11)   # 1h, 40 gün


def test_her_aile_dosyasi_var():
    for a in AILELER:
        assert kayit.kart_ayarlari(a), a


def test_dosyalarda_kart_ayari_dogrulanir():
    assert kayit.dogrula() == []


@pytest.mark.parametrize("aile,kart", KOMBO)
def test_kart_ayarli_strateji_sinyal_ve_backtest(aile, kart):
    s = kayit.kart_ayarli_strateji(aile, kart)
    sig = s.sinyaller(MUMLAR)
    assert len(sig) == len(MUMLAR)
    assert {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)
    backtest(MUMLAR, s, MotorAyarlari())   # CikisYokHatasi atmamalı
