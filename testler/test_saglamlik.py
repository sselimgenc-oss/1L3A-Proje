"""Sağlamlık analizi (Katman 3b): rastgele giriş, bootstrap, DSR, parametre komşuları, rejim, maliyet çarpanı."""
import inspect
import math

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import saglamlik as sg
from motor.arastirma import wf_tarama as wf
from motor.backtest.motor import MotorAyarlari, SembolKurallari, backtest
from motor.strateji import gostergeler as gst
from testler.test_bt_motor import Hazir, mumlar_yap, sinyal_yap


# ---------------------------------------------------------------------------- sentetik piyasa
def _piyasa(n=4000, tohum=1, ziplama=True):
    """1s mum; gürültülü rastgele yürüyüş. ziplama=True: her 50 mumda sinyal mumundan (50m) sonraki 10 mum +%0.5
    sabit yukarı (gizli kenar: 50m kapanışında giren long kazanır)."""
    rng = np.random.default_rng(tohum)
    getiri = rng.normal(0, 0.003, n)
    if ziplama:
        for m in range(1, n // 50):
            getiri[50 * m + 1: 50 * m + 11] = 0.005
    kap = 100 * np.exp(np.cumsum(getiri))
    ac = np.r_[100.0, kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + np.abs(rng.normal(0, 0.0007, n)))
    dus = np.minimum(ac, kap) * (1 - np.abs(rng.normal(0, 0.0007, n)))
    idx = pd.date_range("2022-01-01", periods=n, freq="1h", tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap, "hacim": 1.0}, index=idx)


AYAR = MotorAyarlari(limit_modu="olc")


def _gercek_toplam(mumlar, giris_mumlari, hm=10, mult=3.0, yon=1):
    atr = gst.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], 14).to_numpy(float)
    o, h, l, c = (mumlar[k].to_numpy(float) for k in ("acilis", "yuksek", "dusuk", "kapanis"))
    top = 0.0
    for j in giris_mumlari:
        r = sg._tek_islem_r(o, h, l, c, atr, int(j), yon, hm, mult, AYAR.kayma_bps / 1e4, AYAR.stop_kayma_bps / 1e4,
                            AYAR.komisyon_taker_yuzde / 100)
        top += r if r is not None else 0.0
    return top, atr


def _tanim(m, hm=10, mult=3.0):
    return pd.DataFrame({"yon": [1] * m, "h": [hm] * m, "stop_atr": [mult] * m})


def _uygun(mumlar, atr):
    return sg.uygun_giris_mumlari(mumlar, [{"secilen": "x", "test_bas": str(mumlar.index[0]),
                                            "test_bit": str(mumlar.index[-1] + pd.Timedelta("1h"))}], atr)


def test_rastgele_giris_kenarli_strateji_p_kucuk():
    mum = _piyasa()
    giris = [50 * m + 1 for m in range(1, 79)]               # sinyal 50m kapanışı -> giriş 50m+1 açılışı
    gercek, atr = _gercek_toplam(mum, giris)
    rs = sg.rastgele_giris(mum, _tanim(len(giris)), _uygun(mum, atr), AYAR, n_sim=200, seed=3)
    p, yuz = sg.rastgele_p(gercek, rs["toplam_r"])
    assert gercek > rs["toplam_r"].mean() + 3 * rs["toplam_r"].std()
    assert p <= 0.02 and yuz >= 0.99


def test_rastgele_giris_kenarsiz_strateji_p_buyuk():
    mum = _piyasa(ziplama=False, tohum=5)
    atr = gst.atr(mum["yuksek"], mum["dusuk"], mum["kapanis"], 14).to_numpy(float)
    uygun = _uygun(mum, atr)
    ps = []
    for tohum in range(8):                       # kenarsız "strateji" = rastgele zamanlar; p ~ düzgün dağılmalı
        rng = np.random.default_rng(100 + tohum)
        giris = rng.choice(uygun[uygun < len(mum) - 20], 60, replace=False)
        gercek, _ = _gercek_toplam(mum, giris)
        rs = sg.rastgele_giris(mum, _tanim(60), uygun, AYAR, n_sim=200, seed=tohum)
        ps.append(sg.rastgele_p(gercek, rs["toplam_r"])[0])
    assert np.median(ps) > 0.2
    assert np.mean(np.array(ps) <= 0.05) <= 0.25


