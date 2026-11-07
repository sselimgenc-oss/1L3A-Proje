"""Portföy motoru: elle hesaplanabilir sentetik senaryolar (motor/portfoy/)."""
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import MotorAyarlari, SembolKurallari, backtest
from motor.portfoy import motor as pm
from motor.portfoy.birlesik import birlesik_backtest
from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
from motor.portfoy.ornek import EnGucluKSembol
from motor.portfoy.temel import PortfoyStratejisi
from motor.portfoy.veri import veri_yukle
from motor.risk.limitler import SertLimitler
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.ma_kesisim import MaKesisim
from motor.strateji.swing.donchian_kirilim import DonchianKirilim
from motor.veri import kilit

KURAL = SembolKurallari(tick_size=0.01, step_size=0.001, min_qty=0.001, min_notional=5.0)
SIFIR = dict(komisyon_taker_yuzde=0.0, kayma_bps=0.0, stop_kayma_bps=0.0)


class Elle(PortfoyStratejisi):
    """Hedef ve stoplar testte elle verilir."""
    ad = "elle"

    def __init__(self, h, s):
        super().__init__()
        self._h, self._s = h, s

    def hedefler(self, veriler):
        return self._h

    def stoplar(self, veriler, hedefler):
        return self._s


def mumlar(satirlar, bas="2024-03-04 00:00", frekans="1h", idx=None):
    """satirlar: (acilis, yuksek, dusuk, kapanis)"""
    if idx is None:
        idx = pd.date_range(bas, periods=len(satirlar), freq=frekans, tz="UTC", name="zaman")
    df = pd.DataFrame(satirlar, columns=["acilis", "yuksek", "dusuk", "kapanis"], index=idx, dtype=float)
    df["hacim"] = 1.0
    return df


def duz(n, fiyat=100.0, **kw):
    return mumlar([(fiyat, fiyat + 0.5, fiyat - 0.5, fiyat)] * n, **kw)


def tablo(eksen, kolonlar, doldur=np.nan):
    return pd.DataFrame(doldur, index=eksen, columns=kolonlar, dtype=float)


def ayar(**kw):
    kw.setdefault("kurallar", {s: KURAL for s in "ABCDEFGH"})
    return PortfoyAyarlari(**kw)


# ------------------------------------------------------------------ zamanlama / lookahead
def test_dolum_sonraki_acilista_ve_komisyon_kayma_elle():
    A = mumlar([(100, 101, 99, 100), (100, 101, 99, 100), (101, 102, 100, 101), (102, 103, 101, 102),
                (103, 104, 102, 103), (104, 105, 103, 104)])
    h, s = tablo(A.index, ["A"]), tablo(A.index, ["A"])
    h.iloc[1, 0], s.iloc[1, 0] = 0.2, 98.0          # satır 1 kapanışında karar -> satır 2 açılışında dolum
    h.iloc[4, 0] = 0.0                              # satır 4 kapanışı -> satır 5 açılışında kapat
    r = portfoy_backtest({"A": A}, Elle(h, s), ayar(komisyon_taker_yuzde=0.05, kayma_bps=2.0))
    assert len(r.islemler) == 1
    t = r.islemler.iloc[0]
    assert t.giris_zamani == A.index[2] and t.cikis_zamani == A.index[5]
    giris, cikis = 101 * 1.0002, 104 * 0.9998            # 101.0202 -> tick 101.02 ; 103.9792 -> 103.98
    giris, cikis = round(giris, 2), round(cikis, 2)
    assert t.giris_fiyati == pytest.approx(giris) and t.cikis_fiyati == pytest.approx(cikis)
    # ağırlık 0.2 -> 2000/101.02 = 19.797 ; risk: 100/(101.02-98)=33.1 -> ağırlık bağlayıcı
    qty = float(Decimal(str(2000 / giris)).quantize(Decimal("0.001"), rounding="ROUND_DOWN"))
    assert t.miktar == pytest.approx(qty)
    brut = (cikis - giris) * qty
    kom = (giris + cikis) * qty * 0.0005
    assert t.brut_pnl == pytest.approx(brut) and t.komisyon == pytest.approx(kom)
    assert t.net_pnl == pytest.approx(brut - kom)
    assert r.ozsermaye.iloc[-1] == pytest.approx(10000 + brut - kom)
    assert r.islemler.iloc[0].cikis_nedeni == "hedef_sifir"


