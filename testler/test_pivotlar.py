"""Nedensel pivot tespiti: onay gecikmesi ve lookahead yokluğu."""
import numpy as np
import pandas as pd
import pandas.testing as pdt

from motor.strateji.pivotlar import fraktal_pivotlar, pivot_tablosu, zigzag_pivotlar


def rastgele(n=600, seed=3):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    ac = np.r_[kap[0], kap[:-1]]
    yu = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.004, n))
    du = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.004, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": yu, "dusuk": du, "kapanis": kap, "hacim": 1.0}, index=idx)


def zirveli_seri():
    # 0..9 yükselir, tepe=10 indeksinde 20, sonra düşer; dip 20'de.
    y = np.r_[np.arange(10, 20), 20, np.arange(19, 9, -1), 9, np.arange(10, 16)].astype(float)
    idx = pd.RangeIndex(len(y))
    return pd.Series(y + 0.5, index=idx), pd.Series(y - 0.5, index=idx)


def test_fraktal_pivot_onaydan_once_gorunmez():
    yu, du = zirveli_seri()
    k = 3
    t = fraktal_pivotlar(yu, du, k)
    # tepe indeksi 10: onay 13'te
    assert t["son_tepe_fiyat"].iloc[:13].isna().all()
    assert t["son_tepe_fiyat"].iloc[13] == 20.5
    assert t["son_tepe_idx"].iloc[13] == 10
    assert t["son_tepe_onay_idx"].iloc[13] == 13
    assert bool(t["yeni_tepe"].iloc[13]) and not t["yeni_tepe"].iloc[:13].any()
    # dip indeksi 21 (değer 9): onay 24'te
    assert t["son_dip_fiyat"].iloc[:24].isna().all()
    assert t["son_dip_fiyat"].iloc[24] == 8.5
    assert t["son_dip_idx"].iloc[24] == 21
    # onay mumu her zaman pivot + k
    ok = t["son_tepe_onay_idx"].dropna()
    assert ((ok - t.loc[ok.index, "son_tepe_idx"]) == k).all()


def test_fraktal_son_ve_onceki():
    y = np.r_[np.arange(0, 6), np.arange(5, 0, -1), np.arange(1, 8), np.arange(7, 0, -1), np.arange(1, 5)].astype(float)
    yu, du = pd.Series(y + 0.5), pd.Series(y - 0.5)
    t = fraktal_pivotlar(yu, du, 2)
    son = t.iloc[-1]
    assert son["onceki_tepe_fiyat"] == 5.5 and son["son_tepe_fiyat"] == 7.5
    assert son["onceki_tepe_idx"] < son["son_tepe_idx"]


def test_pivot_lookahead_yok():
    df = rastgele()
    for yontem in ("fraktal", "zigzag"):
        tam = pivot_tablosu(df, yontem, k=3, esik_k=2.0)
        for n in (120, 301, 450):
            pdt.assert_frame_equal(pivot_tablosu(df.iloc[:n], yontem, k=3, esik_k=2.0), tam.iloc[:n])


def test_zigzag_onay_gecikmeli_ve_alternatif():
    df = rastgele()
    t = zigzag_pivotlar(df["yuksek"], df["dusuk"], df["kapanis"], 14, 2.0)
    assert t["yeni_tepe"].sum() > 3 and t["yeni_dip"].sum() > 3
    ok = t.dropna(subset=["son_tepe_onay_idx"])
    assert (ok["son_tepe_onay_idx"] > ok["son_tepe_idx"]).all()
    # pivot fiyatı o mumun gerçek zirvesi
    i = int(t["son_tepe_idx"].iloc[-1])
    assert t["son_tepe_fiyat"].iloc[-1] == df["yuksek"].iloc[i]
    # tepe ve dip onayları dönüşümlü (aynı türden art arda iki onay yok)
    olay = []
    for ix in range(len(t)):
        if t["yeni_tepe"].iloc[ix]:
            olay.append(1)
        if t["yeni_dip"].iloc[ix]:
            olay.append(-1)
    assert all(a != b for a, b in zip(olay, olay[1:]))
