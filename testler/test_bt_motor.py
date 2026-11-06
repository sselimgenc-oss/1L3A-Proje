"""Backtest motoru: elle hesaplanabilir sentetik senaryolar."""
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, SembolKurallari, backtest
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.temel import Strateji


class Hazir(Strateji):
    """Sinyalleri testte elle verilen sahte strateji."""
    ad = "hazir"

    def __init__(self, sinyal, cikis_ayarlari=None):
        super().__init__(cikis_ayarlari=cikis_ayarlari)
        self._s = sinyal

    def cikis_var_mi(self):
        return True     # eski testler: çıkış kuralı testin kendisinde

    def sinyaller(self, mumlar):
        return self._s


def mumlar_yap(satirlar, bas="2024-01-01 00:00", frekans="1h"):
    """satirlar: (acilis, yuksek, dusuk, kapanis)"""
    idx = pd.date_range(bas, periods=len(satirlar), freq=frekans, tz="UTC", name="zaman")
    df = pd.DataFrame(satirlar, columns=["acilis", "yuksek", "dusuk", "kapanis"], index=idx, dtype=float)
    df["hacim"] = 1.0
    return df


def sinyal_yap(df, girisler=(), cikislar=()):
    """girisler: {mum_no: (yon, stop, hedef)}"""
    s = pd.DataFrame({"yon": 0, "stop": np.nan, "hedef": np.nan, "cikis": False}, index=df.index)
    for i, (yon, stop, hedef) in dict(girisler).items():
        s.iloc[i, s.columns.get_loc("yon")] = yon
        s.iloc[i, s.columns.get_loc("stop")] = stop
        s.iloc[i, s.columns.get_loc("hedef")] = hedef
    for i in cikislar:
        s.iloc[i, s.columns.get_loc("cikis")] = True
    return s


SIFIR = dict(komisyon_taker_yuzde=0.0, kayma_bps=0.0, stop_kayma_bps=0.0)


def test_tek_long_pnl_komisyon_kayma():
    df = mumlar_yap([(100, 101, 99.5, 100), (100, 101, 99.5, 100.5), (100.5, 111, 100, 110), (110, 111, 109, 110)])
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)}, cikislar=[2])
    ay = MotorAyarlari(komisyon_taker_yuzde=0.05, kayma_bps=2.0)
    r = backtest(df, Hazir(sig), ay)
    assert len(r.islemler) == 1
    t = r.islemler.iloc[0]
    # giris 100*(1.0002)=100.02 ; stop 98 -> risk/birim 2.02 ; miktar=100/2.02=49.5049 -> 49.504
    assert t.giris_fiyati == pytest.approx(100.02)
    assert t.miktar == pytest.approx(49.504)
    # cikis 110*(1-0.0002)=109.978 -> tick 0.01 -> 109.98
    assert t.cikis_fiyati == pytest.approx(109.98)
    brut = (Decimal("109.98") - Decimal("100.02")) * Decimal("49.504")
    kom = Decimal("49.504") * (Decimal("100.02") + Decimal("109.98")) * Decimal("0.0005")
    assert t.brut_pnl == pytest.approx(float(brut))
    assert t.komisyon == pytest.approx(float(kom))
    assert t.net_pnl == pytest.approx(float(brut - kom))
    assert t.cikis_nedeni == "sinyal"
    assert r.ozsermaye.iloc[-1] == pytest.approx(10000 + float(brut - kom))
    assert t.r == pytest.approx(float(brut - kom) / (49.504 * 2.02))


def test_ayni_mumda_stop_ve_hedef_stop_sayilir():
    df = mumlar_yap([(100, 100, 100, 100), (100, 105, 97, 100), (100, 100, 100, 100)])
    sig = sinyal_yap(df, {0: (1, 98.0, 104.0)})
    r = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "stop"
    assert t.cikis_fiyati == pytest.approx(98.0)


def test_gap_ile_stop_acilis_fiyatindan_dolar():
    df = mumlar_yap([(100, 100, 100, 100), (100, 101, 99.5, 100), (95, 96, 94, 95), (95, 95, 95, 95)])
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)})
    r = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "stop_gap"
    assert t.cikis_fiyati == pytest.approx(95.0)
    assert t.r < -2   # stopu aşan kayıp 1R'den büyük


