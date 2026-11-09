"""D3 dış stratejileri (freqtrade / kural / awesome / jesuistm): lookahead, stop tarafı, sentetik senaryo, gün sonu, motor dumanı."""
import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji import kayit
from motor.strateji.dis._gosterge_d3 import (
    ay_sonuna_kalan_gun, genisleyen_minmax, son_cuma_kalan_gun, td_sayim, tema)
from motor.strateji.dis.d3_freqtrade_scalp import (
    PowerTower, Quickie, SmoothOperator, Strategy005, TechnicalCmf, TrendFollowingEmaObv, TwapRsi)
from motor.strateji.dis.d3_freqtrade_ust import Heracles, HourBased, MultiMa, TdSequential, VolatilitySystem, Wtc
from motor.strateji.dis.d3_kural import (
    Ema21Sapma, Ema50Sapma, HaftaGunuBraket, KapanisMa5, Roc20Ls, Sma200Ls, TrendYargisi, UcOrtalamaBoga,
    UcOrtalamaBogaSma60)
from motor.strateji.dis.d3_takvim import (
    AsiriTepkiErtesiGun, AyDonumu, BtcGeceSeans, JtAwesomeOsilator, MaasGunu, Min10Dip, OcakBarometresi, VadeHaftasi)
from testler.test_daytrade import mumlar_kapanistan, rastgele_mumlar

SINIFLAR = [Heracles, MultiMa, HourBased, TdSequential, VolatilitySystem, Wtc,
            PowerTower, Quickie, SmoothOperator, Strategy005, TechnicalCmf, TrendFollowingEmaObv, TwapRsi,
            Ema21Sapma, Ema50Sapma, HaftaGunuBraket, KapanisMa5, Sma200Ls, Roc20Ls, TrendYargisi,
            UcOrtalamaBoga, UcOrtalamaBogaSma60,
            AyDonumu, AsiriTepkiErtesiGun, BtcGeceSeans, MaasGunu, Min10Dip, OcakBarometresi, VadeHaftasi,
            JtAwesomeOsilator]
GUNLUK = {HaftaGunuBraket, KapanisMa5, Sma200Ls, Roc20Ls, TrendYargisi, UcOrtalamaBoga, UcOrtalamaBogaSma60,
          AyDonumu, AsiriTepkiErtesiGun, MaasGunu, Min10Dip, OcakBarometresi, VadeHaftasi, JtAwesomeOsilator}
DAYTRADE = [s for s in SINIFLAR if s.stil == "daytrade"]


def veri(sinif, n=None, seed=11):
    """Sınıfın tipik zaman dilimine göre rastgele mumlar; hacim değişken (Strategy005 için patlamalar dahil)."""
    if sinif in GUNLUK:
        df = rastgele_mumlar(n or 1800, seed=seed, freq="1D", baslangic="2018-01-01")
    elif sinif in (Heracles, MultiMa, Ema21Sapma, Ema50Sapma):
        df = rastgele_mumlar(n or 4500, seed=seed, freq="4h")
    elif sinif.stil == "scalp":
        df = rastgele_mumlar(n or 4000, seed=seed, freq="15min")
    else:
        df = rastgele_mumlar(n or 4000, seed=seed, freq="1h")
    rng = np.random.default_rng(seed + 1)
    df["hacim"] = rng.uniform(1, 3, len(df)) * np.where(rng.random(len(df)) < 0.03, 10.0, 1.0)
    return df


def _s(sinif, **kw):
    return sinif(yonler="ls", **kw)


# ---------------------------------------------------------------- kayıt / sözleşme
def test_otuz_strateji_kayitli_ve_gecerli():
    kayitli = {a for a, c in kayit.tum_stratejiler().items() if c.__module__.startswith("motor.strateji.dis.d3_")}
    assert kayitli == {c.ad for c in SINIFLAR} and len(kayitli) == 30
    assert [s for s in kayit.dogrula() if any(a in s for a in kayitli)] == []


@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_sozlesme_izgara_cikis(sinif):
    s = sinif()
    assert s.ad.startswith("dis__") and s.stil in {"scalp", "daytrade", "swing"}
    assert s.cikis_var_mi()
    n = 1
    for v in sinif.parametre_izgarasi.values():
        n *= len(v)
    assert 1 < n <= 27
    assert set(sinif.parametre_izgarasi) <= set(sinif.varsayilan_parametreler)
    # ızgaranın her ucu kurulabilmeli ve çalışmalı
    df = veri(sinif, n=1500 if sinif not in (MultiMa,) else 2500)
    for anahtar, degerler in sinif.parametre_izgarasi.items():
        for d in (degerler[0], degerler[-1]):
            sig = sinif(**{anahtar: d}).sinyaller(df)
            assert sig.index.equals(df.index)


