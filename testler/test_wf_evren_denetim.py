"""Denetim (2026-11-08) düzeltmeleri + ON_KAYIT Güncelleme 6: K2 tutma süresi (O1), holdout mührü/yazma kilidi (O3/Ö4),
sembol hatası sayımı (O4), DSR grup N/V ve bayatlık (Y1-a / O2), K4 evreni, deneme kaydı çift kaydı, bilgi sütunları (Ö3),
BIST kapı dışı (Güncelleme 6-C)."""
import json
import math
import shutil

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import saglamlik
from motor.arastirma import wf_evren as we
from motor.arastirma import wf_evren_holdout as wh
from motor.backtest import deneme_kaydi
from motor.strateji import funding
from testler.test_wf_evren import AD, _holdout_cikti, _maliyet_ve_gunluk, veri_dizini  # noqa: F401  (fikstürler)


# ============================================================================ O1: K2 tutma süresi = indeks konumu farkı
def _eski_tutma(idx, giris, cikis):
    aralik = pd.Series(idx).diff().median()
    return np.maximum(1, np.rint((pd.DatetimeIndex(cikis) - pd.DatetimeIndex(giris)) / aralik)).astype(int)


def _seansli_index(gun=40):
    """Hafta içi 09:00-15:00 saatlik 7 mum (hisse benzeri)."""
    gunler = pd.bdate_range("2023-01-02", periods=gun, tz="UTC")
    return pd.DatetimeIndex([g + pd.Timedelta(hours=h) for g in gunler for h in range(9, 16)], name="zaman")


def test_tutma_mum_kripto_ayni_seansli_dogru():
    idx = pd.date_range("2023-01-01", periods=2000, freq="1h", tz="UTC")
    rng = np.random.default_rng(0)
    g = rng.integers(0, 1900, 300)
    c = g + rng.integers(0, 90, 300)
    gi, ci = idx[g], idx[c]
    np.testing.assert_array_equal(saglamlik.tutma_mum(idx, gi, ci), _eski_tutma(idx, gi, ci))    # kripto: birebir
    s = _seansli_index()
    cuma_15 = s[(s.dayofweek == 4) & (s.hour == 15)][0]
    pzt_10 = s[(s > cuma_15) & (s.hour == 10)][0]
    assert saglamlik.tutma_mum(s, [cuma_15], [pzt_10])[0] == 2                 # cuma 15:00 -> pzt 10:00: 2 mum
    assert _eski_tutma(s, [cuma_15], [pzt_10])[0] == 67                        # eski: takvim saati (şişkin)
    # çıkış indekste yoksa ilk >= çıkış mumu; giriş yoksa hata
    assert saglamlik.tutma_mum(s, [cuma_15], [cuma_15 + pd.Timedelta(hours=20)])[0] == 1
    with pytest.raises(ValueError, match="giriş"):
        saglamlik.tutma_mum(s, [cuma_15 + pd.Timedelta(minutes=5)], [pzt_10])


def _k2_girdi(idx, n=15, adim=20, tut=9):
    oos = pd.DataFrame({"sembol": "X", "yon": [1, -1] * (n // 2) + [1] * (n % 2),
                        "giris_zamani": [idx[100 + adim * i] for i in range(n)],
                        "cikis_zamani": [idx[100 + adim * i + tut] for i in range(n)], "stop_mesafe": 1.5, "pencere": 0})
    return oos, [(idx[100], idx[100 + adim * n])]


def _mumlar(idx, tohum=1):
    rng = np.random.default_rng(tohum)
    kap = 100 * np.exp(np.cumsum(rng.normal(0, 0.006, len(idx))))
    ac = np.r_[kap[0], kap[:-1]]
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) * 1.002, "dusuk": np.minimum(ac, kap) * 0.998,
                         "kapanis": kap}, index=idx)


