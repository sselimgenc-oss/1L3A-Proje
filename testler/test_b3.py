"""B3 aileleri: baş-omuz, bayrak-flama, Elliott, elmas, Gann fan, harmonik ABCD, çoklu mum, pin bar, Renko S/R.
Lookahead, elle kurgulanmış formasyon, stop/hedef tarafı, long/short kapatma, gün sonu, ızgara, kart ayarları, hız."""
import itertools
import json
import pathlib
import time

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji import formasyon_b3 as fb
from motor.strateji.daytrade._ortak import seans_kimligi
from motor.strateji.daytrade.bayrak_flama import BayrakFlama as DtBayrak
from motor.strateji.daytrade.elliott_dalga import ElliottDalga
from motor.strateji.daytrade.pin_bar import PinBar as DtPinBar
from motor.strateji.daytrade.renko_sr import RenkoSr
from motor.strateji.pivotlar import pivot_tablosu
from motor.strateji.scalp.bas_omuz import BasOmuz as ScBasOmuz
from motor.strateji.swing.bas_omuz import BasOmuz
from motor.strateji.swing.bayrak_flama import BayrakFlama
from motor.strateji.swing.elmas_formasyon import ElmasFormasyon
from motor.strateji.swing.gann_fan import GannFan
from motor.strateji.swing.harmonik_abcd import HarmonikAbcd
from motor.strateji.swing.mum_coklu_formasyon import MumCokluFormasyon
from motor.strateji.swing.pin_bar import PinBar

KOK = pathlib.Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------ veri üreticileri

def fitilli(n=4000, seed=2, freq="1h"):
    """Üstel fitilli rastgele yürüyüş (pin bar / formasyon adayları çıksın diye)."""
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    ac = np.r_[kap[0], kap[:-1]]
    yu = np.maximum(ac, kap) * (1 + rng.exponential(0.004, n))
    du = np.minimum(ac, kap) * (1 - rng.exponential(0.004, n))
    idx = pd.date_range("2022-01-01", periods=n, freq=freq, tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yu, "dusuk": du, "kapanis": kap,
                         "hacim": rng.uniform(1, 3, n)}, index=idx)


def yoldan(kapanislar, w=0.3, hacim=1.0):
    k = np.asarray(kapanislar, float)
    ac = np.r_[k[0], k[:-1]]
    idx = pd.date_range("2024-01-01", periods=len(k), freq="1h", tz="UTC")
    return pd.DataFrame({"acilis": ac, "yuksek": np.maximum(ac, k) + w, "dusuk": np.minimum(ac, k) - w,
                         "kapanis": k, "hacim": hacim}, index=idx)


def yol(*parcalar):
    cikti = [parcalar[0]]
    for hedef, adim in parcalar[1:]:
        cikti += list(np.linspace(cikti[-1], hedef, adim + 1)[1:])
    return cikti


def isin(n, seviye=100.0, gen=0.3):
    return list(seviye + gen * np.sin(np.arange(n) * 0.9))


def ohlc(satirlar, hacim=1.0):
    a = np.array(satirlar, float)
    idx = pd.date_range("2024-01-01", periods=len(a), freq="1h", tz="UTC")
    return pd.DataFrame({"acilis": a[:, 0], "yuksek": a[:, 1], "dusuk": a[:, 2], "kapanis": a[:, 3],
                         "hacim": hacim}, index=idx)


def aynala(df, eksen=200.0):
    return pd.DataFrame({"acilis": eksen - df.acilis, "yuksek": eksen - df.dusuk, "dusuk": eksen - df.yuksek,
                         "kapanis": eksen - df.kapanis, "hacim": df.hacim}, index=df.index)


def girisler(sig):
    return sig[sig.yon != 0]


# ------------------------------------------------------------------ genel testler

STRATEJILER = [
    BasOmuz(), BasOmuz(pivot_yontemi="fraktal", sim_tol=0.6), ScBasOmuz(),
    BayrakFlama(), BayrakFlama(direk_min_atr=3.0, hacim_k=1.2, ust_tf="4h"),
    DtBayrak(), DtBayrak(direk_min_atr=3.0, bayrak_min=4, bayrak_maks=10),
    ElliottDalga(), ElliottDalga(dalga=4, zigzag_esik_k=2.0),
    ElmasFormasyon(), ElmasFormasyon(genis_oran=1.1, daralma_oran=0.9, min_yuk_atr=1.5, pencere=24),
    GannFan(), GannFan(cizgi_orani=0.5, olcek_atr=0.1),
    HarmonikAbcd(), HarmonikAbcd(ab_oran=0.786, zigzag_esik_k=2.0),
    MumCokluFormasyon(), MumCokluFormasyon(desenler="uc_cizgi,terk_bebek", trend_n=3),
    PinBar(), PinBar(teyit_n=2, trend_ema=50), PinBar(hedef_r=0.0, fitil_oran=2.5),
    DtPinBar(), DtPinBar(seviye_modu="gun", teyit_n=0),
    RenkoSr(), RenkoSr(rsi_alt=50.0, stoch_alt=50.0, ust_tf="4h", renko_k=0.75),
]