# ---------------------------------------------------------------- lookahead
@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_lookahead_yok(sinif):
    df = veri(sinif)
    for s in (sinif(), _s(sinif)):
        tam = s.sinyaller(df)
        for n in (len(df) // 5, len(df) // 2, int(len(df) * 0.8)):
            pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])


def test_lookahead_strategy005_gevsek_parametre():
    df = veri(Strategy005)
    s = _s(Strategy005, rsi_alt=1, fastd_alt=0, fisher_ust=60, hacim_ort=20)
    tam = s.sinyaller(df)
    assert (tam.yon != 0).sum() > 0
    for n in (800, 2000, 3300):
        pdt.assert_frame_equal(s.sinyaller(df.iloc[:n]), tam.iloc[:n])


def test_genisleyen_minmax_nedensel():
    x = pd.Series(np.random.default_rng(1).normal(size=500)).cumsum()
    tam = genisleyen_minmax(x, 50)
    pdt.assert_series_equal(genisleyen_minmax(x.iloc[:300], 50), tam.iloc[:300])
    assert tam.iloc[:50].isna().all() and tam.iloc[50:].between(0, 1).all()


# ---------------------------------------------------------------- stop tarafı ve sinyal üretimi
@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_stop_tarafi_ve_sinyal_var(sinif):
    df = veri(sinif)
    kwargs = {}
    if sinif is Strategy005:
        kwargs = {"rsi_alt": 1, "fastd_alt": 0, "fisher_ust": 60, "hacim_ort": 20}
    elif sinif is HourBased:
        kwargs = {"cikis_saat_min": 12}   # varsayılan çıkış penceresi (22..21) boştur -> short pencere de boş
    sig_hepsi = []
    for yon in ("long", "short"):
        sig = sinif(yonler=yon, **kwargs).sinyaller(df)
        giris = sig[sig.yon != 0]
        assert len(giris) > 0, f"{sinif.ad} {yon}: sinyal yok"
        assert giris.stop.notna().all()
        kap = df.kapanis
        l, s = giris[giris.yon == 1], giris[giris.yon == -1]
        assert (l.stop < kap[l.index]).all() and (s.stop > kap[s.index]).all()
        assert set(giris.yon.unique()) == ({1} if yon == "long" else {-1})
        sig_hepsi.append(sig)
    assert {"yon", "stop", "hedef", "cikis", "cikis_long", "cikis_short"} <= set(sig_hepsi[0].columns)


# ---------------------------------------------------------------- gün sonu (daytrade)
@pytest.mark.parametrize("sinif", DAYTRADE, ids=lambda s: s.ad)
def test_gun_sonu_zorunlu_cikis(sinif):
    df = veri(sinif)
    sig = _s(sinif).sinyaller(df)
    gun = df.index.floor("D")
    son = pd.Series(gun, index=df.index).shift(-1) != pd.Series(gun, index=df.index)
    son.iloc[-1] = False   # son satırın gün sonu olup olmadığı geleceğe bağlı; atlanır
    assert sig.loc[son, "cikis"].all()
    assert (sig.loc[son, "yon"] == 0).all()


# ---------------------------------------------------------------- motor dumanı
@pytest.mark.parametrize("sinif", SINIFLAR, ids=lambda s: s.ad)
def test_motor_calisir(sinif):
    df = veri(sinif, n=1500 if sinif is not MultiMa else 2500)
    sonuc = backtest(df, _s(sinif), MotorAyarlari())
    assert len(sonuc.ozsermaye) == len(df)


# ---------------------------------------------------------------- sentetik senaryolar
def test_ay_donumu_takvim():
    idx = pd.date_range("2022-01-01", periods=120, freq="1D", tz="UTC")
    df = mumlar_kapanistan(np.linspace(100, 120, 120), freq="1D")
    sig = AyDonumu().sinyaller(df)
    giris = list(sig.index[sig.yon == 1].strftime("%m-%d"))
    assert giris[:3] == ["01-30", "02-27", "03-30"]
    cik = list(sig.index[sig.cikis_long].strftime("%m-%d"))
    assert {"02-03", "03-03", "04-03"} <= set(cik)
    assert (ay_sonuna_kalan_gun(idx)[[0, 30, 58]] == [30, 0, 0]).all()


def test_maas_gunu_takvim():
    df = mumlar_kapanistan(np.linspace(100, 120, 90), freq="1D")
    sig = MaasGunu().sinyaller(df)
    assert list(sig.index[sig.yon == 1].strftime("%m-%d")) == ["01-15", "02-15", "03-15"]
    assert (sig.zaman_cikisi_mum.dropna() == 1).all()


