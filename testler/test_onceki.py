"""onceki paketi (arsivden alınan 4 aday): lookahead, sentetik senaryo, stop tarafı, ust_zaman, gün sonu."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import CikisYokHatasi, MotorAyarlari, backtest
from motor.strateji import gostergeler as g
from motor.strateji.onceki.kapitulasyon import Kapitulasyon
from motor.strateji.onceki.kgt import Kgt
from motor.strateji.onceki.kirilim_4s import Kirilim4S
from motor.strateji.onceki.s1_geri_cekilme import S1GeriCekilme


# ----------------------------------------------------------------------------- yardımcılar
def rastgele(n, freq, seed=3, vol=0.01, baslangic="2022-01-03"):       # 2022-01-03 Pazartesi
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0002, vol, n)))
    ac = np.r_[kap[0], kap[:-1]]
    yuk = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.004, n))
    dus = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.004, n))
    idx = pd.date_range(baslangic, periods=n, freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yuk, "dusuk": dus, "kapanis": kap,
                         "hacim": rng.uniform(1, 3, n)}, index=idx)


def mumlar_kapanistan(kap, freq, genlik=0.1, hacim=1.0, baslangic="2022-01-03"):
    kap = np.asarray(kap, dtype=float)
    ac = np.r_[kap[0], kap[:-1]]
    idx = pd.date_range(baslangic, periods=len(kap), freq=freq, tz="UTC", name="zaman")
    hc = np.broadcast_to(np.asarray(hacim, dtype=float), kap.shape).copy()
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, kap) + genlik, "dusuk": np.minimum(ac, kap) - genlik,
                         "kapanis": kap, "hacim": hc}, index=idx)


def sine_gunleri(gun=60, buyume=0.005, A=0.8, mid0=100.0):
    """1h mumlar: her gün mid + A*sin(2 pi t/24); mid günde %buyume artar (dar CPR'li yükseliş trendi)."""
    n = gun * 24
    t = np.arange(n)
    mid = mid0 * (1 + buyume) ** (t // 24)
    kap = mid + A * np.sin(2 * np.pi * (t % 24) / 24)
    return mumlar_kapanistan(kap, "1h", genlik=0.05)


STRATEJILER = [
    (Kirilim4S(), "4h", 2600), (Kirilim4S(hacim_k=0.0, sikisma=0.9, kapanis_konum=0.6, cikis_kanal=20), "4h", 2600),
    (Kirilim4S(donchian=10, hacim_k=0.0, gunluk_ema=20, ema_trend=30), "4h", 2600),
    (Kgt(), "1h", 3200), (Kgt(short=True, cpr_esik=0.6, gun_sonu_kapat=True), "1h", 3200),
    (Kgt(short=True, cpr_esik=0.6, stop_modu="atr"), "1h", 3200),
    (S1GeriCekilme(), "1d", 1500), (S1GeriCekilme(short=True, rsi_esik=75.0), "1d", 1500),
    (Kapitulasyon(esik=0.05), "1h", 3000), (Kapitulasyon(esik=0.03, pencere=12), "1h", 3000),
]


def kimlik(x):
    s, tf, n = x
    return f"{s.ad}-{s.parametreler}"[:90]


# ----------------------------------------------------------------------------- sözleşme / stop tarafı
@pytest.mark.parametrize("s,tf,n", STRATEJILER, ids=[kimlik(x) for x in STRATEJILER])
def test_sozlesme_ve_stop_tarafi(s, tf, n):
    df = rastgele(n, tf.replace("d", "D") if tf.endswith("d") else tf, vol=0.012 if tf != "1d" else 0.025)
    sig = s.sinyaller(df)
    assert sig.index.equals(df.index)
    assert {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)
    assert sig["cikis"].dtype == bool
    giris = sig[sig.yon != 0]
    assert len(giris) > 0, "sentetik veride hiç sinyal yok: test boş kalmasın"
    assert giris["stop"].notna().all()
    k = df["kapanis"]
    ml, ms = sig.yon == 1, sig.yon == -1
    assert (sig.stop[ml] < k[ml]).all()
    assert (sig.stop[ms] > k[ms]).all()
    assert sig["hedef"].isna().all()
    assert s.cikis_var_mi()


# ----------------------------------------------------------------------------- lookahead
@pytest.mark.parametrize("s,tf,n", STRATEJILER, ids=[kimlik(x) for x in STRATEJILER])
def test_lookahead_kesme(s, tf, n):
    df = rastgele(n, tf.replace("d", "D") if tf.endswith("d") else tf, vol=0.012 if tf != "1d" else 0.025)
    tam = s.sinyaller(df)
    for k in (int(n * 0.45) + 1, int(n * 0.7) + 5, int(n * 0.93) + 7):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:k]), tam.iloc[:k])


