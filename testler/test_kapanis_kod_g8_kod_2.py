"""g8_kod_2 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR örneklenebilir."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
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
    assert not K.KODLANAMADI           # 114 kod_g8_modul.KODLANAMADI'da
    kaynaklar = {k.split("#")[0] for k in kimlikler} | {"HAM:X005:114"}
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
    # stop mesafesi >= %50 ise ATR(14)x3 (kaynak 10xATR çok geniş)
    m2 = m.copy()
    m2["dusuk"] = m2["dusuk"] * 0.95
    m2["yuksek"] = m2["yuksek"] * 1.05
    s2 = st.sinyaller(m2)
    g2 = s2["yon"] == 1
    assert g2.any() and (s2.loc[g2, "stop"] > m2.loc[g2, "kapanis"] * 0.5).all()
    atr = K.g.atr(m2["yuksek"], m2["dusuk"], m2["kapanis"], 14)
    geniş = (m2["kapanis"] - 10 * atr) <= m2["kapanis"] * 0.5
    assert (geniş & g2).any() and np.allclose(s2.loc[geniş & g2, "stop"], (m2["kapanis"] - 3 * atr)[geniş & g2])


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


# ---------------------------------------------------------------- pozisyon bilinçli kanca (yaklaşık işaretleri kalktı)
def _kancali(sinif, tf="1d", **par):
    m = _mumlar(tf)
    st = sinif(**par)
    kayit = []
    orijinal = st.pozisyon_cikisi

    def sarmal(d):
        s = orijinal(d)
        if s:
            kayit.append(d)
        return s

    st.pozisyon_cikisi = sarmal
    return m, st, backtest(m, st, MotorAyarlari()), kayit


def test_yaklasik_isaretleri_kalkti_emin_degil_kaldi():
    assert not any(v.get("yaklasik") for v in K.VARYANTLAR)
    emin = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR if v.get("emin_degil")}
    assert emin == {"HAM:X005:" + k for k in ("187", "188", "192", "212", "213")}
    for sinif in (K.Keltner5mIzYuzdeS0174, K.HmaAtrKesisS0185, K.BbBantYonuS0186, K.SmaKesisAdxDiS0187, K.AtrKirilimS0188,
                  K.UyarlanirMaKanalS0189, K.MaDizilimArS0192, K.Stokastik533S0212, K.Rsi14Asiri2585S0213):
        assert callable(sinif().pozisyon_cikisi) and sinif().cikis_ayarlari.geri_cekilme_yuzde is None


@pytest.mark.parametrize("sinif,tf,esik,geri", [(K.SmaKesisAdxDiS0187, "1d", 35.0, 6.8), (K.AtrKirilimS0188, "1d", 20.0, 6.8),
                                                (K.MaDizilimArS0192, "1d", 25.0, 6.8), (K.Stokastik533S0212, "1d", 20.0, 6.8),
                                                (K.Rsi14Asiri2585S0213, "1d", 35.0, 6.8)],
                         ids=lambda x: getattr(x, "__name__", None))
def test_zirveden_yuzde_geri_cekilme_kancasi(sinif, tf, esik, geri):
    st = sinif()
    assert (st.parametreler["iz_kar_esik"], st.parametreler["iz_kar_geri"]) == (esik, geri)
    d = K.PozisyonDurumu if False else None
    from motor.strateji.cikislar import PozisyonDurumu as PD
    # zirve kârı eşiğin altında: çıkış yok; üstünde ve zirvenin %6,8 altında: çıkış
    assert not st.pozisyon_cikisi(PD(1, 100.0, 0, 5, 5, 100 * (1 + (esik - 1) / 100), 99.0, 100 * (1 + (esik - 1) / 100) * 0.9, -5.0))
    zirve = 100 * (1 + (esik + 5) / 100)
    assert st.pozisyon_cikisi(PD(1, 100.0, 0, 5, 5, zirve, 99.0, zirve * (1 - 0.0681), 0.0))
    assert not st.pozisyon_cikisi(PD(1, 100.0, 0, 5, 5, zirve, 99.0, zirve * (1 - 0.06), 0.0))


def test_174_iz_yuzde_kanca_iki_yon():
    from motor.strateji.cikislar import PozisyonDurumu as PD
    st = K.Keltner5mIzYuzdeS0174()
    assert st.pozisyon_cikisi(PD(1, 100.0, 0, 3, 3, 105.0, 99.0, 105 * 0.9919, 4.0))
    assert not st.pozisyon_cikisi(PD(1, 100.0, 0, 3, 3, 105.0, 99.0, 105 * 0.9925, 4.0))
    assert st.pozisyon_cikisi(PD(-1, 100.0, 0, 3, 3, 101.0, 95.0, 95 * 1.0081, 4.0))
    m, st, r, kayit = _kancali(K.Keltner5mIzYuzdeS0174, "5m")
    assert len(r.islemler) > 0


def test_185_hma_stop_ve_yuzde3_hedef_gercek_pozisyondan():
    m, st, r, kayit = _kancali(K.HmaAtrKesisS0185)
    assert kayit, "kanca çıkışı üretmeli"
    atr = K.g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
    hh, hy = K.hma(m["kapanis"], 5), K.hma(m["kapanis"], 30)
    for d in kayit:
        i, s = d.mum_indeksi, d.giris_mum_indeksi - 1
        if d.yon == 1:
            stop = max(hy.iloc[s] - 2 * atr.iloc[s], (hh.iloc[s + 1:i + 1] - 2 * atr.iloc[s + 1:i + 1]).max())
            assert d.kapanis < stop or d.kar_yuzde >= 3.0
        else:
            stop = min(hy.iloc[s] + 2 * atr.iloc[s], (hh.iloc[s + 1:i + 1] + 2 * atr.iloc[s + 1:i + 1]).min())
            assert d.kapanis > stop or d.kar_yuzde >= 3.0


def test_189_uyarlanir_ma_gercek_yastan():
    m, st, r, kayit = _kancali(K.UyarlanirMaKanalS0189)
    assert kayit
    for d in kayit:
        i = d.mum_indeksi
        per = max(10, 50 - (i - (d.giris_mum_indeksi - 1)))
        assert d.kapanis < m["kapanis"].iloc[i - per + 1:i + 1].mean()


def test_186_en_yuksek_kapanistan_geri_cekilme():
    m, st, r, kayit = _kancali(K.BbBantYonuS0186)
    assert st.cikis_ayarlari.zaman_cikisi_mum == 22
    for d in kayit:
        tepe = m["kapanis"].iloc[d.giris_mum_indeksi:d.mum_indeksi + 1].max()
        assert (tepe / d.giris_fiyati - 1) * 100 >= 20.0 and d.kapanis <= tepe * (1 - 0.068) + 1e-9


def test_210_kapanis_bazli_yuzde_stop_yasa_zarar():
    st = K.Cci10DurumGecisS0210()
    assert st.cikis_ayarlari.yasa_bagli_zarar_cikisi == ((0.0, 1.0),)
    m = _mumlar("1d")
    r = backtest(m, st, MotorAyarlari())
    assert len(r.islemler) > 0
    for _, t in r.islemler[r.islemler["cikis_nedeni"] == "yasa_zarar"].iterrows():
        i = m.index.get_loc(t.cikis_zamani) - 1
        assert t.yon * (m["kapanis"].iloc[i] - t.giris_fiyati) / t.giris_fiyati * 100 <= -1.0 + 1e-9
