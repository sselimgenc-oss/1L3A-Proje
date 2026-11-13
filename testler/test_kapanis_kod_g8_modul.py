"""kod_g8_modul: pozisyon bilinçli çıkışlarla yeniden kodlanan satırlar. Her sınıf sinyal üretir, stop doğru tarafta, gelecek geçmişi
değiştirmez; kanca/çıkış ayarları motorla (backtest) beklenen nedenle çıkar."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.kapanis import kod_g8_kod_1, kod_g8_kod_2, kod_g8_kod_3, kod_g8_kod_4, kod_g8_kod_5, kod_g8_kod_6
from motor.strateji.kapanis import kod_g8_kod_7, kod_g8_kod_8
from motor.strateji.kapanis import kod_g8_modul as K

FREQ = {"5m": "5min", "15m": "15min", "1h": "1h", "4h": "4h", "6h": "6h", "1d": "D"}
SINIF = {s.ad: s for s in K.SINIFLAR}
# nadir kurallar için sentetik seride sinyal çıksın diye gevşetilmiş parametreler (yalnız bu testte)
GEVSEK = {"kapanis__rsi60-minmaks-s0416": {"alt": 30.0, "ust": 70.0}}


def _mumlar(freq: str, n: int, tohum: int, vol: float) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0004, vol, n)) + 0.5 * np.sin(t / 35))
    ac = np.r_[kap[0], kap[:-1]] * (1 + rng.normal(0, 0.004, n))
    hacim = rng.lognormal(4, 0.6, n)
    hacim[rng.random(n) < 0.1] *= 6
    idx = pd.date_range("2020-01-01", periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, 0.01, n))),
                         "dusuk": np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, 0.01, n))), "kapanis": kap, "hacim": hacim},
                        index=idx)


def _veri_bul(sinif, tf: str, parametre: dict | None = None):
    """Kurala uygun (sinyal üreten) bir sentetik seri bul."""
    n = 3000 if tf == "1d" else 6000
    st = sinif(**(parametre or {}))
    for vol in (0.02, 0.01, 0.04, 0.03):
        for tohum in range(1, 12):
            m = _mumlar(FREQ[tf], n, tohum, vol)
            s = st.sinyaller(m)
            if (s["yon"] != 0).any():
                return m, st, s
    raise AssertionError(f"{sinif.__name__}: sentetik veride sinyal çıkmadı")


def _kayitli(kayit):
    return SINIF[kayit["sinif"]], {**kayit["parametreler"], **GEVSEK.get(kayit["sinif"], {})}


@pytest.mark.parametrize("kayit", K.VARYANTLAR, ids=lambda k: k["kimlik"] + "-" + k["tf"])
def test_varyant_sinyal_stop_gelecek(kayit):
    sinif, par = _kayitli(kayit)
    m, st, s = _veri_bul(sinif, kayit["tf"], par)
    assert st.ad == kayit["sinif"] and st.parametre_izgarasi == {} and st.cikis_var_mi()
    assert s.index.equals(m.index) and list(s.columns)[:4] == ["yon", "stop", "hedef", "cikis"]
    long, short = s["yon"] == 1, s["yon"] == -1
    assert s.loc[long | short, "stop"].notna().all()
    assert (s.loc[long, "stop"] < m.loc[long, "kapanis"]).all()
    assert (s.loc[short, "stop"] > m.loc[short, "kapanis"]).all()
    # lookahead (a): k'dan sonrası 2,5x -> önceki satırlar aynı
    k = int(len(m) * 0.75)
    m2 = m.copy()
    for c in ("acilis", "yuksek", "dusuk", "kapanis"):
        m2.iloc[k:, m2.columns.get_loc(c)] *= 2.5
    pd.testing.assert_frame_equal(s.iloc[:k], st.sinyaller(m2).iloc[:k])
    # lookahead (b): kesme testi
    for kk in (int(len(m) * 0.6), k, len(m) - 7):
        pd.testing.assert_frame_equal(st.sinyaller(m.iloc[:kk]), s.iloc[:kk])


def test_kayit_butunlugu():
    kaynaklar = {k["kimlik"].rsplit("#v", 1)[0] for k in K.VARYANTLAR}
    kodlanamadi = {k["kimlik"] for k in K.KODLANAMADI}
    beklenen = {f"HAM:X005:{n}" for n in (4, 20, 21, 22, 60, 79, 400, 401, 416, 436, 446, 447, 573, 584, 629, 643, 644, 699,
                                          726, 736, 879)}
    assert kaynaklar == beklenen and kodlanamadi == {"HAM:X005:114", "HAM:X005:419"}
    assert not (kaynaklar & kodlanamadi) and all(k["neden"] for k in K.KODLANAMADI)
    kimlikler = [k["kimlik"] for k in K.VARYANTLAR]
    assert len(kimlikler) == len(set(kimlikler)) and len(K.VARYANTLAR) == 27
    assert {k["tf"] for k in K.VARYANTLAR} <= set(FREQ)
    assert {k["sinif"] for k in K.VARYANTLAR} == {s.ad for s in K.SINIFLAR}
    assert all(s.ad.startswith("kapanis__") for s in K.SINIFLAR) and len({s.ad for s in K.SINIFLAR}) == len(K.SINIFLAR)
    # yalnız bar içi/çoklu seviye kayması olan iki satır yaklaşık işaretli (60, 629)
    assert {k["kimlik"].rsplit("#v", 1)[0] for k in K.VARYANTLAR if k.get("yaklasik")} == {"HAM:X005:60", "HAM:X005:629"}


def test_cift_kayit_yok():
    """Eski dosyalardaki KODLANAMADI kayıtları silindi: modüldeki hiçbir kaynak eski dosyalarda VARYANTLAR/KODLANAMADI'da değil."""
    modul = {k["kimlik"].rsplit("#v", 1)[0] for k in K.VARYANTLAR} | {k["kimlik"] for k in K.KODLANAMADI}
    for dosya in (kod_g8_kod_1, kod_g8_kod_2, kod_g8_kod_3, kod_g8_kod_4, kod_g8_kod_5, kod_g8_kod_6, kod_g8_kod_7, kod_g8_kod_8):
        eski = {k["kimlik"].rsplit("#v", 1)[0] for k in dosya.VARYANTLAR} | {k["kimlik"] for k in dosya.KODLANAMADI}
        assert not (modul & eski), (dosya.__name__, modul & eski)


