"""v2 ham koşu + eleme (ON_KAYIT_V2 bölüm 3, 4, 1.1, 1.2, 0.4; bölüm 11 kabul testleri). Yalnız SENTETİK veri."""
from __future__ import annotations

import ast
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import evren_maliyet
from motor.arastirma import wf_evren as we
from motor.arastirma import wf_tarama
from motor.arastirma.v2 import eleme, ham, maliyet, sabit

KOK = Path(__file__).resolve().parents[1]
V2 = KOK / "motor" / "arastirma" / "v2"


# ------------------------------------------------------------------ yardımcılar
def sentetik(n=1500, seed=3, bas="2018-01-01", tf="D"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(bas, periods=n, freq=tf, tz="UTC")
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.005, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.005, n)))
    return pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": c, "hacim": rng.uniform(1e3, 2e3, n)}, index=idx)


@pytest.fixture(autouse=True)
def _gercek_veri_yok(monkeypatch):
    """B16: ham_yukle/eleme veri özetini şimdiki veriden yeniden hesaplar; testler gerçek veri diskine bağlı olmasın (veri yok = None özet)."""
    def yok(sembol, tf):
        raise FileNotFoundError(f"{sembol} {tf}: test ortamında gerçek veri yok")
    monkeypatch.setattr(we, "_veri", yok)


@pytest.fixture()
def tablo(tmp_path):
    y = maliyet.tabloyu_hazirla(tmp_path)
    return y, evren_maliyet.tablo_hash(y)


# ------------------------------------------------------------------ 1: tohum, sabit kaynağı
def test_satir_tohumu_deterministik_ve_formul():
    import zlib
    a = sabit.satir_tohumu("swing__x", "1d", "k2a")
    assert a == sabit.satir_tohumu("swing__x", "1d", "k2a") == (zlib.crc32(b"swing__x|1d|k2a") ^ 20261109)
    assert a != sabit.satir_tohumu("swing__x", "1d", "k2b")
    with pytest.raises(ValueError):
        sabit.satir_tohumu("swing__x", "1d", "yok")


def test_holdout_sabiti_v1_ile_ayni():
    assert sabit.HOLDOUT_BAS == we.HOLDOUT_BAS


def test_sabit_disinda_esik_sabiti_yok():
    """v2 modüllerinde (sabit.py hariç) sayısal eşik sabiti yok: yalnız 0, 1, 2, -1, birim dönüşümleri (100, 1e4) ve dilimler."""
    izinli = {0, 1, 2, -1, 100, 100.0, 1e4, 10000.0}
    kirli = []
    for f in sorted(V2.glob("*.py")):
        if f.name == "sabit.py":
            continue
        t = ast.parse(f.read_text())
        dilim = {id(c) for n in ast.walk(t) if isinstance(n, ast.Subscript) for c in ast.walk(n.slice)}
        for n in ast.walk(t):
            if (isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
                    and id(n) not in dilim and n.value not in izinli):
                kirli.append((f.name, n.lineno, n.value))
    assert not kirli, kirli


# ------------------------------------------------------------------ 1.2 funding
def test_v1_tablosu_degismedi_v2_sutunu_ayri(tablo, tmp_path):
    v1 = evren_maliyet.TABLO_YOLU
    assert evren_maliyet.tablo_hash(v1) == v1.with_suffix(".sha256").read_text().strip()
    assert "funding_long_8s_oran" not in pd.read_csv(v1).columns
    with pytest.raises(KeyError):
        evren_maliyet.funding_long_8s_oran("DK_XAU", v1)                 # v1 tablosunda sütun yok: açık hata
    y, h = tablo
    v2 = pd.read_csv(y)
    assert (v2.drop(columns="funding_long_8s_oran").to_csv(index=False)) == v1.read_text()      # v1 içeriği aynen
    assert h == y.with_suffix(".sha256").read_text().strip() and h != evren_maliyet.tablo_hash(v1)
    assert evren_maliyet.funding_long_8s_oran("DK_XAU", y) == pytest.approx(sabit.FUNDING_LONG_8S_ORAN)
    assert evren_maliyet.funding_long_8s_oran("BTCUSDT", y) == 0.0        # kripto: gerçek seri (motor), sabit oran yok
    assert maliyet.tabloyu_hazirla(tmp_path) == y                          # ikinci çağrı: bayt bayt aynı doğrulanır


def test_funding_dk_long_16_saat_iki_periyot_short_sifir():
    g = pd.Timestamp("2020-01-01 00:00", tz="UTC")
    c = g + pd.Timedelta(hours=16)
    usd = maliyet.funding_maliyeti_usd([1, -1], [10.0, 10.0], [100.0, 100.0], [g, g], [c, c], 0.0001)
    assert usd[0] == pytest.approx(2 * 0.0001 * 1000.0)       # 16 saat = 2 periyot × %0.01 × nominal(1000)
    assert usd[1] == 0.0


def _tek_islem(yon=1, saat=16, miktar=10.0, fiyat=100.0, r=0.5):
    g = pd.Timestamp("2020-01-01 00:00", tz="UTC")
    risk = 50.0
    return pd.DataFrame({"yon": [yon], "giris_zamani": [g], "giris_fiyati": [fiyat], "cikis_zamani": [g + pd.Timedelta(hours=saat)],
                         "cikis_fiyati": [fiyat], "miktar": [miktar], "brut_pnl": [0.0], "komisyon": [0.0], "funding": [0.0],
                         "net_pnl": [r * risk], "r": [r], "cikis_nedeni": ["x"], "kismi_sayisi": [0], "kismi_pnl": [0.0]})


