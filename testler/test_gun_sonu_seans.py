"""Gün sonu (seansın son mumu) tespiti: seanslı veri (ABD hisse, BIST, 24/5 vadeli) ve kripto regresyonu.

Denetim bulgusu Y2 (2026-11-08): eski kural yalnız "kapanış bir sonraki UTC gününe taşıyor mu" idi; seanslı veride son mum
hiç işaretlenmiyordu. Kripto davranışı birebir korunmalı.
"""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from motor.strateji import seans_takvimi as st
from motor.strateji.daytrade._ortak import seans_son_mumu
from motor.strateji.kayit import al
from motor.strateji.onceki._ortak import gun_sonu_maskesi
from motor.veri.depo import MUM_DIZINI

NY = "America/New_York"


def _eski_kural(index: pd.DatetimeIndex, seans_saat: float = 0.0) -> np.ndarray:
    """Değişiklik öncesi seans_son_mumu (referans; kripto için birebir aynı kalmalı)."""
    n = len(index)
    if n < 2:
        return np.zeros(n, dtype=bool)
    fark = ((index[1:] - index[:-1]) / pd.Timedelta(seconds=1)).to_numpy()
    sure = np.r_[np.nan, np.minimum.accumulate(fark)]
    gecerli = ~np.isnan(sure)
    kap = index + pd.to_timedelta(np.where(gecerli, sure, 0.0), unit="s")
    k = kap - pd.Timedelta(hours=seans_saat)
    a = index - pd.Timedelta(hours=seans_saat)
    return (k.floor("D") != a.floor("D")) & gecerli


def _hisse_index(bas: str, bit: str, adim: str) -> pd.DatetimeIndex:
    """NYSE seansı (09:30-16:00 NY, tatil yok sayılır ama erken kapanış uygulanır), Dukascopy gibi UTC'ye hizalı etiket."""
    zamanlar = []
    for g in pd.bdate_range(bas, bit):
        d = g.date()
        kapanis = "13:00" if st._nyse_erken_kapanis(d) else "16:00"
        if d in st._abd_tatilleri(d.year):
            continue
        a = pd.Timestamp(f"{d} 09:30", tz=NY).tz_convert("UTC")
        k = pd.Timestamp(f"{d} {kapanis}", tz=NY).tz_convert("UTC")
        zamanlar += list(pd.date_range(a.floor(adim), k - pd.Timedelta(adim), freq=adim))
    return pd.DatetimeIndex(zamanlar)


def _mumlar(index: pd.DatetimeIndex, tohum: int = 0, gece_boslugu: float = 0.0) -> pd.DataFrame:
    r = np.random.default_rng(tohum)
    adim = r.normal(0, 0.004, len(index))
    if gece_boslugu:
        yeni_gun = np.r_[False, index[1:].date != index[:-1].date]
        adim = adim + yeni_gun * r.choice([-1, 1], len(index)) * gece_boslugu
    k = 100 * np.exp(np.cumsum(adim))
    a = np.r_[k[0], k[:-1]] * np.where(np.r_[False, index[1:].date != index[:-1].date], np.exp(adim), 1.0)
    y = np.maximum(a, k) * (1 + np.abs(r.normal(0, 0.002, len(index))))
    d = np.minimum(a, k) * (1 - np.abs(r.normal(0, 0.002, len(index))))
    return pd.DataFrame({"acilis": a, "yuksek": y, "dusuk": d, "kapanis": k, "hacim": 1000.0, "quote_hacim": 1e5,
                         "islem_sayisi": 10}, index=index)


