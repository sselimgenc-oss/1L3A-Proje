"""g9_kod_1 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.cikislar import PozisyonDurumu
from motor.strateji.kapanis import kod_g9_kod_1 as K

FREQ = {"5m": "5min", "15m": "15min", "1h": "1h"}
IKI_YON = {K.ElB0221}
SINIF_TF = {v["sinif"]: v["tf"] for v in K.VARYANTLAR}
N = 6000


def _mumlar(freq: str, n: int = N, tohum: int = 7, vol: float = 0.01, dalga: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    t = np.arange(n)
    getiri = rng.standard_t(4, n) * vol + 0.0002 * np.sin(t / dalga * 2 * np.pi)
    kap = 100 * np.exp(np.cumsum(getiri) + 0.5 * np.sin(t / dalga))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    idx = pd.date_range("2020-01-01", periods=n, freq=FREQ[freq], tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(50, 150, n)}, index=idx)


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_sinyal_stop_gelecek(sinif):
    st = sinif()
    tf = SINIF_TF[st.ad]
    m = _mumlar(tf)
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
    kd1 = dict(getattr(st, "_kd", {}))
    # lookahead: son 300 mum 2,5x olunca önceki sinyaller (ve kanca dizileri) değişmez
    k = N - 300
    m2 = m.copy()
    kolon = m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])
    m2.iloc[k:, kolon] *= 2.5
    s2 = st.sinyaller(m2)
    pd.testing.assert_frame_equal(s.iloc[:k], s2.iloc[:k])
    for ad, dizi in kd1.items():
        np.testing.assert_allclose(dizi[:k], st._kd[ad][:k], equal_nan=True, err_msg=f"kanca dizisi {ad} geleceğe bağlı")
    # veri sonunu kesmek de geçmişi değiştirmez
    s3 = st.sinyaller(m.iloc[:k + 1])
    pd.testing.assert_frame_equal(s.iloc[:k + 1], s3)


@pytest.mark.parametrize("kayit", K.VARYANTLAR, ids=lambda v: v["kimlik"])
def test_varyant_orneklenir(kayit):
    assert set(kayit) - {"modul"} == {"kimlik", "sinif", "parametreler", "tf"}
    assert "#v" in kayit["kimlik"] and kayit["tf"] in FREQ
    st = {s.ad: s for s in K.SINIFLAR}[kayit["sinif"]](**kayit["parametreler"])
    m = _mumlar(kayit["tf"], 3000)
    s = st.sinyaller(m)
    assert len(s) == len(m)
    assert st.parametre_izgarasi == {}


def test_varyant_ve_kodlanamadi_kapsami():
    girdi = pd.read_csv("sonuclar/kapanis/kod_girdi/g9_kod_1.csv")
    kimlikler = set(girdi["kaynak_id"])
    kayitli = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR}
    kod_yok = {x["kimlik"] for x in K.KODLANAMADI}
    assert kayitli | kod_yok == kimlikler
    assert not kayitli & kod_yok
    assert kod_yok == {"HAM:B001:406", "HAM:B001:846", "HAM:B001:847"}
    assert len({v["kimlik"] for v in K.VARYANTLAR}) == len(K.VARYANTLAR) == 26
    assert all(x["neden"] for x in K.KODLANAMADI)
    adlar = [s.ad for s in K.SINIFLAR]
    assert len(set(adlar)) == len(adlar) and all(a.startswith("kapanis__") and "-b0" in a for a in adlar)


def test_roi_ve_iz_eslemesi():
    ca = K.AngleWaveCtB0069.cikis_ayarlari
    assert ca.azalan_roi == ((0.0, 20.2), (29.0, 9.4), (76.0, 1.7), (292.0, 0.0))
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (1.1, 2.0)
    ca = K.AwAtrCtB0156.cikis_ayarlari          # 15m, offset şartı yok -> min kâr 0
    assert ca.azalan_roi == ((0.0, 34.9), (6.0, 7.5), (12.0, 4.3), (27.0, 0.0))
    assert (ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde) == (7.0, 0.0)
    # 5m'de 3 ve 5 dk aynı muma düşer: büyük dakikalı (%3,3) geçerli
    assert K.ClucHaNixHhllB0440.cikis_ayarlari.azalan_roi[:2] == ((0.0, 10.3), (1.0, 3.3))
    assert K.OverwatchB0105.cikis_ayarlari.azalan_roi == ((0.0, 35.4), (6.0, 17.8), (9.0, 4.0), (31.0, 0.0))
    ca = K.GodCardB0506.cikis_ayarlari
    assert ca.yalniz_karda_cikis and ca.yalniz_karda_min_kar_yuzde == 0.0
    assert K.BinhClucV5B0449.cikis_ayarlari.yalniz_karda_min_kar_yuzde == 0.1
    assert K.BbRsiOptim2020B0469.cikis_ayarlari.geri_cekilme_yuzde is None
    assert K.ElB0221.cikis_ayarlari.azalan_roi[-1] == (1440.0, 2.0)


def test_pf_seviye():
    assert K._pf_seviye(0.10, -0.178, 0.019, 0.019, 0.065, 0.062) == pytest.approx(0.062 + 0.035)
    assert K._pf_seviye(0.04, -0.178, 0.019, 0.019, 0.065, 0.062) == pytest.approx(0.019 + 0.021 * 0.043 / 0.046)
    assert K._pf_seviye(0.01, -0.178, 0.019, 0.019, 0.065, 0.062) == -0.178
    assert K._pf_seviye(0.01, None, 0.011, 0.011, 0.064, 0.062) is None


def test_t3_trima_kama_dogru():
    x = pd.Series(np.arange(1.0, 200.0))
    # doğrusal artışta TRIMA (n=5) = SMA(SMA(x,3),3): son değer x[-1] - 2
    assert K._trima(x, 5).iloc[-1] == pytest.approx(x.iloc[-1] - 2.0)
    assert K._trima(x, 4).iloc[-1] == pytest.approx(x.iloc[-1] - 1.5)        # SMA(2) sonra SMA(3)
    sabit = pd.Series(np.full(300, 7.0))
    assert K._t3(sabit, 5).iloc[-1] == pytest.approx(7.0)                    # katsayılar toplamı 1
    assert K._rmi(pd.Series(np.arange(100.0)), 8, 4).iloc[-1] == 0.0        # hiç düşüş yok: kaynak 0 döndürür


def _durum(yon=1, giris=100.0, bas=10, i=20, yuk=None, dus=None, kapanis=100.0):
    return PozisyonDurumu(yon, giris, bas, i, i - bas + 1, yuk if yuk is not None else max(giris, kapanis),
                          dus if dus is not None else min(giris, kapanis), kapanis, (kapanis / giris - 1) * 100.0)


def test_pf_kancasi_kar_kilidi_ve_hsl():
    st = K.ClucHaNix5mB0434()
    kv = np.full(60, 100.0)
    kv[12] = 108.0                                  # zirve kâr %8 > pPF_2 -> seviye 0,062 + 0,016 = 0,078
    st._sakla(kap=kv)
    assert st.pozisyon_cikisi(_durum(kapanis=107.5, i=20))       # kâr %7,5 <= %7,8
    assert not st.pozisyon_cikisi(_durum(kapanis=107.9, i=20))
    st._sakla(kap=np.full(60, 100.0))                # zirve yok -> yalnız pHSL (-%35)
    assert not st.pozisyon_cikisi(_durum(kapanis=70.0, i=20))
    assert st.pozisyon_cikisi(_durum(kapanis=64.9, i=20))


def test_b0399_vwap_kolu_ayri_basamak():
    st = K.BbRpbTslVwapB0399()
    kv = np.full(60, 100.0)
    kv[12] = 104.0          # zirve %4: normal seviye 0,019 + 0,021 x 0,043/0,046 ~ %3,86; yalnız-vwap seviyesi 0,01 + 0,03 x 0,032/0,04 = %3,4
    sadece = np.zeros(60)
    st._sakla(kap=kv, sadece_vwap=sadece)
    assert st.pozisyon_cikisi(_durum(kapanis=103.6, i=20))
    sadece[9] = 1.0         # giriş sinyali mumu (giris_mum_indeksi - 1) yalnız vwap kolundan
    st._sakla(kap=kv, sadece_vwap=sadece)
    assert not st.pozisyon_cikisi(_durum(kapanis=103.6, i=20))
    assert st.pozisyon_cikisi(_durum(kapanis=103.3, i=20))


def test_zarar_kilit_ve_iz_stop():
    st = K.BinhClucV5B0449()
    st._tf = 5.0
    kv = np.full(200, 100.0)
    kv[:] = 99.0                                     # giriş 100: hep zararda
    st._sakla(kap=kv)
    # 300 dk = 60 mum; giriş mumu 10 -> kilit j >= 71'den başlar (j-bas)*5 > 300
    assert not st.pozisyon_cikisi(_durum(giris=100.0, bas=10, i=70, kapanis=98.0))
    assert st.pozisyon_cikisi(_durum(giris=100.0, bas=10, i=90, kapanis=98.0))       # 99 x 0,99 = 98,01 >= 98
    assert not st.pozisyon_cikisi(_durum(giris=100.0, bas=10, i=90, kapanis=98.5))
    aw = K.AngleWaveCtB0069()
    kv = np.full(100, 100.0)
    kv[15] = 125.0                                   # kâr %25 -> mesafe %4 -> stop 120
    aw._sakla(kap=kv)
    assert aw.pozisyon_cikisi(_durum(giris=100.0, bas=10, i=20, kapanis=119.0))
    assert not aw.pozisyon_cikisi(_durum(giris=100.0, bas=10, i=20, kapanis=121.0))
    kv2 = np.full(100, 100.0)                        # kârsız: stop = kapanış x (1 - 0,281) ~ 71,9
    aw._sakla(kap=kv2)
    assert aw.pozisyon_cikisi(_durum(giris=100.0, bas=10, i=20, kapanis=71.0))
    assert not aw.pozisyon_cikisi(_durum(giris=100.0, bas=10, i=20, kapanis=72.5))


def test_e0v1e_hold_bayraklari():
    n = 60
    st = K.E0v1eSharpeB0205()
    st._tf = 5.0
    kv = np.full(n, 90.0)
    ma = np.full(n, 100.0)
    nan = np.full(n, np.nan)
    kv[12] = 110.0                                   # bir mum MA'ların üstünde -> HOLD; diğerleri altında -> HOLD1
    st._sakla(kap=kv, yk=np.full(n, 101.0), fastk=np.full(n, 10.0), cci=np.full(n, 0.0), ma_k=ma, ma_u=ma)
    d = _durum(giris=100.0, bas=10, i=20, kapanis=90.0, dus=90.0)
    assert st.pozisyon_cikisi(d)                     # HOLD + kapanış < MA'lar + min kâr -%10 <= -%5
    kv2 = np.full(n, 99.0)
    st._sakla(kap=kv2, yk=np.full(n, 99.0), fastk=np.full(n, 10.0), cci=np.full(n, 0.0), ma_k=nan, ma_u=nan)
    assert not st.pozisyon_cikisi(_durum(giris=100.0, bas=10, i=20, kapanis=99.0, dus=99.0))
    st2 = K.E0v1e2B0206()
    st2._tf = 5.0
    st2._sakla(kap=kv2, yk=np.full(n, 99.0), fastk=np.full(n, 90.0), cci=np.full(n, 0.0), ma_k=nan, ma_u=nan)
    assert st2.pozisyon_cikisi(_durum(giris=100.0, bas=10, i=20, kapanis=101.0))     # kâr > 0 VE fastk > 84


def test_v6_rsi_suzgeci():
    st = K.BinhClucV6B0451()
    st._tf = 5.0
    n = 60
    kv = np.full(n, 100.0)
    st._sakla(kap=kv, rsi=np.full(n, 60.0))
    d = _durum(giris=100.0, bas=10, i=20, kapanis=102.0, yuk=102.0)
    assert not st.pozisyon_cikisi(d), "RSI > 50 iken ROI çıkışı reddedilir"
    st._sakla(kap=kv, rsi=np.full(n, 40.0))
    assert st.pozisyon_cikisi(d), "RSI <= 50 iken kâr >= %1,81 ROI çıkışı"


def test_v8_mutlak_fiyat_farki_terimi():
    st = K.BinhClucV8B0454()
    st._tf = 5.0
    n = 60
    kv = np.full(n, 1000.0)
    st._sakla(kap=kv, rsi=np.full(n, 70.0), dec=np.zeros(n), kosul2=np.zeros(n))
    # giriş 1000, zirve 1500 -> (1500-1000)/100 = 5 > kâr + 0,03: kâr %12 (0,1 < kâr < 0,4)
    assert st.pozisyon_cikisi(_durum(giris=1000.0, bas=10, i=20, kapanis=1120.0, yuk=1500.0))


def test_s0561_s0673_custom_stop_yok():
    # kaynakta use_custom_stoploss kapalı: sınıflarda kanca (basamaklı stop) yok
    assert K.ElliotV5HoB0561.pozisyon_cikisi is None and K.NotAnotherSmaLiteB0673.pozisyon_cikisi is None
    m = _mumlar("5m", 2000)
    s = K.ElliotV5HoB0561().sinyaller(m)
    g = s["yon"] == 1
    assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * (1 - 0.302))


def test_atr_stop_uyarlamasi():
    m = _mumlar("5m", 3000)
    for sinif in (K.SmaOfsetProtectB0694, K.MultiOffsetLamboB0666, K.BinhClucV5B0449, K.ClucHaNixHhllB0440):
        s = sinif().sinyaller(m)
        g = s["yon"] == 1
        assert g.any()
        # kaynak stopu yok/<= -%50: stop ATR(14) x 3 (kapanıştan en az birkaç yüzde uzakta olmalı, sabit yüzde değil)
        oran = (m.loc[g, "kapanis"] - s.loc[g, "stop"]) / m.loc[g, "kapanis"]
        assert oran.nunique() > 3


def test_el_short_ayna_ve_cikislar():
    m = _mumlar("5m", 4000, vol=0.02)
    s = K.ElB0221().sinyaller(m)
    assert s.loc[s["yon"] == 1, "cikis_short"].all() and s.loc[s["yon"] == -1, "cikis_long"].all()
    sh = s["yon"] == -1
    assert np.allclose(s.loc[sh, "stop"], m.loc[sh, "kapanis"] * 1.05)


def test_bb_rpb_tsl_baslangic_stopu_phsl():
    m = _mumlar("5m", 3000)
    s = K.BbRpbTslB0395().sinyaller(m)
    g = s["yon"] == 1
    assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * (1 - 0.178))
    s = K.BbRpbTslVwapB0399().sinyaller(m)
    g = s["yon"] == 1
    assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * (1 - 0.25))


# (sınıf: (tohum, kanca çıkışı bekleniyor mu))
KANCALI = {K.ClucHaNix5mB0434: (5, True), K.BinhClucV5B0449: (11, True), K.BinhClucV6B0451: (5, True),
           K.BinhClucV8B0454: (5, True), K.AngleWaveCtB0069: (11, True), K.E0v1eSharpeB0205: (5, True),
           K.E0v1e2B0206: (5, True), K.BbRpbTslB0395: (5, True), K.ClucHaNixHhllB0440: (5, True),
           K.FahmibahB0547: (5, True), K.BinhClucMadV5B0459: (5, False), K.AwAtrCtB0156: (5, False)}


@pytest.mark.parametrize("sinif", list(KANCALI), ids=lambda s: s.__name__)
def test_kancali_backtest_calisir(sinif):
    tohum, bekle = KANCALI[sinif]
    st = sinif()
    m = _mumlar(SINIF_TF[st.ad], 4000, tohum=tohum, vol=0.03)
    r = backtest(m, st, MotorAyarlari())
    assert len(r.islemler) > 3
    assert callable(st.pozisyon_cikisi)
    if bekle:
        assert "kanca" in set(r.islemler["cikis_nedeni"]), "kanca (custom_stoploss/custom_sell/custom_exit) tetiklenmeli"
