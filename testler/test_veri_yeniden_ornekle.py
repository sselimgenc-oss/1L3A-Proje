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
