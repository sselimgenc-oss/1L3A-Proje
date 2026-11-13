"""g9_kod_7 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR çözülür,
ROI/iz/stop eşlemeleri girdi CSV'sindeki kaynak değerlerle uyumlu."""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.cikislar import PozisyonDurumu
from motor.strateji.kapanis import kod_g9_kod_7 as K

FREQ = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h", "1d": "1D"}
TF_DK = {"5m": 5, "15m": 15, "1h": 60, "4h": 240}
CSV = "sonuclar/kapanis/kod_girdi/g9_kod_7.csv"
SINIF_TF = {}
for _v in K.VARYANTLAR:
    SINIF_TF.setdefault(_v["sinif"], _v["tf"])
N = 6000
# kaynak stopu kullanılan (yüzde stop) ve ATR(14)x3 uyarlaması kullanılan satırlar
ATR_STOP = {K.HmaWillrB0813, K.FisherTemaBbB0865, K.LamboObvWillrB0870, K.OtuzGunDipB0894}


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


def _girdi() -> pd.DataFrame:
    return pd.read_csv(CSV)


def _satir(kimlik: str) -> dict:
    g = _girdi()
    return json.loads(g.loc[g["kaynak_id"] == kimlik, "ayar"].iloc[0])


def _sinif_kimlik() -> dict:
    return {v["sinif"]: v["kimlik"].split("#")[0] for v in K.VARYANTLAR}


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_sinyal_stop_gelecek(sinif):
    st = sinif()
    tf = SINIF_TF[st.ad]
    m = _mumlar(tf)
    s = st.sinyaller(m)
    assert s.index.equals(m.index)
    long, short = s["yon"] == 1, s["yon"] == -1
    assert long.any(), "sentetik veride long sinyal üretmeli"
    assert not short.any(), "kaynak kural yalnız long"
    assert st.cikis_var_mi()
    assert s.loc[long, "stop"].notna().all()
    assert (s.loc[long, "stop"] < m.loc[long, "kapanis"]).all()
    # lookahead: son 300 mum 2,5x olunca önceki sinyaller değişmez
    k = N - 300
    m2 = m.copy()
    kolon = m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])
    m2.iloc[k:, kolon] *= 2.5
    s2 = sinif().sinyaller(m2)
    pd.testing.assert_frame_equal(s.iloc[:k], s2.iloc[:k])
    # veri sonunu kesmek de geçmişi değiştirmez
    s3 = sinif().sinyaller(m.iloc[:k + 1])
    pd.testing.assert_frame_equal(s.iloc[:k + 1], s3)


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_hacim_degisimi_gecmisi_bozmaz(sinif):
    """Hacim kullanan kurallar için ayrıca: son 300 mumun hacmi değişince önceki sinyaller aynı."""
    tf = SINIF_TF[sinif.ad]
    m = _mumlar(tf)
    s = sinif().sinyaller(m)
    k = N - 300
    m2 = m.copy()
    m2.iloc[k:, m2.columns.get_loc("hacim")] *= 7.0
    pd.testing.assert_frame_equal(s.iloc[:k], sinif().sinyaller(m2).iloc[:k])


@pytest.mark.parametrize("kayit", K.VARYANTLAR, ids=lambda v: v["kimlik"])
def test_varyant_orneklenir(kayit):
    assert set(kayit) == {"kimlik", "sinif", "parametreler", "tf"}
    assert "#v" in kayit["kimlik"] and kayit["tf"] in FREQ
    sozluk = {s.ad: s for s in K.SINIFLAR}
    st = sozluk[kayit["sinif"]](**kayit["parametreler"])
    m = _mumlar(kayit["tf"], 3000)
    s = st.sinyaller(m)
    assert len(s) == len(m)
    assert st.parametre_izgarasi == {}