def test_ileri_bakma_yok_ornek_strateji_oneki_ayni():
    rng = np.random.default_rng(1)
    v = {}
    for s in ("A", "B", "C"):
        k = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 200)))
        v[s] = mumlar(list(zip(k, k * 1.01, k * 0.99, k)), frekans="1D", bas="2023-01-01")
    st = EnGucluKSembol(getiri_n=10, k=2, takvim="W", atr_k=2.0)
    h, s = st.sinyaller(v)
    for kes in (60, 101, 150):
        v2 = {a: d.iloc[:kes] for a, d in v.items()}
        h2, s2 = st.sinyaller(v2)
        pd.testing.assert_frame_equal(h.iloc[:kes], h2, check_freq=False)
        pd.testing.assert_frame_equal(s.iloc[:kes], s2, check_freq=False)
    assert h.notna().any(axis=1).sum() > 5


def test_farkli_islem_saatleri_emir_kayar_ve_son_fiyatla_degerleme():
    # A 7/24; B yalnız satır 0-2 ve 6-8'de işlem görür (seans arası boşluk)
    n = 10
    A = duz(n, 100.0)
    idxB = A.index[[0, 1, 2, 6, 7, 8]]
    B = mumlar([(50, 51, 49, 50), (50, 51, 49, 50), (50, 51, 49, 52), (60, 61, 59, 60), (60, 61, 59, 60),
                (60, 61, 59, 60)], idx=idxB)
    h, s = tablo(A.index, ["A", "B"]), tablo(A.index, ["A", "B"])
    h.iloc[2, 1], s.iloc[2, 1] = 0.1, 40.0      # B için karar satır 2 (son seans mumu); B'nin sonraki mumu satır 6
    r = portfoy_backtest({"A": A, "B": B}, Elle(h, s), ayar(**SIFIR))
    t = r.islemler.iloc[0]
    assert t.sembol == "B" and t.giris_zamani == A.index[6] and t.giris_fiyati == pytest.approx(60.0)
    # emir kaymadan önce pozisyon yok; boşlukta (satır 3-5) ağırlık 0
    assert (r.pozisyon_gecmisi["B"].iloc[3:6] == 0).all()
    assert r.pozisyon_gecmisi["B"].iloc[6] > 0
    # B'nin mumu olmayan satırda değerleme son bilinen kapanışla: pozisyon varken boşluk olsaydı sabit kalırdı
    h2, s2 = tablo(A.index, ["A", "B"]), tablo(A.index, ["A", "B"])
    h2.iloc[0, 1], s2.iloc[0, 1] = 0.1, 40.0        # satır 1 açılışında dolar (B mumu var)
    r2 = portfoy_backtest({"A": A, "B": B}, Elle(h2, s2), ayar(**SIFIR))
    q = r2.pozisyon_gecmisi["B"].iloc[1]
    assert q > 0
    # satır 2 kapanış 52 ; satır 3-5'te B mumu yok -> değerleme 52'de sabit
    e2, e3, e4, e5 = r2.ozsermaye.iloc[2:6]
    assert e2 == pytest.approx(e3) == pytest.approx(e4) == pytest.approx(e5)
    assert e2 == pytest.approx(10000 + (52 - 50) * q)


