"""Birleşik hesap oynatması (araclar/canli_birlesik_oynatma.py): sentetik doğrulama (gerçek veri okunmaz)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "araclar"))
import canli_birlesik_oynatma as b  # noqa: E402


def test_toplam_min_ozsermaye_tahsis():
    eg = {"a": [250, 260, 200], "c": [60, 50, 70]}
    r = b.birlestir(eg, {"a": 250.0, "c": 60.0})
    assert list(r["K"]) == [310, 300, 260]
    assert list(r["H"]) == [310, 310, 270]
    assert r["toplam"] == 310 and r["kill_idx"] == -1


def test_kill_sonrasi_durus():
    # toplam 100 -> K 80'e düşünce (>= %20) kill; sonrası donuk (sonraki toparlanma yok sayılır)
    r = b.birlestir({"a": [100, 90, 79, 150, 200]}, {"a": 100.0})
    assert r["kill_idx"] == 2
    assert list(r["K"]) == [100, 90, 79, 79, 79] and list(r["H"]) == [100, 90, 79, 79, 79]
    o = b.olcu(r)
    assert o["kill"] and o["net"] == pytest.approx(-0.21) and o["dd_k"] == pytest.approx(0.21)


def test_kill_tam_esikte_ve_alti():
    assert b.birlestir({"a": [100, 80.0]}, {"a": 100.0})["kill_idx"] == 1
    assert b.birlestir({"a": [100, 80.1]}, {"a": 100.0})["kill_idx"] == -1


def test_kar_K_yi_buyutmez_H_yi_buyutur():
    r = b.birlestir({"a": [100, 150], "c": [100, 90]}, {"a": 100.0, "c": 100.0})
    assert list(r["K"]) == [200, 190] and list(r["H"]) == [200, 240]
    o = b.olcu(r)
    assert o["net"] == pytest.approx(0.2) and o["dd_k"] == pytest.approx(0.05) and o["dd_h"] == 0


def test_eslik_oranlari():
    rows = [dict(net=0.0, dd_k=0.09, dd_h=0.09, kill=False), dict(net=0.12, dd_k=0.10, dd_h=0.05, kill=False),
            dict(net=-0.2, dd_k=0.15, dd_h=0.2, kill=False), dict(net=-0.25, dd_k=0.2, dd_h=0.2, kill=True)]
    o = b.oranlar(rows)
    assert o["n"] == 4
    assert o["fren10_k"] == 0.75           # 0.10, 0.15, 0.20
    assert o["asma15_k"] == 0.25           # yalnız 0.20 (0.15 aşma değil)
    assert o["kill20"] == 0.25
    assert (o["yatay"], o["ust"], o["alt"]) == (0.25, 0.25, 0.5)
    assert o["en_kotu_net"] == -0.25


def test_tarih_siniri():
    t = pd.Timestamp
    ok = pd.DataFrame({"giris_zamani": [t("2025-11-07", tz="UTC")], "cikis_zamani": [t("2025-11-08", tz="UTC")]})
    b.holdout_kontrol(ok, pd.DataFrame({"gun": [t("2025-11-08", tz="UTC")]}))
    kotu = pd.DataFrame({"giris_zamani": [t("2025-11-08", tz="UTC")], "cikis_zamani": [t("2025-11-09", tz="UTC")]})
    with pytest.raises(RuntimeError):
        b.holdout_kontrol(kotu, pd.DataFrame({"gun": []}))
    with pytest.raises(RuntimeError):
        b.holdout_kontrol(ok, pd.DataFrame({"gun": [t("2025-11-09", tz="UTC")]}))
    with pytest.raises(RuntimeError):
        b.pencere_kontrol(t("2025-06-01", tz="UTC"), t("2025-11-08", tz="UTC"))
    for _, _, bas, bit in b.pencereler():
        assert bit < b.HOLDOUT_BAS


def test_pencere_sayilari():
    p = b.pencereler()
    y = [x for x in p if x[1] == "Y12"]
    assert [x[0] for x in y] == [f"Y{i}" for i in range(2018, 2025)]
    assert all((x[3] - x[2]).days in (364, 365) for x in y)
    assert sum(1 for x in p if x[1] == "R6") == 89


def test_denetim_kodu_ana_yolla_uyumlu():
    rng = np.random.default_rng(1)
    eg = [list(250 * np.cumprod(1 + rng.normal(0, 0.02, 200))) for _ in range(3)]
    t = [250.0, 250.0, 60.0]
    a = b.olcu(b.birlestir({str(i): e for i, e in enumerate(eg)}, {str(i): t[i] for i in range(3)}))
    d = b.denetim_yeniden(eg, t)
    for k in ("net", "dd_k", "dd_h", "son_k", "son_h"):
        assert a[k] == pytest.approx(d[k], abs=1e-9)
    assert a["kill"] == d["kill"]


def test_korelasyon_ayni_ve_ters():
    e1 = [100, 101, 99, 103]
    r = b.korelasyon({"a": e1, "c": [200 - x for x in e1]}, {"a": 100.0, "c": 100.0})
    assert r["a|c"]["tum_gunler"] == pytest.approx(-1.0)


def test_uzunluk_uyusmazligi():
    with pytest.raises(ValueError):
        b.birlestir({"a": [1, 2], "c": [1]}, {"a": 1.0, "c": 1.0})