def test_funding_yonu():
    # 1h mumlar; funding 02:00 ve 03:00 (pozisyon 01:00 aciliyor, 05:00 kapaniyor)
    df = mumlar_yap([(100, 100, 100, 100)] * 7)
    fd = pd.DataFrame({"oran": [0.001, 0.001]},
                      index=pd.DatetimeIndex(["2024-01-01 02:00", "2024-01-01 03:00"], tz="UTC", name="zaman"))
    miktar = 100 / 2.0   # risk 100, stop mesafesi 2 -> 50
    for yon, stop in [(1, 98.0), (-1, 102.0)]:
        sig = sinyal_yap(df, {0: (yon, stop, np.nan)}, cikislar=[4])
        r = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR), funding=fd)
        t = r.islemler.iloc[0]
        beklenen = yon * 2 * miktar * 100 * 0.001   # iki funding, pozitif oran long'a gider
        assert t.funding == pytest.approx(beklenen)
        assert t.net_pnl == pytest.approx(-beklenen)   # fiyat sabit -> tek kalem funding
    # long odedi, short tahsil etti
    assert beklenen < 0


def test_min_notional_reddi():
    df = mumlar_yap([(100, 100, 100, 100)] * 4)
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)}, cikislar=[1])
    r = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR, kurallar=SembolKurallari(min_notional=1_000_000)))
    assert len(r.islemler) == 0
    assert r.reddedilenler[0]["neden"] == "min_notional"


def test_yuvarlama_asla_yukari_gitmez():
    # 100/1.7 = 58.82 ; step 1 -> 58 (round 59 verirdi)
    df = mumlar_yap([(100, 100, 100, 100)] * 4)
    sig = sinyal_yap(df, {0: (1, 98.3, np.nan)}, cikislar=[1])
    r = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR, kurallar=SembolKurallari(step_size=1.0, min_qty=1)))
    assert r.islemler.iloc[0].miktar == 58.0


def _stop_dongusu(dongu_sayisi, baslangic="2024-01-01 14:00"):
    """Her döngü 2 saatlik mum: A (sinyal, kapanış 100) + B (açılış 100, stop 99'a değer)."""
    satir = []
    for _ in range(dongu_sayisi):
        satir += [(100, 100, 100, 100), (100, 100.5, 98.5, 99)]
    return mumlar_yap(satir, bas=baslangic)


def test_gunluk_kayip_limiti():
    df = _stop_dongusu(6)    # 14:00'dan 6 döngü -> 14,16,18,20,22 | 00:00 (ertesi gün)
    girisler = {2 * k: (1, 99.0, np.nan) for k in range(6)}
    r = backtest(df, Hazir(sinyal_yap(df, girisler)), MotorAyarlari(kayma_bps=0.0))
    gunler = r.islemler["giris_zamani"].dt.date.astype(str).value_counts().to_dict()
    assert gunler["2024-01-01"] == 3          # 3 kayıptan sonra (≈%3.3) o gün biter
    assert gunler["2024-01-02"] >= 1          # ertesi gün yeniden işlem
    assert any(x["neden"] == "gunluk_kayip_limiti" for x in r.reddedilenler)


def test_kill_switch_gap_kaybindan_sonra_islem_yok():
    satir = [(100, 100, 100, 100), (100, 100, 99.95, 100),      # giris 100, stop 99.9
             (80, 81, 79, 80),                                   # gap: ~-%60
             (80, 80, 80, 80), (80, 80, 80, 80), (80, 80, 80, 80), (80, 80, 80, 80)]
    df = mumlar_yap(satir)
    sig = sinyal_yap(df, {0: (1, 99.9, np.nan), 3: (1, 79.0, np.nan)})
    r = backtest(df, Hazir(sig), MotorAyarlari(kayma_bps=0.0))
    assert len(r.islemler) == 1
    assert r.islemler.iloc[0].cikis_nedeni == "stop_gap"
    assert r.ozsermaye.iloc[-1] < 8000
    assert r.reddedilenler[-1]["neden"] == "kill_switch"


