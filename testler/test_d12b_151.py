"""D12b (151 Trading Strategies eklemeleri): pf__kesit_ls skor=ibs/dusuk_vol/r2_alfa, agirlik=orantili; pf__rotasyon
agirlik=getiri_vol; dis__hp-filtre-ma; dis__fomc-gunu-long.
Kontroller: varsayılan davranış değişmez (d11j özet testi + burada kesit/rotasyon), yeni modlar çalışır, nedensellik, dolar-nötr,
HP filtresi tek taraflı, FOMC gün içi giriş/çıkış, ayar kaydı kurulur.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.strateji import kayit
from motor.strateji.dis._gosterge_d12b import hp_nedensel, hp_son_nokta_agirliklari
from motor.strateji.dis.d12b_151 import FOMC_GUNLERI
from testler.test_d11j_modlar import _pf_veri
from testler.test_daytrade import rastgele_mumlar

KOK = Path(__file__).resolve().parent.parent
EK = json.loads((KOK / "stratejiler" / "ayarlar_d12b_ek.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pf_veri():
    return _pf_veri()


def _par(x):
    return {k: (tuple(v) if isinstance(v, list) else v) for k, v in x["parametreler"].items()}


@pytest.mark.parametrize("x", EK, ids=[x["ayar_id"] for x in EK])
def test_ek_ayar_calisir_ve_nedensel(x, pf_veri):
    sinif = tum_portfoy_stratejileri()[x["hedef"]]
    assert set(x["parametreler"]) <= set(sinif.varsayilan_parametreler)
    s = sinif(**_par(x))
    h = s.hedefler(pf_veri)
    assert h.notna().sum().sum() > 0, x["ayar_id"]
    assert (h.abs().fillna(0.0) <= 1.0 + 1e-9).all().all()
    kisa = {k: v.iloc[:-200] for k, v in pf_veri.items()}
    pdt.assert_frame_equal(h.loc[s.hedefler(kisa).index], s.hedefler(kisa), check_exact=False, rtol=1e-9, atol=1e-9)


def test_orantili_dolar_notr_ve_brut(pf_veri):
    s = tum_portfoy_stratejileri()["pf__kesit_ls"](skor="getiri", lookback_gun=60, takvim="7", agirlik="orantili", brut=1.0)
    h = s.hedefler(pf_veri).dropna(how="all")
    assert len(h) > 10
    assert (h.sum(axis=1).abs() < 1e-9).all()
    assert np.allclose(h.abs().sum(axis=1), 1.0)


def test_orantili_long_ve_tutarli(pf_veri):
    sinif = tum_portfoy_stratejileri()["pf__kesit_ls"]
    h = sinif(skor="getiri", lookback_gun=60, takvim="7", agirlik="orantili", mod="long").hedefler(pf_veri).dropna(how="all")
    assert (h.fillna(0.0) >= -1e-12).all().all() and np.allclose(h.sum(axis=1), 1.0)
    with pytest.raises(ValueError):
        sinif(skor="tutarli", takvim="7", agirlik="orantili").hedefler(pf_veri)


def test_ibs_dusuk_long_yuksek_short(pf_veri):
    s = tum_portfoy_stratejileri()["pf__kesit_ls"](skor="ibs", k=2, takvim="D")
    h = s.hedefler(pf_veri).dropna(how="all")
    i = h.index[len(h) // 2]
    ibs = {}
    for c, df in pf_veri.items():
        g = df.reindex(pd.date_range(df.index[0], df.index[-1], freq="D", tz="UTC"))
        ibs[c] = ((g["kapanis"] - g["dusuk"]) / (g["yuksek"] - g["dusuk"]))
    ibs = pd.DataFrame(ibs)[list(h.columns)].loc[i]
    long_ = [c for c in h.columns if h.loc[i, c] > 0]
    short_ = [c for c in h.columns if h.loc[i, c] < 0]
    assert len(long_) == 2 and len(short_) == 2
    assert ibs[long_].max() <= ibs[short_].min()
    assert abs(h.loc[i].sum()) < 1e-9


def test_dusuk_vol_ve_r2_secer(pf_veri):
    sinif = tum_portfoy_stratejileri()["pf__kesit_ls"]
    h = sinif(skor="dusuk_vol", lookback_gun=60, k=2, takvim="14").hedefler(pf_veri).dropna(how="all")
    i = h.index[-1]
    r = pd.DataFrame({c: df["kapanis"].pct_change() for c, df in pf_veri.items()})
    vol = r.rolling(60).std().loc[i]
    uz, ks = h.loc[i][h.loc[i] > 0].index, h.loc[i][h.loc[i] < 0].index
    assert vol[uz].max() <= vol[ks].min()
    h2 = sinif(skor="r2_alfa", lookback_gun=60, ref_sembol="DK_SPX", k=2, takvim="14").hedefler(pf_veri).dropna(how="all")
    assert len(h2) > 5 and h2.notna().sum().sum() > 0
    assert (h2.sum(axis=1).abs() < 1e-9).all()


def test_rotasyon_getiri_vol_agirlik(pf_veri):
    sinif = tum_portfoy_stratejileri()["pf__rotasyon"]
    h = sinif(k=3, takvim="M", agirlik="getiri_vol").hedefler(pf_veri).dropna(how="all")
    assert len(h) > 5
    assert (h >= -1e-12).all().all() and (h.sum(axis=1) <= 1.0 + 1e-9).all()
    assert ((h > 0).sum(axis=1) <= 3).all()
    e = sinif(k=3, takvim="M", agirlik="esit").hedefler(pf_veri).dropna(how="all")
    assert ((h > 0).sum(axis=1) == (e > 0).sum(axis=1)).all()          # aynı seçim, yalnız ağırlık farklı
    assert not np.allclose(h.to_numpy(), e.to_numpy())


def test_varsayilanlar_degismedi_esit_ayni_agirlik(pf_veri):
    """agirlik='esit' ile varsayılan kesit/rotasyon, yeni parametre eklenmeden önceki davranışla aynı kalır (d11j özet testi de bakar)."""
    for ad in ("pf__kesit_ls", "pf__rotasyon"):
        sinif = tum_portfoy_stratejileri()[ad]
        a, b = sinif().hedefler(pf_veri), sinif(agirlik=sinif.varsayilan_parametreler["agirlik"]).hedefler(pf_veri)
        pdt.assert_frame_equal(a, b)


# ---------------------------------------------------------------- HP filtresi
def test_hp_agirliklari_toplam_bir_ve_klasik_cozumle_ayni():
    w = hp_son_nokta_agirliklari(60, 1600.0)
    assert abs(w.sum() - 1.0) < 1e-9
    y = np.cumsum(np.random.default_rng(3).normal(size=60))
    d = np.zeros((58, 60))
    for i in range(58):
        d[i, i:i + 3] = (1, -2, 1)
    tam = np.linalg.solve(np.eye(60) + 1600.0 * d.T @ d, y)
    assert abs(tam[-1] - w @ y) < 1e-9


def test_hp_nedensel_gelecege_bakmaz():
    y = pd.Series(np.cumsum(np.random.default_rng(4).normal(size=400)))
    a = hp_nedensel(y, 1600.0, 80)
    b = hp_nedensel(y.iloc[:300], 1600.0, 80)
    pdt.assert_series_equal(a.iloc[:300], b)
    assert a.iloc[:79].isna().all() and a.iloc[79:].notna().all()
    y2 = y.copy()
    y2.iloc[350:] += 100.0                       # gelecek değişir, geçmiş trend değişmez
    pdt.assert_series_equal(a.iloc[:350], hp_nedensel(y2, 1600.0, 80).iloc[:350])


def test_hp_ma_sinyal_cikis_ve_nedensellik():
    m = rastgele_mumlar(n=1500, seed=7, freq="1h")
    s = kayit.al("dis__hp-filtre-ma")()
    sig = s.sinyaller(m)
    assert (sig["yon"] == 1).sum() > 0 and (sig["yon"] == -1).sum() > 0
    assert s.cikis_var_mi()
    assert (sig.loc[sig["yon"] == 1, "stop"] < m["kapanis"][sig["yon"] == 1]).all()
    assert (sig.loc[sig["yon"] == -1, "stop"] > m["kapanis"][sig["yon"] == -1]).all()
    pdt.assert_frame_equal(sig.iloc[:1000], s.sinyaller(m.iloc[:1000]))


# ---------------------------------------------------------------- FOMC
def test_fomc_tablosu_gecerli():
    t = pd.to_datetime(list(FOMC_GUNLERI))
    assert len(t) == len(set(t)) == 55 and list(t) == sorted(t)
    assert (t.dayofweek < 5).all()
    assert t.year.min() == 2020 and t.year.max() == 2026


def test_fomc_gunu_long_yalniz_fomc_gununde_ve_cikar():
    m = rastgele_mumlar(n=24 * 60, seed=8, freq="1h", baslangic="2022-03-01")
    s = kayit.al("dis__fomc-gunu-long")()
    sig = s.sinyaller(m)
    gir = sig.index[sig["yon"] == 1]
    assert len(gir) == 1 and gir[0] == pd.Timestamp("2022-03-16", tz="UTC")           # 2022-03-16 FOMC; ilk bar
    assert (sig["yon"] != -1).all()
    assert (sig.loc[gir, "stop"] < m.loc[gir, "kapanis"]).all()
    cik = sig.index[sig["cikis_long"].astype(bool)]
    assert pd.Timestamp("2022-03-16 19:00", tz="UTC") in cik                        # kapanış 20:00 >= cikis_saat
    assert pd.Timestamp("2022-03-16 10:00", tz="UTC") not in cik
    pdt.assert_frame_equal(sig.iloc[:700], s.sinyaller(m.iloc[:700]))
    assert s.cikis_var_mi()


def test_fomc_gunluk_mumda_hata():
    m = rastgele_mumlar(n=400, seed=9, freq="1D", baslangic="2022-01-01")
    with pytest.raises(ValueError):
        kayit.al("dis__fomc-gunu-long")().sinyaller(m)


def test_ayar_izgarasi_en_fazla_27():
    for ad in ("dis__fomc-gunu-long", "dis__hp-filtre-ma"):
        n = 1
        for v in kayit.al(ad).parametre_izgarasi.values():
            n *= len(v)
        assert n <= 27
    assert kayit.dogrula() == []
