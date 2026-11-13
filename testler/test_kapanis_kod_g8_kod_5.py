"""g8_kod_5 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR örneklenebilir."""
from __future__ import annotations

import csv
import functools
import pathlib
import warnings

import numpy as np
import pandas as pd
import pytest

from motor.strateji.kapanis import kod_g8_kod_5 as M

_FREKANS = {"1d": "D", "5m": "5min", "1h": "h", "4h": "4h", "8h": "8h", "1w": "7D"}
# (tohum, günlük oynaklık, sinüs periyodu): seyrek kurallar için birkaç farklı sentetik rejim
_ADAYLAR = [(0, 0.02, 40), (1, 0.02, 40), (2, 0.035, 25), (3, 0.03, 60), (4, 0.05, 15), (5, 0.02, 120), (6, 0.012, 300),
            (7, 0.04, 90), (8, 0.025, 200)]
_N = 2600
_IKI_YON_YOK = {"HAM:X005:438", "HAM:X005:448"}  # (bilgi) long-only sınıflar test (a)'da short beklemez


def _mumlar(tf: str, tohum: int, vol: float, per: int, n: int = _N) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0004, vol, n)) + 0.5 * np.sin(t / per))
    ac = kap * (1 + rng.normal(0, vol / 3, n))
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, vol / 3, n)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, vol / 3, n)))
    idx = pd.date_range("2018-01-01", periods=n, freq=_FREKANS[tf], tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(50, 150, n)}, index=idx)


def _funding(m: pd.DataFrame, tohum: int) -> pd.DataFrame:
    m = m.copy()
    m["funding_orani"] = np.random.default_rng(tohum + 100).standard_t(3, len(m)) * 0.0008
    return m


def _hazirla(st, tf, aday):
    m = _mumlar(tf, *aday)
    return _funding(m, aday[0]) if st.funding_gerekli else m


def _sinyal(st, m):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return st.sinyaller(m)


@functools.lru_cache(maxsize=None)
def _veri_bul(kimlik: str):
    kayit = next(v for v in M.VARYANTLAR if v["kimlik"] == kimlik)
    st = M.SINIFLAR[kayit["sinif"]](**kayit["parametreler"])
    for aday in _ADAYLAR:
        m = _hazirla(st, kayit["tf"], aday)
        s = _sinyal(st, m)
        if (s["yon"] != 0).any():
            return aday, m, s
    return None, None, None


KIMLIKLER = [v["kimlik"] for v in M.VARYANTLAR]


def _kayit(kimlik):
    return next(v for v in M.VARYANTLAR if v["kimlik"] == kimlik)


@pytest.mark.parametrize("kimlik", KIMLIKLER)
def test_sinyal_stop_gelecek(kimlik):
    kayit = _kayit(kimlik)
    st = M.SINIFLAR[kayit["sinif"]](**kayit["parametreler"])
    aday, m, s = _veri_bul(kimlik)
    assert m is not None, "sentetik veride sinyal üretmeli"
    assert st.cikis_var_mi()
    assert list(s.index) == list(m.index)
    # (c) stop dolu ve doğru tarafta
    uzun, kisa = s["yon"] == 1, s["yon"] == -1
    assert s.loc[uzun | kisa, "stop"].notna().all()
    assert (s.loc[uzun, "stop"] < m.loc[uzun, "kapanis"]).all()
    assert (s.loc[kisa, "stop"] > m.loc[kisa, "kapanis"]).all()
    hedef_l = s.loc[uzun, "hedef"].dropna()
    assert (hedef_l > m.loc[hedef_l.index, "kapanis"]).all()
    hedef_s = s.loc[kisa, "hedef"].dropna()
    assert (hedef_s < m.loc[hedef_s.index, "kapanis"]).all()
    # (b) son 300 mum değişince önceki sinyaller değişmez
    k = len(m) - 300
    m2 = m.copy()
    kol = m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])
    m2.iloc[k:, kol] *= 2.5
    if "funding_orani" in m2:
        m2.iloc[k:, m2.columns.get_loc("funding_orani")] *= -1.0
    pd.testing.assert_frame_equal(s.iloc[:k], _sinyal(st, m2).iloc[:k])


def test_varyantlar_biciimi_ve_orneklenebilir():
    kimlikler = [v["kimlik"] for v in M.VARYANTLAR]
    assert len(kimlikler) == len(set(kimlikler)) == 48
    assert len(M.SINIFLAR) == 36
    for v in M.VARYANTLAR:
        assert set(v) == {"kimlik", "sinif", "parametreler", "tf"}
        sinif = M.SINIFLAR[v["sinif"]]
        assert v["tf"] in _FREKANS
        assert sinif.ad == v["sinif"] and sinif.ad.startswith("kapanis__") and sinif.parametre_izgarasi == {}
        sinif(**v["parametreler"])
    for ad, sinif in M.SINIFLAR.items():
        assert ad.rsplit("-", 1)[-1].startswith("s0")
        assert sinif.__doc__ and "X005" in sinif.__doc__