def test_sert_limit_kirpma():
    df = mumlar_yap([(100, 100, 100, 100)] * 4)
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)}, cikislar=[1])
    a = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR, risk_yuzde=1.0))
    b = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR, risk_yuzde=5.0, kaldirac=50))
    assert b.islemler.iloc[0].miktar == a.islemler.iloc[0].miktar
    assert len(b.uyarilar) == 2


def test_kaldirac_tavani():
    # stop çok yakın -> risk bazlı miktar devasa; 3x tavan: 3*10000/100 = 300
    df = mumlar_yap([(100, 100, 100, 100)] * 4)
    sig = sinyal_yap(df, {0: (1, 99.9, np.nan)}, cikislar=[1])
    r = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR))
    assert r.islemler.iloc[0].miktar == pytest.approx(300.0)


def test_sabit_r_hedefi_ve_basabas_ve_zaman_cikisi():
    # sabit 2R hedef: giris 100, stop 98 -> hedef 104
    df = mumlar_yap([(100, 100, 100, 100), (100, 101, 99.5, 100), (100, 104.5, 100, 104), (104, 104, 104, 104)])
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)})
    r = backtest(df, Hazir(sig, CikisAyarlari(sabit_r_hedefi=2.0)), MotorAyarlari(**SIFIR))
    assert r.islemler.iloc[0].cikis_nedeni == "hedef"
    assert r.islemler.iloc[0].cikis_fiyati == pytest.approx(104.0)
    assert r.islemler.iloc[0].r == pytest.approx(2.0, abs=0.01)

    # başabaş: 1. mumda +1R (102) görülür -> stop 100 -> sonraki mum 99'a iner -> 100'den çıkar
    df = mumlar_yap([(100, 100, 100, 100), (100, 102.5, 99.5, 101), (101, 101, 99, 99.5), (99, 99, 99, 99)])
    r = backtest(df, Hazir(sig, CikisAyarlari(basabas_r_esigi=1.0)), MotorAyarlari(**SIFIR))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "stop" and t.cikis_fiyati == pytest.approx(100.0)
    assert t.net_pnl == pytest.approx(0.0)

    # zaman çıkışı: 2 mum tutulur
    df = mumlar_yap([(100, 100, 100, 100)] + [(100, 100.5, 99.5, 100)] * 5)
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)})
    r = backtest(df, Hazir(sig, CikisAyarlari(zaman_cikisi_mum=2)), MotorAyarlari(**SIFIR))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "zaman"
    assert t.cikis_zamani - t.giris_zamani == pd.Timedelta(hours=2)


def test_atr_iz_suren_stop_sadece_yukari_gider():
    n = 30
    satir = [(100 + i, 101 + i, 99 + i, 100 + i) for i in range(n)]        # sürekli yükseliş
    satir += [(130, 130, 90, 95)] * 3                                      # sert düşüş
    df = mumlar_yap(satir)
    sig = sinyal_yap(df, {20: (1, 100.0, np.nan)})
    r = backtest(df, Hazir(sig, CikisAyarlari(atr_iz_suren_k=2.0)), MotorAyarlari(**SIFIR))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni in ("stop", "stop_gap")
    assert t.cikis_fiyati > 100.0   # ilk stop 100'dü, iz süren onu yukarı çekti


def test_stop_kaymasi_ayri_uygulanir():
    df = mumlar_yap([(100, 100, 100, 100), (100, 101, 97, 100), (100, 100, 100, 100)])
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)})
    ay = dict(komisyon_taker_yuzde=0.0, kayma_bps=0.0)
    a = backtest(df, Hazir(sig), MotorAyarlari(**ay, stop_kayma_bps=0.0))
    b = backtest(df, Hazir(sig), MotorAyarlari(**ay, stop_kayma_bps=100.0))
    assert a.islemler.iloc[0].cikis_fiyati == pytest.approx(98.0)
    assert b.islemler.iloc[0].cikis_fiyati == pytest.approx(97.02)   # 98*(1-0.01)
    assert b.islemler.iloc[0].giris_fiyati == pytest.approx(100.0)   # giriş kayma_bps kullanır