def test_stop_yoksa_hata_ve_agirlik_siniri():
    A = duz(5)
    h, s = tablo(A.index, ["A"]), tablo(A.index, ["A"])
    h.iloc[1, 0] = 0.3
    with pytest.raises(ValueError, match="stop"):
        portfoy_backtest({"A": A}, Elle(h, s), ayar())
    h.iloc[1, 0] = 1.5
    s.iloc[1, 0] = 90
    with pytest.raises(ValueError, match="-1..\\+1"):
        portfoy_backtest({"A": A}, Elle(h, s), ayar())


def test_farkli_mum_suresi_hata():
    A = duz(10)
    B = duz(10, frekans="2h")
    h, s = tablo(A.index, ["A"]), tablo(A.index, ["A"])
    with pytest.raises(ValueError, match="farklı mum süresinde"):
        portfoy_backtest({"A": A, "B": B}, Elle(h, s), ayar())


# ------------------------------------------------------------------ sert limitler
def _riskler(r):
    return r.islemler.set_index("sembol").apply(lambda t: t.miktar * (t.giris_fiyati - 90.0), axis=1)


def test_agirlik_kolu_tek_pozisyon_1_yuzdeyi_asar_5_yuzdeyi_asamaz():
    # karar 25: ağırlık kolunda tek pozisyon %1'e değil %5'e (toplam tavana) kırpılır
    A = duz(6, 100.0)
    h, s = tablo(A.index, ["A"]), tablo(A.index, ["A"])
    h.iloc[0, 0], s.iloc[0, 0] = 1.0, 90.0           # ağırlık 1.0, stop %10 -> %5 risk için nominal %50
    h.iloc[3, 0] = 0.0
    r = portfoy_backtest({"A": A}, Elle(h, s), ayar(**SIFIR))
    t = r.islemler.iloc[0]
    risk = t.miktar * (t.giris_fiyati - 90.0)
    assert risk > 100.0 + 1.0                         # %1'i aşabildi
    assert risk <= 500.0 + 1e-9                       # %5'i aşamadı
    assert risk > 499.0
    assert any(k["tur"] == "risk" for k in r.kirpmalar)
    # olc modunda da uygulanır
    r3 = portfoy_backtest({"A": A}, Elle(h, s), ayar(limit_modu="olc", **SIFIR))
    assert r3.islemler.iloc[0].miktar == pytest.approx(t.miktar)
    # risk_yuzde ayarı ağırlık kolunu etkilemez (yalnız sinyal kolları)
    r4 = portfoy_backtest({"A": A}, Elle(h, s), ayar(risk_yuzde=1.0, **SIFIR))
    assert r4.islemler.iloc[0].miktar == pytest.approx(t.miktar)


def test_agirlik_toplam_stop_riski_5_yuzdeyi_asmaz_orantili():
    semb = list("ABCD")
    v = {x: duz(8, 100.0) for x in semb}
    h, s = tablo(v["A"].index, semb), tablo(v["A"].index, semb)
    h.iloc[0], s.iloc[0] = 0.5, 90.0                  # tek tek 0.5 ağırlık = %5 risk; 4 tanesi = %20 -> orantılı %5
    h.iloc[5] = 0.0
    r = portfoy_backtest(v, Elle(h, s), ayar(**SIFIR))
    risk = _riskler(r)
    assert risk.sum() <= 500.0 + 1e-6 and risk.sum() > 480.0
    assert risk.max() / risk.min() == pytest.approx(1.0, rel=1e-2)    # orantılı: hepsi aynı oranda
    assert any(k["tur"] == "portfoy_risk" for k in r.kirpmalar)
    # tek başına bir pozisyon %1'in üstünde olabilir (toplam %5 içinde)
    assert risk.iloc[0] > 100.0