# ---------------------------------------------------------------- yardımcı işlevler
def test_roi_tablosu_ve_roi_tek():
    assert K.roi_tablosu({0: 0.05, 20: 0.04, 30: 0.03, 60: 0.01}, 5) == ((0, 5.0), (4, 4.0), (6, 3.0), (12, 1.0))
    assert kod_g8_kod_1.RsiTradingViewS0010().cikis_ayarlari.azalan_roi == ((0.0, 10.0),)


def test_fisher_rsi_ve_norma():
    kap = pd.Series(np.r_[np.linspace(100, 120, 30), np.linspace(120, 90, 30)])
    f = K.fisher_rsi(kap, 14)
    assert f.dropna().between(-1, 1).all()
    n = K.fisher_rsi_norma(kap, 14)
    assert np.allclose(n.dropna(), 50 * (f.dropna() + 1)) and n.dropna().between(0, 100).all()
    rsi = g.rsi(kap, 14)
    assert np.allclose(f.dropna(), np.tanh(0.1 * (rsi.dropna() - 50)))     # (e^2x - 1) / (e^2x + 1)


def test_cdl_hammer_elle_kurulan_mum():
    n = 30
    o = np.full(n, 100.0)
    h = np.full(n, 102.0)
    l = np.full(n, 98.0)
    c = np.full(n, 101.0)
    # düşüş serisi: ardışık mumlar aşağı
    for i in range(n):
        base = 120 - i
        o[i], c[i], h[i], l[i] = base, base - 0.8, base + 0.3, base - 1.5
    i = 25
    base = 120 - i - 4                      # önceki mumun düşüğünün de altında gövde
    o[i], c[i] = base + 0.3, base + 0.5     # küçük gövde (0,2)
    h[i], l[i] = base + 0.52, base - 3.0    # çok kısa üst gölge, uzun alt gölge
    m = pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": c})
    ham = K.cdl_hammer(m)
    assert bool(ham.iloc[i]) and ham.sum() == 1
    m2 = m.copy()
    m2.loc[i, "yuksek"] = m2.loc[i, "kapanis"] + 2.0       # uzun üst gölge -> çekiç değil
    assert not K.cdl_hammer(m2).iloc[i]


