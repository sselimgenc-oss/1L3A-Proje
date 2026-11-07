"""Durum sözleşmesi (motor/canli/durum.py), final set tanımı ve backtest besleyici testleri."""
import json
import os
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from motor.canli import durum as d

KOK = Path(__file__).resolve().parents[1]
KILIT_VERI = (KOK / "sonuclar" / "kilit" / "islemler" / "swing__cci-esik--SOLUSDT--1d.parquet").exists() and \
    (KOK / "sonuclar" / "wf" / "islemler").exists()


def _q(deger=0.01):
    return {"deger": deger, "p05": -0.02, "p25": -0.005, "p50": 0.006, "p75": 0.02, "p95": 0.07, "bant": d.bant_bul(deger, -0.02, -0.005, 0.006, 0.02, 0.07), "alarm": None}


def _isl(zaman="2026-01-05T10:00:00Z", kimlik="a|BTCUSDT|1h"):
    return {"zaman": zaman, "kimlik": kimlik, "sembol": "BTCUSDT", "yon": "long", "giris_zamani": "2026-01-04T10:00:00Z",
            "giris_fiyati": "100.5", "cikis_zamani": zaman, "cikis_fiyati": "102.0", "miktar": "1.5", "r": 1.2,
            "net_pnl_yerel": "2.10", "set_katki_usd": "1.05", "cikis_nedeni": "sinyal"}


def ornek_durum(kaynak="paper", zaman="2026-01-05T12:00:00Z", bayat=False, dosya_esik_dk=30):
    """Sentetik ama şemaya uygun durum içeriği (motor yerine)."""
    risk = d.risk_blogu(gunluk_kayip=0.004, gunluk_limit=0.03, kaldirac=1.2, kaldirac_limit=3.0, zirveden_dusus=0.02, kill_limit=0.2,
                        acik_stop_riski=0.01, stop_risk_limit=0.05)
    ozet = d.ozet_olustur(kaynak=kaynak, zaman=zaman, yazim_zamani=zaman, donem=None, baslangic_ozsermaye="10000", ozsermaye="10250.55",
                          gun_pnl="-12.34", gun_getiri=-0.0012, zirve_ozsermaye="10460", max_dusus=0.031, risk=risk,
                          sayaclar={"acik_pozisyon": 1, "kapanan_islem": 2})
    strat = {**d._zarf("stratejiler", kaynak, zaman), "beklenti_penceresi_hafta": [4, 8],
             "stratejiler": [{"kimlik": "a|BTCUSDT|1h", "ajan": "swing", "kol": "tek_grafik", "ozsermaye_katkisi": "250.55", "katki_getiri": 0.025055,
                              "acik_pozisyonlar": [{"sembol": "BTCUSDT", "yon": "long"}], "son_islem": _isl(), "islem_sayisi": 2,
                              "kazanma_orani": 0.5, "beklenti": {"4": {"net_getiri": _q(0.013), "max_dusus": _q(0.02)},
                                                                  "8": {"net_getiri": _q(-0.03), "max_dusus": _q(0.02)}}}],
             "set": {"beklenti": {"8": {"net_getiri": _q(0.0123), "max_dusus": _q(0.02)}}}}
    strat["stratejiler"][0]["beklenti"]["8"]["net_getiri"]["alarm"] = True
    saglik = {**d._zarf("saglik", kaynak, zaman), "son_calisma": zaman, "durum": "ok", "bayat_denetimi": True, "dosya_esik_dk": dosya_esik_dk,
              "veri": [{"sembol": "BTCUSDT", "tf": "1h", "son_mum_zamani": "2026-01-05T11:00:00Z", "bayatlik_dk": 60, "esik_dk": 130, "bayat": bayat}],
              "servis": {"calisiyor": True, "surum": "t", "not": ""}, "uyarilar": []}
    gecmis = {**d._zarf("gecmis", kaynak, zaman), "noktalar": [{"gun": "2026-01-03", "ozsermaye": "10000.00"}, {"gun": "2026-01-04", "ozsermaye": "10250.55"}]}
    return {"ozet": ozet, "stratejiler": strat, "islemler": [_isl(), _isl("2026-01-05T11:00:00Z")], "saglik": saglik, "gecmis": gecmis}


def yaz(dizin, **kw):
    p = ornek_durum(**kw)
    d.yaz_hepsi(dizin, **p)
    return p