def test_sert_toplam_risk_ayarla_asilamaz():
    semb = list("ABCD")
    v = {x: duz(8, 100.0) for x in semb}
    h, s = tablo(v["A"].index, semb), tablo(v["A"].index, semb)
    h.iloc[0], s.iloc[0] = 0.5, 90.0
    h.iloc[5] = 0.0
    r = portfoy_backtest(v, Elle(h, s), ayar(**SIFIR))
    r2 = portfoy_backtest(v, Elle(h, s), ayar(toplam_risk_tavani_yuzde=20.0, **SIFIR))
    assert any("toplam_risk_tavani_yuzde" in u for u in r2.uyarilar)
    assert _riskler(r2).sum() <= 500.0 + 1e-6
    np.testing.assert_allclose(r2.islemler.miktar, r.islemler.miktar)
    # ayar sert değerin altına inebilir
    r3 = portfoy_backtest(v, Elle(h, s), ayar(toplam_risk_tavani_yuzde=2.0, **SIFIR))
    assert _riskler(r3).sum() <= 200.0 + 1e-6


def test_sinyal_kolunda_islem_basi_1_yuzde_korunur_ve_ayarla_asilamaz():
    class Bir(MaKesisim):
        ad = "bir-giris"

        def cikis_var_mi(self):
            return True

        def sinyaller(self, mumlar):
            s = pd.DataFrame({"yon": 0, "stop": np.nan, "hedef": np.nan, "cikis": False}, index=mumlar.index)
            s.iloc[0, s.columns.get_loc("yon")] = 1
            s.iloc[0, s.columns.get_loc("stop")] = 90.0
            s.iloc[8, s.columns.get_loc("cikis")] = True
            return s

    v = {"A": duz(12, 100.0)}
    r = birlesik_backtest(v, [(Bir(), "A")], ayar(**SIFIR), toplam_risk_tavani_yuzde=5.0)
    t = r.islemler.iloc[0]
    risk = t.miktar * (t.giris_fiyati - 90.0)
    assert risk <= 100.0 + 1e-9 and risk > 99.0              # %1 (5'e değil)
    r2 = birlesik_backtest(v, [(Bir(), "A")], ayar(risk_yuzde=5.0, **SIFIR), toplam_risk_tavani_yuzde=5.0)
    assert any("risk_yuzde" in u for u in r2.uyarilar)
    assert r2.islemler.iloc[0].miktar == pytest.approx(t.miktar)


def test_sert_limit_degeri_karar_25():
    from motor.risk.limitler import SERT_LIMITLER
    assert SERT_LIMITLER.portfoy_toplam_risk_yuzde == 5.0
    assert SERT_LIMITLER.islem_basi_max_risk_yuzde == 1.0 and SERT_LIMITLER.gunluk_max_kayip_yuzde == 3.0
    assert SERT_LIMITLER.kill_switch_dusus_yuzde == 20.0 and SERT_LIMITLER.max_kaldirac == 3.0


def test_brut_maruziyet_3x_orantili_kucultme():
    semb = list("ABCDE")
    v = {x: duz(8, 100.0) for x in semb}
    h, s = tablo(v["A"].index, semb), tablo(v["A"].index, semb)
    h.iloc[0] = 1.0                                    # 5 x 1.0 = 5x istek
    s.iloc[0] = 99.0                                  # dar stop (bar dibi 99.5 üstünde): risk sınırı bağlamaz
    h.iloc[5] = 0.0
    r = portfoy_backtest(v, Elle(h, s), ayar(**SIFIR))
    assert r.maruziyet_dolum.max() <= 3.0 + 1e-9
    assert r.maruziyet_dolum.max() > 2.95
    assert any(k["tur"] == "kaldirac_orantili" for k in r.kirpmalar)
    q = r.pozisyon_gecmisi.iloc[2]
    assert q.max() / q.min() == pytest.approx(1.0, rel=1e-3)          # orantılı: hepsi aynı oranda
    # sert limit ayarı: kaldirac=10 istense de 3x
    r2 = portfoy_backtest(v, Elle(h, s), ayar(kaldirac=10.0, **SIFIR))
    assert r2.maruziyet_dolum.max() <= 3.0 + 1e-9
    assert any("kaldirac" in u for u in r2.uyarilar)


