"""Rsi32Kaynak: sinyal, gelecekten bağımsızlık, stop ve kaynak çıkış kuralı denetimi.

Kaynak: upupnoah/noahroboros, commit 1e3edc649344e6f4aa4a75a86822809b2a1f0028,
src/strategy/baseline.rs 280-318 (RSI geri kesişim çıkışı 77/23, uç çıkış 85/15).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.kapanis.rsi32_kaynak import Rsi32Kaynak


def _mumlar(n: int = 600, tohum: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(tohum)
    idx = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
    dalga = 6.0 * np.sin(np.arange(n) / 25.0)
    kap = 100.0 + dalga + np.cumsum(rng.normal(0, 0.6, n))
    ac = np.concatenate([[kap[0]], kap[:-1]])
    return pd.DataFrame(
        {"acilis": ac, "yuksek": np.maximum(ac, kap) + 0.4,
         "dusuk": np.minimum(ac, kap) - 0.4, "kapanis": kap,
         "hacim": np.full(n, 1000.0)}, index=idx)


def test_sinyal_uretir_iki_yon() -> None:
    s = Rsi32Kaynak().sinyaller(_mumlar())
    assert (s["yon"] == 1).any()
    assert (s["yon"] == -1).any()


def test_gelecek_mumlar_gecmis_sinyali_degistirmez() -> None:
    m = _mumlar()
    ilk = Rsi32Kaynak().sinyaller(m.iloc[:500])
    tam = Rsi32Kaynak().sinyaller(m)
    pd.testing.assert_frame_equal(ilk, tam.iloc[:500])
    degisik = m.copy()
    degisik.iloc[500:, 1:4] *= 3.0
    sonra = Rsi32Kaynak().sinyaller(degisik)
    pd.testing.assert_frame_equal(ilk, sonra.iloc[:500])


def test_her_girisin_stopu_var_ve_dogru_tarafta() -> None:
    m = _mumlar()
    s = Rsi32Kaynak().sinyaller(m)
    giris = s["yon"] != 0
    assert giris.any()
    assert s.loc[giris, "stop"].notna().all()
    k = m["kapanis"]
    assert (s.loc[s["yon"] == 1, "stop"] < k[s["yon"] == 1]).all()
    assert (s.loc[s["yon"] == -1, "stop"] > k[s["yon"] == -1]).all()


def test_cikis_esigin_gerisine_kesiste() -> None:
    """Long: RSI önceki mumda >=77 iken şimdi <77; eşiğe ilk erişimde çıkış yok."""
    n = 400
    idx = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
    rng = np.random.default_rng(3)
    adim = np.where(np.arange(n) < 200, 0.5, -0.5) + rng.normal(0, 0.45, n)
    kap = 100.0 + np.cumsum(adim)
    ac = np.concatenate([[kap[0]], kap[:-1]])
    m = pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) + 0.3,
                      "dusuk": np.minimum(ac, kap) - 0.3, "kapanis": kap,
                      "hacim": np.full(n, 1000.0)}, index=idx)
    p = Rsi32Kaynak().parametreler
    assert (p["cikis_ust"], p["cikis_alt"], p["guven_ust"], p["guven_alt"]) == (77.0, 23.0, 85.0, 15.0)
    s = Rsi32Kaynak().sinyaller(m)
    rsi = g.rsi(m["kapanis"], 32)
    geri_ust = (rsi.shift(1) >= 77) & (rsi < 77)
    uc_ust = rsi >= 85
    assert (s["cikis_long"] == (geri_ust | uc_ust)).all()
    geri_alt = (rsi.shift(1) <= 23) & (rsi > 23)
    uc_alt = rsi <= 15
    assert (s["cikis_short"] == (geri_alt | uc_alt)).all()
    # 77..85 arasına ilk erişim tek başına çıkış sayılmaz
    ilk_erisim = (rsi >= 77) & (rsi < 85) & (rsi.shift(1) < 77)
    assert ilk_erisim.any()
    assert not s.loc[ilk_erisim, "cikis_long"].any()