# ---------------------------------------------------------------- biçim
def test_para_ve_numpy():
    import numpy as np
    assert d.para(10721.4005811691) == "10721.40"
    assert d.para(Decimal("1.005")) == "1.00"          # yarım-çifte
    assert d.para(np.float64(2.5)) == "2.50"
    assert d.sayi(float("nan")) is None


def test_bant_ve_alarm():
    assert d.bant_bul(-0.03, -0.02, -0.005, 0.006, 0.02, 0.07) == "p05_alti"
    assert d.bant_bul(0.1, -0.02, -0.005, 0.006, 0.02, 0.07) == "p95_ustu"
    q = {"p05": -0.02, "p25": -0.005, "p50": 0.006, "p75": 0.02, "p95": 0.07, "alarm_yonu": "alt", "alarm_esigi": -0.02}
    assert d.konum("net_getiri", -0.03, q, 8)["alarm"] is True
    assert d.konum("net_getiri", -0.03, q, 4)["alarm"] is None
    qd = {**q, "alarm_yonu": "ust", "alarm_esigi": 0.04}
    assert d.konum("max_dusus", 0.05, qd, 8)["alarm"] is True and d.konum("max_dusus", 0.03, qd, 8)["alarm"] is False


def test_zaman_saat_dilimsiz_reddedilir():
    with pytest.raises(ValueError):
        d.zaman_str(pd.Timestamp("2026-01-01"))


# ---------------------------------------------------------------- atomik yazma
def test_atomik_yazma_gecici_kalmaz(tmp_path):
    d.atomik_yaz_json(tmp_path / "a.json", {"x": 1})
    assert json.loads((tmp_path / "a.json").read_text()) == {"x": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]


def test_atomik_yazma_hata_eski_dosyayi_korur(tmp_path, monkeypatch):
    yol = tmp_path / "a.json"
    d.atomik_yaz_json(yol, {"x": 1})

    def boz(*a, **k):
        raise OSError("disk dolu")
    monkeypatch.setattr(os, "replace", boz)
    with pytest.raises(OSError):
        d.atomik_yaz_json(yol, {"x": 2})
    monkeypatch.undo()
    assert json.loads(yol.read_text()) == {"x": 1}              # yarım/yeni içerik yok
    assert [p.name for p in tmp_path.iterdir()] == ["a.json"]   # geçici temizlendi


def test_json_nan_reddedilir(tmp_path):
    with pytest.raises(ValueError):
        d.atomik_yaz_json(tmp_path / "a.json", {"x": float("nan")})
    assert not list(tmp_path.iterdir())


def test_yaz_oku_gidis_donus(tmp_path):
    p = yaz(tmp_path)
    veri, sorun = d.oku_hepsi(tmp_path)
    assert sorun == []
    assert veri["ozet"] == p["ozet"] and veri["stratejiler"] == p["stratejiler"] and veri["islemler"] == p["islemler"]
    assert veri["ozet"]["toplam_pnl"] == "250.55" and veri["ozet"]["ozsermaye"] == "10250.55"


def test_islem_ekle(tmp_path):
    yaz(tmp_path)
    d.islem_ekle(tmp_path, _isl("2026-01-06T10:00:00Z"))
    assert len(d.oku_islemler(tmp_path)) == 3
    with pytest.raises(d.DurumHatasi):
        d.islem_ekle(tmp_path, {"zaman": "x"})


# ---------------------------------------------------------------- okuma hataları
def test_eksik_dosya_acik_hata(tmp_path):
    veri, sorun = d.oku_hepsi(tmp_path)
    assert all(v is None for v in veri.values()) and len(sorun) == 5
    assert all("dosya yok" in s for s in sorun)
    with pytest.raises(d.DurumHatasi, match="dosya yok"):
        d.oku_ozet(tmp_path)


def test_bozuk_json_ve_sema(tmp_path):
    yaz(tmp_path)
    (tmp_path / "ozet.json").write_text("{bozuk", encoding="utf-8")
    with pytest.raises(d.DurumHatasi, match="bozuk JSON"):
        d.oku_ozet(tmp_path)
    o = ornek_durum()["ozet"]
    del o["ozsermaye"]
    (tmp_path / "ozet.json").write_text(json.dumps(o), encoding="utf-8")
    with pytest.raises(d.DurumHatasi, match="eksik alan"):
        d.oku_ozet(tmp_path)
    o = ornek_durum()["ozet"]
    o["surum"] = 99
    (tmp_path / "ozet.json").write_text(json.dumps(o), encoding="utf-8")
    with pytest.raises(d.DurumHatasi, match="sürüm"):
        d.oku_ozet(tmp_path)


