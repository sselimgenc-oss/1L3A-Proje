"""Portföy sağlamlık paketi: rastgele kıyas, blok bootstrap, maliyet çarpanı, komşu ayarlar, yoğunlaşma, kapılar."""
import math

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import saglamlik_portfoy as sp
from motor.arastirma import wf_portfoy as wp
from motor.portfoy.motor import portfoy_backtest
from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.portfoy.stratejiler.ortak import ORTAK_PARAMETRELER, PfTemel, dongusel_hedef, en_iyi_k, tetik_satirlari

SEM = ("A", "B", "C", "D")


def _piyasa(kenar: bool, n=1500, tohum=3):
    """4 sembol, günlük. kenar=True: her 40 günlük blokta rastgele bir sembol +%0.8/gün sürüklenir (momentum kenarı)."""
    rng = np.random.default_rng(tohum)
    surukle = np.zeros((n, 4))
    if kenar:
        for b in range(0, n, 40):
            surukle[b:b + 40, rng.integers(4)] = 0.008
    getiri = surukle + rng.normal(0, 0.012, (n, 4))
    idx = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC", name="zaman")
    v = {}
    for j, s in enumerate(SEM):
        kap = 100 * np.exp(np.cumsum(getiri[:, j]))
        ac = np.r_[100.0, kap[:-1]]
        v[s] = pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) * 1.003, "dusuk": np.minimum(ac, kap) * 0.997,
                             "kapanis": kap, "hacim": 1.0}, index=idx)
    return v


class _Mom(PfTemel):
    ad = "t__mom"
    min_sembol = 2
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": SEM, "lb": 10}
    parametre_izgarasi = {"lb": [5, 10, 20]}

    def _hedef(self, ev, tk):
        mom = tk.mom(self.parametreler["lb"])
        gecerli = mom.notna().any(axis=1).to_numpy()
        tetik = tetik_satirlari(tk.eksen, "W", gecerli)
        return dongusel_hedef(tk.eksen, list(ev), tetik, lambda i: pd.Series(
            {s: 1.0 for s in en_iyi_k(mom.iloc[i], 1)}))


def _p_hesapla(kenar, n_sim=30):
    v = _piyasa(kenar)
    st = _Mom()
    ay = wp.maliyet_ayarlari(1.0)
    r = portfoy_backtest(v, st, ay, {})
    g = r.gunluk_ozsermaye.pct_change().fillna(0.0)
    g = g.iloc[60:]
    hz = sp.RastgeleHazirlik(st, v)
    sims = []
    for k in range(n_sim):
        rr = portfoy_backtest(v, sp.RastgeleAgirlik(st, hz, [7, k]), ay, {})
        x = rr.gunluk_ozsermaye.pct_change().fillna(0.0).iloc[60:]
        sims.append(sp.sharpe(x.to_numpy()))
    return sp.rastgele_p(sp.sharpe(g.to_numpy()), sims)


def test_rastgele_kiyas_kenarli_strateji_p_kucuk():
    assert _p_hesapla(True)["rnd_p"] <= 0.05


def test_rastgele_kiyas_kenarsiz_strateji_p_buyuk():
    assert _p_hesapla(False)["rnd_p"] > 0.2


def test_rastgele_kopya_takvim_ve_agirlik_kumesi_ayni():
    v = _piyasa(True, n=400)
    st = _Mom()
    hz = sp.RastgeleHazirlik(st, v)
    h = st.hedefler(v)
    rnd = sp.RastgeleAgirlik(st, hz, [1, 2]).hedefler(v)
    durum = h.ffill().fillna(0.0)
    degis = (durum != durum.shift(1).fillna(0.0)).any(axis=1)
    assert rnd.notna().any(axis=1).equals(degis) or (rnd.notna().any(axis=1) == degis).all()
    for i in np.flatnonzero(degis.to_numpy()):
        assert sorted(rnd.iloc[i].to_numpy()) == sorted(durum.iloc[i].to_numpy())     # aynı ağırlık kümesi
    # stop kuralı adayın kendisi: sinyaller hatasız, açık hedeflerde stop var
    hh, ss = sp.RastgeleAgirlik(st, hz, [1, 2]).sinyaller(v)
    ac = hh.ffill().fillna(0.0) != 0
    assert ss[ac & hh.notna()].notna().sum().sum() == (ac & hh.notna()).sum().sum()