# ------------------------------------------------------------------ kripto regresyonu
@pytest.mark.parametrize("adim", ["5min", "15min", "1h", "4h", "1D"])
@pytest.mark.parametrize("seans_saat", [0.0, 7.0, 13.5])
def test_kripto_birebir_ayni(adim, seans_saat):
    idx = pd.date_range("2024-01-01", "2024-03-15", freq=adim, tz="UTC")
    # veri delikleri (borsa kesintisi) de olsun
    idx = idx.delete(np.arange(50, len(idx), 97))
    assert st.seans_turu(idx) == st.KRIPTO
    assert (seans_son_mumu(idx, seans_saat) == _eski_kural(idx, seans_saat)).all()
    if seans_saat == 0.0:
        assert (gun_sonu_maskesi(idx) == _eski_kural(idx, 0.0)).all()


def test_kripto_kisa_hafta_ici_pencere_kripto_kalir():
    # Cumartesisiz kısa pencere (Pzt-Cum), kesintisiz: seanslı sayılmamalı
    idx = pd.date_range("2024-01-01", "2024-01-05 23:00", freq="1h", tz="UTC")
    assert st.seans_turu(idx) == st.KRIPTO
    assert (seans_son_mumu(idx) == _eski_kural(idx)).all()


@pytest.mark.parametrize("ad", ["daytrade__gap-devam", "daytrade__vwap-trend", "daytrade__pin-bar",
                                "swing__gap-devam", "onceki__kgt"])
def test_kripto_strateji_sinyalleri_ayni(ad, monkeypatch):
    idx = pd.date_range("2024-01-01", periods=24 * 60, freq="1h", tz="UTC")
    m = _mumlar(idx, 3)
    yeni = al(ad)().sinyaller(m)
    import motor.strateji.daytrade._ortak as ortak
    gercek = ortak.seans_son_mumu
    monkeypatch.setattr(ortak, "seans_son_mumu", lambda i, s=0.0, tur=None: gercek(i, s, st.KRIPTO))
    import sys
    for mod in list(sys.modules.values()):
        if getattr(mod, "seans_son_mumu", None) is gercek:
            monkeypatch.setattr(mod, "seans_son_mumu", ortak.seans_son_mumu)
    eski = al(ad)().sinyaller(m)
    pd.testing.assert_frame_equal(yeni, eski)


# ------------------------------------------------------------------ ABD hisse
@pytest.mark.parametrize("adim", ["5min", "30min", "1h"])
def test_hisse_her_seans_gununde_tam_bir_gun_sonu(adim):
    idx = _hisse_index("2023-06-01", "2024-01-31", adim)
    assert st.seans_turu(idx) == st.ABD_HISSE
    son = seans_son_mumu(idx)
    gun = pd.Index(idx.tz_convert(NY).date)
    say = pd.Series(son).groupby(gun).sum()
    assert (say == 1).all()
    # işaretli mum günün son mumu
    son_mum = pd.Series(idx, index=idx).groupby(gun).max()
    assert set(idx[son]) == set(son_mum)
    # erken kapanış günü (24 Kasım 2023, 13:00 NY = 18:00 UTC): son mum 18:00'de kapanır
    t = idx[son][gun[son] == date(2023, 11, 24)][0]
    assert t + pd.Timedelta(adim) == pd.Timestamp("2023-11-24 18:00", tz="UTC")


def test_hisse_yaz_kis_saati_kapanisi():
    idx = _hisse_index("2024-03-01", "2024-03-29", "1h")
    son = idx[seans_son_mumu(idx)]
    # DST 10 Mart 2024: öncesi son mum 20:00 UTC (16:00 EST), sonrası 19:00 UTC (16:00 EDT)
    assert {t.hour for t in son if t.day < 10} == {20}
    assert {t.hour for t in son if t.day > 10} == {19}


def test_hisse_seans_disi_mum_da_isaretli():
    idx = _hisse_index("2024-01-08", "2024-01-12", "1h")
    ekstra = pd.Timestamp("2024-01-09 21:00", tz="UTC")       # 16:00 NY: seans sonrası mum
    idx = idx.append(pd.DatetimeIndex([ekstra])).sort_values()
    son = pd.Series(seans_son_mumu(idx), index=idx)
    assert son[pd.Timestamp("2024-01-09 20:00", tz="UTC")] and son[ekstra]