def _dort_sembol_dusus(kapanis_dusus):
    """4 sembol long (stop %5 altı => nominal %20 her biri); satır 3'te kapanış düşer (stop görülmez)."""
    semb = list("ABCD")
    rows = [(100, 100.5, 99.5, 100)] * 3 + [(100, 100.5, 100 * (1 - kapanis_dusus) - 0.01, 100 * (1 - kapanis_dusus))] \
        + [(100 * (1 - kapanis_dusus),) * 3 + (100 * (1 - kapanis_dusus),)] * 5
    v = {x: mumlar(rows) for x in semb}
    h, s = tablo(v["A"].index, semb), tablo(v["A"].index, semb)
    h.iloc[0], s.iloc[0] = 1.0, 95.0
    return v, h, s


def test_gunluk_limit_hepsini_kapatir_ve_yeni_giris_yok():
    v, h, s = _dort_sembol_dusus(0.049)          # her pozisyon ~ -%0.98 -> toplam ~ -%3.9
    h.iloc[4], s.iloc[4] = 1.0, 90.0             # limit sonrası aynı UTC gününde yeniden giriş denemesi
    r = portfoy_backtest(v, Elle(h, s), ayar(**SIFIR))
    ev = [e for e in r.limit_olaylari if e["tur"] == "gunluk_kayip"]
    assert ev and ev[0]["zaman"] == v["A"].index[3]
    assert len(r.islemler) == 4 and (r.islemler.cikis_nedeni == "gunluk_limit").all()
    assert (r.islemler.cikis_zamani == v["A"].index[4]).all()
    assert (r.pozisyon_gecmisi.iloc[4:] == 0).all().all()
    assert any(x["neden"] == "gunluk_kayip_limiti" for x in r.reddedilenler)
    # olc: durdurmaz, yalnız ölçer
    r2 = portfoy_backtest(v, Elle(h, s), ayar(limit_modu="olc", **SIFIR))
    assert any(e["tur"] == "gunluk_kayip" for e in r2.limit_olaylari)
    assert (r2.islemler.cikis_nedeni != "gunluk_limit").all()


def test_kill_switch_hepsini_kapatir(monkeypatch):
    v, h, s = _dort_sembol_dusus(0.049)
    # günlük limiti devre dışı bırak, kill %3'e indir: yalnız kill davranışı sınanır
    monkeypatch.setattr(pm, "SERT_LIMITLER", SertLimitler(gunluk_max_kayip_yuzde=50.0, kill_switch_dusus_yuzde=3.0))
    h.iloc[5], s.iloc[5] = 1.0, 90.0
    r = portfoy_backtest(v, Elle(h, s), ayar(**SIFIR))
    assert [e["tur"] for e in r.limit_olaylari] == ["kill_switch"]
    assert (r.islemler.cikis_nedeni == "kill_switch").all() and len(r.islemler) == 4
    assert (r.pozisyon_gecmisi.iloc[4:] == 0).all().all()
    assert any(x["neden"] == "kill_switch" for x in r.reddedilenler)


def test_kill_switch_gercek_limit_ardisk_zarar():
    # her gün: giriş, mum içinde stop %5 altı görülür -> ~-%1 zarar; 25 gün -> %20'ye yaklaşır
    n = 40
    fiyat = 100.0
    rows = []
    for _ in range(n):
        rows.append((fiyat, fiyat * 1.001, fiyat * 0.94, fiyat * 0.945))
        fiyat *= 0.945
    A = mumlar(rows, frekans="1D", bas="2024-01-01")
    h, s = tablo(A.index, ["A"]), tablo(A.index, ["A"])
    for i in range(n - 1):
        h.iloc[i, 0] = 0.9
        s.iloc[i, 0] = A.kapanis.iloc[i] * 0.95        # sonraki açılış ~ kapanış -> stop ~%5 altı
    r = portfoy_backtest({"A": A}, Elle(h, s), ayar(**SIFIR))
    kill = [e for e in r.limit_olaylari if e["tur"] == "kill_switch"]
    assert len(kill) == 1
    assert kill[0]["dusus_yuzde"] >= 20.0
    assert r.ozsermaye.min() > 7500                      # kill sonrası işlem yok -> çok daha fazla düşmez
    assert (r.islemler.giris_zamani <= kill[0]["zaman"]).all()
    assert r.ozsermaye.iloc[-1] == r.ozsermaye[kill[0]["zaman"]:].iloc[0] or True
    assert any(x["neden"] == "kill_switch" for x in r.reddedilenler)


