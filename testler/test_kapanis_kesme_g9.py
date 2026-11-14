"""Kesme (lookahead) testi — aşama 2 Robotic/K3 kod dosyaları. Yöntem `test_kapanis_kesme.py` ile aynı (yardımcılar oradan):
sinyaller(m.iloc[:k]) == sinyaller(m).iloc[:k]; kancalı sınıflarda kanca yalnız açık pozisyonda ve sonraki açılışta çıkış."""
from __future__ import annotations

import importlib
import inspect

import pandas as pd
import pytest

from motor.strateji.temel import Strateji
from testler.test_kapanis_kesme import FREQ, KESME, _mumlar

ADLAR = ["kod_g9_kod_1", "kod_g9_kod_2", "kod_g9_kod_3", "kod_g9_kod_4", "kod_g9_kod_5", "kod_g9_kod_6", "kod_g9_kod_7",
         "kod_g9_kod_8b", "kod_k3_kod_1"]
DOSYALAR = []
for _ad in ADLAR:
    try:
        DOSYALAR.append(importlib.import_module(f"motor.strateji.kapanis.{_ad}"))
    except ModuleNotFoundError:
        pass

SINIF = {}
for _mod in DOSYALAR:
    for _c in [v for v in vars(_mod).values() if inspect.isclass(v)]:
        if issubclass(_c, Strateji) and _c is not Strateji and getattr(_c, "ad", ""):
            SINIF.setdefault(_c.ad, _c)
KAYITLAR = [(m.__name__.rsplit(".", 1)[1], k) for m in DOSYALAR for k in m.VARYANTLAR if k["sinif"] in SINIF]


def test_kimlikler_tekil_ve_tf_destekli():
    kim = [k["kimlik"] for m in DOSYALAR for k in m.VARYANTLAR]
    assert len(kim) == len(set(kim))
    for m in DOSYALAR:
        for k in m.VARYANTLAR:
            assert k["tf"] in FREQ, (k["kimlik"], k["tf"])


@pytest.mark.parametrize("dosya,kayit", KAYITLAR, ids=lambda x: x if isinstance(x, str) else x["kimlik"] + "-" + x["tf"])
def test_kesme(dosya, kayit):
    st = SINIF[kayit["sinif"]](**kayit["parametreler"])
    for tohum in (3, 8):
        m = _mumlar(FREQ[kayit["tf"]], tohum)
        tam = st.sinyaller(m)
        assert list(tam.index) == list(m.index)
        for k in KESME:
            pd.testing.assert_frame_equal(st.sinyaller(m.iloc[:k]), tam.iloc[:k], check_exact=False, rtol=1e-9, atol=1e-9)