def _id(s):
    return f"{s.ad.split('__')[1]}-{abs(hash(str(s.parametreler))) % 997}"


@pytest.mark.parametrize("s", STRATEJILER, ids=_id)
def test_lookahead_yok(s):
    df = fitilli(4000, seed=2)
    tam = s.sinyaller(df)
    assert tam.index.equals(df.index) and {"yon", "stop", "hedef", "cikis"} <= set(tam.columns)
    for n in (700, 1500, 2400, 3300):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])


@pytest.mark.parametrize("s", STRATEJILER, ids=_id)
def test_stil_ad_ve_cikis(s):
    assert s.ad.startswith(s.stil + "__") and s.stil in ("swing", "daytrade", "scalp")
    assert s.cikis_var_mi() is True


def test_ad_stil_listesi():
    beklenen = {"scalp__bas-omuz", "swing__bas-omuz", "daytrade__bayrak-flama", "swing__bayrak-flama",
                "daytrade__elliott-dalga", "swing__elmas-formasyon", "swing__gann-fan", "swing__harmonik-abcd",
                "swing__mum-coklu-formasyon", "daytrade__pin-bar", "swing__pin-bar", "daytrade__renko-sr"}
    assert {s.ad for s in STRATEJILER} == beklenen


@pytest.mark.parametrize("s", STRATEJILER, ids=_id)
def test_stop_ve_hedef_dogru_tarafta(s):
    sayi = 0
    for tohum in (1, 2, 3):
        df = fitilli(4000, seed=tohum)
        sig = s.sinyaller(df)
        gir = girisler(sig)
        sayi += len(gir)
        assert gir.stop.notna().all()
        kap = df.kapanis[gir.index]
        assert (gir.stop[gir.yon == 1] < kap[gir.yon == 1]).all()
        assert (gir.stop[gir.yon == -1] > kap[gir.yon == -1]).all()
        h = gir.hedef.dropna()
        yon_h, kap_h = gir.yon[h.index], kap[h.index]
        assert (h[yon_h == 1] > kap_h[yon_h == 1]).all() and (h[yon_h == -1] < kap_h[yon_h == -1]).all()
        assert sig[sig.yon == 0].stop.isna().all()
    assert sayi > 0


@pytest.mark.parametrize("s", [x for x in STRATEJILER if x.parametreler["long"] and x.parametreler["short"]][::2],
                         ids=_id)
def test_long_short_kapatilabilir(s):
    df = fitilli(4000, seed=1)
    tam = s.sinyaller(df)
    sadece_long = s.yeni(short=False).sinyaller(df)
    sadece_short = s.yeni(long=False).sinyaller(df)
    assert (sadece_long.yon >= 0).all() and (sadece_short.yon <= 0).all()
    # kapatınca sinyaller yalnızca ilgili yönün alt kümesi
    assert ((tam.yon == 1) >= (sadece_long.yon == 1)).all()
    assert ((tam.yon == -1) >= (sadece_short.yon == -1)).all()


def test_parametre_izgarasi_sinirli():
    for s in STRATEJILER:
        assert 1 <= np.prod([len(v) for v in s.parametre_izgarasi.values()]) <= 27
        assert set(s.parametre_izgarasi) <= set(s.varsayilan_parametreler)
        for komb in itertools.islice(itertools.product(*s.parametre_izgarasi.values()), 4):
            s.yeni(**dict(zip(s.parametre_izgarasi, komb)))


def test_bilinmeyen_parametre_reddedilir():
    with pytest.raises(ValueError):
        BasOmuz(yok_boyle_bir_sey=1)
    with pytest.raises(ValueError):
        MumCokluFormasyon(desenler="yok").sinyaller(fitilli(300))


GUN_SONU = [DtBayrak(direk_min_atr=3.0), ElliottDalga(), DtPinBar(), DtPinBar(seviye_modu="gun", teyit_n=0),
            RenkoSr(rsi_alt=50.0, stoch_alt=50.0)]


