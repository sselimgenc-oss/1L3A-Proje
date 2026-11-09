"""Ağ gerektirmeyen testler: ayrıştırma, birleştirme, checksum, artımlı güncelleme."""
import hashlib
import io
import zipfile

import pandas as pd
import pytest

from motor.veri import indir
from motor.veri.indir import (birlestir, funding_csv_ayristir, mum_csv_ayristir, _bos_mum)

BASLIK = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n"
T0 = 1788220800000  # 2026-09-01 00:00 UTC (ms)


def _satir(t, o=1.0):
    return f"{t},{o},{o+1},{o-1},{o+0.5},10,{t+299999},100.5,7,4,40,0\n"


def test_mum_baslikli_ms():
    df = mum_csv_ayristir(BASLIK + _satir(T0) + _satir(T0 + 300000, 2.0))
    assert list(df.columns) == ["acilis", "yuksek", "dusuk", "kapanis", "hacim", "quote_hacim", "islem_sayisi"]
    assert df.index.name == "zaman" and str(df.index.tz) == "UTC"
    assert df.index[0] == pd.Timestamp("2026-09-01", tz="UTC")
    assert df["islem_sayisi"].dtype == "int64" and df["acilis"].dtype == "float64"
    assert len(df) == 2 and df["acilis"].iloc[1] == 2.0


def test_mum_baslıksiz_ms():
    df = mum_csv_ayristir(_satir(T0) + _satir(T0 + 300000))
    assert len(df) == 2 and df.index[0] == pd.Timestamp("2026-09-01", tz="UTC")


def test_mum_mikrosaniye():
    df = mum_csv_ayristir(_satir(T0 * 1000) + _satir((T0 + 300000) * 1000))
    assert df.index[0] == pd.Timestamp("2026-09-01", tz="UTC")
    assert df.index[1] - df.index[0] == pd.Timedelta("5min")


def test_funding_ayristir():
    df = funding_csv_ayristir("calc_time,funding_interval_hours,last_funding_rate\n"
                              f"{T0+5},8,0.00008482\n{T0+28800000},8,0.0001\n")
    assert list(df.columns) == ["oran"] and df["oran"].iloc[0] == pytest.approx(8.482e-5)
    assert df.index.name == "zaman" and len(df) == 2


def test_funding_baslıksiz_us():
    df = funding_csv_ayristir(f"{T0*1000},8,0.0001\n")
    assert df.index[0] == pd.Timestamp("2026-09-01", tz="UTC")


def test_birlestir_tekrar_ve_sira():
    a = mum_csv_ayristir(_satir(T0 + 300000, 2.0) + _satir(T0, 1.0))
    b = mum_csv_ayristir(_satir(T0 + 300000, 9.0) + _satir(T0 + 600000, 3.0))
    df = birlestir([a, b], _bos_mum)
    assert df.index.is_monotonic_increasing and df.index.is_unique and len(df) == 3
    assert df["acilis"].iloc[1] == 9.0  # sonraki parça kazanır
    assert len(birlestir([], _bos_mum)) == 0


def _zip(csv_metni: str) -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("x.csv", csv_metni)
    return b.getvalue()


def test_zip_icinden_csv():
    assert indir.zip_icinden_csv(_zip("abc")) == b"abc"


def test_checksum():
    bayt = b"deneme"
    h = hashlib.sha256(bayt).hexdigest()
    assert indir._checksum_tamam(bayt, f"{h}  dosya.zip\n")
    assert not indir._checksum_tamam(bayt, f"{'0'*64}  dosya.zip\n")


def test_mum_indir_artimli_sahte_ag(tmp_path, monkeypatch):
    """Ağ yerine sahte listeleme/indirme; ikinci çağrı yalnız yeni ayı ekler, tekrar atılır."""
    ay1 = _zip(BASLIK + _satir(T0) + _satir(T0 + 300000))          # 2026-09
    ay2 = _zip(_satir(T0 + 30 * 86400000) + _satir(T0 + 30 * 86400000 + 300000))  # 2026-10 başlıksız
    arsiv = {"2026-09": ay1}
    cagri = []

    def sahte_liste(onek):
        return [f"data/futures/um/monthly/klines/X/5m/X-5m-{a}.zip" for a in arsiv] if "monthly" in onek else []

    def sahte_getir(anahtar, ham=None):
        cagri.append(anahtar)
        return arsiv[anahtar[-11:-4]]

    monkeypatch.setattr(indir, "s3_listele", sahte_liste)
    monkeypatch.setattr(indir, "zip_getir", sahte_getir)
    bitis = "2026-12-01"
    df = indir.mum_indir("X", "5m", bitis=bitis, dizin=tmp_path, sessiz=True)
    assert len(df) == 2
    arsiv["2026-10"] = ay2
    df = indir.mum_indir("X", "5m", bitis=bitis, dizin=tmp_path, sessiz=True)
    assert len(df) == 4 and df.index.is_unique
    from motor.veri.depo import mum_oku
    assert len(mum_oku("X", "5m", dizin=tmp_path)) == 4
    assert len(mum_oku("X", "5m", baslangic="2026-10-01", dizin=tmp_path)) == 2