def test_rastgele_evren_kripto_regresyon_seansli_fark(monkeypatch):
    from motor.arastirma import evren_maliyet
    ay = evren_maliyet.maliyet_ayarlari("BTCUSDT", None)
    ortak = dict(n_sim=30, seed=5, tf="1h")
    # kripto (kesintisiz): yeni = eski formül, birebir
    idx = pd.date_range("2023-01-01", periods=900, freq="1h", tz="UTC")
    m = _mumlar(idx)
    oos, sinir = _k2_girdi(idx)
    yeni = we.rastgele_evren(oos, sinir, veri_al=lambda s: (m, ay), **ortak)
    monkeypatch.setattr(saglamlik, "tutma_mum", _eski_tutma)
    eski = we.rastgele_evren(oos, sinir, veri_al=lambda s: (m, ay), **ortak)
    np.testing.assert_array_equal(yeni["toplam_r"], eski["toplam_r"])
    # seanslı: eski formül tutma süresini şişirir -> farklı sonuç; yeni 9 mum tutar
    s = _seansli_index(130)
    ms = _mumlar(s, 2)
    oos_s, sinir_s = _k2_girdi(s)
    eski_s = we.rastgele_evren(oos_s, sinir_s, veri_al=lambda x: (ms, ay), **ortak)
    monkeypatch.undo()
    yeni_s = we.rastgele_evren(oos_s, sinir_s, veri_al=lambda x: (ms, ay), **ortak)
    assert not np.allclose(yeni_s["toplam_r"], eski_s["toplam_r"])
    assert (saglamlik.tutma_mum(s, oos_s["giris_zamani"], oos_s["cikis_zamani"]) == 9).all()


# ============================================================================ O3/Ö4: holdout mührü + yazma kilidi
def test_muhur_kapsami_ve_uyusmazlikta_dur(tmp_path, veri_dizini, monkeypatch):  # noqa: F811
    monkeypatch.setattr(we, "HOLDOUT_BAS", pd.Timestamp("2023-09-01", tz="UTC"))
    monkeypatch.setitem(we._EVREN_OVR, "swing", ("TESTUSDT",))
    cikti = _holdout_cikti(tmp_path)
    m = json.loads((cikti / wh.MUHUR).read_text())
    assert m["surum"] == 2 and set(m["dosyalar"]) == set(wh.MUHUR_DOSYALARI)
    assert {"wf_evren.parquet", "saglamlik.parquet", "pbo.csv"} <= set(m["dosyalar"]) and all(m["dosyalar"].values())
    assert m["olcut_hash"] == wh.olcut_hash()
    assert m["kosular"] == [{"liste": "iyi", "strateji": AD, "tf": "4h", "stil": "swing", "ayar": "varsayilan",
                             "dislanan": [], "gelistirme_pf": 1.3, "gelistirme_sharpe": 0.7}]
    dosyalar = m["strateji_hash"][AD]
    assert any(y.endswith(".py") and y.startswith("motor/strateji/") for y in dosyalar) and all(dosyalar.values())
    wh.muhur_kontrol(cikti)
    # (1) mühürlü girdi dosyaları değişirse DUR
    for f in ("wf_evren.parquet", "saglamlik.parquet", "pbo.csv"):
        yol = cikti / f
        eski = yol.read_bytes()
        yol.write_bytes(eski + b"\0")
        with pytest.raises(wh.HoldoutHatasi, match="değişmiş"):
            wh.holdout_asamasi(cikti, veri_dizini=veri_dizini)
        yol.write_bytes(eski)
    # (2) ölçüt/eşik değişirse DUR
    monkeypatch.setitem(we.OLCUT, "holdout_pf", 1.0)
    with pytest.raises(wh.HoldoutHatasi, match="ölçüt"):
        wh.muhur_kontrol(cikti)
    monkeypatch.setitem(we.OLCUT, "holdout_pf", 1.1)
    # (3) strateji kodu / kartı değişirse DUR
    gercek = wh.strateji_hashleri
    monkeypatch.setattr(wh, "strateji_hashleri", lambda k: {a: {**d, "motor/strateji/x.py": "ff"} for a, d in gercek(k).items()})
    with pytest.raises(wh.HoldoutHatasi, match="strateji kodu"):
        wh.muhur_kontrol(cikti)
    monkeypatch.setattr(wh, "strateji_hashleri", gercek)
    # (4) mühür dosyasındaki ayar elle değiştirilirse DUR
    m2 = {**m, "kosular": [{**m["kosular"][0], "ayar": "izgara:{}"}]}
    (cikti / wh.MUHUR).write_text(json.dumps(m2))
    with pytest.raises(wh.HoldoutHatasi, match="uyuşmuyor"):
        wh.muhur_kontrol(cikti)
    # (5) eski biçim mühür reddedilir
    (cikti / wh.MUHUR).write_text(json.dumps({"dosyalar": {f: m["dosyalar"][f] for f in wh.LISTE_DOSYALARI},
                                              "maliyet_hash": m["maliyet_hash"]}))
    with pytest.raises(wh.HoldoutHatasi, match="eski"):
        wh.muhur_kontrol(cikti)
    assert not wh.holdout_baslamis_mi(cikti)
    # holdout ayarı mühürden okunur
    (cikti / wh.MUHUR).write_text(json.dumps(m))
    df = wh.holdout_asamasi(cikti, veri_dizini=veri_dizini)
    assert df["ayar"].iloc[0] == "varsayilan" and df["hata"].iloc[0] == "" and df["n_hata_sembol"].iloc[0] == 0


