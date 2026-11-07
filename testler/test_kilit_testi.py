"""Kilitli dönem testi (kilit_testi.py): ayar seçimi kilit öncesi veriyle, işlemler yalnız kilitli dönemde, açılış günlüğe."""
import json

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import kilit_testi as kt
from motor.veri import kilit

SW = "swing__donchian-kirilim"
SEMBOL = "TESTUSDT"
KB = pd.Timestamp("2025-11-01", tz="UTC")


def _veri(tmp_path, kilitli_carpan=1.0, ad="v"):
    """2022-01..2026-03 saatlik sentetik fiyat (dalgalı trend). kilitli_carpan: kilit sonrası fiyatları değiştirir."""
    idx = pd.date_range("2022-01-01", "2026-03-01", freq="1h", tz="UTC", inclusive="left")
    t = np.arange(len(idx))
    rng = np.random.default_rng(7)
    fiyat = 100 + 25 * np.sin(t / 700.0) + np.cumsum(rng.normal(0, 0.15, len(idx)))
    fiyat = np.maximum(fiyat, 5.0)
    fiyat = np.where(idx >= KB, fiyat * kilitli_carpan + (t - t[idx >= KB][0]) * 0.01 * (kilitli_carpan - 1), fiyat)
    df = pd.DataFrame({"acilis": fiyat, "yuksek": fiyat * 1.004, "dusuk": fiyat * 0.996, "kapanis": fiyat,
                       "hacim": 10.0, "quote_hacim": fiyat * 10.0, "islem_sayisi": 5}, index=idx)
    df["islem_sayisi"] = df["islem_sayisi"].astype("int64")
    d = tmp_path / ad / SEMBOL
    d.mkdir(parents=True)
    df.to_parquet(d / "1h.parquet")
    return tmp_path / ad


def test_ayar_secimi_kilitli_veriden_bagimsiz(tmp_path):
    a = kt.ayar_sec_tek(SW, SEMBOL, "1d", _veri(tmp_path, 1.0, "a"), min_islem=3)
    b = kt.ayar_sec_tek(SW, SEMBOL, "1d", _veri(tmp_path, 3.0, "b"), min_islem=3)   # kilitli dönem fiyatları çok farklı
    assert a["secilen_ayar"] is not None
    assert a["secilen_ayar"] == b["secilen_ayar"]
    assert a["egitim_skor"] == b["egitim_skor"] and a["egitim_islem"] == b["egitim_islem"]
    assert pd.Timestamp(a["veri_son"]) < KB                                      # seçimde kilitli bar görülmedi
    assert a["egitim_bit"] == str(KB) and a["egitim_bas"] == str(KB - pd.Timedelta(days=730))


def test_egitim_penceresi_stile_gore():
    assert kt.egitim_penceresi("swing")[1] == KB and kt.egitim_penceresi("swing")[0] == KB - pd.Timedelta(days=730)
    assert kt.egitim_penceresi("daytrade")[0] == KB - pd.Timedelta(days=365)
    assert kt.egitim_penceresi("scalp")[0] == KB - pd.Timedelta(days=365)
    assert kt.egitim_penceresi("portfoy")[0] == KB - pd.Timedelta(days=730)


def test_kilit_kosusu_islemler_yalniz_kilitli_donemde_ve_gunluge_yazilir(tmp_path):
    veri = _veri(tmp_path, 1.0, "c")
    ayar = kt.ayar_sec_tek(SW, SEMBOL, "1d", veri, min_islem=3)["secilen_ayar"]
    assert not kilit.KILIT_LOG.exists()                                           # ayar seçimi kilidi açmadı
    m, oos = kt.kilit_kos_tek(SW, SEMBOL, "1d", ayar, veri, kilit_baslangic=KB, kilit_ac=True, gerekce=kt.GEREKCE)
    assert m["kilit_bar_sayisi"] > 0
    assert len(oos) > 0
    assert pd.DatetimeIndex(oos["giris_zamani"]).min() >= KB
    assert pd.Timestamp(m["ilk_giris"]) >= KB
    satirlar = [json.loads(x) for x in kilit.KILIT_LOG.read_text(encoding="utf-8").splitlines()]
    assert satirlar and all(s["gerekce"] == kt.GEREKCE for s in satirlar)
    assert any(s["sembol"] == SEMBOL for s in satirlar)


def test_kilit_gerekcesiz_acilmaz(tmp_path):
    veri = _veri(tmp_path, 1.0, "d")
    with pytest.raises(ValueError):
        kt.kilit_kos_tek(SW, SEMBOL, "1d", "varsayilan", veri, kilit_baslangic=KB, kilit_ac=True, gerekce="")


def test_kilit_asamasi_onkosulsuz_calismaz(tmp_path):
    with pytest.raises(RuntimeError):
        kt.asama_kilit(cikti=tmp_path)
    assert not kilit.KILIT_LOG.exists()


def test_aday_karari_olcutu():
    assert kt.aday_karari(0.05, 1.3, 10) == (True, "")
    assert kt.aday_karari(0.05, float("inf"), 3) == (True, "")
    assert kt.aday_karari(0.0, 1.0, 5)[0] is False           # net > 0 şart
    assert kt.aday_karari(0.05, 0.99, 5)[0] is False         # PF >= 1.0 şart
    assert kt.aday_karari(0.0, float("nan"), 0)[0] is False  # işlem yok = kaldı
    assert kt.aday_karari(0.1, 2.0, 5, hata="x")[0] is False


def test_gruplar_on_kayita_uygun():
    g = kt.gruplari_kur()
    assert int(g.A.sum()) == 7 and int(g.B.sum()) == 6
    assert (g[g.A | g.B].C).all()                            # A ve B, C'nin alt kümesi
    assert not (g.C & g.D).any()                             # C önceliklidir
    assert int((g.d_kaynak == "rastgele").sum()) == 60
    assert g["kimlik"].is_unique
    g2 = kt.gruplari_kur()
    assert list(g["kimlik"]) == list(g2["kimlik"])           # tohum 42: tekrarlanabilir