def test_rastgele_tohum_deterministik_ve_farkli():
    v = _piyasa(True, n=300)
    st = _Mom()
    hz = sp.RastgeleHazirlik(st, v)
    a = sp.RastgeleAgirlik(st, hz, [1, 1]).hedefler(v)
    b = sp.RastgeleAgirlik(st, hz, [1, 1]).hedefler(v)
    c = sp.RastgeleAgirlik(st, hz, [1, 2]).hedefler(v)
    assert a.equals(b) and not a.equals(c)


def test_rastgele_p_formulu():
    r = sp.rastgele_p(1.0, [0.0] * 199 + [2.0])
    assert r["rnd_p"] == pytest.approx(2 / 201) and r["rnd_yuzdelik"] == pytest.approx(199 / 200)
    assert sp.rastgele_p(5.0, np.zeros(199))["rnd_p"] == pytest.approx(1 / 200)
    assert math.isnan(sp.rastgele_p(float("nan"), [1.0])["rnd_p"])


def test_blok_bootstrap_kapsama():
    """iid getirilerde gerçek Sharpe %90 aralığa ~%90 oranında girer (örneklem küçük: geniş tolerans)."""
    rng = np.random.default_rng(5)
    mu, sd, T = 0.0015, 0.01, 600
    gercek = mu / sd * math.sqrt(365)
    ic, n = 0, 150
    for k in range(n):
        x = rng.normal(mu, sd, T)
        b = sp.blok_bootstrap_sharpe(x, tekrar=300, tohum=k)
        ic += b["boot_alt"] <= gercek <= b["boot_ust"]
    assert 0.78 <= ic / n <= 0.98


def test_bootstrap_kenarsiz_alt_uc_negatif_kenarli_pozitif():
    rng = np.random.default_rng(1)
    assert sp.blok_bootstrap_sharpe(rng.normal(0, 0.01, 800))["boot_alt"] < 0
    assert sp.blok_bootstrap_sharpe(rng.normal(0.003, 0.01, 800))["boot_alt"] > 0
    x = rng.normal(0, 0.01, 800)
    assert sp.blok_bootstrap_sharpe(x, tohum=3) == sp.blok_bootstrap_sharpe(x, tohum=3)
    assert math.isnan(sp.blok_bootstrap_sharpe([0.01] * 10)["boot_alt"])


def test_maliyet_carpani_iki_kati_ve_net_duser():
    a1, a2 = wp.maliyet_ayarlari(1.0), wp.maliyet_ayarlari(2.0)
    assert a2.komisyon_taker_yuzde == pytest.approx(2 * a1.komisyon_taker_yuzde)
    assert a2.kayma_bps == pytest.approx(2 * a1.kayma_bps) and a2.stop_kayma_bps == pytest.approx(2 * a1.stop_kayma_bps)
    v = _piyasa(True, n=500)
    n1 = portfoy_backtest(v, _Mom(), a1, {}).ozsermaye.iloc[-1]
    n2 = portfoy_backtest(v, _Mom(), a2, {}).ozsermaye.iloc[-1]
    assert n2 < n1


