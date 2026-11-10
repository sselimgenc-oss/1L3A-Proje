"""B16b (denetim kapanışı, 2. tur): (1) kimlik damgasının kapsamı OTOMATİK (proje-içi import kapanışı); (2) test / saglamlik / kasa
devam önbellekleri girdi damgasıyla doğrulanır; bayat ham dosya yüzünden oluşan hata KALICI "hata" satırı olmaz.
Yalnız SENTETİK veri; gerçek veri/ klasörü sonuçları etkilemez (_gercek_veri_yok)."""
from __future__ import annotations

import json
import math
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import evren_maliyet
from motor.arastirma import wf_evren as we
from motor.arastirma import wf_evren_holdout as v1h
from motor.arastirma.v2 import eleme, ham, kapsam, kasa, maliyet, sabit
from motor.arastirma.v2 import saglamlik
from motor.arastirma.v2 import test as k2
from motor.strateji import kayit
from testler.test_v2_ham_eleme import _ham_yaz, _havuz_kur
from testler.test_v2_test_set_holdout import SentetikStub, _kapanis, _mtm_yaz, _satir

KOK = Path(__file__).resolve().parents[1]
EVREN = sabit.evren_listesi("kripto")
AD_GERCEK = "swing__bant-donus"                                  # kayıtlı strateji: gostergeler_b2 / _gosterge_d11j kapanışında


@pytest.fixture(autouse=True)
def _temiz(monkeypatch):
    ham.damga_onbellegini_sifirla()
    monkeypatch.delenv(ham.ESKI_ORTAM, raising=False)

    def yok(sembol, tf):
        raise FileNotFoundError(f"{sembol} {tf}: test ortamında gerçek veri yok")
    monkeypatch.setattr(we, "_veri", yok)
    yield
    ham.damga_onbellegini_sifirla()


@pytest.fixture()
def tablo(tmp_path):
    y = maliyet.tabloyu_hazirla(tmp_path)
    return y, evren_maliyet.tablo_hash(y)


def _dosya_degisti(monkeypatch, *adlar):
    """İçeriği değişmiş dosya simülasyonu: v1 özet fonksiyonu bu dosya adları için başka değer döndürür (hash girdisi yolu)."""
    gercek = v1h._sha
    monkeypatch.setattr(v1h, "_sha", lambda p: "DEGISTI" if Path(p).as_posix().endswith(tuple(adlar)) else gercek(p))
    ham.damga_onbellegini_sifirla()


def _motor_degisti(monkeypatch):
    gercek = ham.motor_hash_girdisi()
    monkeypatch.setattr(ham, "motor_hash_girdisi", lambda: {**gercek, "motor/degisti.py": "x"})
    ham.damga_onbellegini_sifirla()


# ================================================================== 1. kapsam: import kapanışı
def test_kapanis_gecisli_tembel_goreli_ve_sirali(tmp_path, monkeypatch):
    p = tmp_path / "pk"
    (p / "alt").mkdir(parents=True)
    (p / "__init__.py").write_text("")
    (p / "alt" / "__init__.py").write_text("")
    (p / "a.py").write_text("import json\nfrom pk import b\nimport pk.alt.c\n")
    (p / "b.py").write_text("from . import d\n")                                   # göreli, `from . import altmodül`
    (p / "d.py").write_text("def f():\n    from pk.alt.e import x\n    return x\n")  # fonksiyon içi tembel import
    (p / "alt" / "c.py").write_text("x = 1\n")
    (p / "alt" / "e.py").write_text("x = 2\n")
    (p / "alakasiz.py").write_text("x = 3\n")
    monkeypatch.setattr(we, "KOK", tmp_path)
    kapsam.onbellegi_sifirla()
    try:
        k = kapsam.kapanis(["pk/a.py"])
        assert k == sorted(k) == ["pk/__init__.py", "pk/a.py", "pk/alt/__init__.py", "pk/alt/c.py", "pk/alt/e.py", "pk/b.py", "pk/d.py"]
        with pytest.raises(FileNotFoundError):
            kapsam.kapanis(["pk/yok.py"])                                          # kök yoksa kapsam sessizce daralmaz
    finally:
        kapsam.onbellegi_sifirla()