def test_rastgele_islem_gelecegi_gormez():
    """Bir rastgele işlemin R'si giriş mumundan j+H'den sonraki mumlara bağlı olamaz."""
    mum = _piyasa(n=600)
    atr = gst.atr(mum["yuksek"], mum["dusuk"], mum["kapanis"], 14).to_numpy(float)
    j, hm = 300, 10

    def r_of(m):
        o, h, l, c = (m[k].to_numpy(float) for k in ("acilis", "yuksek", "dusuk", "kapanis"))
        return sg._tek_islem_r(o, h, l, c, atr, j, 1, hm, 3.0, 2e-4, 5e-4, 5e-4)

    temel = r_of(mum)
    bozuk = mum.copy()
    bozuk.iloc[j + hm + 1:, :4] = 1e6                     # çıkış açılışından SONRAki mumlar çöpe
    assert r_of(bozuk) == temel
    bozuk2 = mum.copy()
    bozuk2.iloc[j + hm, bozuk2.columns.get_loc("acilis")] *= 1.01     # çıkış açılışı gerçekten kullanılıyor
    assert r_of(bozuk2) != temel


def test_islem_tanimlari_stop_mesafesi_ve_sure():
    mum = _piyasa(n=300, ziplama=False)
    atr = gst.atr(mum["yuksek"], mum["dusuk"], mum["kapanis"], 14).to_numpy(float)
    j = 100
    oos = pd.DataFrame({"yon": [-1], "giris_zamani": [mum.index[j]], "cikis_zamani": [mum.index[j + 7]],
                        "miktar": [2.0], "net_pnl": [-10.0], "r": [-0.5]})        # risk_tutar = 20 -> mesafe 10
    t = sg.islem_tanimlari(mum, oos, atr)
    assert t["yon"][0] == -1 and t["h"][0] == 7
    assert t["stop_atr"][0] == pytest.approx(10.0 / atr[j - 1])


# ---------------------------------------------------------------------------- bootstrap
def _kapsama(n, blok, n_rep=200):
    rng = np.random.default_rng(7)
    gercek_pf = 0.4 * 2 / 0.6                              # kazanç 0.4 x +2R, kayıp 0.6 x -1R
    kapsa = 0
    for i in range(n_rep):
        r = np.where(rng.random(n) < 0.4, 2.0, -1.0)
        lo, hi, med = sg.pf_boot(r, blok=blok, n_boot=400, rng=np.random.default_rng(i))
        assert lo <= med <= hi
        kapsa += lo <= gercek_pf <= hi
    return kapsa / n_rep


def test_bootstrap_kapsama():
    """Bilinen PF = 4/3 (iid): blok=1 iken %90 aralık ~%90 kapsar; 20'lik bloklu aralık uzun örneklemde makul kapsar.
    (n=100'de 20'lik blok yalnız 5 blok verir ve bilinen biçimde dar kalır, ~%80; bu yüzden n=400 ile sınanır.)"""
    assert 0.84 <= _kapsama(100, 1) <= 0.96
    assert 0.82 <= _kapsama(400, 20) <= 0.97


def test_bootstrap_kenarsizda_alt_sinir_bire_yakin_veya_alti():
    rng = np.random.default_rng(3)
    r = rng.normal(0, 1, 120)
    lo, hi, _ = sg.pf_boot(r, rng=np.random.default_rng(0))
    assert lo < 1.0 < hi


# ---------------------------------------------------------------------------- DSR
def test_psr_bilinen_deger():
    """x = 0.1 + {-1,+1} eşit: çarpıklık 0, basıklık 1 => paydanın düzeltmesi 1; N=1 => SR0=0, DSR = Phi(sr*sqrt(T-1))."""
    x = np.tile([1.1, -0.9], 50)
    d = sg.deflated_sharpe(x, 1, 1.0)
    sr = 0.1 / math.sqrt(100 / 99)
    z = sr * math.sqrt(99)
    assert d["sr"] == pytest.approx(sr)
    assert d["carpiklik"] == pytest.approx(0.0, abs=1e-12) and d["basiklik"] == pytest.approx(1.0)
    assert d["dsr"] == pytest.approx(0.5 * (1 + math.erf(z / math.sqrt(2))))
    assert d["dsr"] == pytest.approx(0.8389, abs=1e-3)


def test_beklenen_maks_sr_bilinen_deger():
    # N=100, V=0.25: 0.5*((1-g)*Z(0.99) + g*Z(1-1/(100e))); Z(0.99)=2.326348, Z(0.9963212)=2.678(2) -> ~1.2653
    z2 = 2.6782
    beklenen = 0.5 * ((1 - 0.5772156649) * 2.326348 + 0.5772156649 * z2)
    assert sg.beklenen_maks_sr(100, 0.25) == pytest.approx(beklenen, abs=2e-3)
    assert sg.beklenen_maks_sr(1, 0.25) == 0.0
    assert sg.beklenen_maks_sr(1000, 0.25) > sg.beklenen_maks_sr(100, 0.25)