def _gelecegi_boz(df, k, bitis):
    """k'dan SONRAKİ (k+1..bitis-1) mumların fiyatlarını değiştirir; üst TF mumu henüz kapanmamıştır."""
    d2 = df.copy()
    d2.iloc[k + 1:bitis, d2.columns.get_indexer(["acilis", "yuksek", "dusuk", "kapanis"])] *= 3.0
    return d2


def _bitis(df, k, aralik):
    """k. mumun ait olduğu üst TF periyodunun bittiği satır (dışlayıcı)."""
    t = df.index[k]
    son = t.floor("D") + pd.Timedelta(days=1) if aralik == "1d" else \
        t.floor("4h") + pd.Timedelta(hours=4) if aralik == "4h" else \
        (t.floor("D") - pd.Timedelta(days=t.dayofweek)) + pd.Timedelta(days=7)
    return int(df.index.searchsorted(son))


@pytest.mark.parametrize("s,tf,n,aralik", [
    (Kirilim4S(hacim_k=0.0), "4h", 2600, "1d"),
    (Kgt(), "1h", 3200, "1d"),
    (Kgt(), "1h", 3200, "4h"),
    (S1GeriCekilme(), "1d", 1500, "1w"),
    (Kapitulasyon(esik=0.03, pencere=12), "1h", 3000, "4h"),
], ids=["4s-gunluk", "kgt-gunluk", "kgt-4s", "s1-haftalik", "kap-4s"])
def test_ust_zaman_kapanmamis_mum_kullanilmaz(s, tf, n, aralik):
    """Üst TF periyodu bitmeden sonraki mumları değiştirmek, o ana kadarki sinyalleri DEĞİŞTİRMEMELİ."""
    df = rastgele(n, tf.replace("d", "D") if tf.endswith("d") else tf, vol=0.012 if tf != "1d" else 0.025)
    tam = s.sinyaller(df)
    sayac = 0
    for k0 in (int(n * 0.5), int(n * 0.75), int(n * 0.9)):
        # periyodun ortasında bir satır seç
        k = next(i for i in range(k0, k0 + 200) if _bitis(df, i, aralik) - i >= 2)
        d2 = _gelecegi_boz(df, k, _bitis(df, k, aralik))
        pdt.assert_frame_equal(s.sinyaller(d2).iloc[:k + 1], tam.iloc[:k + 1])
        sayac += 1
    assert sayac == 3


def test_gunluk_filtre_gunun_kapanisini_beklemez():
    """4s-kirilim: günlük kapanış < EMA ise gün içinde fiyat EMA üstüne çıksa bile long yok; gün kapanınca (ertesi
    gün) filtre açılır."""
    kap = np.r_[np.linspace(100, 80, 40 * 6), np.full(6, 80.0)]          # 40 gün düşüş, günlük kapanış < EMA
    df = mumlar_kapanistan(kap, "4h", genlik=0.05, hacim=1.0)
    # son gün (6 mum): son 2 mum sert yükselir -> gün içi kapanış EMA(5) üstü, ama günlük mum henüz kapanmadı
    k2 = kap.copy()
    k2[-2:] = [95.0, 99.0]
    df2 = mumlar_kapanistan(k2, "4h", genlik=0.05, hacim=1.0)
    s = Kirilim4S(donchian=5, hacim_k=0.0, ema_trend=0, gunluk_ema=5, short=False)
    sig = s.sinyaller(df2)
    assert (sig.yon.iloc[-6:] == 0).all()          # gün bitmeden filtre kapalı
    # ertesi gün başı mumu: dünkü günlük kapanış 99 > EMA5 -> filtre açık; kırılım hâlâ sürüyorsa long olabilir
    k3 = np.r_[k2, [100.0, 101.0]]
    sig3 = s.sinyaller(mumlar_kapanistan(k3, "4h", genlik=0.05, hacim=1.0))
    assert sig3.yon.iloc[-2] == 1 or sig3.yon.iloc[-1] == 1


