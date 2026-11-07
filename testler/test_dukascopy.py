"""Dukascopy modülü testleri (ağsız: sahte istemci)."""
import json
import lzma
import struct
from datetime import date

import pandas as pd
import pytest

from motor.veri import dukascopy as dk
from motor.veri.depo import MUM_SUTUNLARI, mum_oku


def _bi5(kayitlar):
    return lzma.compress(b"".join(struct.pack(">5If", *k) for k in kayitlar))


class SahteIstemci:
    """yol -> bayt | None (404) | 'hata' (AgHatasi). Çağrıları sayar."""

    def __init__(self, yanitlar):
        self.yanitlar, self.cagrilar = yanitlar, []

    def getir(self, yol):
        self.cagrilar.append(yol)
        y = self.yanitlar.get(yol, None)
        if y == "hata":
            raise dk.AgHatasi(yol)
        return y


GUN = pd.Timestamp("2024-01-02", tz="UTC")


def test_bi5_coz_sirasi_ve_olcek():
    # kayıt: ofset, açılış, KAPANIŞ, düşük, yüksek, hacim ; fiyat = değer/1000
    b = _bi5([(0, 100000, 100500, 99900, 100600, 2.5), (60, 100500, 100500, 100500, 100500, 0.0),
              (120, 100500, 100100, 100000, 100700, 1.0)])
    df = dk.bi5_coz(b, GUN, 1000)
    assert len(df) == 2  # hacimsiz dolgu mumu atıldı
    r = df.iloc[0]
    assert (r.acilis, r.kapanis, r.dusuk, r.yuksek) == (100.0, 100.5, 99.9, 100.6)
    assert df.index[0] == GUN and df.index[1] == GUN + pd.Timedelta(minutes=2)
    assert df.index.tz is not None
    assert len(dk.bi5_coz(b, GUN, 1000, hacimsiz_at=False)) == 3


def test_bi5_bos_ve_bozuk():
    assert dk.bi5_coz(b"", GUN, 1000).empty
    assert dk.bi5_coz(lzma.compress(b""), GUN, 1000).empty
    with pytest.raises(ValueError):
        dk.bi5_coz(lzma.compress(b"x" * 25), GUN, 1000)


def test_bir_dakikadan_5m():
    # dakika 0,1,2 ve 7 (3-4 eksik, 5-6 eksik): iki 5m mum, eksikler doldurulmaz
    m1 = dk.bi5_coz(_bi5([(0, 10000, 10100, 9900, 10200, 1.0), (60, 10100, 10300, 10050, 10400, 2.0),
                          (120, 10300, 10200, 10100, 10350, 3.0), (420, 10200, 10250, 10150, 10260, 4.0)]), GUN, 1000)
    m5 = dk.bir_dakikadan_5m(m1)
    assert list(m5.columns) == MUM_SUTUNLARI and len(m5) == 2
    a = m5.iloc[0]
    assert (a.acilis, a.yuksek, a.dusuk, a.kapanis, a.hacim) == (10.0, 10.4, 9.9, 10.2, 6.0)
    assert a.quote_hacim == pytest.approx(6.0 * 10.2) and a.islem_sayisi == 0
    assert m5.index[1] == GUN + pd.Timedelta(minutes=5)
    assert m5["islem_sayisi"].dtype == "int64"


def test_bolunme_duzeltme():
    idx = pd.DatetimeIndex(["2024-06-07 15:00", "2024-06-10 15:00"], tz="UTC", name="zaman")
    df = pd.DataFrame({"acilis": [1200.0, 120.0], "yuksek": [1210.0, 121.0], "dusuk": [1190.0, 119.0],
                       "kapanis": [1200.0, 120.0], "hacim": [10.0, 100.0], "quote_hacim": [12000.0, 12000.0],
                       "islem_sayisi": [0, 0]}, index=idx)
    d = dk.bolunme_duzelt(df, [("2024-06-10", 10.0)])
    assert d["kapanis"].tolist() == [120.0, 120.0] and d["hacim"].tolist() == [100.0, 100.0]
    assert d["quote_hacim"].tolist() == [12000.0, 12000.0]
    assert df["kapanis"].iloc[0] == 1200.0  # girdi değişmez