def test_kaynak_satirlari_tam_kapsanir():
    yol = pathlib.Path(__file__).resolve().parents[1] / "sonuclar" / "kapanis" / "kod_girdi" / "g8_kod_5.csv"
    if not yol.exists():
        pytest.skip("girdi csv yok")
    with open(yol, encoding="utf-8", newline="") as f:
        ids = [r["kaynak_id"] for r in csv.DictReader(f)]
    kodlu = {v["kimlik"].split("#")[0] for v in M.VARYANTLAR}
    kodsuz = {k["kimlik"] for k in M.KODLANAMADI}
    assert len(ids) == 40
    assert not (kodlu & kodsuz)
    assert set(ids) == kodlu | kodsuz
    assert all(k["neden"] for k in M.KODLANAMADI)


# ---------------------------------------------------------------- kurala özgü denetimler
def _st(kimlik):
    kayit = _kayit(kimlik)
    return M.SINIFLAR[kayit["sinif"]](**kayit["parametreler"])


def test_cci_esik_kesisim_ve_sifir_cikis():
    from motor.strateji.gostergeler_b2 import cci
    for kim, e in (("HAM:X005:428#v1", 100.0), ("HAM:X005:428#v2", 200.0)):
        _, m, s = _veri_bul(kim)
        c = cci(m["yuksek"], m["dusuk"], m["kapanis"], 20)
        assert ((s["yon"] == 1) == ((c.shift(1) >= -e) & (c < -e))).all()
        assert ((s["yon"] == -1) == ((c.shift(1) < e) & (c >= e))).all()
        assert (s["cikis_long"] == ((c.shift(1) <= 0) & (c > 0))).all()


def test_bb_alt_ardisik_kural():
    from motor.strateji import gostergeler as g
    _, m, s = _veri_bul("HAM:X005:430#v1")
    k = m["kapanis"]
    alt = g.bollinger(k, 20, 2.0)["alt"]
    alti = (k < alt).fillna(False)
    beklenen = alti & (k > k.shift(1)) & alti.shift(1, fill_value=False) & alti.shift(2, fill_value=False)
    assert ((s["yon"] == 1) == beklenen).all()


def test_rsi5m_yuzde_stop_hedef():
    _, m, s = _veri_bul("HAM:X005:432#v1")
    u = s["yon"] == 1
    assert np.allclose(s.loc[u, "stop"], m.loc[u, "kapanis"] * 0.985)
    assert np.allclose(s.loc[u, "hedef"], m.loc[u, "kapanis"] * 1.02)
    d = s["yon"] == -1
    assert np.allclose(s.loc[d, "stop"], m.loc[d, "kapanis"] * 1.015)
    assert d.any()


def test_destek_kumesi_elle():
    dusuk = np.array([10.0, 10.02, 9.0, 12.0, 11.5, 11.52])
    kap = np.r_[np.full(5, 20.0), 11.6]
    # t=5: önceki 5 bar (t-1..t-5) dipleri [11.5, 12.0, 9.0, 10.02, 10.0]; kapanış 11.6 altındaki kümeler:
    # 10.0 ve 10.02 (%0,3 içinde) -> küme ortalaması 10.01; 11.5 tek; 9.0 tek -> en yakın destek 10.01
    s = M._destek_kumesi(dusuk, kap, 5, 2, 0.003)
    assert np.isnan(s[:5]).all()
    assert s[5] == pytest.approx(10.01)
    # küme yoksa pencere en düşüğü
    s2 = M._destek_kumesi(np.array([10.0, 11.0, 9.0, 12.0, 13.0, 14.0]), kap, 5, 2, 0.003)
    assert s2[5] == pytest.approx(9.0)


def test_sma_rsi_destek_cikis_ayarlari():
    st = _st("HAM:X005:450#v1")
    assert st.cikis_ayarlari.kismi == ((1.0, 0.5),) and st.cikis_ayarlari.basabas_r_esigi == 1.0
    _, m, s = _veri_bul("HAM:X005:450#v1")
    u = s["yon"] == 1
    risk = m.loc[u, "kapanis"] - s.loc[u, "stop"]
    assert np.allclose((s.loc[u, "hedef"] - m.loc[u, "kapanis"]) / risk, 2.0)


def test_kademeli_ve_roi_ayarlari():
    assert _st("HAM:X005:456#v1").cikis_ayarlari.kismi == ((1.0, 0.5),)
    assert _st("HAM:X005:548#v1").cikis_ayarlari.azalan_roi == ((0.0, 1.0),)
    assert _st("HAM:X005:549#v1").cikis_ayarlari.azalan_roi == ((0.0, 10.0),)
    assert _st("HAM:X005:552#v1").cikis_ayarlari.azalan_roi == ((0.0, 1.0),)
    ca = _st("HAM:X005:550#v1").cikis_ayarlari
    assert ca.azalan_roi == ((0.0, 10.0), (1.0, 5.0), (2.0, 2.5))
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (5.0, 10.0)
    ca = _st("HAM:X005:554#v1").cikis_ayarlari
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (15.0, 0.0)
    ca = _st("HAM:X005:556#v1").cikis_ayarlari
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (45.0, 50.0)
    assert _st("HAM:X005:508#v1").cikis_ayarlari.zaman_cikisi_mum == 1


