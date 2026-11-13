"""Pozisyon bilinçli çıkışlar (varsayılanda kapalı): her tür için elle hesaplı sentetik senaryo, kanca ve kapalıyken aynılık."""
import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, backtest
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.ma_kesisim import MaKesisim
from testler.test_bt_motor import SIFIR, Hazir, mumlar_yap, sinyal_yap
from testler.test_bt_strateji import rastgele_mumlar


def ayna(df):
    """Fiyatı 200 - x yapar (long senaryosunun short eşi)."""
    o = df.copy()
    o["acilis"], o["yuksek"], o["dusuk"], o["kapanis"] = 200 - df["acilis"], 200 - df["dusuk"], 200 - df["yuksek"], 200 - df["kapanis"]
    return o


def kos(df, yon, ca, cikislar=(), giris=0, stop=None, strateji_sinifi=Hazir):
    sig = sinyal_yap(df, {giris: (yon, stop if stop is not None else (50.0 if yon == 1 else 150.0), np.nan)}, cikislar)
    return backtest(df, strateji_sinifi(sig, ca), MotorAyarlari(**SIFIR))


def cikis_mumu(r, df):
    t = r.islemler.iloc[0]
    return int(df.index.get_loc(t.cikis_zamani)), t.cikis_nedeni, t.cikis_fiyati


LONG_KARDA = [(100, 100, 100, 100),
              (100, 100.5, 99, 99.5),     # 1: giriş 100, kapanış zararda
              (99.5, 100, 99, 99),        # 2: zararda
              (99, 102, 99, 101),         # 3: kârda
              (101, 101.5, 100.5, 101),   # 4
              (101, 101.5, 100.5, 101)]   # 5


@pytest.mark.parametrize("yon", [1, -1])
def test_yalniz_karda_cikis(yon):
    df = mumlar_yap(LONG_KARDA)
    df = df if yon == 1 else ayna(df)
    fx = (lambda v: v) if yon == 1 else (lambda v: 200 - v)
    # kapalı: mum 2'deki (zararda) sinyal mum 3 açılışında uygulanır
    assert cikis_mumu(kos(df, yon, CikisAyarlari(), [2, 3]), df) == (3, "sinyal", pytest.approx(fx(99.0)))
    # açık: mum 2 sinyali (zarar) yok sayılır; mum 3 (kâr) sinyali mum 4 açılışında uygulanır
    assert cikis_mumu(kos(df, yon, CikisAyarlari(yalniz_karda_cikis=True), [2, 3]), df) == (4, "sinyal", pytest.approx(fx(101.0)))
    # min kâr %2: kâr %1 yetmez -> veri sonuna kadar
    r = kos(df, yon, CikisAyarlari(yalniz_karda_cikis=True, yalniz_karda_min_kar_yuzde=2.0), [2, 3])
    assert r.islemler.iloc[0].cikis_nedeni == "veri_sonu"


def test_yalniz_karda_stop_etkilenmez():
    df = mumlar_yap([(100, 100, 100, 100), (100, 100, 99, 99.5), (99.5, 99.5, 94, 95), (95, 95, 95, 95)])
    r = kos(df, 1, CikisAyarlari(yalniz_karda_cikis=True), [], stop=96.0)
    assert r.islemler.iloc[0].cikis_nedeni == "stop"


@pytest.mark.parametrize("yon", [1, -1])
def test_min_tutma_mum(yon):
    df = mumlar_yap([(100, 100.5, 99.5, 100)] * 8)
    df = df if yon == 1 else ayna(df)
    # her mumda sinyal; kapalı: mum 1 kapanışında -> mum 2 açılışı
    assert cikis_mumu(kos(df, yon, CikisAyarlari(), range(1, 8)), df)[:2] == (2, "sinyal")
    # min_tutma 3: tutulan=3 mum 3 kapanışında dolar -> mum 4 açılışı
    assert cikis_mumu(kos(df, yon, CikisAyarlari(min_tutma_mum=3), range(1, 8)), df)[:2] == (4, "sinyal")


def test_min_tutma_stop_her_zaman_gecerli():
    df = mumlar_yap([(100, 100, 100, 100), (100, 100, 90, 91), (91, 91, 91, 91), (91, 91, 91, 91)])
    r = kos(df, 1, CikisAyarlari(min_tutma_mum=5), [1, 2], stop=95.0)
    assert cikis_mumu(r, df)[:2] == (1, "stop_gap") or r.islemler.iloc[0].cikis_nedeni.startswith("stop")


