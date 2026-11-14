"""Kapanış ek 12 portföy ileri dönem koşusu: ölçüt mantığı, dönem kesimi, tek-koşu koruması (SENTETİK veri; holdout okunmaz)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from araclar import kapanis_ileri_sinav_pf as pf
from araclar import kapanis_kosu as kk
from motor.arastirma.kapanis.portfoy import PortfoyHesap

BAS = pf.DONEM_BAS
DONCHIAN = "KOD:v3__donchian-ansambl-vol-hedef"


def _satir(kimlik=DONCHIAN):
    return next(s for s in pf.kayit_satirlari(dogrula=False) if s["kimlik"] == kimlik)


def _veri(sembol, tf):
    idx = pd.date_range("2025-09-01", "2026-02-28", freq="D", tz="UTC")
    f = 100 + np.arange(len(idx)) * 0.1 + abs(hash(sembol)) % 7
    return pd.DataFrame({"acilis": f, "yuksek": f + 1, "dusuk": f - 1, "kapanis": f, "hacim": 1.0, "quote_hacim": 1e5}, index=idx), None


def _hesap_fn(kill_zamani=None, gunluk=0.002):
    def f(st, v, fon, evren_t, tf, carpan, tablo, lim):
        idx = pd.date_range("2025-09-01", "2026-02-28", freq="D", tz="UTC")
        g = pd.Series(gunluk / carpan, index=idx)
        g[idx < BAS] = -0.5                                       # ısınma dönemi ölçüme girmemeli
        deng = pd.Series(idx.day == 1, index=idx)
        kill = [] if kill_zamani is None else [{"tur": "kill_switch", "zaman": pd.Timestamp(kill_zamani, tz="UTC")}]
        return PortfoyHesap(carpan, (1 + g).cumprod() * 1e4, g, pd.DataFrame(), deng, kill, kill, 0, [], 0.0, 0.0)
    return f


def test_alti_kayit_cozulur():
    s = pf.kayit_satirlari()
    assert [x["kimlik"] for x in s] == list(pf.KIMLIKLER) and len(s) == 6
    assert "kullanıcı kararı 2026-11-14" in pf.GEREKCE and "ek 12" in pf.GEREKCE


def test_olcut_pf():
    assert pf.olcut_pf(0.1, 0, True, 0.05)["karar"] == "gecti"
    assert pf.olcut_pf(0.1, 0, True, 0.2)["karar"] == "al_tutu_gecemedi"
    assert pf.olcut_pf(0.1, 1, False, math.nan)["karar"] == "paper_cikar"
    assert pf.olcut_pf(0.0, 0, False, math.nan)["karar"] == "paper_cikar"
    assert pf.olcut_pf(0.1, 0, False, math.nan)["c_al_tutu_gecti"] is None


def test_yardimcilar():
    assert pf.net([0.1, 0.1]) == pytest.approx(0.21)
    assert pf.max_dusus([0.1, -0.5, 0.0]) == pytest.approx(0.5)
    assert pf.kill_say([{"zaman": "2025-10-01"}, {"zaman": "2025-12-01"}]) == (1, 1)
    g = pd.Series(1.0, index=pd.date_range("2025-11-06", periods=5, freq="D", tz="UTC"))
    assert len(pf.donem_getiri(g, BAS, pd.Timestamp("2025-11-10", tz="UTC"))) == 2


def test_kayit_kos_yalniz_donem_icinde():
    r = pf.kayit_kos(_satir(), kk.TABLO, _veri, _hesap_fn())
    assert r["net_x1"] > 0 and r["net_x2"] > 0 and r["net_x2"] < r["net_x1"]      # -%50'lik ısınma günleri dışarıda
    assert r["long_only"] is True and not math.isnan(r["bh_net_x2"])
    assert r["kill_x2"] == 0 and r["dengeleme"] >= 3 and r["gun"] > 100
    assert r["karar"] in ("gecti", "al_tutu_gecemedi")


def test_long_degilse_al_tut_yok():
    r = pf.kayit_kos(_satir("KOD:pf__v3-funding-kesit-decil-carry"), kk.TABLO, _veri, _hesap_fn())
    assert r["long_only"] is False and r["c_al_tutu_gecti"] is None and math.isnan(r["bh_net_x2"])


def test_donem_ici_kill_paperdan_cikarir():
    r = pf.kayit_kos(_satir(), kk.TABLO, _veri, _hesap_fn(kill_zamani="2025-12-15"))
    assert r["kill_x2"] == 1 and r["karar"] == "paper_cikar"


def test_isinmada_kill_hata():
    with pytest.raises(RuntimeError, match="ısınma"):
        pf.kayit_kos(_satir(), kk.TABLO, _veri, _hesap_fn(kill_zamani="2025-10-15"))


def test_tek_kosu_ve_hata_kaydi(tmp_path):
    cikti = tmp_path / "o"
    s = pf.kos([_satir()], cikti, kk.TABLO, _veri, _hesap_fn())
    assert len(s) == 1
    for ad in ("sonuc.csv", "rapor.md", pf.ISARET):
        assert (cikti / ad).exists()
    assert list(pd.read_csv(cikti / "sonuc.csv").columns) == pf.SUTUNLAR
    with pytest.raises(pf.TekKosuHatasi):
        pf.kos([_satir()], cikti, kk.TABLO, _veri, _hesap_fn())
    with pytest.raises(SystemExit):
        pf.main(["--zorla"])

    def kotu(*a, **k):
        raise RuntimeError("bu evrende uygun değil")
    h = pf.kos([_satir()], tmp_path / "h", kk.TABLO, _veri, kotu)
    assert h[0]["karar"] == "HATA" and "uygun değil" in h[0]["hata"]
    assert "HATA" in (tmp_path / "h" / "rapor.md").read_text(encoding="utf-8")


def test_kuru_veri_okumaz(monkeypatch):
    def yasak(*a, **k):
        raise AssertionError("kuru modda veri okunmamalı")
    monkeypatch.setattr(pf, "tf_mumlari", yasak)
    monkeypatch.setattr(pf.depo, "funding_oku", yasak)
    monkeypatch.setattr(pf.depo, "mum_oku", yasak)
    pf.main(["--kuru", "--cikti", "/nonexistent_xyz/o"])


def test_taze_sermaye_isinmada_islem_ve_kill_yok():
    """hesap_ileri: dönem öncesi özsermaye düz 10.000, işlem yok, kill yok; dönem içinde işlem açılabilir."""
    s = _satir()
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    v = {}
    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        idx = pd.date_range("2025-01-01", "2026-02-28", freq="D", tz="UTC")
        f = 100 * np.exp(np.cumsum(np.random.default_rng(abs(hash(sym)) % 99).normal(0.003, 0.02, len(idx))))
        v[sym] = pd.DataFrame({"acilis": f, "yuksek": f * 1.01, "dusuk": f * 0.99, "kapanis": f, "hacim": 1.0, "quote_hacim": 1e5}, index=idx)
    st = tum_portfoy_stratejileri()[s["sinif"]](**__import__("json").loads(s["parametreler"]))
    lim = {"islem_risk": 1.5, "kill": 30.0, "toplam_risk": 7.5}
    h = pf.hesap_ileri(st, v, {}, tuple(v), "1d", 2.0, kk.TABLO, lim, BAS)
    once = h.ozsermaye[pd.DatetimeIndex(h.ozsermaye.index) < BAS]
    assert len(once) > 100 and (once == 10_000.0).all()                     # taze sermaye, ısınmada düz
    assert not h.dengeleme[pd.DatetimeIndex(h.dengeleme.index) < BAS].any()
    assert not h.kill_olaylari
    if len(h.islemler):
        assert (pd.to_datetime(h.islemler["giris_zamani"], utc=True) >= BAS).all()
