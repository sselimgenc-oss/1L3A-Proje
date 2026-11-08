"""spot_vekil: perp başına spot ekleme, işaret dosyası, idempotans (ağ yok)."""
import io
import json
import zipfile

import pandas as pd

from motor.veri import spot_vekil
from motor.veri.depo import mum_yolu


def _df(bas, n, fiyat):
    idx = pd.date_range(bas, periods=n, freq="5min", tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": fiyat, "yuksek": fiyat + 1, "dusuk": fiyat - 1, "kapanis": fiyat,
                         "hacim": 1.0, "quote_hacim": 1.0, "islem_sayisi": 1}, index=idx).astype({"islem_sayisi": "int64"})


def test_spot_ekle_ve_idempotent(tmp_path, monkeypatch):
    perp = _df("2020-01-01", 300, 100.0)
    yol = mum_yolu("XUSDT", "5m", tmp_path)
    yol.parent.mkdir(parents=True)
    perp.to_parquet(yol)
    spot = _df("2019-12-30", 600, 99.0)   # perp ile çakışan kısım da var

    monkeypatch.setattr(spot_vekil, "spot_mumlari",
                        lambda s, bitis, bas=None, dizin=None, sessiz=False: spot[spot.index < bitis])
    r = spot_vekil.spot_vekil_ekle("XUSDT", dizin=tmp_path, sessiz=True)
    d = pd.read_parquet(yol)
    assert d.index.is_unique and d.index.is_monotonic_increasing
    assert d.index[0] == pd.Timestamp("2019-12-30", tz="UTC")
    assert (d.loc[d.index >= "2020-01-01", "kapanis"] == 100.0).all()   # perp bozulmadı
    assert r["spot_vekil_bitis"].startswith("2019-12-31 23:55")
    assert abs(r["birlesim_fark_yuzde"] - (100 / 99 - 1) * 100) < 1e-3
    assert json.loads(spot_vekil.kaynak_yolu("XUSDT", tmp_path).read_text())["perp_baslangic"].startswith("2020-01-01")
    n = len(d)
    spot_vekil.spot_vekil_ekle("XUSDT", dizin=tmp_path, sessiz=True)   # ikinci çalıştırma aynı sonuç
    assert len(pd.read_parquet(yol)) == n


def test_spot_yoksa_dokunmaz(tmp_path, monkeypatch):
    perp = _df("2025-05-30", 50, 10.0)
    yol = mum_yolu("HYPEUSDT", "5m", tmp_path)
    yol.parent.mkdir(parents=True)
    perp.to_parquet(yol)
    monkeypatch.setattr(spot_vekil, "spot_mumlari", lambda *a, **k: perp.iloc[0:0])
    r = spot_vekil.spot_vekil_ekle("HYPEUSDT", dizin=tmp_path, sessiz=True)
    assert r["spot_mum_sayisi"] == 0
    assert len(pd.read_parquet(yol)) == 50


def test_hizasiz_spot_mumlari_atilir(tmp_path, monkeypatch):
    import motor.veri.indir as ind
    ham = _df("2018-02-09 09:30", 6, 5.0)
    kayik = _df("2018-02-09 09:58:14.789", 3, 5.0)
    csv = pd.concat([ham, kayik]).sort_index()
    monkeypatch.setattr(spot_vekil, "s3_listele", lambda onek: ["data/spot/monthly/klines/XUSDT/5m/XUSDT-5m-2018-02.zip"])
    monkeypatch.setattr(spot_vekil, "_spot_zip_getir", lambda k, h: b"")
    monkeypatch.setattr(spot_vekil, "zip_icinden_csv", lambda b: b"")
    monkeypatch.setattr(spot_vekil, "mum_csv_ayristir", lambda b: csv)
    out = spot_vekil.spot_mumlari("XUSDT", pd.Timestamp("2018-03-01", tz="UTC"), dizin=tmp_path, sessiz=True)
    assert len(out) == 6 and (out.index.minute % 5 == 0).all() and (out.index.second == 0).all()
