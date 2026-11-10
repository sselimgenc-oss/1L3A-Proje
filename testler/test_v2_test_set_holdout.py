"""v2 test / sağlamlık / set / mühür / holdout (ON_KAYIT_V2 bölüm 5, 6, 7, 11 kabul testleri). Yalnız SENTETİK veri.
Gerçek holdout verisi ASLA okunmaz: holdout testleri sentetik `HoldoutSaglayici` kullanır."""
from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import evren_k2, evren_maliyet
from motor.arastirma import wf_evren as we
from motor.arastirma.v2 import eleme, ham, holdout, kasa, maliyet, rejim, sabit, saglamlik, spa
from motor.arastirma.v2 import set as setm
from motor.arastirma.v2 import test as k2
from motor.backtest.motor import MotorAyarlari
from testler.test_v2_ham_eleme import _ham_yaz, _havuz_kur, sentetik

KOK = Path(__file__).resolve().parents[1]
V2 = KOK / "motor" / "arastirma" / "v2"
EVREN = sabit.evren_listesi("kripto")


# ------------------------------------------------------------------ yardımcılar
@pytest.fixture()
def tablo(tmp_path):
    y = maliyet.tabloyu_hazirla(tmp_path)
    return y, evren_maliyet.tablo_hash(y)


def mumlar_uzun(n=3200, seed=11):
    return sentetik(n=n, seed=seed, bas="2017-06-01")


class SentetikStub:
    """test.tek_satir_baglam yerine: sentetik mumlar + boş çıkış kuralları."""

    def __init__(self, n=3200):
        self.mumlar = {s: mumlar_uzun(n, seed=20 + i) for i, s in enumerate(EVREN)}

    def __call__(self, ad, tf, tablo_yolu):
        def veri_al(s):
            return self.mumlar[s], MotorAyarlari()

        def cikis_al(s):
            n = len(self.mumlar[s])
            z = np.zeros(n, dtype=bool)
            return {"ex_long": z, "ex_short": z, "hedef_r": math.nan, "iz_k": None, "iz_periyot": 14, "be_r": None, "desteklenmeyen": []}
        return veri_al, cikis_al, []


def _mtm_yaz(cikti, ad, tf, semboller, carpan=1.0):
    hd = cikti / "ham" / ham.carpan_adi(carpan)
    md = cikti / "mtm" / ham.carpan_adi(carpan)
    for s in semboller:
        h = pd.read_parquet(ham.dosya_yolu(hd, ad, tf, s))
        no, gun, kum = [], [], []
        for i, (g, c, r) in enumerate(zip(h["giris_zamani"], h["cikis_zamani"], h["r"])):
            gunler = pd.date_range(g.floor("D"), c.floor("D"), freq="D")
            for k, d in enumerate(gunler):
                no.append(i)
                gun.append(d)
                kum.append(float(r) * (k + 1) / len(gunler))
        df = pd.DataFrame({"islem_no": np.array(no, dtype=np.int32), "gun": pd.DatetimeIndex(gun).as_unit("ns"),
                           "kum_r": np.array(kum, dtype=np.float32)})
        ham._yaz_atomik(df, ham.dosya_yolu(md, ad, tf, s))


def _satir(ad, etiket="trend", alt="x", kume=1, stil="swing", tf="1d", evren="kripto"):
    return {"strateji": ad, "stil_v2": stil, "tf": tf, "evren": evren, "etiket": etiket, "alt_etiket": alt, "kume_no": kume,
            "kilit_gorulmus": "hayir"}


# ================================================================== 0.4 / 1: holdout ve sabit kaynağı
def test_gelistirme_modulleri_holdout_ve_kilit_ac_icermez():
    """v2 modüllerinin yalnız holdout.py'si 'holdout' dönemini açar; hiçbiri kilit_ac vermez."""
    kirli = []
    for f in sorted(V2.glob("*.py")):
        t = ast.parse(f.read_text())
        for n in ast.walk(t):
            if isinstance(n, ast.keyword) and n.arg == "kilit_ac":
                kirli.append((f.name, n.lineno, "kilit_ac"))
            if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "veri_ayarla":
                for a in n.args[1:] + [k.value for k in n.keywords]:
                    if isinstance(a, ast.Constant) and a.value == "holdout" and f.name != "holdout.py":
                        kirli.append((f.name, n.lineno, "holdout donemi"))
    assert not kirli, kirli
    assert "veri_ayarla(None, \"holdout\")" in (V2 / "holdout.py").read_text()


def test_gelistirme_asamalari_yalniz_gelistirme_donemi_acar(tablo, tmp_path, monkeypatch):
    y, h = tablo
    cagrilar = []
    monkeypatch.setattr(we, "veri_ayarla", lambda d=None, donem="kilit_oncesi": cagrilar.append(donem))
    for modul in (k2, saglamlik):
        modul._baslat({"veri_dizini": None, "tablo_yolu": str(y), "cikti": str(tmp_path)})
    assert cagrilar == [sabit.DONEM, sabit.DONEM] and "holdout" not in cagrilar


def test_gercek_saglayici_yetkisiz_kurulamaz_ve_pytest_altinda_holdout_kapali(tmp_path, monkeypatch):
    def yasak(*a, **k):
        raise AssertionError("holdout verisi açıldı")
    monkeypatch.setattr(we, "veri_ayarla", yasak)
    with pytest.raises(holdout.HoldoutHatasi, match="yalnız holdout_asamasi"):
        holdout.GercekSaglayici(tmp_path / "t.csv")
    with pytest.raises(holdout.HoldoutHatasi, match="testler gerçek holdout"):
        holdout.holdout_asamasi(tmp_path)                       # sağlayıcı yok: gerçek veriye gidecekti -> kapalı


# ================================================================== 5.1 K2 çekirdeği
def _kur_k2(n=900, seed=5, n_islem=12, tutma=4, mult=2.0, rng_seed=0):
    from motor.strateji import gostergeler as gst
    m = sentetik(n=n, seed=seed, bas="2019-01-01")
    atr = gst.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14).to_numpy(float)
    rng = np.random.default_rng(rng_seed)
    j = np.sort(rng.choice(np.arange(100, n - 20), n_islem, replace=False))
    yon = rng.choice([-1, 1], n_islem)
    d = pd.DataFrame({"giris_zamani": m.index[j].as_unit("ns"), "cikis_zamani": m.index[j + tutma].as_unit("ns"), "yon": yon.astype(np.int8),
                      "r": np.zeros(n_islem), "sf": 0.05, "stop_mesafe": mult * atr[j - 1]})
    return m, atr, d, j


def test_k2_rastgele_giris_ayni_enstruman_yon_ceyrek_ve_cikis_kurallari(monkeypatch):
    m, atr, d, j = _kur_k2()
    n = len(m)
    ex_l, ex_s = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
    ex_l[::7] = True
    ci = {"ex_long": ex_l, "ex_short": ex_s, "hedef_r": 2.0, "iz_k": None, "iz_periyot": 14, "be_r": None, "desteklenmeyen": []}
    cagrilar = []
    gercek = evren_k2.tek_islem_r

    def kaydet(o, h, l, c, atr_, jj, yon, hm_, mult, kayma, skayma, taker, **kw):
        cagrilar.append((jj, yon, hm_, mult, kw))
        return gercek(o, h, l, c, atr_, jj, yon, hm_, mult, kayma, skayma, taker, **kw)
    monkeypatch.setattr(evren_k2, "tek_islem_r", kaydet)
    toplam, gec, ni = k2._sembol_k2(d, m, MotorAyarlari(), ci, 50, np.random.default_rng(1))
    assert len(toplam) == 50 and ni == 50 * len(d) and cagrilar
    gercek_ceyrek = {(m.index[jj].year, m.index[jj].quarter) for jj in j}
    for jj, yon, hm_, mult, kw in cagrilar:
        assert (m.index[jj].year, m.index[jj].quarter) in gercek_ceyrek       # çeyrek içinde
        assert mult == pytest.approx(2.0, rel=1e-6)                           # stop/ATR katı korunur
        assert kw["hedef_r"] == 2.0 and kw["iz_k"] is None and kw["be_r"] is None
        assert kw["ex"] is (ex_l if yon == 1 else ex_s)                       # stratejinin KENDİ çıkış sinyalleri
    # her işlem için yön korunur: yön sayıları gerçek yön sayılarıyla çeyrek bazında uyumlu
    yon_say = {1: int((d["yon"] == 1).sum()), -1: int((d["yon"] == -1).sum())}
    assert {y: sum(1 for c_ in cagrilar if c_[1] == y) > 0 for y in yon_say} == {y: v > 0 for y, v in yon_say.items()}


def test_ceyrek_sinirlari_ve_holdout_kesmesi():
    gi = pd.DatetimeIndex(["2025-11-20", "2025-02-14"], tz="UTC")
    bas, bit = k2.ceyrek_sinirlari(gi)
    assert bas[0] == pd.Timestamp("2025-10-01", tz="UTC") and bit[0] == pd.Timestamp("2026-01-01", tz="UTC")
    assert bas[1] == pd.Timestamp("2025-01-01", tz="UTC") and bit[1] == pd.Timestamp("2025-04-01", tz="UTC")
    bas2, _ = k2.ceyrek_sinirlari(gi, alt_sinir=sabit.HOLDOUT_BAS)           # holdout sınırını aşan çeyrek kesilir
    assert bas2[0] == sabit.HOLDOUT_BAS and bas2[1] == sabit.HOLDOUT_BAS