def test_varyant_ve_kodlanamadi_kapsami():
    kimlikler = set(_girdi()["kaynak_id"])
    kayitli = {v["kimlik"].split("#")[0] for v in K.VARYANTLAR}
    kod_yok = {x["kimlik"] for x in K.KODLANAMADI}
    assert kayitli | kod_yok == kimlikler
    assert not kayitli & kod_yok
    assert len({v["kimlik"] for v in K.VARYANTLAR}) == len(K.VARYANTLAR)
    assert all(x["neden"] for x in K.KODLANAMADI)
    adlar = [s.ad for s in K.SINIFLAR]
    assert len(set(adlar)) == len(adlar) and all(a.startswith("kapanis__") for a in adlar)
    # ad son eki kaynak numarası: b0813 <-> HAM:B001:813
    for v in K.VARYANTLAR:
        assert v["sinif"].endswith("-b%04d" % int(v["kimlik"].split("#")[0].split(":")[-1]))
    # TF'ler girdi satırıyla aynı
    tf_girdi = dict(zip(_girdi()["kaynak_id"], _girdi()["tf"]))
    assert all(v["tf"] == tf_girdi[v["kimlik"].split("#")[0]] for v in K.VARYANTLAR)


def test_roi_trailing_stop_girdi_ile_uyumlu():
    """Her satır için: azalan_roi = CSV minimal_roi (negatif basamaklar ve 'devre dışı' 100x hariç), iz süren/offset ve stop yüzdesi CSV'deki gibi."""
    sinif_kimlik = _sinif_kimlik()
    for sinif in K.SINIFLAR:
        kimlik = sinif_kimlik[sinif.ad]
        a = _satir(kimlik)
        tf_dk = TF_DK[a["tf_satir"]]
        ca = sinif.cikis_ayarlari
        roi = {int(k): v for k, v in a["minimal_roi"].items()}
        if kimlik == "HAM:B001:899":      # dinamik ROI kancada: azalan_roi boş, tablo sınıf sabitinde
            assert ca.azalan_roi == () and {int(k): v for k, v in K.DynaBinB0899.ROI_DK.items()} == roi
        elif kimlik == "HAM:B001:903":    # ROI {0: 100} = devre dışı
            assert ca.azalan_roi == ()
        elif not roi:
            assert ca.azalan_roi == ()
        else:
            pozitif = {k: v for k, v in roi.items() if v >= 0}
            assert ca.azalan_roi == K._roi(pozitif, tf_dk), kimlik
        if a.get("trailing_stop"):
            assert ca.geri_cekilme_yuzde == pytest.approx(a["trailing_stop_positive"] * 100)
            assert a["trailing_only_offset_is_reached"] is True
            assert ca.geri_cekilme_min_kar_yuzde == pytest.approx(a["trailing_stop_positive_offset"] * 100)
        else:
            assert ca.geri_cekilme_yuzde is None, kimlik
        # stop
        m = _mumlar(a["tf_satir"], 3000)
        st = sinif()
        s = st.sinyaller(m)
        g = s["yon"] == 1
        if sinif in ATR_STOP:
            assert "ATR" in a["stop_uygulanan"]
            assert a["baslangic_stop_etkin"] <= -0.5
        else:
            assert a["stop_uygulanan"] == "kaynak stopu"
            assert np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * (1 + a["stoploss"]))


def test_lambo_roi_tablosu_csv_ile_ayni_ve_negatif_kuyruk():
    a = _satir("HAM:B001:870")
    roi = {int(k): v for k, v in a["minimal_roi"].items()}
    assert len(roi) == 731
    # anahtarlar 120..3755 arası 5 dk adımlı, sonra -%1/-%2/-%3
    assert sorted(roi)[0] == 120 and roi[3755] == 0 and (roi[3900], roi[3960], roi[4020]) == (-0.01, -0.02, -0.03)
    assert K.LamboObvWillrB0870.cikis_ayarlari.azalan_roi == K._roi({k: v for k, v in roi.items() if v >= 0}, 15)
    st = K.LamboObvWillrB0870()

    def durum(tutulan, kar):
        return PozisyonDurumu(1, 100.0, 0, tutulan, tutulan, 100.0, 100.0, 100.0 * (1 + kar / 100), kar)

    assert not st.pozisyon_cikisi(durum(259, 0.0))
    assert st.pozisyon_cikisi(durum(260, -0.9)) and not st.pozisyon_cikisi(durum(260, -1.1))
    assert st.pozisyon_cikisi(durum(264, -1.9)) and not st.pozisyon_cikisi(durum(264, -2.1))
    assert st.pozisyon_cikisi(durum(268, -2.9)) and not st.pozisyon_cikisi(durum(268, -3.1))
    assert not st.pozisyon_cikisi(durum(500, -5.0))