# ----------------------------------------------------------------------------- 4s-kirilim senaryosu
def _yatay(n=300):
    return 100 + 0.2 * np.sin(np.arange(n))


def test_4s_kirilim_hacimli_long_ve_olay_kurali():
    kap = _yatay()
    kap[250] = 105.0
    kap[251] = 106.0
    hc = np.ones(300)
    hc[250] = hc[251] = 5.0
    df = mumlar_kapanistan(kap, "4h", genlik=0.1, hacim=hc)
    s = Kirilim4S(ema_trend=20, gunluk_ema=0, short=True)
    sig = s.sinyaller(df)
    assert sig.yon.iloc[250] == 1
    assert sig.yon.iloc[251] == 0                        # olay kuralı: devam eden kırılımda yeni sinyal yok
    assert (sig.yon.drop(sig.index[250]) == 0).all()
    atr = g.atr(df.yuksek, df.dusuk, df.kapanis, 14)
    assert sig.stop.iloc[250] == pytest.approx(105.0 - 2.0 * atr.iloc[250])
    assert sig.zaman_cikisi_mum.iloc[250] == 180
    # hacim yetersiz -> sinyal yok
    df_dusuk = mumlar_kapanistan(kap, "4h", genlik=0.1, hacim=1.0)
    assert (s.sinyaller(df_dusuk).yon == 0).all()
    assert (Kirilim4S(ema_trend=20, gunluk_ema=0, hacim_k=0.0).sinyaller(df_dusuk).yon.iloc[250] == 1)


def test_4s_kirilim_short_ayna_ve_kapali():
    kap = _yatay()
    kap[250] = 95.0
    hc = np.ones(300)
    hc[250] = 5.0
    df = mumlar_kapanistan(kap, "4h", genlik=0.1, hacim=hc)
    sig = Kirilim4S(ema_trend=20, gunluk_ema=0).sinyaller(df)
    assert sig.yon.iloc[250] == -1 and sig.stop.iloc[250] > 95.0
    assert (Kirilim4S(ema_trend=20, gunluk_ema=0, short=False).sinyaller(df).yon == 0).all()


def test_4s_ema_cikis_yonlu():
    """Long pozisyon: kapanış EMA altına inince cikis; short pozisyon aynı barlarda cikis olmaz."""
    kap = _yatay()
    kap[250] = 105.0
    hc = np.ones(300)
    hc[250] = 5.0
    kap[251:] = np.linspace(105.0, 90.0, 49)
    df = mumlar_kapanistan(kap, "4h", genlik=0.1, hacim=hc)
    sig = Kirilim4S(ema_trend=20, gunluk_ema=0).sinyaller(df)
    assert sig.yon.iloc[250] == 1
    assert sig.cikis.iloc[251:].any() and not sig.cikis.iloc[:250].any()


