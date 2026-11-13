"""Kapanış aşama 1 koşucusu ve koşu listesi: sentetik veriyle uçtan uca küçük koşu (GERÇEK MUM VERİSİ KULLANILMAZ).

2 sahte strateji x 3 sahte sembol: kapı hesapları, kontrol noktası/yeniden başlatma, BH sıralaması, HATA yolu, liste dondurma SHA kararlılığı.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from araclar import kapanis_kosu as kk
from araclar import kapanis_kosu_listesi as kl
from motor.arastirma.v2.ham import HoldoutSizintisi
from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji

SEMBOLLER = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


class SahteA(Strateji):
    """Her 6. mumda long, 2 mum sonra sinyalle çık; stop 3 ATR."""
    ad, stil = "test__sahte-a", "swing"
    varsayilan_parametreler = {"aralik": 6}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, mumlar):
        i = np.arange(len(mumlar))
        a = self.parametreler["aralik"]
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], 14)
        kap = mumlar["kapanis"]
        return cerceve(mumlar, pd.Series(i % a == 0, index=mumlar.index), False, kap - 3 * atr, kap + 3 * atr,
                       cikis=pd.Series(i % a == 2, index=mumlar.index))


class SahteB(Strateji):
    """Long ve short: ters yönde de girer (iki yönlü); SahteA'dan farklı ritim."""
    ad, stil = "test__sahte-b", "swing"
    varsayilan_parametreler = {"aralik": 9}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, mumlar):
        i = np.arange(len(mumlar))
        a = self.parametreler["aralik"]
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], 14)
        kap = mumlar["kapanis"]
        return cerceve(mumlar, pd.Series(i % a == 0, index=mumlar.index), pd.Series(i % a == 4, index=mumlar.index),
                       kap - 3 * atr, kap + 3 * atr, cikis=pd.Series(i % a == 2, index=mumlar.index))


class SahteFaz(Strateji):
    """Desteklenmeyen çıkış alanı (stop_sonrasi_bekleme_mum) -> kapı 6 HATA, p=1."""
    ad, stil = "test__sahte-bekleme", "swing"
    varsayilan_parametreler = {}
    cikis_ayarlari = CikisAyarlari(stop_sonrasi_bekleme_mum=3)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, mumlar):
        i = np.arange(len(mumlar))
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], 14)
        kap = mumlar["kapanis"]
        return cerceve(mumlar, pd.Series(i % 7 == 0, index=mumlar.index), False, kap - 3 * atr, kap + 3 * atr,
                       cikis=pd.Series(i % 7 == 2, index=mumlar.index))


@pytest.fixture(autouse=True)
def sahte_siniflar(monkeypatch):
    h = kl.sinif_haritasi()
    monkeypatch.setitem(h["tek"], SahteA.ad, SahteA)
    monkeypatch.setitem(h["tek"], SahteB.ad, SahteB)
    monkeypatch.setitem(h["tek"], SahteFaz.ad, SahteFaz)
    monkeypatch.setattr(kk, "_CTX", None)