PAYLASILAN = ("motor/strateji/gostergeler_b2.py", "motor/strateji/pivotlar.py", "motor/strateji/_gosterge_d11j.py",
              "motor/strateji/gostergeler_b1.py", "motor/strateji/swing/_ortak.py")


def _kapanislar():
    out = {}
    for ad in sorted(kayit.tum_stratejiler()):
        stil = ad.split("__")[0]
        out[ad] = (stil, set(kapsam.kapanis([y for y in v1h.strateji_dosyalari(ad, stil) if y.endswith(".py")])))
    return out


@pytest.mark.parametrize("dosya", PAYLASILAN)
def test_paylasilan_gosterge_degisince_yalniz_kullanan_stratejinin_damgasi_bozulur(dosya, monkeypatch):
    kap = _kapanislar()
    kullanan = [a for a, (_, k) in kap.items() if dosya in k]
    kullanmayan = [a for a, (_, k) in kap.items() if dosya not in k]
    assert kullanan, f"{dosya}: hiçbir stratejinin kapanışında yok (kapsam çalışmıyor)"
    a = kullanan[0]
    once = ham.kimlik_damgasi(a, kap[a][0])["strateji_hash"]
    onceki_motor = ham.kimlik_damgasi(a, kap[a][0])["motor_hash"]
    kul_degil = kullanmayan[0] if kullanmayan else None
    once_degil = ham.kimlik_damgasi(kul_degil, kap[kul_degil][0])["strateji_hash"] if kul_degil else None
    _dosya_degisti(monkeypatch, dosya)
    sonra = ham.kimlik_damgasi(a, kap[a][0])
    assert sonra["strateji_hash"] != once, f"{dosya} değişti ama {a} strateji_hash'i değişmedi"
    assert sonra["motor_hash"] in (onceki_motor, sonra["motor_hash"])               # motor_hash'in değişmesi serbest (motor kapanışında olabilir)
    if kul_degil:
        assert ham.kimlik_damgasi(kul_degil, kap[kul_degil][0])["strateji_hash"] == once_degil


def test_paylasilan_gosterge_degisince_ham_cikti_bayat(tablo, tmp_path, monkeypatch):
    """Uçtan uca: gostergeler_b2.py içeriği değişti -> o göstergeyi kullanan stratejinin eski ham çıktısı okunmaz, görev yeniden koşar."""
    from testler.test_b16_damga_kapsam import sentetik
    y, h = tablo
    veri = sentetik()
    kos = lambda: ham.ham_gorev(AD_GERCEK, "1d", "DK_XAU", 1.0, tmp_path, y, h, _veri=lambda s, t: (veri, None))      # noqa: E731
    assert kos()["n_islem"] > 0
    al = lambda s, t: (veri, None)                                                                                    # noqa: E731
    assert "DK_XAU" in ham.ham_yukle(tmp_path, 1.0, AD_GERCEK, "1d", ("DK_XAU",), h, veri_al=al)[0]
    assert kos() == {"atlandi": True}
    _dosya_degisti(monkeypatch, "motor/strateji/gostergeler_b2.py")
    with pytest.raises(ham.DamgaUyusmazligi, match="strateji_hash|motor_hash"):
        ham.ham_yukle(tmp_path, 1.0, AD_GERCEK, "1d", ("DK_XAU",), h, veri_al=al)
    assert kos() != {"atlandi": True}                                                                                 # yeniden koşar


def test_portfoy_motoru_pf_damgasinda(monkeypatch):
    once = ham.kimlik_damgasi("pf__sentetik", "portfoy")
    assert "motor/portfoy/motor.py" in ham.motor_hash_girdisi_pf()
    _dosya_degisti(monkeypatch, "motor/portfoy/motor.py")
    sonra = ham.kimlik_damgasi("pf__sentetik", "portfoy")
    assert sonra["motor_hash"] != once["motor_hash"]                                # pf__ satırının motor_hash'i portföy motorunu kapsar


def test_motor_kapanisi_tek_grafik_motoru_ve_yardimcilari_kapsar():
    g = ham.motor_hash_girdisi()
    for y in ("motor/backtest/motor.py", "motor/strateji/htf.py", "motor/strateji/funding.py", "motor/veri/depo.py"):
        assert g[y], y
    assert set(ham.MOTOR_EK_MODULLER) <= set(g)                                      # taban hâlâ içeride
    assert list(g) == list(g)                                                       # deterministik sıra (sözlük ekleme sırası sabit)
    assert ham._sha_json(g) == ham._sha_json(ham.motor_hash_girdisi())


