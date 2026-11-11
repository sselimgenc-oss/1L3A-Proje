"""Funding sütunu (nedensellik, DK_ hatası, girdi değişmezliği) ve dis__ewmac-carry / dis__funding-carry stratejileri."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.portfoy.birlesik import birlesik_backtest
from motor.strateji import kayit
from motor.strateji.dis.d4_sistematik import EwmacCarver
from motor.strateji.dis.d6_funding import EwmacCarry, FundingCarry
from motor.strateji.funding import (
    GUNLUK_TOPLAM_SUTUN, SUTUN, FundingYokHatasi, funding_sutunu_ekle, stratejiye_hazirla,
)
from testler.test_daytrade import rastgele_mumlar


def fund_serisi(n_gun, seed=1, ofset="0h", ort=0.0001, sd=0.0002):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n_gun * 3, freq="8h", tz="UTC", name="zaman") + pd.Timedelta(ofset)
    return pd.DataFrame({"oran": ort + sd * rng.standard_normal(len(idx))}, index=idx)


def test_funding_sutunu_nedensel():
    m = rastgele_mumlar(100, freq="1h")
    f = pd.DataFrame({"oran": [0.001, 0.002]},
                     index=pd.DatetimeIndex(["2022-01-01 03:00", "2022-01-01 08:00:00.002"], tz="UTC", name="zaman"))
    o = funding_sutunu_ekle(m, f, "1h")
    c = o[SUTUN]
    assert c[:"2022-01-01 01:00"].isna().all()          # 02:00 mumu 03:00'te kapanır -> 03:00 funding'i görür
    assert np.isnan(c["2022-01-01 01:00"]) and c["2022-01-01 02:00"] == 0.001
    assert c["2022-01-01 06:00"] == 0.001
    assert c["2022-01-01 07:00"] == 0.001               # 07:00 mumu 08:00'de kapanır; funding 08:00:00.002 -> GÖRÜNMEZ
    assert c["2022-01-01 08:00"] == 0.002 and c["2022-01-02 00:00"] == 0.002
    assert "funding_orani" not in m.columns             # girdi değişmedi


def test_funding_zamani_tam_kapanista_gorunur():
    m = rastgele_mumlar(10, freq="1h")
    f = pd.DataFrame({"oran": [0.5]}, index=pd.DatetimeIndex(["2022-01-01 03:00"], tz="UTC", name="zaman"))
    c = funding_sutunu_ekle(m, f, "1h")[SUTUN]
    assert np.isnan(c["2022-01-01 01:00"]) and c["2022-01-01 02:00"] == 0.5


def test_funding_gunluk_toplam_uc_odeme_ve_gelecek_odemeyi_dislar():
    idx = pd.date_range("2022-01-01", periods=3, freq="1D", tz="UTC", name="zaman")
    m = pd.DataFrame({"acilis": 100.0, "yuksek": 101.0, "dusuk": 99.0,
                      "kapanis": 100.0, "hacim": 1.0}, index=idx)
    f = pd.DataFrame(
        {"oran": [0.001, 0.002, 0.003, 0.500]},
        index=pd.DatetimeIndex(["2022-01-01 01:00", "2022-01-01 09:00", "2022-01-02 00:00",
                                "2022-01-02 00:00:00.001"], tz="UTC", name="zaman"),
    )
    o = funding_sutunu_ekle(m, f, "1d")
    assert o.loc[idx[0], GUNLUK_TOPLAM_SUTUN] == pytest.approx(0.006)
    assert o.loc[idx[0], SUTUN] == pytest.approx(0.003)
    assert o.loc[idx[1], GUNLUK_TOPLAM_SUTUN] == pytest.approx(0.500)
    # İlk mum kapanışından 1 ms sonraki ödeme ilk günün toplamına sızmaz.
    f2 = f.copy()
    f2.loc[pd.Timestamp("2022-01-02 00:00:00.001", tz="UTC"), "oran"] = 9.0
    o2 = funding_sutunu_ekle(m, f2, "1d")
    assert o2.loc[idx[0], GUNLUK_TOPLAM_SUTUN] == o.loc[idx[0], GUNLUK_TOPLAM_SUTUN]


def test_gelecek_funding_degisince_gecmis_sutun_degismez():
    m = rastgele_mumlar(300, freq="1h")
    f = fund_serisi(20)
    a = funding_sutunu_ekle(m, f, "1h")[SUTUN]
    f2 = f.copy()
    f2.iloc[-5:, 0] = 9.9
    b = funding_sutunu_ekle(m, f2, "1h")[SUTUN]
    t0 = f.index[-5]
    esit = a.index < t0
    pdt.assert_series_equal(a[esit], b[esit])


def test_dk_sembolde_acik_hata():
    m = rastgele_mumlar(50)
    for s in (EwmacCarry(), FundingCarry()):
        with pytest.raises(FundingYokHatasi, match="DK_XAU"):
            stratejiye_hazirla(s, m, None, "DK_XAU", "1h")


def test_funding_gerekmeyen_strateji_girdisi_ayni_nesne():
    m = rastgele_mumlar(50)
    s = EwmacCarver()
    assert not s.funding_gerekli
    assert stratejiye_hazirla(s, m, fund_serisi(5), "BTCUSDT", "1h") is m
    assert stratejiye_hazirla(s, m, None, "DK_XAU", "1h") is m
    for ad, sinif in kayit.tum_stratejiler().items():
        assert sinif.funding_gerekli == (ad in (
            "dis__ewmac-carry", "dis__funding-carry",
            "v2__funding-asiri-kontra", "v2__funding-esik-karsit", "v2__trend-funding-suzgec")), ad


def test_once_sonra_esitlik_sentetik():
    """funding_gerekli=False strateji: hazırlanan girdiyle ve eskisi gibi doğrudan çalıştırma AYNI işlemleri üretir."""
    m = rastgele_mumlar(3000, freq="4h", baslangic="2020-01-01")
    f = fund_serisi(520)
    s = EwmacCarver()
    ay = MotorAyarlari(limit_modu="olc")
    r_eski = backtest(m, s, ay, f)
    r_yeni = backtest(stratejiye_hazirla(s, m, f, "BTCUSDT", "4h"), s, ay, f)
    assert len(r_eski.islemler) > 0
    pdt.assert_frame_equal(r_eski.islemler, r_yeni.islemler)


def test_sutunsuz_girdide_hata():
    with pytest.raises(ValueError, match="funding_orani"):
        FundingCarry().sinyaller(rastgele_mumlar(100))
    with pytest.raises(ValueError, match="funding_orani"):
        EwmacCarry().sinyaller(rastgele_mumlar(100, freq="4h"))


# ------------------------------------------------------------------ dis__ewmac-carry
def carry_girdi(n=4500, seed=11, **kw):
    m = rastgele_mumlar(n, seed=seed, freq="4h", baslangic="2020-01-01")
    return funding_sutunu_ekle(m, fund_serisi(n // 6 + 5, **kw), "4h")


def test_ewmac_carry_kayit_ve_izgara():
    assert kayit.dogrula() == []
    n = 1
    for v in EwmacCarry.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27 and set(EwmacCarry.parametre_izgarasi) <= set(EwmacCarry.varsayilan_parametreler)
    df = carry_girdi(2500)
    for anahtar, degerler in EwmacCarry.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = EwmacCarry(**{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index)


def test_ewmac_carry_lookahead_ve_stop_tarafi():
    df = carry_girdi()
    for s in (EwmacCarry(), EwmacCarry(varyantlar="2/8+4/16+8/32", esik=3.0, trend_agirlik=0.5)):
        tam = s.sinyaller(df)
        for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])
        giris = tam[tam.yon != 0]
        assert len(giris) > 0 and giris.stop.notna().all()
        kap = df.kapanis
        l, sh = giris[giris.yon == 1], giris[giris.yon == -1]
        assert (l.stop < kap[l.index]).all() and (sh.stop > kap[sh.index]).all()
        assert abs(s.tahmin(df).dropna()).max() <= 20.0


def test_ewmac_carry_isaret_ve_agirlik():
    df = carry_girdi(ort=0.0003, sd=1e-6)           # sürekli yüksek pozitif funding -> carry negatif (long öder)
    s = EwmacCarry(trend_agirlik=0.0)
    c = s.carry_tahmin(df).dropna()
    assert len(c) > 0 and (c < 0).all() and c.min() >= -20
    df2 = carry_girdi(ort=-0.0003, sd=1e-6)
    assert (EwmacCarry(trend_agirlik=0.0).carry_tahmin(df2).dropna() > 0).all()
    # trend_agirlik=1 -> saf EwmacCarver tahmini
    pdt.assert_series_equal(EwmacCarry(trend_agirlik=1.0).tahmin(df), EwmacCarver().tahmin(df))
    # carry gelecek funding'e bağlı değil
    a = s.carry_tahmin(df)
    d2 = df.copy()
    d2.iloc[-100:, d2.columns.get_loc(SUTUN)] = 0.5
    pdt.assert_series_equal(a.iloc[:-100], s.carry_tahmin(d2).iloc[:-100])


def test_ewmac_carry_motor_dumani():
    df = carry_girdi(3000)
    f = fund_serisi(520)
    r = backtest(df, EwmacCarry(), MotorAyarlari(limit_modu="olc"), f)
    assert len(r.islemler) > 0


# ------------------------------------------------------------------ dis__funding-carry
def fc_girdi(n=6000, seed=3):
    m = rastgele_mumlar(n, seed=seed, freq="1h", baslangic="2020-01-01")
    return funding_sutunu_ekle(m, fund_serisi(n // 24 + 5, seed=seed), "1h")


def test_funding_carry_sozlesme_ve_izgara():
    n = 1
    for v in FundingCarry.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27 and set(FundingCarry.parametre_izgarasi) <= set(FundingCarry.varsayilan_parametreler)
    df = fc_girdi(3000)
    for anahtar, degerler in FundingCarry.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = FundingCarry(**{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index)


@pytest.mark.parametrize("kw", [{}, {"rejim": False, "short": True, "giris_z": -1.0}])
def test_funding_carry_lookahead_stop_ve_zaman_cikisi(kw):
    df = fc_girdi()
    s = FundingCarry(**kw)
    tam = s.sinyaller(df)
    for k in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])
    giris = tam[tam.yon != 0]
    assert len(giris) > 0 and giris.stop.notna().all()
    kap = df.kapanis
    l, sh = giris[giris.yon == 1], giris[giris.yon == -1]
    assert (l.stop < kap[l.index]).all() and (sh.stop > kap[sh.index]).all()
    assert (giris.zaman_cikisi_mum == 16).all()
    assert tam.zaman_cikisi_mum[tam.yon == 0].isna().all()
    if kw.get("short"):
        assert len(sh) > 0


def test_funding_carry_yalniz_dusuk_z_ve_rejim():
    df = fc_girdi()
    s = FundingCarry(rejim=False)
    z = s.zskor(df)
    sig = s.sinyaller(df)
    assert (z[sig.yon == 1] < -1.5).all() and (sig.yon == 1).any()
    assert (sig.yon != -1).all()                                  # short kapalı
    sig_r = FundingCarry(rejim=True).sinyaller(df)
    sma = df.kapanis.rolling(500).mean()
    assert (df.kapanis[sig_r.yon == 1] > sma[sig_r.yon == 1]).all()
    assert (sig_r.yon == 1).sum() <= (sig.yon == 1).sum()


def test_funding_carry_sabit_funding_sinyal_yok():
    m = rastgele_mumlar(3000, freq="1h")
    f = pd.DataFrame({"oran": 0.0001}, index=pd.date_range("2022-01-01", periods=400, freq="8h", tz="UTC", name="zaman"))
    assert (FundingCarry().sinyaller(funding_sutunu_ekle(m, f, "1h")).yon == 0).all()    # std=0


def test_funding_carry_motor_ve_portfoy_dumani():
    m = rastgele_mumlar(6000, seed=3, freq="1h", baslangic="2020-01-01")
    f = fund_serisi(260, seed=3)
    s = FundingCarry(rejim=False, giris_z=-1.0)
    r = backtest(funding_sutunu_ekle(m, f, "1h"), s, MotorAyarlari(limit_modu="olc"), f)
    assert len(r.islemler) > 0
    # portföy yolu: veriler ham mum, funding ayrı; kol kurulumunda sütun eklenir
    rp = birlesik_backtest({"BTCUSDT": m}, [(s, "BTCUSDT")], fundingler={"BTCUSDT": f})
    assert len(rp.islemler) > 0
    with pytest.raises(FundingYokHatasi):
        birlesik_backtest({"DK_XAU": m}, [(s, "DK_XAU")], fundingler={})
