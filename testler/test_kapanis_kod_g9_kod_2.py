"""g9_kod_2 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.cikislar import PozisyonDurumu
from motor.strateji.kapanis import kod_g9_kod_2 as K

FREQ = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h"}
IKI_YON = {K.Mk4RsiGraB0227, K.ZaratustraV13B0056, K.ZaratustraV17B0057, K.ZaratustraV4B0058, K.KeltnerBbrB0064,
           K.ZaratustraLukeB0134}
SINIF_TF = {}
for _v in K.VARYANTLAR:
    SINIF_TF.setdefault(_v["sinif"], _v["tf"])
# sınıf -> (mum sayısı, tohum, oynaklık, hacim ölçeği): bazı kurallar seyrek tetiklenir / büyük hacim ister
VERI = {K.StarriseDipB0054: (12000, 11, 0.02, 100.0), K.EmaxZlsmaB0146: (12000, 3, 0.01, 100.0),
        K.LamboWrStochB0871: (6000, 7, 0.01, 100000.0)}


def _mumlar(freq: str, n: int = 6000, tohum: int = 7, vol: float = 0.01, hacim: float = 100.0, dalga: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    getiri = rng.standard_t(4, n) * vol + 0.0002 * np.sin(t / dalga * 2 * np.pi)
    kap = 100 * np.exp(np.cumsum(getiri) + 0.5 * np.sin(t / dalga))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    idx = pd.date_range("2020-01-01", periods=n, freq=FREQ[freq], tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(0.5, 1.5, n) * hacim}, index=idx)


def _veri(sinif, tf: str) -> pd.DataFrame:
    n, tohum, vol, hacim = VERI.get(sinif, (6000, 7, 0.01, 100.0))
    return _mumlar(tf, n, tohum, vol, hacim)


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_sinyal_stop_gelecek(sinif):
    st = sinif()
    m = _veri(sinif, SINIF_TF[st.ad])
    s = st.sinyaller(m)
    assert s.index.equals(m.index)
    long, short = s["yon"] == 1, s["yon"] == -1
    assert long.any(), "sentetik veride long sinyal üretmeli"
    if sinif in IKI_YON:
        assert short.any(), "iki yönlü kural short da üretmeli"
    else:
        assert not short.any()
    assert st.cikis_var_mi()
    assert s.loc[long | short, "stop"].notna().all()
    assert (s.loc[long, "stop"] < m.loc[long, "kapanis"]).all()
    assert (s.loc[short, "stop"] > m.loc[short, "kapanis"]).all()
    # lookahead: son 300 mum 2,5x olunca önceki sinyaller değişmez
    k = len(m) - 300
    m2 = m.copy()
    kolon = m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])
    m2.iloc[k:, kolon] *= 2.5
    s2 = st.sinyaller(m2)
    pd.testing.assert_frame_equal(s.iloc[:k], s2.iloc[:k])
    # veri sonunu kesmek de geçmişi değiştirmez
    s3 = st.sinyaller(m.iloc[:k + 1])
    pd.testing.assert_frame_equal(s.iloc[:k + 1], s3)


@pytest.mark.parametrize("kayit", K.VARYANTLAR, ids=lambda v: v["kimlik"])
def test_varyant_orneklenir(kayit):
    assert set(kayit) - {"modul"} == {"kimlik", "sinif", "parametreler", "tf"}
    assert "#v" in kayit["kimlik"] and kayit["tf"] in FREQ
    sozluk = {s.ad: s for s in K.SINIFLAR}
    st = sozluk[kayit["sinif"]](**kayit["parametreler"])
    m = _mumlar(kayit["tf"], 3000)
    s = st.sinyaller(m)
    assert len(s) == len(m)
    assert st.parametre_izgarasi == {}


def test_varyant_ve_kodlanamadi_kapsami():
    girdi = pd.read_csv("sonuclar/kapanis/kod_girdi/g9_kod_2.csv")
    kimlikler = set(girdi["kaynak_id"])
    kayitli = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR}
    kod_yok = {x["kimlik"] for x in K.KODLANAMADI}
    assert len(kimlikler) == 30
    assert kayitli | kod_yok == kimlikler
    assert not kayitli & kod_yok
    assert len({v["kimlik"] for v in K.VARYANTLAR}) == len(K.VARYANTLAR)
    assert all(x["neden"] for x in K.KODLANAMADI)
    assert kod_yok == {"HAM:B001:571", "HAM:B001:52", "HAM:B001:78", "HAM:B001:755"}
    adlar = [s.ad for s in K.SINIFLAR]
    assert len(set(adlar)) == len(adlar) and all(a.startswith("kapanis__") and "-b0" in a for a in adlar)
    assert len(K.SINIFLAR) == 26 and len(K.VARYANTLAR) == 26


def test_roi_donusumleri_ve_cikis_ayarlari():
    assert K.ElliotV7B0564.cikis_ayarlari.azalan_roi == ((0, 5.1), (2, 3.1), (5, 1.8), (14, 0.0))
    assert K.ElliotV7B0564.cikis_ayarlari.geri_cekilme_yuzde == 0.5
    assert K.ElliotV7B0564.cikis_ayarlari.geri_cekilme_min_kar_yuzde == 3.0
    assert K.NasosV5B0573.cikis_ayarlari.azalan_roi == ((72, 0.0),)
    assert K.NasosV5B0573.cikis_ayarlari.geri_cekilme_yuzde is None
    assert K.NasosV5Mod1B0574.cikis_ayarlari.azalan_roi == ((0, 40.0),)
    # 134: 1,3,5 dk aynı muma düşer -> büyük dakika geçerli (%50); 15 dk -> 3. mum %60
    assert K.ZaratustraLukeB0134.cikis_ayarlari.azalan_roi == ((1, 50.0), (3, 60.0))
    assert K.ZaratustraV4B0058.cikis_ayarlari.azalan_roi == ((0, 100.0), (1440, 0.0))
    # 136: ROI {0:1, 30:0,2, 60:-1} -> iki basamak + 2 mum sonra koşulsuz zaman çıkışı
    c = K.IchiV1B0136.cikis_ayarlari
    assert c.azalan_roi == ((0, 1.0), (1, 0.2)) and c.zaman_cikisi_mum == 2
    # 146: trailing_only_offset tanımsız -> lider kuralı: iz offsetten önce de çalışır (min kâr 0)
    assert K.EmaxZlsmaB0146.cikis_ayarlari.geri_cekilme_min_kar_yuzde == 0.0
    assert K.StarriseDipB0054.cikis_ayarlari.yalniz_karda_cikis and K.LamboWrStochB0871.cikis_ayarlari.yalniz_karda_cikis
    assert K.MarketCipherB0251.cikis_ayarlari.azalan_roi[1] == (4, 20.624)


def test_yardimcilar_gosterge_dogrulugu():
    x = pd.Series(np.arange(30, dtype=float) * 2.0 + 5.0)  # tam doğru: uç = son değer, eğim 2
    uc, egim = K._linreg(x, 5)
    assert np.allclose(uc.dropna(), x.iloc[4:]) and np.allclose(egim.dropna(), 2.0)
    y = pd.Series([1.0, 3.0, 2.0, 5.0, 4.0])
    e, k = np.polyfit(np.arange(5), y, 1)
    uc, egim = K._linreg(y, 5)
    assert np.isclose(uc.iloc[-1], e * 4 + k) and np.isclose(egim.iloc[-1], e)
    z = pd.Series(np.random.default_rng(1).normal(size=40)).cumsum()
    assert np.isclose(K._cti(z, 10).iloc[-1], np.corrcoef(z.iloc[-10:], np.arange(10))[0, 1])
    sabit = pd.Series(np.full(20, 5.0))
    assert np.allclose(K._tema(sabit, 4).dropna(), 5.0)
    assert np.isclose(K._cmo(z, 14).iloc[-1], 2 * K.g.rsi(z, 14).iloc[-1] - 100)
    # qtpylib std ddof=1, TA-Lib BBANDS ddof=0
    a = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    assert np.isclose(K._bb(a, 5, 1.0, 1)["ust"].iloc[-1], 3 + np.std([1, 2, 3, 4, 5], ddof=1))
    assert np.isclose(K._bb(a, 5, 1.0, 0)["ust"].iloc[-1], 3 + np.std([1, 2, 3, 4, 5]))


def test_nasos5_custom_stoploss_kademeleri_ve_kanca():
    kar = np.array([0.0, 0.02, 0.03, 0.05, 0.07, 0.2, 0.35])
    assert list(K._nasos5_mesafe(kar, None)) == [0.15, 0.005, 0.005, 0.01, 0.02, 0.03, 0.05]
    st = K.NasosV5B0573()
    st._sakla(kap=np.array([100.0, 108.0, 107.5, 107.4]))
    d = lambda i: PozisyonDurumu(yon=1, giris_fiyati=100.0, giris_mum_indeksi=0, mum_indeksi=i, tutulan_mum=i,  # noqa: E731
                                 en_yuksek=108.0, en_dusuk=100.0, kapanis=0.0, kar_yuzde=0.0)
    # %8 kârda mesafe %2 -> stop 105,84; 107,4 üstünde: çıkış yok
    assert not st.pozisyon_cikisi(d(3))
    st._sakla(kap=np.array([100.0, 108.0, 105.0]))
    assert st.pozisyon_cikisi(d(2))          # 105 <= 108 x 0,98


def test_ralli_ve_starrise_kancalari():
    assert list(K._ralli_mesafe(np.array([0.0, 0.0, 0.01]), np.array([10, 29, 40]))) == [1.0, 0.005, 1.0]
    st = K.StarriseDipB0054()
    d = lambda i: PozisyonDurumu(yon=1, giris_fiyati=100.0, giris_mum_indeksi=0, mum_indeksi=i, tutulan_mum=i,  # noqa: E731
                                 en_yuksek=0.0, en_dusuk=0.0, kapanis=0.0, kar_yuzde=0.0)
    st._sakla(kap=np.array([100.0, 102.0, 101.9]))      # %2 kâr: stop ~ +%1,95 -> 101,9 ihlal
    assert st.pozisyon_cikisi(d(2))
    st._sakla(kap=np.array([100.0, 101.0, 100.5]))      # kâr < %1,1: kilit yok (pHSL -0,998 pratikte yok)
    assert not st.pozisyon_cikisi(d(2))


def _kancali_backtest(sinif, tf="5m", n=6000, tohum=3, vol=0.02):
    m = _mumlar(tf, n, tohum, vol)
    st = sinif()
    return st, backtest(m, st, MotorAyarlari())


@pytest.mark.parametrize("sinif", [K.NasosV5B0573, K.RalliV1B0590, K.SupertrendEmaObvB0828, K.Mk4RsiGraB0227],
                         ids=lambda s: s.__name__)
def test_kanca_backtestte_tetiklenir(sinif):
    tf = SINIF_TF[sinif.ad]
    st, r = _kancali_backtest(sinif, tf=tf)
    assert callable(st.pozisyon_cikisi) and len(r.islemler) > 3
    assert "kanca" in set(r.islemler["cikis_nedeni"]), "pozisyon_cikisi kancası tetiklenmeli"


@pytest.mark.parametrize("sinif", [K.ElliotV7B0564, K.ElliotV8B0570, K.NasosV5Mod1B0574, K.NasosSmaOfsetB0670, K.MarketCipherB0251,
                                   K.ZaratustraV13B0056, K.IchiV1B0136],
                         ids=lambda s: s.__name__)
def test_kancasiz_siniflar_backteste_girer(sinif):
    st, r = _kancali_backtest(sinif, tf=SINIF_TF[sinif.ad])
    assert st.pozisyon_cikisi is None and len(r.islemler) > 0


def test_takvim_tablosu_ve_saatler():
    assert len(K._TDW_TABLO) == 38
    m = _mumlar("15m")
    s = K.TakvimTdwTdmB0250().sinyaller(m)
    al = s["yon"] == 1
    idx = m.index
    assert (idx[al.to_numpy()].hour == 0).all()
    assert all(w * 100 + d in K._TDW_TABLO for w, d in zip(idx[al.to_numpy()].dayofweek, idx[al.to_numpy()].day))
    cik = s["cikis_long"].to_numpy()
    assert cik.any() and (idx[cik].hour == 23).all() and (idx[cik].minute == 45).all()


def test_ichi_gostergeleri_ve_cikis():
    m = _mumlar("30m")
    s = K.IchiV1Fan1B0138().sinyaller(m)
    assert s["cikis_long"].any()
    g = s["yon"] == 1
    assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * 0.725)
    assert "cikis_long" not in K.IchiV1B0136().sinyaller(m).columns     # 136: çıkış sinyali kapalı
    # 136 stopu ATR(14)x3
    s136 = K.IchiV1B0136().sinyaller(m)
    g = s136["yon"] == 1
    atr = K.g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
    assert np.allclose(s136.loc[g, "stop"], (m["kapanis"] - 3 * atr)[g])


def test_cift_yon_catismasi_ve_zaratustra_short_kolu():
    m = _mumlar("5m")
    # çatışma: ikisi de doğruysa ikisi de düşer
    a = pd.Series(True, index=m.index)
    s = K._cift(m, a, a, m["kapanis"] * 0.9, m["kapanis"] * 1.1)
    assert (s["yon"] == 0).all()
    s = K._cift(m, a, ~a, m["kapanis"] * 0.9, m["kapanis"] * 1.1)
    assert (s["yon"] == 1).all()
    # V13 short DI kolu dosyadaki gibi (dx>mdi, adx>pdi, mdi>pdi): stop yüzdesi
    s = K.ZaratustraV13B0056().sinyaller(m)
    sh = s["yon"] == -1
    assert np.allclose(s.loc[sh, "stop"], m.loc[sh, "kapanis"] * 1.296)


def test_supertrend_ham_ve_emax_adx_boolean():
    m = _mumlar("5m", 400)
    st, atr = K.SupertrendEmaObvB0828._supertrend_ham(m, 10, 1.8)
    assert len(st) == len(m) and st.iloc[0] == 0.0 and np.isfinite(st.iloc[50:]).all()
    # ham supertrend yön yukarıyken alt bant (hl2 - 1,8 ATR), aşağıyken üst bant
    hl2 = (m["yuksek"] + m["dusuk"]) / 2.0
    assert ((st.iloc[20:] - hl2.iloc[20:]).abs() <= 1.8 * atr.iloc[20:] + 1e-9).all()
    s = K.EmaxZlsmaB0146().sinyaller(_mumlar("5m", 12000, 3))
    assert (s["yon"] == 1).any()


def test_confirm_suzgeci_sinyal_cikisini_dusurur():
    hma50 = pd.Series([100.0, 100.0])
    ema100 = pd.Series([200.0, 100.0])
    kap = pd.Series([10.0, 100.0])
    # satır 0: hma50 x1,149 > ema100 DEĞİL (114,9 < 200) -> süzgeç pasif; kapanış ema100 x 0,951'den küçük de olsa
    b = K._onay_a(hma50, ema100, kap)
    assert list(b) == [False, False]
    assert K._onay_a(pd.Series([200.0]), pd.Series([100.0]), pd.Series([90.0])).iloc[0]
    m = _mumlar("5m")
    s = K.NasosSmaOfsetB0670().sinyaller(m)
    kp = m["kapanis"]
    engel = K._onay_a(K._hma(kp, 50), K.g.ema(kp, 100), kp)
    assert not (s["cikis_long"] & engel).any()