def test_v1_ortak_moduller_dokunulmamis():
    """v1 mühür kontrolleri ORTAK_MODULLER'e bağlı: liste ve v1 strateji_hashleri biçimi aynı."""
    assert len(v1h.ORTAK_MODULLER) == 14 and "motor/risk/limitler.py" in v1h.ORTAK_MODULLER
    assert set(v1h.strateji_hashleri([{"strateji": AD_GERCEK, "stil": "swing"}])[AD_GERCEK]) == set(
        v1h.strateji_dosyalari(AD_GERCEK, "swing"))                                  # v1 çıktısına kapanış anahtarı sızmadı


# ================================================================== 2. önbellekler: girdi damgası
def _gelistirme(tablo, tmp_path, monkeypatch, adlar=("iyi1",)):
    y, h = tablo
    for ad in adlar:
        for c in (1.0, 2.0):
            _ham_yaz(tmp_path, h, ad, "1d", EVREN, c, tohum=5, kar=0.9)
        _mtm_yaz(tmp_path, ad, "1d", EVREN, 1.0)
    hv, mh = _havuz_kur(tmp_path, [_satir(a, "trend", chr(97 + i), i + 1) for i, a in enumerate(adlar)])
    eleme.eleme_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)
    monkeypatch.setattr(k2, "tek_satir_baglam", SentetikStub())
    return y, h, hv, mh


def _satir_dosyasi(tmp_path, ad="iyi1"):
    return json.loads(k2.satir_yolu(tmp_path, ad, "1d").read_text())


def _yeniden_uret(tmp_path, h, ad="iyi1"):
    for c in (1.0, 2.0):
        _ham_yaz(tmp_path, h, ad, "1d", EVREN, c, tohum=5, kar=0.9)
    _mtm_yaz(tmp_path, ad, "1d", EVREN, 1.0)


def test_test_onbellegi_damga_uyusmazliginda_yeniden_kosar(tablo, tmp_path, monkeypatch):
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch)
    cagri = []
    gercek_sim = k2.k2_simule
    monkeypatch.setattr(k2, "k2_simule", lambda *a, **k: (cagri.append(1), gercek_sim(*a, **k))[1])
    k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    n1 = len(cagri)
    d1 = _satir_dosyasi(tmp_path)["girdi_damgasi"]
    assert n1 > 0 and d1
    k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    assert len(cagri) == n1                                                         # girdi aynı: önbellek isabeti (davranış korunur)
    # kod değişti (hash girdisi): önbellekteki eski p artık "bitti" sayılmaz; ham de bayat -> görev ertelenir, eski p ile rapor YAZILMAZ
    (tmp_path / "test.csv").unlink()
    (tmp_path / "test_ozet.json").unlink()
    _motor_degisti(monkeypatch)
    o = k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    assert o.get("bekleyen") == 1 and "motor_hash" in o["neden"] and not (tmp_path / "test.csv").exists()
    assert _satir_dosyasi(tmp_path)["durum"] == "tamam"                             # kalıcı hata satırı yazılmadı
    _yeniden_uret(tmp_path, h)                                                      # ham yeni kodla yeniden üretildi
    o = k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    assert "bekleyen" not in o and len(cagri) > n1                                  # yeni girdiyle gerçekten yeniden koştu
    assert _satir_dosyasi(tmp_path)["girdi_damgasi"] != d1 and (tmp_path / "test.csv").exists()


def test_test_onbellegi_ham_yeniden_uretilince_yeniden_kosar(tablo, tmp_path, monkeypatch):
    """Ham yan dosyanın damgası değişti (çıktı aynı kodla ama başka veri özetiyle yeniden üretildi) -> eski p yeniden hesaplanır."""
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch)
    k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    d1 = _satir_dosyasi(tmp_path)["girdi_damgasi"]
    yan = ham.dosya_yolu(tmp_path / "ham" / "x1", "iyi1", "1d", EVREN[0]).with_suffix(".json")
    m = json.loads(yan.read_text())
    yan.write_text(json.dumps(dict(m, veri_sha256="a" * 64)))
    assert not kasa.satir_bitti_mi(tmp_path, k2.satir_yolu(tmp_path, "iyi1", "1d"), _satir("iyi1") | {"evren": "kripto"}, (1.0,),
                                   "motor/arastirma/v2/test.py", kasa.SATIR_BITTI)
    assert d1 != kasa.girdi_damgasi(tmp_path, _satir("iyi1"), (1.0,), "motor/arastirma/v2/test.py")