def test_holdout_basladiysa_gelistirme_asamalari_yazmaz(tmp_path):
    from motor.arastirma import wf_evren_portfoy as wep
    from motor.arastirma import wf_evren_rapor
    cikti = tmp_path / "c"
    (cikti / "holdout").mkdir(parents=True)
    (cikti / wh.GUNLUK).write_text(json.dumps({"olay": "basladi"}) + "\n")
    for f in (lambda: we.wf_asamasi(cikti=cikti, ilerleme=False), lambda: we.saglamlik_asamasi(cikti=cikti, ilerleme=False),
              lambda: we.pbo_asamasi(cikti, ilerleme=False), lambda: we.olcut_asamasi(cikti),
              lambda: wep.pf_wf_asamasi(cikti, ilerleme=False), lambda: wf_evren_rapor.secim_ve_ozet(cikti),
              lambda: wh.muhur_yaz(cikti)):
        with pytest.raises(wh.HoldoutHatasi, match="holdout"):
            f()
    assert sorted(p.name for p in cikti.iterdir()) == ["holdout"]          # hiçbir şey yazılmadı


# ============================================================================ O4: sembol hataları sayılır
def _hatali_hazirla(monkeypatch, hatali: str, tur=RuntimeError) -> dict:
    """funding.stratejiye_hazirla'yı sarar: `hatali` sembolde ayar['tur'] istisnası (None: normal). -> ayar sözlüğü."""
    gercek = funding.stratejiye_hazirla
    ayar = {"tur": tur}

    def sahte(st, mumlar, fund, sembol, tf):
        if sembol == hatali and ayar["tur"] is not None:
            raise ayar["tur"](f"{sembol} bozuk")
        return gercek(st, mumlar, fund, sembol, tf)
    monkeypatch.setattr(funding, "stratejiye_hazirla", sahte)
    return ayar


@pytest.fixture
def iki_sembol(veri_dizini):  # noqa: F811
    shutil.copytree(veri_dizini / "TESTUSDT", veri_dizini / "BOSUSDT")
    return veri_dizini


def test_holdout_sembol_hatasi_sayilir_ve_satir_hata(tmp_path, iki_sembol, monkeypatch):
    monkeypatch.setattr(we, "HOLDOUT_BAS", pd.Timestamp("2023-09-01", tz="UTC"))
    monkeypatch.setitem(we._EVREN_OVR, "swing", ("TESTUSDT", "BOSUSDT"))
    we.veri_ayarla(iki_sembol, "holdout")
    temiz = wh.holdout_kos(AD, "4h", "swing", "varsayilan")
    assert temiz["n_hata_sembol"] == 0 and temiz["n_enstruman_veri"] == 2
    ayar = _hatali_hazirla(monkeypatch, "BOSUSDT")
    h = wh.holdout_kos(AD, "4h", "swing", "varsayilan")
    assert h["n_hata_sembol"] == 1 and "BOSUSDT" in h["hata_ornegi"] and "bozuk" in h["hata_ornegi"]
    # FundingYokHatasi: K-L beklenen, hata sayılmaz
    ayar["tur"] = funding.FundingYokHatasi
    h = wh.holdout_kos(AD, "4h", "swing", "varsayilan")
    assert h["n_hata_sembol"] == 0 and h["n_beklenen_hata"] == 1
    # holdout aşaması: sembol hatası -> durum 'hata'
    ayar["tur"] = None
    cikti = _holdout_cikti(tmp_path)
    ayar["tur"] = RuntimeError
    df = wh.holdout_asamasi(cikti, veri_dizini=iki_sembol)
    assert df["durum"].iloc[0] == "hata" and "sembol hatası" in df["hata"].iloc[0] and df["n_hata_sembol"].iloc[0] == 1
    assert wh.gunluk_oku(cikti)[-1]["hata"] == 1


