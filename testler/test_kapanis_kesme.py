"""Kesme (lookahead) testi: TÜM kod_g8_kod_1..8 ve kod_g8_modul VARYANTLAR kayıtları için sinyaller(m.iloc[:k]) == sinyaller(m).iloc[:k]
(tüm sütunlar, birkaç k). Ayrıca kanca kullanan sınıflar için motorla backtest: kanca çıkışı True döndüğü mumun sonraki açılışında, nedeni
"kanca" olarak gelir ve kanca yalnız kapanmış mumları görür."""
from __future__ import annotations

import importlib
import inspect

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.kapanis import (jesse_kaynak, k2_kaynak, kod_g8_kod_1, kod_g8_kod_2, kod_g8_kod_3, kod_g8_kod_4, kod_g8_kod_5,
                                    kod_g8_kod_6, kod_g8_kod_7, kod_g8_kod_8, kod_g8_modul)
from motor.strateji.temel import Strateji

DOSYALAR = [kod_g8_kod_1, kod_g8_kod_2, kod_g8_kod_3, kod_g8_kod_4, kod_g8_kod_5, kod_g8_kod_6, kod_g8_kod_7, kod_g8_kod_8, kod_g8_modul]
FREQ = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "2h": "2h", "3h": "3h", "4h": "4h", "6h": "6h", "8h": "8h", "1d": "D"}
N = 2600
KESME = (1300, 1777, 2050, 2399)


def _siniflar() -> dict:
    """Strateji alt sınıflarının ad -> sınıf sözlüğü (modül düzeyi sınıflar + SINIFLAR liste/sözlükleri + dış modüller)."""
    sozluk = {}
    for mod in DOSYALAR + [jesse_kaynak, k2_kaynak]:
        adaylar = [v for _, v in inspect.getmembers(mod, inspect.isclass)]
        koleksiyon = getattr(mod, "SINIFLAR", None)
        if isinstance(koleksiyon, dict):
            adaylar += list(koleksiyon.values())
        elif isinstance(koleksiyon, (list, tuple)):
            adaylar += [v for v in koleksiyon if inspect.isclass(v)]
        adaylar += [v for v in vars(mod).values() if inspect.isclass(v)]
        for c in adaylar:
            if issubclass(c, Strateji) and c is not Strateji and getattr(c, "ad", ""):
                sozluk.setdefault(c.ad, c)
    return sozluk


SINIF = _siniflar()
KAYITLAR = [(mod.__name__.rsplit(".", 1)[1], k) for mod in DOSYALAR for k in mod.VARYANTLAR]


def _mumlar(freq: str, tohum: int, n: int = N) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    vol = 0.012 * (1.0 + 0.8 * np.sin(t / 55.0) ** 2)
    siclama = (rng.random(n) < 0.02) * rng.normal(0.0, 4.0, n)
    getiri = (rng.normal(0.0004, 1.0, n) + siclama) * vol + 0.004 * np.sin(t / 23.0)
    kap = 100 * np.exp(np.cumsum(getiri) + 0.35 * np.sin(t / 90.0))
    ac = np.r_[kap[0], kap[:-1]] * (1 + rng.normal(0, vol / 4))
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, vol / 2)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, vol / 2)))
    hacim = rng.lognormal(4, 0.6, n)
    hacim[rng.random(n) < 0.1] *= 6
    idx = pd.date_range("2020-01-01", periods=n, freq=freq, tz="UTC")
    m = pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap, "hacim": hacim}, index=idx)
    m["funding_orani"] = rng.normal(0.0, 1.5e-3, n)           # yalnız funding_gerekli sınıflar kullanır
    return m


def _ornek(kayit):
    sinif = SINIF[kayit["sinif"]]
    return sinif(**kayit["parametreler"])