def test_bayat_ham_hatasi_kalici_hata_satiri_olmaz_ve_yenilenince_yeniden_denenir(tablo, tmp_path, monkeypatch):
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch, adlar=("iyi2",))
    satir = _satir("iyi2")
    _motor_degisti(monkeypatch)                                                     # ham bayat
    r = k2.satir_test(satir, tmp_path, y, h, None)
    assert r.get("ertelendi") and r.get("damga") and "motor_hash" in r["neden"]
    assert not k2.satir_yolu(tmp_path, "iyi2", "1d").exists()                       # "durum=hata" KALICI yazılmadı
    _yeniden_uret(tmp_path, h, "iyi2")                                              # ham yeniden üretildi
    s = k2.satir_test(satir, tmp_path, y, h, None)
    assert s["durum"] == "tamam" and not s["hata"]


def test_damgali_hata_satiri_girdi_degisince_yeniden_denenir(tablo, tmp_path, monkeypatch):
    """Başka nedenle oluşmuş (damgalı) hata satırı: ham yenilenince (yan damga değişince) yeniden denenir; girdi aynıyken kalıcıdır."""
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch, adlar=("iyi2",))
    yan = ham.dosya_yolu(tmp_path / "ham" / "x1", "iyi2", "1d", EVREN[0]).with_suffix(".json")
    m = json.loads(yan.read_text())
    yan.write_text(json.dumps(dict(m, hata="boom")))                                # ham koşusu bu sembolde hata vermiş
    satir = _satir("iyi2")
    s = k2.satir_test(satir, tmp_path, y, h, None)
    assert s["durum"] == "hata" and "hatalı sembol" in s["hata"] and s["girdi_damgasi"]
    assert k2.satir_test(satir, tmp_path, y, h, None)["durum"] == "hata"            # girdi aynı: sonuç kalıcı (eski davranış)
    yan.write_text(json.dumps(m))                                                   # ham yeniden üretildi (hata yok)
    s2 = k2.satir_test(satir, tmp_path, y, h, None)
    assert s2["durum"] == "tamam" and s2["girdi_damgasi"] != s["girdi_damgasi"]


def test_test_asamasi_planlamasi_bayat_satiri_kuyruga_alir(tablo, tmp_path, monkeypatch):
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch)
    k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    yol = k2.satir_yolu(tmp_path, "iyi1", "1d")
    r = _satir("iyi1")
    assert kasa.satir_bitti_mi(tmp_path, yol, r, (1.0,), "motor/arastirma/v2/test.py", kasa.SATIR_BITTI)
    _dosya_degisti(monkeypatch, "motor/arastirma/v2/test.py")                       # aşama kodu değişti
    assert not kasa.satir_bitti_mi(tmp_path, yol, r, (1.0,), "motor/arastirma/v2/test.py", kasa.SATIR_BITTI)


def test_bayat_satirda_kismi_sonuclar_silinir(tablo, tmp_path, monkeypatch):
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch)
    k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    kd = k2.kismi_dizin(tmp_path, "iyi1", "1d", "k2a")
    kd.mkdir(parents=True, exist_ok=True)
    (kd / "eski.npy").write_bytes(b"eski")
    _motor_degisti(monkeypatch)
    _yeniden_uret(tmp_path, h)
    k2.satir_test(_satir("iyi1"), tmp_path, y, h, None)
    assert not (kd / "eski.npy").exists()                                           # eski kısmi p-değeri girdisi yeni satıra karışmadı