def test_islem_hazirla_funding_dk_kripto_ve_x2_carpmaz(tablo):
    y, _ = tablo
    m = sentetik(40, bas="2019-12-25")
    r_dk = ham.islem_hazirla(_tek_islem(1), "DK_XAU", "1d", 1.0, m, y)[0]
    assert float(r_dk["r"].iloc[0]) == pytest.approx(0.5 - 2 * 0.0001 * 1000.0 / 50.0, abs=1e-6)     # R'den 0.004 düşer
    assert float(r_dk["fonlama_r"].iloc[0]) == pytest.approx(0.004, abs=1e-7)
    r_sh = ham.islem_hazirla(_tek_islem(-1), "DK_XAU", "1d", 1.0, m, y)[0]
    assert float(r_sh["r"].iloc[0]) == pytest.approx(0.5) and float(r_sh["fonlama_r"].iloc[0]) == 0.0
    r_kr = ham.islem_hazirla(_tek_islem(1), "BTCUSDT", "1d", 1.0, m, y)[0]
    assert float(r_kr["r"].iloc[0]) == pytest.approx(0.5) and float(r_kr["fonlama_r"].iloc[0]) == 0.0   # kriptoda gerçek seri motorda
    r_x2 = ham.islem_hazirla(_tek_islem(1), "DK_XAU", "1d", 2.0, m, y)[0]
    assert float(r_x2["fonlama_r"].iloc[0]) == pytest.approx(float(r_dk["fonlama_r"].iloc[0]))        # ×2 funding'i çarpmaz


# ------------------------------------------------------------------ 3 MTM yolu
def _mtm_kur(kapanis, giris_gun, cikis_gun, yon=1, r_son=0.7):
    idx = pd.date_range("2020-01-01", periods=len(kapanis), freq="D", tz="UTC")
    kg = pd.Series(kapanis, index=idx, dtype=float)
    g = idx[giris_gun] + pd.Timedelta(hours=3)
    c = idx[cikis_gun] + pd.Timedelta(hours=1)
    return ham.mtm_yolu([g], [c], [yon], [100.0], [10.0], [r_son], [0.02], [0.1], kg)


def test_mtm_son_deger_r_ve_gun_sayisi():
    p = _mtm_kur([100, 105, 110, 90, 95, 99, 100, 101], 1, 4)
    assert len(p) == 4                                       # giriş günü 1 ... çıkış günü 4 (takvim günü, uçlar dahil)
    assert float(p["kum_r"].iloc[-1]) == pytest.approx(0.7)  # son değer = işlemin R'si
    assert list(p["gun"].dt.day) == [2, 3, 4, 5]
    g, c = pd.Timestamp("2020-01-02 03:00", tz="UTC"), pd.Timestamp("2020-01-05 01:00", tz="UTC")
    pay = (pd.Timestamp("2020-01-03", tz="UTC") - g) / (c - g)
    assert float(p["kum_r"].iloc[0]) == pytest.approx((105 - 100) / 10 - 0.02 - 0.1 * pay)


def test_mtm_ara_gun_formulu_ve_short():
    p = _mtm_kur([100, 105, 110, 90, 95], 1, 3, yon=-1)       # short: fiyat düşerse kâr
    ilk = float(p["kum_r"].iloc[0])
    giris = pd.Timestamp("2020-01-02 03:00", tz="UTC")
    cikis = pd.Timestamp("2020-01-04 01:00", tz="UTC")
    pay = (pd.Timestamp("2020-01-03", tz="UTC") - giris) / (cikis - giris)
    assert ilk == pytest.approx(-1 * (105 - 100) / 10 - 0.02 - 0.1 * pay)


def test_mtm_ayni_gun_tek_nokta():
    p = _mtm_kur([100, 101, 102], 1, 1)
    assert len(p) == 1 and float(p["kum_r"].iloc[0]) == pytest.approx(0.7)


def test_mtm_gelecek_mumu_okumaz():
    m = sentetik(30)
    kg_tam = ham.gunluk_kapanis(m, "1d")
    kes = m.iloc[:12]                                          # günler 0..11
    bozuk = m.copy()
    bozuk.iloc[12:, bozuk.columns.get_loc("kapanis")] *= 50.0  # gelecek değişse de yol değişmez
    g, c = m.index[3] + pd.Timedelta(hours=1), m.index[11] + pd.Timedelta(hours=1)
    arg = dict(yon=[1], giris_fiyati=[100.0], stop_mesafe=[10.0], r_son=[0.3], giris_maliyet_r=[0.01], funding_r=[0.0])
    a = ham.mtm_yolu([g], [c], kapanis_gun=kg_tam, **arg)
    b = ham.mtm_yolu([g], [c], kapanis_gun=ham.gunluk_kapanis(kes, "1d"), **arg)
    d = ham.mtm_yolu([g], [c], kapanis_gun=ham.gunluk_kapanis(bozuk, "1d"), **arg)
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(a, d)


