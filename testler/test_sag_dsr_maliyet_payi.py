"""Regresyon: sağlamlık DSR serisi (_gunluk_dizi) OOS tablosundaki maliyet_payi'yi korumalı.

Hata (2026-11-09): _gunluk_dizi sütun seçerken maliyet_payi'yi düşürüyordu; secim.yeniden_oyna ValueError verdi ve
sağlamlık aşaması başlamadan durdu. DSR serisi WF yeniden oynatmasıyla AYNI olmalı (maliyet dahil).
"""
import numpy as np
import pandas as pd

from motor.arastirma import wf_evren as w


def _oos(mp: float) -> pd.DataFrame:
    giris = pd.date_range("2021-01-04", periods=6, freq="2D", tz="UTC")
    return pd.DataFrame({
        "kol": ["BTCUSDT", "ETHUSDT"] * 3, "sembol": ["BTCUSDT", "ETHUSDT"] * 3, "yon": [1, -1, 1, 1, -1, 1],
        "giris": giris, "cikis": giris + pd.Timedelta("1D"),
        "r": [1.5, -1.0, 2.0, -1.0, 0.8, 1.2], "sf": [0.02] * 6, "stop_mesafe": [100.0] * 6, "maliyet_payi": [mp] * 6,
        "fazla_sutun": ["x"] * 6})


def test_gunluk_dizi_maliyet_payi_ile_calisir_ve_wf_ile_ayni():
    oos = _oos(0.004)
    rec = {"oos_bas": "2021-01-01 00:00+00:00", "oos_bit": "2021-02-01 00:00+00:00"}
    seri = w._gunluk_dizi(oos, rec)
    tablo = oos[["kol", "sembol", "yon", "giris", "cikis", "r", "sf", "stop_mesafe", "maliyet_payi"]]
    beklenen = w.kasa_metrikleri(tablo, pd.Timestamp(rec["oos_bas"]), pd.Timestamp(rec["oos_bit"]))["getiri_serisi"]
    assert np.allclose(seri, beklenen.to_numpy(dtype=float), equal_nan=True)


def test_gunluk_dizi_maliyet_payini_gercekten_kullanir():
    rec = {"oos_bas": "2021-01-01 00:00+00:00", "oos_bit": "2021-02-01 00:00+00:00"}
    s0 = w._gunluk_dizi(_oos(0.0), rec)
    s1 = w._gunluk_dizi(_oos(0.01), rec)
    assert np.prod(1 + s1) < np.prod(1 + s0)       # maliyet payı risk tabanını küçültür -> farklı (düşük) seri