def test_dsr_deneme_sayisi_arttikca_duser():
    rng = np.random.default_rng(0)
    x = rng.normal(0.001, 0.01, 1000)
    v = 0.0001
    a, b, c = (sg.deflated_sharpe(x, n, v)["dsr"] for n in (1, 30, 1000))
    assert a > b > c


# ---------------------------------------------------------------------------- parametre komşuları, rejim
def test_komsu_parametreler():
    izgara = {"periyot": [10, 14, 20], "k": [1.5, 2.0, 2.5]}
    par = {"periyot": 14, "k": 1.5, "bayrak": True, "mod": "x", "sabit": 50, "sifir": 0}
    k = sg.komsu_parametreler(par, izgara)
    assert ("periyot", -1, 10) in k and ("periyot", 1, 20) in k
    assert ("k", 1, 2.0) in k and not any(a == "k" and y < 0 for a, y, _ in k)       # ızgara ucu: tek komşu
    assert not any(a in ("bayrak", "mod", "sifir") for a, _, _ in k)
    assert ("sabit", -1, 40) in k and ("sabit", 1, 60) in k                            # ızgarada yok: +-%20


def test_rejim_nedensel_ve_siniflama():
    n = 600
    idx = pd.date_range("2021-01-01", periods=n, freq="1D", tz="UTC")
    kap = np.r_[np.linspace(100, 200, 300), np.linspace(200, 80, 300)]
    mum = pd.DataFrame({"acilis": kap, "yuksek": kap, "dusuk": kap, "kapanis": kap, "hacim": 1.0}, index=idx)
    rej = sg.gunluk_rejim(mum)
    assert rej.iloc[150] == "belirsiz"                                  # SMA200 + eğim henüz yok
    assert rej.iloc[280] == "boga" and rej.iloc[590] == "ayi"
    # nedensellik: bugünün kapanışı değişse de bugünün rejim etiketi değişmez
    mum2 = mum.copy()
    mum2.iloc[280, :4] = 1.0
    assert sg.gunluk_rejim(mum2).iloc[280] == rej.iloc[280]
    et = sg.rejim_etiketle(rej, [idx[280] + pd.Timedelta(hours=5)])
    assert et[0] == rej.iloc[280]


def test_oneri_kurali():
    ok = dict(m2_pf=1.2, rnd_p=0.01, pf_boot_alt=1.1, par_oran=0.8)
    assert sg.oneri(ok) == (True, "")
    assert sg.oneri({**ok, "m2_pf": 1.04})[1] == "K1_maliyet2_pf"
    assert sg.oneri({**ok, "rnd_p": 0.06})[1] == "K2_rastgele_p"
    assert sg.oneri({**ok, "pf_boot_alt": 1.0})[1] == "K3_boot_alt"
    assert sg.oneri({**ok, "par_oran": 0.59})[1] == "K4_komsu_param"
    assert sg.oneri({**ok, "par_oran": math.nan})[0] is False


def test_gunluk_getiri_wf_sharpe_ile_ayni():
    t0 = pd.Timestamp("2022-01-01", tz="UTC")
    rng = np.random.default_rng(1)
    giris = t0 + pd.to_timedelta(np.sort(rng.integers(0, 300, 60)), "D")
    oos = pd.DataFrame({"giris_zamani": giris, "cikis_zamani": giris + pd.Timedelta("12h"),
                        "r": rng.normal(0.1, 1, 60), "yon": 1})
    bit = t0 + pd.Timedelta(days=360)
    g = sg.gunluk_getiri(oos, t0, bit)
    m = wf.oos_metrikleri(oos, t0, bit)
    assert g.mean() / g.std(ddof=1) * math.sqrt(365) == pytest.approx(m["sharpe"])


# ---------------------------------------------------------------------------- maliyet çarpanı
def test_maliyet_carpani_ayarlari_ikiye_katlar():
    k = SembolKurallari()
    a1, a2 = wf.maliyet_ayarlari(k, 1.0), wf.maliyet_ayarlari(k, 2.0)
    assert a1 == MotorAyarlari(limit_modu="olc", kurallar=k)           # 1.0 = eski davranış
    for alan in ("komisyon_taker_yuzde", "komisyon_maker_yuzde", "kayma_bps", "stop_kayma_bps"):
        assert getattr(a2, alan) == pytest.approx(2 * getattr(a1, alan))
    assert a2.risk_yuzde == a1.risk_yuzde and a2.kaldirac == a1.kaldirac
    with pytest.raises(ValueError):
        wf.maliyet_ayarlari(k, 0.0)
    assert "maliyet_carpani" in inspect.signature(wf.wf_tara).parameters


