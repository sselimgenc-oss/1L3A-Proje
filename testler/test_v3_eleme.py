"""v3 eleme hattı (ON_KAYIT_V3 bölüm 1, 1.2, 2, 3, 6). YALNIZ SENTETİK veri: gerçek mum verisi okunmaz, hiçbir gerçek performans hesaplanmaz."""
from __future__ import annotations

import ast
import json
import math
import zlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import wf_evren as we
from motor.arastirma.v2 import eleme as v2e
from motor.arastirma.v3 import __main__ as cli
from motor.arastirma.v3 import destek, dondurma, kos, rapor, rastgele, sabit, veri
from motor.backtest.motor import MotorAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji

KOK = Path(__file__).resolve().parents[1]
V3 = KOK / "motor" / "arastirma" / "v3"
TABLO = sabit.MALIYET_V2


# ------------------------------------------------------------------ sentetik veri
def mum(n, tf="1h", seed=3, bas="2021-06-01", vol=0.003):
    dk = {"15m": 15, "30m": 30, "1h": 60, "1d": 1440}[tf]
    rng = np.random.default_rng(seed)
    idx = pd.date_range(bas, periods=n, freq=f"{dk}min", tz="UTC")
    c = 100 * np.exp(np.cumsum(rng.normal(0.00002, vol, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.001, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.001, n)))
    return pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": c, "hacim": rng.uniform(1e3, 2e3, n)}, index=idx)


def veri_al_fabrika(n=24 * 365 * 4):
    onb = {}

    def veri_al(sembol, tf):
        if (sembol, tf) not in onb:
            onb[(sembol, tf)] = (mum(n, tf), None)
        return onb[(sembol, tf)]
    return veri_al


class SmaTest(Strateji):
    """Sentetik: kapanış SMA(L) üstüne çıkınca long, altına inince çık (ısınma = L mum)."""
    ad, stil = "", "swing"
    varsayilan_parametreler = {"L": 200, "atr_k": 3.0}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        from motor.strateji import gostergeler as g
        L = int(self.parametreler["L"])
        sma = m["kapanis"].rolling(L, min_periods=L).mean()
        ust = m["kapanis"] > sma
        giris = ust & ~ust.shift(1, fill_value=True)
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
        k = float(self.parametreler["atr_k"])
        return cerceve(m, giris, False, m["kapanis"] - k * atr, m["kapanis"] + k * atr, cikis=(m["kapanis"] < sma))


# ------------------------------------------------------------------ sabitler / satır tablosu
def test_satir_tohumu_formul():
    a = sabit.satir_tohumu("v3__x", "k2")
    assert a == (zlib.crc32(b"v3__x|k2") ^ 20261111)
    assert a != sabit.satir_tohumu("v3__x", "rw")
    with pytest.raises(ValueError):
        sabit.satir_tohumu("v3__x", "yok")


def test_satir_tablosu_bolum_1():
    s = sabit.satirlar()
    assert [x.no for x in s] == list(range(1, 10))
    assert [x.tur for x in s] == ["portfoy"] * 5 + ["tek"] * 4
    assert s[6].bas == pd.Timestamp("2024-10-15", tz="UTC") and s[7].bas == pd.Timestamp("2022-01-01", tz="UTC")
    assert all(x.bas is None for i, x in enumerate(s) if i not in (6, 7))
    assert len(s[0].evren) == 13 and s[4].evren != s[0].evren and len(s[4].evren) == 13
    assert s[5].evren == ("DK_SPX",) and s[6].evren == ("BTCUSDT",) and s[7].evren == ("BTCUSDT",)   # satır 8: kodlama_v3.csv
    assert s[8].evren == ("DK_SPX",) and s[8].rapor_evren == ("BTCUSDT",)
    assert [x.rastgele for x in s] == [None, "agirlik", "agirlik", "agirlik", None, "giris", "giris", "giris", "giris"]
    assert [x.al_tut for x in s[:5]] == [True, False, False, False, True]
    assert [x.min_islem for x in s[5:]] == [60, 40, 60, 40]
    assert sabit.VERI_SONU == pd.Timestamp("2026-10-31", tz="UTC") and sabit.B == 2000


def test_esik_sayilari_yalniz_sabit_py():
    """Kaynak taraması: eşik değerleri başka v3 modülünde sayı sabiti olarak geçmez."""
    yasak = {1.2, 60, 40, 0.1, 0.5, 1095, 20, 2000, 20261111, 20.0, 0.10}
    for f in sorted(V3.glob("*.py")):
        if f.name == "sabit.py":
            continue
        for d in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(d, ast.Constant) and not isinstance(d.value, (str, bool)) and isinstance(d.value, (int, float)) and d.value in yasak:
                pytest.fail(f"{f.name}:{d.lineno}: eşik benzeri sayı sabiti {d.value!r} (yalnız sabit.py'de olmalı)")