def test_bozuk_jsonl_satiri_hata(tmp_path):
    yaz(tmp_path)
    with open(tmp_path / "islemler.jsonl", "a", encoding="utf-8") as f:
        f.write('{"zaman": "2026')
    with pytest.raises(d.DurumHatasi, match="islemler.jsonl:3"):
        d.oku_islemler(tmp_path)


def test_para_alani_metin_olmali():
    o = ornek_durum()["ozet"]
    o["ozsermaye"] = 10250.55
    with pytest.raises(d.DurumHatasi):
        d.dogrula_ozet(o)


def test_bayat_esigi():
    assert d.bayat_esigi_dk("1h") == 130 and d.bayat_esigi_dk("30m") == 70 and d.bayat_esigi_dk("1d") == 2890


# ---------------------------------------------------------------- final_set.json
def test_final_set_7_satir_ve_oneri_uyumu():
    from motor.arastirma import final_set
    s = final_set.yukle(KOK / "stratejiler" / "final_set.json")
    assert len(s["stratejiler"]) == 7
    o = pd.read_csv(KOK / "sonuclar" / "secim" / "oneri.csv")
    assert {x["kimlik"] for x in s["stratejiler"]} == set(o[o["rol"] == "secim"]["kimlik"])
    kollar = [x["kol"] for x in s["stratejiler"]]
    assert kollar.count("tek_grafik") == 4 and kollar.count("portfoy") == 3
    assert [x["ajan"] for x in s["stratejiler"]].count("swing") == 3
    assert s["risk"]["kol_paylari"] == {"tek_grafik": 0.5, "portfoy": 0.5}
    assert s["risk"]["tek_grafik"]["islem_basi_risk"] == 0.01 and s["risk"]["tek_grafik"]["kill_switch"] == 0.2


def test_final_set_bozulursa_hata():
    from motor.arastirma import final_set
    s = final_set.yukle(KOK / "stratejiler" / "final_set.json")
    s["stratejiler"].pop()
    with pytest.raises(ValueError, match="7 strateji"):
        final_set.dogrula(s)


def test_guncel_ayarlar_csv():
    df = pd.read_csv(KOK / "sonuclar" / "final" / "guncel_ayarlar.csv")
    assert len(df) == 7 and df["hata"].fillna("").eq("").all() and df["ayar"].notna().all()
    assert {"kimlik", "ayar", "egitim_bas", "egitim_bit", "egitim_skor", "egitim_islem", "sonraki_yenileme", "kilit_ayarindan_farkli"} <= set(df.columns)


# ---------------------------------------------------------------- backtest besleyici <-> set.csv
@pytest.mark.skipif(not KILIT_VERI, reason="sonuclar/kilit parquet dosyaları (gitignore) yok")
def test_backtest_durum_set_csv_ile_tutarli(tmp_path):
    from motor.canli import backtest_durum as bd
    p = bd.olustur(yazim_zamani=pd.Timestamp("2026-11-07", tz="UTC"))
    set_csv = pd.read_csv(KOK / "sonuclar" / "kilit" / "set.csv").set_index("kol")
    o = p["ozet"]
    assert o["toplam_getiri"] == pytest.approx(set_csv.loc["set_harman_50_50", "net"], abs=1e-6)
    assert o["max_dusus"] == pytest.approx(set_csv.loc["set_harman_50_50", "max_dusus"], abs=1e-9)
    assert o["ozsermaye"] == d.para(Decimal("10000") * Decimal(repr(1 + float(set_csv.loc["set_harman_50_50", "net"]))))
    # katkılar toplamı = toplam PnL (kuruş yuvarlaması payı)
    toplam = sum(Decimal(x["ozsermaye_katkisi"]) for x in p["stratejiler"]["stratejiler"])
    assert abs(toplam - Decimal(o["toplam_pnl"])) < Decimal("0.05")
    assert len(p["stratejiler"]["stratejiler"]) == 7
    d.yaz_hepsi(tmp_path, ozet=p["ozet"], stratejiler=p["stratejiler"], islemler=p["islemler"], saglik=p["saglik"], gecmis=p["gecmis"])
    assert d.oku_hepsi(tmp_path)[1] == []
    assert o["kaynak"] == "backtest" and o["sayaclar"]["kapanan_islem"] == len(p["islemler"])
