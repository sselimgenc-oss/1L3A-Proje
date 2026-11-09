"""Dış kaynak (TradingView/freqtrade) ayarları: her biri kurulur, sinyaller() çalışır, backtest CikisYokHatasi vermez."""
import json

import pytest

from motor.arastirma import tarama
from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from testler.test_bt_strateji import rastgele_mumlar

DIZIN = tarama.DIS_AYAR_DIZINI
_CIKIS_ALANLARI = {"atr_iz_suren_k", "atr_periyot", "zaman_cikisi_mum", "sabit_r_hedefi", "basabas_r_esigi", "kismi"}
KOMBO = [(y.stem, k["dis_id"]) for y in sorted(DIZIN.glob("*.json"))
         for k in json.loads(y.read_text(encoding="utf-8"))]
MUMLAR = rastgele_mumlar(n=24 * 40, seed=11)   # 1h, 40 gün


def test_dis_ayar_dosyalari_var():
    assert KOMBO, "stratejiler/dis_ayarlari/ boş"


def test_dosya_adi_strateji_ve_anahtarlar():
    for yol in sorted(DIZIN.glob("*.json")):
        sinif = kayit.al(yol.stem)           # dosya adı = aile_id; yoksa KeyError
        idler = []
        for k in json.loads(yol.read_text(encoding="utf-8")):
            assert set(k) == {"dis_id", "kaynak_dosya", "parametreler", "cikis_ayarlari", "not"}, (yol.name, k.get("dis_id"))
            assert set(k["parametreler"]) <= set(sinif.varsayilan_parametreler), (yol.name, k["dis_id"])
            assert k["cikis_ayarlari"] is None or set(k["cikis_ayarlari"]) <= _CIKIS_ALANLARI
            idler.append(k["dis_id"])
        assert len(idler) == len(set(idler)), f"{yol.name}: dis_id tekrarı"


@pytest.mark.parametrize("aile,dis_id", KOMBO)
def test_dis_ayarli_strateji_sinyal_ve_backtest(aile, dis_id):
    s = tarama.dis_ayarli_strateji(aile, dis_id)
    sig = s.sinyaller(MUMLAR)
    assert len(sig) == len(MUMLAR)
    assert {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)
    backtest(MUMLAR, s, MotorAyarlari())   # CikisYokHatasi atmamalı