def test_genis_stop_parametresi_dokuz_satirda():
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    for s in sabit.satirlar():
        st = tum_portfoy_stratejileri()[s.strateji]() if s.tur == "portfoy" else kos.strateji_uret(s.strateji)
        assert kos.genis_stop_parametresi(st) == {"atr_k": 20.0}
        assert st.yeni(**kos.genis_stop_parametresi(st)).parametreler["atr_k"] == 20.0
    with pytest.raises(KeyError):
        class Yok(Strateji):
            ad, varsayilan_parametreler = "", {"x": 1}
            def sinyaller(self, m): ...
        kos.genis_stop_parametresi(Yok())


# ------------------------------------------------------------------ kapı sınırları (tek grafik)
def _o1(**k):
    d = {"pf": sabit.V1_PF_MIN, "n_islem": 60, "kill": 0, "r_yil": {2020: 5.0, 2021: 3.0, 2022: 1.0}}
    d.update(k)
    return d


def test_v1_siniri():
    assert kos.kapi_tek(_o1(), 0.01, 0.01, 60)["v1"]
    assert not kos.kapi_tek(_o1(pf=sabit.V1_PF_MIN - 1e-9), 0.01, 0.01, 60)["v1"]
    assert not kos.kapi_tek(_o1(), 0.0, 0.01, 60)["v1"]                        # net(x2) > 0 şart (eşitlik geçmez)
    assert not kos.kapi_tek(_o1(pf=math.nan), 0.01, 0.01, 60)["v1"]
    assert not kos.kapi_tek(_o1(), math.nan, 0.01, 60)["v1"]


def test_v2_siniri_satira_gore():
    assert kos.kapi_tek(_o1(n_islem=sabit.V2_MIN_ISLEM), 0.01, 0.01, sabit.V2_MIN_ISLEM)["v2"]
    assert not kos.kapi_tek(_o1(n_islem=sabit.V2_MIN_ISLEM - 1), 0.01, 0.01, sabit.V2_MIN_ISLEM)["v2"]
    assert kos.kapi_tek(_o1(n_islem=sabit.V2_MIN_ISLEM_KISA), 0.01, 0.01, sabit.V2_MIN_ISLEM_KISA)["v2"]
    assert not kos.kapi_tek(_o1(n_islem=sabit.V2_MIN_ISLEM_KISA - 1), 0.01, 0.01, sabit.V2_MIN_ISLEM_KISA)["v2"]
    assert [x.min_islem for x in sabit.satirlar()[5:]] == [sabit.V2_MIN_ISLEM, sabit.V2_MIN_ISLEM_KISA, sabit.V2_MIN_ISLEM, sabit.V2_MIN_ISLEM_KISA]


def test_v3_en_iyi_yil_cikarilinca():
    assert kos.kapi_tek(_o1(r_yil={2020: 5.0, 2021: 1e-6}), 0.01, 0.01, 60)["v3"]
    assert not kos.kapi_tek(_o1(r_yil={2020: 5.0, 2021: 0.0}), 0.01, 0.01, 60)["v3"]          # ΣR > 0 şart
    assert not kos.kapi_tek(_o1(r_yil={2020: 5.0, 2021: -1e-6}), 0.01, 0.01, 60)["v3"]
    assert not kos.kapi_tek(_o1(r_yil={2020: 5.0}), 0.01, 0.01, 60)["v3"]                       # tek yıl: kalan boş -> geçmez
    assert not kos.kapi_tek(_o1(r_yil={}), 0.01, 0.01, 60)["v3"]


def test_v4_p_siniri():
    assert kos.kapi_tek(_o1(), 0.01, sabit.V4_P_MAX, 60)["v4"]
    assert not kos.kapi_tek(_o1(), 0.01, sabit.V4_P_MAX + 1e-9, 60)["v4"]
    assert not kos.kapi_tek(_o1(), 0.01, math.nan, 60)["v4"]


def test_v5_kill_siniri():
    assert kos.kapi_tek(_o1(kill=0), 0.01, 0.01, 60)["v5"]
    assert not kos.kapi_tek(_o1(kill=1), 0.01, 0.01, 60)["v5"]
    assert not kos.kapi_tek(_o1(kill=math.nan), 0.01, 0.01, 60)["v5"]
    assert kos.kapi_tek(_o1(), 0.01, 0.01, 60)["gecti"]


# ------------------------------------------------------------------ kapı sınırları (portföy)
def _m(**k):
    d = {"net_x2": 0.01, "sharpe_x1": sabit.P1_SHARPE_MIN, "gun": sabit.P2_MIN_GUN, "dengeleme": sabit.P2_MIN_DENGELEME,
         "net_en_iyi_yil_haric": 0.01, "kill_x1": 0}
    d.update(k)
    return d