def test_gunluk_kapanis_sinir_asan_mum_ertesi_gune():
    """4h mum 22:00-02:00 gece yarısını aşıyorsa o günün kapanışı sayılmaz (henüz kapanmadı)."""
    idx = pd.DatetimeIndex(["2020-01-01 18:00", "2020-01-01 22:00", "2020-01-02 02:00"], tz="UTC")
    m = pd.DataFrame({"kapanis": [10.0, 11.0, 12.0]}, index=idx)
    s = ham.gunluk_kapanis(m, "4h")
    assert s.loc["2020-01-01"] == 10.0 and s.loc["2020-01-02"] == 12.0


def test_islem_hazirla_mtm_gercek_backtest_son_deger_r(tablo):
    y, h = tablo
    m = sentetik()
    etiket, st = ham.varsayilan_strateji("swing__bant-donus")
    from motor.backtest.motor import backtest
    ay = evren_maliyet.maliyet_ayarlari("DK_XAU", we.tarama.VARSAYILAN_KURAL, 1.0, y)
    res = backtest(m, st, ay, None)
    hm_, mtm = ham.islem_hazirla(res.islemler, "DK_XAU", "1d", 1.0, m, y)
    assert len(hm_) > 5
    son = mtm.groupby("islem_no")["kum_r"].last().to_numpy()
    assert np.allclose(son, hm_["r"].to_numpy(), atol=1e-6)
    gun = (hm_["cikis_zamani"].dt.floor("D") - hm_["giris_zamani"].dt.floor("D")).dt.days + 1
    assert (mtm.groupby("islem_no").size().to_numpy() == gun.to_numpy()).all()


# ------------------------------------------------------------------ 1.1 varsayılan ayar
def test_varsayilan_ayar_kart_ilk_kayit_yoksa_sinif(monkeypatch):
    from motor.strateji import kayit
    etiket, st = ham.varsayilan_strateji("swing__bant-donus")
    ilk = kayit.kart_ayarlari("swing__bant-donus")[0]["kart_id"]
    assert etiket == f"kart:{ilk}"
    monkeypatch.setattr(kayit, "kart_ayarlari", lambda ad: [])
    etiket2, st2 = ham.varsayilan_strateji("swing__bant-donus")
    assert etiket2 == "varsayilan" and st2.parametreler == kayit.al("swing__bant-donus")().parametreler


def test_ham_gorev_tek_kosu_izgara_yok(monkeypatch, tablo, tmp_path):
    y, h = tablo
    cagri = {"n": 0}
    gercek = ham.backtest

    def say(*a, **k):
        cagri["n"] += 1
        return gercek(*a, **k)
    monkeypatch.setattr(ham, "backtest", say)

    def yasak(*a, **k):
        raise AssertionError("aday_listesi/ızgara çağrılamaz")
    monkeypatch.setattr(wf_tarama, "aday_listesi", yasak)
    m = sentetik()
    r = ham.ham_gorev("swing__bant-donus", "1d", "DK_XAU", 1.0, tmp_path, y, h, _veri=lambda s, t: (m, None))
    assert cagri["n"] == 1 and r["n_islem"] > 0 and r["ayar"].startswith("kart:")


# ------------------------------------------------------------------ 0.4 holdout sızıntısı = sert hata
def test_sizinti_kontrol_mum_ve_funding():
    ok = sentetik(10, bas="2025-10-20")
    ham.sizinti_kontrol("X", "1d", ok, None)
    kotu = sentetik(30, bas="2025-10-20")                      # 2025-11-08 ve sonrasına uzanır
    with pytest.raises(ham.HoldoutSizintisi):
        ham.sizinti_kontrol("X", "1d", kotu, None)
    f = pd.DataFrame({"oran": [0.0001]}, index=pd.DatetimeIndex(["2025-11-08 00:00"], tz="UTC"))
    with pytest.raises(ham.HoldoutSizintisi):
        ham.sizinti_kontrol("X", "1d", ok, f)


def test_ham_gorev_sizinti_sert_hata_yan_dosya_yok(tablo, tmp_path):
    y, h = tablo
    kotu = sentetik(40, bas="2025-10-20")
    with pytest.raises(ham.HoldoutSizintisi):
        ham.ham_gorev("swing__bant-donus", "1d", "DK_XAU", 1.0, tmp_path, y, h, _veri=lambda s, t: (kotu, None))
    assert not list((tmp_path / "ham").rglob("*.json"))        # "bitti" işareti yazılmadı


def test_veri_oku_gelistirme_donemi_ve_v1_siniri(monkeypatch):
    """veri_oku v1 yükleyicisini kullanır; sınırı aşan veri dönerse HoldoutSizintisi."""
    kotu = sentetik(30, bas="2025-10-20")
    monkeypatch.setattr(we, "_veri", lambda s, t: (kotu, None))
    with pytest.raises(ham.HoldoutSizintisi):
        ham.veri_oku("BTCUSDT", "1d")
    assert sabit.DONEM in we.GELISTIRME_DONEMLERI and we.DONEMLER[sabit.DONEM]["bit"] == sabit.HOLDOUT_BAS