def test_k4_sembol_hatasi_sayilir_ve_tum_sembol_hatasi_gecersiz(iki_sembol, monkeypatch):
    monkeypatch.setitem(we.DONEMLER, "test_tam", {"bas": None, "bit": None, "kilit_ac": True})
    we.veri_ayarla(iki_sembol, "test_tam")
    a, b = pd.Timestamp("2022-06-01", tz="UTC"), pd.Timestamp("2024-06-01", tz="UTC")
    r = we.komsu_evren_pf(AD, "varsayilan", "4h", ("TESTUSDT", "BOSUSDT"), a, b)
    assert r["par_n_hata_sembol"] == 0 and r["par_n_enstruman"] == 2 and r["par_n_gecerli"] > 0
    _hatali_hazirla(monkeypatch, "BOSUSDT")
    r = we.komsu_evren_pf(AD, "varsayilan", "4h", ("TESTUSDT", "BOSUSDT"), a, b)
    assert r["par_n_hata_sembol"] == 1 + r["par_n_gecerli"] and "BOSUSDT" in r["par_hata_ornegi"]
    # tek sembolde hata = tüm sembollerde: merkez ayar geçersiz -> açık ValueError (satır 'hata' olur)
    with pytest.raises(ValueError, match="tüm sembollerde"):
        we.komsu_evren_pf(AD, "varsayilan", "4h", ("BOSUSDT",), a, b)


def test_k4_wf_enstruman_listesi():
    w = {"kisa_gecmis": "HYPEUSDT", "disarida": "DK_COPPER,DK_WTI", "hatali_sembol": ""}
    ev = we.wf_enstrumanlari(w, "swing")
    assert "HYPEUSDT" not in ev and "DK_WTI" not in ev and "DK_COPPER" not in ev
    assert len(ev) == len(we.EVREN_GENEL) - 3 and ev == tuple(s for s in we.EVREN_GENEL if s in ev)


# ============================================================================ Güncelleme 6 (A) + O2: DSR grup N/V, bayatlık
def test_grup_dsr_parametreleri_ve_sutunlar():
    rng = np.random.default_rng(1)
    M = rng.normal(0, 0.01, (400, 30))
    M[:, 5] = 0.0                                                          # sabit sütun: sayılmaz
    n, v = we.grup_dsr_parametreleri(M)
    ok = np.delete(M, 5, axis=1)
    assert n == 29 and v == pytest.approx(np.var(ok.mean(0) / ok.std(0, ddof=1), ddof=1))
    n0, v0 = we.grup_dsr_parametreleri(np.zeros((400, 1)))
    assert n0 == 0 and math.isnan(v0)
    g = rng.normal(0.002, 0.01, 500)
    d = {"n": n, "v": v, "n_bilgi": 200000, "n_sembol": 5_000_000}
    s = we.dsr_sutunlari(g, d)
    assert s["dsr_deneme"] == pytest.approx(saglamlik.deflated_sharpe(g, n, v)["dsr"])
    assert s["dsr_bilgi"] < s["dsr_deneme"] and s["dsr_tanim"] == we.DSR_TANIM and s["dsr_n_deneme"] == n
    s0 = we.dsr_sutunlari(g, {**d, "v": math.nan})
    assert math.isnan(s0["dsr_deneme"]) and not we.saglamlik_oneri({"dsr_deneme": s0["dsr_deneme"]})[0]
    assert we.OLCUT["k5_dsr"] == 0.90 and we.YAKIN_OLCUT["k5_dsr"] == 0.50          # eşik değişmedi
    assert not we.dsr_bayat_mi(s, d) and we.dsr_bayat_mi(s, {**d, "n": n + 1}) and we.dsr_bayat_mi({**s, "dsr_tanim": None}, d)


