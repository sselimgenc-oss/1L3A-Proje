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


def _noise_veri(son_gun_duzenle=None):
    """15 seans x 13 adet 30 dk mum (09:30-15:30 ET açılışlı). İlk 14 gün: 10:00 slotunda %1 hareket, kapanış 110."""
    gunler = pd.bdate_range("2024-01-02", periods=15, tz="America/New_York")
    idx = pd.DatetimeIndex([t + pd.Timedelta(hours=9, minutes=30) + pd.Timedelta(minutes=30 * i)
                            for t in gunler for i in range(13)]).tz_convert("UTC")
    fiyat = np.full(len(idx), 100.0)
    for g in range(14):
        fiyat[g * 13 + 1] = 101.0       # aynı 10:00 slotunda yüzde 1 hareket
        fiyat[g * 13 + 12] = 110.0      # dünkü 16:00 kapanışı
    fiyat[-13 + 1] = 112.0              # UB = max(100,110) * 1.01 = 111.10
    fiyat[-13 + 3] = 80.0               # karşı bandı kırar: long çıkış + short giriş
    if son_gun_duzenle:
        son_gun_duzenle(fiyat)
    m = _mum(idx, fiyat)
    m.loc[m.index[::13], "acilis"] = 100.0
    return m


def _gunluk_atr_beklenen(m, n=14):
    """Bağımsız hesap: tamamlanmış nakit seansların (09:30-16:00 ET) günlük ATR(14) değeri, tarih -> ATR (shift'siz)."""
    ny = m.index.tz_convert("America/New_York")
    d = pd.Series(ny.date, index=m.index)
    h, l, c = (m[x].groupby(d).agg(f) for x, f in (("yuksek", "max"), ("dusuk", "min"), ("kapanis", "last")))
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def test_noise_yuzde_bandi_onceki_kapanis_cikisi_ve_ters_donus():
    m = _noise_veri()
    s = GuniciMomentumNoise().sinyaller(m)
    atr = _gunluk_atr_beklenen(m)
    son_gun = m.index[-1].tz_convert("America/New_York").date()
    onceki_atr = atr.shift(1)[son_gun]              # yalnız tamamlanmış önceki seanslar
    assert np.isfinite(onceki_atr) and onceki_atr > 0
    assert s.yon.iloc[-13 + 1] == 1
    # Motor stopu felaket stopu: giriş kapanışı - 1 x günlük ATR (giriş anı bant/VWAP seviyesi DEĞİL).
    assert s.stop.iloc[-13 + 1] == pytest.approx(112.0 - onceki_atr)
    assert s.stop.iloc[-13 + 1] != pytest.approx(111.1)
    assert s.yon.iloc[-13 + 3] == -1 and s.cikis_long.iloc[-13 + 3]
    assert s.stop.iloc[-13 + 3] == pytest.approx(80.0 + onceki_atr)
    assert s.cikis.iloc[-1]
    assert not (s.yon.iloc[:14*13] != 0).any()
    assert al(GuniciMomentumNoise.ad) is GuniciMomentumNoise


def test_noise_cikis_kapanis_tabanli_cari_cizgiye_gore_fitil_cikis_degil():
    """Çıkış yalnız mum KAPANIŞINDA, o anki max(UB,VWAP) ile karşılaştırılır; fitil tek başına çıkış sayılmaz."""
    def fitil(f):
        f[-13 + 2] = 111.5      # kapanış UB (111.1) üstünde kalır
        f[-13 + 3] = 111.5
    m = _noise_veri(fitil)
    m.loc[m.index[-13 + 2], "dusuk"] = 90.0       # derin fitil: eski mum-içi stop bunu tetiklerdi
    s = GuniciMomentumNoise().sinyaller(m)
    assert s.yon.iloc[-13 + 1] == 1
    assert not s.cikis_long.iloc[-13 + 2]
    # 10:30 slotunda sigma=0: UB=110. Kapanış 109.5 < 110 -> çıkış işareti; stop ise çok daha aşağıda kalır.
    def alti(f):
        f[-13 + 2] = 109.5
    m2 = _noise_veri(alti)
    s2 = GuniciMomentumNoise().sinyaller(m2)
    assert s2.cikis_long.iloc[-13 + 2]
    assert s2.stop.iloc[-13 + 1] < 109.5 - 0.5