# ----------------------------------------------------------------------------- kapitülasyon
def test_kapitulasyon_senaryo():
    kap = np.full(600, 100.0) + 0.1 * np.sin(np.arange(600))
    kap[500:524] = np.linspace(100.0, 80.0, 24)          # 24 mumda -%20
    kap[524:] = 80.0
    df = mumlar_kapanistan(kap, "1h", genlik=0.05)
    sig = Kapitulasyon().sinyaller(df)
    ilk = sig.index[sig.yon == 1][0]
    assert df.index.get_loc(ilk) >= 500
    assert (sig.yon.iloc[:500] == 0).all()
    assert sig.yon.iloc[520] == 1                          # -%16'dan beri sinyal
    assert (sig.loc[sig.yon == 1, "stop"] < df.kapanis[sig.yon == 1]).all()
    assert (sig.zaman_cikisi_mum[sig.yon == 1] == 96).all()
    # -%10 düşüş eşiği geçmez
    kap2 = np.full(600, 100.0) + 0.1 * np.sin(np.arange(600))
    kap2[500:524] = np.linspace(100.0, 90.0, 24)
    kap2[524:] = 90.0
    assert (Kapitulasyon().sinyaller(mumlar_kapanistan(kap2, "1h", genlik=0.05)).yon == 0).all()
    assert (Kapitulasyon(esik=0.08).sinyaller(mumlar_kapanistan(kap2, "1h", genlik=0.05)).yon == 1).any()


def test_kapitulasyon_cikis_yok_hatasi():
    s = Kapitulasyon(max_mum=0)
    assert not s.cikis_var_mi()
    with pytest.raises(CikisYokHatasi):
        backtest(mumlar_kapanistan(_yatay(400), "1h"), s)


# ----------------------------------------------------------------------------- KGT
def _kgt_referans(df, p):
    """Bağımsız referans: pivotlar gün gruplamasıyla, 'önceki gün' shift(1) ile (ust_zaman kullanmadan)."""
    gun = df.index.floor("D")
    d = df.groupby(gun).agg(h=("yuksek", "max"), l=("dusuk", "min"), c=("kapanis", "last"))
    pv = (d.h + d.l + d.c) / 3
    bc = (d.h + d.l) / 2
    tc = 2 * pv - bc
    gen = (np.maximum(tc, bc) - np.minimum(tc, bc))
    datr = g.atr(d.h, d.l, d.c, 14)
    eh, ey = g.ema(d.c, p["gunluk_hizli"]), g.ema(d.c, p["gunluk_yavas"])
    trend_up = (eh > ey) & (d.c > ey)
    ref = pd.DataFrame({"r1": 2 * pv - d.l, "dar": gen <= p["cpr_esik"] * datr, "up": trend_up}).shift(1)
    x = ref.reindex(gun)
    x.index = df.index
    kap = df.kapanis
    saat = df.index.hour
    ham = ((x.dar == True) & (x.up == True) & (kap > x.r1) & (kap.shift(1) <= x.r1) & (saat < p["pencere_bit"]))  # noqa: E712
    sira = ham.astype(int).groupby(gun).cumsum()
    return ham & (sira <= p["gunluk_max"])


def test_kgt_senaryo_ve_bagimsiz_referans():
    df = sine_gunleri(60)
    s = Kgt()
    sig = s.sinyaller(df)
    beklenen = _kgt_referans(df, s.parametreler)
    assert beklenen.sum() > 5
    assert ((sig.yon == 1) == beklenen).all()
    assert (sig.yon != -1).all()                                   # short kapalı
    # günde en çok bir giriş
    assert sig[sig.yon == 1].groupby(sig[sig.yon == 1].index.floor("D")).size().max() == 1
    # stop: kapanış - 3 x ATR14(1s) (kırpılmış üst sınır) ya da daha yakın; alt sınır 0.75 ATR
    atr = g.atr(df.yuksek, df.dusuk, df.kapanis, 14)
    mesafe = (df.kapanis - sig.stop)[sig.yon == 1] / atr[sig.yon == 1]
    assert (mesafe <= 3.0 + 1e-9).all() and (mesafe >= 0.75 - 1e-9).all()
    # geniş CPR eşiği çok dar -> sinyal yok
    assert (Kgt(cpr_esik=0.001).sinyaller(df).yon == 0).all()
    # 20 saat penceresi: 20:00 ve sonrası açılan mumlarda giriş yok
    assert (sig[sig.yon == 1].index.hour < 20).all()