def test_k2_onbellekli_yol_naif_dongu_ile_ayni_p(monkeypatch):
    """Çekim stratejisi (ilk geçerli çekim) naif döngüyle birebir: bağımsız yeniden hesapla."""
    m, atr, d, j = _kur_k2(n_islem=5, rng_seed=3)
    ci = {"ex_long": np.zeros(len(m), dtype=bool), "ex_short": np.zeros(len(m), dtype=bool), "hedef_r": math.nan, "iz_k": None,
          "iz_periyot": 14, "be_r": None, "desteklenmeyen": []}
    ay = MotorAyarlari()
    t1, _, _ = k2._sembol_k2(d, m, ay, ci, 40, np.random.default_rng(9))
    # naif: aynı rng akışı, işlem işlem, çekim çekim
    rng = np.random.default_rng(9)
    o, h, l, c = (m[k].to_numpy(float) for k in ("acilis", "yuksek", "dusuk", "kapanis"))
    idx, n = m.index, len(m)
    from motor.arastirma import saglamlik as v1s
    hm_ = v1s.tutma_mum(idx, d["giris_zamani"], d["cikis_zamani"])
    qb, qe = k2.ceyrek_sinirlari(d["giris_zamani"])
    top = np.zeros(40)
    for k in range(len(d)):
        lo = max(1, int(idx.searchsorted(qb[k])))
        hi = min(int(idx.searchsorted(qe[k])), n - int(hm_[k]))
        if hi <= lo:
            hi = lo + 1
        u = rng.random((40, sabit.K2_YENIDEN_CEKIM))
        for b in range(40):
            for e in range(sabit.K2_YENIDEN_CEKIM):
                jj = min(max(int(lo + u[b, e] * (hi - lo)), 1), n - 2)
                r = evren_k2.tek_islem_r(o, h, l, c, atr, jj, int(d["yon"].iloc[k]), min(int(hm_[k]), n - 1 - jj),
                                         float(d["stop_mesafe"].iloc[k] / atr[int(idx.get_loc(d["giris_zamani"].iloc[k])) - 1]),
                                         ay.kayma_bps / 1e4, ay.stop_kayma_bps / 1e4, ay.komisyon_taker_yuzde / 100,
                                         ex=ci["ex_long"], hedef_r=math.nan, iz_k=None, iz_atr=None, be_r=None)
                if r is not None and np.isfinite(atr[jj - 1]):
                    top[b] += r
                    break
    np.testing.assert_allclose(t1, top, rtol=0, atol=1e-9)


def test_k2_avantajsiz_stratejide_p_tekduze_ks():
    """Gerçek işlemler de aynı çeyrek-rastgele süreçten gelirse p ~ U(0,1) (KS, 400 tohum)."""
    from motor.strateji import gostergeler as gst
    m = sentetik(n=900, seed=5, bas="2019-01-01")
    atr = gst.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14).to_numpy(float)
    o, h, l, c = (m[k].to_numpy(float) for k in ("acilis", "yuksek", "dusuk", "kapanis"))
    ay = MotorAyarlari()
    ci = {"ex_long": np.zeros(len(m), dtype=bool), "ex_short": np.zeros(len(m), dtype=bool), "hedef_r": math.nan, "iz_k": None,
          "iz_periyot": 14, "be_r": None, "desteklenmeyen": []}
    q = m.index.to_period("Q")
    n = len(m)
    ps = []
    for tohum in range(400):
        rng = np.random.default_rng(1000 + tohum)
        j = np.sort(rng.choice(np.arange(100, n - 20), 12, replace=False))
        yon = rng.choice([-1, 1], 12)
        r = []
        for jj, y in zip(j, yon):
            lo = int(m.index.searchsorted(q[jj].start_time.tz_localize("UTC")))
            hi = int(m.index.searchsorted((q[jj] + 1).start_time.tz_localize("UTC")))
            jr = int(rng.integers(max(lo, 1), min(hi, n - 5)))                    # gerçek giriş: aynı çeyrekte rastgele
            r.append(evren_k2.tek_islem_r(o, h, l, c, atr, jr, int(y), 4, 2.0, ay.kayma_bps / 1e4, ay.stop_kayma_bps / 1e4,
                                          ay.komisyon_taker_yuzde / 100, ex=ci["ex_long"], hedef_r=math.nan))
        jg = np.array([int(rng.integers(max(int(m.index.searchsorted(q[jj].start_time.tz_localize("UTC"))), 1),
                                        min(int(m.index.searchsorted((q[jj] + 1).start_time.tz_localize("UTC"))), n - 5)))
                       for jj in j])
        d = pd.DataFrame({"giris_zamani": m.index[jg].as_unit("ns"), "cikis_zamani": m.index[jg + 4].as_unit("ns"), "yon": yon.astype(np.int8),
                          "r": 0.0, "stop_mesafe": 2.0 * atr[jg - 1]})
        T = 0.0
        for jj, y in zip(jg, yon):
            rr = evren_k2.tek_islem_r(o, h, l, c, atr, int(jj), int(y), 4, 2.0, ay.kayma_bps / 1e4, ay.stop_kayma_bps / 1e4,
                                      ay.komisyon_taker_yuzde / 100, ex=ci["ex_long"], hedef_r=math.nan)
            T += 0.0 if rr is None else rr
        sim, _, _ = k2._sembol_k2(d, m, ay, ci, 100, np.random.default_rng(7000 + tohum))
        ps.append(k2.p_degeri(T, sim))
    x = np.sort(np.array(ps))
    ks = float(np.max(np.maximum(np.arange(1, 401) / 400 - x, x - np.arange(0, 400) / 400)))
    assert ks < 0.09, ks                                                          # KS 5% kritik ≈ 0.068 (+ ayrık p payı)
    assert abs(float(np.mean(ps)) - 0.5) < 0.06 and float(np.mean(np.array(ps) <= 0.05)) < 0.09


# ================================================================== 5.3 iki aşama
def _ctx(sim_fn, T=10.0):
    return {"gercek": {"S": pd.DataFrame({"giris_zamani": [], "r": []})}, "veri_al": None, "cikis_al": None, "destek_yok": []}


def _satir_test_kos(tmp_path, monkeypatch, sims_by_tohum, tf="1d", T=10.0):
    """k2_simule ve toplam_r taklit edilir: aşama başına (n_sim, tohum) kaydedilir, simülasyon dizisi sims_by_tohum[aşama]."""
    cagri = []

    def sahte(islemler, veri_al, cikis_al, n_sim, tohum, alt_sinir=None, kismi_dizin=None):
        asama = "k2a" if tohum == sabit.satir_tohumu("a", tf, "k2a") else "k2b"
        cagri.append((asama, n_sim, tohum))
        return {"toplam_r": sims_by_tohum[asama](n_sim), "n_gecersiz": 0, "n_islem": 5}
    monkeypatch.setattr(k2, "k2_simule", sahte)
    monkeypatch.setattr(k2, "toplam_r", lambda i: T)
    ctx = {"gercek": {"S": pd.DataFrame({"giris_zamani": [], "r": []})}, "veri_al": None, "cikis_al": None, "destek_yok": []}
    row = _satir("a", tf=tf)
    s = k2.satir_test(row, tmp_path, "x", "h", None, _ctx=ctx)
    return s, cagri