@pytest.mark.parametrize("yon", [1, -1])
def test_yasa_bagli_zarar_cikisi(yon):
    df = mumlar_yap([(100, 100, 100, 100),
                     (100, 100, 96.5, 97),     # 1: tutulan 1, zarar %3
                     (97, 97, 93.5, 94),       # 2: tutulan 2, zarar %6 >= 5 -> çık
                     (94, 94, 94, 94), (94, 94, 94, 94)])
    df = df if yon == 1 else ayna(df)
    fx = (lambda v: v) if yon == 1 else (lambda v: 200 - v)
    r = kos(df, yon, CikisAyarlari(yasa_bagli_zarar_cikisi=((2, 5.0),)))
    assert cikis_mumu(r, df) == (3, "yasa_zarar", pytest.approx(fx(94.0)))
    # eşik mum sayısı dolmadan (3) zarar yeterli olsa da çıkış yok
    r = kos(df, yon, CikisAyarlari(yasa_bagli_zarar_cikisi=((3, 5.0),)))
    assert cikis_mumu(r, df)[:2] == (4, "yasa_zarar")
    # zarar eşiği yüksek -> hiç çıkış yok
    r = kos(df, yon, CikisAyarlari(yasa_bagli_zarar_cikisi=((2, 9.0),)))
    assert r.islemler.iloc[0].cikis_nedeni == "veri_sonu"




def _chandelier_df():
    # ATR(3) ~ 2: her mum o=önceki kapanış, h=kapanış+0.5, l=önceki kapanış-0.5 (TR=2). Mum 0-14 yükselir (kapanış 100+k).
    sat, pc = [], 100.0
    for k in range(15):
        c = 100.0 + k
        sat.append((pc, c + 0.5, pc - 0.5, c))
        pc = c
    sat.append((pc, pc + 0.2, pc - 1.8, pc - 1.0))   # 15: zirve(114.5)'e göre -1.5 kapanış: ATR~2 -> k=1 eşiği 112.5 üstü, çıkış yok
    sat.append((pc - 1, pc - 1, pc - 7.5, pc - 7.0)) # 16: kapanış 107 <= 114.5 - ATR(~3.4) -> çıkış
    sat += [(pc - 7, pc - 7, pc - 7, pc - 7)] * 2    # 17,18
    return mumlar_yap(sat)


@pytest.mark.parametrize("yon", [1, -1])
def test_kapanis_chandelier(yon):
    df = _chandelier_df()
    df = df if yon == 1 else ayna(df)
    ca = CikisAyarlari(kapanis_chandelier_k=1.0, kapanis_chandelier_periyot=3)
    r = kos(df, yon, ca, giris=9)
    assert cikis_mumu(r, df)[:2] == (17, "kapanis_chandelier")      # mum 16 kapanışında tetik -> mum 17 açılışı
    # kapalıyken aynı seri veri sonuna taşınır
    assert kos(df, yon, CikisAyarlari(zaman_cikisi_mum=500), giris=9).islemler.iloc[0].cikis_nedeni == "veri_sonu"


@pytest.mark.parametrize("yon", [1, -1])
def test_kismi_yuzde(yon):
    df = mumlar_yap([(100, 100, 100, 100), (100, 100.5, 99.5, 100), (100, 102.5, 100, 102), (102, 102, 101, 101.5), (101.5, 101.5, 101.5, 101.5)])
    df = df if yon == 1 else ayna(df)
    r = kos(df, yon, CikisAyarlari(kismi_yuzde=((2.0, 0.5),), zaman_cikisi_mum=500))
    t = r.islemler.iloc[0]
    assert t.kismi_sayisi == 1
    # giriş 100, seviye %2 -> 102 (short 98); ilk miktarın yarısı kapanır: brüt = 0.5*miktar*2
    assert t.kismi_pnl == pytest.approx(0.5 * t.miktar * 2.0, abs=0.01 * 2)
    assert t.cikis_nedeni == "veri_sonu"
    # kapalı: kısmi yok
    assert kos(df, yon, CikisAyarlari(zaman_cikisi_mum=500)).islemler.iloc[0].kismi_sayisi == 0


class KancaliHazir(Hazir):
    cagrilar = None
    kural = None

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        self.cagrilar.append(d)
        return self.kural(d)


def _kanca_kos(kural, df=None, yon=1):
    df = df if df is not None else mumlar_yap([(100, 100, 100, 100), (100, 101, 99, 100.5), (100.5, 103, 100, 102),
                                               (102, 102.5, 101, 101.5), (101.5, 102, 100.8, 101), (101, 101, 101, 101),
                                               (101, 101, 101, 101)])
    df = df if yon == 1 else ayna(df)
    sig = sinyal_yap(df, {0: (yon, 50.0 if yon == 1 else 150.0, np.nan)})
    s = KancaliHazir(sig, CikisAyarlari())
    s.cagrilar, s.kural = [], kural
    return df, s, backtest(df, s, MotorAyarlari(**SIFIR))


