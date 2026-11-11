"""Parti 6 (Cuma 15 EST tutma, kripto MAX piyango) kural testleri; yalnız sentetik veri, backtest yok."""
import numpy as np
import pandas as pd
import pytest

from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.portfoy.stratejiler.v3 import V3_KRIPTO, KriptoMaxPiyango
from motor.strateji.dis.v3_adaylar_6 import Cuma15EstTutma
from motor.strateji.kayit import al


def _mum(idx, fiyat, genlik=0.002):
    k = pd.Series(fiyat, index=idx, dtype=float)
    o = k.shift(1).fillna(k.iloc[0])
    return pd.DataFrame({"acilis": o, "yuksek": np.maximum(o, k) * (1 + genlik),
                         "dusuk": np.minimum(o, k) * (1 - genlik), "kapanis": k, "hacim": 10.0}, index=idx)


# ------------------------------------------------------------------ Cuma 15:00 EST tutma
def _saatlik(bas="2024-01-01", gun=70):
    idx = pd.date_range(bas, periods=gun * 24, freq="1h", tz="UTC")
    rng = np.random.default_rng(3)
    return _mum(idx, 100.0 * np.exp(np.cumsum(rng.normal(0, 0.003, len(idx)))))


def test_cuma15_giris_cuma_20_utc_cikis_cumartesi_00_utc_sabit_est():
    m = _saatlik()                            # kış (Ocak) ve yaz (Haziran'a uzanmayan) dahil; aşağıda yaz ayrıca
    s = Cuma15EstTutma().sinyaller(m)
    giris = np.flatnonzero(s.yon.to_numpy() == 1)
    cikis = np.flatnonzero(s.cikis.to_numpy())
    assert len(giris) >= 8
    assert (m.index[giris].day_of_week == 4).all() and (m.index[giris].hour == 20).all()
    assert (m.index[cikis].day_of_week == 5).all() and (m.index[cikis].hour == 0).all()
    # Dolum zamanı: giriş sinyalinden sonraki mum 21:00 UTC (= 16:00 EST), çıkış dolumu 01:00 UTC (= 20:00 EST).
    assert (m.index[giris + 1].hour == 21).all() and (m.index[cikis + 1].hour == 1).all()
    # 4 mum tutulur: giriş mumu +4 = çıkış sinyali mumu.
    assert (cikis[:len(giris)] - giris[:len(cikis)] == 4).all()
    # Hiçbir mumda short yok; stop long için kapanışın altında ve 2 ATR mesafesinde.
    assert not (s.yon == -1).any()
    assert (s.stop[s.yon == 1] < m.kapanis[s.yon == 1]).all()
    assert s.stop[s.yon == 1].notna().all()


def test_cuma15_yaz_saatinde_de_utc_saati_kaymaz():
    m = _saatlik("2024-06-03", 40)              # Haziran: EDT olsa 19:00 UTC olurdu; sabit EST -> 20:00 UTC
    s = Cuma15EstTutma().sinyaller(m)
    g = m.index[s.yon == 1]
    assert len(g) >= 4 and (g.hour == 20).all() and (g.day_of_week == 4).all()


def test_cuma15_diger_gun_ve_saatlerde_sinyal_yok_ve_stop_atr_x2():
    m = _saatlik()
    s = Cuma15EstTutma().sinyaller(m)
    diger = ~((m.index.day_of_week == 4) & (m.index.hour == 20))
    assert (s.yon[diger] == 0).all()
    from motor.strateji import gostergeler as g
    atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14)
    j = np.flatnonzero(s.yon.to_numpy() == 1)[-1]
    assert s.stop.iloc[j] == pytest.approx(m.kapanis.iloc[j] - 2.0 * atr.iloc[j])
    assert al(Cuma15EstTutma.ad) is Cuma15EstTutma and Cuma15EstTutma().cikis_var_mi()