def test_iki_asama_p_kucukse_ikinci_asama_yeni_tohumla_ve_nihai_yalniz_ikinciden(tmp_path, monkeypatch):
    s, cagri = _satir_test_kos(tmp_path, monkeypatch, {
        "k2a": lambda n: np.zeros(n),                       # hepsi T'nin altında -> p1 = 1/501 <= 0.02
        "k2b": lambda n: np.r_[np.full(n // 2, 100.0), np.zeros(n - n // 2)]})  # yarısı >= T
    assert [c[0] for c in cagri] == ["k2a", "k2b"]
    assert cagri[0][1] == sabit.K2_B1 and cagri[1][1] == sabit.K2_B2["1d"]
    assert cagri[0][2] != cagri[1][2] and cagri[1][2] == sabit.satir_tohumu("a", "1d", "k2b")
    assert s["p1"] == pytest.approx(1 / 501)
    assert s["p"] == s["p2"] == pytest.approx((1 + sabit.K2_B2["1d"] // 2) / (sabit.K2_B2["1d"] + 1)) and s["asama"] == 2
    assert s["p"] > 0.4                                     # 1. aşamanın küçük p'si nihai p'ye karışmaz


def test_iki_asama_p_buyukse_ikinci_asama_kosmaz(tmp_path, monkeypatch):
    s, cagri = _satir_test_kos(tmp_path, monkeypatch, {"k2a": lambda n: np.full(n, 100.0), "k2b": lambda n: np.zeros(n)})
    assert [c[0] for c in cagri] == ["k2a"] and s["asama"] == 1 and s["p"] == s["p1"] == 1.0 and math.isnan(s["p2"])


def test_p_siniri_tam_002_ikinci_asamaya_gecer_0021_gecmez(tmp_path, monkeypatch):
    # B=500: p = (1 + k)/501 ; k=9 -> 0.01996 (<=0.02) geçer; k=10 -> 0.02196 geçmez
    for k, beklenen in ((9, 2), (10, 1)):
        d = tmp_path / f"k{k}"
        s, cagri = _satir_test_kos(d, monkeypatch, {"k2a": lambda n, k=k: np.r_[np.full(k, 100.0), np.zeros(n - k)], "k2b": lambda n: np.zeros(n)})
        assert s["asama"] == beklenen


def test_15m_ikinci_asama_5000():
    assert k2.b_ikinci("15m") == 5000 and k2.b_ikinci("1d") == 10000 and k2.b_ikinci("4h") == 10000


def test_butce_dolunca_ikinci_asama_baslamaz_ve_devam_eder(tmp_path, monkeypatch):
    import time
    cagri = []

    def sahte(islemler, veri_al, cikis_al, n_sim, tohum, alt_sinir=None, kismi_dizin=None):
        cagri.append(n_sim)
        return {"toplam_r": np.zeros(n_sim), "n_gecersiz": 0, "n_islem": 1}
    monkeypatch.setattr(k2, "k2_simule", sahte)
    monkeypatch.setattr(k2, "toplam_r", lambda i: 10.0)
    ctx = {"gercek": {"S": pd.DataFrame({"giris_zamani": [], "r": []})}, "veri_al": None, "cikis_al": None, "destek_yok": []}
    row = _satir("a")
    # 1. aşama bitince bütçe dolmuş sayılır (son = geçmiş): 2. aşama ertelenir, 1. aşama diske yazılmıştır
    ilk = k2.satir_test(row, tmp_path, "x", "h", time.time() + 1e6, _ctx=ctx)
    assert ilk["asama"] == 2
    d = tmp_path / "y"
    monkeypatch.setattr(k2, "k2_simule", lambda *a, **k: (cagri.append(a[3]) or {"toplam_r": np.zeros(a[3]), "n_gecersiz": 0, "n_islem": 1}))
    sayac = {"n": 0}
    gercek_time = time.time

    def zaman():                      # 1. aşamadan sonraki ilk kontrolde bütçe doldu
        sayac["n"] += 1
        return gercek_time() + (1e7 if sayac["n"] > 1 else 0.0)
    monkeypatch.setattr(k2.time, "time", zaman)
    e = k2.satir_test(row, d, "x", "h", gercek_time() + 100, _ctx=ctx)
    assert e.get("ertelendi") and json.loads(k2.satir_yolu(d, "a", "1d").read_text())["a1"]["B"] == sabit.K2_B1
    monkeypatch.setattr(k2.time, "time", gercek_time)
    n_once = len(cagri)
    son = k2.satir_test(row, d, "x", "h", None, _ctx=ctx)
    assert son["asama"] == 2 and cagri[n_once:] == [sabit.K2_B2["1d"]]          # yalnız eksik 2. aşama koşuldu


def test_desteklenmeyen_cikis_modulu_p1(tmp_path):
    ctx = {"gercek": {}, "veri_al": None, "cikis_al": None, "destek_yok": ["kismi"]}
    s = k2.satir_test(_satir("a"), tmp_path, "x", "h", None, _ctx=ctx)
    assert s["p"] == 1.0 and s["durum"] == "rnd_desteklenmeyen" and s["rnd_desteklenmeyen"] == "kismi"


def test_holdout_sizintisi_yutulmaz(tmp_path, monkeypatch):
    def patlat(*a, **k):
        raise ham.HoldoutSizintisi("x")
    monkeypatch.setattr(k2.hm, "ham_yukle", patlat)
    with pytest.raises(ham.HoldoutSizintisi):
        k2.satir_test(_satir("a"), tmp_path, "x", "h", None)


# ================================================================== 5.4 BH / BY
def test_bh_elle_hesap_ve_alfabetik_esitlik():
    p = {"a": 1e-5, "b": 2e-4, "c": 3.2e-4, "d": 5e-4, "e": 0.9}
    r = k2.bh_kesif(p, 939)
    # eşikler 0.1 k / 939: 1.065e-4, 2.13e-4, 3.195e-4, 4.26e-4, 5.3e-4  -> a,b ✓ ; c: 3.2e-4 > 3.195e-4 ✗ ; d ✗ ; e ✗
    assert r["k_yildiz"] == 2 and r["kesif"] == ["a", "b"]
    # alfabetik eşitlik: aynı p, sıra alfabetik
    r3 = k2.bh_kesif({"b": 1e-5, "a": 1e-5, "c": 0.5}, 939)
    assert r3["sira"]["a"] == 1 and r3["sira"]["b"] == 2


def test_bh_step_up_ve_m_etkisi():
    # m=939: eşik_k = 1.0649e-4 k. p = [5e-5, 2.1e-4, 3.0e-4]: k=3 eşik 3.195e-4 >= 3.0e-4 -> k*=3 (step-up: k=2 geçtiği için de)
    r = k2.bh_kesif({"a": 5e-5, "b": 2.1e-4, "c": 3.0e-4}, 939)
    assert r["k_yildiz"] == 3
    # m=1000'de eşikler daha küçük: 1e-4 k -> k=3 eşik 3e-4 >= 3.0e-4 hâlâ geçer; m=1100: 2.727e-4 -> k=3 ✗, k=2 eşik 1.8e-4 < 2.1e-4 ✗, k=1 ✓
    assert k2.bh_kesif({"a": 5e-5, "b": 2.1e-4, "c": 3.0e-4}, 1100)["k_yildiz"] == 1
    with pytest.raises(ValueError):
        k2.bh_kesif({"a": 0.1, "b": 0.2}, 1)
    assert k2.bh_kesif({"a": 0.5}, 939)["k_yildiz"] == 0


def test_by_esigi_harmonik_toplamla_bolunur():
    p = {f"s{i}": 1e-4 * (i + 1) for i in range(5)}
    bh = k2.bh_kesif(p, 939)
    by = k2.by_kesif(p, 939)
    c = sum(1 / j for j in range(1, 940))
    assert by["c_m"] == pytest.approx(c) and by["k_yildiz"] <= bh["k_yildiz"]


def test_m_havuz_muhrunden_okunur(tablo, tmp_path):
    y, h = tablo
    kripto = sabit.evren_listesi("kripto")
    hv, mh = _havuz_kur(tmp_path, [_satir("iyi")])
    j = json.loads(mh.read_text())
    j["m"] = 1234
    mh.write_text(json.dumps(j))
    d = pd.DataFrame([{"strateji": "iyi", "tf": "1d", "durum": "elendi"}]).set_index(["strateji", "tf"])
    havuz = pd.read_csv(hv)
    (tmp_path / "eleme.csv").write_text("x\n")
    o = k2.rapor_yaz(tmp_path, havuz, d, j, h)
    assert o["m"] == 1234
    t = pd.read_csv(tmp_path / "test.csv")
    assert t.loc[0, "p"] == 1.0 and t.loc[0, "bh_esik"] == pytest.approx(0.1 / 1234)


# ================================================================== 5.2 portföy rastgele ağırlık
def test_pf_k2_simulatoru_tohum_devam_ve_p(tmp_path):
    kayit = []

    def sim(b, tohum):
        kayit.append((b, tohum))
        return float(np.random.default_rng([tohum, b]).normal())
    tam = k2.pf_k2_simule("pf__x", "genel", None, None, 60, 123, None, sim)
    assert tam.shape == (60,) and not np.isnan(tam).any()
    # kesilen koşu: 30. simülasyonda patla, kısmi diske yazıldı; yeniden çalıştırınca kalan sürer ve sonuç aynı
    kd = tmp_path / "kismi"
    ilk = []

    def patlayan(b, tohum):
        if b == 30 and not ilk:
            ilk.append(1)
            raise KeyboardInterrupt
        return sim(b, tohum)
    with pytest.raises(KeyboardInterrupt):
        k2.pf_k2_simule("pf__x", "genel", None, None, 60, 123, kd, patlayan)
    assert len(np.load(kd / "sharpe.npy")) == 25            # PF_KAYIT_BLOK=25 -> son tam blok kayıtlı
    devam = k2.pf_k2_simule("pf__x", "genel", None, None, 60, 123, kd, patlayan)
    np.testing.assert_array_equal(devam, tam)
    assert k2.p_degeri(1.0, tam) == pytest.approx((1 + (tam >= 1.0).sum()) / 61)


# ================================================================== 5.5 SPA
def test_spa_gurultude_buyuk_p_gucluyde_kucuk_p():
    gun = pd.date_range("2018-01-01", periods=1200, freq="D", tz="UTC")
    rng = np.random.default_rng(1)
    gurultu = {f"g{i}": pd.Series(rng.normal(0, 0.01, len(gun)), index=gun) for i in range(8)}
    r0 = spa.hansen_spa(gurultu, tohum=7, n_cekim=400)
    assert r0["p"] > 0.10 and r0["n_model"] == 8
    guclu = dict(gurultu)
    guclu["iyi"] = pd.Series(rng.normal(0.004, 0.01, len(gun)), index=gun)
    r1 = spa.hansen_spa(guclu, tohum=7, n_cekim=400)
    assert r1["p"] < 0.05 and r1["en_iyi"] == "iyi"
    assert spa.hansen_spa(guclu, tohum=7, n_cekim=400) == r1        # deterministik


def test_durgan_bootstrap_blok_ortalamasi():
    rng = np.random.default_rng(0)
    idx = next(spa.durgan_indeks(5000, 20, 40, rng))
    atlama = (np.diff(idx, axis=1) % 5000 != 1).mean()
    assert 0.03 < atlama < 0.08                                       # ≈ 1/20


# ================================================================== 6.1 S1-S4
def test_s1_siniri():
    assert saglamlik.s1_karar(1.0) and not saglamlik.s1_karar(0.999) and not saglamlik.s1_karar(math.nan)


def test_s2_sinirlari():
    assert saglamlik.s2_karar([1.1, 1.1, 1.1])["gecti"]                            # medyan 1.1 geçer
    assert not saglamlik.s2_karar([1.099, 1.099, 1.099])["gecti"]                  # 1.099 kalır
    assert saglamlik.s2_karar([0.9, 1.2, 1.2])["gecti"]                            # en düşük 0.9 geçer
    assert not saglamlik.s2_karar([0.899, 1.2, 1.2])["gecti"]                      # en düşük 0.899 kalır
    assert not saglamlik.s2_karar([1.5])["gecti"]                                  # geçerli komşu 1 -> kalır
    assert not saglamlik.s2_karar([1.5, None, math.nan])["gecti"]
    assert saglamlik.s2_karar([1.5, 1.4])["gecti"]


def test_s3_siniri():
    assert saglamlik.s3_karar(1.0) and not saglamlik.s3_karar(0.9999) and not saglamlik.s3_karar(math.nan)


def test_s4_siniri_ve_az_ornek():
    k = saglamlik.s4_karar(-20.0, 100.0, 20)
    assert k["gecti"] and not k["az_ornek"]                                         # tam -%20 geçer
    assert not saglamlik.s4_karar(-20.01, 100.0, 20)["gecti"]
    k19 = saglamlik.s4_karar(-500.0, 100.0, 19)                                    # 19 işlem: ölçülemedi = geçti + bayrak
    assert k19["gecti"] and k19["az_ornek"]


def _kapanis(n=420, seed=1, a=100.0):
    g = pd.date_range("2018-01-01", periods=n, freq="D", tz="UTC")
    rng = np.random.default_rng(seed)
    return pd.Series(a * np.exp(np.cumsum(rng.normal(0.0, 0.02, n))), index=g)


def test_s4_ayi_gunu_d_minus_1_verisini_kullanir():
    kap = {"A": _kapanis(), "B": _kapanis(seed=2)}
    e = rejim.endeks_kur(kap)
    ayi = rejim.ayi_gunleri(e)
    assert not ayi.iloc[:sabit.S4_SMA_GUN].any()                                    # ilk 200 gün tanımsız = ayı değil
    d = 350
    degisik = {k: v.copy() for k, v in kap.items()}
    for k in degisik:
        degisik[k].iloc[d:] *= 0.3                                                  # d günü ve sonrası fiyat çöker
    ayi2 = rejim.ayi_gunleri(rejim.endeks_kur(degisik))
    assert ayi2.iloc[d] == ayi.iloc[d]                                              # d günü etiketi d günü fiyatından etkilenmez
    assert (ayi2.iloc[:d] == ayi.iloc[:d]).all()
    # d+1 günü etiketi d günü fiyatından etkilenebilir
    ayi_kes = rejim.ayi_gunleri(rejim.endeks_kur({k: v.iloc[:d] for k, v in kap.items()}))
    assert (ayi_kes.iloc[:d] == ayi.iloc[:d]).all()


def test_endeks_5_gun_doldurma_siniri():
    g = pd.date_range("2020-01-01", periods=30, freq="D", tz="UTC")
    a = pd.Series(np.linspace(100, 130, 30), index=g)
    b = a.drop(g[10:20])                                                            # 10 günlük boşluk
    e = rejim.endeks_kur({"A": a, "B": b})
    assert e.iloc[0] == 1.0 and len(e) == 30
    # boşluk > 5 gün: B 5 günden sonra üye olmaktan çıkar -> getiri yalnız A'dan; hata vermeden hesaplanır
    assert np.isfinite(e.to_numpy()).all()


def test_giris_ayi_atamasi_giris_gunune_gore():
    g = pd.date_range("2020-01-01", periods=3, freq="D", tz="UTC")
    ayi = pd.Series([False, True, False], index=g)
    a = rejim.giris_ayi_mi(ayi, pd.DatetimeIndex(["2020-01-02 23:59", "2020-01-03 00:01"], tz="UTC"))
    assert list(a) == [True, False]


# ================================================================== 6.2 set
def _hafta(seed, n=200, ort=0.0):
    g = pd.date_range("2018-01-07", periods=n, freq="W-SUN", tz="UTC")
    return pd.Series(np.random.default_rng(seed).normal(ort, 0.02, n), index=g)


def test_kume_esik_ve_ortak_hafta_99():
    a = _hafta(1)
    ayni = {"a": a, "b": a * 1.0 + _hafta(2) * 0.9}                                  # yüksek korelasyon
    assert setm.kumeler(ayni)["a"] == setm.kumeler(ayni)["b"]
    ayri = {"a": a, "b": _hafta(5)}
    k = setm.kumeler(ayri)
    assert k["a"] != k["b"]
    kisa = {"a": a, "b": a.iloc[:99] * 1.0}                                          # birebir aynı ama ortak hafta 99
    assert setm.kumeler(kisa)["a"] != setm.kumeler(kisa)["b"]
    tam = {"a": a, "b": a.iloc[:100] * 1.0}                                          # 100 ortak hafta ölçülür
    assert setm.kumeler(tam)["a"] == setm.kumeler(tam)["b"]


def test_siralama_p_sonra_pf_x2_sonra_alfabetik_ve_stil_basina_en_fazla_3():
    ad = []
    for i, (p, pf) in enumerate([(0.001, 1.5), (0.001, 1.8), (0.0005, 1.2), (0.002, 2.0), (0.001, 1.8)]):
        ad.append({"strateji": f"s{i}", "tf": "1d", "stil_v2": "swing", "etiket": f"e{i}", "p": p, "pf_x2": pf})
    sirali = sorted(ad, key=setm.sira_anahtari)
    assert [a["strateji"] for a in sirali] == ["s2", "s1", "s4", "s0", "s3"]       # p, sonra pf x2 azalan, sonra alfabetik
    kume = {f"s{i}|1d": i for i in range(5)}                                        # hepsi ayrı küme, ayrı etiket
    sec, atl = setm.acgozlu_sec(ad, kume)
    assert [a["strateji"] for a in sec] == ["s2", "s1", "s4"] and atl["s0|1d"] == "stilde dolu"


def test_ayni_kume_ve_ayni_etiket_ikinci_alinmaz_stil_basina():
    ad = [{"strateji": "a", "tf": "1d", "stil_v2": "swing", "etiket": "trend", "p": 0.001, "pf_x2": 1.5},
          {"strateji": "b", "tf": "1d", "stil_v2": "swing", "etiket": "donus", "p": 0.002, "pf_x2": 1.5},
          {"strateji": "c", "tf": "1d", "stil_v2": "swing", "etiket": "trend", "p": 0.003, "pf_x2": 1.5},
          {"strateji": "d", "tf": "1d", "stil_v2": "gunici_kripto", "etiket": "trend", "p": 0.004, "pf_x2": 1.5}]
    sec, atl = setm.acgozlu_sec(ad, {"a|1d": 1, "b|1d": 1, "c|1d": 2, "d|1d": 3})
    assert [a["strateji"] for a in sec] == ["a", "d"]                                # b: küme 1 dolu; c: swing'de 'trend' dolu; d: ayrı stil
    assert "küme" in atl["b|1d"] and "etiket" in atl["c|1d"]


def test_s_en_buyuk_uygun_deger_ve_hicbiri_uymazsa_set_yok():
    rng = np.random.default_rng(3)
    g = rng.normal(0.0004, 0.01, 1500)
    b = setm.boyut_sec(g, tohum=5)
    assert b["s"] is not None
    tablo = b["tablo"]
    assert tablo[b["s"]] <= sabit.DD_MAKS
    ust = [s for s in sabit.S_IZGARA if s > b["s"]]
    assert all(tablo[s] > sabit.DD_MAKS for s in ust)                               # bir üst değer uymaz: s en büyük uygun
    assert setm.boyut_sec(g, tohum=5) == b                                          # deterministik
    felaket = rng.normal(-0.02, 0.15, 800)                                          # s = 0.1'de bile %15 aşılır
    assert setm.boyut_sec(felaket, tohum=5)["s"] is None


# ================================================================== uçtan uca: test -> saglamlik -> set -> mühür
@pytest.fixture()
def gelistirme(tablo, tmp_path, monkeypatch):
    """Sentetik geliştirme çıktısı: iki 'iyi' + bir 'tek' strateji; ham x1/x2 + mtm; eleme.csv. Havuz mührü m=939."""
    y, h = tablo
    for ad, kar, tohum in (("iyi1", 0.9, 5), ("iyi2", 0.9, 6)):
        for c in (1.0, 2.0):
            _ham_yaz(tmp_path, h, ad, "1d", EVREN, c, tohum=tohum, kar=kar)
        _mtm_yaz(tmp_path, ad, "1d", EVREN, 1.0)
    for c in (1.0, 2.0):
        _ham_yaz(tmp_path, h, "tek", "1d", EVREN, c, tohum=5, kar=0.0, tek_sembol=EVREN[0])
    hv, mh = _havuz_kur(tmp_path, [_satir("iyi1", "trend", "a", 1), _satir("iyi2", "donus", "b", 2), _satir("tek", "trend", "c", 3)])
    eleme.eleme_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)
    monkeypatch.setattr(k2, "tek_satir_baglam", SentetikStub())
    return tmp_path, hv, mh, y, h


def test_test_asamasi_uctan_uca_elenen_p1_ve_bayt_ayni(gelistirme, tmp_path_factory):
    tmp_path, hv, mh, y, h = gelistirme
    o = k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    assert o["satir"] == 3 and o["m"] == 939
    t = pd.read_csv(tmp_path / "test.csv").set_index("strateji")
    assert t.loc["tek", "p"] == 1.0 and t.loc["tek", "test_durum"] == "elendi"        # elenen satır p = 1
    assert t.loc["iyi1", "test_durum"] == "tamam" and 0 < t.loc["iyi1", "p"] < 1 and t.loc["iyi1", "asama"] in (1, 2)
    assert "p1" in t.columns and (tmp_path / "test_ozet.json").exists()
    # aynı girdiyle ikinci koşu (temiz dizin) bayt bayt aynı test.csv
    ikinci = tmp_path_factory.mktemp("ikinci")
    import shutil
    for alt in ("ham", "mtm"):
        shutil.copytree(tmp_path / alt, ikinci / alt)
    for f in ("maliyet_tablosu_v2.csv", "maliyet_tablosu_v2.sha256", "eleme.csv", "eleme_ozet.json"):
        shutil.copy(tmp_path / f, ikinci / f)
    k2.test_asamasi(ikinci, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    assert (ikinci / "test.csv").read_bytes() == (tmp_path / "test.csv").read_bytes()


def test_test_asamasi_eleme_yoksa_acik_hata_ve_muhurden_sonra_yazmaz(gelistirme):
    tmp_path, hv, mh, y, h = gelistirme
    (tmp_path / "eleme.csv").write_text("bozuk")
    with pytest.raises(RuntimeError, match="sha256 ile uyuşmuyor"):
        k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)
    (tmp_path / "eleme.csv").unlink()
    with pytest.raises(RuntimeError, match="önce eleme"):
        k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)
    (tmp_path / sabit.SET_MUHRU).write_text("{}")
    with pytest.raises(kasa.MuhurEngeli):
        k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)


def test_test_asamasi_butce_dolunca_csv_yazmaz_sonra_devam(gelistirme):
    tmp_path, hv, mh, y, h = gelistirme
    o = k2.test_asamasi(tmp_path, 1, 1e-9, hv, mh, ilerleme=False, spa_hesapla=False)
    assert o["bekleyen"] >= 1 and not (tmp_path / "test.csv").exists()
    o2 = k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    assert (tmp_path / "test.csv").exists() and "bekleyen" not in o2


def _test_csv_kesif_yaz(tmp_path, kesifler, h):
    """test.csv'yi doğrudan yaz (BH sonucunu sabitlemek için): kesifler listesi = keşif satırları."""
    havuz = pd.read_csv(tmp_path / "havuz.csv")
    satir = []
    for _, r in havuz.iterrows():
        satir.append({**{k: r[k] for k in ("strateji", "stil_v2", "tf", "evren", "etiket", "alt_etiket", "kume_no", "kilit_gorulmus")},
                      "p": 1e-5 if r["strateji"] in kesifler else 1.0, "kesif": r["strateji"] in kesifler})
    pd.DataFrame(satir).to_csv(tmp_path / "test.csv", index=False)
    (tmp_path / "test_ozet.json").write_text(json.dumps({"test_csv_sha256": kasa.sha256(tmp_path / "test.csv")}))


def test_saglamlik_satiri_s1_s4_uctan_uca(gelistirme, monkeypatch):
    tmp_path, hv, mh, y, h = gelistirme
    _test_csv_kesif_yaz(tmp_path, ["iyi1"], h)
    kayit = {}

    class SahteSt:
        parametreler = {"n": 20, "esik": 0.5}
        parametre_izgarasi = {"n": [10, 20, 30]}

        def yeni(self, **kw):
            s = SahteSt()
            s.kw = kw
            return s

    monkeypatch.setattr(saglamlik.hm, "varsayilan_strateji", lambda ad: ("varsayilan", SahteSt()))

    def sahte_ham(st, tf, evren_t, tablo_yolu, gecikme=0, carpan=1.0):
        kayit.setdefault("cagri", []).append((tf, gecikme, getattr(st, "kw", None)))
        ham1, b1 = ham.ham_yukle(tmp_path, 1.0, "iyi1", "1d", evren_t, h, veri_al=ham.veri_oku)
        return ham1, b1
    monkeypatch.setattr(saglamlik, "strateji_ham", sahte_ham)
    monkeypatch.setattr(saglamlik, "kapanis_serileri", lambda ev: {"A": _kapanis(2500), "B": _kapanis(2500, seed=3)})
    row = _satir("iyi1")
    s = saglamlik.saglamlik_satiri(row, tmp_path, y, h)
    assert s["durum"] == "tamam" and "s1" in s and "s2" in s and "s3" in s and "s4" in s
    tfler = [c[0] for c in kayit["cagri"]]
    assert ("1d", sabit.S1_GECIKME_MUM, None) in kayit["cagri"]                          # S1: 1 mum gecikme
    assert "4h" in tfler                                                                 # S3: diğer tf
    assert s["s2_n_komsu"] == 4 and s["s2_n_gecerli"] == 4                               # n: 10/30 (ızgara) ve esik: x0.8/x1.2
    assert s["saglam"] == all(s[k] for k in ("s1", "s2", "s3", "s4"))
    assert s["s4_az_ornek"] in ("evet", "hayir")
    assert (tmp_path / "saglamlik_satir" / "iyi1--1d.json").exists()
    # biten satır yeniden koşulmaz
    n = len(kayit["cagri"])
    saglamlik.saglamlik_satiri(row, tmp_path, y, h)
    assert len(kayit["cagri"]) == n


def test_saglamlik_asamasi_bos_kesif_ve_set_sifir_sonuc_holdout_acilmaz(gelistirme, monkeypatch):
    tmp_path, hv, mh, y, h = gelistirme
    _test_csv_kesif_yaz(tmp_path, [], h)
    o = saglamlik.saglamlik_asamasi(tmp_path, 1, None, ilerleme=False)
    assert o["kesif"] == 0 and o["saglam_kesif"] == 0 and (tmp_path / "saglamlik.csv").exists()
    monkeypatch.setattr(holdout, "strateji_hashleri", lambda s: {})
    r = setm.set_asamasi(tmp_path, None, hv, mh, ilerleme=False)
    assert r["sonuc"] == "0 strateji" and (tmp_path / sabit.SET_MUHRU).exists()
    with pytest.raises(holdout.HoldoutHatasi, match="set boş"):
        holdout.muhur_kontrol(tmp_path, hv)                                              # sonuç 0 -> holdout AÇILMAZ
    sag = SentetikHoldout({})
    with pytest.raises(holdout.HoldoutHatasi, match="set boş"):
        holdout.holdout_asamasi(tmp_path, sag, hv)
    assert not sag.cagrildi


def _saglamlik_csv_yaz(tmp_path, saglamlar, tf="1d"):
    havuz = pd.read_csv(tmp_path / "havuz.csv")
    el = pd.read_csv(tmp_path / "eleme.csv")
    sat = []
    for i, r in havuz[havuz["strateji"].isin(saglamlar)].iterrows():
        sat.append({**{k: r[k] for k in ("strateji", "stil_v2", "tf", "evren", "etiket", "alt_etiket", "kume_no", "kilit_gorulmus")},
                    "p": 0.001 * (i + 1), "liste": "saglam_kesif", "saglam": True, "pf_x2": 1.5, "s1": True, "s2": True, "s3": True, "s4": True})
    pd.DataFrame(sat).to_csv(tmp_path / "saglamlik.csv", index=False)
    (tmp_path / "saglamlik_ozet.json").write_text(json.dumps({"saglamlik_csv_sha256": kasa.sha256(tmp_path / "saglamlik.csv")}))


@pytest.fixture()
def muhurlu(gelistirme, monkeypatch):
    """set aşamasını uçtan uca koşturur: iki sağlam keşif -> set + mühür."""
    tmp_path, hv, mh, y, h = gelistirme
    monkeypatch.setattr(holdout, "strateji_hashleri", lambda s: {})
    _test_csv_kesif_yaz(tmp_path, ["iyi1", "iyi2"], h)
    _saglamlik_csv_yaz(tmp_path, ["iyi1", "iyi2"])
    o = setm.set_asamasi(tmp_path, None, hv, mh, ilerleme=False)
    return tmp_path, hv, mh, o


def test_set_asamasi_uctan_uca_ve_muhur_icerigi(muhurlu):
    tmp_path, hv, mh, o = muhurlu
    assert o["saglam_kesif"] == 2
    muhur = json.loads((tmp_path / sabit.SET_MUHRU).read_text())
    for k in ("set", "s", "dosyalar", "maliyet_tablosu_v2_sha256", "on_kayit_v2_sha256", "git_commit", "ortak_modul_hash", "v2_modul_hash",
              "strateji_hash", "evren"):
        assert k in muhur
    assert set(muhur["dosyalar"]) == {"havuz_v2.csv", "eleme.csv", "test.csv", "saglamlik.csv", "set.csv"}
    assert o["secilen"]                                        # B17: koşullu doğrulama yok, set seçilmiş olmalı
    assert all(a["ayar"] for a in muhur["set"]) and muhur["s"] in sabit.S_IZGARA
    assert 1 <= len(muhur["set"]) <= 2 * sabit.STIL_BASINA_MAKS
    assert holdout.muhur_kontrol(tmp_path, hv)["s"] == muhur["s"]
    # mühürden sonra geliştirme aşamaları yazamaz
    with pytest.raises(kasa.MuhurEngeli):
        setm.set_asamasi(tmp_path, None, hv, mh, ilerleme=False)
    with pytest.raises(kasa.MuhurEngeli):
        saglamlik.saglamlik_asamasi(tmp_path, 1, None, ilerleme=False)


def test_muhurlu_dosyalardan_biri_degisince_holdout_durur(muhurlu):
    tmp_path, hv, mh, o = muhurlu
    assert o["secilen"], "sentetik koşuda set seçilmeli (s bulunamadıysa test sessizce atlanmaz, FAIL eder)"
    sag = SentetikHoldout({})
    for dosya in ("eleme.csv", "test.csv", "saglamlik.csv", "set.csv"):
        yol = tmp_path / dosya
        orijinal = yol.read_bytes()
        yol.write_bytes(orijinal + b"\n#\n")
        with pytest.raises(holdout.HoldoutHatasi, match="değişmiş"):
            holdout.holdout_asamasi(tmp_path, sag, hv)
        yol.write_bytes(orijinal)
    hv_orijinal = hv.read_bytes()
    hv.write_bytes(hv_orijinal + b"\n")
    with pytest.raises(holdout.HoldoutHatasi, match="havuz_v2.csv"):
        holdout.holdout_asamasi(tmp_path, sag, hv)
    hv.write_bytes(hv_orijinal)
    (tmp_path / "maliyet_tablosu_v2.csv").write_text("x")
    with pytest.raises(holdout.HoldoutHatasi, match="maliyet"):
        holdout.holdout_asamasi(tmp_path, sag, hv)
    assert not sag.cagrildi and not holdout.baslamis_mi(tmp_path)


# ================================================================== 7 holdout (SENTETİK sağlayıcı)
class SentetikHoldout(holdout.HoldoutSaglayici):
    """Sentetik holdout: işlemler elle verilir; mumlar sentetik. `sira` günlükte 'basladi' kaydını görmeden veri vermez."""

    def __init__(self, islemler, pf=None, cikti=None, k2_p=None):
        self.islemler, self.pf, self.cikti, self.cagrildi, self.k2_p = islemler, pf or {}, cikti, False, k2_p
        self.mumlar = {s: sentetik(n=1500, seed=40 + i, bas="2023-01-01") for i, s in enumerate(EVREN)}

    def _gir(self):
        self.cagrildi = True
        if self.cikti is not None:
            assert holdout.baslamis_mi(self.cikti), "veri okunmadan ÖNCE günlüğe 'basladi' yazılmalı"

    def veri_sonu(self):
        self._gir()
        return "2026-11-01 00:00:00+00:00"

    def tek_islemler(self, kayit):
        self._gir()
        return self.islemler.get(kayit["strateji"], {}), EVREN, []

    def k2_baglam(self, kayit):
        self._gir()

        def veri_al(s):
            return self.mumlar[s], MotorAyarlari()

        def cikis_al(s):
            z = np.zeros(len(self.mumlar[s]), dtype=bool)
            return {"ex_long": z, "ex_short": z, "hedef_r": math.nan, "iz_k": None, "iz_periyot": 14, "be_r": None, "desteklenmeyen": []}
        return veri_al, cikis_al

    def pf_gunluk(self, kayit):
        self._gir()
        return self.pf[kayit["strateji"]]

    def pf_k2_p(self, kayit, n_sim, tohum):
        return 0.01


def _holdout_islem(sembol_idx, r, seed, n=40):
    """Sentetik holdout işlemleri (ham biçimi). Giriş zamanları SENTETİK mumların indeksindedir."""
    m = sentetik(n=1500, seed=40 + sembol_idx, bas="2023-01-01")
    rng = np.random.default_rng(seed)
    j = np.sort(rng.choice(np.arange(700, 1300), n, replace=False))
    from motor.strateji import gostergeler as gst
    atr = gst.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14).to_numpy(float)
    return pd.DataFrame({"ayar_no": np.zeros(n, dtype=np.int16), "giris_zamani": m.index[j].as_unit("ns"),
                         "cikis_zamani": m.index[j + 3].as_unit("ns"), "yon": np.ones(n, dtype=np.int8),
                         "r": np.full(n, r, dtype=np.float32), "sf": np.full(n, 0.05, dtype=np.float32),
                         "stop_mesafe": (2.0 * atr[j - 1]).astype(np.float32), "fonlama_r": np.zeros(n, dtype=np.float32)})


def _holdout_tarihleri_kaydir(df, sat_ofset):
    return df


def _set_kur(tmp_path, monkeypatch, tablo, stratejiler, s=0.5):
    """Doğrudan sentetik mühür: set.csv + diğer dosyalar + muhur_yaz. stratejiler: [(ad, stil)]."""
    y, h = tablo
    hv = tmp_path / "havuz.csv"
    pd.DataFrame([_satir(a, stil=st) for a, st in stratejiler]).to_csv(hv, index=False)
    for f in ("eleme.csv", "test.csv", "saglamlik.csv"):
        (tmp_path / f).write_text(f"x\n{f}\n")
    secilen = [{**_satir(a, stil=st), "ayar": "varsayilan", "p": 0.001, "pf_x2": 1.5, "kume": i + 1, "sira": i + 1}
               for i, (a, st) in enumerate(stratejiler)]
    pd.DataFrame(secilen).to_csv(tmp_path / "set.csv", index=False)
    monkeypatch.setattr(holdout, "strateji_hashleri", lambda s_: {})
    holdout.muhur_yaz(tmp_path, hv, {"secilen": secilen, "s": s, "sonuc": f"{len(secilen)} strateji", "s_tablo": {}})
    return hv


@pytest.fixture()
def ho_ortam(tablo, tmp_path, monkeypatch):
    # holdout zamanı ham tarihleri HOLDOUT_BAS öncesi olabilir (sentetik); çekirdek yalnız girişi >= HOLDOUT_BAS olanları sayar:
    monkeypatch.setattr(sabit, "HOLDOUT_BAS", pd.Timestamp("2023-01-01", tz="UTC"))
    maliyet.tabloyu_hazirla(tmp_path)
    return tmp_path


def test_holdout_muhur_yokken_acik_hata_ve_veri_okunmaz(ho_ortam):
    sag = SentetikHoldout({})
    with pytest.raises(holdout.HoldoutHatasi, match="yok"):
        holdout.holdout_asamasi(ho_ortam, sag)
    assert not sag.cagrildi and not holdout.baslamis_mi(ho_ortam)


def test_holdout_ikinci_cagri_acik_hata_ve_gunluk_once_yazilir(ho_ortam, tablo, monkeypatch):
    hv = _set_kur(ho_ortam, monkeypatch, tablo, [("hA", "swing")])
    isl = {"hA": {EVREN[0]: _holdout_islem(0, 2.0, 1)}}
    sag = SentetikHoldout(isl, cikti=ho_ortam)
    o = holdout.holdout_asamasi(ho_ortam, sag, hv)
    assert "kapi_gecti" in o and holdout.baslamis_mi(ho_ortam)
    olaylar = [k["olay"] for k in holdout.gunluk_oku(ho_ortam)]
    assert olaylar[0] == "basladi" and olaylar[-1] == "bitti"
    sag2 = SentetikHoldout(isl, cikti=ho_ortam)
    with pytest.raises(holdout.HoldoutTekrarHatasi):
        holdout.holdout_asamasi(ho_ortam, sag2, hv)
    assert not sag2.cagrildi
    with pytest.raises(holdout.HoldoutHatasi):
        holdout.muhur_yaz(ho_ortam, hv, {"secilen": [], "s": 0.5})               # holdout başladıktan sonra mühür değişmez


def test_set_kapisi_sinirlari():
    assert holdout.set_kapisi(0.01, 0.05)
    assert not holdout.set_kapisi(0.01, 0.051)               # p_set = 0.051 kalır
    assert not holdout.set_kapisi(0.0, 0.001) and not holdout.set_kapisi(-0.01, 0.001)    # net <= 0 kalır
    assert not holdout.set_kapisi(0.01, math.nan) and not holdout.set_kapisi(math.nan, 0.01)


def _sim_p_sabitle(monkeypatch, p_hedef_sayi):
    """k2_simule: toplam B çekimden `p_hedef_sayi` tanesi T'yi aşar (p_set = (1 + sayı)/(B+1))."""
    def sahte(islemler, veri_al, cikis_al, n_sim, tohum, alt_sinir=None, kismi_dizin=None):
        if n_sim == sabit.HOLDOUT_B_SET:
            t = np.full(n_sim, -1e9)
            t[:p_hedef_sayi] = 1e9
            return {"toplam_r": t, "n_gecersiz": 0, "n_islem": 1}
        return {"toplam_r": np.full(n_sim, -1e9), "n_gecersiz": 0, "n_islem": 1}      # strateji düzeyi (B=2000): p küçük
    monkeypatch.setattr(k2, "k2_simule", sahte)


def test_holdout_p_set_0051_kalir_0050_gecer(ho_ortam, tablo, monkeypatch):
    hv = _set_kur(ho_ortam, monkeypatch, tablo, [("hA", "swing")])
    isl = {"hA": {EVREN[0]: _holdout_islem(0, 2.0, 1)}}
    B = sabit.HOLDOUT_B_SET
    kritik = int(sabit.HOLDOUT_P_SET * (B + 1))                # 250 -> p = 251/5001 = 0.0502 > 0.05 ; 249 -> 250/5001 = 0.04999
    _sim_p_sabitle(monkeypatch, kritik - 1)
    o = holdout.holdout_asamasi(ho_ortam, SentetikHoldout(isl), hv)
    assert o["p_set"] == pytest.approx(kritik / (B + 1)) and o["p_set"] <= 0.05 and o["net_set"] > 0 and o["kapi_gecti"]
    # yeni ortam: p_set = 0.0502
    d2 = ho_ortam.parent / (ho_ortam.name + "_b")
    d2.mkdir()
    maliyet.tabloyu_hazirla(d2)
    hv2 = _set_kur(d2, monkeypatch, tablo, [("hA", "swing")])
    _sim_p_sabitle(monkeypatch, kritik)
    o2 = holdout.holdout_asamasi(d2, SentetikHoldout(isl), hv2)
    assert o2["p_set"] > 0.05 and not o2["kapi_gecti"]


def test_holdout_net_sifir_ya_da_eksi_kapi_kalir_ve_paper_girdisi_yok(ho_ortam, tablo, monkeypatch):
    hv = _set_kur(ho_ortam, monkeypatch, tablo, [("hA", "swing")])
    isl = {"hA": {EVREN[0]: _holdout_islem(0, -1.0, 1)}}
    _sim_p_sabitle(monkeypatch, 0)                              # p_set çok küçük (geçer) ama net < 0
    o = holdout.holdout_asamasi(ho_ortam, SentetikHoldout(isl), hv)
    assert o["net_set"] < 0 and not o["kapi_gecti"] and o["p_set"] < 0.05
    assert o["kalan"] == [] and o["cikan"] == {}                # kapı kalınca budama yapılmaz
    assert not (ho_ortam / "holdout" / "paper_girdisi.json").exists()
    assert (ho_ortam / "holdout" / "holdout_raporu.md").exists() and (ho_ortam / "holdout" / "holdout.csv").exists()


def test_holdout_kapi_budamadan_onceki_set_uzerinden_ve_yerine_yenisi_alinmaz(ho_ortam, tablo, monkeypatch):
    hv = _set_kur(ho_ortam, monkeypatch, tablo, [("hA", "swing"), ("hB", "swing"), ("hC", "gunici_kripto")], s=0.5)
    isl = {"hA": {EVREN[0]: _holdout_islem(0, 3.0, 1)},
           "hB": {EVREN[1]: _holdout_islem(1, -0.2, 2)},        # net < 0 -> budanır (set toplamı yine pozitif)
           "hC": {EVREN[2]: _holdout_islem(2, 3.0, 3)}}
    _sim_p_sabitle(monkeypatch, 0)
    o = holdout.holdout_asamasi(ho_ortam, SentetikHoldout(isl), hv)
    assert o["kapi_gecti"]
    # kapı BUDAMADAN ÖNCEKİ tüm mühürlü set (üçü) üzerinden: hB'nin zararı set netine dahil
    tam = holdout.oynat_net({a: {s: isl[a][s] for s in isl[a]} for a in isl}, {a: EVREN for a in isl}, 0.5,
                            ho_ortam / sabit.TABLO_V2_AD, pd.Timestamp("2026-11-01", tz="UTC"))
    assert o["net_set"] == pytest.approx(tam)
    assert "hB" in o["cikan"] and "holdout neti" in o["cikan"]["hB"]
    assert sorted(o["kalan"]) == ["hA", "hC"]                   # yerine yenisi alınmadı: kalan ⊂ mühürlü set
    pg = json.loads((ho_ortam / "holdout" / "paper_girdisi.json").read_text())
    assert sorted(a["strateji"] for a in pg["set"]) == ["hA", "hC"]


def test_budama_kurali_net_ve_k2_p():
    ol = {"a": {"net": 0.1, "k2_p": 0.25}, "b": {"net": 0.1, "k2_p": 0.2501}, "c": {"net": 0.0, "k2_p": 0.01},
          "d": {"net": 0.1, "k2_p": math.nan}, "e": {"net": 0.2, "k2_p": 0.01}}
    kalan, cikan = holdout.budama(ol)
    assert kalan == ["a", "e"] and set(cikan) == {"b", "c", "d"}


def test_holdout_portfoy_kolu_p_sete_girmez_ama_net_e_girer(ho_ortam, tablo, monkeypatch):
    hv = _set_kur(ho_ortam, monkeypatch, tablo, [("hA", "swing"), ("pf__x", "portfoy")], s=0.5)
    g = pd.date_range("2025-11-08", periods=100, freq="D", tz="UTC")
    pf = {"pf__x": pd.Series(0.001, index=g)}
    isl = {"hA": {EVREN[0]: _holdout_islem(0, 2.0, 1)}}
    _sim_p_sabitle(monkeypatch, 0)
    o = holdout.holdout_asamasi(ho_ortam, SentetikHoldout(isl, pf), hv)
    assert o["net_portfoy"] == pytest.approx(holdout.pf_net(pf["pf__x"], 0.5)) and o["net_portfoy"] > 0
    assert o["net_set"] == pytest.approx(o["net_tek"] + o["net_portfoy"])
    assert o["T_set"] == pytest.approx(k2.toplam_r(k2.cakisma_suz(isl["hA"], sabit.HOLDOUT_BAS)))   # yalnız tek-grafik; çakışma süzgeci sonrası


def test_holdout_saglayici_gercek_degil_testte_gercek_veriye_dokunulmaz(ho_ortam, tablo, monkeypatch):
    hv = _set_kur(ho_ortam, monkeypatch, tablo, [("hA", "swing")])

    def yasak(*a, **k):
        raise AssertionError("gerçek holdout verisi açıldı")
    monkeypatch.setattr(we, "veri_ayarla", yasak)
    monkeypatch.setattr(we, "_veri", yasak)
    isl = {"hA": {EVREN[0]: _holdout_islem(0, 2.0, 1)}}
    holdout.holdout_asamasi(ho_ortam, SentetikHoldout(isl), hv)         # sentetik sağlayıcı: we.* çağrılmaz


def test_cli_holdout_onay_bayragi_ve_muhur(tmp_path):
    from motor.arastirma.v2.__main__ import main
    with pytest.raises(SystemExit):
        main(["holdout", "--cikti", str(tmp_path)])                      # --holdout-bir-kez yok
    with pytest.raises(holdout.HoldoutHatasi):
        main(["holdout", "--cikti", str(tmp_path), "--holdout-bir-kez"])  # (pytest altında zaten kapalı; mühür de yok)


# ================================================================== gerçek motor + sentetik mum entegrasyonu
def test_strateji_ham_gecikme_ve_k2_gercek_motorla(tablo, monkeypatch):
    y, h = tablo
    m = sentetik(n=1800, seed=3, bas="2018-01-01")
    monkeypatch.setattr(ham, "veri_oku", lambda s, t: (m, None))
    monkeypatch.setattr(saglamlik.hm, "veri_oku", lambda s, t: (m, None))
    etiket, st = ham.varsayilan_strateji("swing__bant-donus")
    sem = ("DK_XAU", "DK_WTI")
    h0, b0 = saglamlik.strateji_ham(st, "1d", sem, y)
    h1, b1 = saglamlik.strateji_ham(st, "1d", sem, y, gecikme=sabit.S1_GECIKME_MUM)
    assert not b0["hatali"] and not b1["hatali"] and set(h0) == set(sem)
    assert sum(len(d) for d in h0.values()) > 5
    assert not h0["DK_XAU"]["giris_zamani"].equals(h1["DK_XAU"]["giris_zamani"])            # gecikme girişleri kaydırır
    assert np.isfinite(saglamlik.evren_pf(h0, pd.Timestamp("2018-06-01", tz="UTC")))
    # K2: aynı strateji, gerçek çıkış kuralları, gerçek ham işlemler
    monkeypatch.setattr(k2.hm, "veri_oku", lambda s, t: (m, None))
    veri_al, cikis_al, destek_yok = k2.tek_satir_baglam("swing__bant-donus", "1d", y)
    gercek = k2.cakisma_suz(h0, pd.Timestamp("2018-06-01", tz="UTC"))
    assert gercek and isinstance(destek_yok, list)
    if not destek_yok:
        sim = k2.k2_simule(gercek, veri_al, cikis_al, 60, 123)
        p = k2.p_degeri(k2.toplam_r(gercek), sim["toplam_r"])
        assert 0 < p <= 1 and sim["n_islem"] == 60 * sum(len(d) for d in gercek.values())


def test_k2_kismi_sonuc_devam_eder_ayni_sonuc(tmp_path):
    m, atr, d, j = _kur_k2(n_islem=6)
    isl = {"ETHUSDT": d, "BTCUSDT": d}
    stub = SentetikStub(900)
    ci = {"ex_long": np.zeros(len(m), dtype=bool), "ex_short": np.zeros(len(m), dtype=bool), "hedef_r": math.nan, "iz_k": None,
          "iz_periyot": 14, "be_r": None, "desteklenmeyen": []}
    va = lambda s: (m, MotorAyarlari())               # noqa: E731
    ca = lambda s: ci                                  # noqa: E731
    tam = k2.k2_simule(isl, va, ca, 50, 77)
    kd = tmp_path / "kismi"
    cag = []

    def patlayan(s):
        if s == "ETHUSDT" and not cag:
            cag.append(1)
            raise KeyboardInterrupt
        return va(s)
    with pytest.raises(KeyboardInterrupt):
        k2.k2_simule(isl, patlayan, ca, 50, 77, kismi_dizin=kd)
    assert (kd / "BTCUSDT.npz").exists() and not (kd / "ETHUSDT.npz").exists()      # biten sembol diske yazıldı
    devam = k2.k2_simule(isl, patlayan, ca, 50, 77, kismi_dizin=kd)
    np.testing.assert_array_equal(devam["toplam_r"], tam["toplam_r"])


def test_spa_asamasi_havuz_gunluk_mtm_ile_ozete_yazilir(gelistirme):
    tmp_path, hv, mh, y, h = gelistirme
    o = k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False)
    spa_o = json.loads((tmp_path / "test_ozet.json").read_text())["spa"]
    assert spa_o["durum"] == "tamam" and spa_o["n_model"] == 2 and spa_o["atlanan"] == 1      # 'tek' için mtm yok: atlanır ve sayılır
    assert 0.0 <= spa_o["p"] <= 1.0 and (tmp_path / "gunluk" / "iyi1--1d.parquet").exists()
    assert (spa_o["ilk_satir"] == sabit.SPA_RAPOR_METNI) == (spa_o["p"] > sabit.SPA_RAPOR_ESIK_P)
    assert "spa" in o
    # test.csv SPA'dan etkilenmez (mühürlenebilir): SPA'sız koşuyla aynı bayt
    csv1 = (tmp_path / "test.csv").read_bytes()
    k2.test_asamasi(tmp_path, 1, None, hv, mh, ilerleme=False, spa_hesapla=False)
    assert (tmp_path / "test.csv").read_bytes() == csv1


# ================================================================== B15: veri hatası kapıyı KODDA düşürür
def test_b15_set_kapisi_hata_varsa_gecmez():
    assert holdout.set_kapisi(0.01, 0.05, [])
    assert holdout.set_kapisi(0.01, 0.05, None)
    assert not holdout.set_kapisi(0.01, 0.001, {"hA": ["X: veri_okunamadi"]})
    assert not holdout.set_kapisi(0.01, 0.001, ["X: veri_okunamadi"])


def test_b15_holdout_hatali_sembol_kapiyi_dusurur_ve_raporlanir(ho_ortam, tablo, monkeypatch):
    class HataliSag(SentetikHoldout):
        def tek_islemler(self, kayit):
            isl, sira, _ = super().tek_islemler(kayit)
            return isl, sira, ["ZZZ: holdout_verisi_yok: son mum 2022-12-31 < HOLDOUT_BAS"]
    hv = _set_kur(ho_ortam, monkeypatch, tablo, [("hA", "swing")])
    isl = {"hA": {EVREN[0]: _holdout_islem(0, 2.0, 1)}}
    _sim_p_sabitle(monkeypatch, 0)                               # net > 0 ve p_set küçük: hatasız olsaydı kapı GEÇERDİ
    o = holdout.holdout_asamasi(ho_ortam, HataliSag(isl), hv)
    assert o["net_set"] > 0 and o["p_set"] < 0.05
    assert not o["kapi_gecti"] and o["kapi_hata_engeli"]
    assert o["hatalar"]["hA"] and "ZZZ" in o["hatalar"]["hA"][0]
    assert o["kapsam"]["hA"] == {"evren": len(EVREN), "islemli": 1, "hatali": 1}
    assert not (ho_ortam / "holdout" / "paper_girdisi.json").exists()
    csv = pd.read_csv(ho_ortam / "holdout" / "holdout.csv")
    assert "ZZZ" in csv["hatalar"].iloc[0] and csv["kapsam_hatali"].iloc[0] == 1
    assert "ZZZ" in (ho_ortam / "holdout" / "holdout_raporu.md").read_text(encoding="utf-8")


def test_b15_gercek_saglayici_atlanan_sembolleri_hatalara_yazar(monkeypatch):
    class Deneme:
        pass
    monkeypatch.setitem(holdout._YETKI, "acik", True)
    monkeypatch.setattr(we, "veri_ayarla", lambda *a, **k: None)
    sag = holdout.GercekSaglayici("tablo.csv")
    monkeypatch.setattr(sag, "_strateji", lambda kayit: Deneme())
    sira = sabit.evren_listesi("kripto")
    ekle = pd.DataFrame({"kapanis": [1.0]}, index=pd.DatetimeIndex([sabit.HOLDOUT_BAS - pd.Timedelta(days=5)]))
    bos = ekle.iloc[0:0]

    def sahte_veri(s, tf):
        if s == sira[0]:
            raise FileNotFoundError("yok")
        if s == sira[1]:
            raise ValueError("bozuk")
        if s == sira[2]:
            return bos, None
        return ekle, None                                         # holdout öncesinde biten veri
    monkeypatch.setattr(we, "_veri", sahte_veri)
    out, s2, hatalar = sag.tek_islemler({"strateji": "x", "tf": "1d", "evren": "kripto"})
    assert out == {} and s2 == sira
    assert len(hatalar) == len(sira)                              # HİÇBİR sembol sessizce atlanmaz
    assert hatalar[0].startswith(f"{sira[0]}: veri_okunamadi") and hatalar[1].startswith(f"{sira[1]}: veri_okunamadi")
    assert hatalar[2].startswith(f"{sira[2]}: veri_bos") and "holdout_verisi_yok" in hatalar[3]


# ================================================================== B14: atomik başlangıç işareti
def test_b14_baslangic_isareti_atomik_ve_eski_gunluk_okunur(tmp_path):
    assert not holdout.baslamis_mi(tmp_path)
    holdout.baslangic_isaretle(tmp_path)
    assert holdout.baslamis_mi(tmp_path)
    with pytest.raises(holdout.HoldoutTekrarHatasi):              # ikinci (yarışan) deneme O_EXCL ile reddedilir
        holdout.baslangic_isaretle(tmp_path)
    # eski biçim: yalnız günlükte "basladi" (işaret dosyası yok) hâlâ başlamış sayılır
    d2 = tmp_path / "eski"
    holdout.gunluge_yaz(d2, {"olay": "basladi"})
    assert not holdout._baslangic_isareti(d2).exists() and holdout.baslamis_mi(d2)


def test_b14_holdout_isaret_dosyasi_olusur_ve_gunluk_yazilmadan_ikinci_kosu_reddedilir(ho_ortam, tablo, monkeypatch):
    hv = _set_kur(ho_ortam, monkeypatch, tablo, [("hA", "swing")])
    holdout.baslangic_isaretle(ho_ortam)                          # başka bir koşu işareti yarıştan önce koymuş
    sag = SentetikHoldout({"hA": {EVREN[0]: _holdout_islem(0, 2.0, 1)}})
    with pytest.raises(holdout.HoldoutTekrarHatasi):
        holdout.holdout_asamasi(ho_ortam, sag, hv)
    assert not sag.cagrildi and holdout.gunluk_oku(ho_ortam) == []