def test_ham_yukle_sidecar_sizinti_reddeder(tablo, tmp_path):
    y, h = tablo
    hd = tmp_path / "ham" / "x1"
    hd.mkdir(parents=True)
    ham._yaz_atomik(ham._HAM_BOS, hm_yol := ham.dosya_yolu(hd, "a", "1d", "BTCUSDT"))
    ham._yan_yaz(hm_yol.with_suffix(".json"), {"maliyet_hash": h, "veri_yok": False, "hata": "", "veri_bas": "2020-01-01", "veri_bit": "2025-11-08"})
    with pytest.raises(ham.HoldoutSizintisi):
        ham.ham_yukle(tmp_path, 1.0, "a", "1d", ("BTCUSDT",), h)


def test_havuz_muhru_yoksa_veya_uyusmuyorsa_hata(tmp_path):
    hv = tmp_path / "h.csv"
    hv.write_text("strateji,stil_v2,tf,evren\na,swing,1d,genel\n")
    with pytest.raises(RuntimeError, match="mührü yok"):
        ham.havuz_muhru_dogrula(hv, tmp_path / "yok.json")
    mh = tmp_path / "m.json"
    mh.write_text(json.dumps({"havuz_csv_sha256": "0" * 64}))
    with pytest.raises(RuntimeError, match="uyuşmuyor"):
        ham.havuz_muhru_dogrula(hv, mh)
    mh.write_text(json.dumps({"havuz_csv_sha256": hashlib.sha256(hv.read_bytes()).hexdigest()}))
    assert ham.havuz_muhru_dogrula(hv, mh)


def test_gercek_havuz_muhru_tutarli():
    assert ham.havuz_muhru_dogrula()["m"] >= sabit.M_TABAN


# ------------------------------------------------------------------ devam ettirilebilirlik ve bütçe
def test_ham_gorev_devam_ettirilebilir(tablo, tmp_path):
    y, h = tablo
    m = sentetik()
    a = ham.ham_gorev("swing__bant-donus", "1d", "DK_XAU", 1.0, tmp_path, y, h, _veri=lambda s, t: (m, None))
    assert a["n_islem"] > 0
    p = ham.dosya_yolu(tmp_path / "ham" / "x1", "swing__bant-donus", "1d", "DK_XAU")
    once = p.read_bytes()
    b = ham.ham_gorev("swing__bant-donus", "1d", "DK_XAU", 1.0, tmp_path, y, h, _veri=lambda s, t: (m, None))
    assert b == {"atlandi": True} and p.read_bytes() == once                    # biten atlanır, dosya değişmez
    c2 = ham.ham_gorev("swing__bant-donus", "1d", "DK_XAU", 2.0, tmp_path, y, h, _veri=lambda s, t: (m, None))
    assert c2["n_islem"] > 0 and (tmp_path / "ham" / "x2").exists()             # çarpan başına ayrı bitti işareti


def test_ayni_girdi_ayni_cikti_bayt_bayt(tablo, tmp_path):
    y, h = tablo
    m = sentetik()
    for d in ("a", "b"):
        ham.ham_gorev("swing__bant-donus", "1d", "DK_XAU", 1.0, tmp_path / d, y, h, _veri=lambda s, t: (m, None))
    for alt in ("ham/x1", "mtm/x1"):
        pa = (tmp_path / "a" / alt / "swing__bant-donus--1d--DK_XAU.parquet").read_bytes()
        pb = (tmp_path / "b" / alt / "swing__bant-donus--1d--DK_XAU.parquet").read_bytes()
        assert pa == pb


def test_gorevleri_uret_biten_listeye_girmez(tablo, tmp_path):
    y, h = tablo
    havuz = pd.DataFrame([{"strateji": "swing__a", "stil_v2": "swing", "tf": "1d", "evren": "kripto"}])
    veri = lambda s, t: (sentetik(30), None)                                             # noqa: E731
    g, toplam, kalan = ham.gorevleri_uret(havuz, tmp_path, veri_al=veri)
    assert toplam == 26 and kalan == 26 and {x["carpan"] for x in g} == {1.0, 2.0} and len(g) == 26
    damga = ham.kimlik_damgasi("swing__a", veri=ham.veri_sha256(sentetik(30), None))       # B16: bitti = var + damga uyumlu
    ham._yan_yaz(ham.dosya_yolu(tmp_path / "ham" / "x1", "swing__a", "1d", "BTCUSDT").with_suffix(".json"), {"hata": "", **damga})
    g, toplam, kalan = ham.gorevleri_uret(havuz, tmp_path, veri_al=veri)
    assert kalan == 25
    gp = ham.gorevleri_uret(pd.DataFrame([{"strateji": "pf__z", "stil_v2": "portfoy", "tf": "1d", "evren": "genel"}]), tmp_path)
    assert gp[1] == 2 and gp[0][0]["tur"] == "portfoy"


def test_butce_dolunca_yeni_gorev_baslamaz(tablo, tmp_path, monkeypatch):
    import time
    y, h = tablo
    ham._baslat({"veri_dizini": None, "cikti": str(tmp_path), "tablo_yolu": str(y), "tablo_hash": h, "son": time.time() - 1})
    g = {"tur": "tek", "tf": "1d", "sembol": "DK_XAU", "carpan": 1.0, "stratejiler": ["swing__bant-donus", "swing__bas-omuz"]}
    s = ham._isci(g)
    assert s["ertelendi"] == 2 and s["sonuc"] == []
    assert not list(tmp_path.rglob("*.json"))
    assert ham._isci({"tur": "portfoy", "strateji": "pf__cta", "tf": "1d", "carpan": 1.0, "evren": "genel", "sembol": ham.PF_SEMBOL})["ertelendi"] == 1