def test_kgt_dusus_trendinde_long_yok_short_ayna():
    df = sine_gunleri(60, buyume=-0.005)
    assert (Kgt().sinyaller(df).yon == 0).all()
    sig = Kgt(short=True).sinyaller(df)
    assert (sig.yon == -1).sum() > 5 and (sig.yon == 1).sum() == 0
    assert (sig.loc[sig.yon == -1, "stop"] > df.kapanis[sig.yon == -1]).all()


def test_kgt_gun_sonu_kapat():
    df = sine_gunleri(60)
    acik = Kgt(pencere_bit=24, gun_sonu_kapat=False).sinyaller(df)
    kapali = Kgt(pencere_bit=24, gun_sonu_kapat=True).sinyaller(df)
    son = df.index.hour == 23
    assert kapali.cikis[son].all()                              # UTC gün sonu mumunda cikis
    assert (kapali.yon[son] == 0).all()                         # gün sonu mumunda yeni giriş yok
    assert not acik.cikis[son].all()                            # kapalıyken zorlama yok (4S trend yukarı)
    pdt.assert_series_equal(kapali.yon[~son], acik.yon[~son])


def test_kgt_gun_sonu_backtest_ayni_gun_kapanir():
    df = sine_gunleri(80)
    ay = MotorAyarlari(limit_modu="olc")
    uzak = dict(stop_modu="atr", stop_max_atr=20.0)          # stop gün içinde vurulmasın: çıkışı gün sonu belirlesin
    t = backtest(df, Kgt(gun_sonu_kapat=True, **uzak), ay).islemler
    assert len(t) > 5
    sure = t.cikis_zamani - t.giris_zamani
    assert (sure <= pd.Timedelta(hours=24)).all()
    assert (t.cikis_zamani.dt.floor("D") - t.giris_zamani.dt.floor("D") <= pd.Timedelta(days=1)).all()
    t_ic = t[t.cikis_nedeni != "veri_sonu"]
    assert (t_ic.cikis_nedeni == "sinyal").all() and (t_ic.cikis_zamani.dt.hour == 0).all()
    # kapalı: gün sonu zorlaması yok; pozisyon günlerce taşınır (4S trend hep yukarı, stop uzak)
    ta = backtest(df, Kgt(gun_sonu_kapat=False, **uzak), ay).islemler
    assert (ta.cikis_zamani - ta.giris_zamani).max() > pd.Timedelta(hours=24)


def test_kgt_4s_trend_cikisi():
    """4S EMA21<EMA50 ve kapanış<EMA21 -> long için cikis (short pozisyonda değil)."""
    kap = np.r_[np.linspace(100, 200, 1200), np.linspace(200, 100, 1200)]
    df = mumlar_kapanistan(kap, "1h", genlik=0.05)
    # yön için bir giriş sinyali gerekir: yapay olarak son girişin yönünü long say
    s = Kgt(cpr_esik=100.0, pencere_bit=24)      # CPR filtresi pratikte kapalı
    sig = s.sinyaller(df)
    assert (sig.yon == 1).any()
    assert sig.cikis.iloc[1200:].any() and not sig.cikis.iloc[:1000].any()