# ---- saglamlik
def _saglamlik_kur(tablo, tmp_path, monkeypatch):
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch)
    cagri = []

    class SahteSt:
        parametreler = {"n": 20}
        parametre_izgarasi = {"n": [10, 20, 30]}

        def yeni(self, **kw):
            return SahteSt()

    monkeypatch.setattr(saglamlik.hm, "varsayilan_strateji", lambda ad: ("varsayilan", SahteSt()))

    def sahte_ham(st, tf, evren_t, tablo_yolu, gecikme=0, carpan=1.0):
        cagri.append(1)
        return ham.ham_yukle(tmp_path, 1.0, "iyi1", "1d", evren_t, h, veri_al=ham.veri_oku)
    monkeypatch.setattr(saglamlik, "strateji_ham", sahte_ham)
    monkeypatch.setattr(saglamlik, "kapanis_serileri", lambda ev: {"A": _kapanis(2500), "B": _kapanis(2500, seed=3)})
    return y, h, cagri


def test_saglamlik_onbellegi_damga_uyusmazliginda_yeniden_kosar(tablo, tmp_path, monkeypatch):
    y, h, cagri = _saglamlik_kur(tablo, tmp_path, monkeypatch)
    row = _satir("iyi1")
    s = saglamlik.saglamlik_satiri(row, tmp_path, y, h)
    n1, d1 = len(cagri), s["girdi_damgasi"]
    assert s["durum"] == "tamam" and n1 > 0 and d1
    saglamlik.saglamlik_satiri(row, tmp_path, y, h)
    assert len(cagri) == n1                                                         # önbellek isabeti
    ky = saglamlik._kismi_yolu(tmp_path, "iyi1", "1d")
    kasa.atomik_yaz_json(ky, {"eski": {"pf": 9.0, "hata": ""}})
    _motor_degisti(monkeypatch)
    r = saglamlik.saglamlik_satiri(row, tmp_path, y, h)                             # ham bayat: eski sonuç SESSİZCE döndürülmez
    assert r.get("ertelendi") and r.get("damga")
    assert json.loads(saglamlik.satir_yolu(tmp_path, "iyi1", "1d").read_text())["durum"] == "tamam"      # kalıcı hata yok
    assert not ky.exists()                                                          # bayat S2 kısmi sonucu silindi
    assert not kasa.satir_bitti_mi(tmp_path, saglamlik.satir_yolu(tmp_path, "iyi1", "1d"), row, (1.0, 2.0),
                                   "motor/arastirma/v2/saglamlik.py", saglamlik.SATIR_BITTI)
    _yeniden_uret(tmp_path, h)
    s2 = saglamlik.saglamlik_satiri(row, tmp_path, y, h)
    assert s2["durum"] == "tamam" and len(cagri) > n1 and s2["girdi_damgasi"] != d1


def test_saglamlik_bayat_ham_hatasi_kalici_hata_olmaz(tablo, tmp_path, monkeypatch):
    y, h, cagri = _saglamlik_kur(tablo, tmp_path, monkeypatch)
    row = _satir("iyi1")
    _motor_degisti(monkeypatch)
    r = saglamlik.saglamlik_satiri(row, tmp_path, y, h)
    assert r.get("ertelendi") and not saglamlik.satir_yolu(tmp_path, "iyi1", "1d").exists()
    _yeniden_uret(tmp_path, h)
    assert saglamlik.saglamlik_satiri(row, tmp_path, y, h)["durum"] == "tamam"


# ---- kasa günlük önbelleği
def test_kasa_gunluk_onbellegi_damga_uyusmazliginda_yeniden_hesaplar(tablo, tmp_path, monkeypatch):
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch)
    row = _satir("iyi1")
    a = kasa.satir_gunluk(tmp_path, row, y, h)
    assert (tmp_path / "gunluk" / "iyi1--1d.json").exists()
    gercek_oynat = kasa.satir_oynat
    cagri = []
    monkeypatch.setattr(kasa, "satir_oynat", lambda *x, **k: (cagri.append(1), gercek_oynat(*x, **k))[1])
    pd.testing.assert_series_equal(kasa.satir_gunluk(tmp_path, row, y, h), a, check_names=False, check_freq=False)
    assert not cagri                                                                # girdi aynı: önbellek isabeti
    _motor_degisti(monkeypatch)
    with pytest.raises(ham.DamgaUyusmazligi, match="motor_hash"):                   # eski günlük seri bayat ham ile SESSİZCE sunulmaz
        kasa.satir_gunluk(tmp_path, row, y, h)
    assert cagri
    _yeniden_uret(tmp_path, h)
    kasa.satir_gunluk(tmp_path, row, y, h)
    assert json.loads((tmp_path / "gunluk" / "iyi1--1d.json").read_text())["girdi_damgasi"] != ""