def test_tum_kayitlar_cozulur_ve_tf_desteklenir():
    assert len(KAYITLAR) >= 430
    for dosya, k in KAYITLAR:
        assert k["sinif"] in SINIF, (dosya, k["kimlik"])
        assert k["tf"] in FREQ, (dosya, k["kimlik"], k["tf"])          # 1w / 1M gibi desteklenmeyen TF yok
        assert "#v" in k["kimlik"]
    kimlikler = [k["kimlik"] for _, k in KAYITLAR]
    assert len(kimlikler) == len(set(kimlikler))                       # dosyalar arası çift kayıt yok
    kodlanamadi = [k["kimlik"] for d in DOSYALAR for k in d.KODLANAMADI]
    assert len(kodlanamadi) == len(set(kodlanamadi))
    assert not ({k.rsplit("#v", 1)[0] for k in kimlikler} & set(kodlanamadi))
    assert all(k.get("yaklasik") is True for _, k in KAYITLAR if "yaklasik" in k)


@pytest.mark.parametrize("dosya,kayit", KAYITLAR, ids=lambda x: x if isinstance(x, str) else x["kimlik"] + "-" + x["tf"])
def test_kesme_tum_sutunlar(dosya, kayit):
    """sinyaller(m.iloc[:k]) == sinyaller(m).iloc[:k]; iki sentetik seri x birkaç kesme noktası, tüm sütunlar."""
    st = _ornek(kayit)
    for tohum in (3, 8):
        m = _mumlar(FREQ[kayit["tf"]], tohum)
        tam = st.sinyaller(m)
        assert list(tam.index) == list(m.index)
        for k in KESME:
            pd.testing.assert_frame_equal(st.sinyaller(m.iloc[:k]), tam.iloc[:k], check_exact=False, rtol=1e-9, atol=1e-9)


def _kancali_kayitlar():
    return [(d, k) for d, k in KAYITLAR if callable(getattr(SINIF[k["sinif"]], "pozisyon_cikisi", None))]


def test_kancali_siniflar_var():
    adlar = {k["sinif"] for _, k in _kancali_kayitlar()}
    assert len(adlar) >= 25, "kanca kullanan sınıf sayısı beklenenden az"


@pytest.mark.parametrize("dosya,kayit", _kancali_kayitlar(), ids=lambda x: x if isinstance(x, str) else x["kimlik"] + "-" + x["tf"])
def test_kanca_backtest_cikis_nedeni(dosya, kayit):
    """Motorla koş: kanca True döndüğü mumun SONRAKİ açılışında çıkış 'kanca' olarak gelir (aynı açılışa stop/zaman vb. düşmedikçe);
    kanca yalnız kapanmış, indeksi geçerli mumlarda çağrılır."""
    for vol, tohum in ((None, 3), (None, 8), (None, 13), (None, 21)):
        m = _mumlar(FREQ[kayit["tf"]], tohum)
        st = _ornek(kayit)
        cagri, dogru = [], []
        orijinal = st.pozisyon_cikisi

        def sarmal(d, orijinal=orijinal, cagri=cagri, dogru=dogru, n=len(m)):
            assert 0 <= d.giris_mum_indeksi <= d.mum_indeksi < n and d.tutulan_mum >= 1
            s = bool(orijinal(d))
            cagri.append(d.mum_indeksi)
            if s:
                dogru.append(d.mum_indeksi)
            return s

        st.pozisyon_cikisi = sarmal
        r = backtest(m, st, MotorAyarlari())
        if dogru:
            break
    islem = r.islemler
    kanca_cikis = set(islem.loc[islem["cikis_nedeni"] == "kanca", "cikis_zamani"])
    beklenen = {m.index[i + 1] for i in dogru if i + 1 < len(m)}
    assert kanca_cikis <= beklenen
    if dogru:
        assert kanca_cikis, f"{kayit['kimlik']}: kanca True döndü ama 'kanca' nedenli çıkış yok"
    # kanca yalnız açık pozisyonda çağrılır: çağrı mumları bir işlemin [giriş, çıkış) aralığına düşer
    if cagri:
        giris = [m.index.get_loc(z) for z in islem["giris_zamani"]]
        cikis = [m.index.get_loc(z) if z in m.index else len(m) for z in islem["cikis_zamani"]]
        for i in cagri:
            assert any(g <= i < c for g, c in zip(giris, cikis)) or i == len(m) - 1