def test_vade_haftasi_takvim():
    df = mumlar_kapanistan(np.linspace(100, 120, 60), freq="1D", baslangic="2022-09-01")
    sig = VadeHaftasi().sinyaller(df)
    # Eylül 2022'nin son Cuma'sı 30 Eylül; Pazar 25'te gir, Perşembe 29'da çık
    assert list(sig.index[sig.yon == 1].strftime("%m-%d")) == ["09-25", "10-23"]
    assert "09-29" in list(sig.index[sig.cikis_long].strftime("%m-%d"))
    assert son_cuma_kalan_gun(pd.DatetimeIndex(["2022-09-25"], tz="UTC"))[0] == 5


def test_hafta_gunu_braket():
    df = mumlar_kapanistan(np.linspace(100, 120, 60), freq="1D")
    sig = HaftaGunuBraket().sinyaller(df)
    assert set(df.index[sig.yon == 1].dayofweek) == {1, 3, 4}
    g = sig[sig.yon == 1].iloc[0]
    k = df.kapanis[sig.index[sig.yon == 1][0]]
    assert g.stop == pytest.approx(k * 0.97) and g.hedef == pytest.approx(k * 1.03) and g.zaman_cikisi_mum == 7


def test_btc_gece_seans_ve_gun_sonu():
    df = mumlar_kapanistan(np.linspace(100, 120, 96), freq="1h")
    sig = BtcGeceSeans().sinyaller(df)
    assert set(df.index[sig.yon == 1].hour) == {21}
    assert set(df.index[sig.cikis].hour) == {23}


def test_hour_based_saat_penceresi():
    df = mumlar_kapanistan(np.linspace(100, 120, 96), freq="1h")
    sig = HourBased().sinyaller(df)
    saat = df.index[sig.yon == 1].hour
    assert saat.min() == 4 and saat.max() == 22   # 23:00 gün sonunun son mumu: giriş yok


def test_ocak_barometresi():
    idx = pd.date_range("2020-12-01", "2023-03-01", freq="1D", tz="UTC")
    kap = pd.Series(100.0, index=idx)
    kap[(idx >= "2021-01-01") & (idx < "2021-02-01")] = np.linspace(100, 110, 31)   # 2021 Ocak yükselir
    kap[idx >= "2021-02-01"] = 110.0
    kap[(idx >= "2022-01-01") & (idx < "2022-02-01")] = np.linspace(110, 100, 31)   # 2022 Ocak düşer
    kap[idx >= "2022-02-01"] = 100.0
    df = mumlar_kapanistan(kap.to_numpy(), freq="1D", baslangic="2020-12-01")
    sig = OcakBarometresi().sinyaller(df)
    giris = list(sig.index[sig.yon == 1].strftime("%Y-%m-%d"))
    assert giris[0] == "2020-12-31"
    cik = list(sig.index[sig.cikis_long].strftime("%Y-%m-%d"))
    # 2021 Ocak yükseldi -> 2021'de çıkış yok; 2022 Ocak düştü -> 31 Ocak 2022 kapanışında çık
    assert not [c for c in cik if "2021-02-01" <= c < "2022-01-01"]
    assert "2022-01-31" in cik
    # 2023 Ocak sonrası (Şubat'tan beri) tutma: veri 2023-03-01'de bitiyor, 2022 Aralık sonu yeniden girildi
    assert "2022-12-31" in giris


def test_ocak_ilk_gun_eksikse_yukselmis_sayilmaz():
    idx = pd.date_range("2021-01-15", "2021-03-31", freq="1D", tz="UTC")
    df = mumlar_kapanistan(np.linspace(100, 150, len(idx)), freq="1D", baslangic="2021-01-15")
    sig = OcakBarometresi().sinyaller(df)
    assert sig.cikis_long.loc["2021-01-31"]


def test_td_sequential_dusus_sayimi():
    kap = np.r_[np.full(10, 100.0), 100 - np.arange(1, 31) * 0.5]
    df = mumlar_kapanistan(kap, genlik=0.1, freq="15min")
    t = td_sayim(df.yuksek, df.dusuk, df.kapanis, 4, 9)
    assert t["alis"][10:19].tolist() == list(range(1, 10))   # düşüş idx 10'da başlar (kapanış < 4 mum önceki)
    s = TdSequential(stop_yuzde=0.2).sinyaller(df)
    ilk = np.flatnonzero(s.yon.to_numpy() == 1)[0]
    assert ilk == 18


