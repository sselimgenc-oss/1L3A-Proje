"""B10c (2026-11-10): tick'e yuvarlanmış dolum kaldıraç tavanını aşamaz. Dolum fiyatı borsa tick'ine yuvarlandığından GERÇEKLEŞEN kayma
|dolum - ham| / ham nominal kaymadan büyük olabilir (XRP benzeri: tick 0.0001, fiyat ~0.512, kayma 5 bps -> ~5.86 bps). Tavan paydası yalnız
nominal kaymayı taşıyınca tavandaki pozisyon 3x'i 3.0001-3.0008 aşıyor, kucult_emri / kaldirac_azalt doğuruyordu.
Düzeltme: tavan paydasındaki kayma = max(nominal, gerçekleşen) (tek grafik: dolum başına; portföy/paper: o satırın emirlerinin en büyüğü). Ağ yok."""
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, SembolKurallari, backtest
from motor.canli import paper as pp
from motor.canli.paper_motor import PaperMotor
from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
from motor.strateji.cikislar import CikisAyarlari
from testler.test_b10_short_kaldirac import HepsiShort
from testler.test_bt_motor import Hazir, mumlar_yap, sinyal_yap
from testler.test_paper_motor import duz, tanim
from testler.test_portfoy_motor import Elle, mumlar, tablo

FIYAT = 0.512
KURAL = SembolKurallari(0.0001, 0.0001, 0.0001, 5.0)        # XRP benzeri: kaba tick, ince step
KAYMA_BPS = 5.0


def _gerceklesen_kayma(yon):
    """Önkoşul: bu kurallarla tick yuvarlaması gerçekleşen kaymayı nominalin gerçekten üstüne çıkarıyor."""
    dolum = round(round(FIYAT * (1 + yon * KAYMA_BPS / 1e4), 4), 4)
    return abs(dolum - FIYAT) / FIYAT * 1e4


@pytest.mark.parametrize("yon", [1, -1])
def test_onkosul_tick_gerceklesen_kaymayi_nominalin_ustune_cikarir(yon):
    assert _gerceklesen_kayma(yon) > KAYMA_BPS + 0.5


# ---------------------------------------------------------------------------- tek grafik
@pytest.mark.parametrize("yon", [1, -1])
def test_tek_grafik_tick_yuvarlamasi_tavani_asmaz(yon):
    df = mumlar_yap([(FIYAT, FIYAT + 0.002, FIYAT - 0.002, FIYAT)] * 6)
    sig = sinyal_yap(df, {0: (yon, FIYAT - yon * 0.0005, np.nan)})     # dar stop: boyutu kaldıraç tavanı belirler
    ay = MotorAyarlari(komisyon_taker_yuzde=0.05, kayma_bps=KAYMA_BPS, kurallar=KURAL)
    r = backtest(df, Hazir(sig, CikisAyarlari(zaman_cikisi_mum=1000)), ay)
    assert len(r.islemler) == 1
    assert "kaldirac_azalt" not in set(r.islemler.cikis_nedeni)
    t = r.islemler.iloc[0]
    q, fiyat, ham = Decimal(repr(float(t.miktar))), Decimal(repr(float(t.giris_fiyati))), Decimal(repr(FIYAT))
    ozs_sonra = Decimal(10000) - q * fiyat * Decimal("0.0005") - q * abs(fiyat - ham)
    brut = q * ham / ozs_sonra
    assert brut <= Decimal(3) + Decimal("1e-9")
    assert brut >= Decimal("2.99")                                   # tavan gerçekten belirleyici


# ---------------------------------------------------------------------------- portföy motoru
@pytest.mark.parametrize("yon", [1, -1])
def test_portfoy_tick_yuvarlamasi_tavani_asmaz_ve_azaltma_uretmez(yon):
    n = 6
    ad = ["A", "B", "C", "D"]
    veri = {k: mumlar([(FIYAT, FIYAT + 0.002, FIYAT - 0.002, FIYAT)] * n, frekans="1D") for k in ad}
    ix = veri["A"].index
    h, s = tablo(ix, ad), tablo(ix, ad)
    h.iloc[0, :], s.iloc[0, :] = float(yon), FIYAT - yon * 0.005
    ay = PortfoyAyarlari(komisyon_taker_yuzde=0.05, kayma_bps=KAYMA_BPS, kurallar={k: KURAL for k in ad})
    r = portfoy_backtest(veri, Elle(h, s), ay)
    assert len(r.islemler) == 4
    assert "kaldirac_azalt" not in set(r.islemler.cikis_nedeni)
    assert float(r.maruziyet["brut"].max()) <= 3.0 + 1e-9


# ---------------------------------------------------------------------------- paper motoru
@pytest.mark.parametrize("yon", [1, -1])
def test_paper_tick_yuvarlamasi_tavani_asmaz_ve_azaltma_uretmez(monkeypatch, yon):
    tans = [tanim(f"k{i}|S{i}USDT|1d", f"S{i}USDT", grup=f"g{i}", pay="1", stop_yuzde=0.05) for i in range(4)]
    if yon == -1:
        for t in tans:
            t.nesne, t.strateji_ad = HepsiShort(stop_yuzde=0.05), "test__hepsi_short"
    mum = {(t.sembol, "1d"): duz(10, FIYAT, dalga=0.0) for t in tans}
    kur = {t.sembol: KURAL for t in tans}
    kirpilan, kucult = [], []
    orj_kirp, orj_kapanis = PaperMotor._kirp, PaperMotor.kapanis_fazi

    def kirp(self, t, kol, neden, *a, **k):
        kirpilan.append(neden)
        return orj_kirp(self, t, kol, neden, *a, **k)

    def kapanis(self, b, t, karar_fn, son_satir=False):
        orj_kapanis(self, b, t, karar_fn, son_satir)
        kucult.extend(k.kucult_emri for k in self.tum_kollar if k.kucult_emri is not None)

    monkeypatch.setattr(PaperMotor, "_kirp", kirp)
    monkeypatch.setattr(PaperMotor, "kapanis_fazi", kapanis)
    p = pp.tekrar_calistir(tans, mum, {}, kur, mum[("S0USDT", "1d")].index[6], ayarlar=PortfoyAyarlari(kayma_bps=KAYMA_BPS), kapat=False)
    m = p.motor
    assert len(m.acik) > 0 and all(q.yon == yon for q in m.acik.values())
    assert "kaldirac_orantili" in kirpilan                        # tavan gerçekten devrede
    assert m.brut_kaldirac() <= 3.0 + 1e-9
    assert "kaldirac_azalt" not in kirpilan and not kucult
    assert not any(i["cikis_nedeni"] == "kaldirac_azalt" for i in m.islemler)