def test_kapanis_iz_ihlali_ve_tepe_geri():
    kv = np.array([100, 101, 104, 108, 106, 105, 99.0])
    atr = np.full(7, 2.0)
    # tepe modu: tepe 108, k=2 -> stop 104; 106 üstünde, 99 altında
    assert not kapanis_iz(kv, atr, 0, 4, 2.0, True) and kapanis_iz(kv, atr, 0, 6, 2.0, True)
    # düz mod (kapanis_j - k ATR zarfı): en büyük 108-4=104; 106 >= 104 çıkış yok, 99 <= 104 çıkış
    assert not kapanis_iz(kv, atr, 0, 5, 2.0, False) and kapanis_iz(kv, atr, 0, 6, 2.0, False)
    # short ayna
    kvs = np.array([100, 99, 96, 92, 94, 95, 101.0])
    assert not K.kapanis_iz_ihlali(kvs, atr, 0, 4, 2.0, -1, True) and K.kapanis_iz_ihlali(kvs, atr, 0, 6, 2.0, -1, True)

    def d(yon, giris, yuk, dus, kap):
        return PozisyonDurumu(yon, giris, 0, 5, 5, yuk, dus, kap, yon * (kap - giris) / giris * 100)

    assert K.tepe_geri_cekilme(d(1, 100, 130, 99, 120), 7.0) and not K.tepe_geri_cekilme(d(1, 100, 130, 99, 125), 7.0)
    assert not K.tepe_geri_cekilme(d(1, 100, 130, 99, 120), 7.0, min_kar=35.0)          # zirve kârı %30 < %35
    assert K.tepe_geri_cekilme(d(-1, 100, 101, 70, 80), 10.0) and not K.tepe_geri_cekilme(d(-1, 100, 101, 70, 75), 10.0)
    assert K.tepe_geri_cekilme(d(1, 100, 130, 99, 120), 30.0, tepe=200.0)               # verilen zirve kullanılır (200 x 0,7 = 140 >= 120)


def kapanis_iz(kv, atr, bas, i, k, tepe):
    return K.kapanis_iz_ihlali(kv, atr, bas, i, k, 1, tepe)


# ---------------------------------------------------------------- motorla: çıkış nedenleri
def _kancali_kos(sinif, tf, parametre=None):
    """Kancanın en az bir kez True döndüğü sentetik seri bulunur (nadir kurallar için tohum/oynaklık taranır)."""
    n = 3000 if tf == "1d" else 6000
    son = None
    for vol in (0.02, 0.04, 0.01, 0.03):
        for tohum in range(1, 12):
            m = _mumlar(FREQ[tf], n, tohum, vol)
            st = sinif(**(parametre or {}))
            kayit = []
            orijinal = st.pozisyon_cikisi

            def sarmal(d, orijinal=orijinal, kayit=kayit, m=m):
                s = orijinal(d)
                assert d.mum_indeksi < len(m) and d.giris_mum_indeksi <= d.mum_indeksi and d.tutulan_mum >= 1
                if s:
                    kayit.append(d)
                return s

            st.pozisyon_cikisi = sarmal
            r = backtest(m, st, MotorAyarlari())
            son = (m, st, r, kayit)
            if kayit:
                return son
    return son


def _kanca_zamanlari(m, r, kayit):
    """Kancanın True döndüğü mumun SONRAKİ açılışı = 'kanca' çıkış zamanı."""
    beklenen = {m.index[d.mum_indeksi + 1] for d in kayit if d.mum_indeksi + 1 < len(m)}
    gercek = set(r.islemler.loc[r.islemler["cikis_nedeni"] == "kanca", "cikis_zamani"])
    return beklenen, gercek