def test_m2_wf_portfoy_carpan_2_ile_cagrilir(monkeypatch, tmp_path):
    cagri = {}

    def sahte(*a, **k):
        cagri.update(k)
        return pd.DataFrame([{"hata": "", "sharpe": 0.9, "net_getiri": 0.3, "max_dusus": 0.1}])
    monkeypatch.setattr(sp.wp, "wf_portfoy", sahte)
    s = {"strateji": "pf__x", "evren": "kripto", "tf": "1d"}
    r = sp.bilesen_m2(s, {"wf_etiket": "e", "cikti_dizini": tmp_path})
    assert cagri["maliyet_carpani"] == 2.0 and r["m2_sharpe"] == 0.9 and cagri["surec"] == 1


def test_komsu_ayarlari_izgara_ve_yuzde():
    sinif = tum_portfoy_stratejileri()["pf__rotasyon"]
    p = {**sinif.varsayilan_parametreler, "lookback_gun": 90, "k": 2, "takvim": "M"}
    kom = sp.komsu_ayarlari(sinif, p)
    assert {"lookback_gun": 30} in kom and {"lookback_gun": 180} in kom and {"k": 1} in kom and {"k": 3} in kom
    assert not any("takvim" in k for k in kom) and not any("semboller" in k for k in kom)
    assert {"atr_k": pytest.approx(2.4)} in kom or any(abs(k.get("atr_k", 0) - 2.4) < 1e-9 for k in kom)
    kes = tum_portfoy_stratejileri()["pf__kesit_ls"]
    kom2 = sp.komsu_ayarlari(kes, {**kes.varsayilan_parametreler, "takvim": "14", "k": 1})
    assert {"takvim": "7"} in kom2 and {"takvim": "30"} in kom2          # rakam dizgeleri sıralı sayısal
    assert [k for k in kom2 if "k" in k] == [{"k": 2}]                   # ızgara ucu: tek komşu


def test_yogunlasma_ve_rejim_yil():
    g = pd.Series([0.10] + [0.001] * 99, index=pd.date_range("2022-01-01", periods=100, freq="D", tz="UTC"))
    y = sp.yogunlasma(g)
    assert y["net_ex1"] == pytest.approx(1.001 ** 99 - 1) and y["net_ex5"] < y["net_ex1"]
    assert 0.5 < y["en_iyi_ay_pay"] <= 1.0
    k = pd.Series(np.linspace(100, 300, 600), index=pd.date_range("2021-01-01", periods=600, freq="D", tz="UTC"))
    et = sp.rejim_etiketleri(k, pd.date_range("2022-01-01", periods=5, freq="D", tz="UTC"))
    assert set(et) == {"boga"}
    m = sp.rejim_ve_yil(g, k)
    assert m["rej_boga_gun"] == 100 and m["rej_ayi_gun"] == 0 and "2022" in m["yil_json"]
    assert sp.rejim_ve_yil(g, None)["rej_belirsiz_gun"] == 100


def test_kapilar():
    iyi = {"m2_sharpe": 0.5, "m2_net_getiri": 0.1, "rnd_p": 0.03, "boot_alt": 0.1, "komsu_oran": 0.7, "komsu_n": 5}
    assert sp.kapilar(iyi) == (True, [])
    for k, kotu in [("m2_sharpe", 0.39), ("m2_net_getiri", 0.0), ("rnd_p", 0.051), ("boot_alt", 0.0), ("komsu_oran", 0.59),
                    ("komsu_n", 1)]:
        ok, ned = sp.kapilar({**iyi, k: kotu})
        assert not ok and len(ned) == 1
    assert not sp.kapilar({})[0]
    assert sp.kapilar({**iyi, "m2_sharpe": 0.4, "rnd_p": 0.05, "komsu_oran": 0.6})[0]       # sınırlar geçer


def test_dik_secimsiz_pencere_sifir():
    gun = pd.date_range("2022-01-01", periods=10, freq="D", tz="UTC")
    gl = {"a": pd.Series(0.01, index=gun)}
    out = sp.dik(gl, [("a", gun[2], gun[5])], gun)
    assert out.iloc[2:5].eq(0.01).all() and out.iloc[:2].eq(0).all() and out.iloc[5:].eq(0).all()