@pytest.mark.parametrize("s", GUN_SONU, ids=_id)
def test_daytrade_gun_sonu(s):
    df = fitilli(3000, seed=2)
    sig = s.sinyaller(df)
    seans = pd.Series(seans_kimligi(df.index, s.parametreler["seans_saat"]), index=df.index)
    son = seans.ne(seans.shift(-1)) & seans.shift(-1).notna()
    assert son.sum() > 30 and sig.cikis[son].all() and (sig.yon[son] == 0).all()
    assert not sig.cikis.iloc[1:-1][~son.iloc[1:-1]].any()          # cikis yalnız gün sonunda
    assert (sig.yon != 0).any()


def test_swing_ve_scalp_gun_sonu_uygulamaz():
    df = fitilli(3000, seed=2)
    for s in (BasOmuz(), PinBar(), ScBasOmuz()):
        assert not s.sinyaller(df).cikis.any()


@pytest.mark.parametrize("s", [BasOmuz(), BayrakFlama(), DtBayrak(), ElliottDalga(), ElmasFormasyon(), GannFan(),
                               HarmonikAbcd(), MumCokluFormasyon(), PinBar(), DtPinBar(), RenkoSr(), ScBasOmuz()],
                         ids=_id)
def test_hiz_60k_mum(s):
    df = fitilli(60000, seed=7)
    t0 = time.time()
    s.sinyaller(df)
    assert time.time() - t0 < 10.0


# ------------------------------------------------------------------ yardımcılar

def test_ayna_ve_iki_yon_simetri():
    df = fitilli(500, seed=4)
    a = fb.ayna(df)
    assert np.allclose(a.yuksek, -df.dusuk) and np.allclose(a.dusuk, -df.yuksek)
    assert np.allclose(fb.ayna(a).kapanis, df.kapanis)


def test_renko_kurallari():
    kap = np.array([100, 100.5, 101.6, 102.0, 103.1, 102.0, 100.9, 99.9, 101.0, 102.2, 104.5])
    yon, yeni, dondu = fb.renko_serisi(kap, np.ones(len(kap)), 1.0)
    assert list(yon[:6]) == [0, 0, 1, 1, 1, 1]
    assert yeni[2] == 1 and yeni[3] == 1 and yeni[4] == 1 and yeni[5] == 0
    assert yeni[6] == -1 and dondu[6]            # 2 tuğla kuralı: 102 üst -> 100.9 ≤ alt(101)-0 ... dönüş
    assert yeni[9] == 1 and dondu[9]
    assert not dondu[:6].any()


def test_stoch_rsi_sinirli_ve_nedensel():
    df = fitilli(500, seed=4)
    s = fb.stoch_rsi(df.kapanis)
    assert s.dropna().between(-1e-9, 100 + 1e-9).all()
    pdt.assert_series_equal(fb.stoch_rsi(df.kapanis.iloc[:300]), s.iloc[:300])


# ------------------------------------------------------------------ baş-omuz

def test_ters_bas_omuz_long_ve_ayna_short():
    k = isin(30, 130) + yol(130, (100, 12), (112, 6), (94, 8), (112, 8), (100, 6), (111, 5), (114, 2))
    df = yoldan(k)
    for s in (BasOmuz(), ScBasOmuz(sag_omuz_filtre=0)):
        g = girisler(s.sinyaller(df))
        assert len(g) == 1 and g.yon.iloc[0] == 1
        t = df.index.get_loc(g.index[0])
        assert t >= 72                                        # D3 pivotu 70'te, onay 72
        assert df.kapanis.iloc[t] > 112.0                     # boyun çizgisi (~112.3) üstü kapanış
        assert abs(g.stop.iloc[0] - (100 - 0.25 * 2.9)) < 2.0  # sağ omuz dibi - tampon
        assert g.hedef.iloc[0] > 125                          # boyun + baş yüksekliği (~18)
        sh = girisler(s.sinyaller(aynala(df)))
        assert len(sh) == 1 and sh.yon.iloc[0] == -1 and sh.index[0] == g.index[0]
        assert sh.stop.iloc[0] > 200 - df.kapanis.iloc[t] and sh.hedef.iloc[0] < 200 - df.kapanis.iloc[t]


def test_bas_omuz_sinyal_formasyon_tamamlanmadan_yok():
    k = isin(30, 130) + yol(130, (100, 12), (112, 6), (94, 8), (112, 8), (100, 6))
    assert not girisler(BasOmuz().sinyaller(yoldan(k))).shape[0]