# ================================================================== 3. eski bayrak davranışı değişmez
def _eski_satir_yaz(tmp_path, ad="iyi1"):
    """Mühürlü v2 çıktısı gibi: damgasız ('girdi_damgasi' yok) bitmiş satır."""
    yol = k2.satir_yolu(tmp_path, ad, "1d")
    kasa.atomik_yaz_json(yol, {"strateji": ad, "tf": "1d", "evren": "kripto", "stil_v2": "swing", "durum": "tamam", "p": 0.003, "p1": 0.003,
                               "p2": math.nan, "asama": 1, "hata": "", "T": 1.0, "n_islem": 5, "rnd_desteklenmeyen": ""})
    return yol


def test_eski_damgasiz_satir_bayraksiz_reddedilir_dosyaya_dokunulmaz(tablo, tmp_path, monkeypatch):
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch)
    yol = _eski_satir_yaz(tmp_path)
    once = yol.read_bytes()
    r = k2.satir_test(_satir("iyi1"), tmp_path, y, h, None)
    assert r.get("ertelendi") and "girdi damgası yok" in r["neden"]
    assert yol.read_bytes() == once                                                 # tarihsel çıktının üzerine yazılmadı
    with pytest.raises(ham.DamgaUyusmazligi, match="V2_ESKI_YAN_DOSYA"):
        k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)


def test_eski_bayrakla_damgasiz_satir_gecerli_ve_degismez(tablo, tmp_path, monkeypatch):
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch)
    yol = _eski_satir_yaz(tmp_path)
    once = yol.read_bytes()
    monkeypatch.setenv(ham.ESKI_ORTAM, "1")
    assert k2.satir_test(_satir("iyi1"), tmp_path, y, h, None)["p"] == 0.003         # eski kayıt aynen döner, yeniden koşulmaz
    assert yol.read_bytes() == once
    o = k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    assert "bekleyen" not in o and yol.read_bytes() == once
    assert float(pd.read_csv(tmp_path / "test.csv").set_index("strateji").loc["iyi1", "p"]) == 0.003


def test_eski_bayrakla_damgasiz_gunluk_onbellek_okunur(tablo, tmp_path, monkeypatch):
    y, h, hv, mh = _gelistirme(tablo, tmp_path, monkeypatch)
    row = _satir("iyi1")
    a = kasa.satir_gunluk(tmp_path, row, y, h)
    (tmp_path / "gunluk" / "iyi1--1d.json").unlink()                                # mühürlü çıktıda sidecar yoktu
    with pytest.raises(ham.DamgaUyusmazligi, match="V2_ESKI_YAN_DOSYA"):
        kasa.satir_gunluk(tmp_path, row, y, h)
    monkeypatch.setenv(ham.ESKI_ORTAM, "1")
    pd.testing.assert_series_equal(kasa.satir_gunluk(tmp_path, row, y, h), a, check_names=False, check_freq=False)
    assert not (tmp_path / "gunluk" / "iyi1--1d.json").exists()                     # okuma dosya üretmedi/değiştirmedi


def test_eski_bayrak_ham_yan_dosya_davranisi_ayni(tablo, tmp_path):
    from testler.test_b16_damga_kapsam import sentetik
    y, h = tablo
    veri = sentetik()
    ham.ham_gorev(AD_GERCEK, "1d", "DK_XAU", 1.0, tmp_path, y, h, _veri=lambda s, t: (veri, None))
    yan = ham.dosya_yolu(tmp_path / "ham" / "x1", AD_GERCEK, "1d", "DK_XAU").with_suffix(".json")
    m = json.loads(yan.read_text())
    yan.write_text(json.dumps({k: v for k, v in m.items() if k not in ham.DAMGA_ALANLARI}))
    with pytest.raises(RuntimeError, match="kimlik damgası yok"):                   # DamgaUyusmazligi, RuntimeError alt sınıfı
        ham.ham_yukle(tmp_path, 1.0, AD_GERCEK, "1d", ("DK_XAU",), h, veri_al=lambda s, t: (veri, None))
    assert "DK_XAU" in ham.ham_yukle(tmp_path, 1.0, AD_GERCEK, "1d", ("DK_XAU",), h, eski_kabul=True)[0]