def test_p1_p2_p3_p5_sinirlari():
    assert kos.kapi_portfoy(_m(), None, None, False, False)["gecti"]
    assert not kos.kapi_portfoy(_m(sharpe_x1=sabit.P1_SHARPE_MIN - 1e-9), None, None, False, False)["p1"]
    assert not kos.kapi_portfoy(_m(net_x2=0.0), None, None, False, False)["p1"]
    assert not kos.kapi_portfoy(_m(gun=sabit.P2_MIN_GUN - 1), None, None, False, False)["p2"]
    assert not kos.kapi_portfoy(_m(dengeleme=sabit.P2_MIN_DENGELEME - 1), None, None, False, False)["p2"]
    assert not kos.kapi_portfoy(_m(net_en_iyi_yil_haric=0.0), None, None, False, False)["p3"]
    assert not kos.kapi_portfoy(_m(net_en_iyi_yil_haric=math.nan), None, None, False, False)["p3"]
    assert not kos.kapi_portfoy(_m(kill_x1=1), None, None, False, False)["p5"]
    assert not kos.kapi_portfoy(_m(sharpe_x1=math.nan), None, None, False, False)["gecti"]


def test_p4_yalniz_kesitsel_ve_sinir():
    assert kos.kapi_portfoy(_m(), sabit.P4_P_MAX, None, True, False)["p4"] is True
    assert kos.kapi_portfoy(_m(), sabit.P4_P_MAX + 1e-9, None, True, False)["p4"] is False
    assert kos.kapi_portfoy(_m(), math.nan, None, True, False)["gecti"] is False
    assert kos.kapi_portfoy(_m(), 0.9, None, False, False)["p4"] is None            # uygulanmayan satır: yok, geçmeyi engellemez
    assert kos.kapi_portfoy(_m(), 0.9, None, False, False)["gecti"]


def test_p6_siniri_kesin_buyuk():
    m = _m(sharpe_x1=1.0)
    assert kos.kapi_portfoy(m, None, 0.999999, False, True)["p6"] is True
    assert kos.kapi_portfoy(m, None, 1.0, False, True)["p6"] is False               # eşit geçmez (strateji > kıyas)
    assert kos.kapi_portfoy(m, None, math.nan, False, True)["gecti"] is False
    assert kos.kapi_portfoy(m, None, 5.0, False, False)["p6"] is None


# ------------------------------------------------------------------ eleme dönemi: başlangıç kesimi ve ısınma
def test_eleme_baslangici_oncesi_islem_sayilmaz_isinma_kullanilir():
    m = mum(24 * 365 * 3)
    st = SmaTest()
    ham, _ = kos.tek_ham(st, "BTCUSDT", "1h", 1.0, lambda s, t: (m, None), TABLO)
    assert len(ham) > 20
    bas = m.index[24 * 365 * 2]
    sayilan = int((pd.DatetimeIndex(ham["giris_zamani"]) >= bas).sum())
    assert 0 < sayilan < len(ham)
    o = kos.tek_donem(ham, "BTCUSDT", bas, 1.0, TABLO)
    assert o["n_ham"] == sayilan and o["n_islem"] <= sayilan
    assert sum(1 for _ in o["r_yil"]) <= 2                                        # yalnız 2023-... yılları
    # tam dönemde daha çok işlem sayılır
    t = kos.tek_donem(ham, "BTCUSDT", m.index[0], 1.0, TABLO)
    assert t["n_ham"] == len(ham)
    # ısınma: veri başlangıçtan değil tüm geçmişten koşulur; bas'tan hemen sonraki işlem, yalnız bas sonrası veriyle koşsaydı
    # SMA ısınması (L mum) bitmeden mümkün olmazdı
    L = int(st.parametreler["L"])
    erken = ham[(pd.DatetimeIndex(ham["giris_zamani"]) >= bas) & (pd.DatetimeIndex(ham["giris_zamani"]) < bas + L * pd.Timedelta(hours=1))]
    sonrasi = m[m.index >= bas]
    ham_k, _ = kos.tek_ham(st, "BTCUSDT", "1h", 1.0, lambda s, t: (sonrasi, None), TABLO)
    erken_k = ham_k[pd.DatetimeIndex(ham_k["giris_zamani"]) < bas + L * pd.Timedelta(hours=1)]
    assert len(erken) > 0 and len(erken_k) == 0


def test_replay_bas_oncesini_saymaz_ve_kill_kapisi_alt_hesapta():
    ham = pd.DataFrame({
        "giris_zamani": pd.to_datetime(["2022-01-01", "2023-03-01", "2024-03-01", "2024-09-01"], utc=True).as_unit("ns"),
        "cikis_zamani": pd.to_datetime(["2022-01-02", "2023-03-02", "2024-03-02", "2024-09-02"], utc=True).as_unit("ns"),
        "yon": np.array([1, 1, 1, 1], dtype=np.int8), "r": np.array([2.0, 2.0, 1.0, 1.0], dtype=np.float32),
        "sf": np.full(4, 0.02, dtype=np.float32), "stop_mesafe": np.full(4, 2.0, dtype=np.float32)})
    o = kos.tek_donem(ham, "BTCUSDT", pd.Timestamp("2024-01-01", tz="UTC"), 1.0, TABLO)
    assert o["n_ham"] == 2 and o["n_islem"] == 2 and set(o["r_yil"]) == {2024}
    assert o["r_yil"][2024] == pytest.approx(2.0)


# ------------------------------------------------------------------ rastgele giriş: tutma süresi ve çeyrek
def _rnd_veri(n=24 * 200):
    m = mum(n, "1h", bas="2023-12-15")
    return m