def test_onbellek_devam_ve_404_isareti(tmp_path):
    ham = tmp_path / "ham"
    g1, g2 = date(2024, 1, 2), date(2024, 1, 3)
    y1 = "X/2024/00/02/BID_candles_min_1.bi5"
    y2 = "X/2024/00/03/BID_candles_min_1.bi5"
    ist = SahteIstemci({y1: _bi5([(0, 1000, 1000, 1000, 1000, 1.0)]), y2: None})
    yeni, yok, bas = dk.gunleri_indir(ist, ham, "X", [g1, g2], es_zamanli=1)
    assert (yeni, yok, bas) == (1, 1, [])
    assert (ham / "X/2024/00/02/BID_candles_min_1.bi5").exists()
    assert (ham / "X/2024/00/03/BID_candles_min_1.bi5.yok").exists()
    # ikinci çalıştırma: hiç istek yok (devam + 404 tekrar istenmez)
    n = len(ist.cagrilar)
    assert dk.gunleri_indir(ist, ham, "X", [g1, g2], es_zamanli=1) == (0, 0, [])
    assert len(ist.cagrilar) == n


def test_kalici_basarisiz_listelenir_ve_onbellege_yazilmaz(tmp_path):
    ham = tmp_path / "ham"
    g = date(2024, 1, 2)
    ist = SahteIstemci({"X/2024/00/02/BID_candles_min_1.bi5": "hata"})
    yeni, yok, bas = dk.gunleri_indir(ist, ham, "X", [g], es_zamanli=1)
    assert bas == [g] and (yeni, yok) == (0, 0)
    assert not list((ham / "X").rglob("*")) or not any(p.is_file() for p in (ham / "X").rglob("*"))
    # sonraki çalıştırmada yeniden denenir
    ist.yanitlar["X/2024/00/02/BID_candles_min_1.bi5"] = _bi5([(0, 1000, 1000, 1000, 1000, 1.0)])
    assert dk.gunleri_indir(ist, ham, "X", [g], es_zamanli=1)[0] == 1


def test_istemci_geri_cekilme(monkeypatch):
    sonuclar = iter([503, 503, 200])

    class R:
        def __init__(self, k):
            self.status_code, self.content = k, b"abc"

    class S:
        headers = {}

        def get(self, url, timeout):
            return R(next(sonuclar))

    ist = dk.Istemci(bekleme=0, taban_bekleme=0, deneme=5)
    monkeypatch.setattr(ist, "_oturum", lambda: S())
    assert ist.getir("a") == b"abc"
    sonuclar2 = iter([503] * 3)
    monkeypatch.setattr(S, "get", lambda self, url, timeout: R(next(sonuclar2)))
    ist2 = dk.Istemci(bekleme=0, taban_bekleme=0, deneme=3)
    monkeypatch.setattr(ist2, "_oturum", lambda: S())
    with pytest.raises(dk.AgHatasi):
        ist2.getir("a")


def test_sembol_indir_uctan_uca(tmp_path, monkeypatch):
    """Yıllık günlük dosya -> işlem günleri -> dakika dosyası -> 5m parquet (+ bölünme düzeltmesi)."""
    # yıllık: ofset 86400 (2 Ocak) hacimli, 0 (1 Ocak) hacimsiz
    yillik = _bi5([(0, 1000, 1000, 1000, 1000, 0.0), (86400, 1200000, 1200000, 1200000, 1200000, 5.0)])
    dakika = _bi5([(0, 1200000, 1200000, 1190000, 1210000, 2.0), (60, 1200000, 1200000, 1200000, 1200000, 3.0)])
    ist = SahteIstemci({"AAPLUSUSD/2024/BID_candles_day_1.bi5": yillik,
                        "AAPLUSUSD/2024/00/02/BID_candles_min_1.bi5": dakika})
    bf = tmp_path / "bol.json"
    bf.write_text(json.dumps({"DK_AAPL": [["2024-06-10", 10.0]]}))
    r = dk.sembol_indir("DK_AAPL", None, "2024-02-01", dizin=tmp_path, istemci=ist, es_zamanli=1,
                        log=lambda m: None, bolunme_dosyasi=bf)
    assert r["mum_sayisi"] == 1 and r["basarisiz"] == []
    df = mum_oku("DK_AAPL", "5m", dizin=tmp_path)
    assert df.index[0] == pd.Timestamp("2024-01-02", tz="UTC")
    assert df["kapanis"].iloc[0] == pytest.approx(120.0)  # 1200 / 10 (bölünme öncesi)
    assert df["hacim"].iloc[0] == pytest.approx(50.0)


def test_varsayilan_bolunme_tablosu():
    assert ("2024-06-10", 10.0) in dk.bolunmeler_oku("DK_NVDA")
    assert dk.bolunmeler_oku("DK_XAU") == []
