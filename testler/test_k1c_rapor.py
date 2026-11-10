"""K1c açıklama alanları yalnız rapordur; S1 kapısı değişmez."""
import json

import pandas as pd
import pytest

from motor.arastirma.v2 import saglamlik


def _islemler(idx, girisler, yonler, rs):
    return pd.DataFrame({"giris_zamani": idx[girisler], "yon": yonler, "r": rs})


def test_k1c_eslesme_reddedilme_ve_pf():
    idx = pd.date_range("2024-01-01", periods=9, freq="D", tz="UTC")
    temel = {"BTC": _islemler(idx, [1, 3, 5], [1, -1, 1], [2.0, -1.0, -1.0])}
    gecikmeli = {"BTC": _islemler(idx, [2, 6, 8], [1, 1, -1], [1.0, 2.0, -0.5])}
    bilgi = {"k1c_indeks": {"BTC": idx},
             "k1c_reddedilenler": {"BTC": {"gecersiz_stop": 2, "min_qty": 1}}}
    rapor = saglamlik.k1c_rapor(temel, gecikmeli, bilgi, idx[0], 1.0, 1.5)
    assert rapor["k1c_eslesen_islem"] == 2
    assert rapor["k1c_yalniz_temel"] == 1
    assert rapor["k1c_yalniz_gecikmeli"] == 1
    assert json.loads(rapor["k1c_reddedilenler"]) == {"gecersiz_stop": 2, "min_qty": 1}
    assert rapor["k1c_reddedilen_gecersiz_stop"] == 2
    assert rapor["k1c_eslesen_temel_pf"] == pytest.approx(2.0)
    assert rapor["k1c_eslesen_gecikmeli_pf"] == pytest.approx(float("inf"))
    assert rapor["k1c_atlanan_toplam_r"] == -1.0
    assert rapor["k1c_atlanan_ortalama_r"] == -1.0
    assert rapor["k1c_aciklama_gerekli"] is True


def test_k1c_sadece_bilgi_kapi_ayni():
    idx = pd.date_range("2024-01-01", periods=4, freq="D", tz="UTC")
    temel = {"BTC": _islemler(idx, [1], [1], [-1.0])}
    gecikmeli = {"BTC": _islemler(idx, [2], [1], [1.0])}
    bilgi = {"k1c_indeks": {"BTC": idx}, "k1c_reddedilenler": {"BTC": {}}}
    for pf in (0.5, 1.5):
        karar = saglamlik.s1_karar(pf)
        rapor = saglamlik.k1c_rapor(temel, gecikmeli, bilgi, idx[0], 0.5, pf)
        assert saglamlik.s1_karar(pf) == karar
        assert "s1" not in rapor and "s1_pf" not in rapor
        assert rapor["k1c_aciklama_gerekli"] == (pf > 0.5)