def test_rastgele_giris_tutma_suresi_ve_ceyrek_korunur():
    m = _rnd_veri()
    idx = m.index
    gi = [int(x) for x in np.linspace(400, len(idx) - 500, 8)]
    hold = [2, 4, 7, 13, 25, 3, 4, 9]
    d = pd.DataFrame({"giris_zamani": idx[gi], "cikis_zamani": [idx[g + h] for g, h in zip(gi, hold)], "yon": [1, -1] * 4,
                      "stop_mesafe": [float(m["kapanis"].iloc[g]) * 0.02 for g in gi]})
    ayr = []
    rastgele.sembol_simule(d, m, MotorAyarlari(), 40, np.random.default_rng(5), ayrinti=ayr)
    assert len(ayr) > 40 * 8 * 0.9
    qb, qe = rastgele.v2test.ceyrek_sinirlari(d["giris_zamani"])
    for k, j, h in ayr:
        assert h == hold[k]                                    # tutma süresi (mum) aynen
        assert qb[k] <= idx[j] < qe[k]                         # gerçek girişin takvim çeyreği
        assert j + h <= len(idx) - 1                           # tutma süresi kırpılmaz
    assert len({j for _, j, _ in ayr}) > 50                    # gerçekten dağılıyor


def test_rastgele_giris_alt_sinir_eleme_baslangicinin_oncesini_cekmez():
    m = _rnd_veri()
    idx = m.index
    g = int(np.searchsorted(idx, pd.Timestamp("2024-02-10", tz="UTC")))
    d = pd.DataFrame({"giris_zamani": [idx[g]], "cikis_zamani": [idx[g + 5]], "yon": [1], "stop_mesafe": [2.0]})
    bas = pd.Timestamp("2024-02-01", tz="UTC")
    ayr = []
    rastgele.sembol_simule(d, m, MotorAyarlari(), 300, np.random.default_rng(1), alt_sinir=bas, ayrinti=ayr)
    assert min(idx[j] for _, j, _ in ayr) >= bas
    ayr2 = []
    rastgele.sembol_simule(d, m, MotorAyarlari(), 300, np.random.default_rng(1), ayrinti=ayr2)
    assert min(idx[j] for _, j, _ in ayr2) < bas              # alt sınır yoksa çeyreğin başına kadar iner


def test_rastgele_giris_zaman_cikisi_tam_h_mum_sonra_acilis():
    """Stop hiç vurulmaz (çok geniş): R = (o[j+h] - o[j]) / risk; maliyetsiz ayar."""
    m = _rnd_veri()
    idx = m.index
    g, h = 700, 11
    d = pd.DataFrame({"giris_zamani": [idx[g]], "cikis_zamani": [idx[g + h]], "yon": [1], "stop_mesafe": [float(m["kapanis"].iloc[g]) * 5]})
    ay = MotorAyarlari(komisyon_taker_yuzde=0.0, kayma_bps=0.0, stop_kayma_bps=0.0)
    ayr = []
    toplam, _, _ = rastgele.sembol_simule(d, m, ay, 1, np.random.default_rng(9), ayrinti=ayr)
    _, j, hh = ayr[0]
    from motor.strateji import gostergeler as gst
    atr = gst.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14).to_numpy()
    mult = float(m["kapanis"].iloc[g]) * 5 / atr[g - 1]
    stop = m["kapanis"].iloc[j - 1] - mult * atr[j - 1]
    beklenen = (m["acilis"].iloc[j + hh] - m["acilis"].iloc[j]) / (m["acilis"].iloc[j] - stop)
    assert hh == h and toplam[0] == pytest.approx(beklenen)


def test_rastgele_giris_uygun_mum_yoksa_acik_hata():
    m = mum(300, "1h")
    d = pd.DataFrame({"giris_zamani": [m.index[250]], "cikis_zamani": [m.index[299]], "yon": [1], "stop_mesafe": [1.0]})
    with pytest.raises(ValueError):
        rastgele.sembol_simule(d, m, MotorAyarlari(), 5, np.random.default_rng(1), alt_sinir=m.index[299])


def test_p_degeri_v2_ile_ayni():
    sim = np.array([1.0, 2.0, 3.0, 4.0])
    assert rastgele.p_degeri(3.0, sim) == (1 + 2) / 5
    assert math.isnan(rastgele.p_degeri(math.nan, sim))


# ------------------------------------------------------------------ P6: al-tut kıyası ölçekleme
def _pf_veri():
    gun = pd.date_range("2024-01-01", periods=6, freq="D", tz="UTC")
    a = pd.DataFrame({"kapanis": [100.0, 110.0, 99.0, 99.0, 108.9, 108.9]}, index=gun)
    b = pd.DataFrame({"kapanis": [50.0, 50.0, 55.0, 60.5, 60.5, 66.55]}, index=gun)
    return {"A": a, "B": b}, gun