def test_lookahead_yok_onek_degismez():
    """Bir mumun işareti, serinin sonraki mumlarından bağımsızdır (önek ile tam seri aynı)."""
    for idx in (_hisse_index("2024-01-02", "2024-02-28", "30min"),
                pd.read_parquet(MUM_DIZINI / "DK_XAU" / "1h.parquet").index[-3000:]
                if (MUM_DIZINI / "DK_XAU" / "1h.parquet").exists() else None):
        if idx is None:
            continue
        tam = seans_son_mumu(idx)
        tur = st.seans_turu(idx)
        for kes in (len(idx) // 3, len(idx) // 2, len(idx) - 7):
            assert st.seans_turu(idx[:kes]) == tur
            assert (seans_son_mumu(idx[:kes]) == tam[:kes]).all()


# ------------------------------------------------------------------ BIST
def test_bist_kapanis_ve_yarim_gun():
    gunler = [d for d in pd.bdate_range("2026-10-19", "2026-11-06")]
    idx = []
    for g in gunler:
        d = g.date()
        k = "12:30" if d == date(2026, 10, 28) else "18:00"
        a = pd.Timestamp(f"{d} 10:00", tz="Europe/Istanbul").tz_convert("UTC")
        b = pd.Timestamp(f"{d} {k}", tz="Europe/Istanbul").tz_convert("UTC")
        idx += list(pd.date_range(a, b - pd.Timedelta("30min"), freq="30min"))
    idx = pd.DatetimeIndex(idx)
    assert st.seans_turu(idx) == st.BIST
    son = seans_son_mumu(idx)
    say = pd.Series(son).groupby(pd.Index(idx.date)).sum()
    assert (say == 1).all()
    assert {t.strftime("%H:%M") for t in idx[son] if t.date() != date(2026, 10, 28)} == {"14:30"}
    assert [t.strftime("%H:%M") for t in idx[son] if t.date() == date(2026, 10, 28)] == ["09:00"]


# ------------------------------------------------------------------ 24/5 vadeli (CME benzeri)
def test_vadeli_cuma_ve_buyuk_cuma_arifesi():
    idx = pd.date_range("2024-03-17 22:00", "2024-04-12 20:00", freq="1h", tz="UTC")
    ny = idx.tz_convert(NY)
    acik = (ny.weekday < 5) | ((ny.weekday == 6) & (ny.hour >= 18))
    acik &= ~((ny.weekday == 4) & (ny.hour >= 17))
    acik &= ~((ny.hour == 17))                                  # günlük mola 17-18 NY
    kapali_bas = pd.Timestamp("2024-03-28 17:00", tz=NY)        # Büyük Cuma (29 Mart) arifesi
    kapali_bit = pd.Timestamp("2024-03-31 18:00", tz=NY)
    acik &= ~((idx >= kapali_bas) & (idx < kapali_bit))
    idx = idx[acik]
    assert st.seans_turu(idx) == st.VADELI
    son = pd.Series(seans_son_mumu(idx), index=idx)
    # Cuma 17:00 NY (yaz: 21:00 UTC) kapanışından önceki son mum 20:00 UTC işaretli
    for cuma in ("2024-03-22", "2024-04-05", "2024-04-12"):
        assert son[pd.Timestamp(f"{cuma} 20:00", tz="UTC")]
    assert son[pd.Timestamp("2024-03-28 20:00", tz="UTC")]
    # hafta içi gece yarısı kuralı aynen (23:00 mumu)
    assert son[pd.Timestamp("2024-04-03 23:00", tz="UTC")]
    assert not son[pd.Timestamp("2024-04-03 20:00", tz="UTC")]


# ------------------------------------------------------------------ gap stratejileri hissede sinyal üretir
@pytest.mark.parametrize("ad", ["swing__gap-devam", "swing__gap-doldurma", "daytrade__gap-devam",
                                "daytrade__gap-doldurma"])
def test_gap_stratejileri_hissede_sinyal_uretir(ad):
    idx = _hisse_index("2022-01-03", "2023-12-29", "1h")
    m = _mumlar(idx, 7, gece_boslugu=0.02)
    sig = al(ad)().sinyaller(m)
    assert (sig["yon"] != 0).sum() > 0


def test_daytrade_hisse_pozisyon_gun_sonunda_kapanis_fiyatindan_kapanir():
    """Gün sonu çıkışı seansın son mumunun KAPANIŞINDAN dolar (kayma + taker aynen): işlem aynı seans günü kapanır,
    çıkış zamanı = son mumun kapanış anı, gece boşluğu çıkış fiyatına girmez."""
    from motor.backtest.motor import MotorAyarlari, backtest
    idx = _hisse_index("2022-01-03", "2023-12-29", "1h")
    m = _mumlar(idx, 11, gece_boslugu=0.02)
    s = al("daytrade__gap-devam")()
    sig = s.sinyaller(m)
    assert "gun_sonu_kapanis" in sig.columns
    assert (sig["gun_sonu_kapanis"] == seans_son_mumu(idx)).all()
    ay = MotorAyarlari(limit_modu="olc")      # rastgele veride kill switch işlemi durdurmasın
    isl = backtest(m, s, ay).islemler
    gs = isl[isl["cikis_nedeni"] == "gun_sonu"]
    assert len(gs) > 0 and set(isl["cikis_nedeni"]) <= {"gun_sonu", "stop", "hedef"}
    g = pd.DatetimeIndex(isl["giris_zamani"]).tz_convert(NY).date
    c = (pd.DatetimeIndex(isl["cikis_zamani"]) - pd.Timedelta(seconds=1)).tz_convert(NY).date
    assert (g == c).all()                                            # hiçbir işlem geceye taşınmaz
    kayma = ay.kayma_bps / 10000
    for _, r in gs.iterrows():
        mum = r["cikis_zamani"] - pd.Timedelta("1h")
        assert seans_son_mumu(idx)[idx.get_loc(mum)]
        beklenen = m.loc[mum, "kapanis"] * (1 - r["yon"] * kayma)
        assert r["cikis_fiyati"] == pytest.approx(beklenen, abs=0.011)  # tick 0.01


def test_kripto_sinyalinde_gun_sonu_kapanis_sutunu_yok():
    idx = pd.date_range("2024-01-01", periods=24 * 30, freq="1h", tz="UTC")
    for ad in ("daytrade__gap-devam", "daytrade__pin-bar", "onceki__kgt"):
        assert "gun_sonu_kapanis" not in al(ad)().sinyaller(_mumlar(idx, 5)).columns


# ------------------------------------------------------------------ gerçek veri (varsa)
@pytest.mark.parametrize("dosya", ["DK_AAPL/1h.parquet", "DK_AAPL/5m.parquet"])
def test_gercek_hisse_verisi_gun_sonu(dosya):
    yol = MUM_DIZINI / dosya
    if not yol.exists():
        pytest.skip(f"veri yok: {yol}")
    idx = pd.read_parquet(yol).index
    son = seans_son_mumu(idx)
    gun = pd.Index(idx.tz_convert(NY).date)
    df = pd.DataFrame({"g": gun, "s": son})
    var = df.groupby("g")["s"].any()
    # işaretler günün sonunda kesintisiz bir blok (kapanışı kapsayan mum + varsa seans dışı mumlar)
    sonek = df.groupby("g")["s"].apply(lambda x: (not x.any()) or bool(x.values[int(np.argmax(x.values)):].all()))
    assert sonek.all()
    # gün sonu bulunamayan gün yalnız veri deliği (kapanış saatinden önce biten gün): <= %0.2
    assert (~var).sum() <= max(3, int(0.002 * len(var)))