def test_desen_ve_tema_dema_temel_ozellikler():
    # tam yükselen mum, önceki yükseğin üstünde kapanış: konum +1, karşılaştırma +1 -> 8; tam düşen: -1,-1 -> 0
    m = pd.DataFrame({"acilis": [10.0, 10.0, 12.0], "yuksek": [10.5, 12.0, 12.0], "dusuk": [9.5, 10.0, 8.0],
                      "kapanis": [10.0, 11.9, 8.1]})
    d = K._desen(m)
    assert list(d) == [4, 8, 0]
    sabit = pd.Series(np.full(300, 5.0))
    assert np.allclose(K._tema(sabit, 9).dropna(), 5.0) and np.allclose(K._dema(sabit, 8).dropna(), 5.0)
    fr = K._fisher_rsi(pd.Series(np.arange(100, dtype=float) + 1.0), 9).dropna()
    assert (fr > 0.99).all() and (fr <= 1.0).all()


def test_fray_kaynak_esasli_periyotlar():
    p = K.FrayCokluB0854.varsayilan_parametreler
    assert p["tema_n"] == 7 and p["bb_n"] == 16           # kural_tam 9 / 20 diyordu; kaynak dosya esas
    assert K.FrayCokluB0854.cikis_ayarlari.azalan_roi == ((0.0, 6.0), (2.0, 8.0), (4.0, 12.0))


def test_yalniz_karda_bayraklari():
    for sinif in (K.FisherTemaBbB0865, K.OtuzGunDipB0894, K.Rsi30BbTemaB0843):
        assert sinif.cikis_ayarlari.yalniz_karda_cikis
    for sinif in (K.HmaWillrB0813, K.Rsi30DemaB0817, K.ClucFiatSlowB0845, K.FrayCokluB0854, K.IkiMumB0876):
        assert not sinif.cikis_ayarlari.yalniz_karda_cikis


def test_iki_mum_4h_desenleri_ve_kapanmis_4h():
    m = _mumlar("1h")
    st = K.IkiMum4hB0875()
    s = st.sinyaller(m)
    assert (s["yon"] == 1).sum() > 10
    # 4h bilgi yalnız kapanmış mumdan: 4h mumun ilk 1h satırında (bar henüz açılmamış) önceki kapanmış 4h değeri geçerli;
    # bu yüzden 4h'in içindeki herhangi bir 1h mumunun yüksek/düşüğünü bozmak ayni 4h mumun sinyallerini değiştirmez.
    m2 = m.copy()
    j = 3000
    sat = m2.index[j]
    ayni_4h = [t for t in m2.index if t.floor("4h") == sat.floor("4h")]
    son_4h = ayni_4h[-1]
    m2.loc[son_4h, ["yuksek", "kapanis"]] = m2.loc[son_4h, "yuksek"] * 1.5
    s2 = st.sinyaller(m2)
    onceki = m2.index < son_4h
    pd.testing.assert_frame_equal(s.loc[onceki], s2.loc[onceki])


def test_slowbro_ust_zaman_gunluk():
    m = _mumlar("1h")
    s = K.OtuzGunDipB0894().sinyaller(m)
    # ilk 30 günlük kapanış dolmadan (ve ilk gün kapanmadan) sinyal yok
    assert (s["yon"].iloc[: 30 * 24] == 0).all()
    assert s["cikis_long"].any()