def test_p6_kiyas_esit_agirlik_ve_brut_olcekleme():
    v, gun = _pf_veri()
    k1 = kos.al_tut_getiri(v, ("A", "B"), gun, 1.0)
    ra = v["A"]["kapanis"].pct_change()
    rb = v["B"]["kapanis"].pct_change()
    beklenen = ((ra + rb) / 2).fillna(0.0)
    assert k1.to_numpy() == pytest.approx(beklenen.to_numpy())
    k05 = kos.al_tut_getiri(v, ("A", "B"), gun, 0.5)
    assert k05.to_numpy() == pytest.approx(0.5 * k1.to_numpy())
    assert k05.iloc[1] == pytest.approx(0.5 * (0.10 + 0.0) / 2)


def test_p6_kiyas_henuz_listelenmemis_sembol_ortalamaya_girmez():
    v, gun = _pf_veri()
    v["B"] = v["B"].iloc[3:]                       # B yalnız 4. günden başlar
    k = kos.al_tut_getiri(v, ("A", "B"), gun, 1.0)
    ra = v["A"]["kapanis"].pct_change()
    assert k.iloc[1] == pytest.approx(ra.iloc[1])                     # yalnız A
    assert k.iloc[3] == pytest.approx(ra.iloc[3])                     # B'nin ilk günü: getirisi yok (NaN) -> yalnız A
    rb = v["B"]["kapanis"].pct_change()
    assert k.iloc[4] == pytest.approx((ra.iloc[4] + rb.iloc[1]) / 2)


# ------------------------------------------------------------------ deterministik tohum
def test_rastgele_giris_ayni_girdi_ayni_cikti():
    m = _rnd_veri()
    idx = m.index
    gi = [500, 1500, 2500, 3500]
    d = pd.DataFrame({"giris_zamani": idx[gi], "cikis_zamani": [idx[g + 6] for g in gi], "yon": [1, 1, -1, 1], "stop_mesafe": [1.5] * 4})
    ay = MotorAyarlari()
    t = sabit.satir_tohumu("v3__cuma-15-est-tutma", "k2")
    a = rastgele.simule({"BTCUSDT": d}, lambda s: (m, ay), 60, t)
    b = rastgele.simule({"BTCUSDT": d}, lambda s: (m, ay), 60, t)
    assert np.array_equal(a["toplam_r"], b["toplam_r"]) and a["n_gecersiz"] == b["n_gecersiz"]
    c = rastgele.simule({"BTCUSDT": d}, lambda s: (m, ay), 60, t + 1)
    assert not np.array_equal(a["toplam_r"], c["toplam_r"])


def test_satir_sonucu_ayni_girdi_ayni_cikti():
    sat = sabit.satir_al(8)
    va = veri_al_fabrika()
    a = kos.satir_calistir(sat, va, None, TABLO, n_sim=40)
    b = kos.satir_calistir(sat, va, None, TABLO, n_sim=40)
    for x in (a, b):
        x.pop("sure_sn")
    assert a == b and a["durum"] in ("gecti", "elendi") and a["B"] == 40
    assert a["tohum_k2"] == sabit.satir_tohumu(sat.strateji, "k2")
    assert a["analiz_bas"].startswith("2022-01-01")


def test_rw_dizisi_isci_sayisindan_bagimsiz():
    def sim(b, tohum):
        return float(np.random.default_rng([tohum, b]).normal())
    a = kos.rw_sharpe_dizisi(sim, 130, 7, isci=1)
    b = kos.rw_sharpe_dizisi(sim, 130, 7, isci=2)
    assert len(a) == 130 and np.array_equal(a, b)


# ------------------------------------------------------------------ hata satırı elenir
def test_hata_veren_satir_elenmis_sayilir(monkeypatch):
    def patla(*a, **k):
        raise ValueError("sentetik hata")
    monkeypatch.setattr(kos, "tek_ham", patla)
    r = kos.satir_calistir(sabit.satir_al(8), veri_al_fabrika(), None, TABLO, n_sim=10)
    assert r["durum"] == "hata" and r["gecti"] is False and "ValueError: sentetik hata" in r["hata"]
    assert r["hata_turu"] == "hesap" and "Traceback" in r["hata_iz"] and r["no"] == 8


def test_altyapi_hatasi_isaretlenir(monkeypatch):
    def patla(*a, **k):
        raise FileNotFoundError("mum yok")
    monkeypatch.setattr(kos, "tek_ham", patla)
    r = kos.satir_calistir(sabit.satir_al(7), veri_al_fabrika(), None, TABLO, n_sim=10)
    assert r["durum"] == "hata" and r["hata_turu"] == "altyapi" and r["gecti"] is False


def test_desteklenmeyen_cikis_hata_olur_p_1_degil(monkeypatch):
    monkeypatch.setattr(destek, "satir_destek_st", lambda s, st: {"ok": False, "neden": "kismi çıkış"})
    r = kos.satir_calistir(sabit.satir_al(6), veri_al_fabrika(), None, TABLO, n_sim=10)
    assert r["durum"] == "hata" and "DestekHatasi" in r["hata"] and r.get("p_rastgele") is None