def _mumlar(tohum: int, n: int = 500, bas: str = "2022-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    fiyat = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, n)))
    idx = pd.date_range(bas, periods=n, freq="1D", tz="UTC")
    acilis = np.r_[fiyat[0], fiyat[:-1]]
    return pd.DataFrame({"acilis": acilis, "yuksek": np.maximum(acilis, fiyat) * 1.01, "dusuk": np.minimum(acilis, fiyat) * 0.99,
                         "kapanis": fiyat, "hacim": np.full(n, 1000.0), "quote_hacim": np.full(n, 1e5)}, index=idx)


def _veri_al(sembol: str, tf: str):
    if sembol == "YOKUSDT":
        raise FileNotFoundError(f"Veri yok: {sembol}")
    # SOL daha geç başlar: analiz başlangıcı (>=%75 kapsama) SOL'un başlangıcı; al-tut tabanı bir önceki gün (BTC+ETH sepeti)
    return _mumlar({"BTCUSDT": 1, "ETHUSDT": 2, "SOLUSDT": 3}.get(sembol, 4), 500,
                   "2022-02-15" if sembol == "SOLUSDT" else "2022-01-01"), None


def _satir(kimlik, sinif, evren=",".join(SEMBOLLER), tf="1d", yon="", durum="KOSULACAK", par="{}"):
    s = {k: "" for k in kl.SUTUNLAR}
    s.update(kimlik=kimlik, katman="G8", kaynak_id=kimlik, sinif=sinif, parametreler=par, tf=tf, yon=yon, evren=evren, durum=durum,
             notlar="sahte")
    return s


def _baglam(tmp_path, **ek):
    esik = {**kk.ESIK, "min_islem": 5, "b": 300, **ek.pop("esik", {})}
    return kk.baglam_kur(veri_al=_veri_al, veri_al_40=_veri_al, sembol_40=("BTCUSDT", "ETHUSDT"), kurallar_40={}, tablo_40=kk.TABLO,
                         cikti=tmp_path / "kosu", esik=esik, **ek)


# ---------------------------------------------------------------- kapı hesapları (saf)
def test_kapi_hesaplari_saf() -> None:
    esik = kk.ESIK
    iyi = {"net_getiri": 0.2, "profit_factor": 1.5, "islem_sayisi": 250, "r_enstruman": {"A": 5.0, "B": 3.0}, "r_yil": {2021: 4.0, 2022: 2.0},
           "kill_olayi": 0}
    k = kk.kapilar_tek(iyi, 1.0, 0.5, True, esik)
    assert all(k[x] for x in ("k1", "k2", "k3", "k4", "k5"))
    assert not kk.kapilar_tek({**iyi, "profit_factor": 1.1}, 1.0, 0.5, True, esik)["k1"]
    assert not kk.kapilar_tek({**iyi, "net_getiri": -0.01}, 1.0, 0.5, True, esik)["k1"]
    assert not kk.kapilar_tek({**iyi, "islem_sayisi": 199}, 1.0, 0.5, True, esik)["k2"]
    # tek sembol / tek yıl: en iyi çıkarılınca kalan 0 -> geçmez
    assert not kk.kapilar_tek({**iyi, "r_enstruman": {"A": 5.0}}, 1.0, 0.5, True, esik)["k3"]
    kz = kk.kapilar_tek({**iyi, "r_yil": {2021: 4.0, 2022: -1.0}}, 1.0, 0.5, True, esik)
    assert kz["k3a"] and not kz["k3b"] and not kz["k3"]
    assert not kk.kapilar_tek({**iyi, "kill_olayi": 1}, 1.0, 0.5, True, esik)["k4"]
    assert not kk.kapilar_tek({**iyi, "kill_olayi": None}, 1.0, 0.5, True, esik)["k4"]        # ölçülemeyen geçmez
    assert not kk.kapilar_tek(iyi, 0.4, 0.5, True, esik)["k5"]                                 # al-tut Sharpe'ı aşamadı
    assert not kk.kapilar_tek(iyi, float("nan"), 0.5, True, esik)["k5"]
    assert kk.kapilar_tek(iyi, 0.1, 0.5, False, esik)["k5"]                                    # long-only değil: uygulanmaz
    pf = {"net_x2": 0.1, "sharpe_x2": 0.6, "gun": 1200, "dengeleme": 30, "net_en_iyi_yil_haric_x2": 0.01, "kill_x2": 0}
    assert all(kk.kapilar_portfoy(pf, 0.2, True, esik)[x] for x in ("k1", "k2", "k3", "k4", "k5"))
    assert not kk.kapilar_portfoy({**pf, "gun": 1000}, 0.2, False, esik)["k2"]
    assert not kk.kapilar_portfoy({**pf, "sharpe_x2": 0.4}, 0.2, False, esik)["k1"]


# ---------------------------------------------------------------- uçtan uca küçük koşu
def test_uctan_uca_kontrol_noktasi_ve_hata(tmp_path) -> None:
    b = _baglam(tmp_path)
    satirlar = [_satir("T:A", SahteA.ad, yon="long"), _satir("T:B", SahteB.ad),
                _satir("T:VERI-YOK", SahteA.ad, evren="BTCUSDT,YOKUSDT"),
                _satir("T:COZULEMEDI", "yok-sinif", durum="COZULEMEDI"),
                _satir("T:BEKLEME", SahteFaz.ad)]
    s1 = kk.kos(satirlar, isci=1, b=b)
    assert s1["kosulan"] == 5 and s1["atlanan"] == 0
    j = {s["kimlik"]: json.loads(kk.json_yolu(s["kimlik"], b.cikti).read_text()) for s in satirlar}
    a = j["T:A"]
    assert a["durum"] == "TAMAM" and a["tur"] == "tek" and a["n_islem_x2"] > 5
    assert 0 < a["p"] <= 1 and a["k6"]["B"] == 300 and a["k6"]["tohum"] == 20261113 + __import__("zlib").crc32(b"T:A")
    assert a["net_x1"] > a["net_x2"] or a["pf_x1"] >= a["pf_x2"]          # x2 maliyet daha pahalı
    assert a["long_only"] is True and a["bh_sharpe_x2"] is not None
    assert all(isinstance(a[x], bool) for x in ("k1", "k2", "k3", "k4", "k5"))
    bj = j["T:B"]
    assert bj["durum"] == "TAMAM" and bj["long_only"] is False and bj["k5"] is True      # iki yönlü: kıyas uygulanmaz
    # HATA yolu: diğerleri sürdü, mesaj sembolü içeriyor
    h = j["T:VERI-YOK"]
    assert h["durum"] == "HATA" and "YOKUSDT" in h["hata"] and h["p"] == 1.0
    assert j["T:COZULEMEDI"]["durum"] == "COZULEMEDI" and j["T:COZULEMEDI"]["p"] == 1.0
    # desteklenmeyen çıkış: kapı 6 HATA, p=1
    w = j["T:BEKLEME"]
    assert w["durum"] == "HATA" and "desteklenmeyen" in w["hata"] and w["p"] == 1.0 and w["k6"]["desteklenmeyen"] == ["stop_sonrasi_bekleme_mum"]
    # yeniden başlatma: bitenler atlanır, dosyalar değişmez
    onceki = {p.name: p.read_bytes() for p in b.cikti.glob("*.json")}
    s2 = kk.kos(satirlar, isci=1, b=b)
    assert s2["kosulan"] == 0 and s2["atlanan"] == 5
    assert {p.name: p.read_bytes() for p in b.cikti.glob("*.json")} == onceki
    # --sinir: ilk K kimlik
    (b.cikti / kk.json_yolu("T:B", b.cikti).name).unlink()
    s3 = kk.kos(satirlar, isci=1, sinir=2, b=b)
    assert s3["hedef"] == 2 and s3["kosulan"] == 1


def test_cok_isci_havuzu(tmp_path) -> None:
    b = _baglam(tmp_path)
    satirlar = [_satir("T:A", SahteA.ad), _satir("T:B", SahteB.ad), _satir("T:C", SahteA.ad, par=json.dumps({"aralik": 8}))]
    sonuc = kk.kos(satirlar, isci=2, b=b)
    assert sonuc["kosulan"] == 3
    assert all(json.loads(kk.json_yolu(s["kimlik"], b.cikti).read_text())["durum"] == "TAMAM" for s in satirlar)


def test_ayni_tohum_ayni_p(tmp_path) -> None:
    b = _baglam(tmp_path)
    s = _satir("T:A", SahteA.ad)
    p1 = kk.kimlik_isle(s, b)["p"]
    p2 = kk.kimlik_isle(s, b)["p"]
    assert p1 == p2


def test_holdout_sizintisi_yutulmaz(tmp_path) -> None:
    def sizdiran(sembol, tf):
        m = _mumlar(1)
        m.index = pd.date_range("2025-11-08", periods=len(m), freq="1D", tz="UTC")
        return m, None
    b = _baglam(tmp_path)
    b.veri_al = sizdiran
    with pytest.raises(HoldoutSizintisi):
        kk.kimlik_isle(_satir("T:A", SahteA.ad), b)


def test_tf_cozumu() -> None:
    assert kk.tf_cozum("1d")[0] and kk.tf_cozum("3h")[0] and kk.tf_cozum("6h")[0] and kk.tf_cozum("8h")[0] and kk.tf_cozum("2h")[0]
    for kotu in ("1w", "1M", "7x", "1m", "90s"):
        ok, ac = kk.tf_cozum(kotu)
        assert not ok and ac.startswith("VERI_TF_YOK")


# ---------------------------------------------------------------- birleştirme: BH sıralaması ve ikinci kapı
def _json_yaz(b, kimlik, p, durum="TAMAM", kapilar=True):
    r = {"kimlik": kimlik, "durum": durum, "p": p, "tur": "tek", "k1": kapilar, "k2": kapilar, "k3": kapilar, "k4": kapilar, "k5": kapilar,
         "hata": ""}
    kk.atomik_yaz(kk.json_yolu(kimlik, b.cikti), r)


def test_bh_siralamasi_esit_p_kimlik_sirasi_ve_ikinci_kapi(tmp_path) -> None:
    b = _baglam(tmp_path)
    ids = ["T:D", "T:C", "T:B", "T:A", "T:HATA", "T:YOK"]
    satirlar = [_satir(i, SahteA.ad) for i in ids]
    for i, p in (("T:A", 0.03), ("T:B", 0.03), ("T:C", 0.001), ("T:D", 0.9)):
        _json_yaz(b, i, p)
    kk.atomik_yaz(kk.json_yolu("T:HATA", b.cikti), {"kimlik": "T:HATA", "durum": "HATA", "p": 0.0001, "hata": "x"})   # HATA: p=1 sayılır
    kk.atomik_yaz(kk.json_yolu("T:YOK", b.cikti), {"kimlik": "T:YOK", "durum": "COZULEMEDI", "p": 1.0, "hata": "y"})
    sonuc_csv, ozet = tmp_path / "sonuc.csv", tmp_path / "ozet.md"
    o = kk.birlestir(satirlar, b, sonuc_csv=sonuc_csv, ozet_md=ozet)
    assert o["aile"] == 6 and o["hata"] == 1 and o["cozulemedi"] == 1
    d = pd.read_csv(sonuc_csv).set_index("kimlik")
    # aile m=6, q=0.10: eşikler 0.10*k/6; sıra: C(0.001), A(0.03), B(0.03: eşit p -> kimlik sırası), sonra 0.9/HATA/YOK (p=1)
    assert d.loc["T:C", "bh_sira"] == 1 and d.loc["T:A", "bh_sira"] == 2 and d.loc["T:B", "bh_sira"] == 3
    assert d.loc["T:C", "bh_esik"] == pytest.approx(0.1 / 6) and d.loc["T:B", "bh_esik"] == pytest.approx(0.1 * 3 / 6)
    assert all(bool(d.loc[i, "kapi7_bh"]) for i in ("T:C", "T:A", "T:B"))                 # k*=3 (0.03 <= 0.05)
    assert not bool(d.loc["T:D", "kapi7_bh"]) and not bool(d.loc["T:HATA", "kapi7_bh"]) and not bool(d.loc["T:YOK", "kapi7_bh"])
    assert d.loc["T:HATA", "kapi6_p"] == 1.0


def test_bh_k_yildiz_en_buyuk_gecen_k(tmp_path) -> None:
    """BH: k* = en büyük k ki p_(k) <= q k / m; ondan küçük sıradakiler p eşiğini kaçırsa bile keşiftir."""
    b = _baglam(tmp_path)
    satirlar = [_satir(i, SahteA.ad) for i in ("T:1", "T:2", "T:3", "T:4")]
    for i, p in (("T:1", 0.04), ("T:2", 0.04), ("T:3", 0.04), ("T:4", 0.5)):
        _json_yaz(b, i, p)
    o = kk.birlestir(satirlar, b, sonuc_csv=tmp_path / "s.csv", ozet_md=tmp_path / "o.md")
    d = pd.read_csv(tmp_path / "s.csv").set_index("kimlik")
    # m=4: eşikler 0.025, 0.05, 0.075 ... 3. sıra 0.04 <= 0.075 geçer -> k*=3: üçü de keşif (1. sıra 0.04 > 0.025 olsa da)
    assert o["bh_k_yildiz"] == 3
    assert all(bool(d.loc[i, "kapi7_bh"]) for i in ("T:1", "T:2", "T:3")) and not bool(d.loc["T:4", "kapi7_bh"])
    # kapı 6 (p<=0.05) de geçti -> birinci kapı geçenlerde ikinci kapı hesaplandı (sentetik veriyle), eksik sembol yazılabilir
    assert bool(d.loc["T:1", "birinci_kapi"]) and d.loc["T:1", "ikinci_n"] > 0


def test_ikinci_kapi_eksik_sembol_gecmez(tmp_path) -> None:
    b = _baglam(tmp_path)
    b.sembol_40 = ("BTCUSDT", "YOKUSDT")
    ik = kk.ikinci_kapi_tek(_satir("T:A", SahteA.ad), b)
    assert ik["gecti"] is False and any("YOKUSDT" in e for e in ik["eksik"])
    b.sembol_40 = ("BTCUSDT", "ETHUSDT")
    ik2 = kk.ikinci_kapi_tek(_satir("T:A", SahteA.ad), b)
    assert ik2["eksik"] == [] and ik2["n"] > 0 and ik2["ort_r"] is not None
    assert ik2["gecti"] == (ik2["ort_r"] > 0)


def test_birlestir_eksik_json_hata(tmp_path) -> None:
    b = _baglam(tmp_path)
    satirlar = [_satir("T:A", SahteA.ad)]
    with pytest.raises(RuntimeError, match="bitmedi"):
        kk.birlestir(satirlar, b, sonuc_csv=tmp_path / "s.csv", ozet_md=tmp_path / "o.md")
    o = kk.birlestir(satirlar, b, eksik_izin=True, sonuc_csv=tmp_path / "s.csv", ozet_md=tmp_path / "o.md")
    assert o["eksik"] == 1 and o["birinci"] == 0


# ---------------------------------------------------------------- koşu listesi: dondurma ve SHA kararlılığı
def _liste_kopya(tmp_path: Path) -> Path:
    kok = tmp_path / "kapanis"
    for alt in ("eleme", "kod_girdi", "ara"):
        (kok / alt).mkdir(parents=True)
    for rel in ("eleme/eleme.csv", "kod_girdi/g8_mevcut_sinif.csv", "ara/k1_nihai.csv", "ara/k2_nihai.csv"):
        (kok / rel).write_bytes((kl.KAPANIS / rel).read_bytes())
    return kok


def test_liste_sha_kararli_ve_dondurma(tmp_path) -> None:
    kok = _liste_kopya(tmp_path)
    o1 = kl.dondur(kok)
    sha1 = (kok / "kosu_listesi_asama1.csv.sha256").read_text().split()[0]
    assert sha1 == o1["sha256"] == kl.dogrula(kok)
    o2 = kl.dondur(kok)                                    # aynı girdi: değişmez, hata yok
    assert o2["sha256"] == sha1
    satirlar = list(csv.DictReader(open(kok / "kosu_listesi_asama1.csv", encoding="utf-8")))
    assert len(satirlar) == o1["satir"] > 300
    assert len({s["kimlik"] for s in satirlar}) == len(satirlar)
    assert {s["durum"] for s in satirlar} <= {"KOSULACAK", "COZULEMEDI"}
    assert all(s["durum"] == "COZULEMEDI" for s in satirlar if "COZULEMEDI" in s["notlar"])
    # aynı hipotez birleştirmesi: K kimliği listede, G8 ikizi yok; eşleme sütunu dolu
    by = {s["kimlik"]: s for s in satirlar}
    for g8_id, k_id in kl.ESLEME.items():
        assert g8_id not in by or g8_id == k_id
    assert by["HAM:X005:5"]["eslesme"] == "HAM:X005:5#v1" and by["HAM:X005:83"]["eslesme"] == "HAM:X005:83#v1"
    assert by["HAM:X005:879"]["eslesme"] == "HAM:X005:879#v1" and by["HAM:X005:395#1"]["eslesme"] == "HAM:X005:395#1#v1"
    elenen = list(csv.DictReader(open(kok / "kosu_listesi_asama1_elenen.csv", encoding="utf-8")))
    assert elenen and all(e["durum"] in ("ELENDI_ON", "EVREN_DISI") for e in elenen)
    assert sum(e["durum"] == "EVREN_DISI" for e in elenen) == len(kl.LIDER_EVREN_DISI)
    assert not ({e["kimlik"] for e in elenen} & set(by))                 # elenen koşulmaz, ailede yok
    assert "HAM:X005:395#3" in {e["kimlik"] for e in elenen}             # ikizi ÇIKAR -> K satırı da elenir
    # dondurulmuş liste değiştirilirse: doğrulama ve üzerine yazma reddedilir
    (kok / "eleme" / "eleme.csv").write_text((kok / "eleme" / "eleme.csv").read_text(encoding="utf-8").replace("ÇIKAR", "KOŞ", 3), encoding="utf-8")
    with pytest.raises(RuntimeError, match="DONDURULMUŞ"):
        kl.dondur(kok)
    kl.dondur(kok, yeniden=True)                                          # bilinçli yeniden dondurma
    with open(kok / "kosu_listesi_asama1.csv", "a", encoding="utf-8") as f:
        f.write("x\n")
    with pytest.raises(RuntimeError, match="uyuşmuyor"):
        kl.dogrula(kok)


def test_kuru_mod_sahte_dizin(tmp_path) -> None:
    """Kuru mod: backtest/mum okuma yok; veri dosyası varlığı ve sınıf çözümü. Sahte mum dizininde 5m dosyası yok -> VERI_YOK."""
    satirlar = [_satir("T:A", SahteA.ad, evren="BTCUSDT"), _satir("T:3h", SahteA.ad, evren="BTCUSDT", tf="3h"),
                _satir("T:1w", SahteA.ad, evren="BTCUSDT", tf="1w"), _satir("T:X", "yok-sinif", durum="COZULEMEDI")]
    d = tmp_path / "mumlar"
    (d / "BTCUSDT").mkdir(parents=True)
    (d / "BTCUSDT" / "5m.parquet").write_bytes(b"x")
    r = {x["kimlik"]: x for x in kk.kuru(satirlar, mum_dizini=d)}
    assert r["T:A"]["durum"] == "TAMAM" and r["T:3h"]["durum"] == "TAMAM"
    assert r["T:1w"]["durum"] == "SORUNLU" and "VERI_TF_YOK" in r["T:1w"]["sorun"]
    assert r["T:X"]["durum"] == "COZULEMEDI"
    (d / "BTCUSDT" / "5m.parquet").unlink()
    assert "VERI_YOK" in {x["kimlik"]: x for x in kk.kuru(satirlar[:1], mum_dizini=d)}["T:A"]["sorun"]