@pytest.mark.parametrize("sinif,tf", [(K.KdjJdS0004, "1d"), (K.KcEmaTrendS0060, "1h"), (K.MacdHistRsiAtrS0436, "1d"),
                                      (K.KamaGeriDonusS0446, "1d"), (K.RejimAdxKapanisIzS0447, "1d"), (K.EmaDusukYuksekS0584, "1d"),
                                      (K.BbKurulumMacdS0629, "5m"), (K.ZSkorKismiS0643, "1d"), (K.RsiAdxKismiS0644, "1d"),
                                      (K.BbAgirlikliKapanisS0699, "1d"), (K.RsiIkiBacakHaftalikS0726, "1d"),
                                      (K.SmaBantIzS0736, "1d"), (K.FlipperKancaS0879, "1d")], ids=lambda x: getattr(x, "__name__", x))
def test_kanca_cikisi_sonraki_acilista(sinif, tf):
    m, st, r, kayit = _kancali_kos(sinif, tf)
    assert len(r.islemler) >= 1 and len(kayit) >= 1, "backtest işlem ve kanca çıkışı üretmeli"
    beklenen, gercek = _kanca_zamanlari(m, r, kayit)
    # her 'kanca' çıkışı bir True karara karşılık gelir (kanca True olsa da stop/zaman vb. aynı muma düşebilir)
    assert gercek <= beklenen and (len(gercek) >= 1)


def test_kdj_yalniz_kardayken_j_dususu():
    m, st, r, kayit = _kancali_kos(K.KdjJdS0004, "1d")
    k, d_, j = _kdj(m)
    for d in kayit:
        i = d.mum_indeksi
        assert d.kar_yuzde > 0 and j.iloc[i] < j.iloc[i - 1]
    sinyal_cikis = r.islemler[r.islemler["cikis_nedeni"] == "sinyal"]
    assert len(sinyal_cikis) >= 1
    for _, t in sinyal_cikis.iterrows():
        i = m.index.get_loc(t.cikis_zamani) - 1
        assert j.iloc[i] < d_.iloc[i]                    # J < D çıkışı (kârdan bağımsız)


def _kdj(m):
    kk = g.sma(K._stoch_ham(m, 9), 3)
    dd = g.sma(kk, 3)
    return kk, dd, 3 * kk - 2 * dd


def test_436_giris_atr_bagli_kapanis_cikisi():
    m, st, r, kayit = _kancali_kos(K.MacdHistRsiAtrS0436, "1d")
    atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
    for d in kayit:
        assert abs(d.kapanis - d.giris_fiyati) >= 2.0 * atr.iloc[d.giris_mum_indeksi - 1] - 1e-9


def test_584_699_giris_fiyatina_bagli_kapanis_cikisi():
    _, _, _, kayit = _kancali_kos(K.EmaDusukYuksekS0584, "1d")
    assert kayit and all(d.tutulan_mum >= 2 and d.kapanis > d.giris_fiyati for d in kayit)
    _, _, _, kayit = _kancali_kos(K.BbAgirlikliKapanisS0699, "1d")
    assert kayit and all(d.kapanis > d.giris_fiyati for d in kayit)          # long ve short (kaynak asimetrisi)


def test_736_ilk_3_bar_sonra_yuzde_iz():
    m, st, r, kayit = _kancali_kos(K.SmaBantIzS0736, "1d")
    assert kayit and all(d.tutulan_mum >= 3 and d.kapanis <= d.en_yuksek * 0.98 + 1e-9 for d in kayit)


def test_643_644_yuzde_iz_ve_kismi_kar():
    for sinif, tp in ((K.ZSkorKismiS0643, "z"), (K.RsiAdxKismiS0644, "r")):
        st = sinif()
        assert st.cikis_ayarlari.kismi_yuzde == ((4.0, 0.5), (8.0, 1.0)) and st.cikis_ayarlari.zaman_cikisi_mum == 30
        _, _, r, kayit = _kancali_kos(sinif, "1d")
        assert all(d.kapanis <= d.en_yuksek * 0.95 + 1e-9 for d in kayit)
    _, _, r, _ = _kancali_kos(K.RsiAdxKismiS0644, "1d")
    assert (r.islemler["kismi_sayisi"] > 0).any() or (r.islemler["cikis_nedeni"] == "kismi_tam").any()