# ----------------------------------------------------------------------------- S1
def test_s1_yukselis_geri_cekilme_senaryosu():
    n = 500
    t = np.arange(n)
    kap = 100 * 1.004 ** t
    for baslangic in range(300, 480, 20):                    # 3 günlük geri çekilme sonra güçlü dönüş
        kap[baslangic:baslangic + 3] *= np.array([0.985, 0.97, 0.965])
        kap[baslangic + 3] *= 1.02
        kap[baslangic + 4:] = kap[baslangic + 4:] * (kap[baslangic + 3] / (100 * 1.004 ** (baslangic + 3)))
    df = mumlar_kapanistan(kap, "1D", genlik=0.2)
    s = S1GeriCekilme(rsi_esik=90.0, temas_atr=1.0)
    sig = s.sinyaller(df)
    assert (sig.yon == 1).sum() >= 2
    # her sinyal: günlük trend + tetik (önceki gün yükseğinin üstünde kapanış) + stop altında
    eh, ey = g.ema(df.kapanis, s.parametreler["hizli"]), g.ema(df.kapanis, s.parametreler["yavas"])
    m = sig.yon == 1
    assert (df.kapanis[m] > ey[m]).all() and (eh[m] > ey[m]).all()
    assert (df.kapanis[m] > df.yuksek.shift(1)[m]).all() and (df.kapanis[m] > eh[m]).all()
    assert (sig.zaman_cikisi_mum[m] == 30).all()
    # bağımsız haftalık yön referansı: HA yeşil ve kapanış > SMA20(hafta); Pazartesi'den itibaren
    w = df.resample("W-SUN").agg({"acilis": "first", "yuksek": "max", "dusuk": "min", "kapanis": "last"})
    hc = (w.acilis + w.yuksek + w.dusuk + w.kapanis) / 4
    ho = [(w.acilis.iloc[0] + w.kapanis.iloc[0]) / 2]
    for i in range(1, len(w)):
        ho.append((ho[-1] + hc.iloc[i - 1]) / 2)
    yesil = (hc > pd.Series(ho, index=w.index)) & (w.kapanis > g.sma(w.kapanis, 20))
    yesil.index = yesil.index + pd.Timedelta(days=1)
    yesil_g = yesil.reindex(df.index, method="ffill").fillna(False)
    assert yesil_g[m].all()


def test_s1_dusus_trendinde_long_yok_ve_short_ayna():
    n = 500
    kap = 400 * 0.996 ** np.arange(n)
    for baslangic in range(300, 480, 20):
        kap[baslangic:baslangic + 3] *= np.array([1.015, 1.03, 1.035])
        kap[baslangic + 3] *= 0.98
        kap[baslangic + 4:] = kap[baslangic + 4:] * (kap[baslangic + 3] / (400 * 0.996 ** (baslangic + 3)))
    df = mumlar_kapanistan(kap, "1D", genlik=0.2)
    assert (S1GeriCekilme(rsi_esik=90.0, temas_atr=1.0).sinyaller(df).yon == 1).sum() == 0
    sig = S1GeriCekilme(rsi_esik=90.0, temas_atr=1.0, short=True).sinyaller(df)
    assert (sig.yon == -1).sum() >= 1
    assert (sig.loc[sig.yon == -1, "stop"] > df.kapanis[sig.yon == -1]).all()


# ----------------------------------------------------------------------------- motorla uçtan uca
@pytest.mark.parametrize("s,tf,n", STRATEJILER[::2], ids=[kimlik(x) for x in STRATEJILER[::2]])
def test_backtest_calisir(s, tf, n):
    df = rastgele(n, tf.replace("d", "D") if tf.endswith("d") else tf, vol=0.012 if tf != "1d" else 0.025)
    r = backtest(df, s, MotorAyarlari(limit_modu="olc"))
    assert len(r.islemler) > 0
    assert np.isfinite(r.ozsermaye.iloc[-1])


def test_izgara_ve_parametreler():
    for S in (Kirilim4S, Kgt, S1GeriCekilme, Kapitulasyon):
        n = 1
        for k, v in S.parametre_izgarasi.items():
            assert k in S.varsayilan_parametreler
            n *= len(v)
        assert n <= 27
        S(**{k: v[0] for k, v in S.parametre_izgarasi.items()})
    assert Kirilim4S.ad == "onceki__4s-kirilim" and Kirilim4S.stil == "swing"
    assert Kgt.ad == "onceki__kgt" and Kgt.stil == "daytrade"
    assert S1GeriCekilme.ad == "onceki__s1-geri-cekilme" and S1GeriCekilme.stil == "swing"
    assert Kapitulasyon.ad == "onceki__kapitulasyon" and Kapitulasyon.stil == "swing"
    with pytest.raises(ValueError):
        Kgt(yok=1)