def test_bas_omuz_bas_omuzlardan_yeterince_dusuk_degilse_formasyon_degil():
    k = isin(30, 130) + yol(130, (100, 12), (112, 6), (101, 8), (112, 8), (100, 6), (111, 5), (114, 2))
    assert not len(girisler(BasOmuz().sinyaller(yoldan(k))))     # baş omuzlardan yalnız 1 puan düşük (< min_bas_atr*ATR)


def test_sag_omuz_filtresi():
    # sağ omuz (D3) başa soldan DAHA YAKIN: D1=100, D3=97 (baş 94) -> filtre açıkken reddedilir
    k = isin(30, 130) + yol(130, (100, 12), (112, 6), (94, 8), (112, 8), (97, 6), (111, 5), (114, 2))
    df = yoldan(k)
    assert len(girisler(BasOmuz(sim_tol=0.6, sag_omuz_filtre=0).sinyaller(df))) == 1
    assert len(girisler(BasOmuz(sim_tol=0.6, sag_omuz_filtre=1).sinyaller(df))) == 0


# ------------------------------------------------------------------ bayrak

def test_bayrak_kirilim_long_ve_ayna_short():
    k = isin(30, 100) + yol(100, (130, 10), (124, 8), (133, 3))
    df = yoldan(k)
    g = girisler(BayrakFlama().sinyaller(df))
    assert len(g) == 1 and g.yon.iloc[0] == 1
    t = df.index.get_loc(g.index[0])
    assert df.kapanis.iloc[t] > df.yuksek.iloc[t - 5:t].max()        # bayrak (en az 5 mum) tepesi üstü kapanış
    assert g.stop.iloc[0] < df.dusuk.iloc[t - 5:t].min()             # stop bayrak dibinin altı
    assert g.hedef.iloc[0] > df.kapanis.iloc[t] + 15                 # direk ~30 yüksekliğinde ölçü
    sh = girisler(BayrakFlama().sinyaller(aynala(df)))
    assert len(sh) == 1 and sh.yon.iloc[0] == -1


def test_bayrak_derin_geri_cekilme_formasyon_degil():
    k = isin(30, 100) + yol(100, (130, 10), (112, 8), (133, 3))      # derinlik %60 > %50
    assert not len(girisler(BayrakFlama(maks_derinlik=0.5).sinyaller(yoldan(k))))


def test_bayrak_kirilim_olmadan_sinyal_yok():
    k = isin(30, 100) + yol(100, (130, 10), (124, 8), (126, 3))
    assert not len(girisler(BayrakFlama().sinyaller(yoldan(k))))


def test_daytrade_bayrak_ust_tf_filtresi_ve_gun_sonu():
    # 1h; kırılım üst TF trendi yukarıyken alınır
    k = isin(60, 100) + yol(100, (130, 10), (124, 8), (133, 3))
    df = yoldan(k)
    s = DtBayrak(direk_min_atr=4.0, ust_tf="")
    assert len(girisler(s.sinyaller(df))) >= 1


# ------------------------------------------------------------------ Elliott

def test_elliott_dalga2_girisi():
    k = isin(30, 100) + yol(100, (120, 10), (108, 6), (132, 10), (150, 8), (138, 6), (160, 8))
    df = yoldan(k)
    g = girisler(ElliottDalga(dalga=2).sinyaller(df))
    assert len(g) >= 1 and (g.yon == 1).all()
    ilk = g.iloc[0]
    assert ilk.stop < 108 and ilk.stop > 100                       # swing dibi (108) altı, dalga başlangıcı üstü
    assert ilk.hedef > df.kapanis[g.index[0]]
    r = (ilk.hedef - df.kapanis[g.index[0]]) / (df.kapanis[g.index[0]] - ilk.stop)
    assert abs(r - 2.0) < 1e-6


def test_elliott_dalga4_girisi_ve_kurallar():
    k = isin(30, 100) + yol(100, (120, 10), (108, 6), (132, 10), (150, 8), (138, 6), (160, 8))
    g = girisler(ElliottDalga(dalga=4).sinyaller(yoldan(k)))
    assert len(g) == 1 and g.yon.iloc[0] == 1 and 130 < g.stop.iloc[0] < 138
    # dalga 4 dibi dalga 1 tepesinin (120) altına inerse dalga 4 girişi yok
    k2 = isin(30, 100) + yol(100, (120, 10), (108, 6), (132, 10), (150, 8), (115, 8), (160, 8))
    assert not len(girisler(ElliottDalga(dalga=4).sinyaller(yoldan(k2))))
    # dalga 2 başlangıcın (100) altına inerse dalga 2 girişi yok
    k3 = isin(30, 100) + yol(100, (120, 10), (97, 6), (132, 10))
    assert not len(girisler(ElliottDalga(dalga=2).sinyaller(yoldan(k3))))


