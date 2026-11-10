"""B10b (2026-11-10): kaldıraç tavanı SHORT'ta da aşılmaz. Brüt maruziyet ham fiyatla ölçülür; short dolum fiyatı ham fiyatın altında
olduğundan tavan dolum fiyatıyla hesaplanınca tavandaki short ilk kapanışta `kucult_emri`, sonraki açılışta `kaldirac_azalt` doğuruyordu.
Düzeltme: tavan miktarı max(ham, dolum) fiyatıyla hesaplanır (long'da dolum >= ham olduğundan davranış aynı). Ağ yok."""
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, SembolKurallari, backtest, kaldirac_tavani_miktar
from motor.canli import paper as pp
from motor.canli.paper_motor import PaperMotor
from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.temel import Strateji
from testler.test_bt_motor import Hazir, mumlar_yap, sinyal_yap
from testler.test_paper_motor import duz, tanim
from testler.test_portfoy_motor import Elle, ayar, mumlar, tablo


# ---------------------------------------------------------------------------- tek grafik (backtest.motor)
@pytest.mark.parametrize("yon", [1, -1])
@pytest.mark.parametrize("olumsuz", [0.0, 0.5])
def test_tek_grafik_tavandaki_pozisyon_ham_fiyatla_3x_asmaz(yon, olumsuz):
    df = mumlar_yap([(100, 100.4, 99.6, 100)] * 6)
    sig = sinyal_yap(df, {0: (yon, 100 - yon * 0.01, np.nan)})     # dar stop: boyutu kaldıraç tavanı belirler
    ay = MotorAyarlari(komisyon_taker_yuzde=0.05, kayma_bps=20.0, olumsuz_dolum=olumsuz)
    r = backtest(df, Hazir(sig, CikisAyarlari(zaman_cikisi_mum=1000)), ay)
    assert len(r.islemler) == 1
    t = r.islemler.iloc[0]
    q, fiyat, ham = Decimal(repr(float(t.miktar))), Decimal(repr(float(t.giris_fiyati))), Decimal("100")
    ozs_sonra = Decimal(10000) - q * fiyat * Decimal("0.0005") - q * abs(fiyat - ham)
    # ham fiyatla ölçülen brüt (short'ta dolumdan büyük), dolum sonrası özsermayeye göre 3x'i aşmaz
    assert q * max(fiyat, ham) / ozs_sonra <= Decimal(3) + Decimal("1e-9")
    assert q * ham / ozs_sonra <= Decimal(3) + Decimal("1e-9")


@pytest.mark.parametrize("yon, beklenen_fiyat", [(1, "100.2"), (-1, "100")])
def test_tek_grafik_tavan_fiyati_max_ham_dolum(monkeypatch, yon, beklenen_fiyat):
    # long: dolum (100.2) >= ham -> tavan fiyatı eskisiyle aynı; short: dolum 99.8 < ham 100 -> tavan ham fiyatla
    import motor.backtest.motor as bm
    gorulen = []

    def kayit(nakit, kaldirac, taker, fiyat):
        gorulen.append(fiyat)
        return kaldirac_tavani_miktar(nakit, kaldirac, taker, fiyat)

    monkeypatch.setattr(bm, "kaldirac_tavani_miktar", kayit)
    df = mumlar_yap([(100, 100.4, 99.6, 100)] * 6)
    sig = sinyal_yap(df, {0: (yon, 100 - yon * 0.01, np.nan)})
    backtest(df, Hazir(sig, CikisAyarlari(zaman_cikisi_mum=1000)), MotorAyarlari(komisyon_taker_yuzde=0.05, kayma_bps=20.0))
    assert gorulen == [Decimal(beklenen_fiyat)]


# ---------------------------------------------------------------------------- portföy motoru
@pytest.mark.parametrize("yon", [1, -1])
def test_portfoy_tavandaki_pozisyon_kucult_ve_kaldirac_azalt_uretmez(yon):
    n = 6
    ad = ["A", "B", "C", "D"]
    veri = {k: mumlar([(100, 100.5, 99.5, 100)] * n, frekans="1D") for k in ad}
    ix = veri["A"].index
    h, s = tablo(ix, ad), tablo(ix, ad)
    h.iloc[0, :], s.iloc[0, :] = float(yon), 100 - yon * 1.0     # 4 x 1x istenir -> orantılı olarak 3x tavana kırpılır
    r = portfoy_backtest(veri, Elle(h, s), ayar(komisyon_taker_yuzde=0.05, kayma_bps=20.0))
    assert len(r.islemler) == 4
    assert "kaldirac_azalt" not in set(r.islemler.cikis_nedeni)
    assert float(r.maruziyet["brut"].max()) <= 3.0 + 1e-9


# ---------------------------------------------------------------------------- paper motoru
class HepsiShort(Strateji):
    ad = "test__hepsi_short"
    stil = "swing"
    varsayilan_parametreler = {"stop_yuzde": 1.0}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=1000)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, mumlar):
        c = mumlar["kapanis"]
        return pd.DataFrame({"yon": -1, "stop": c * (1 + self.parametreler["stop_yuzde"] / 100), "hedef": np.nan,
                             "cikis": False}, index=mumlar.index)


@pytest.mark.parametrize("yon", [1, -1])
def test_paper_tavandaki_pozisyon_kucult_ve_kaldirac_azalt_uretmez(monkeypatch, yon):
    tans = [tanim(f"k{i}|S{i}USDT|1d", f"S{i}USDT", grup=f"g{i}", pay="1", stop_yuzde=0.05) for i in range(4)]
    if yon == -1:
        for t in tans:
            t.nesne, t.strateji_ad = HepsiShort(stop_yuzde=0.05), "test__hepsi_short"
    mum = {(t.sembol, "1d"): duz(10, 100.0, dalga=0.0) for t in tans}
    kur = {t.sembol: SembolKurallari(0.01, 0.001, 0.001, 5.0) for t in tans}
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
    p = pp.tekrar_calistir(tans, mum, {}, kur, mum[("S0USDT", "1d")].index[6], ayarlar=PortfoyAyarlari(kayma_bps=20.0), kapat=False)
    m = p.motor
    assert len(m.acik) > 0 and all(q.yon == yon for q in m.acik.values())
    assert "kaldirac_orantili" in kirpilan                        # tavan gerçekten devrede
    assert m.brut_kaldirac() <= 3.0 + 1e-9
    assert "kaldirac_azalt" not in kirpilan and not kucult
    assert not any(i["cikis_nedeni"] == "kaldirac_azalt" for i in m.islemler)
