"""Kayıtlı bütün stratejilerde geçmiş çıktılarının geleceğe bağlı olmadığını denetler.

Her stratejinin tam seri çıktısı, aynı serinin iki farklı noktada kesilmiş çıktısıyla
karşılaştırılır. Veri hem 7/24 hem de hafta sonu/gece boşluklu seanslı olarak üretilir.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.strateji import kayit


TOHUMLAR = (17, 43)
KESIMLER = (0.45, 0.75)


def _indeks(mod: str, n: int) -> pd.DatetimeIndex:
    if mod == "24_7":
        return pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC", name="zaman")

    gunler = pd.date_range("2024-01-02", periods=(n // 78) + 2, freq="B", tz="UTC")
    parcalar = [
        pd.date_range(gun + pd.Timedelta(hours=9, minutes=30), periods=78, freq="5min", tz="UTC")
        for gun in gunler
    ]
    return pd.DatetimeIndex(np.concatenate(parcalar)[:n], name="zaman")


def _mumlar(n: int, tohum: int, mod: str) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    idx = _indeks(mod, n)
    getiri = rng.normal(0.0, 0.0025, len(idx))
    kapanis = 100.0 * np.exp(np.cumsum(getiri))
    acilis = np.r_[kapanis[0], kapanis[:-1]] * (1.0 + rng.normal(0.0, 0.0008, len(idx)))
    yuksek = np.maximum(acilis, kapanis) * (1.0 + rng.uniform(0.0001, 0.004, len(idx)))
    dusuk = np.minimum(acilis, kapanis) * (1.0 - rng.uniform(0.0001, 0.004, len(idx)))
    return pd.DataFrame(
        {
            "acilis": acilis,
            "yuksek": yuksek,
            "dusuk": dusuk,
            "kapanis": kapanis,
            "hacim": rng.lognormal(np.log(1_000.0), 0.25, len(idx)),
            # Funding isteyen kayıtlı kripto stratejileri için nedensel sentetik girdi.
            "funding_orani": rng.normal(0.0, 0.0001, len(idx)),
        },
        index=idx,
    )


@lru_cache(maxsize=None)
def _tek_veri(tohum: int, mod: str) -> pd.DataFrame:
    return _mumlar(2_400, tohum, mod)


def _portfoy_sembolleri() -> tuple[str, ...]:
    """Kayıtlı portföy varsayılanlarında geçen piyasa sembollerini toplar."""
    bulunan: set[str] = set()
    for sinif in tum_portfoy_stratejileri().values():
        for anahtar, deger in sinif.varsayilan_parametreler.items():
            if "sembol" not in anahtar and anahtar != "ciftler":
                continue
            yigin = [deger]
            while yigin:
                parca = yigin.pop()
                if isinstance(parca, str):
                    bulunan.add(parca)
                elif isinstance(parca, (tuple, list)):
                    yigin.extend(parca)
    return tuple(sorted(bulunan | {"BTCUSDT", "ETHUSDT", "SOLUSDT", "DK_AAPL", "DK_MSFT", "DK_XAU"}))


@lru_cache(maxsize=None)
def _portfoy_veri(tohum: int, mod: str) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(tohum)
    semboller = _portfoy_sembolleri()
    n = 420
    if mod == "24_7":
        ortak_indeks = pd.date_range("2021-01-01", periods=n, freq="D", tz="UTC", name="zaman")
    else:
        ortak_indeks = pd.date_range("2021-01-01", periods=n, freq="B", tz="UTC", name="zaman")

    ortak = np.cumsum(rng.normal(0.0002, 0.01, n))
    sonuc: dict[str, pd.DataFrame] = {}
    for sembol in semboller:
        fiyat = 100.0 * np.exp(0.65 * ortak + np.cumsum(rng.normal(0.0001, 0.012, n)))
        acilis = np.r_[fiyat[0], fiyat[:-1]] * (1.0 + rng.normal(0.0, 0.002, n))
        sonuc[sembol] = pd.DataFrame(
            {
                "acilis": acilis,
                "yuksek": np.maximum(acilis, fiyat) * (1.0 + rng.uniform(0.0002, 0.008, n)),
                "dusuk": np.minimum(acilis, fiyat) * (1.0 - rng.uniform(0.0002, 0.008, n)),
                "kapanis": fiyat,
                "hacim": rng.lognormal(np.log(1_000.0), 0.25, n),
            },
            index=ortak_indeks,
        )
    return sonuc


def _kes(veri, kesim: float):
    """Her sembolü aynı ortak zamana kadar kes; seans boşlukları korunur."""
    bitis = next(iter(veri.values())).index[int(len(next(iter(veri.values()))) * kesim)]
    return {sembol: df.loc[df.index <= bitis].copy() for sembol, df in veri.items()}, bitis


def _tek_lookahead_kontrol(sinif, mod: str, tohum: int) -> None:
    strateji = sinif()
    veri = _tek_veri(tohum, mod)
    tam = strateji.sinyaller(veri)
    for kesim in KESIMLER:
        kesik = veri.iloc[: int(len(veri) * kesim)]
        onceki = strateji.sinyaller(kesik)
        pdt.assert_frame_equal(tam.iloc[: len(kesik)], onceki, check_freq=False)


def _portfoy_lookahead_kontrol(sinif, mod: str, tohum: int) -> None:
    strateji = sinif()
    veri = _portfoy_veri(tohum, mod)
    tam_hedef, tam_stop = strateji.sinyaller(veri)
    for kesim in KESIMLER:
        kesik, bitis = _kes(veri, kesim)
        hedef, stop = strateji.sinyaller(kesik)
        pdt.assert_frame_equal(tam_hedef.loc[:bitis], hedef, check_freq=False)
        pdt.assert_frame_equal(tam_stop.loc[:bitis], stop, check_freq=False)


@pytest.mark.parametrize("ad", sorted(kayit.tum_stratejiler()))
def test_kayitli_tek_grafik_stratejileri_lookahead_yok(ad):
    sinif = kayit.tum_stratejiler()[ad]
    for mod in ("24_7", "seansli"):
        for tohum in TOHUMLAR:
            _tek_lookahead_kontrol(sinif, mod, tohum)


@pytest.mark.parametrize("ad", sorted(tum_portfoy_stratejileri()))
def test_kayitli_portfoy_stratejileri_lookahead_yok(ad):
    sinif = tum_portfoy_stratejileri()[ad]
    for mod in ("24_7", "seansli"):
        for tohum in TOHUMLAR:
            _portfoy_lookahead_kontrol(sinif, mod, tohum)