def test_hata_satiri_sayilir_yan_dosyada(tablo, tmp_path, monkeypatch):
    y, h = tablo
    monkeypatch.setattr(ham, "backtest", lambda *a, **k: (_ for _ in ()).throw(ValueError("patladı")))
    r = ham.ham_gorev("swing__bant-donus", "1d", "DK_XAU", 1.0, tmp_path, y, h, _veri=lambda s, t: (sentetik(), None))
    assert "ValueError: patladı" in r["hata"] and not r["veri_yok"]
    assert json.loads(ham.dosya_yolu(tmp_path / "ham" / "x1", "swing__bant-donus", "1d", "DK_XAU").with_suffix(".json").read_text())["hata"]


# ------------------------------------------------------------------ E1–E5 sınır testleri (saf işlev)
def _iyi(**ov):
    m = {"net_x2": 0.1, "pf_x1": 1.5, "n_islem_x1": 300, "n_enstruman_x1": 12, "kill_x1": 0,
         "r_enstruman": {f"s{i}": 10.0 for i in range(12)}, "r_yil": {2019: 40.0, 2020: 40.0, 2021: 40.0},
         "r_sinif": {"kripto": 40.0, "hisse": 40.0, "emtia": 40.0}}
    m.update(ov)
    return m


def test_e_hepsi_gecer():
    k = eleme.eleme_tek(_iyi(), "genel")
    assert k["gecti"] and all(k[x] for x in eleme.KAPILAR) and k["nedenler"] == ""


@pytest.mark.parametrize("ov,kapi,gecer", [
    ({"pf_x1": 1.199}, "e1", False), ({"pf_x1": 1.2}, "e1", True), ({"net_x2": 0.0}, "e1", False), ({"net_x2": 1e-9}, "e1", True),
    ({"n_islem_x1": 199}, "e2", False), ({"n_islem_x1": 200}, "e2", True),
    ({"n_enstruman_x1": 9}, "e2", False), ({"n_enstruman_x1": 10}, "e2", True),
    ({"kill_x1": 1}, "e5", False), ({"kill_x1": 0}, "e5", True),
    ({"pf_x1": math.nan}, "e1", False), ({"net_x2": math.nan}, "e1", False), ({"n_islem_x1": math.nan}, "e2", False),
    ({"kill_x1": math.nan}, "e5", False), ({"kill_x1": None}, "e5", False),
])
def test_e_sinirlar_genel(ov, kapi, gecer):
    assert eleme.eleme_tek(_iyi(**ov), "genel")[kapi] is gecer


def test_e2_kripto_6_enstruman():
    assert not eleme.eleme_tek(_iyi(n_enstruman_x1=5), "kripto")["e2"]
    assert eleme.eleme_tek(_iyi(n_enstruman_x1=6), "kripto")["e2"]
    assert not eleme.eleme_tek(_iyi(n_enstruman_x1=9), "genel")["e2"]


def test_e3_tek_enstruman_ya_da_tek_yila_bagli_kalir():
    tek_en = {"A": 100.0, **{f"s{i}": -1.0 for i in range(11)}}
    assert not eleme.eleme_tek(_iyi(r_enstruman=tek_en), "genel")["e3"]
    tek_yil = {2019: 100.0, 2020: -5.0, 2021: -5.0}
    assert not eleme.eleme_tek(_iyi(r_yil=tek_yil), "genel")["e3"]
    assert eleme.eleme_tek(_iyi(r_yil={2019: 100.0, 2020: 0.5, 2021: 0.0}), "genel")["e3"]
    assert not eleme.eleme_tek(_iyi(r_yil={2019: 100.0, 2020: 0.0}), "genel")["e3"]      # kalan tam 0: geçmez (> 0)
    assert not eleme.eleme_tek(_iyi(r_enstruman={"A": 5.0}), "genel")["e3"]              # tek enstrüman: kalan 0
    assert not eleme.eleme_tek(_iyi(r_enstruman={}), "genel")["e3"]                      # veri yok = NaN = geçmez
    assert not eleme.eleme_tek(_iyi(r_enstruman={"A": 5.0, "B": math.nan}), "genel")["e3"]


def test_e4_genislik_sinif_payi():
    sinir = {"kripto": 14.9, "hisse": 14.9, "emtia": 70.2}                    # yalnız emtia ≥ %15
    assert not eleme.eleme_tek(_iyi(r_sinif=sinir), "genel")["e4"]
    iki = {"kripto": 15.0, "hisse": 15.0, "emtia": 70.0}                      # tam %15 geçer
    assert eleme.eleme_tek(_iyi(r_sinif=iki), "genel")["e4"]
    assert not eleme.eleme_tek(_iyi(r_sinif={"kripto": 100.0, "hisse": 0.0, "emtia": 0.0}), "genel")["e4"]
    assert not eleme.eleme_tek(_iyi(r_sinif={"kripto": -10.0, "hisse": -10.0, "emtia": -10.0}), "genel")["e4"]
    assert not eleme.eleme_tek(_iyi(r_sinif={}), "genel")["e4"]
    assert eleme.eleme_tek(_iyi(r_sinif={"kripto": 100.0}), "kripto")["e4"]    # kripto evreninde kapı yok