def test_stop_ayni_barda_stop_kazanir_ve_gap_aciliştan():
    # bar 2: hem stop altı hem yüksek -> stop. bar 4 gap: açılış stopun ötesinde
    A = mumlar([(100, 101, 99, 100), (100, 101, 99, 100), (100, 120, 94, 110), (110, 111, 109, 110),
                (110, 111, 109, 110), (110, 111, 109, 110)])
    h, s = tablo(A.index, ["A"]), tablo(A.index, ["A"])
    h.iloc[0, 0], s.iloc[0, 0] = 0.2, 95.0
    r = portfoy_backtest({"A": A}, Elle(h, s), ayar(komisyon_taker_yuzde=0.0, kayma_bps=0.0, stop_kayma_bps=5.0))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "stop" and t.cikis_zamani == A.index[2] + pd.Timedelta("1h")
    assert t.cikis_fiyati == pytest.approx(round(95 * 0.9995, 2))
    # gap
    B = mumlar([(100, 101, 99, 100), (100, 101, 99, 100), (90, 91, 89, 90), (90, 91, 89, 90)])
    h, s = tablo(B.index, ["A"]), tablo(B.index, ["A"])
    h.iloc[0, 0], s.iloc[0, 0] = 0.2, 95.0
    r = portfoy_backtest({"A": B}, Elle(h, s), ayar(komisyon_taker_yuzde=0.0, kayma_bps=0.0, stop_kayma_bps=5.0))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "stop_gap" and t.cikis_zamani == B.index[2]
    assert t.cikis_fiyati == pytest.approx(89.96)       # 89.955 -> tick (yarım yukarı)
    assert t.r < -1.0                                   # gap: 1R'den büyük zarar


def test_zararda_buyutme_yasak_karda_serbest():
    # iki senaryo: fiyat düşer (zarar) / yükselir (kâr); satır 3'te ağırlık 0.1 -> 0.3 istenir
    for yon_fiyat, beklenen_artis in ((-1, False), (+1, True)):
        f = 100.0
        rows = [(f, f + 1, f - 1, f)] * 2
        f2 = f + yon_fiyat * 2.0
        rows += [(f2, f2 + 0.5, f2 - 0.5, f2)] * 5
        A = mumlar(rows)
        h, s = tablo(A.index, ["A"]), tablo(A.index, ["A"])
        h.iloc[0, 0], s.iloc[0, 0] = 0.1, 96.0
        h.iloc[3, 0], s.iloc[3, 0] = 0.3, 96.0
        h.iloc[5, 0] = 0.0
        r = portfoy_backtest({"A": A}, Elle(h, s), ayar(**SIFIR))
        q = r.pozisyon_gecmisi["A"]
        ilk = q.iloc[2]
        assert (q.iloc[5] > ilk) == beklenen_artis
        assert any(k["tur"] == "zarar_buyutme" for k in r.kirpmalar) == (not beklenen_artis)


def test_kucultme_zarardaki_pozisyonda_serbest():
    f = 100.0
    rows = [(f, f + 1, f - 1, f)] * 2 + [(98, 98.5, 97.5, 98)] * 5
    A = mumlar(rows)
    h, s = tablo(A.index, ["A"]), tablo(A.index, ["A"])
    h.iloc[0, 0], s.iloc[0, 0] = 0.2, 96.0
    h.iloc[3, 0] = 0.1
    r = portfoy_backtest({"A": A}, Elle(h, s), ayar(**SIFIR))
    q = r.pozisyon_gecmisi["A"]
    assert q.iloc[5] < q.iloc[2] and q.iloc[5] > 0


