"""Kapanış tek grafik hattının sentetik mumla uçtan uca denetimi."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.arastirma.kapanis.tek_grafik import kendi_hesabi_oynat, tek_ham_kos
from motor.arastirma.v2.ham import HoldoutSizintisi
from motor.strateji import kayit


TABLO = Path(__file__).resolve().parents[1] / "sonuclar/evren/v2/maliyet_tablosu_v2.csv"


def _mumlar() -> pd.DataFrame:
    n = 600
    i = np.arange(n)
    fiyat = 100 + 8 * np.sin(i / 15) + i * 0.02
    idx = pd.date_range("2022-01-01", periods=n, freq="1d", tz="UTC")
    return pd.DataFrame(
        {"acilis": fiyat, "yuksek": fiyat + 1, "dusuk": fiyat - 1,
         "kapanis": fiyat, "hacim": np.full(n, 1000.0),
         "quote_hacim": np.full(n, 100000.0)},
        index=idx,
    )


def test_tek_ham_ve_kendi_hesabi_sentetik() -> None:
    mumlar = _mumlar()
    veri = lambda sembol, tf: (mumlar, None)
    ad = "v3__momentum-sifir-kesisim"
    ham1, _, _ = tek_ham_kos(kayit.al(ad)(), "BTCUSDT", "1d", 1.0, TABLO, veri)
    ham2, mtm2, _ = tek_ham_kos(kayit.al(ad)(), "BTCUSDT", "1d", 2.0, TABLO, veri)
    assert len(ham1) == len(ham2) > 0
    assert ham2["r"].sum() < ham1["r"].sum()
    assert not mtm2.empty
    metrik, tablo = kendi_hesabi_oynat(
        {"BTCUSDT": ham2}, ("BTCUSDT",), mumlar.index[0], mumlar.index[-1], 2.0, TABLO
    )
    assert metrik["islem_sayisi"] > 0
    assert metrik["kill_olayi"] == 0
    assert set(metrik["r_enstruman"]) == {"BTCUSDT"}
    assert set(metrik["r_yil"]) == {2022, 2023}
    assert len(tablo) == len(ham2)


def test_holdout_verisi_sessizce_okunmaz() -> None:
    mumlar = _mumlar()
    mumlar.index = pd.date_range("2025-11-08", periods=len(mumlar), freq="1d", tz="UTC")
    with pytest.raises(HoldoutSizintisi):
        tek_ham_kos(kayit.al("v3__momentum-sifir-kesisim")(), "BTCUSDT", "1d", 2.0,
                    TABLO, lambda sembol, tf: (mumlar, None))


def test_mum_yoksa_acik_hata() -> None:
    bos = _mumlar().iloc[:0]
    with pytest.raises(FileNotFoundError, match="mum yok"):
        tek_ham_kos(kayit.al("v3__momentum-sifir-kesisim")(), "BTCUSDT", "1d", 2.0,
                    TABLO, lambda sembol, tf: (bos, None))