def test_cuma15_lookahead_yok():
    m = _saatlik()
    tam = Cuma15EstTutma().sinyaller(m)
    for n in (len(m) // 3 + 7, len(m) * 2 // 3):
        kisa = Cuma15EstTutma().sinyaller(m.iloc[:n])
        pd.testing.assert_frame_equal(kisa, tam.iloc[:n], check_dtype=False)


# ------------------------------------------------------------------ kripto MAX piyango
def _max_veri(n=130, sicrama=None):
    """10 sembol; i. sembolün günlük getiri genliği 0.1%*(i+1) (alternatif işaret): MAX sırası = i sırası."""
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC", name="zaman")
    adlar = V3_KRIPTO[:10]
    veri = {}
    for i, a in enumerate(adlar):
        r = np.where(np.arange(n) % 2 == 0, 0.001 * (i + 1), -0.001 * (i + 1) * 0.5)
        veri[a] = r
    if sicrama:
        for a, gun, getiri in sicrama:
            veri[a] = veri[a].copy()
            veri[a][gun] = getiri
    return {a: _mum(idx, 100.0 * np.cumprod(1.0 + r)) for a, r in veri.items()}


def test_max_piyango_yuksek_max_long_dusuk_max_short_haftalik_pazartesi():
    adlar = V3_KRIPTO[:10]
    veri = _max_veri(sicrama=[(adlar[0], 60, 0.20)])       # en düşük genlikli coin 60. günde +%20 yapar
    st = KriptoMaxPiyango(semboller=adlar)
    h, s = st.sinyaller(veri)
    acik = h.dropna(how="all")
    assert (acik.index[1:].day_of_week == 0).all()           # ilk geçerli satırdan sonra yalnız Pazartesi
    pazartesi = h.loc["2024-03-11"]                          # 2024-01-01 + 70 gün; sıçrama (gün 60) pencerede
    assert pazartesi[adlar[0]] == pytest.approx(0.25)        # k = ceil(10*0.2) = 2 -> bacak başı 0.25
    uzun = pazartesi[pazartesi > 0].index.tolist()
    kisa = pazartesi[pazartesi < 0].index.tolist()
    assert set(uzun) == {adlar[0], adlar[9]}                 # en yüksek MAX: sıçrayan + en yüksek genlikli
    assert set(kisa) == {adlar[1], adlar[2]}                 # en düşük MAX: sıçramasız en düşük genlikler
    assert pazartesi.sum() == pytest.approx(0.0) and pazartesi.abs().sum() == pytest.approx(1.0)
    # Sıçrama 28 günlük pencereden çıkınca (gün 60 + 28 = 88 sonrası ilk Pazartesi) coin artık long değil.
    sonra = h.loc["2024-04-01"]                              # gün 91: pencere gün 64..91, sıçrama dışarıda
    assert sonra[adlar[0]] <= 0
    assert tum_portfoy_stratejileri()[KriptoMaxPiyango.ad] is KriptoMaxPiyango
    # Stop zorunlu: açık her hedefte stop var, long altta short üstte.
    kap = pd.DataFrame({a: veri[a]["kapanis"] for a in adlar})
    t = pd.Timestamp("2024-03-11", tz="UTC")
    assert s.loc[t, adlar[0]] < kap.loc[t, adlar[0]] and s.loc[t, adlar[1]] > kap.loc[t, adlar[1]]


def test_max_piyango_lookahead_yok_ve_min_sembol():
    adlar = V3_KRIPTO[:10]
    veri = _max_veri(sicrama=[(adlar[0], 60, 0.20)])
    st = KriptoMaxPiyango(semboller=adlar)
    h, _ = st.sinyaller(veri)
    kes = pd.Timestamp("2024-03-11", tz="UTC")
    kisa = {a: d.loc[d.index <= kes] for a, d in veri.items()}
    hk, _ = st.sinyaller(kisa)
    pd.testing.assert_frame_equal(hk, h.loc[:kes], check_dtype=False)
    # Gelecek verisi bozulsa da Pazartesi hedefi aynı kalır.
    bozuk = {a: d.copy() for a, d in veri.items()}
    for d in bozuk.values():
        d.loc[d.index > kes, ["acilis", "yuksek", "dusuk", "kapanis"]] *= 7.0
    hb, _ = st.sinyaller(bozuk)
    pd.testing.assert_series_equal(hb.loc[kes], h.loc[kes], check_dtype=False)
    az = {a: veri[a] for a in adlar[:4]}
    assert not KriptoMaxPiyango(semboller=tuple(az)).uygun_mu(az)
    with pytest.raises(ValueError, match="en az 5 sembol"):
        KriptoMaxPiyango(semboller=tuple(az)).sinyaller(az)