def test_kanca_durum_ve_cikis():
    df, s, r = _kanca_kos(lambda d: d.tutulan_mum >= 3 and d.kar_yuzde > 0)
    assert cikis_mumu(r, df)[:2] == (4, "kanca")     # tutulan=3 mum 3 kapanışında -> mum 4 açılışı
    assert [d.mum_indeksi for d in s.cagrilar] == [1, 2, 3]   # yalnız açık pozisyonda, yalnız kapanmış mumlarda
    d = s.cagrilar[-1]
    assert d.yon == 1 and d.giris_fiyati == 100.0 and d.giris_mum_indeksi == 1 and d.tutulan_mum == 3
    assert d.en_yuksek == 103.0 and d.en_dusuk == 99.0 and d.kapanis == 101.5
    assert d.kar_yuzde == pytest.approx(1.5)


def test_kanca_short_durumu():
    df, s, r = _kanca_kos(lambda d: d.tutulan_mum >= 2, yon=-1)
    d = s.cagrilar[-1]
    assert d.yon == -1 and d.giris_fiyati == 100.0 and d.kapanis == 98.0 and d.kar_yuzde == pytest.approx(2.0)
    assert d.en_dusuk == 97.0 and d.en_yuksek == 101.0
    assert cikis_mumu(r, df)[:2] == (3, "kanca")


def test_kanca_asla_true_donmezse_sonuc_ayni():
    _, _, r1 = _kanca_kos(lambda d: False)
    df = mumlar_yap([(100, 100, 100, 100), (100, 101, 99, 100.5), (100.5, 103, 100, 102), (102, 102.5, 101, 101.5),
                     (101.5, 102, 100.8, 101), (101, 101, 101, 101), (101, 101, 101, 101)])
    r0 = backtest(df, Hazir(sinyal_yap(df, {0: (1, 50.0, np.nan)}), CikisAyarlari()), MotorAyarlari(**SIFIR))
    pd.testing.assert_frame_equal(r1.islemler, r0.islemler)
    pd.testing.assert_series_equal(r1.ozsermaye, r0.ozsermaye)


def test_kanca_varsayilan_yok():
    from motor.strateji.temel import Strateji
    assert Strateji.pozisyon_cikisi is None and Hazir.pozisyon_cikisi is None


class HicTrue(MaKesisim):
    def pozisyon_cikisi(self, d):
        return False


VARYANTLAR = [dict(), dict(atr_iz_suren_k=3.0), dict(zaman_cikisi_mum=24), dict(sabit_r_hedefi=2.0, kismi=((1.0, 0.5),))]
KAPALI = dict(yalniz_karda_cikis=False, yalniz_karda_min_kar_yuzde=0.0, min_tutma_mum=None, yasa_bagli_zarar_cikisi=(),
              kapanis_chandelier_k=None, kapanis_chandelier_periyot=14, kismi_yuzde=())


def test_alanlar_varsayilanda_kapali():
    ca = CikisAyarlari()
    for ad, v in KAPALI.items():
        assert getattr(ca, ad) == v


@pytest.mark.parametrize("seed", [7, 21])
@pytest.mark.parametrize("v", VARYANTLAR)
def test_kapaliyken_bit_bit_ayni(v, seed):
    df = rastgele_mumlar(1200, seed)
    a = backtest(df, MaKesisim(cikis_ayarlari=CikisAyarlari(**v)), MotorAyarlari())
    b = backtest(df, MaKesisim(cikis_ayarlari=CikisAyarlari(**v, **KAPALI)), MotorAyarlari())
    c = backtest(df, HicTrue(cikis_ayarlari=CikisAyarlari(**v)), MotorAyarlari())   # kanca var ama hiç tetiklenmez
    for x in (b, c):
        pd.testing.assert_frame_equal(a.islemler, x.islemler, check_exact=True)
        pd.testing.assert_series_equal(a.ozsermaye, x.ozsermaye, check_exact=True)
        assert a.reddedilenler == x.reddedilenler


def test_dogrulama_hatalari():
    for kw in (dict(min_tutma_mum=0), dict(yasa_bagli_zarar_cikisi=((5, 0.0),)), dict(kapanis_chandelier_k=0.0),
               dict(kismi_yuzde=((2.0, 1.5),)), dict(kismi_yuzde=((0.0, 0.5),))):
        with pytest.raises(ValueError):
            CikisAyarlari(**kw)