def test_saglamlik_dsr_parametreleri_pbo_gerekir_ve_bayat_satir_tazelenir(tmp_path):
    cikti = tmp_path
    wf = pd.DataFrame([{"strateji": "pf__x", "stil": "portfoy", "tf": "1d", "n_aday": 10, "hata": "", "sharpe": 0.8}])
    with pytest.raises(RuntimeError, match="pbo"):
        we.dsr_parametreleri(cikti, wf)
    pd.DataFrame([{"stil": "portfoy", "tf": "1d", "pbo": 0.3}]).to_csv(cikti / "pbo.csv", index=False)
    with pytest.raises(RuntimeError, match="eski biçim"):
        we.dsr_parametreleri(cikti, wf)
    pd.DataFrame([{"stil": "portfoy", "tf": "1d", "pbo": 0.3, "dsr_n": 40, "dsr_v": 4e-4}]).to_csv(cikti / "pbo.csv", index=False)
    dp = we.dsr_parametreleri(cikti, wf)
    assert dp["grup"][("portfoy", "1d")] == {"n": 40, "v": 4e-4}
    (cikti / "pf").mkdir()
    g = np.random.default_rng(2).normal(0.003, 0.01, 600)
    pd.DataFrame({"oos_getiri": g}).to_parquet(cikti / "pf" / "pf__x--gunluk.parquet")
    iyi = {"m2_pf": 1.5, "m3_pf": 1.4, "g1_pf": 1.3, "rnd_p": 0.01, "pf_boot_alt": math.nan, "boot_sharpe_alt": 0.3,
           "par_oran": 0.9}
    onceki = pd.DataFrame([{"strateji": "pf__x", "stil": "portfoy", "tf": "1d", "hata": "", **iyi, "dsr_deneme": 0.1,
                            "dsr_n_deneme": 222807, "sr_varyans": 1e-3, "saglam_mi": False, "kapi_basarisiz": "K5_dsr"},
                           {"strateji": "pf__y", "stil": "portfoy", "tf": "1d", "hata": "boom", "dsr_deneme": 0.1,
                            "dsr_n_deneme": 1, "sr_varyans": 1.0, "saglam_mi": False, "kapi_basarisiz": "hata"}])
    yeni, n = we.dsr_tazele(onceki, wf, dp, cikti)
    beklenen = we.dsr_sutunlari(g, we.dsr_g(dp, "portfoy", "1d"))
    assert n == 1 and yeni.loc[0, "dsr_n_deneme"] == 40 and yeni.loc[0, "dsr_deneme"] == pytest.approx(beklenen["dsr_deneme"])
    assert yeni.loc[0, "saglam_mi"] == we.saglamlik_oneri(yeni.loc[0].to_dict())[0]
    assert yeni.loc[1, "dsr_n_deneme"] == 1                                 # hatalı satıra dokunulmaz
    assert we.dsr_tazele(yeni, wf, dp, cikti)[1] == 0                      # artık güncel
    # WF satırı yoksa açık hata
    with pytest.raises(RuntimeError, match="DSR tazeleme"):
        we.dsr_tazele(onceki, wf.iloc[0:0], dp, cikti)


# ============================================================================ deneme kaydı: çift kayıt yok, evren anahtarda
def test_evren_deneme_kaydi_cift_kayit_yok_evren_ayri(tmp_path):
    yol = tmp_path / "d.jsonl"
    # eski kayıtlar (imzasız): scalp 5m (4'lü evren) ve swing 4h (48'li evren)
    deneme_kaydi.kaydet("scalp__a", "evren", "5m", 12, 30, 12, yol)
    deneme_kaydi.kaydet("swing__b", "evren", "4h", 20, 9, 20, yol)
    s = {"strateji": "scalp__a", "tf": "5m", "n_aday": 12, "n_pencere": 30, "n_kosu": 12}
    assert not we.evren_deneme_kaydet(s, "2017_gelistirme", we.EVREN_SCALP, yol)       # aynı 4'lü evren: çift kayıt yok
    assert we.evren_deneme_kaydet(s, "2017_gelistirme", we.EVREN_GENEL, yol)           # 48'li evren: AYRI deneme
    assert not we.evren_deneme_kaydet(s, "2017_gelistirme", we.EVREN_GENEL, yol)       # ikinci kez yazılmaz
    assert we.evren_deneme_kaydet(s, "2020_gelistirme", we.EVREN_GENEL, yol)           # başka dönem: ayrı
    assert not we.evren_deneme_kaydet({**s, "strateji": "swing__b", "tf": "4h"}, "2017_gelistirme", we.EVREN_GENEL, yol)
    k = deneme_kaydi.oku(yol)
    assert len(k) == 4 and k[0] == {**k[0]} and "evren_imza" not in k[0]                # eski kayıtlar silinmedi/değişmedi
    assert k[2]["evren_imza"] == we.evren_imza(we.EVREN_GENEL) and k[2]["donem"] == "2017_gelistirme"
    assert we.evren_imza(we.EVREN_SCALP) != we.evren_imza(we.EVREN_GENEL) and we.evren_imza(we.EVREN_GENEL).startswith(f"{len(we.EVREN_GENEL)}:")
    with pytest.raises(ValueError, match="çakışıyor"):
        deneme_kaydi.kaydet("a", "b", "c", 1, 1, 1, yol, ek={"strateji": "x"})