def test_noise_gun_sonu_16_00_fiyatindan_kapanir_ve_son_mumda_giris_yok():
    def son_mum(f):
        f[-1] = 125.0         # 15:30 mumu bandın çok üstünde: yeni giriş olmamalı
    m = _noise_veri(son_mum)
    s = GuniciMomentumNoise().sinyaller(m)
    ny = m.index.tz_convert("America/New_York")
    son = np.asarray((ny.hour * 60 + ny.minute) >= 930)
    assert s.gun_sonu_kapanis.to_numpy().tolist() == son.tolist()       # motor 15:30 mumunun KAPANIŞINDA (16:00) kapatır
    assert s.cikis.to_numpy()[son].all() and not s.cikis.to_numpy()[~son].any()
    assert s.cikis_long.to_numpy()[son].all() and s.cikis_short.to_numpy()[son].all()
    assert (s.yon.to_numpy()[son] == 0).all()


def test_noise_lookahead_yok_gelecegi_kesmek_gecmis_sinyali_degistirmez():
    m = _noise_veri()
    tam = GuniciMomentumNoise().sinyaller(m)
    for kes in (m.index[-13 + 2], m.index[-13 + 5]):
        kisa = GuniciMomentumNoise().sinyaller(m[m.index <= kes])
        pd.testing.assert_frame_equal(kisa, tam.loc[kisa.index], check_dtype=False)
    # Aynı seansın sonraki mumları değişse de önceki mumun stopu (günlük ATR) değişmez.
    m2 = m.copy()
    m2.iloc[-8:, m2.columns.get_loc("yuksek")] = 500.0
    s2 = GuniciMomentumNoise().sinyaller(m2)
    assert s2.stop.iloc[-13 + 1] == pytest.approx(tam.stop.iloc[-13 + 1])


def _btc_veri(bas="2023-12-01", gun=70, fiyat_fn=None):
    idx = pd.date_range(bas, periods=gun * 24, freq="1h", tz="UTC")
    f = np.linspace(100.0, 160.0, len(idx))
    if fiyat_fn:
        f = fiyat_fn(idx, f)
    return _mum(idx, f)


def _ny_konum(m, tarih, saat):
    ny = m.index.tz_convert("America/New_York")
    return int(np.where((ny.date == pd.Timestamp(tarih).date()) & (ny.hour == saat))[0][0])


def test_btc_max10_cuma_giris_hafta_sonu_tutma_pazartesi_cikis():
    m = _btc_veri()
    s = BtcGecelikMax10().sinyaller(m)
    ny = m.index.tz_convert("America/New_York")
    friday = _ny_konum(m, "2024-01-26", 15)
    assert s.yon.iloc[friday] == 1 and s.stop.iloc[friday] < m.kapanis.iloc[friday]
    monday = _ny_konum(m, "2024-01-29", 9)
    assert s.cikis.iloc[monday]
    assert not s.cikis.iloc[friday + 1:monday].any()
    # Giriş yalnız Cuma/Pzt/Salı 15:00 ET mumunda; başka saat/gün sinyal yok.
    giris = np.flatnonzero(s.yon.to_numpy() == 1)
    assert len(giris) > 0
    assert set(ny.hour[giris]) == {15} and set(ny.day_of_week[giris]) <= {0, 1, 4}
    assert al(BtcGecelikMax10.ad) is BtcGecelikMax10