def test_elliott_short_ayna():
    k = isin(30, 100) + yol(100, (120, 10), (108, 6), (132, 10), (150, 8), (138, 6), (160, 8))
    g = girisler(ElliottDalga(dalga=2).sinyaller(aynala(yoldan(k))))
    assert len(g) >= 1 and (g.yon == -1).all() and g.stop.iloc[0] > 92


# ------------------------------------------------------------------ elmas

def _elmas_veri(kuyruk):
    env = np.r_[np.linspace(1, 8, 20), np.linspace(8, 0.5, 20)]
    osc = [100 + env[i] * np.sin(2 * np.pi * i / 8) for i in range(40)]
    return yoldan(isin(20, 100) + osc + kuyruk, w=0.2)


def test_elmas_yukari_ve_asagi_kirilim():
    df = _elmas_veri([100.5, 103.5])
    g = girisler(ElmasFormasyon().sinyaller(df))
    assert len(g) == 1 and g.yon.iloc[0] == 1
    assert g.stop.iloc[0] < df.dusuk.iloc[-12:-1].min() + 1.0
    H = df.yuksek.iloc[-41:-1].max() - df.dusuk.iloc[-41:-1].min()
    assert abs(g.hedef.iloc[0] - (df.kapanis.iloc[-1] + 0.65 * H)) < 1.0
    sh = girisler(ElmasFormasyon().sinyaller(aynala(df)))
    assert len(sh) == 1 and sh.yon.iloc[0] == -1


def test_elmas_kirilim_yoksa_veya_genisleme_yoksa_sinyal_yok():
    assert not len(girisler(ElmasFormasyon().sinyaller(_elmas_veri([100.5, 100.8]))))
    env = np.full(40, 4.0)                                   # genişleyen/daralan yok: sabit salınım
    osc = [100 + env[i] * np.sin(2 * np.pi * i / 8) for i in range(40)]
    df = yoldan(isin(20, 100) + osc + [100.5, 106.0], w=0.2)
    assert not len(girisler(ElmasFormasyon().sinyaller(df)))


# ------------------------------------------------------------------ Gann fan

def test_gann_cizgiden_donus():
    k = isin(30, 130) + yol(130, (100, 20), (140, 10), (132, 6), (134, 2))
    df = yoldan(k)
    pv = pivot_tablosu(df, "zigzag", 3, 14, 3.0)
    T = len(k) - 2
    atr = fb._atr(df, GannFan().parametreler)
    i0, f0, onay = int(pv.son_dip_idx.iloc[T]), pv.son_dip_fiyat.iloc[T], int(pv.son_dip_onay_idx.iloc[T])
    u = (df.dusuk.iloc[T] + 0.1 * atr[T] - f0) / (T - i0)         # 1x1 çizgisi T'deki düşüğün hemen altından geçsin
    s = GannFan(olcek_atr=u / atr[onay])
    g = girisler(s.sinyaller(df))
    assert len(g) >= 1 and g.index[0] == df.index[T] and g.yon.iloc[0] == 1
    cizgi = f0 + u * (T - i0)
    assert g.stop.iloc[0] < cizgi and g.stop.iloc[0] < df.dusuk.iloc[T]
    kap = df.kapanis.iloc[T]
    assert g.hedef.iloc[0] > kap and (g.hedef.iloc[0] - kap) <= 4.0 * (kap - g.stop.iloc[0]) + 1e-9
    sh = girisler(s.sinyaller(aynala(df)))
    assert len(sh) >= 1 and sh.yon.iloc[0] == -1


def test_gann_fan_cizgi_kirilinca_sinyal_yok():
    # fiyat çizginin altına inerse (kapanış < çizgi) giriş yok
    k = isin(30, 130) + yol(130, (100, 20), (140, 10), (110, 10), (112, 2))
    df = yoldan(k)
    pv = pivot_tablosu(df, "zigzag", 3, 14, 3.0)
    atr = fb._atr(df, GannFan().parametreler)
    s = GannFan(olcek_atr=2.0)                                     # çok dik fan: fiyat altında kalır
    assert not len(girisler(s.sinyaller(df)))


