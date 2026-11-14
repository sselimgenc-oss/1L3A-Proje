"""Kapanış ek 10 ileri dönem sınavı: ölçüt mantığı, dönem kesimi, tek-koşu koruması (SENTETİK veri; gerçek mum/holdout okunmaz)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from araclar import kapanis_ileri_sinav as ik
from araclar import kapanis_kosu as kk

BAS = ik.DONEM_BAS


# ---------------------------------------------------------------- ölçüt mantığı
def test_olcut_gecti():
    o = ik.olcut_degerlendir(0.20, 0, True, 0.05, 50)
    assert o["a_net_pozitif"] and o["b_kill_yok"] and o["c_al_tutu_gecti"] is True
    assert o["karar"] == "gecti" and not o["yetersiz_ornek"]


def test_olcut_net_negatif_paperdan_cikar():
    assert ik.olcut_degerlendir(-0.01, 0, False, math.nan, 50)["karar"] == "paper_cikar"
    assert ik.olcut_degerlendir(0.0, 0, False, math.nan, 50)["karar"] == "paper_cikar"       # net > 0 kesin


def test_olcut_kill_paperdan_cikar():
    o = ik.olcut_degerlendir(0.5, 1, True, 0.0, 50)
    assert not o["b_kill_yok"] and o["karar"] == "paper_cikar"


def test_olcut_al_tutu_gecemedi_long_only():
    o = ik.olcut_degerlendir(0.10, 0, True, 0.30, 50)
    assert o["c_al_tutu_gecti"] is False and o["karar"] == "al_tutu_gecemedi"
    assert ik.olcut_degerlendir(0.30, 0, True, 0.30, 50)["c_al_tutu_gecti"] is True            # eşitlik geçer (al-tut <= strateji)


def test_olcut_long_only_degilse_c_yok():
    o = ik.olcut_degerlendir(0.10, 0, False, math.nan, 50)
    assert o["c_al_tutu_gecti"] is None and o["karar"] == "gecti"


def test_olcut_nan_gecmez():
    assert ik.olcut_degerlendir(math.nan, 0, False, math.nan, 50)["karar"] == "paper_cikar"
    assert ik.olcut_degerlendir(0.1, 0, True, math.nan, 50)["c_al_tutu_gecti"] is False


def test_yetersiz_ornek_etiketi_olcutleri_degistirmez():
    az = ik.olcut_degerlendir(0.2, 0, True, 0.0, 19)
    assert az["yetersiz_ornek"] and az["karar"] == "gecti"
    assert not ik.olcut_degerlendir(0.2, 0, True, 0.0, 20)["yetersiz_ornek"]
    assert ik.olcut_degerlendir(-0.2, 0, True, 0.0, 5)["karar"] == "paper_cikar"


def test_bh_bitisi_ve_toplam():
    assert ik.bh_bitisi("2026-11-07 00:00") == pd.Timestamp("2026-11-07", tz="UTC")             # gece yarısı: önceki gün tam
    assert ik.bh_bitisi("2026-11-06 23:55") == pd.Timestamp("2026-11-06", tz="UTC")             # kısmi gün dışarıda
    assert ik.bh_toplam([0.1, 0.1]) == pytest.approx(0.21)
    assert math.isnan(ik.bh_toplam([]))


def test_kapanmamis_mum_atilir():
    idx = pd.date_range("2026-11-01", periods=10, freq="1h", tz="UTC")
    m = pd.DataFrame({"kapanis": np.arange(10.0)}, index=idx)
    k = ik.kapanmis_mumlar(m, "1h", pd.Timestamp("2026-11-01 05:30", tz="UTC"))
    assert k.index[-1] == pd.Timestamp("2026-11-01 04:00", tz="UTC")                             # 05:00 mumu 06:00'da kapanır


def test_donem_basi_holdout_bas_ile_ayni():
    from motor.arastirma.v2 import sabit
    assert ik.DONEM_BAS == sabit.HOLDOUT_BAS == pd.Timestamp("2025-11-08", tz="UTC")
    assert "kullanıcı kararı 2026-11-14" in ik.GEREKCE


# ---------------------------------------------------------------- dönem kesimi (sentetik koşu)
def _gunluk(sembol_no: int) -> pd.DataFrame:
    idx = pd.date_range("2025-09-01", "2026-02-28", freq="D", tz="UTC")
    f = 100 + np.arange(len(idx)) * 0.1 + sembol_no
    return pd.DataFrame({"acilis": f, "yuksek": f + 1, "dusuk": f - 1, "kapanis": f, "hacim": 1.0, "quote_hacim": 1e5}, index=idx)


def _ham(giris_gunleri, r=0.5):
    g = pd.DatetimeIndex(pd.to_datetime(giris_gunleri, utc=True, format="ISO8601")).as_unit("ns")
    n = len(g)
    return pd.DataFrame({"ayar_no": np.zeros(n, dtype=np.int16), "giris_zamani": g, "cikis_zamani": g + pd.Timedelta(2, "D"),
                         "yon": np.ones(n, dtype=np.int8), "r": np.full(n, r, dtype=np.float32),
                         "sf": np.full(n, 0.05, dtype=np.float32), "stop_mesafe": np.full(n, 5.0, dtype=np.float32),
                         "fonlama_r": np.zeros(n, dtype=np.float32)})


def _satir():
    return next(s for s in ik.kayit_satirlari(dogrula=False) if s["kimlik"] == "HAM:X005:664#v1")


def _sahte_ham_fn(yon=1):
    def f(st, sembol, tf, carpan, tablo, veri_al):
        mumlar, _ = veri_al(sembol, tf)
        # 3 işlem dönem ÖNCESİ (ısınma), 4 işlem dönem içinde; yalnız sembol BTCUSDT işlem üretir
        if sembol != "BTCUSDT":
            return _ham([]), None, mumlar
        h = _ham(["2025-10-01", "2025-10-10", "2025-11-07 23:00", "2025-11-08", "2025-11-20", "2025-12-05", "2026-01-10"])
        h["yon"] = np.int8(yon)
        h["r"] = np.float32(0.5 if carpan == 1.0 else 0.4)
        return h, None, mumlar
    return f


def _veri(sembol, tf):
    return _gunluk(abs(hash(sembol)) % 7), None


def test_donem_kes_giris_zamanina_gore():
    h = _ham(["2025-11-07 23:59", "2025-11-08 00:00", "2025-11-09"])
    assert len(ik.donem_kes(h)) == 2


def test_kayit_kos_yalniz_donem_ici_islem_sayar():
    r = ik.kayit_kos(_satir(), kk.TABLO, _veri, _sahte_ham_fn())
    assert r["n_islem"] == 4                                   # dönem öncesi 3 işlem ölçüme girmedi
    assert r["long_only"] is True
    assert r["yetersiz_ornek"] is True                         # <20 işlem
    assert r["net_x2"] is not None and r["net_x2"] < r["net_x1"]
    assert r["kill_x2"] == 0
    assert r["donem_bas"].startswith("2025-11-08")
    assert not math.isnan(r["bh_net_x2"])
    assert r["karar"] in ("gecti", "al_tutu_gecemedi", "paper_cikar")


def test_long_degilse_al_tut_hesaplanmaz():
    r = ik.kayit_kos(_satir(), kk.TABLO, _veri, _sahte_ham_fn(yon=-1))
    assert r["long_only"] is False and r["c_al_tutu_gecti"] is None and math.isnan(r["bh_net_x2"])


def test_donem_oncesi_islem_varsa_sonuc_bos():
    def f(st, sembol, tf, carpan, tablo, veri_al):
        mumlar, _ = veri_al(sembol, tf)
        return (_ham(["2025-10-01", "2025-10-20"]) if sembol == "BTCUSDT" else _ham([])), None, mumlar
    r = ik.kayit_kos(_satir(), kk.TABLO, _veri, f)
    assert r["n_islem"] == 0 and r["karar"] == "paper_cikar" and r["long_only"] is False


# ---------------------------------------------------------------- tek koşu koruması
def test_tek_kosu_koruma(tmp_path):
    cikti = tmp_path / "ileri_sinav"
    sat = [_satir()]
    s1 = ik.kos(sat, cikti, kk.TABLO, _veri, _sahte_ham_fn())
    assert len(s1) == 1
    for ad in ("sonuc.csv", "rapor.md", ik.ISARET):
        assert (cikti / ad).exists()
    assert any(p.suffix == ".json" for p in cikti.iterdir())
    with pytest.raises(ik.TekKosuHatasi):
        ik.kos(sat, cikti, kk.TABLO, _veri, _sahte_ham_fn())                                    # ikinci koşu reddedilir
    with pytest.raises(SystemExit):                                                               # --zorla bayrağı tanımlı değil
        ik.main(["--zorla"])


def test_isaret_tek_basina_yeniden_kosuyu_engeller(tmp_path):
    (tmp_path / ik.ISARET).write_text("x")
    with pytest.raises(ik.TekKosuHatasi):
        ik.tek_kosu_kontrol(tmp_path)
    ik.tek_kosu_kontrol(tmp_path / "yok")                                                         # dizin yoksa serbest


def test_hata_kaydi_yazilir_ve_koşu_devam_eder(tmp_path):
    def kotu(*a, **k):
        raise RuntimeError("sentetik hata")
    s = ik.kos([_satir()], tmp_path / "o", kk.TABLO, _veri, kotu)
    assert s[0]["karar"] == "HATA" and "sentetik hata" in s[0]["hata"]
    df = pd.read_csv(tmp_path / "o" / "sonuc.csv")
    assert df.loc[0, "karar"] == "HATA"


def test_sonuc_csv_sutunlari_ve_rapor(tmp_path):
    ik.kos([_satir()], tmp_path / "o", kk.TABLO, _veri, _sahte_ham_fn())
    df = pd.read_csv(tmp_path / "o" / "sonuc.csv")
    assert list(df.columns) == ik.SUTUNLAR
    rapor = (tmp_path / "o" / "rapor.md").read_text(encoding="utf-8")
    assert "yetersiz_ornek" in rapor and "HAM:X005:664#v1" in rapor


# ---------------------------------------------------------------- kayıt seçimi / kuru
def test_alti_kayit_cozulur():
    s = ik.kayit_satirlari()
    assert [x["kimlik"] for x in s] == [k for k, _ in ik.KAYITLAR] and len(s) == 6
    assert {x["tf"] for x in s} == {"1d", "4h", "5m"}


@pytest.mark.skipif(not ik.depo.mum_yolu("BTCUSDT", "5m").exists(),
                    reason="yerel 5m mum verisi yok (veri/mumlar repoda değil; CI'da kuru mod veri dosyası denetimi yapılamaz)")
def test_kuru_holdout_okumaz(monkeypatch, capsys):
    def yasak(*a, **k):
        raise AssertionError("kuru modda veri okunmamalı")
    monkeypatch.setattr(ik, "tf_mumlari", yasak)
    monkeypatch.setattr(ik.depo, "funding_oku", yasak)
    monkeypatch.setattr(ik.depo, "mum_oku", yasak)
    assert ik.main(["--kuru", "--cikti", "/nonexistent_xyz/ileri"]) == 0
    assert "[kuru] 6 kayıt" in capsys.readouterr().out