def test_maliyet_carpani_motorda_gercek_maliyeti_ikiye_katlar():
    """Düz fiyat: işlemin tüm kaybı komisyon + kayma. Birim miktar başına net kayıp x2 olmalı."""
    df = mumlar_yap([(100, 100, 100, 100)] * 6)
    sig = sinyal_yap(df, {0: (1, 90.0, np.nan)}, cikislar=[3])
    k = SembolKurallari()
    net = []
    for c in (1.0, 2.0):
        r = backtest(df, Hazir(sig), wf.maliyet_ayarlari(k, c))
        t = r.islemler.iloc[0]
        net.append(-t.net_pnl / t.miktar)
    assert net[0] > 0
    assert net[1] / net[0] == pytest.approx(2.0, rel=1e-6)


# ---------------------------------------------------------------------------- seanslı (DK_ tipi) veri
def _seansli(n_gun=500):
    """Hafta içi, 7 saatlik seans (14-20 UTC), hafta sonu ve tatil boşluklu 1s mum; gürültülü yürüyüş."""
    rng = np.random.default_rng(5)
    gunler = pd.bdate_range("2021-01-04", periods=n_gun, tz="UTC")
    gunler = gunler.delete(np.arange(37, n_gun, 60))                      # tatil boşlukları
    idx = pd.DatetimeIndex([g + pd.Timedelta(hours=h) for g in gunler for h in range(14, 21)], name="zaman")
    kap = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, len(idx))))
    ac = np.r_[100.0, kap[:-1]]
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) * 1.001, "dusuk": np.minimum(ac, kap) * 0.999,
                         "kapanis": kap, "hacim": 1.0}, index=idx)


def test_seansli_veride_rastgele_giris_ve_rejim_calisir():
    from motor.veri.yeniden_ornekle import yeniden_ornekle
    m = _seansli()
    m = m.assign(quote_hacim=1.0, islem_sayisi=1)
    gun = yeniden_ornekle(m, "1d", kaynak="1h", eksikleri_at=True, esik_orani=0.25)
    for mum in (m, gun):
        atr = gst.atr(mum["yuksek"], mum["dusuk"], mum["kapanis"], 14).to_numpy(float)
        j = np.array([40, 90, 140, 190])
        oos = pd.DataFrame({"yon": [1, -1, 1, -1], "giris_zamani": mum.index[j], "cikis_zamani": mum.index[j + 5],
                            "miktar": 1.0, "net_pnl": 1.0, "r": 0.1})
        tanim = sg.islem_tanimlari(mum, oos, atr)
        uygun = _uygun(mum, atr)
        rs = sg.rastgele_giris(mum, tanim, uygun, AYAR, n_sim=200, seed=1)
        assert len(rs["toplam_r"]) == 200 and np.isfinite(rs["toplam_r"]).all()
        rej = sg.gunluk_rejim(mum)
        et = sg.rejim_etiketle(rej, oos["giris_zamani"])
        assert len(et) == 4 and set(et) <= {"boga", "ayi", "yatay", "belirsiz"}


def test_islem_tanimlari_indekste_olmayan_giris_acik_hata():
    mum = _seansli()
    atr = gst.atr(mum["yuksek"], mum["dusuk"], mum["kapanis"], 14).to_numpy(float)
    oos = pd.DataFrame({"yon": [1], "giris_zamani": [mum.index[50] + pd.Timedelta(minutes=30)],
                        "cikis_zamani": [mum.index[55]], "miktar": [1.0], "net_pnl": [1.0], "r": [0.1]})
    with pytest.raises(ValueError, match="mum indeksinde yok"):
        sg.islem_tanimlari(mum, oos, atr)


def test_parametre_duyarlilik_islemsiz_ayarda_coker_degil(monkeypatch):
    """İşlemsiz backtest boş/naive giris_zamani üretir; UTC Timestamp ile kıyas TypeError vermemeli."""
    class _S:
        parametre_izgarasi = {}
        parametreler = {}
    class _R:
        islemler = pd.DataFrame({"giris_zamani": pd.Series([], dtype="datetime64[s]"), "r": pd.Series([], dtype=float)})
    monkeypatch.setattr(sg, "ayar_coz", lambda ad, e: _S())
    monkeypatch.setattr(sg, "backtest", lambda *a, **k: _R())
    out = sg._parametre_duyarlilik("x", "varsayilan", _seansli(), None, AYAR, pd.Timestamp("2021-06-01", tz="UTC"),
                                   pd.Timestamp("2022-01-01", tz="UTC"))
    assert out["par_merkez_islem"] == 0 and math.isnan(out["par_merkez_pf"])