# ------------------------------------------------------------------ harmonik ABCD

def test_abcd_boga_d_noktasi_ve_ayna():
    k = isin(30, 110) + yol(110, (120, 6), (100, 10), (112, 8), (91, 14), (94, 2))
    df = yoldan(k)
    g = girisler(HarmonikAbcd().sinyaller(df))
    assert len(g) == 1 and g.yon.iloc[0] == 1
    D = 112 - 1.0 * (120 - 100)                                   # 92
    assert g.stop.iloc[0] < D and g.hedef.iloc[0] > df.kapanis[g.index[0]]
    assert abs(g.hedef.iloc[0] - (D + 0.618 * (120.3 - D))) < 3.0   # A tepesi fitille ~120.3
    sh = girisler(HarmonikAbcd().sinyaller(aynala(df)))
    assert len(sh) == 1 and sh.yon.iloc[0] == -1


def test_abcd_d_olusmadan_veya_asiri_dususte_sinyal_yok():
    k = isin(30, 110) + yol(110, (120, 6), (100, 10), (112, 8), (98, 6))       # D'ye (92) ulaşmadı
    assert not len(girisler(HarmonikAbcd().sinyaller(yoldan(k)))), "D'ye ulaşılmadan giriş olmaz"
    k2 = isin(30, 110) + yol(110, (120, 6), (100, 10), (112, 8), (80, 14), (82, 2))   # D'nin çok altına kaçış
    assert not len(girisler(HarmonikAbcd().sinyaller(yoldan(k2))))


def test_abcd_c_a_yi_asarsa_gecersiz():
    k = isin(30, 110) + yol(110, (120, 6), (100, 10), (124, 8), (95, 14), (97, 2))
    assert not len(girisler(HarmonikAbcd().sinyaller(yoldan(k))))


# ------------------------------------------------------------------ çoklu mum

def _dusus(c0, n, adim=1.3):
    out, c = [], c0
    for _ in range(n):
        o = c
        c = o - adim
        out.append((o, o + 0.1, c - 0.1, c))
    return out, c


def _yukselis(c0, n, adim=1.3):
    out, c = [], c0
    for _ in range(n):
        o = c
        c = o + adim
        out.append((o, c + 0.1, o - 0.1, c))
    return out, c


ISINMA = [(100 + 0.2 * (i % 2), 100.5, 99.5, 100 + 0.2 * ((i + 1) % 2)) for i in range(20)]


def test_uc_cizgi_vurusu_long_ve_short():
    d, c = _dusus(100, 15)
    y1 = d[-3][1]
    bar = (c, c + 6, c - 0.1, y1 + 0.6)
    df = ohlc(ISINMA + d + [bar])
    g = girisler(MumCokluFormasyon(desenler="uc_cizgi").sinyaller(df))
    assert len(g) == 1 and g.yon.iloc[0] == 1 and g.index[0] == df.index[-1]
    assert g.stop.iloc[0] < min(x[2] for x in d[-3:]) and g.hedef.iloc[0] > df.kapanis.iloc[-1]
    sh = girisler(MumCokluFormasyon(desenler="uc_cizgi").sinyaller(aynala(df)))
    assert len(sh) == 1 and sh.yon.iloc[0] == -1


def test_uc_kara_karga_yalniz_short():
    u, c = _yukselis(100, 15)
    kk = []
    for _ in range(3):
        o = c
        c = o - 1.3
        kk.append((o, o + 0.1, c - 0.1, c))
    df = ohlc(ISINMA + u + kk)
    g = girisler(MumCokluFormasyon(desenler="uc_kara_karga").sinyaller(df))
    assert len(g) == 1 and g.yon.iloc[0] == -1 and g.index[0] == df.index[-1]
    assert g.stop.iloc[0] > max(x[1] for x in kk)
    assert not len(girisler(MumCokluFormasyon(desenler="uc_kara_karga", short=False).sinyaller(df)))
    # düşüşte oluşan üç kırmızı mum karga değildir
    d, c = _dusus(100, 15)
    assert not len(girisler(MumCokluFormasyon(desenler="uc_kara_karga").sinyaller(ohlc(ISINMA + d))))


