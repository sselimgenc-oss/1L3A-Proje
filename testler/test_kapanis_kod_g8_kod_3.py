"""g8_kod_3 sınıfları: sinyal üretir, gelecek geçmişi değiştirmez, her girişte stop doğru tarafta, VARYANTLAR bütün."""
from __future__ import annotations

import csv
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.strateji.kapanis import kod_g8_kod_3 as mod
from motor.strateji.temel import Strateji

SINIFLAR = {s.ad: s for _, s in inspect.getmembers(mod, inspect.isclass)
            if issubclass(s, Strateji) and s is not Strateji}
GIRDI = Path(__file__).resolve().parents[1] / "sonuclar" / "kapanis" / "kod_girdi" / "g8_kod_3.csv"
SAAT = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "2h": "2h", "4h": "4h", "1d": "1D"}
# bar sayısı: ısınması uzun olanlar için büyük
BAR = {"HAM:X005:296": 2600, "HAM:X005:297": 2600, "HAM:X005:310": 1500, "HAM:X005:325": 6000,
       "HAM:X005:314": 4000, "HAM:X005:313": 4000, "HAM:X005:317": 4000, "HAM:X005:247": 4000,
       "HAM:X005:294": 4000, "HAM:X005:332": 4000, "HAM:X005:287": 6000, "HAM:X005:328": 4000}


def _mumlar(n: int, aralik: str, tohum: int = 11) -> pd.DataFrame:
    """Rejim değiştiren (yükseliş / düşüş / yatay) sentetik seri; hem trend hem ortalamaya dönüş kuralları sinyal bulur."""
    rng = np.random.default_rng(tohum)
    getiri = np.empty(n)
    i = 0
    while i < n:
        uz = int(rng.integers(60, 260))
        surukle = rng.choice([0.0035, -0.003, 0.0, 0.0008])
        vol = rng.choice([0.008, 0.012, 0.02])
        getiri[i:i + uz] = rng.normal(surukle, vol, min(uz, n - i))
        i += uz
    kapanis = 100 * np.exp(np.cumsum(getiri))
    acilis = np.r_[kapanis[0], kapanis[:-1]] * (1 + rng.normal(0, 0.001, n))
    yuksek = np.maximum(acilis, kapanis) * (1 + np.abs(rng.normal(0, 0.006, n)))
    dusuk = np.minimum(acilis, kapanis) * (1 - np.abs(rng.normal(0, 0.006, n)))
    idx = pd.date_range("2021-01-04", periods=n, freq=aralik, tz="UTC")
    return pd.DataFrame({"acilis": acilis, "yuksek": yuksek, "dusuk": dusuk, "kapanis": kapanis,
                         "hacim": 100.0}, index=idx)


def _kayit_id(v):
    return v["kimlik"]