def test_portfoy_satiri_hata(monkeypatch):
    def patla(*a, **k):
        raise RuntimeError("portföy patladı")
    monkeypatch.setattr(kos, "pf_kos", patla)
    r = kos.satir_calistir(sabit.satir_al(1), None, None, TABLO, n_sim=5)
    assert r["durum"] == "hata" and not r["gecti"] and r["hata_turu"] == "hesap"


# ------------------------------------------------------------------ destek ön şartı
def test_destek_kontrol_dokuz_satir_ok():
    s = destek.destek_kontrol()
    assert len(s) == 9 and all(x["ok"] for x in s)
    for x in s[5:]:
        assert x["v2_tutma_korur"] is False                  # v2 yolu saat/seans çıkışlı satırlarda tutma süresini korumaz
        assert "v3.rastgele" in x["kullanilan"]


def test_destek_desteklenmeyen_modul_ok_degil():
    from motor.strateji.cikislar import CikisAyarlari
    st = kos.strateji_uret("v3__cuma-15-est-tutma").yeni()
    st.cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=5.0)
    r = destek.satir_destek_st(sabit.satir_al(8), st)
    assert r["ok"] is False and "geri_cekilme_yuzde" in r["neden"]


# ------------------------------------------------------------------ dondurma
def _kume(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.md").write_text("on kayit\n")
    return {"on_kayit": ["b.md"], "motor": ["a.py"]}


def test_dondurma_degisen_dosyayi_yakalar(tmp_path):
    k = _kume(tmp_path)
    yol = tmp_path / "dondurma.json"
    d = dondurma.yaz(yol, k, tmp_path, commit="abc123", git_kontrol=False)
    assert len(d["dosyalar"]["motor"]["a.py"]) == 64
    dondurma.dogrula(yol, lambda: k, tmp_path, commit_kontrol=False)                 # değişmedi: geçer
    (tmp_path / "a.py").write_text("x = 2\n")
    with pytest.raises(dondurma.DondurmaHatasi, match="a.py"):
        dondurma.dogrula(yol, lambda: k, tmp_path, commit_kontrol=False)
    (tmp_path / "a.py").write_text("x = 1\n")
    dondurma.dogrula(yol, lambda: k, tmp_path, commit_kontrol=False)
    (tmp_path / "c.py").write_text("y = 1\n")                                         # kümeye yeni dosya eklendi
    with pytest.raises(dondurma.DondurmaHatasi, match="c.py"):
        dondurma.dogrula(yol, lambda: {**k, "motor": ["a.py", "c.py"]}, tmp_path, commit_kontrol=False)
    (tmp_path / "a.py").unlink()                                                      # silindi
    with pytest.raises(dondurma.DondurmaHatasi):
        dondurma.dogrula(yol, lambda: k, tmp_path, commit_kontrol=False)


def test_dondurma_uzerine_yazilmaz_ve_eksik_dosya_hata(tmp_path):
    k = _kume(tmp_path)
    yol = tmp_path / "d.json"
    with pytest.raises(dondurma.DondurmaHatasi):
        dondurma.dogrula(yol, lambda: k, tmp_path, commit_kontrol=False)              # dondurma yok
    dondurma.yaz(yol, k, tmp_path, commit="abc", git_kontrol=False)
    with pytest.raises(dondurma.DondurmaHatasi, match="zaten var"):
        dondurma.yaz(yol, k, tmp_path, commit="abc", git_kontrol=False)


def test_dondurma_gercek_kumeler_ve_icerik():
    k = dondurma.girdi_kumeleri()
    assert {"on_kayit", "kodlama_csv", "maliyet", "motor", "motor_pf", "v3_kod", "girdi_takvim"} <= set(k)
    assert sum(1 for a in k if a.startswith("strateji:")) == 9
    assert "motor/arastirma/v3/kos.py" in k["v3_kod"] and "motor/arastirma/v2/test.py" in k["v3_kod"]
    assert "sonuclar/evren/maliyet_tablosu.csv" in k["maliyet"]
    d = dondurma.hesapla(k, commit="deadbeef")
    assert d["on_kayit_sha256"] and len(d["maliyet_tablosu_sha256"]) == 64 and len(d["satirlar"]) == 9 and d["git_commit"] == "deadbeef"


# ------------------------------------------------------------------ CLI
def test_cli_dondurma_olmadan_eleme_reddeder(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sabit, "DONDURMA", tmp_path / "yok.json")
    monkeypatch.setattr(sabit, "SATIR_DIZINI", tmp_path / "satir")
    monkeypatch.setattr(kos, "satir_calistir", lambda *a, **k: pytest.fail("dondurma olmadan satır koşulmamalı"))
    assert cli.main(["eleme"]) == 3
    assert "dondurma" in capsys.readouterr().err
    assert not (tmp_path / "satir").exists()
    with pytest.raises(dondurma.DondurmaHatasi):
        cli.eleme_calistir(dondurma_yol=tmp_path / "yok.json", cikti_dizini=tmp_path / "s")


def test_cli_hash_farkinda_eleme_durur(tmp_path, monkeypatch):
    k = _kume(tmp_path)
    yol = tmp_path / "d.json"
    dondurma.yaz(yol, k, tmp_path, commit="abc", git_kontrol=False)
    (tmp_path / "a.py").write_text("x = 99\n")
    monkeypatch.setattr(dondurma, "girdi_kumeleri", lambda: k)
    monkeypatch.setattr(dondurma, "git_commit", lambda: "abc")
    monkeypatch.setattr(sabit, "KOK", tmp_path)
    monkeypatch.setattr(kos, "satir_calistir", lambda *a, **k: pytest.fail("hash farkında satır koşulmamalı"))
    with pytest.raises(dondurma.DondurmaHatasi, match="ihlali"):
        cli.eleme_calistir(dondurma_yol=yol, cikti_dizini=tmp_path / "s")


def test_cli_destek_komutu_sentetik(capsys):
    assert cli.main(["destek"]) == 0
    c = capsys.readouterr().out
    assert c.count("OK —") == 9 and "satır 8" in c


def test_cli_eleme_satiri_yazar_ve_atlar(tmp_path, monkeypatch):
    k = _kume(tmp_path)
    yol = tmp_path / "d.json"
    dondurma.yaz(yol, k, tmp_path, commit="abc", git_kontrol=False)
    monkeypatch.setattr(dondurma, "girdi_kumeleri", lambda: k)
    monkeypatch.setattr(dondurma, "git_commit", lambda: "abc")
    monkeypatch.setattr(sabit, "KOK", tmp_path)
    monkeypatch.setattr(veri, "hazirla", lambda *a, **k: None)
    cagri = []

    def sahte(satir, *a, **k):
        cagri.append(satir.no)
        return {"gecti": False, "durum": "elendi", "hata": "", "hata_turu": "", "no": satir.no, "sure_sn": 0.0}
    monkeypatch.setattr(kos, "satir_calistir", sahte)
    out = cli.eleme_calistir(8, cikti_dizini=tmp_path / "s", dondurma_yol=yol, ilerleme=False)
    assert cagri == [8] and out[0]["dondurma_sha256"] == dondurma.sha256(yol)
    assert json.loads((tmp_path / "s" / "satir_8.json").read_text())["no"] == 8
    cli.eleme_calistir(8, cikti_dizini=tmp_path / "s", dondurma_yol=yol, ilerleme=False)
    assert cagri == [8]                                                               # biten satır yeniden koşulmaz


def test_altyapi_hatasi_yalniz_bir_kez_yeniden(tmp_path, monkeypatch):
    k = _kume(tmp_path)
    yol = tmp_path / "d.json"
    dondurma.yaz(yol, k, tmp_path, commit="abc", git_kontrol=False)
    monkeypatch.setattr(dondurma, "girdi_kumeleri", lambda: k)
    monkeypatch.setattr(dondurma, "git_commit", lambda: "abc")
    monkeypatch.setattr(sabit, "KOK", tmp_path)
    monkeypatch.setattr(veri, "hazirla", lambda *a, **k: None)
    sayac = []

    def sahte(satir, *a, **kw):
        sayac.append(1)
        return {"gecti": False, "durum": "hata", "hata": "FileNotFoundError: x", "hata_turu": "altyapi", "no": satir.no, "sure_sn": 0.0}
    monkeypatch.setattr(kos, "satir_calistir", sahte)
    s = tmp_path / "s"
    cli.eleme_calistir(7, cikti_dizini=s, dondurma_yol=yol, ilerleme=False)
    cli.eleme_calistir(7, cikti_dizini=s, dondurma_yol=yol, ilerleme=False)           # bayraksız: atlanır
    assert len(sayac) == 1
    r = cli.eleme_calistir(7, yeniden_altyapi=True, cikti_dizini=s, dondurma_yol=yol, ilerleme=False)[0]
    assert len(sayac) == 2 and r["yeniden_sayisi"] == 1 and "yeniden koşuldu" in r["guncelleme"]
    cli.eleme_calistir(7, yeniden_altyapi=True, cikti_dizini=s, dondurma_yol=yol, ilerleme=False)
    assert len(sayac) == 2                                                            # ikinci yeniden koşu yok


# ------------------------------------------------------------------ rapor
def _satir_json(no, **k):
    s = sabit.satir_al(no)
    d = {"no": no, "kart": s.kart, "strateji": s.strateji, "tur": s.tur, "tf": s.tf, "evren": ",".join(s.evren), "bas": "",
         "durum": "elendi", "gecti": False, "hata": "", "hata_turu": "", "nedenler": "V1 ...", "p_rastgele": 0.5}
    if s.tur == "tek":
        d.update(v1=False, v2=True, v3=False, v4=False, v5=True)
    else:
        d.update(p1=False, p2=True, p3=False, p4=None, p5=True, p6=False)
    d.update(k)
    return d


def test_rapor_csv_ve_md(tmp_path):
    k = _kume(tmp_path)
    dy = tmp_path / "d.json"
    dondurma.yaz(dy, k, tmp_path, commit="abcdef0123456789", git_kontrol=False)
    st = dondurma.sha256(dy)
    sd = tmp_path / "satir"
    sd.mkdir()
    for no in (1, 6, 8):
        (sd / f"satir_{no}.json").write_text(json.dumps(_satir_json(no, dondurma_sha256=st, **({"durum": "gecti", "gecti": True} if no == 6 else {}),
                                                                   **({"durum": "hata", "hata": "ValueError: x", "hata_turu": "hesap"} if no == 8 else {}))))
    df = rapor.rapor_yaz(sd, tmp_path / "eleme.csv", tmp_path / "R.md", dy, dogrula=False)
    assert len(df) == 9 and list(df["durum"]) == ["elendi", "kosulmadi", "kosulmadi", "kosulmadi", "kosulmadi", "gecti", "kosulmadi", "hata", "kosulmadi"]
    csv = pd.read_csv(tmp_path / "eleme.csv")
    assert len(csv) == 9 and {"v1", "p1", "durum", "hata", "p_rastgele"} <= set(csv.columns)
    md = (tmp_path / "R.md").read_text(encoding="utf-8")
    assert "performans beklentisi" in md and "HATA (elendi)" in md and "GEÇTİ" in md and "1 / 9" in md and "koşulmadı" in md
    (sd / "satir_1.json").write_text(json.dumps(_satir_json(1, dondurma_sha256="0" * 64)))
    with pytest.raises(dondurma.DondurmaHatasi, match="damga"):
        rapor.rapor_yaz(sd, tmp_path / "e2.csv", tmp_path / "R2.md", dy, dogrula=False)


# ------------------------------------------------------------------ v3 dönemi (sentetik; v1 dosyaları değişmez)
def test_veri_hazirla_donem_kaydi(monkeypatch):
    monkeypatch.setitem(we.DONEMLER, sabit.DONEM, {})
    monkeypatch.setattr(we, "donem_gerekce", we.donem_gerekce)
    monkeypatch.setitem(we._CFG, "donem", we._CFG["donem"])
    monkeypatch.setitem(we._CFG, "veri_dizini", we._CFG["veri_dizini"])
    monkeypatch.setenv("L3A_KILIT_LOG", str(sabit.KILIT_GUNLUGU))
    veri.hazirla()
    assert we.DONEMLER[sabit.DONEM] == {"bas": None, "bit": sabit.VERI_SONU, "kilit_ac": True}
    assert we.donem_gerekce(sabit.DONEM) == sabit.KILIT_GEREKCE and we._CFG["donem"] == sabit.DONEM
    assert "v3_eleme" not in {"2017_gelistirme", "holdout"} and we.DONEMLER["2017_gelistirme"]["bit"] == we.HOLDOUT_BAS   # v2 dönemi aynı


def test_veri_sinir_kontrolu():
    m = mum(100, "1d", bas="2026-06-01")
    veri.sinir_kontrol("X", "1d", m, None)
    m2 = mum(100, "1d", bas="2026-08-01")
    with pytest.raises(RuntimeError, match="VERI_SONU"):
        veri.sinir_kontrol("X", "1d", m2, None)


# ------------------------------------------------------------------ portföy uçtan uca (sentetik, kısa)
def _pf_al(evren):
    v, f = {}, {}
    for i, s in enumerate(evren):
        v[s] = mum(900 - 15 * i, "1d", seed=20 + i, bas=f"2022-01-{1 + i:02d}", vol=0.03)
        fi = pd.date_range(v[s].index[0], periods=len(v[s]) * 3, freq="8h", tz="UTC")
        f[s] = pd.DataFrame({"oran": np.random.default_rng(i).normal(0.0001, 0.0002, len(fi))}, index=fi)
    return v, f, []


def test_portfoy_satiri_uctan_uca_rastgele_agirlik_ve_determinizm():
    sat = sabit.satir_al(2)
    a = kos.satir_calistir(sat, None, _pf_al, TABLO, n_sim=3)
    b = kos.satir_calistir(sat, None, _pf_al, TABLO, n_sim=3)
    for x in (a, b):
        x.pop("sure_sn")
    assert a == b and a["durum"] in ("gecti", "elendi"), a.get("hata_iz")
    assert a["B"] == 3 and a["tohum_rw"] == sabit.satir_tohumu(sat.strateji, "rw") and 0 < a["p_rastgele"] <= 1
    assert a["p4"] in (True, False) and a["p6"] is None and a["p2"] is False          # kısa sentetik dönem: P2 kalır
    assert a["genis_kill"] in (0, 1) and "genis_net" in a and a["kill_x1"] in (0, 1)


def test_portfoy_satiri_al_tut_p6_ve_rastgele_yok():
    r = kos.satir_calistir(sabit.satir_al(5), None, _pf_al, TABLO, n_sim=3)
    assert r["durum"] in ("gecti", "elendi"), r.get("hata_iz")
    assert r["p4"] is None and r["p6"] in (True, False) and math.isnan(r["p_rastgele"]) and 0 <= r["ort_brut"]
    assert math.isfinite(r["kiyas_sharpe"])