def test_btc_max10_zirve_16_00_kapanislarindan_gelir_fitil_ve_esitlik():
    """MAX = önceki 10 işlem gününün 16:00 KAPANIŞLARI (gün içi fitil değil); eşitlik (>=) giriş verir."""
    def duz(idx, f):
        return np.full(len(f), 100.0)
    m = _btc_veri(fiyat_fn=duz)
    ny = m.index.tz_convert("America/New_York")
    cuma = _ny_konum(m, "2024-01-26", 15)
    # Düz 100: her 16:00 kapanışı 100 -> eşitlik: giriş var.
    assert BtcGecelikMax10().sinyaller(m).yon.iloc[cuma] == 1
    # Önceki bir günün gün içi FITILI çok yüksek: kapanış tanımında etkisiz, giriş sürer.
    m_f = m.copy()
    m_f.iloc[_ny_konum(m, "2024-01-22", 11), m_f.columns.get_loc("yuksek")] = 500.0
    assert BtcGecelikMax10().sinyaller(m_f).yon.iloc[cuma] == 1
    # Önceki bir günün 16:00 KAPANIŞI yüksek: Cuma kapanışı onu geçemez, giriş yok.
    m_k = m.copy()
    j = _ny_konum(m, "2024-01-22", 15)
    m_k.iloc[j, m_k.columns.get_loc("kapanis")] = 130.0
    m_k.iloc[j, m_k.columns.get_loc("yuksek")] = 130.0
    s_k = BtcGecelikMax10().sinyaller(m_k)
    assert s_k.yon.iloc[cuma] == 0
    # Pencere dışı (11 işlem günü önce) yüksek kapanış etkisiz.
    m_e = m.copy()
    j2 = _ny_konum(m, "2024-01-10", 15)
    m_e.iloc[j2, m_e.columns.get_loc("kapanis")] = 130.0
    m_e.iloc[j2, m_e.columns.get_loc("yuksek")] = 130.0
    assert BtcGecelikMax10().sinyaller(m_e).yon.iloc[cuma] == 1


def test_btc_max10_islem_gunu_takvimi_tatil_ve_eksik_gun():
    def duz(idx, f):
        return np.full(len(f), 100.0)
    m = _btc_veri(fiyat_fn=duz)
    sali = _ny_konum(m, "2024-01-16", 15)   # Pzt 15 Ocak = MLK tatili; Salı girişi çalışır
    # Tatil günü (MLK) 16:00 kapanışı yüksek olsa da pencereye girmez (NYSE işlem günü değil).
    m_t = m.copy()
    jt = _ny_konum(m, "2024-01-15", 15)
    m_t.iloc[jt, m_t.columns.get_loc("kapanis")] = 150.0
    s_t = BtcGecelikMax10().sinyaller(m_t)
    assert s_t.yon.iloc[sali] == 1
    assert s_t.yon.iloc[jt] == 0           # tatil gününde giriş yok
    # Pencerede eksik işlem günü (15:00 mumu veride yok): kısa pencereden sinyal üretilmez.
    m_x = m.drop(m.index[_ny_konum(m, "2024-01-22", 15)])
    s_x = BtcGecelikMax10().sinyaller(m_x)
    cuma = m_x.index[_ny_konum(m, "2024-01-26", 15) - 1]
    assert s_x.loc[cuma, "yon"] == 0


def test_btc_max10_stop_gunluk_atr_ve_lookahead_yok():
    m = _btc_veri()
    s = BtcGecelikMax10().sinyaller(m)
    ny = m.index.tz_convert("America/New_York")
    d = pd.Series(ny.date, index=m.index)
    h, l, c = (m[x].groupby(d).agg(f) for x, f in (("yuksek", "max"), ("dusuk", "min"), ("kapanis", "last")))
    tr = pd.concat([h - l, (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean().shift(1)   # yalnız tamamlanmış günler
    cuma = _ny_konum(m, "2024-01-26", 15)
    beklenen = m.kapanis.iloc[cuma] - 2.0 * atr[pd.Timestamp("2024-01-26").date()]
    assert s.stop.iloc[cuma] == pytest.approx(beklenen)
    # Gelecek kesilirse / değişirse geçmiş sinyal ve stop aynı kalır.
    kisa = BtcGecelikMax10().sinyaller(m.iloc[:cuma + 1])
    pd.testing.assert_frame_equal(kisa, s.iloc[:cuma + 1], check_dtype=False)
    m2 = m.copy()
    m2.iloc[cuma + 1:, m2.columns.get_loc("yuksek")] = 1000.0
    m2.iloc[cuma + 1:, m2.columns.get_loc("kapanis")] = 1000.0
    s2 = BtcGecelikMax10().sinyaller(m2)
    assert s2.stop.iloc[cuma] == pytest.approx(s.stop.iloc[cuma]) and s2.yon.iloc[cuma] == 1


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