def test_fonlama_esikleri():
    for kim, (lo, hi) in (("HAM:X005:508#v1", (-15.47, 18.8)), ("HAM:X005:508#v2", (-32.61, 35.93))):
        st = _st(kim)
        assert st.funding_gerekli
        _, m, s = _veri_bul(kim)
        bp = m["funding_orani"] * 1e4
        assert ((s["yon"] == 1) == (bp <= lo))[20:].all()   # ilk mumlarda ATR stopu yok
        assert ((s["yon"] == -1) == (bp >= hi))[20:].all()
        assert (s.loc[s["yon"] == 1, "yon"].index.isin(bp.index[bp <= lo])).all()
        assert (s.loc[s["yon"] == -1].index.isin(bp.index[bp >= hi])).all()
        assert (s["yon"] == -1).any() and (s["yon"] == 1).any()
    with pytest.raises(ValueError):
        _st("HAM:X005:508#v1").sinyaller(_mumlar("8h", 0, 0.02, 40).drop(columns=[]))


def test_sezonsal_yalniz_mevsim_icinde_girer():
    _, m, s = _veri_bul("HAM:X005:495#v1")
    md = m.index.month * 100 + m.index.day
    g = s["yon"] == 1
    assert g.any()
    assert ((md[g] >= 1016) | (md[g] < 420)).all()
    assert (s["yon"] != -1).all()
    # yaz aylarında (haziran-eylül) hiçbir giriş yok ve pozisyon (içeride) bayrağı değilse çıkış True
    assert not g[(md >= 600) & (md < 1000)].any()


def test_tsmom_sma_kurali():
    from motor.strateji import gostergeler as g
    _, m, s = _veri_bul("HAM:X005:540#v1")
    k = m["kapanis"]
    assert ((s["yon"] == 1) == (k > k.shift(10)).fillna(False))[20:].all()   # ilk mumlarda ATR stopu yok
    _, m, s = _veri_bul("HAM:X005:540#v6")   # sma, N=50
    assert ((s["yon"] == 1) == (m["kapanis"] > g.sma(m["kapanis"], 50)).fillna(False)).all()
    assert [v["parametreler"]["N"] for v in M.VARYANTLAR if v["kimlik"].startswith("HAM:X005:540#")] == [10, 50, 100, 200] * 2


def test_bb_n_varyantlari_ve_cikis():
    from motor.strateji import gostergeler as g
    assert [v["parametreler"]["bb_n"] for v in M.VARYANTLAR if v["kimlik"].startswith("HAM:X005:544#")] == [10, 20, 50, 250]
    _, m, s = _veri_bul("HAM:X005:544#v2")
    bb = g.bollinger(m["kapanis"], 20, 2.0)
    k = m["kapanis"]
    assert (s["cikis_long"] == ((k.shift(1) >= bb["ust"].shift(1)) & (k < bb["ust"])).fillna(False)).all()


def test_kama_sma_fark_cevirir():
    _, m, s = _veri_bul("HAM:X005:525#v1")
    assert (s["yon"] == -1).any() and (s["yon"] == 1).any()
    assert (s.loc[s["yon"] == 1, "cikis_short"]).all() and (s.loc[s["yon"] == -1, "cikis_long"]).all()


def test_nr7_icgun_short_ve_zirve():
    _, m, s = _veri_bul("HAM:X005:494#v1")
    assert (s["yon"] == -1).any() and (s["yon"] == 1).sum() == 0
    assert (s["cikis_short"] == (m["kapanis"] < m["acilis"])).all()
    _, m, s = _veri_bul("HAM:X005:503#v1")
    oran = m["kapanis"] / m["kapanis"].cummax()
    assert ((s["yon"] == 1) == (oran >= 0.95))[20:].all()


def test_ao_macd_ve_ema800():
    _, m, s = _veri_bul("HAM:X005:554#v1")
    assert (m.loc[s["yon"] == 1, "hacim"] > 0).all()
    assert np.allclose(s.loc[s["yon"] == 1, "stop"], m.loc[s["yon"] == 1, "kapanis"] * 0.85)


def test_kodlanamadi_listesi():
    ids = [k["kimlik"] for k in M.KODLANAMADI]
    assert ids == ["HAM:X005:436", "HAM:X005:446", "HAM:X005:447", "HAM:X005:553"]
    assert "pozisyon bilinçli çıkış gerekli" in M.KODLANAMADI[0]["neden"]
