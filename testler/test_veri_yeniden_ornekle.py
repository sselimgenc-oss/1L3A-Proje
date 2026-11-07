import numpy as np
import pandas as pd
import pytest

from motor.veri.yeniden_ornekle import yeniden_ornekle


def _mumlar(bas, n, atla=()):
    idx = pd.date_range(bas, periods=n, freq="5min", tz="UTC", name="zaman")
    i = np.arange(n, dtype=float)
    df = pd.DataFrame({"acilis": 100 + i, "yuksek": 110 + i, "dusuk": 90 + i, "kapanis": 101 + i,
                       "hacim": 1.0 + i * 0, "quote_hacim": 2.0 + i * 0, "islem_sayisi": np.full(n, 3, dtype="int64")},
                      index=idx)
    return df.drop(df.index[list(atla)]) if atla else df


def test_1h_dogruluk():
    df = _mumlar("2026-01-01 00:00", 24)  # 2 saat
    r = yeniden_ornekle(df, "1h")
    assert len(r) == 2 and not r["eksik"].any()
    h = r.iloc[0]
    assert h["acilis"] == 100 and h["kapanis"] == 101 + 11
    assert h["yuksek"] == 110 + 11 and h["dusuk"] == 90
    assert h["hacim"] == 12 and h["quote_hacim"] == 24 and h["islem_sayisi"] == 36
    assert r["islem_sayisi"].dtype == "int64"
    assert r.index[1] == pd.Timestamp("2026-01-01 01:00", tz="UTC")


def test_hizalama_ve_kismi_ilk_son():
    df = _mumlar("2026-01-01 00:35", 20)  # 00:35 .. 02:10 -> baş ve son kısmi
    r = yeniden_ornekle(df, "1h")
    assert list(r.index.hour) == [0, 1, 2]
    assert list(r["eksik"]) == [True, False, True]


def test_eksik_mum_isaretleme_ve_atma():
    df = _mumlar("2026-01-01 00:00", 24, atla=[3])
    r = yeniden_ornekle(df, "1h")
    assert list(r["eksik"]) == [True, False]
    assert r.iloc[0]["hacim"] == 11
    a = yeniden_ornekle(df, "1h", eksikleri_at=True)
    assert len(a) == 1 and "eksik" not in a.columns


def test_4h_ve_1d():
    df = _mumlar("2026-01-01 00:00", 288 * 2)
    assert len(yeniden_ornekle(df, "4h")) == 12
    g = yeniden_ornekle(df, "1d")
    assert len(g) == 2 and not g["eksik"].any() and g.iloc[0]["hacim"] == 288


def test_15m():
    r = yeniden_ornekle(_mumlar("2026-01-01 00:00", 6), "15m")
    assert len(r) == 2 and r.iloc[0]["hacim"] == 3


def test_gecersiz():
    with pytest.raises(ValueError):
        yeniden_ornekle(_mumlar("2026-01-01", 6), "1m")


# ------------------------------------------------------------------ seanslı piyasalar (hisse / emtia)
def _hisse_5m(gunler, acilis_utc="13:30", kapanis_utc="20:00"):
    parcalar = []
    for g in gunler:
        idx = pd.date_range(f"{g} {acilis_utc}", f"{g} {kapanis_utc}", freq="5min", tz="UTC", inclusive="left")
        parcalar.append(pd.DataFrame({"acilis": 100.0, "yuksek": 101.0, "dusuk": 99.0, "kapanis": 100.5, "hacim": 1.0,
                                      "quote_hacim": 100.0, "islem_sayisi": 0}, index=idx))
    df = pd.concat(parcalar)
    df.index.name = "zaman"
    return df


def _sembol_dizini(tmp_path, ad, df, aralik):
    d = tmp_path / ad
    d.mkdir(parents=True)
    df.to_parquet(d / f"{aralik}.parquet")
    return tmp_path


