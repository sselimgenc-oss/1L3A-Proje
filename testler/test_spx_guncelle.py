"""spx_guncelle: artımlı başlangıç/bitis hesabı, birleştirme, hata yolları. Ağ YOK (indirici taklit edilir)."""
from datetime import date

import pandas as pd
import pytest

from motor.canli import spx_guncelle as sg
from motor.veri import depo
from motor.veri.indir import _yaz


def _df(bas, n, fiyat=100.0):
    ix = pd.date_range(bas, periods=n, freq="h", tz="UTC", name="zaman")
    return pd.DataFrame({"kapanis": [fiyat + i for i in range(n)]}, index=ix)


def _sahte(df, basarisiz=()):
    cagri = {}

    def indir(sembol, bas, bit, dizin=None, bugun=None, log=print):
        cagri.update(sembol=sembol, bas=bas, bit=bit, bugun=bugun)
        _yaz(df, depo.mum_yolu(sembol, "1h", dizin))
        return {"basarisiz": list(basarisiz)}
    return indir, cagri


def test_bitis_yarin_ve_baslangic_son_mum_ayindan_bir_ay_once():
    assert sg.bitis_hesapla(date(2026, 11, 8)) == "2026-11-09"
    assert sg.bitis_hesapla(date(2026, 12, 31)) == "2027-01-01"
    assert sg.baslangic_hesapla(pd.Timestamp("2026-11-03 10:00", tz="UTC"), None) == "2026-10"
    assert sg.baslangic_hesapla(pd.Timestamp("2026-01-15", tz="UTC"), None) == "2025-12"
    assert sg.baslangic_hesapla(None, "2024-01") == "2024-01"
    with pytest.raises(sg.GuncellemeHatasi):
        sg.baslangic_hesapla(None, None)


def test_artimli_birlestirme_eski_gecmis_korunur_ortusmede_yeni_kazanir(tmp_path):
    eski = _df("2026-09-01", 24 * 40, 100.0)                     # 09-01 .. 10-10
    _yaz(eski, depo.mum_yolu("DK_SPX", "1h", tmp_path))
    yeni = _df("2026-10-01", 24 * 40, 500.0)                     # 10-01 .. 11-10 (örtüşme)
    indir, c = _sahte(yeni)
    r = sg.guncelle(tmp_path, date(2026, 11, 9), indir=indir, log=lambda m: None)
    assert c["bas"] == "2026-09" and c["bit"] == "2026-11-10" and c["sembol"] == "DK_SPX"
    out = pd.read_parquet(depo.mum_yolu("DK_SPX", "1h", tmp_path))
    assert out.index.is_monotonic_increasing and not out.index.duplicated().any()
    assert out.index.min() == eski.index.min() and out.index.max() == yeni.index.max()
    assert out["kapanis"].iloc[0] == 100.0                        # eski kısım aynen
    assert out.loc[yeni.index[0], "kapanis"] == 500.0             # örtüşmede yeni
    assert r["eklenen"] == len(out) - len(eski) > 0


def test_ilk_kurulum_baslangic_ister_arsiv_yoksa(tmp_path):
    with pytest.raises(sg.GuncellemeHatasi, match="baslangic"):
        sg.guncelle(tmp_path, date(2026, 11, 9), indir=_sahte(_df("2026-11-01", 5))[0], log=lambda m: None)
    indir, c = _sahte(_df("2026-11-01", 24 * 8))
    sg.guncelle(tmp_path, date(2026, 11, 9), baslangic="2026-10", indir=indir, log=lambda m: None)
    assert c["bas"] == "2026-10" and depo.mum_yolu("DK_SPX", "1h", tmp_path).exists()


def test_basarisiz_ay_ve_bayat_sonuc_yuksek_sesle_hata_dosya_degismez(tmp_path):
    eski = _df("2026-10-01", 48)
    yol = depo.mum_yolu("DK_SPX", "1h", tmp_path)
    _yaz(eski, yol)
    with pytest.raises(sg.GuncellemeHatasi, match="indirilemeyen"):
        sg.guncelle(tmp_path, date(2026, 11, 9), indir=_sahte(_df("2026-10-01", 100), basarisiz=["2026-11"])[0], log=lambda m: None)
    with pytest.raises(sg.GuncellemeHatasi, match="bayat"):
        sg.guncelle(tmp_path, date(2026, 11, 9), indir=_sahte(_df("2026-10-01", 60))[0], log=lambda m: None)
    pd.testing.assert_frame_equal(pd.read_parquet(yol), eski, check_freq=False)
    with pytest.raises(sg.GuncellemeHatasi, match="boş"):
        sg.birlestir(eski, eski.iloc[0:0])


def test_arastirma_dizini_reddedilir_ve_cli_kodu(tmp_path, capsys):
    with pytest.raises(sg.GuncellemeHatasi, match="kilit"):
        sg.guncelle(depo.MUM_DIZINI, date(2026, 11, 9), indir=_sahte(_df("2026-11-01", 5))[0], log=lambda m: None)
    assert sg.main(["--veri", str(tmp_path)]) == 1                 # arşiv yok + --baslangic yok: ağa çıkmadan hata
    assert "HATA" in capsys.readouterr().err