def _dyna_durum(i, tutulan, kar, en_yuksek_kar=None):
    ey = 100.0 * (1 + (kar if en_yuksek_kar is None else en_yuksek_kar) / 100.0)
    return PozisyonDurumu(1, 100.0, i - tutulan, i, tutulan, ey, 90.0, 100.0 * (1 + kar / 100.0), kar)


def test_dyna_dinamik_roi_ve_ozel_stop():
    m = _mumlar("5m")
    st = K.DynaBinB0899()
    st.sinyaller(m)
    tr = st._kd["trend"]
    i_trend = int(np.flatnonzero(tr == 1.0)[500])
    i_yok = int(np.flatnonzero(tr == 0.0)[500])
    assert st._tf_dk == 5.0
    # ROI tablosu: 72 dk sonrası (tutulan >= 15) hedef 0: trend yokken kâr > 0 çık, zarardaysa çıkma
    assert st.pozisyon_cikisi(_dyna_durum(i_yok, 20, 0.5))
    assert not st.pozisyon_cikisi(_dyna_durum(i_yok, 20, -1.0))
    # 20 dk (tutulan 4): hedef %4,751
    assert not st.pozisyon_cikisi(_dyna_durum(i_yok, 4, 4.0)) and st.pozisyon_cikisi(_dyna_durum(i_yok, 4, 5.0))
    # trend içindeyken ROI askıda (min_roi = 100)
    assert not st.pozisyon_cikisi(_dyna_durum(i_trend, 20, 30.0))
    # özel stop: kâr < -%5 ve süre > 961 dk (>= 193 mum) -> çık; süre kısaysa çıkma
    assert st.pozisyon_cikisi(_dyna_durum(i_yok, 193, -6.0))
    assert not st.pozisyon_cikisi(_dyna_durum(i_yok, 192, -6.0))
    assert not st.pozisyon_cikisi(_dyna_durum(i_yok, 300, -4.0))
    # pullback açık, tabloya uy: trend içinde zirveden %1,5'ten fazla gerilediyse tablo ROI'si geçerli
    st2 = K.DynaBinB0899(droi_pullback=True)
    st2.sinyaller(m)
    assert st2.pozisyon_cikisi(_dyna_durum(i_trend, 20, 1.0, en_yuksek_kar=4.0))
    assert not st2.pozisyon_cikisi(_dyna_durum(i_trend, 20, 1.0, en_yuksek_kar=1.2))
    # roc kolu: SROC seri değeri koşulu sağlayan satırı bul
    st3 = K.DynaBinB0899(cstp_bail_how="roc", cstp_bail_roc=-0.001)
    st3.sinyaller(m)
    sr = st3._kd["sroc"]
    i_neg = int(np.flatnonzero(sr / 100.0 <= -0.001)[0])
    i_poz = int(np.flatnonzero(sr / 100.0 > -0.001)[-1])
    assert st3.pozisyon_cikisi(_dyna_durum(i_neg, 2, -6.0))
    assert not st3.pozisyon_cikisi(_dyna_durum(i_poz, 500, -6.0))


def test_dyna_bilgi_1h_sizinti_yok_ve_hook_gelecege_bakmaz():
    m = _mumlar("5m")
    st = K.DynaBinB0899()
    st.sinyaller(m)
    tr1 = st._kd["trend"].copy()
    k = N - 300
    m2 = m.copy()
    m2.iloc[k:, m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 2.5
    st2 = K.DynaBinB0899()
    st2.sinyaller(m2)
    assert np.array_equal(tr1[:k], st2._kd["trend"][:k], equal_nan=True)
    assert np.array_equal(st._kd["sroc"][:k], st2._kd["sroc"][:k], equal_nan=True)


@pytest.mark.parametrize("sinif", K.SINIFLAR, ids=lambda s: s.__name__)
def test_backtest_calisir(sinif):
    tf = SINIF_TF[sinif.ad]
    m = _mumlar(tf, N)
    st = sinif()
    r = backtest(m, st, MotorAyarlari())
    assert len(r.islemler) > 0
    assert not math.isnan(float(r.ozsermaye.iloc[-1]))