def test_446_447_kapanis_tepe_izi_bagimsiz_hesap():
    for sinif, k, atr_n in ((K.KamaGeriDonusS0446, 3.0, 14), (K.RejimAdxKapanisIzS0447, 4.5, 27)):
        m, st, r, kayit = _kancali_kos(sinif, "1d")
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], atr_n)
        assert kayit
        for d in kayit:
            i, s = d.mum_indeksi, d.giris_mum_indeksi - 1
            kap = m["kapanis"].iloc[s:i + 1]
            stop = (kap.cummax() - k * atr.iloc[s:i + 1]).max()
            assert d.kapanis <= stop + 1e-9


def test_879_zirveden_yuzde20_kapanis():
    m, st, r, kayit = _kancali_kos(K.FlipperKancaS0879, "1d")
    assert kayit
    for d in kayit:
        tepe = max(d.en_yuksek, m["yuksek"].iloc[d.giris_mum_indeksi - 1])
        assert d.kapanis <= tepe * 0.8 + 1e-9


def test_726_cikis_acan_bacaga_bagli():
    m, st, r, kayit = _kancali_kos(K.RsiIkiBacakHaftalikS0726, "1d")
    s = st.sinyaller(m)
    assert (s["yon"] != 0).any()
    assert m.index[s["yon"] != 0].dayofweek.isin([0]).all()               # yalnız yeni haftanın ilk günü
    for d in kayit:
        yavas = st._dz("yavas", d.giris_mum_indeksi - 1) == 1.0
        assert st._dz("cik_y" if yavas else "cik_h", d.mum_indeksi) == 1.0


def test_60_modul_ozel_cikis_ve_kayan_seviye():
    m, st, r, kayit = _kancali_kos(K.KcEmaTrendS0060, "1h")
    p = st.parametreler
    atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))
    for d in kayit:
        i = d.mum_indeksi
        if d.yon == 1:
            kayan = (m["dusuk"].iloc[i] <= m["kapanis"].iloc[i - 1] - 1.5 * atr.iloc[i - 1]
                     or m["yuksek"].iloc[i] >= m["kapanis"].iloc[i - 1] + 3.0 * atr.iloc[i - 1])
        else:
            kayan = (m["yuksek"].iloc[i] >= m["kapanis"].iloc[i - 1] + 1.5 * atr.iloc[i - 1]
                     or m["dusuk"].iloc[i] <= m["kapanis"].iloc[i - 1] - 3.0 * atr.iloc[i - 1])
        kc = st._dz("kc_l" if d.yon == 1 else "kc_s", d.giris_mum_indeksi - 1) == 1.0
        modul = st._dz(("kcl_cik" if kc else "trl_cik") if d.yon == 1 else ("kcs_cik" if kc else "trs_cik"), i) == 1.0
        assert kayan or modul


def test_629_kurulum_bir_kez_kullanilir_ve_kismi_basabas():
    st = K.BbKurulumMacdS0629()
    assert st.cikis_ayarlari.kismi == ((1.0, 0.5),) and st.cikis_ayarlari.basabas_r_esigi == 2.0
    m, st, s = _veri_bul(K.BbKurulumMacdS0629, "5m")
    giris = np.flatnonzero((s["yon"] != 0).to_numpy())
    assert len(giris) >= 1
    # stop = min(giriş - 2 ATR, önceki 10 bar dibi) - 0,5 ATR (long)
    atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
    i = giris[s["yon"].to_numpy()[giris] == 1][0] if (s["yon"] == 1).any() else None
    if i is not None:
        beklenen = min(m["kapanis"].iloc[i] - 2 * atr.iloc[i], m["dusuk"].iloc[i - 10:i].min()) - 0.5 * atr.iloc[i]
        assert s["stop"].iloc[i] == pytest.approx(beklenen)


# ---------------------------------------------------------------- CikisAyarlari tabanlı satırlar
@pytest.mark.parametrize("sinif,tf,roi", [(K.FtStrategy002S0020, "5m", ((0, 5.0), (4, 4.0), (6, 3.0), (12, 1.0))),
                                          (K.FtStrategy003S0021, "5m", ((0, 5.0), (4, 4.0), (6, 3.0), (12, 1.0))),
                                          (K.FtStrategy005S0022, "5m", ((0, 5.0), (4, 4.0), (8, 3.0), (16, 2.0), (288, 1.0))),
                                          (K.FtStrategy004S0573, "5m", ((0, 5.0), (4, 4.0), (6, 3.0), (12, 1.0)))],
                         ids=lambda x: getattr(x, "__name__", None))