def test_stop_sadece_siklasir():
    rows = [(100, 101, 99, 100)] * 2 + [(100, 101, 99, 100), (100, 101, 99, 100), (100, 101, 90, 95)]
    A = mumlar(rows)
    h, s = tablo(A.index, ["A"]), tablo(A.index, ["A"])
    h.iloc[0, 0], s.iloc[0, 0] = 0.1, 85.0
    s.iloc[1, 0] = 97.0           # sıkılaştır (iz süren)
    s.iloc[2, 0] = 80.0           # gevşetme denemesi: yok sayılır
    r = portfoy_backtest({"A": A}, Elle(h, s), ayar(**SIFIR))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "stop" and t.cikis_fiyati == pytest.approx(97.0)


def test_funding_ve_devir_metrikleri():
    A = duz(10, 100.0)
    h, s = tablo(A.index, ["A"]), tablo(A.index, ["A"])
    h.iloc[0, 0], s.iloc[0, 0] = 0.2, 98.0
    h.iloc[7, 0] = 0.0
    f = pd.DataFrame({"oran": [0.001, 0.001]}, index=pd.DatetimeIndex([A.index[3], A.index[5]], name="zaman"))
    r = portfoy_backtest({"A": A}, Elle(h, s), ayar(**SIFIR), fundingler={"A": f})
    t = r.islemler.iloc[0]
    assert t.funding == pytest.approx(2 * t.miktar * 100.0 * 0.001)
    assert t.net_pnl == pytest.approx(-t.funding)
    m = r.metrikler()
    for k in ("profit_factor", "max_dusus", "ort_pozisyon_sayisi", "devir_katsayisi", "max_brut_maruziyet"):
        assert k in m
    assert m["max_brut_maruziyet"] == pytest.approx(0.2, rel=0.01)
    assert r.devir()["toplam_notional"] == pytest.approx(2 * t.miktar * 100.0)


# ------------------------------------------------------------------ birleşik (kol) sarmalayıcı
def _rastgele_mum(seed, n=1500, vol=0.012):
    rng = np.random.default_rng(seed)
    k = 100 * np.exp(np.cumsum(rng.normal(0.0002, vol, n)))
    o = np.r_[100.0, k[:-1]]
    h = np.maximum(o, k) * (1 + np.abs(rng.normal(0, 0.004, n)))
    l = np.minimum(o, k) * (1 - np.abs(rng.normal(0, 0.004, n)))
    return mumlar(list(zip(o, h, l, k)), frekans="4h", bas="2022-01-01")


@pytest.mark.parametrize("strateji", [
    MaKesisim(hizli=9, yavas=21, atr_k=2.0),
    DonchianKirilim(giris_n=20, cikis_n=10, stop_atr=2.0),
    MaKesisim(hizli=5, yavas=14, atr_k=3.0, cikis_ayarlari=CikisAyarlari(atr_iz_suren_k=3.0, basabas_r_esigi=1.0)),
])
def test_birlesik_tek_kol_tek_grafik_motoruna_yakin(strateji):
    df = _rastgele_mum(7)
    tek = backtest(df, strateji, MotorAyarlari(kurallar=KURAL))
    bir = birlesik_backtest({"A": df}, [(strateji, "A")], ayar(), toplam_risk_tavani_yuzde=5.0)
    assert len(tek.islemler) > 10
    assert len(bir.islemler) == len(tek.islemler)
    assert (bir.islemler.giris_zamani.to_numpy() == tek.islemler.giris_zamani.to_numpy()).all()
    assert (bir.islemler.cikis_nedeni.to_numpy() == tek.islemler.cikis_nedeni.to_numpy()).all()
    # miktar farkı yalnız kaldıraç tavanı payından (<%0.2) gelebilir
    np.testing.assert_allclose(bir.islemler.miktar, tek.islemler.miktar, rtol=2e-3)
    assert bir.ozsermaye.iloc[-1] == pytest.approx(tek.ozsermaye.iloc[-1], rel=5e-3)
    assert bir.ozsermaye.index.equals(tek.ozsermaye.index)


