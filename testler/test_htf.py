"""Üst zaman dilimi hizalama: lookahead ve sınır testleri."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji.htf import ust_zaman
from testler.test_bt_strateji import rastgele_mumlar


def _kapanis_ve_ma(ust):
    return pd.DataFrame({"kap": ust["kapanis"], "ma3": ust["kapanis"].rolling(3).mean()})


def mumlar_1h(gun=20, bas="2024-01-01"):          # 2024-01-01 Pazartesi
    n = 24 * gun
    idx = pd.date_range(bas, periods=n, freq="1h", tz="UTC", name="zaman")
    kap = np.arange(n, dtype=float) + 100
    return pd.DataFrame({"acilis": kap, "yuksek": kap + 1, "dusuk": kap - 1, "kapanis": kap, "hacim": 1.0}, index=idx)


def test_gunluk_hizalama_siniri():
    df = mumlar_1h(5)
    s = ust_zaman(df, "1d", lambda u: u["kapanis"])
    # 1 Ocak mumunun kapanışı = 123 (saat 23:00); 2 Ocak 00:00'dan önce NaN, sonra 123
    assert s.loc["2024-01-01 23:00"] != s.loc["2024-01-01 23:00"]          # NaN
    assert s.loc["2024-01-02 00:00"] == 123.0 and s.loc["2024-01-02 23:00"] == 123.0
    assert s.loc["2024-01-03 00:00"] == 147.0
    assert s.index.equals(df.index)


def test_4h_hizalama_siniri():
    df = mumlar_1h(2)
    s = ust_zaman(df, "4h", lambda u: u["kapanis"])
    assert s.loc["2024-01-01 03:00"] != s.loc["2024-01-01 03:00"]
    assert s.loc["2024-01-01 04:00"] == 103.0          # 00-04 mumunun kapanışı (03:00 saatlik kapanış)
    assert s.loc["2024-01-01 07:00"] == 103.0 and s.loc["2024-01-01 08:00"] == 107.0


def test_haftalik_pazartesi_hizasi():
    df = mumlar_1h(21)       # 3 hafta, Pzt 00:00'dan
    s = ust_zaman(df, "1w", lambda u: u["kapanis"])
    # 1. hafta kapanışı: 7*24-1 -> 267 ; 8 Ocak (Pzt) 00:00'dan itibaren geçerli
    assert s.loc["2024-01-07 23:00"] != s.loc["2024-01-07 23:00"]
    assert s.loc["2024-01-08 00:00"] == 267.0 and s.loc["2024-01-14 23:00"] == 267.0
    assert s.loc["2024-01-15 00:00"] == 435.0
    # Pazartesi dışı başlayan veri: ilk (kısmi) hafta atılır
    df2 = mumlar_1h(15, bas="2024-01-03")           # Çarşamba
    s2 = ust_zaman(df2, "1w", lambda u: u["kapanis"])
    assert s2.loc["2024-01-08 00:00":"2024-01-14 23:00"].isna().all()    # ilk hafta kısmi -> yok
    assert s2.loc["2024-01-15 00:00"] == s2.loc["2024-01-15 00:00"]       # 8-14 Ocak tam hafta
    assert s2.loc["2024-01-15 00:00"] == 100 + (np.datetime64("2024-01-14T23:00") - np.datetime64("2024-01-03T00:00")) / np.timedelta64(1, "h")


def test_kismi_ust_mum_kullanilmaz_ve_bosluk():
    df = mumlar_1h(4)
    df = df.drop(df.index[30:33])                    # 2 Ocak'ta 3 saatlik boşluk -> o günlük mum eksik
    s = ust_zaman(df, "1d", lambda u: u["kapanis"])
    assert s.loc["2024-01-03 00:00"] == 123.0      # 2 Ocak mumu atıldı: 1 Ocak değeri kalır
    assert s.loc["2024-01-04 00:00"] == 100 + 71                          # 3 Ocak tam


def test_lookahead_yok_alt_tf_kesme():
    df = rastgele_mumlar(n=24 * 40, seed=11)
    for aralik in ("4h", "1d", "1w"):
        tam = ust_zaman(df, aralik, _kapanis_ve_ma)
        for n in (100, 257, 500, 700):
            pdt.assert_frame_equal(ust_zaman(df.iloc[:n], aralik, _kapanis_ve_ma), tam.iloc[:n])


def test_gecersiz_aralik():
    df = mumlar_1h(3)
    with pytest.raises(ValueError):
        ust_zaman(df, "1h", lambda u: u["kapanis"])
    with pytest.raises(ValueError):
        ust_zaman(df, "5m", lambda u: u["kapanis"])


def test_seansli_piyasa_ust_mumlari_atilmaz():
    """Hisse gibi seanslı veride (günde 7 saat, hafta içi) günlük/haftalık mumlar 'eksik' sayılıp atılmamalı."""
    idx = pd.date_range("2024-01-01", "2024-03-01", freq="1h", tz="UTC")
    idx = idx[(idx.dayofweek < 5) & (idx.hour >= 14) & (idx.hour < 21)]
    x = np.arange(len(idx), dtype=float) + 100
    df = pd.DataFrame({"acilis": x, "yuksek": x, "dusuk": x, "kapanis": x, "hacim": 1.0}, index=idx)
    g = ust_zaman(df, "1d", lambda u: u["kapanis"])
    assert g.notna().mean() > 0.95
    assert g.loc["2024-01-02 14:00"] == 106.0           # 1 Ocak'ın son (20:00) mumu, ertesi gün kullanılır
    h = ust_zaman(df, "1w", lambda u: u["kapanis"])
    assert h.notna().mean() > 0.85
    assert h.loc["2024-01-08 14:00"] == 100 + 5 * 7 - 1  # 1. haftanın son mumu
