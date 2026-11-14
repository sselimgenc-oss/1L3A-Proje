"""g8_kod_1 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.kapanis import jesse_kaynak, k2_kaynak
from motor.strateji.kapanis import kod_g8_kod_1 as K
from motor.strateji.kapanis import kod_g8_modul

FREQ = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "3h": "3h", "4h": "4h", "1d": "1D"}
IKI_YON = {K.LinregAdxS0006, K.Rsi2Sma200S0007, K.EmaObvS0025, K.AdxSma1248S0027, K.AralikKirilimS0036,
           K.Rsi4DonusS0051, K.RsiH1D1S0067, K.MaIbsS0070, K.AoWmaDunS0073, K.SmaKesisDonS0081}
SINIF_TF = {}
for _v in K.VARYANTLAR:
    SINIF_TF.setdefault(_v["sinif"], _v["tf"])
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
    # lookahead: son 300 mum 2,5x olunca önceki sinyaller değişmez
    k = N - 300
    m2 = m.copy()
    kolon = m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])
    m2.iloc[k:, kolon] *= 2.5
    s2 = st.sinyaller(m2)
    pd.testing.assert_frame_equal(s.iloc[:k], s2.iloc[:k])
    # veri sonunu kesmek de geçmişi değiştirmez
    s3 = st.sinyaller(m.iloc[:k + 1])
    pd.testing.assert_frame_equal(s.iloc[:k + 1], s3)


def _cozucu() -> dict:
    sozluk = {s.ad: s for s in K.SINIFLAR}
    sozluk[k2_kaynak.DonchianEma2RS0083.ad] = k2_kaynak.DonchianEma2RS0083
    sozluk[jesse_kaynak.MacdEmaS0005.ad] = jesse_kaynak.MacdEmaS0005
    return sozluk


@pytest.mark.parametrize("kayit", K.VARYANTLAR, ids=lambda v: v["kimlik"])
def test_varyant_orneklenir(kayit):
    assert set(kayit) - {"modul"} == {"kimlik", "sinif", "parametreler", "tf"}
    assert "#v" in kayit["kimlik"] and kayit["tf"] in FREQ
    st = _cozucu()[kayit["sinif"]](**kayit["parametreler"])
    m = _mumlar(kayit["tf"], 3000)
    s = st.sinyaller(m)
    assert len(s) == len(m)
    assert st.parametre_izgarasi == {}


def test_varyant_ve_kodlanamadi_kapsami():
    girdi = pd.read_csv("sonuclar/kapanis/kod_girdi/g8_kod_1.csv")
    kimlikler = set(girdi["kaynak_id"])
    kayitli = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR}
    kod_yok = {x["kimlik"] for x in K.KODLANAMADI}
    modulde = {v["kimlik"].split("#")[0] for v in kod_g8_modul.VARYANTLAR} | {x["kimlik"] for x in kod_g8_modul.KODLANAMADI}
    assert kayitli | kod_yok | (modulde & kimlikler) == kimlikler
    assert not kayitli & modulde and not kod_yok & modulde      # çift kayıt yok
    assert {"HAM:X005:4", "HAM:X005:20", "HAM:X005:21", "HAM:X005:22", "HAM:X005:60", "HAM:X005:79"} <= modulde
    assert not kayitli & kod_yok
    assert len({v["kimlik"] for v in K.VARYANTLAR}) == len(K.VARYANTLAR)
    assert all(x["neden"] for x in K.KODLANAMADI)
    adlar = [s.ad for s in K.SINIFLAR]
    assert len(set(adlar)) == len(adlar) and all(a.startswith("kapanis__") for a in adlar)


def test_roi_tablosu_mum_donusumu():
    assert K._roi({0: 0.05, 20: 0.04, 30: 0.03, 60: 0.01}, 5) == ((0, 5.0), (4, 4.0), (6, 3.0), (12, 1.0))
    # 1h'de 30dk ve 60dk aynı muma düşer: büyük dakika (60 -> %7,5) geçerli
    assert K._roi({0: 0.05, 30: 0.10, 60: 0.075}, 60) == ((0, 5.0), (1, 7.5))
    assert K._roi({0: 0.162, 69: 0.097, 229: 0.061, 566: 0.0}, 15) == ((0, 16.2), (5, 9.7), (16, 6.1), (38, 0.0))
    assert K.BandtasticS0018.cikis_ayarlari.geri_cekilme_min_kar_yuzde == 5.8
    assert K.HlhbS0023.cikis_ayarlari.azalan_roi[1] == (3, 21.87)


def test_linreg_uc_noktasi():
    x = pd.Series(np.arange(30, dtype=float) * 2.0 + 5.0)  # tam doğru: uç nokta = son değer
    assert np.allclose(K._linreg_uc(x, 5).dropna(), x.iloc[4:])
    y = pd.Series([1.0, 3.0, 2.0, 5.0, 4.0])
    egim, kesim = np.polyfit(np.arange(5), y, 1)
    assert np.isclose(K._linreg_uc(y, 5).iloc[-1], egim * 4 + kesim)


def test_s0006_hedef_stop_geometrisi():
    m = _mumlar("4h")
    s = K.LinregAdxS0006().sinyaller(m)
    for yon in (1, -1):
        g = s["yon"] == yon
        risk = (m.loc[g, "kapanis"] - s.loc[g, "stop"]) * yon
        odul = (s.loc[g, "hedef"] - m.loc[g, "kapanis"]) * yon
        assert np.allclose(odul / risk, 2.5)


def test_s0036_zaman_cikisi_ve_cevirme():
    m = _mumlar("30m")
    s = K.AralikKirilimS0036().sinyaller(m)
    assert (s["zaman_cikisi_mum"] == 240).all()
    al, sat = s["yon"] == 1, s["yon"] == -1
    assert (s.loc[al, "cikis_short"]).all() and (s.loc[sat, "cikis_long"]).all()
    assert np.allclose(s.loc[al, "stop"], m.loc[al, "kapanis"] * 0.97)


def test_s0070_bir_gun_tutma():
    m = _mumlar("1d")
    s = K.MaIbsS0070().sinyaller(m)
    assert (s["zaman_cikisi_mum"] == 1).all()


def test_s0073_emir_omru_ve_seviye():
    kap = np.array([10, 10, 10, 10, 12, 10, 10, 10, 10, 10, 10, 10, 10, 10, 13.0])
    kurulum = np.zeros(len(kap), bool)
    kurulum[1] = True
    seviye = np.full(len(kap), 11.5)
    # kurulum 1'de, seviye 11.5; 4. mumda kapanış 12 > 11.5 -> tetik
    t = K.AoWmaDunS0073._tetik(kurulum, seviye, kap, 12, 1)
    assert list(np.flatnonzero(t)) == [4]
    # emir ömrü 2 mum: 4. mum (yaş 3) geç kalır
    assert not K.AoWmaDunS0073._tetik(kurulum, seviye, kap, 2, 1).any()
    # short: seviye altına inen kapanış
    kap2 = np.array([10, 10, 10, 8.0, 10])
    k2 = np.zeros(5, bool)
    k2[1] = True
    assert list(np.flatnonzero(K.AoWmaDunS0073._tetik(k2, np.full(5, 9.0), kap2, 12, -1))) == [3]
    m = _mumlar("1h")
    s = K.AoWmaDunS0073().sinyaller(m)
    g = s["yon"] == 1
    assert np.allclose(s.loc[g, "hedef"], m.loc[g, "kapanis"] * 1.007)


def test_s0074_pazartesi_carsamba():
    m = _mumlar("1d")
    s = K.IbsPazartesiS0074().sinyaller(m)
    assert (s.index[s["yon"] == 1].dayofweek == 0).all()
    assert (s.index[s["cikis_long"]].dayofweek == 2).all()
    g = s["yon"] == 1
    assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * 0.9)


def test_s0084_stop_sinyal_mumu_dususu():
    m = _mumlar("1d")
    s = K.MacdHaftalikS0084().sinyaller(m)
    g = s["yon"] == 1
    assert np.allclose(s.loc[g, "stop"], m.loc[g, "dusuk"])


def test_s0067_ters_cikis_ve_s0051_dur_ve_ters():
    for sinif, tf in ((K.RsiH1D1S0067, "1h"), (K.Rsi4DonusS0051, "4h"), (K.SmaKesisDonS0081, "4h")):
        m = _mumlar(tf)
        s = sinif().sinyaller(m)
        assert s.loc[s["yon"] == 1, "cikis_short"].all()
        assert s.loc[s["yon"] == -1, "cikis_long"].all()


def test_s0041_s0043_iz_parametreleri():
    # iz artık motorun bar içi ATR izi değil, kapanış bazlı kanca (cikis_ayarlari boş)
    assert K.MacdSmaIzS0041.cikis_ayarlari.atr_iz_suren_k is None
    assert K.MacdSmaIzS0041.varsayilan_parametreler["iz_k"] == 3.0 and K.MacdSmaIzS0041.varsayilan_parametreler["atr_n"] == 14
    assert K.SmaKesIzS0043.varsayilan_parametreler["iz_k"] == 2.0 and K.SmaKesIzS0043.varsayilan_parametreler["atr_n"] == 100


def test_x005_5_jesse_kaynagina_baglanir():
    k = [v for v in K.VARYANTLAR if v["kimlik"].startswith("HAM:X005:5#")]
    assert len(k) == 1 and k[0]["sinif"] == jesse_kaynak.MacdEmaS0005.ad
    assert k[0]["modul"] == "motor.strateji.kapanis.jesse_kaynak"
    assert not any(s.ad == "kapanis__macd-ema100-s0005" for s in K.SINIFLAR)


def test_tek_basamakli_roi_azalan_roi():
    for sinif, beklenen in ((K.RsiTradingViewS0010, 10.0), (K.RsiBbTipikS0012, 10.0), (K.ClucMayS0015, 1.0),
                            (K.MultiRsiS0016, 1.0), (K.AdxSmasS0024, 10.0), (K.Ema821Ust48S0030, 50.0)):
        st = sinif()
        assert st.cikis_ayarlari.azalan_roi == ((0.0, beklenen),)
        m = _mumlar(SINIF_TF[st.ad], 3000)
        assert st.sinyaller(m)["hedef"].isna().all(), "limit hedef kalmamalı"
        assert sinif(**{st.roi_anahtar: 0.02}).cikis_ayarlari.azalan_roi == ((0.0, 2.0),)


def _kancali_backtest(sinif, tf="1d", n=4000):
    m = _mumlar(tf, n, tohum=3, vol=0.02)
    st = sinif()
    r = backtest(m, st, MotorAyarlari())
    return st, r


def test_s0041_s0043_kapanis_bazli_iz_kanca():
    for sinif in (K.MacdSmaIzS0041, K.SmaKesIzS0043):
        st, r = _kancali_backtest(sinif)
        assert st.cikis_ayarlari.atr_iz_suren_k is None and callable(st.pozisyon_cikisi)
        assert len(r.islemler) > 3
        assert "kanca" in set(r.islemler["cikis_nedeni"]), "kapanış bazlı iz kancayla tetiklenmeli"
