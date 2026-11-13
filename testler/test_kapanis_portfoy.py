"""Kapanış portföy araştırma hesabının sentetik fiyatla denetimi (veri/mumlar gerekmez)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import wf_evren_portfoy as wep
from motor.arastirma.kapanis import portfoy as kp
from motor.arastirma.v2.ham import HoldoutSizintisi
from motor.portfoy import motor as pmotor
from motor.risk.limitler import SERT_LIMITLER

TABLO = Path(__file__).resolve().parents[1] / "sonuclar/evren/v2/maliyet_tablosu_v2.csv"
EVREN = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
AD = "pf__sabit_sepet"
AYAR = {"takvim": "W"}   # sık yeniden dengeleme


def _mumlar(tohum: int, n: int = 900, baslangic="2021-01-01", cokus_gun=None, cokus=0.5) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    getiri = rng.normal(0.001, 0.02, n)
    kap = 100 * np.exp(np.cumsum(getiri))
    if cokus_gun is not None:
        kap[cokus_gun:] *= cokus
    acilis = np.r_[kap[0], kap[:-1]]
    if cokus_gun is not None:
        acilis[cokus_gun] = kap[cokus_gun]          # gap
    idx = pd.date_range(baslangic, periods=n, freq="1D", tz="UTC", name="zaman")
    yuksek = np.maximum(acilis, kap) * 1.005
    dusuk = np.minimum(acilis, kap) * 0.995
    return pd.DataFrame({"acilis": acilis, "yuksek": yuksek, "dusuk": dusuk, "kapanis": kap,
                         "hacim": np.full(n, 1000.0), "quote_hacim": np.full(n, 1e5)}, index=idx)


def _veri(**kw):
    m = {s: _mumlar(i + 1, **kw) for i, s in enumerate(EVREN)}
    return lambda sembol, tf: (m[sembol], None)


def _kos(veri, **kw):
    return kp.portfoy_kos(AD, AYAR, "1d", EVREN, veri, TABLO, **kw)


def test_parametreler_uygulaniyor_ve_kill_tetiklenmeyen_senaryo(monkeypatch):
    gorulen = []
    orijinal = wep._kos

    def _izle(*a, **k):
        gorulen.append(pmotor.SERT_LIMITLER)
        return orijinal(*a, **k)

    monkeypatch.setattr(wep, "_kos", _izle)
    r = _kos(_veri())
    assert gorulen and all(g.islem_basi_max_risk_yuzde == 1.5 and g.kill_switch_dusus_yuzde == 30.0
                           and g.portfoy_toplam_risk_yuzde == pytest.approx(7.5) for g in gorulen)
    assert kp.TOPLAM_RISK_YUZDE == pytest.approx(7.5)
    assert len(r.x1.islemler) > 0 and r.x1.dengeleme.sum() >= 1
    assert r.x1.kill_olaylari == [] and r.x2.kill_olaylari == []
    assert r.metrikler["kill_x1"] == 0
    assert r.x1.ozsermaye.iloc[0] > 0.9 * kp.BASLANGIC_SERMAYE


def test_kill_tetiklenen_senaryo_kalici():
    # tüm semboller 400. günde aniden -%60: gap'te stop dolumu, kayıp -%30'u aşar -> kill, sonra işlem yok
    r = _kos(_veri(cokus_gun=400, cokus=0.4))
    assert len(r.x1.kill_olaylari) == 1
    olay = r.x1.kill_olaylari[0]
    assert olay["dusus_yuzde"] >= 30.0 and olay["mod"] == "uygula"
    sonra = r.x1.islemler[pd.to_datetime(r.x1.islemler["giris_zamani"]) > olay["zaman"]]
    assert sonra.empty                                   # kalıcı kill
    assert r.metrikler["kill_x1"] == 1


def test_kill_esigi_parametresi_etkili():
    # varsayılan -%30'da kill yok, -%1'de (parametre) kill tetiklenir: parametre gerçekten motora ulaşıyor
    assert _kos(_veri()).x1.kill_olaylari == []
    assert len(_kos(_veri(), kill=1.0).x1.kill_olaylari) == 1


def test_maliyet_x2_net_x1_den_dusuk():
    r = _kos(_veri())
    assert r.x2.net_tum < r.x1.net_tum
    assert r.x2.islemler["komisyon"].sum() > r.x1.islemler["komisyon"].sum()
    assert r.metrikler["net_x2"] < r.metrikler["net_x1"]


def test_holdout_sonrasi_veri_acik_hata():
    veri = _veri(baslangic="2025-11-08", n=40)
    with pytest.raises(HoldoutSizintisi):
        _kos(veri)
    veri2 = _veri(baslangic="2024-03-01", n=800)          # 2025-11-07'den sonrasına uzanır
    with pytest.raises(HoldoutSizintisi):
        _kos(veri2)


def test_sert_limitler_degismedi_ve_geri_yuklenir():
    def kontrol():
        assert SERT_LIMITLER.portfoy_toplam_risk_yuzde == 5.0
        assert SERT_LIMITLER.islem_basi_max_risk_yuzde == 1.0 and SERT_LIMITLER.gunluk_max_kayip_yuzde == 3.0
        assert SERT_LIMITLER.kill_switch_dusus_yuzde == 20.0 and SERT_LIMITLER.max_kaldirac == 3.0
        assert pmotor.SERT_LIMITLER is SERT_LIMITLER
    kontrol()
    _kos(_veri())
    kontrol()
    with pytest.raises(RuntimeError):
        with kp.arastirma_limitleri():
            raise RuntimeError("x")
    kontrol()


def test_gelecek_mum_gecmis_ozsermayeyi_degistirmez():
    ana = {s: _mumlar(i + 1, n=900) for i, s in enumerate(EVREN)}
    kes = 700
    kisa = {s: d.iloc[:kes] for s, d in ana.items()}
    degisik = {s: d.copy() for s, d in ana.items()}
    for d in degisik.values():
        d.iloc[kes:, :4] = d.iloc[kes:, :4] * 0.3         # gelecek değişir
    uzun = lambda m: (lambda s, tf: (m[s], None))
    a = _kos(uzun(kisa)).x1.ozsermaye
    b = _kos(uzun(degisik)).x1.ozsermaye
    c = _kos(uzun(ana)).x1.ozsermaye
    ortak = a.index[:-2]                                  # veri_sonu kapanışı son satırı etkileyebilir
    pd.testing.assert_series_equal(a.loc[ortak], c.loc[ortak], check_freq=False)
    pd.testing.assert_series_equal(b.loc[ortak], c.loc[ortak], check_freq=False)