def test_power_tower_yukselis():
    kap = 100 * 1.004 ** np.arange(60)
    df = mumlar_kapanistan(kap, genlik=0.01)
    s = PowerTower().sinyaller(df)
    assert (s.yon == 1).any() and not (s.yon == -1).any()
    assert PowerTower(yonler="short").sinyaller(mumlar_kapanistan(kap[::-1].copy(), genlik=0.01)).yon.eq(-1).any()


def test_trend_following_kesisim_obv():
    kap = np.r_[np.full(60, 100.0), 104.0, 104.5, 105.0]
    df = mumlar_kapanistan(kap, genlik=0.05)
    s = TrendFollowingEmaObv().sinyaller(df)
    assert s.yon.iloc[60] == 1 and (s.yon.iloc[:60] == 0).all()
    assert s.stop.iloc[60] == pytest.approx(104.0 * (1 - 0.265)) and s.hedef.iloc[60] == pytest.approx(104.0 * 1.05)


def test_twap_rsi_yonler():
    dus = mumlar_kapanistan(100 - np.arange(60) * 0.3)
    yuk = mumlar_kapanistan(100 + np.arange(60) * 0.3)
    assert (TwapRsi().sinyaller(dus).yon == 1).any()
    assert (TwapRsi(yonler="long").sinyaller(yuk).yon == 0).all()
    assert (TwapRsi(yonler="short").sinyaller(yuk).yon == -1).any()


def test_technical_cmf_dusuk_kapanis_long():
    n = 80
    kap = np.full(n, 100.0)
    df = mumlar_kapanistan(kap, genlik=0.0)
    df["yuksek"] = 101.0
    df["dusuk"] = 99.0
    df["kapanis"] = 99.2    # aralığın dibine yakın kapanış -> CMF < 0
    s = TechnicalCmf().sinyaller(df)
    assert (s.yon.iloc[21:] == 1).all() and (s.yon.iloc[:20] == 0).all()
    df["kapanis"] = 100.8   # tepeye yakın -> CMF > 0 -> long yok, long çıkışı var
    s2 = TechnicalCmf().sinyaller(df)
    assert (s2.yon == 0).all() and s2.cikis_long.iloc[21:].all()


def test_volatility_system_sicrama():
    rng = np.random.default_rng(3)
    kap = 100 + np.cumsum(rng.normal(0, 0.05, 300))
    kap = np.r_[kap, kap[-1] + 5.0 + np.cumsum(rng.normal(0, 0.05, 20))]
    df = mumlar_kapanistan(kap, genlik=0.05, freq="1h", baslangic="2022-01-03")
    s = VolatilitySystem().sinyaller(df)
    assert (s.yon.iloc[300:312] == 1).any()
    assert (s.yon.iloc[:300] == 1).sum() <= (s.yon.iloc[:300] == -1).sum() + 3


def test_strategy005_hacim_patlamasi_senaryosu():
    n = 300
    kap = np.r_[np.full(150, 100.0), 100 - np.arange(1, 151) * 0.05]
    df = mumlar_kapanistan(kap, genlik=0.02, freq="15min")
    df["hacim"] = 1.0
    df.iloc[200, df.columns.get_loc("hacim")] = 50.0
    s = Strategy005(rsi_alt=1, fastd_alt=0, fisher_ust=60, hacim_ort=50).sinyaller(df)
    assert s.yon.iloc[200] in (0, 1)
    # patlama olmayan mumlarda giriş yok
    assert (s.yon.drop(df.index[200]) == 0).all()


def test_uc_ortalama_boga_mumu():
    kap = np.r_[np.linspace(110, 100, 40), 100.0, 104.5]
    df = mumlar_kapanistan(kap, genlik=0.1, freq="1D")
    df.iloc[41, df.columns.get_loc("acilis")] = 99.0   # SMA'ların altından açıl, üstlerinde kapan
    s = UcOrtalamaBoga(govde=0.02).sinyaller(df)
    assert s.yon.iloc[41] == 1


def test_ema21_sapma_giris_ve_cikis():
    kap = np.r_[np.full(60, 100.0), 97.0, 97.0, 97.0, 103.0, 103.0]
    df = mumlar_kapanistan(kap, genlik=0.1, freq="4h")
    s = Ema21Sapma(yonler="ls").sinyaller(df)
    assert s.yon.iloc[60] == 1 and s.yon.iloc[63] == -1 and s.cikis_long.iloc[63]


def test_tema_ve_td_nedensel_sabit_seri():
    assert tema(pd.Series(np.full(100, 5.0)), 10).dropna().round(9).eq(5.0).all()
