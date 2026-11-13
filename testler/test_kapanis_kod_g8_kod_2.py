"""g8_kod_2 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR örneklenebilir."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.strateji.kapanis import kod_g8_kod_2 as K

_FREQ = {"5m": ("5min", 4000), "15m": ("15min", 4000), "1h": ("1h", 2500), "4h": ("4h", 3000), "1d": ("1D", 1500)}


def _mumlar(tf: str, tohum: int = 7) -> pd.DataFrame:
    freq, n = _FREQ[tf]
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    vol = 0.012 * (1.0 + 0.8 * np.sin(t / 55.0) ** 2)
    siclama = (rng.random(n) < 0.02) * rng.normal(0.0, 4.0, n)       # kalın kuyruk: nadir büyük mumlar
    getiri = (rng.normal(0.0004, 1.0, n) + siclama) * vol + 0.004 * np.sin(t / 23.0)
    fiyat = 100 * np.exp(np.cumsum(getiri) + 0.35 * np.sin(t / 90.0))
    acilis = np.r_[fiyat[0], fiyat[:-1]] * (1 + rng.normal(0, vol / 4))
    yuk = np.maximum(acilis, fiyat) * (1 + np.abs(rng.normal(0, vol / 2)))
    dus = np.minimum(acilis, fiyat) * (1 - np.abs(rng.normal(0, vol / 2)))
    idx = pd.date_range("2020-01-01", periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({"acilis": acilis, "yuksek": yuk, "dusuk": dus, "kapanis": fiyat, "hacim": 100.0}, index=idx)


def _veri(kayit) -> pd.DataFrame:
    m = _mumlar(kayit["tf"])
    if kayit["kimlik"].startswith("HAM:X005:192"):          # AR < 75 için uzun alt fitiller (kurala uygun sentetik seri)
        m["dusuk"] = m["dusuk"] * 0.97
    return m


def _ornek(kayit):
    return getattr(K, kayit["sinif"]) if False else next(c for c in _siniflar() if c.ad == kayit["sinif"])(**kayit["parametreler"])


def _siniflar():
    return [v for v in vars(K).values() if isinstance(v, type) and issubclass(v, K.Strateji) and v is not K.Strateji]


@pytest.mark.parametrize("kayit", K.VARYANTLAR, ids=lambda k: k["kimlik"])
def test_sinyal_stop_gelecek(kayit):
    st = _ornek(kayit)
    m = _veri(kayit)
    s = st.sinyaller(m)
    assert s.index.equals(m.index)
    giris = s["yon"] != 0
    assert giris.any(), "sentetik veride sinyal üretmeli"
    assert s.loc[giris, "stop"].notna().all()
    uzun, kisa = s["yon"] == 1, s["yon"] == -1
    assert (s.loc[uzun, "stop"] < m.loc[uzun, "kapanis"]).all()
    assert (s.loc[kisa, "stop"] > m.loc[kisa, "kapanis"]).all()
    assert st.cikis_var_mi()
    k = int(len(m) * 0.8)
    m2 = m.copy()
    kol = m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])
    m2.iloc[k:, kol] *= 2.5
    m2.iloc[k + 5::7, kol] *= 0.7
    s2 = st.sinyaller(m2)
    pd.testing.assert_frame_equal(s.iloc[:k], s2.iloc[:k])


def test_varyant_kayitlari_tam():
    kimlikler = [v["kimlik"] for v in K.VARYANTLAR]
    assert len(kimlikler) == len(set(kimlikler))
    assert {k["kimlik"] for k in K.KODLANAMADI} == {"HAM:X005:114"}
    kaynaklar = {k.split("#")[0] for k in kimlikler} | {k["kimlik"] for k in K.KODLANAMADI}
    import csv
    from pathlib import Path
    girdi = Path(__file__).resolve().parents[1] / "sonuclar/kapanis/kod_girdi/g8_kod_2.csv"
    if girdi.exists():
        tum = {r["kaynak_id"] for r in csv.DictReader(open(girdi, encoding="utf-8"))}
        assert kaynaklar == tum
    adlar = [c.ad for c in _siniflar()]
    assert len(adlar) == len(set(adlar)) and all(a.startswith("kapanis__") for a in adlar)
    assert {v["sinif"] for v in K.VARYANTLAR} == set(adlar)
    assert all(c.parametre_izgarasi == {} for c in _siniflar())


def test_s0138_tutma_gun_sutunu():
    st = K.SmaKesisSabitTutmaS0138(tutma_gun=5)
    s = st.sinyaller(_mumlar("1d"))
    assert (s.loc[s["yon"] != 0, "zaman_cikisi_mum"] == 5).all()


def test_s0144_durum_ve_cikis():
    st = K.EwmaKutleMerkeziS0144(hizli_com=3, yavas_com=12)
    m = _mumlar("1d")
    s = st.sinyaller(m)
    kap = m["kapanis"]
    fark = kap.ewm(com=3, adjust=False).mean() - kap.ewm(com=12, adjust=False).mean()
    assert ((s["cikis_long"]) == (fark < 0)).all() and ((s["cikis_short"]) == (fark > 0)).all()


def test_s0147_iz_suren_ve_zirve():
    st = K.TumZamanZirveIzS0147()
    m = _mumlar("1d")
    s = st.sinyaller(m)
    assert st.cikis_ayarlari.atr_iz_suren_k == 10.0
    assert (m.loc[s["yon"] == 1, "kapanis"] >= m["kapanis"].cummax()[s["yon"] == 1]).all()


def test_s0136_haftalik_gecikme_ve_yeni_hafta():
    m = _mumlar("1d")
    s = K.HaftalikKapanisKanaliS0136().sinyaller(m)
    gir = s.index[s["yon"] == 1]
    assert (gir.dayofweek == 0).all()      # yalnız yeni haftalık değerin göründüğü Pazartesi mumunda


def test_s0141_ay_sonu_durumu():
    m = _mumlar("1d")
    s = K.AylikSma10GtaaS0141().sinyaller(m)
    me = m["kapanis"][(m.index + pd.Timedelta(days=1)).month != m.index.month]
    durum = (me > me.rolling(10).mean()).reindex(m.index).ffill()
    beklenen = durum.where(me.rolling(10).mean().reindex(m.index).ffill().notna())
    uzun = s["yon"] == 1
    assert uzun.sum() > 0 and (beklenen[uzun] == True).all()  # noqa: E712


def test_s0222_stop_varyantlari():
    m = _mumlar("4h")
    a = K.BbKurulumTeyit4hS0222(stop_varyant="A").sinyaller(m)
    b = K.BbKurulumTeyit4hS0222(stop_varyant="B").sinyaller(m)
    ga = a["yon"] == 1
    assert np.allclose(a.loc[ga, "stop"], m["dusuk"].shift(1)[ga])
    gb = b["yon"] == 1
    assert np.allclose(b.loc[gb, "stop"], m["dusuk"].shift(2)[gb])
    with pytest.raises(ValueError):
        K.BbKurulumTeyit4hS0222(stop_varyant="C").sinyaller(m)


def test_s0229_hedef_15r():
    m = _mumlar("15m")
    s = K.Rsi3CokluTf15mS0229().sinyaller(m)
    g = s["yon"] == 1
    risk = m.loc[g, "kapanis"] - s.loc[g, "stop"]
    assert np.allclose((s.loc[g, "hedef"] - m.loc[g, "kapanis"]) / risk, 1.5)


def test_s0244_gun_sonu_ve_ilk_tetik():
    m = _mumlar("1h")
    s = K.GunIciHacimKirilimS0244().sinyaller(m)
    gir = s.index[s["yon"] == 1]
    assert len(gir) == len(set(gir.floor("D")))            # günde en çok bir giriş
    son = s.index[s["cikis_long"]]
    assert (son.hour == 23).all()


def _duz_mumlar(n=12) -> pd.DataFrame:
    idx = pd.date_range("2021-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame({"acilis": 100.0, "yuksek": 101.0, "dusuk": 99.0, "kapanis": 100.0, "hacim": 1.0}, index=idx)


def test_sanal_cikis_mumunda_giris_yok_ve_sonraki_mumda_var():
    m = _duz_mumlar()
    n = len(m)
    gl, gs, cl, cs = (np.zeros(n, bool) for _ in range(4))
    gl[3] = True
    gs[5] = gs[6] = True            # t=5: long açıkken ters giriş koşulu; kaynak sırası: önce çıkış
    cl[5] = True
    sl, ss = np.full(n, 90.0), np.full(n, 110.0)
    vl, vs, kl, ks = K._sanal(m, gl, gs, cl, cs, sl, ss)
    assert vl[3] and kl[5] and not vs[5] and vs[6]


def test_sanal_stop_ve_zaman_sonrasi_giris():
    m = _duz_mumlar()
    m.iloc[5, m.columns.get_loc("dusuk")] = 80.0     # t=5 bar içi stop
    n = len(m)
    gl = np.zeros(n, bool)
    gl[[2, 5, 8]] = True
    z = np.zeros(n, bool)
    sl, ss = np.full(n, 90.0), np.full(n, 110.0)
    vl, _, kl, _ = K._sanal(m, gl, z, z, z, sl, ss, max_mum=2)
    assert vl[2] and vl[5]          # stop mumunda (t=5) flat olunca giriş serbest
    assert not kl.any()


def test_s0189_uyarlanir_periyot_cikisi():
    # giriş sonrası periyot azalır: eşik SMA her gün kısalır
    m = _mumlar("1d")
    st = K.UyarlanirMaKanalS0189()
    s = st.sinyaller(m)
    assert s["cikis_long"].any() and (s["yon"] == 1).any()
    assert not (s["yon"] == -1).any()


def test_s0182_aroon_formulu():
    yuk = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0.5], float)
    dus = yuk - 0.5
    up, dn = K._aroon(yuk, dus, 10)
    assert up[9] == 100.0 and up[10] == 90.0 and np.isnan(up[8])
    assert dn[9] == 10.0            # en düşük pencerenin en eski mumunda: (10-9)/10x100
