"""BIST (Yahoo) ayrıştırma, bozuk günlük kesme ve tf_mumlari seans mantığı."""
import numpy as np
import pandas as pd

from motor.veri import depo
from motor.veri.yahoo_bist import ayristir, bozuk_oncesini_at
from motor.veri.yeniden_ornekle import tf_mumlari


def _sonuc(zaman, kapanis, hacim=None, splits=None):
    n = len(zaman)
    r = {"timestamp": zaman, "indicators": {"quote": [{"open": kapanis, "high": kapanis, "low": kapanis,
                                                      "close": kapanis, "volume": hacim or [100] * n}]}}
    if splits:
        r["events"] = {"splits": splits}
    return r


def test_ayristir_gunluk_utc_gun_basi_ve_bolunme():
    t = [1_700_000_000 + 86400 * i for i in range(3)]   # 07:00 UTC civarı
    df, bol = ayristir(_sonuc(t, [10.0, 11.0, 12.0], splits={"x": {"date": t[1], "numerator": 2, "denominator": 1}}), "1d")
    assert (df.index == df.index.normalize()).all() and bol[0][1] == 2.0 and len(df) == 3


def test_ayristir_gun_ici_duz_hacimsiz_mumu_atar():
    t = [1_700_000_000, 1_700_003_600]
    df, _ = ayristir(_sonuc(t, [10.0, 10.0], hacim=[0, 50]), "1h")
    assert len(df) == 1 and df["hacim"].iloc[0] == 50


def test_bozuk_oncesini_at():
    idx = pd.date_range("2005-01-01", periods=5, tz="UTC")
    df = pd.DataFrame({"kapanis": [0.001, 0.001, 1.0, 1.1, 1.2]}, index=idx)
    assert len(bozuk_oncesini_at(df)) == 3


def test_tf_mumlari_bist_4h_tsi_hizali(tmp_path):
    # 1 gün: Yahoo :30 saatlik mumlar 06:30..14:30 UTC (09:30..17:30 TSİ)
    idx = pd.DatetimeIndex([pd.Timestamp("2024-03-04", tz="UTC") + pd.Timedelta(hours=6.5 + i) for i in range(9)], name="zaman")
    c = np.arange(1, 10, dtype=float)
    df = pd.DataFrame({"acilis": c, "yuksek": c + 1, "dusuk": c - 1, "kapanis": c, "hacim": 10.0, "quote_hacim": 10.0,
                       "islem_sayisi": np.int64(0)}, index=idx)
    yol = depo.mum_yolu("BIST_TEST", "1h", tmp_path)
    yol.parent.mkdir(parents=True)
    df.to_parquet(yol)
    h4 = tf_mumlari("BIST_TEST", "4h", dizin=tmp_path)
    assert list(h4.index.tz_convert("Europe/Istanbul").strftime("%H:%M")) == ["09:30", "13:30", "17:30"]
    assert tf_mumlari("BIST_TEST", "1h", dizin=tmp_path).index[0] == idx[0]
