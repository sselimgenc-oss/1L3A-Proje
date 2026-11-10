"""v3 adayları ikinci parti: öncelik 2 kural, kayıt ve CSV testleri."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.portfoy.stratejiler.v3 import FundingZ90UcGun
from motor.strateji.dis.v3_adaylar_2 import (
    AralikKirilimBekleyenEmir, LSekliMaKirilimLong, Orb4sHacimAtr,
    Rsi2Sma200GeriCekilme, TersFvgNqLong,
)
from motor.strateji.kayit import tum_stratejiler


KOK = Path(__file__).resolve().parents[1]


def mum(kapanis, freq="5min", bas="2024-01-01", hacim=None, genlik=0.001):
    k = np.asarray(kapanis, dtype=float)
    idx = pd.date_range(bas, periods=len(k), freq=freq, tz="UTC", name="zaman")
    o = np.r_[k[0], k[:-1]]
    h = np.maximum(o, k) * (1.0 + genlik)
    d = np.minimum(o, k) * (1.0 - genlik)
    v = np.ones(len(k)) if hacim is None else np.asarray(hacim, dtype=float)
    return pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": d, "kapanis": k, "hacim": v}, index=idx)


def test_aralik_kirilimi_karsi_uc_stop_1r_hedef_ve_22_cikisi():
    df = mum(np.full(2 * 24 * 12, 100.0))
    i = df.index.get_loc(pd.Timestamp("2024-01-02 07:00", tz="UTC"))
    df.iloc[i, df.columns.get_loc("kapanis")] = 105.0
    df.iloc[i, df.columns.get_loc("yuksek")] = 105.1
    sig = AralikKirilimBekleyenEmir(tampon_atr=0.0).sinyaller(df)
    g = sig[sig["yon"] != 0]
    assert len(g) == 1 and g.iloc[0].yon == 1
    assert g.iloc[0].stop < df.loc[g.index[0], "kapanis"] < g.iloc[0].hedef
    assert np.isclose(g.iloc[0].hedef - df.loc[g.index[0], "kapanis"],
                      df.loc[g.index[0], "kapanis"] - g.iloc[0].stop)
    assert sig.loc[pd.Timestamp("2024-01-02 21:55", tz="UTC"), "cikis"]


def test_l_sekli_dusus_sikisma_ve_sma_kiriliminda_long():
    fiyat = np.r_[np.full(100, 110.0), [108, 104, 99, 95], np.full(10, 95.0), 112.0]
    df = mum(fiyat, "1h")
    sig = LSekliMaKirilimLong().sinyaller(df)
    g = sig[sig["yon"] != 0]
    assert list(g.index) == [df.index[-1]]
    assert g.iloc[0].stop == 112.0 * 0.95 and g.iloc[0].hedef == 112.0 * 1.10


def test_orb_ilk_4s_araligini_hacimle_kirar_ve_iz_stop_ayarlidir():
    fiyat = np.full(40, 100.0)
    hacim = np.ones(40)
    fiyat[31], hacim[31] = 110.0, 3.0
    df = mum(fiyat, "4h", hacim=hacim)
    sig = Orb4sHacimAtr().sinyaller(df)
    assert sig.iloc[31].yon == 1 and pd.notna(sig.iloc[31].stop)
    assert Orb4sHacimAtr.cikis_ayarlari.atr_iz_suren_k == 1.0


def test_ters_fvg_15m_kapandiktan_sonra_5m_retest_long_ve_1545_cikis():
    idx = pd.date_range("2024-01-02 14:00", periods=84, freq="5min", tz="UTC", name="zaman")
    df = pd.DataFrame({"acilis": 99.0, "yuksek": 100.0, "dusuk": 98.0,
                       "kapanis": 99.0, "hacim": 1.0}, index=idx)
    # 14:00 HTF mumu tepe 100; 14:15 ara mum; 14:30 HTF mumu dip 105 -> [100,105] FVG.
    df.loc["2024-01-02 14:15":"2024-01-02 14:25", ["acilis", "yuksek", "dusuk", "kapanis"]] = [105, 106, 104, 105]
    df.loc["2024-01-02 14:30":"2024-01-02 14:40", ["acilis", "yuksek", "dusuk", "kapanis"]] = [106, 108, 105, 107]
    # 14:55'te yerel [101,103] FVG, 15:00'te içine inip üstünde kapanış.
    df.loc["2024-01-02 14:45", ["acilis", "yuksek", "dusuk", "kapanis"]] = [101, 101, 100.5, 100.8]
    df.loc["2024-01-02 14:50", ["acilis", "yuksek", "dusuk", "kapanis"]] = [102, 102.5, 101.5, 102]
    df.loc["2024-01-02 14:55", ["acilis", "yuksek", "dusuk", "kapanis"]] = [103, 104, 103, 103.5]
    df.loc["2024-01-02 15:00", ["acilis", "yuksek", "dusuk", "kapanis"]] = [103, 104.5, 102, 104]
    sig = TersFvgNqLong().sinyaller(df)
    assert sig.loc[pd.Timestamp("2024-01-02 15:00", tz="UTC"), "yon"] == 1
    assert sig.loc[pd.Timestamp("2024-01-02 15:00", tz="UTC"), "stop"] == 99.0
    assert sig.loc[pd.Timestamp("2024-01-02 20:40", tz="UTC"), "cikis"]


def test_rsi2_sma200_ustunde_dipte_long_stop_ve_bes_mum_suresi():
    fiyat = np.r_[np.linspace(100, 200, 210), 198.0, 194.0, 190.0]
    df = mum(fiyat, "1D")
    sig = Rsi2Sma200GeriCekilme().sinyaller(df)
    g = sig[sig["yon"] == 1]
    assert len(g) > 0 and g.stop.notna().all() and g.zaman_cikisi_mum.eq(5).all()


def test_funding_z90_uc_gunde_bir_dolar_notr_ve_stoplu():
    idx = pd.date_range("2023-01-01", periods=200, freq="D", tz="UTC", name="zaman")
    veriler = {}
    for s, oran in zip(("BTCUSDT", "ETHUSDT", "SOLUSDT"), (1.0, -1.0, 0.2)):
        k = 100.0 * np.exp(0.001 * np.arange(len(idx)))
        df = mum(k, "1D")
        df.index = idx
        df["funding_orani"] = oran * np.linspace(-0.001, 0.001, len(idx))
        veriler[s] = df
    h, stop = FundingZ90UcGun(semboller=tuple(veriler)).sinyaller(veriler)
    acik = h.dropna(how="all")
    acik = acik[acik.abs().sum(axis=1) > 0]
    assert len(acik) > 0 and np.allclose(acik.sum(axis=1), 0.0)
    assert stop.loc[acik.index].notna().any(axis=1).all()
    assert (acik.index[1:] - acik.index[:-1] == pd.Timedelta(days=3)).all()


def test_ikinci_parti_kayitlari_ve_csv_durumlari_tam():
    tek = tum_stratejiler()
    pf = tum_portfoy_stratejileri()
    yeni_tek = {
        "v3__aralik-kirilim-bekleyen-emir", "v3__l-sekli-ma-kirilim-long",
        "v3__orb-4s-hacim-atr", "v3__ters-fvg-nq-long", "v3__rsi2-sma200-geri-cekilme",
    }
    assert yeni_tek <= set(tek) and "pf__v3-funding-z90-3gun" in pf

    with (KOK / "stratejiler/v3_adaylar/adaylar.csv").open(encoding="utf-8-sig", newline="") as f:
        adaylar = [r for r in csv.DictReader(f) if r["oncelik"] == "2"]
    with (KOK / "stratejiler/v3_adaylar/kodlama_v3.csv").open(encoding="utf-8", newline="") as f:
        kodlama = {r["kart_id"]: r for r in csv.DictReader(f)}
    assert {r["kart_id"] for r in adaylar} <= set(kodlama)
    uygun = set()
    for aday in adaylar:
        kart = KOK / "stratejiler/v3_adaylar/kartlar" / f"{aday['kart_id']}.json"
        if json.loads(kart.read_text())["veri_uygun"][0]:
            uygun.add(aday["kart_id"])
    assert len(uygun) == 8
    assert {kodlama[x]["durum"] for x in uygun} == {"kodlandi", "tekrar", "belirsiz"}
    assert sum(kodlama[x]["durum"] == "kodlandi" for x in uygun) == 6
    assert all(kodlama[r["kart_id"]]["durum"] == "veri_yok" for r in adaylar if r["kart_id"] not in uygun)