def test_terk_edilmis_bebek_bosluk_gerekli():
    d, c = _dusus(100, 12)
    doji = (c - 2.0, c - 1.7, c - 2.3, c - 1.95)
    boga = (doji[3] + 1.8, doji[3] + 4.0, doji[3] + 1.7, doji[3] + 3.5)
    g = girisler(MumCokluFormasyon(desenler="terk_bebek").sinyaller(ohlc(ISINMA + d + [doji, boga])))
    assert len(g) == 1 and g.yon.iloc[0] == 1
    # boşluksuz (doji önceki mumla örtüşüyor) -> desen yok
    doji2 = (c, c + 0.4, c - 0.4, c + 0.02)
    boga2 = (c + 0.02, c + 4.0, c - 0.1, c + 3.5)
    assert not len(girisler(MumCokluFormasyon(desenler="terk_bebek").sinyaller(ohlc(ISINMA + d + [doji2, boga2]))))


def test_harami_capraz_hacim_ve_yutan_mum():
    d, c = _dusus(100, 10)
    buyuk = (c, c + 0.1, c - 4.1, c - 4.0)
    doji = (c - 1.0, c - 0.6, c - 1.4, c - 1.05)
    boga = (c - 1.0, c + 0.8, c - 1.2, c + 0.5)
    hac = [1.0] * 30 + [3.0, 1.0, 2.0]
    df = ohlc(ISINMA + d + [buyuk, doji, boga], hacim=hac)
    g = girisler(MumCokluFormasyon(desenler="harami_capraz").sinyaller(df))
    assert len(g) == 1 and g.yon.iloc[0] == 1
    # doji'de hacim düşmüyorsa (filtre açık) sinyal yok; filtre kapalıysa var
    df2 = ohlc(ISINMA + d + [buyuk, doji, boga], hacim=[1.0] * 30 + [1.0, 2.0, 2.0])
    assert not len(girisler(MumCokluFormasyon(desenler="harami_capraz").sinyaller(df2)))
    assert len(girisler(MumCokluFormasyon(desenler="harami_capraz", hacim_filtre=0).sinyaller(df2))) == 1
    # yutan mum yoksa (kapanış büyük kırmızının açılışının altında)
    boga3 = (c - 1.0, c - 0.2, c - 1.2, c - 0.5)
    df3 = ohlc(ISINMA + d + [buyuk, doji, boga3], hacim=hac)
    assert not len(girisler(MumCokluFormasyon(desenler="harami_capraz").sinyaller(df3)))


def test_mum_desenleri_trend_ister():
    # üç çizgi vuruşu, önceki düşüş trendi olmadan sinyal vermez
    base = [(100 + 0.1 * (i % 2), 100.6, 99.4, 100 + 0.1 * ((i + 1) % 2)) for i in range(30)]
    c = base[-1][3]
    reds = []
    for _ in range(3):
        o = c
        c = o - 1.3
        reds.append((o, o + 0.1, c - 0.1, c))
    bar = (c, c + 6, c - 0.1, reds[0][1] + 0.6)
    assert not len(girisler(MumCokluFormasyon(desenler="uc_cizgi", trend_min_atr=3.0).sinyaller(ohlc(base + reds + [bar]))))


# ------------------------------------------------------------------ pin bar

def _pin_veri():
    taban = []
    for i in range(60):
        c = 100 + 4 * np.sin(2 * np.pi * i / 12)
        o = 100 + 4 * np.sin(2 * np.pi * (i - 1) / 12) if i else c
        taban.append((o, max(o, c) + 1.0, min(o, c) - 1.0, c))
    pin = (96.5, 97.2, 90.0, 97.0)
    dev = [(97.0, 99, 96.8, 98.5), (98.5, 101, 98, 100.5)]
    return taban, pin, dev


def test_pin_bar_aralik_dibinde_long_ve_ayna_short():
    taban, pin, dev = _pin_veri()
    df = ohlc(taban + [pin] + dev)
    g = girisler(PinBar().sinyaller(df))
    assert len(g) == 1 and g.yon.iloc[0] == 1 and g.index[0] == df.index[60]       # pin kapanışı
    assert g.stop.iloc[0] < 90.0                                                      # fitil ucunun altı
    assert abs(g.hedef.iloc[0] - (97.0 + 2 * (97.0 - g.stop.iloc[0]))) < 1e-9
    sh = girisler(PinBar().sinyaller(ohlc([(200 - o, 200 - l, 200 - h, 200 - c) for o, h, l, c in taban + [pin] + dev])))
    assert len(sh) == 1 and sh.yon.iloc[0] == -1