# ============================================================================ Ö3: bilgi sütunları listelerde
def test_listelerde_bilgi_sutunlari_onde():
    wf = pd.DataFrame([{"strateji": "a", "stil": "swing", "tf": "4h", "gecti": True, "yakin_wf": True, "basarisiz_sayi": 0,
                        "sharpe": 1.0, "nedenler": "", "kill_olayi": 1, "gunluk_limit_olayi": 12, "red_toplam_risk": 3,
                        "red_kaldirac": 0, "red_gunluk": 5, "red_kill": 40, "net_bist": 0.02, "bist_short_payi": 0.4}])
    sag = pd.DataFrame([{"strateji": "a", "tf": "4h", "saglam_mi": True, "kapi_basarisiz": "", "rnd_p": 0.01, "m2_pf": 1.5,
                         "m3_pf": 1.4, "g1_pf": 1.3, "pf_boot_alt": 1.2, "par_oran": 0.9, "dsr_deneme": 0.95,
                         "dsr_bilgi": 0.4, "hata": ""}])
    iyi, _ = we.listeler(wf, sag, pd.DataFrame({"stil": ["swing"], "tf": ["4h"], "pbo": [0.2]}))
    for c in ("kill_olayi", "gunluk_limit_olayi", "red_toplam_risk", "red_kaldirac", "red_gunluk", "red_kill", "net_bist",
              "bist_short_payi", "dsr_bilgi"):
        assert c in iyi.columns[:30], c
    assert iyi["kill_olayi"].iloc[0] == 1 and len(iyi) == 1                       # kapı değil: kill olsa da iyi
    from motor.arastirma import wf_evren_rapor
    assert wf_evren_rapor._red(iyi.iloc[0].to_dict()) == "3/0/5/40"


# ============================================================================ Güncelleme 6 (C): BIST kapı dışı
def test_bist_genislik_kapisinda_sayilmaz():
    net = {"BTCUSDT": 0.10, "DK_AAPL": -0.02, "BIST_THYAO": 0.50, "BIST_AKBNK": 0.30}
    adet = {k: 10 for k in net}
    g = we.genislik_net(net, adet)
    assert g["n_enstruman_islemli"] == 2 and g["enstruman_kar_orani"] == 0.5
    assert g["n_sinif_kar"] == 1                                       # kripto; bist kâr etse de sayılmaz
    assert g["tek_enstruman_pay"] == pytest.approx(0.10 / 0.08) and g["en_buyuk_enstruman"] == "BTCUSDT"
    assert g["sinif_net"]["bist"] == pytest.approx(0.8) and g["bist_islem"] == 20 and g["bist_n_enstruman_kar"] == 2
    assert "BIST_THYAO" in g["enstruman_net"]                          # bilgi olarak duruyor
    # yeniden oynatma tablosundan BIST short payı
    tablo = pd.DataFrame({"sembol": ["BIST_THYAO", "BIST_THYAO", "BTCUSDT", "BIST_AKBNK"], "yon": [-1, 1, -1, -1]})
    m = we.genislik(tablo, [0, 1, 2, 3], {0: (0, 0.1), 1: (0, 0.1), 2: (0, 0.1), 3: (0, -0.1)})
    assert m["bist_short_payi"] == pytest.approx(2 / 3)