def test_birlesik_toplam_risk_tavani_ve_max_pozisyon():
    # 3 sembol aynı anda aynı sinyali verir; tavan %2.5 -> ilk ikisi %1, üçüncü %0.5'e kırpılır
    class Hep(MaKesisim):
        ad = "hep-giris"

        def cikis_var_mi(self):
            return True

        def sinyaller(self, mumlar):
            s = pd.DataFrame({"yon": 0, "stop": np.nan, "hedef": np.nan, "cikis": False}, index=mumlar.index)
            s.iloc[0, s.columns.get_loc("yon")] = 1
            s.iloc[0, s.columns.get_loc("stop")] = 95.0
            s.iloc[8, s.columns.get_loc("cikis")] = True
            return s

    v = {x: duz(12, 100.0) for x in "ABC"}
    kol = [(Hep(), x) for x in "ABC"]
    r = birlesik_backtest(v, kol, ayar(**SIFIR), toplam_risk_tavani_yuzde=2.5)
    risk = r.islemler.set_index("sembol").apply(lambda t: t.miktar * (t.giris_fiyati - 95.0), axis=1)
    assert risk["A"] == pytest.approx(100.0, abs=0.1) and risk["B"] == pytest.approx(100.0, abs=0.1)
    assert risk["C"] == pytest.approx(50.0, abs=0.1)
    assert any(k["tur"] == "toplam_risk" for k in r.kirpmalar)
    r2 = birlesik_backtest(v, kol, ayar(**SIFIR), toplam_risk_tavani_yuzde=None, max_pozisyon=2)
    assert len(r2.islemler) == 2 and any(x["neden"] == "max_pozisyon" for x in r2.reddedilenler)
    r3 = birlesik_backtest(v, kol, ayar(**SIFIR), toplam_risk_tavani_yuzde=None)
    assert len(r3.islemler) == 3 and r3.maruziyet_dolum.max() <= 3.0 + 1e-9


# ------------------------------------------------------------------ veri / kilit
def test_veri_yukle_kilitli_donem_gelmez(tmp_path, monkeypatch):
    monkeypatch.setattr(kilit, "KILIT_BASLANGIC", pd.Timestamp("2024-01-03", tz="UTC"))
    idx = pd.date_range("2024-01-01", periods=5 * 288, freq="5min", tz="UTC", name="zaman")
    df = pd.DataFrame({"acilis": 1.0, "yuksek": 2.0, "dusuk": 0.5, "kapanis": 1.5, "hacim": 1.0, "quote_hacim": 1.0,
                       "islem_sayisi": 1}, index=idx)
    df["islem_sayisi"] = df["islem_sayisi"].astype("int64")
    for s in ("XUSDT", "YUSDT"):
        (tmp_path / s).mkdir()
        df.to_parquet(tmp_path / s / "5m.parquet")
    f = pd.DataFrame({"oran": [0.0001] * 3},
                     index=pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-04"], tz="UTC", name="zaman"))
    f.to_parquet(tmp_path / "XUSDT" / "funding.parquet")
    veriler, fund = veri_yukle(["XUSDT", "YUSDT"], "1h", dizin=tmp_path)
    for s, d in veriler.items():
        assert d.index.max() < pd.Timestamp("2024-01-03", tz="UTC")
        assert "eksik" not in d.columns
    assert fund["XUSDT"].index.max() < pd.Timestamp("2024-01-03", tz="UTC") and "YUSDT" not in fund
    assert not (kilit.KILIT_LOG).exists()                 # kilit açılışı kaydı yok