@pytest.mark.parametrize("v", mod.VARYANTLAR, ids=_kayit_id)
def test_sinyal_stop_gelecek(v):
    kaynak = v["kimlik"].split("#")[0]
    st = SINIFLAR[v["sinif"]](**v["parametreler"])
    m = _mumlar(BAR.get(kaynak, 1800), SAAT[v["tf"]])
    s = st.sinyaller(m)
    assert list(m.index) == list(s.index)
    giris = s["yon"] != 0
    assert giris.any(), "sentetik veride sinyal üretmeli"
    uzun, kisa = s["yon"] == 1, s["yon"] == -1
    assert s.loc[giris, "stop"].notna().all()
    assert (s.loc[uzun, "stop"] < m.loc[uzun, "kapanis"]).all()
    assert (s.loc[kisa, "stop"] > m.loc[kisa, "kapanis"]).all()
    assert st.cikis_var_mi() and st.parametre_izgarasi == {}
    # lookahead: son mumlar değişince önceki sinyaller aynı kalır
    k = len(m) - 80
    m2 = m.copy()
    m2.iloc[k:, m2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 2.5
    s2 = st.sinyaller(m2)
    pd.testing.assert_frame_equal(s.iloc[:k], s2.iloc[:k])


def test_varyantlar_butun():
    kimlikler = [v["kimlik"] for v in mod.VARYANTLAR]
    assert len(kimlikler) == len(set(kimlikler))
    for v in mod.VARYANTLAR:
        assert v["sinif"] in SINIFLAR and v["tf"] in SAAT
        st = SINIFLAR[v["sinif"]](**v["parametreler"])
        assert st.ad == v["sinif"]
    kaynaklar = {r["kaynak_id"] for r in csv.DictReader(open(GIRDI, encoding="utf-8"))}
    kodlu = {k.split("#")[0] for k in kimlikler}
    kodsuz = {k["kimlik"] for k in mod.KODLANAMADI}
    assert kodlu | kodsuz == kaynaklar and not (kodlu & kodsuz)
    assert all(k["neden"] for k in mod.KODLANAMADI)
    assert len(SINIFLAR) == len({v["sinif"] for v in mod.VARYANTLAR}) + 1  # EmaHiloS0353 koşulmaz
    assert all(v.get("yaklasik") for v in mod.VARYANTLAR if v["kimlik"].split("#")[0] in ("HAM:X005:294", "HAM:X005:310", "HAM:X005:325"))


def test_306_varyant_sayisi_ve_kural():
    v306 = [v for v in mod.VARYANTLAR if v["kimlik"].startswith("HAM:X005:306#")]
    assert len(v306) == 36 and len({tuple(v["parametreler"].values()) for v in v306}) == 36
    m = _mumlar(900, "1D")
    s = mod.SmaBantS0306(s=1, l=20, b=0.01).sinyaller(m)
    kap = m["kapanis"]
    sma = kap.rolling(20).mean()
    assert (s["cikis_long"] == (kap < sma * 0.99)).all()
    durum = kap > sma * 1.01
    olay = durum & ~durum.shift(1, fill_value=False)
    assert ((s["yon"] == 1) == (olay & s["stop"].notna())).all()


def test_339_varyantlari():
    v339 = [v for v in mod.VARYANTLAR if v["kimlik"].startswith("HAM:X005:339#")]
    assert len(v339) == 10
    m = _mumlar(1800, "1D")
    kap = m["kapanis"]
    s3 = mod.RsiBantiTrendS0339(alt_std=2.0, kar_al_pct=2.0).sinyaller(m)
    g3 = s3["yon"] == 1
    assert g3.any() and np.allclose(s3.loc[g3, "hedef"], kap[g3] * 1.02)
    s5 = mod.RsiBantiTrendS0339(alt_std=2.0, stop_pct=5.0).sinyaller(m)
    g5 = s5["yon"] == 1
    assert g5.any() and np.allclose(s5.loc[g5, "stop"], kap[g5] * 0.95)


def test_283_hedef_stop():
    m = _mumlar(1800, "1D")
    s = mod.BbAltGeriS0283().sinyaller(m)
    g = s["yon"] == 1
    kap = m["kapanis"]
    ort = kap.rolling(20).mean()
    assert g.any() and np.allclose(s.loc[g, "hedef"], ort[g])
    assert (s.loc[g, "hedef"] > kap[g]).all()


def test_320_zaman_cikisi_iki_yon():
    for n in (1, 2, 3):
        st = mod.ArdisikKapanisS0320(n=n)
        assert st.cikis_ayarlari.zaman_cikisi_mum == 1
        s = st.sinyaller(_mumlar(900, "1D"))
        assert (s["yon"] == 1).any() and (s["yon"] == -1).any()
    s = mod.ArdisikKapanisS0320(n=2).sinyaller(_mumlar(900, "1D"))
    m = _mumlar(900, "1D")
    dus = (m["kapanis"].diff() < 0) & (m["kapanis"].diff().shift(1) < 0)
    assert ((s["yon"] == 1) == (dus & s["stop"].notna())).all()


def test_310_baslangic_stopu_ve_iz_suren_cikis():
    m = _mumlar(1500, "1D")
    s = mod.PmaHaftalikS0310().sinyaller(m)
    g = s["yon"] == 1
    assert g.any() and np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * 0.9)
    assert s["cikis_long"].any()


def test_325_iz_suren_sanal_pozisyon():
    # sanal pozisyon: iki giriş arasında çıkış (kapanış zirve kapanışın %3 altı) ya da sert stop olmalı
    m = _mumlar(6000, "5min")
    s = mod.CokluTfSmaS0325().sinyaller(m)
    gi = np.flatnonzero((s["yon"] == 1).to_numpy())
    assert len(gi) >= 1
    ci = (s["cikis_long"]).to_numpy()
    kap, dus = m["kapanis"].to_numpy(), m["dusuk"].to_numpy()
    for a, b in zip(gi[:-1], gi[1:]):
        assert ci[a:b + 1].any() or (dus[a + 1:b + 1] <= s["stop"].iloc[a]).any()


def test_294_iz_yuzdeleri():
    m = _mumlar(4000, "15min")
    for y in (7.0, 3.0):
        s = mod.BbIzStopS0294(iz_yuzde=y).sinyaller(m)
        g = s["yon"] == 1
        assert g.any() and np.allclose(s.loc[g, "stop"], m.loc[g, "kapanis"] * (1 - y / 100))


def test_356_kodlanamadi():
    assert sorted(k["kimlik"] for k in mod.KODLANAMADI) == ["HAM:X005:353", "HAM:X005:356"]