def test_e5_kill_sonuclari_ve_p_ust():
    k = eleme.eleme_tek(_iyi(kill_x1=3), "genel")
    assert not k["gecti"] and k["e1"] and not k["e5"] and "E5" in k["nedenler"]
    assert eleme.p_ust(False) == 1.0 and math.isnan(eleme.p_ust(True))


def _pf(**ov):
    m = {"net_x2": 0.2, "sharpe_x1": 0.8, "gun": 2000, "dengeleme": 50, "net_en_iyi_yil_haric": 0.1, "kill_x1": 0}
    m.update(ov)
    return m


@pytest.mark.parametrize("ov,kapi,gecer", [
    ({}, "e1", True), ({"sharpe_x1": 0.4999}, "e1", False), ({"sharpe_x1": 0.5}, "e1", True), ({"net_x2": 0.0}, "e1", False),
    ({"gun": 1094}, "e2", False), ({"gun": 1095}, "e2", True), ({"dengeleme": 19}, "e2", False), ({"dengeleme": 20}, "e2", True),
    ({"net_en_iyi_yil_haric": 0.0}, "e3", False), ({"net_en_iyi_yil_haric": 0.001}, "e3", True),
    ({"kill_x1": 1}, "e5", False), ({"sharpe_x1": math.nan}, "e1", False), ({"net_en_iyi_yil_haric": math.nan}, "e3", False),
])
def test_e_portfoy_sinirlar(ov, kapi, gecer):
    assert eleme.eleme_portfoy(_pf(**ov))[kapi] is gecer
    assert eleme.eleme_portfoy(_pf())["e4"] is True and eleme.eleme_portfoy(_pf())["gecti"]


def test_yil_haric_net():
    idx = pd.date_range("2019-01-01", "2021-12-31", freq="D", tz="UTC")
    r = pd.Series(0.0, index=idx)
    r[r.index.year == 2020] = 0.001                   # en iyi yıl
    r[r.index.year == 2021] = -0.0001
    assert eleme._yil_haric_net(r) < 0
    r[r.index.year == 2021] = 0.0001
    assert eleme._yil_haric_net(r) > 0


# ------------------------------------------------------------------ aşama: sentetik ham çıktısından eleme.csv
def _ham_yaz(cikti, h, ad, tf, semboller, carpan, tohum=1, kar=0.25, tek_sembol=None):
    hd = cikti / "ham" / ham.carpan_adi(carpan)
    rng = np.random.default_rng(tohum)
    for s in semboller:
        n = 40
        g = pd.DatetimeIndex(sorted(pd.Timestamp("2019-02-01", tz="UTC") + pd.to_timedelta(rng.integers(0, 365 * 5, n), unit="D")))
        c = g + pd.Timedelta(days=3)
        r = rng.normal(kar * (0 if (tek_sembol and s != tek_sembol) else 1), 1.0, n).astype(np.float32)
        if tek_sembol:
            r = np.where(s == tek_sembol, r + 0.0, rng.normal(-0.3, 0.2, n)).astype(np.float32)
        df = pd.DataFrame({"ayar_no": np.zeros(n, dtype=np.int16), "giris_zamani": g.as_unit("ns"), "cikis_zamani": c.as_unit("ns"),
                           "yon": np.ones(n, dtype=np.int8), "r": r, "sf": np.full(n, 0.05, dtype=np.float32),
                           "stop_mesafe": np.full(n, 5.0, dtype=np.float32), "fonlama_r": np.zeros(n, dtype=np.float32)})
        p = ham.dosya_yolu(hd, ad, tf, s)
        ham._yaz_atomik(df, p)
        ham._yan_yaz(p.with_suffix(".json"), {"maliyet_hash": h, "veri_yok": False, "hata": "", "veri_bas": "2018-01-01 00:00:00+00:00",
                                              "veri_bit": "2025-11-07 00:00:00+00:00", "ayar": "varsayilan",
                                              **ham.kimlik_damgasi(ad)})


def _havuz_kur(tmp_path, satirlar):
    hv = tmp_path / "havuz.csv"
    pd.DataFrame(satirlar).to_csv(hv, index=False)
    mh = tmp_path / "muhur.json"
    mh.write_text(json.dumps({"havuz_csv_sha256": hashlib.sha256(hv.read_bytes()).hexdigest(), "m": 939}))
    return hv, mh