def test_pin_bar_teyit_mumu_ve_tek_giris():
    taban, pin, dev = _pin_veri()
    df = ohlc(taban + [pin] + dev)
    g = girisler(PinBar(teyit_n=2).sinyaller(df))
    assert len(g) == 1 and g.index[0] == df.index[61]                  # pin sonrası ilk teyit kapanışı
    assert g.stop.iloc[0] < 90.0
    # teyit gelmezse (pin tepesi 97.2'nin üstünde kapanış yok) giriş yok
    zayif = [(97.0, 97.1, 96.0, 96.5), (96.5, 97.0, 96.0, 96.9)]
    assert not len(girisler(PinBar(teyit_n=2).sinyaller(ohlc(taban + [pin] + zayif))))


def test_pin_bar_seviyede_degilse_veya_fitil_kisaysa_yok():
    taban, pin, dev = _pin_veri()
    ortada = (101.0, 101.7, 98.0, 101.5)                              # aralığın dibinde değil, ortasında
    assert not len(girisler(PinBar().sinyaller(ohlc(taban + [ortada]))))
    kisa = (96.5, 97.2, 95.0, 97.0)                                  # alt fitil gövdeye göre kısa
    assert not len(girisler(PinBar(fitil_oran=3.5).sinyaller(ohlc(taban + [kisa]))))


def test_pin_bar_hedef_aralik_karsi_ucu():
    taban, pin, dev = _pin_veri()
    g = girisler(PinBar(hedef_r=0.0).sinyaller(ohlc(taban + [pin] + dev)))
    assert len(g) == 1
    assert abs(g.hedef.iloc[0] - max(x[1] for x in taban[-40:])) < 1e-9


def test_daytrade_pin_bar_ust_tf_filtresi():
    # 4h EMA20 üstündeki kapanış gerektirir; düşüş trendindeki aralık dibi pin atlanır
    taban, pin, dev = _pin_veri()
    df = ohlc(taban + [pin] + dev)
    kapali = DtPinBar(teyit_n=0, ust_tf="")
    assert len(girisler(kapali.sinyaller(df))) == 1


# ------------------------------------------------------------------ Renko S/R

def test_renko_destekte_yesil_donus_long_ve_ayna():
    k = isin(40, 120) + yol(120, (100, 25), (103, 2), (108, 3), (111, 2))
    df = yoldan(k)
    g = girisler(RenkoSr().sinyaller(df))
    assert len(g) == 1 and g.yon.iloc[0] == 1
    t = df.index.get_loc(g.index[0])
    assert t > 65 and df.kapanis.iloc[t] > df.kapanis.iloc[t - 3]
    assert g.stop.iloc[0] < df.dusuk.iloc[t - 10:t + 1].min()
    r = (g.hedef.iloc[0] - df.kapanis.iloc[t]) / (df.kapanis.iloc[t] - g.stop.iloc[0])
    assert abs(r - 3.0) < 1e-9
    sh = girisler(RenkoSr().sinyaller(aynala(df)))
    assert len(sh) == 1 and sh.yon.iloc[0] == -1


def test_renko_asiri_bolge_yoksa_sinyal_yok():
    # yavaş, derin olmayan düşüş: RSI/StochRSI aşırı satıma inmez, destek de yok
    rng = np.random.default_rng(3)
    k = list(100 + np.cumsum(rng.normal(0, 0.3, 300)))
    sig = RenkoSr(rsi_alt=5.0, stoch_alt=2.0).sinyaller(yoldan(k))
    assert not len(girisler(sig))


# ------------------------------------------------------------------ kart ayarları

KART_DIR = KOK / "stratejiler" / "kart_ayarlari"
SINIFLAR = {s.ad: type(s) for s in STRATEJILER}


@pytest.mark.parametrize("ad", sorted(SINIFLAR))
def test_kart_ayarlari_gecerli(ad):
    dosya = KART_DIR / f"{ad}.json"
    assert dosya.exists(), dosya
    liste = json.loads(dosya.read_text(encoding="utf-8"))
    assert isinstance(liste, list) and liste
    aileler = {a["aile_id"]: a for a in json.loads((KOK / "stratejiler" / "aileler.json").read_text(encoding="utf-8"))}
    kartlar = set(aileler[ad]["kaynak_kartlar"])
    for e in liste:
        assert set(e) == {"kart_id", "parametreler", "cikis_ayarlari", "not"}
        assert e["kart_id"] in kartlar
        assert e["cikis_ayarlari"] is None
        SINIFLAR[ad](**e["parametreler"])            # parametre adları/değerleri geçerli
        df = fitilli(800, seed=5, freq="1h")
        SINIFLAR[ad](**e["parametreler"]).sinyaller(df)