def test_olc_modunda_kill_switch_durdurmaz_ve_kaydeder():
    satir = [(100, 100, 100, 100), (100, 100, 99.95, 100), (80, 81, 79, 80),
             (80, 80, 80, 80), (80, 80, 80, 80), (80, 80, 80, 80), (80, 80, 80, 80)]
    df = mumlar_yap(satir)
    sig = sinyal_yap(df, {0: (1, 99.9, np.nan), 3: (1, 79.0, np.nan)})
    r = backtest(df, Hazir(sig), MotorAyarlari(kayma_bps=0.0, limit_modu="olc"))
    assert all(x["neden"] != "kill_switch" for x in r.reddedilenler)
    assert len(r.islemler) == 2                       # ikinci giriş engellenmedi
    turler = [o["tur"] for o in r.limit_olaylari]
    assert "kill_switch" in turler
    o = next(o for o in r.limit_olaylari if o["tur"] == "kill_switch")
    assert o["dusus_yuzde"] >= 20 and o["ozsermaye"] < 8000


def test_uygula_modu_varsayilan_ve_olay_yok():
    df = mumlar_yap([(100, 100, 100, 100), (100, 100, 99.95, 100), (80, 81, 79, 80)] + [(80, 80, 80, 80)] * 4)
    sig = sinyal_yap(df, {0: (1, 99.9, np.nan), 3: (1, 79.0, np.nan)})
    assert MotorAyarlari().limit_modu == "uygula"
    r = backtest(df, Hazir(sig), MotorAyarlari(kayma_bps=0.0))
    assert r.limit_olaylari == [] and len(r.islemler) == 1
    with pytest.raises(ValueError):
        backtest(df, Hazir(sig), MotorAyarlari(limit_modu="x"))


def test_olc_modunda_risk_tavani_hala_uygulanir():
    df = mumlar_yap([(100, 100, 100, 100)] * 4)
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)}, cikislar=[1])
    r = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR, risk_yuzde=5.0, kaldirac=50, limit_modu="olc"))
    assert len(r.uyarilar) == 2


# ------------------------------------------------------------------ yönlü çıkış
def _yonlu_senaryo(**kolonlar):
    df = mumlar_yap([(100, 101, 99.5, 100)] * 8)
    sig = sinyal_yap(df, {0: (1, 90.0, np.nan)})
    for ad, mumlar in kolonlar.items():
        sig[ad] = False
        for i in mumlar:
            sig.iloc[i, sig.columns.get_loc(ad)] = True
    return df, sig


def test_yonlu_cikis_long_cikis_short_sutunu_kapatmaz():
    df, sig = _yonlu_senaryo(cikis_short=[2])
    r = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR))
    assert r.islemler.iloc[0].cikis_nedeni == "veri_sonu"      # long'u short çıkışı kapatmadı


def test_yonlu_cikis_long_cikis_long_sutunu_kapatir():
    df, sig = _yonlu_senaryo(cikis_long=[2])
    t = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR)).islemler.iloc[0]
    assert t.cikis_nedeni == "sinyal" and t.cikis_zamani == df.index[3]


def test_yonlu_cikis_short_pozisyon_ve_genel_cikis():
    df = mumlar_yap([(100, 101, 99.5, 100)] * 8)
    sig = sinyal_yap(df, {0: (-1, 110.0, np.nan)})
    sig["cikis_long"] = False
    sig["cikis_short"] = False
    sig.iloc[2, sig.columns.get_loc("cikis_long")] = True      # short'u kapatmaz
    sig.iloc[4, sig.columns.get_loc("cikis_short")] = True
    t = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR)).islemler.iloc[0]
    assert t.cikis_nedeni == "sinyal" and t.cikis_zamani == df.index[5]
    # genel `cikis` her iki yönü kapatır (sütun varken de)
    sig2 = sinyal_yap(df, {0: (-1, 110.0, np.nan)}, cikislar=[1])
    sig2["cikis_long"] = False
    t2 = backtest(df, Hazir(sig2), MotorAyarlari(**SIFIR)).islemler.iloc[0]
    assert t2.cikis_zamani == df.index[2]