def test_eleme_asamasi_sentetik_uctan_uca(tablo, tmp_path):
    y, h = tablo
    kripto = sabit.evren_listesi("kripto")
    assert len(kripto) == 13 and len(sabit.evren_listesi("genel")) == 35
    for c in (1.0, 2.0):
        _ham_yaz(tmp_path, h, "iyi", "1d", kripto, c, tohum=5, kar=0.6)
        _ham_yaz(tmp_path, h, "tek", "1d", kripto, c, tohum=5, kar=0.0, tek_sembol=kripto[0])
    hv, mh = _havuz_kur(tmp_path, [
        {"strateji": "iyi", "stil_v2": "swing", "tf": "1d", "evren": "kripto", "etiket": "trend", "alt_etiket": "x", "kume_no": 1, "kilit_gorulmus": "hayir"},
        {"strateji": "tek", "stil_v2": "swing", "tf": "1d", "evren": "kripto", "etiket": "trend", "alt_etiket": "y", "kume_no": 2, "kilit_gorulmus": "hayir"}])
    o = eleme.eleme_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)
    assert o["satir"] == 2 and o["bekleyen"] == 0
    d = pd.read_csv(tmp_path / "eleme.csv").set_index("strateji")
    assert d.loc["iyi", "durum"] == "gecti" and bool(d.loc["iyi", "e1"]) and d.loc["iyi", "n_enstruman_x1"] >= 6
    assert d.loc["tek", "durum"] == "elendi" and not bool(d.loc["tek", "e3"])          # tek enstrümana bağlı: E3'ten kalır
    assert d.loc["tek", "p_ust"] == 1.0 and math.isnan(d.loc["iyi", "p_ust"])
    assert (tmp_path / "eleme_ozet.json").exists()
    assert json.loads((tmp_path / "eleme_ozet.json").read_text())["maliyet_tablosu_sha256"] == h


def test_eleme_ham_eksikse_yazmaz_ve_hata_satiri(tablo, tmp_path):
    y, h = tablo
    kripto = sabit.evren_listesi("kripto")
    hv, mh = _havuz_kur(tmp_path, [{"strateji": "eksik", "stil_v2": "swing", "tf": "1d", "evren": "kripto"}])
    o = eleme.eleme_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)
    assert o["bekleyen"] == 1 and not (tmp_path / "eleme.csv").exists()               # ham yok: açık, csv yazılmaz
    # bir sembolde hata -> satır "hata", p_ust = 1
    for c in (1.0, 2.0):
        _ham_yaz(tmp_path, h, "eksik", "1d", kripto, c)
        p = ham.dosya_yolu(tmp_path / "ham" / ham.carpan_adi(c), "eksik", "1d", kripto[0]).with_suffix(".json")
        p.write_text(json.dumps({"maliyet_hash": h, "veri_yok": False, "hata": "ValueError: patladı", **ham.kimlik_damgasi("eksik")}))
    o = eleme.eleme_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)
    d = pd.read_csv(tmp_path / "eleme.csv")
    assert o["hata"] == 1 and d.loc[0, "durum"] == "hata" and d.loc[0, "p_ust"] == 1.0 and "patladı" in d.loc[0, "hata"]


def test_eleme_butce_dolunca_yazmaz(tablo, tmp_path):
    y, h = tablo
    kripto = sabit.evren_listesi("kripto")
    for c in (1.0, 2.0):
        _ham_yaz(tmp_path, h, "iyi", "1d", kripto, c, tohum=5, kar=0.6)
    hv, mh = _havuz_kur(tmp_path, [{"strateji": "iyi", "stil_v2": "swing", "tf": "1d", "evren": "kripto"}])
    o = eleme.eleme_asamasi(tmp_path, 1, 1e-9, hv, mh, ilerleme=False)       # bütçe anında dolmuş
    assert o["bekleyen"] == 1 and not (tmp_path / "eleme.csv").exists()
    o = eleme.eleme_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)       # yeniden çalıştır: sürer
    assert o["bekleyen"] == 0 and (tmp_path / "eleme.csv").exists()


def test_eleme_muhur_yoksa_acik_hata(tmp_path):
    hv = tmp_path / "h.csv"
    hv.write_text("strateji,stil_v2,tf,evren\na,swing,1d,genel\n")
    with pytest.raises(RuntimeError, match="mührü yok"):
        eleme.eleme_asamasi(tmp_path, 1, None, hv, tmp_path / "yok.json", ilerleme=False)


def test_portfoy_metrikleri_sentetik(tmp_path):
    gun = pd.date_range("2018-01-01", "2024-12-31", freq="D", tz="UTC")
    rng = np.random.default_rng(0)
    r = rng.normal(0.0008, 0.01, len(gun))
    g = pd.DataFrame({"gun": gun.as_unit("ns"), "getiri": r, "dengeleme": (np.arange(len(gun)) % 30 == 0)})
    m1 = {"veri_bas_sembol": {"BTCUSDT": "2017-08-18 00:00:00+00:00", "ETHUSDT": "2017-08-18 00:00:00+00:00"}, "kill_olayi": 0}
    met = eleme.portfoy_metrikleri(g, m1, g)
    assert met["gun"] == len(gun) - 0 or met["gun"] > 2000
    k = eleme.eleme_portfoy(met)
    assert k["e2"] and k["e5"]


