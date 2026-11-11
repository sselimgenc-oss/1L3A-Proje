"""Parti 4 sinyal kuralları; piyasa sonucu veya backtest çalıştırmaz."""
import numpy as np
import pandas as pd
import pytest

from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.portfoy.stratejiler.v3 import DonchianAnsambl, VolYonetimliLong
from motor.strateji.dis.v3_adaylar_4 import BtcGecelikMax10, GuniciMomentumNoise
from motor.strateji.kayit import al


def _mum(idx, fiyat):
    k = pd.Series(fiyat, index=idx, dtype=float)
    return pd.DataFrame({"acilis": k - 0.1, "yuksek": k + 0.2,
                         "dusuk": k - 0.2, "kapanis": k,
                         "hacim": 10.0}, index=idx)


def test_noise_yuzde_bandi_onceki_kapanis_cikisi_ve_ters_donus():
    gunler = pd.bdate_range("2024-01-02", periods=15, tz="America/New_York")
    idx = pd.DatetimeIndex([t + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(minutes=30*i)
                            for t in gunler for i in range(13)]).tz_convert("UTC")
    fiyat = np.full(len(idx), 100.0)
    for g in range(14):
        fiyat[g * 13 + 1] = 101.0       # aynı 10:00 slotunda yüzde 1 hareket
        fiyat[g * 13 + 12] = 110.0      # dünkü 16:00 kapanışı
    fiyat[-13 + 1] = 112.0              # UB = max(100,110) * 1.01 = 111.10
    fiyat[-13 + 3] = 80.0               # karşı bandı kırar: long çıkış + short giriş
    m = _mum(idx, fiyat)
    m.loc[m.index[::13], "acilis"] = 100.0
    s = GuniciMomentumNoise().sinyaller(m)
    assert s.yon.iloc[-13 + 1] == 1
    assert s.stop.iloc[-13 + 1] == pytest.approx(111.1)
    assert s.yon.iloc[-13 + 3] == -1 and s.cikis_long.iloc[-13 + 3]
    assert s.stop.iloc[-13 + 3] > m.kapanis.iloc[-13 + 3]
    assert s.cikis.iloc[-1]
    assert not (s.yon.iloc[:14*13] != 0).any()
    assert al(GuniciMomentumNoise.ad) is GuniciMomentumNoise


def test_btc_max10_cuma_giris_hafta_sonu_tutma_pazartesi_cikis():
    idx = pd.date_range("2024-01-01", periods=30*24, freq="1h", tz="UTC")
    m = _mum(idx, np.linspace(100, 120, len(idx)))
    s = BtcGecelikMax10().sinyaller(m)
    ny = idx.tz_convert("America/New_York")
    friday = np.where((ny.day_of_week == 4) & (ny.hour == 15) & (ny.date >= pd.Timestamp("2024-01-19").date()))[0][0]
    assert s.yon.iloc[friday] == 1 and s.stop.iloc[friday] < m.kapanis.iloc[friday]
    monday = np.where((ny.day_of_week == 0) & (ny.hour == 9) & (ny.date == pd.Timestamp("2024-01-22").date()))[0][0]
    assert s.cikis.iloc[monday]
    assert not s.cikis.iloc[friday + 1:monday].any()
    assert al(BtcGecelikMax10.ad) is BtcGecelikMax10


def _gunluk_veri(kapanis, bas="2022-01-01"):
    k = np.asarray(kapanis, dtype=float)
    idx = pd.date_range(bas, periods=len(k), freq="D", tz="UTC", name="zaman")
    o = np.r_[k[0], k[:-1]]
    return pd.DataFrame({"acilis": o, "yuksek": np.maximum(o, k) * 1.01,
                         "dusuk": np.minimum(o, k) * 0.99, "kapanis": k,
                         "hacim": 1_000.0}, index=idx)


def test_donchian_modeli_kapanis_kanali_ve_asagi_inmeyen_mid_stopla_cikar():
    k = pd.Series([100.0] * 4 + [110.0, 109.0, 108.0, 107.0, 105.0, 104.0])
    durum = DonchianAnsambl._model_durumu(k, 5)
    assert durum.iloc[4:8].all()
    assert not durum.iloc[8:].any()  # TS 105'e yükselmiştir; Close <= TS çıkışı


def test_donchian_dokuz_model_agirligi_stopu_ve_vol_emir_esigi():
    n = 470
    r = np.where(np.arange(n) % 2, 0.035, 0.002)
    a = 100.0 * np.exp(np.cumsum(r))
    b = 80.0 * np.exp(np.cumsum(r[::-1]))
    veri = {"A": _gunluk_veri(a), "B": _gunluk_veri(b)}
    st = DonchianAnsambl(semboller=("A", "B"))
    h, stop = st.sinyaller(veri)
    emir = h.dropna(how="all")
    assert st.parametreler["pencereler"] == (5, 10, 20, 30, 60, 90, 150, 250, 360)
    assert len(emir) > 0 and (emir.fillna(0.0) >= 0).all().all()
    assert (emir.fillna(0.0) <= 1.0).all().all()
    acilis = emir.gt(0).any(axis=1)
    assert stop.loc[emir.index[acilis]].where(emir.loc[acilis] > 0).notna().any(axis=1).all()
    h0, _ = DonchianAnsambl(semboller=("A", "B"), vol_islem_esigi=0.0).sinyaller(veri)
    assert len(emir) < len(h0.dropna(how="all"))
    assert tum_portfoy_stratejileri()[DonchianAnsambl.ad] is DonchianAnsambl


def test_vol_yonetimli_long_onceki_tam_ayi_kullanir_ve_aylik_dengeler():
    idx = pd.date_range("2024-01-01", "2024-03-10", freq="D", tz="UTC", name="zaman")
    jan = np.where(np.arange(31) % 2, 0.01, -0.005)
    feb = np.where(np.arange(29) % 2, 0.03, -0.015)
    mar = np.full(10, 0.20)  # Mart geleceği, Mart başı ağırlığını etkilememeli
    k = 100.0 * np.cumprod(1.0 + np.r_[jan, feb, mar])
    veri = {"X": _gunluk_veri(k, "2024-01-01")}
    st = VolYonetimliLong(semboller=("X",))
    h, stop = st.sinyaller(veri)
    mart = pd.Timestamp("2024-03-01", tz="UTC")
    r = veri["X"].kapanis.pct_change(fill_method=None)
    subat = r[(r.index.month == 2)]
    beklenen = min(0.20 / (subat.std() * np.sqrt(252.0)), 1.0)
    assert h.loc[mart, "X"] == pytest.approx(beklenen)
    assert h.loc[mart, "X"] > 0 and stop.loc[mart, "X"] < veri["X"].loc[mart, "kapanis"]
    assert h.dropna(how="all").index.tz_localize(None).to_period("M").is_unique
    veri2 = {"X": veri["X"].copy()}
    veri2["X"].loc[veri2["X"].index >= mart, "kapanis"] *= 4.0
    h2, _ = st.sinyaller(veri2)
    assert h2.loc[mart, "X"] == pytest.approx(h.loc[mart, "X"])
    assert tum_portfoy_stratejileri()[VolYonetimliLong.ad] is VolYonetimliLong
    # İki sembolde her biri 1/2 sermaye alır: toplam ağırlık tavanı aşmaz.
    st2 = VolYonetimliLong(semboller=("X", "Y"))
    h3, _ = st2.sinyaller({"X": veri["X"], "Y": veri["X"].copy()})
    assert h3.loc[mart, "X"] == pytest.approx(beklenen / 2)
    assert h3.loc[mart].sum() <= 1.0 + 1e-12