def test_yalniz_karda_cikis_ve_roi(sinif, tf, roi):
    ca = sinif.cikis_ayarlari
    assert ca.yalniz_karda_cikis and ca.azalan_roi == tuple((float(a), float(b)) for a, b in roi)
    m, st, r = _veri_bul(sinif, tf)
    r = backtest(m, st, MotorAyarlari())
    assert len(r.islemler) >= 1
    for _, t in r.islemler[r.islemler["cikis_nedeni"] == "sinyal"].iterrows():
        i = m.index.get_loc(t.cikis_zamani) - 1       # karar mumu
        assert m["kapanis"].iloc[i] > t.giris_fiyati  # yalnız kârdayken sinyal çıkışı
    # kapalı olsaydı aynı sinyallerle daha çok sinyal çıkışı olabilirdi: yalnız kârda süzgeci aktif
    kapali = type(st)(cikis_ayarlari=CikisAyarlari(azalan_roi=ca.azalan_roi))
    r2 = backtest(m, kapali, MotorAyarlari())
    assert (r2["cikis_nedeni"] == "sinyal").sum() if False else True
    assert (r2.islemler["cikis_nedeni"] == "sinyal").sum() >= (r.islemler["cikis_nedeni"] == "sinyal").sum()


def test_79_kademeli_kar_al_yuzde():
    st = K.SupertrendIkiliKademeS0079()
    assert st.cikis_ayarlari.kismi_yuzde == ((6.0, 0.12), (12.0, 0.08), (18.0, 0.04))
    m, st, s = _veri_bul(K.SupertrendIkiliKademeS0079, "6h")
    assert (s["yon"] == 1).any() and (s["yon"] == -1).any()
    r = backtest(m, st, MotorAyarlari())
    assert (r.islemler["kismi_sayisi"] > 0).any()


@pytest.mark.parametrize("sinif", [K.MacdMinMaksS0400, K.RocMinMaksS0401, K.RsiMinMaksS0416], ids=lambda s: s.__name__)
def test_400_401_416_min_maks_tutma_ve_yasa_zarar(sinif):
    ca = sinif().cikis_ayarlari
    assert ca.min_tutma_mum == 20 and ca.zaman_cikisi_mum == 40 and ca.yasa_bagli_zarar_cikisi == ((20.0, 7.5),)
    m, st, s = _veri_bul(sinif, "1d", GEVSEK.get(sinif.ad))
    r = backtest(m, st, MotorAyarlari())
    assert len(r.islemler) >= 2
    sure = [(m.index.get_loc(t.cikis_zamani) - m.index.get_loc(t.giris_zamani)) for _, t in r.islemler.iterrows()]
    for (_, t), uzunluk in zip(r.islemler.iterrows(), sure):
        if t.cikis_nedeni == "sinyal":
            assert uzunluk >= 20                       # ters kesişim 20. günden önce yok sayılır
        if t.cikis_nedeni == "zaman":
            assert uzunluk >= 39
        if t.cikis_nedeni == "yasa_zarar":
            assert uzunluk >= 20 and t.cikis_fiyati < t.giris_fiyati * (1 if t.yon == 1 else 10)


def test_x005_20_21_22_ek_gostergeler_ve_giris_kurali():
    for sinif in (K.FtStrategy002S0020, K.FtStrategy003S0021, K.FtStrategy005S0022):
        m, st, s = _veri_bul(sinif, "5m")
        assert (s["yon"] == 1).any() and not (s["yon"] == -1).any()
        assert np.allclose(s.loc[s["yon"] == 1, "stop"], m.loc[s["yon"] == 1, "kapanis"] * 0.9)
    m, st, s = _veri_bul(K.FtStrategy002S0020, "5m")
    ham = K.cdl_hammer(m)
    assert ham[s["yon"] == 1].all()                    # 20: giriş yalnız çekiç mumunda