def test_hisse_1d_4h_1h_kismi_seans_tutulur(tmp_path):
    from motor.veri.yeniden_ornekle import tf_mumlari
    # yaz (EDT): 13:30-20:00 UTC; kış (EST): 14:30-21:00 UTC
    df = pd.concat([_hisse_5m(["2024-07-01", "2024-07-02"]), _hisse_5m(["2024-12-02", "2024-12-03"], "14:30", "21:00")])
    dizin = _sembol_dizini(tmp_path, "DK_AAPL", df, "5m")
    g1 = tf_mumlari("DK_AAPL", "1d", dizin=dizin)
    assert len(g1) == 4 and (g1.index == g1.index.floor("D")).all()
    h4 = tf_mumlari("DK_AAPL", "4h", dizin=dizin)
    assert len(h4) == 8                                    # günde 2 (09-13 ve 13-17 NY)
    assert sorted(set(h4.index[:4].strftime("%H:%M"))) == ["13:00", "17:00"]       # yaz: NY 09:00 = 13:00 UTC
    assert sorted(set(h4.index[4:].strftime("%H:%M"))) == ["14:00", "18:00"]       # kış: NY 09:00 = 14:00 UTC
    h1 = tf_mumlari("DK_AAPL", "1h", dizin=dizin)
    assert h1.index[0] == pd.Timestamp("2024-07-01 13:00", tz="UTC")               # yarım saatlik ilk mum tutulur
    assert len(h1) == 4 * 7


def test_hisse_1h_kaynagindan_1d_4h(tmp_path):
    from motor.veri.yeniden_ornekle import tf_mumlari
    h5 = _hisse_5m(["2024-07-01", "2024-07-02"])
    h1 = yeniden_ornekle(h5, "1h", "5m")
    h1 = h1.drop(columns="eksik")
    dizin = _sembol_dizini(tmp_path, "DK_MSFT", h1, "1h")
    assert len(tf_mumlari("DK_MSFT", "1d", dizin=dizin)) == 2
    h4 = tf_mumlari("DK_MSFT", "4h", dizin=dizin)
    assert len(h4) == 4 and set(h4.index.strftime("%H:%M")) == {"13:00", "17:00"}


def test_emtia_gunluk_ara_1d_4h_bos_degil(tmp_path):
    from motor.veri.yeniden_ornekle import tf_mumlari
    parcalar = []
    for g in ["2024-07-02", "2024-07-03", "2024-07-04"]:       # 22:00-23:00 UTC günlük ara yok
        idx = pd.date_range(f"{g} 00:00", f"{g} 22:00", freq="5min", tz="UTC", inclusive="left")
        parcalar.append(pd.DataFrame({"acilis": 1.0, "yuksek": 2.0, "dusuk": 0.5, "kapanis": 1.5, "hacim": 1.0,
                                      "quote_hacim": 1.0, "islem_sayisi": 0}, index=idx))
    df = pd.concat(parcalar); df.index.name = "zaman"
    dizin = _sembol_dizini(tmp_path, "DK_XAU", df, "5m")
    assert len(tf_mumlari("DK_XAU", "1d", dizin=dizin)) == 3
    assert len(tf_mumlari("DK_XAU", "4h", dizin=dizin)) == 18      # günde 6 kova (20-24 kısmi tutulur)


def test_kripto_davranisi_ayni_kalir(tmp_path):
    from motor.veri.yeniden_ornekle import tf_mumlari
    idx = pd.date_range("2024-01-01", periods=288 * 2 - 3, freq="5min", tz="UTC", name="zaman")   # son gün eksik
    df = pd.DataFrame({"acilis": 1.0, "yuksek": 2.0, "dusuk": 0.5, "kapanis": 1.5, "hacim": 1.0,
                       "quote_hacim": 1.0, "islem_sayisi": 1}, index=idx)
    dizin = _sembol_dizini(tmp_path, "BTCUSDT", df, "5m")
    assert len(tf_mumlari("BTCUSDT", "1d", dizin=dizin)) == 1       # eksik gün atılır (eski kural)
    esk = yeniden_ornekle(df, "4h", "5m", eksikleri_at=True)
    assert tf_mumlari("BTCUSDT", "4h", dizin=dizin).equals(esk)