def test_pf_fonlama_duzeltmesi_dk_long_kripto_short(tablo):
    y, _ = tablo
    gun = pd.date_range("2020-01-01", periods=4, freq="D", tz="UTC")
    ozs = pd.Series([1000.0, 1000.0, 1000.0, 1000.0], index=gun)
    getiri = pd.Series([0.0, 0.01, 0.0, 0.0], index=gun)
    poz = pd.DataFrame({"DK_XAU": [1.0, 1.0, -1.0, 0.0], "BTCUSDT": [5.0, 5.0, 5.0, 5.0]}, index=gun)
    veri = {"DK_XAU": pd.DataFrame({"kapanis": [100.0] * 4}, index=gun), "BTCUSDT": pd.DataFrame({"kapanis": [10.0] * 4}, index=gun)}
    adj, top = ham.pf_fonlama_duzeltmesi(getiri, ozs, poz, veri, y)
    gunluk = 1.0 * 100.0 * 0.0001 * 3 / 1000.0                      # 1 adet × 100 × %0.01 × 3 periyot / özsermaye
    assert adj.iloc[1] == pytest.approx(0.01 - gunluk) and adj.iloc[2] == 0.0 and adj.iloc[3] == 0.0    # short/kripto: düzeltme yok
    assert adj.iloc[0] == pytest.approx(-gunluk) and top == pytest.approx(2 * gunluk)


# ------------------------------------------------------------------ B16: kimlik damgası
def test_b16_yan_dosya_damgasi_ve_uyusmazlik_reddi(tablo, tmp_path, monkeypatch):
    y, h = tablo
    _ham_yaz(tmp_path, h, "swing__a", "1d", ["BTCUSDT"], 1.0)
    yan = ham.dosya_yolu(tmp_path / "ham" / "x1", "swing__a", "1d", "BTCUSDT").with_suffix(".json")
    m = json.loads(yan.read_text())
    assert set(ham.DAMGA_ALANLARI) <= set(m) and m["motor_hash"] and m["strateji_hash"] and "git_commit" in m
    with pytest.raises(ValueError, match="veri özeti"):                                  # B16: veri_al zorunlu
        ham.ham_yukle(tmp_path, 1.0, "swing__a", "1d", ("BTCUSDT",), h)
    ham.ham_yukle(tmp_path, 1.0, "swing__a", "1d", ("BTCUSDT",), h, veri_al=ham.veri_oku)  # uyumlu: okunur
    for alan in ("strateji_hash", "motor_hash"):
        bozuk = dict(m, **{alan: "0" * 64})
        yan.write_text(json.dumps(bozuk))
        with pytest.raises(RuntimeError, match=alan):
            ham.ham_yukle(tmp_path, 1.0, "swing__a", "1d", ("BTCUSDT",), h, veri_al=ham.veri_oku)
    # veri özeti: veri_al verilirse karşılaştırılır
    mum = sentetik(30, bas="2020-01-01")
    yan.write_text(json.dumps(dict(m, veri_sha256=ham.veri_sha256(mum, None))))
    ham.ham_yukle(tmp_path, 1.0, "swing__a", "1d", ("BTCUSDT",), h, veri_al=lambda s, t: (mum, None))
    with pytest.raises(RuntimeError, match="veri_sha256"):
        ham.ham_yukle(tmp_path, 1.0, "swing__a", "1d", ("BTCUSDT",), h, veri_al=lambda s, t: (mum.iloc[:-1], None))


def test_b16_eski_damgasiz_yan_dosya_yalniz_acik_bayrakla_okunur(tablo, tmp_path, monkeypatch):
    y, h = tablo
    _ham_yaz(tmp_path, h, "swing__a", "1d", ["BTCUSDT"], 1.0)
    yan = ham.dosya_yolu(tmp_path / "ham" / "x1", "swing__a", "1d", "BTCUSDT").with_suffix(".json")
    m = json.loads(yan.read_text())
    yan.write_text(json.dumps({k: v for k, v in m.items() if k not in ham.DAMGA_ALANLARI}))     # v2 tarihsel biçim
    monkeypatch.delenv(ham.ESKI_ORTAM, raising=False)
    with pytest.raises(RuntimeError, match="kimlik damgası yok"):
        ham.ham_yukle(tmp_path, 1.0, "swing__a", "1d", ("BTCUSDT",), h)
    assert "BTCUSDT" in ham.ham_yukle(tmp_path, 1.0, "swing__a", "1d", ("BTCUSDT",), h, eski_kabul=True)[0]
    monkeypatch.setenv(ham.ESKI_ORTAM, "1")
    assert "BTCUSDT" in ham.ham_yukle(tmp_path, 1.0, "swing__a", "1d", ("BTCUSDT",), h)[0]


def test_b16_eleme_satiri_damgali_ve_uyusmazlik_reddedilir(tablo, tmp_path):
    y, h = tablo
    kripto = sabit.evren_listesi("kripto")
    hv, mh = _havuz_kur(tmp_path, [{"strateji": "swing__a", "stil_v2": "swing", "tf": "1d", "evren": "kripto"}])
    for c in (1.0, 2.0):
        _ham_yaz(tmp_path, h, "swing__a", "1d", kripto, c)
    eleme.eleme_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)
    satir = eleme._satir_yolu(tmp_path, "swing__a", "1d")
    s = json.loads(satir.read_text())
    assert set(ham.DAMGA_ALANLARI) <= set(s["kimlik"]) and s["kimlik"]["veri_sha256"]
    assert "kimlik" not in pd.read_csv(tmp_path / "eleme.csv").columns                    # csv şeması değişmedi
    satir.write_text(json.dumps(dict(s, kimlik=dict(s["kimlik"], motor_hash="1" * 64))))
    with pytest.raises(RuntimeError, match="motor_hash"):
        eleme.eleme_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)
