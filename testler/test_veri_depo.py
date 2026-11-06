import pandas as pd
import pytest

from motor.veri.depo import bosluk_raporu, mum_oku, funding_oku, aralik_suresi, funding_yolu


def _df(zamanlar):
    idx = pd.DatetimeIndex(pd.to_datetime(zamanlar, utc=True), name="zaman")
    return pd.DataFrame({"acilis": 1.0}, index=idx)


def test_bosluk_yok():
    assert bosluk_raporu(_df(pd.date_range("2026-01-01", periods=10, freq="5min")), "5m") == []


def test_bosluk_var():
    z = list(pd.date_range("2026-01-01 00:00", periods=3, freq="5min")) + \
        list(pd.date_range("2026-01-01 00:30", periods=2, freq="5min")) + \
        [pd.Timestamp("2026-01-01 00:50")]
    r = bosluk_raporu(_df(z), "5m")
    assert r == [(pd.Timestamp("2026-01-01 00:15", tz="UTC"), pd.Timestamp("2026-01-01 00:25", tz="UTC"), 3),
                 (pd.Timestamp("2026-01-01 00:40", tz="UTC"), pd.Timestamp("2026-01-01 00:45", tz="UTC"), 2)]


def test_bosluk_kisa_df():
    assert bosluk_raporu(_df(["2026-01-01"]), "5m") == []


def test_aralik_suresi():
    assert aralik_suresi("4h") == pd.Timedelta(hours=4) and aralik_suresi("1d") == pd.Timedelta(days=1)
    with pytest.raises(ValueError):
        aralik_suresi("5x")


def test_oku_ve_kesme(tmp_path):
    df = _df(pd.date_range("2026-01-01", periods=6, freq="5min"))
    yol = tmp_path / "S" / "5m.parquet"
    yol.parent.mkdir()
    df.to_parquet(yol)
    assert len(mum_oku("S", "5m", dizin=tmp_path)) == 6
    assert len(mum_oku("S", "5m", "2026-01-01 00:10", "2026-01-01 00:20", dizin=tmp_path)) == 2
    with pytest.raises(FileNotFoundError):
        mum_oku("YOK", "5m", dizin=tmp_path)
    with pytest.raises(FileNotFoundError):
        funding_oku("S", dizin=tmp_path)