def test_genislik_yeniden_degerlendir_bist_ile_gecen_kalir():
    satir = {"strateji": "a", "stil": "swing", "tf": "4h", "hata": "", "net_getiri": 0.5, "profit_factor": 1.5,
             "islem_sayisi": 300, "pf_en_iyi5_haric": 1.1, "sharpe": 0.9, "max_dusus": 0.1,
             "enstruman_net": json.dumps({"BTCUSDT": 0.05, "ETHUSDT": 0.04, "DK_AAPL": -0.01, "BIST_THYAO": 0.4}),
             "enstruman_adet": json.dumps({"BTCUSDT": 5, "ETHUSDT": 5, "DK_AAPL": 5, "BIST_THYAO": 5}),
             "gecti": True, "yakin_wf": True, "nedenler": "", "enstruman_kar_orani": 0.75, "n_sinif_kar": 2,
             "tek_enstruman_pay": 0.83}
    pf = {"strateji": "pf__x", "stil": "portfoy", "tf": "1d", "hata": "", "gecti": True, "yakin_wf": True, "nedenler": "",
          "enstruman_net": "{}"}
    d = we.genislik_yeniden_degerlendir(pd.DataFrame([satir, pf]))
    r = d.iloc[0]
    assert r["gecti_g5"] == True and r["gecti"] == False and r["n_sinif_kar"] == 1        # noqa: E712  (BIST olmadan 1 sınıf)
    assert "kârlı sınıf" in r["nedenler"] and r["bist_islem"] == 5
    assert d.iloc[1]["gecti"] == True and d.iloc[1]["gecti_g5"] == True                     # noqa: E712  portföye dokunulmaz
    d2 = we.genislik_yeniden_degerlendir(d)                                                  # idempotent, eski karar korunur
    assert d2.iloc[0]["gecti_g5"] == True and d2.iloc[0]["gecti"] == False                  # noqa: E712


def test_saglamlik_asamasi_grup_dsr_gorevi_tazeleme_ve_hata_isareti(tmp_path, monkeypatch):
    cikti = tmp_path
    wf = pd.DataFrame([{"strateji": s_, "stil": "portfoy", "tf": "1d", "n_aday": 10, "hata": "", "sharpe": 0.8,
                        "gecti": True, "yakin_wf": True} for s_ in ("pf__x", "pf__y")])
    wf.to_parquet(cikti / "wf_evren.parquet")
    pd.DataFrame([{"stil": "portfoy", "tf": "1d", "pbo": 0.3, "dsr_n": 40, "dsr_v": 4e-4}]).to_csv(cikti / "pbo.csv", index=False)
    (cikti / "pf").mkdir()
    for s_ in ("pf__x", "pf__y"):
        pd.DataFrame({"oos_getiri": np.random.default_rng(3).normal(0.002, 0.01, 500)}).to_parquet(cikti / "pf" / f"{s_}--gunluk.parquet")
    pd.DataFrame([{"strateji": "pf__x", "stil": "portfoy", "tf": "1d", "hata": "", "dsr_deneme": 0.1, "dsr_n_deneme": 9,
                   "sr_varyans": 1.0, "saglam_mi": False, "kapi_basarisiz": "K5_dsr"}]).to_parquet(cikti / "saglamlik.parquet")
    gorulen = []

    def sahte_havuz(isci, gorevler, *a, **k):
        gorulen.extend(gorevler)
        return [{"strateji": g["strateji"], "stil": g["stil"], "tf": g["tf"], "hata": "", **we.dsr_sutunlari(g["getiri"], g["dsr"])}
                for g in gorevler]
    monkeypatch.setattr(we, "havuz_calistir", sahte_havuz)
    o = we.saglamlik_asamasi(cikti=cikti, ilerleme=False)
    assert o["dsr_tazelenen"] == 1 and o["yeni"] == 1 and [g["strateji"] for g in gorulen] == ["pf__y"]
    assert gorulen[0]["dsr"]["n"] == 40 and gorulen[0]["dsr"]["v"] == 4e-4
    sag = pd.read_parquet(cikti / "saglamlik.parquet")
    assert (sag["dsr_n_deneme"] == 40).all() and (sag["dsr_tanim"] == we.DSR_TANIM).all()
    assert sag.loc[sag["strateji"] == "pf__y", "wf_sha"].iloc[0] == we._dosya_sha(cikti / "wf_evren.parquet")
    # _sag_isci: içerik satıra 'hata' yazdıysa (ör. K4 sembol hatası) sağlam sayılmaz
    def icerik(g, satir):
        satir.update({"m2_pf": 2, "m3_pf": 2, "g1_pf": 2, "rnd_p": 0.0, "pf_boot_alt": 2, "par_oran": 1, "dsr_deneme": 1,
                      "hata": "K4 komşu ayar: 1 sembol hatası"})
    monkeypatch.setattr(we, "_sag_icerik", icerik)
    r = we._sag_isci({"strateji": "a", "stil": "swing", "tf": "4h"})
    assert r["saglam_mi"] is False and r["kapi_basarisiz"] == "hata"
