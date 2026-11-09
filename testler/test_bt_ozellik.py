"""Aşama 1A: zorunlu çıkış, günlük limit kapatma, kısmi kâr, metrikler, eleme, deneme kaydı."""
import numpy as np
import pandas as pd
import pytest

from motor.backtest import deneme_kaydi
from motor.backtest.eleme import Esikler, degerlendir
from motor.backtest.metrikler import hesapla
from motor.backtest.motor import CikisYokHatasi, MotorAyarlari, SembolKurallari, backtest
from motor.backtest.walk_forward import walk_forward
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.ma_kesisim import MaKesisim
from motor.strateji.swing.dar_aralik_kirilim import DarAralikKirilim
from testler.test_bt_motor import SIFIR, Hazir, mumlar_yap, sinyal_yap
from testler.test_bt_strateji import rastgele_mumlar


class HazirCikissiz(Hazir):
    def cikis_var_mi(self):
        return False


# ---------- 1) zorunlu çıkış ----------
def test_cikis_yoksa_hata():
    df = mumlar_yap([(100, 100, 100, 100)] * 4)
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)})
    with pytest.raises(ValueError, match="ilk stop dışında çıkış yok"):
        backtest(df, HazirCikissiz(sig), MotorAyarlari(**SIFIR))
    # CikisAyarlari'nda herhangi bir çıkış varsa geçer
    for ca in (CikisAyarlari(zaman_cikisi_mum=2), CikisAyarlari(sabit_r_hedefi=2.0),
               CikisAyarlari(atr_iz_suren_k=2.0)):
        backtest(df, HazirCikissiz(sig, ca), MotorAyarlari(**SIFIR))
    # başabaş ve kısmi kâr tek başına çıkış sayılmaz (kalan pozisyon yalnız stopla kapanır)
    for ca in (CikisAyarlari(basabas_r_esigi=1.0), CikisAyarlari(kismi=((1.0, 0.5),))):
        with pytest.raises(CikisYokHatasi):
            backtest(df, HazirCikissiz(sig, ca), MotorAyarlari(**SIFIR))


def test_strateji_cikis_var_mi_parametreye_gore():
    assert DarAralikKirilim(hedef_r=0.0).cikis_var_mi() is False
    assert DarAralikKirilim(hedef_r=2.0).cikis_var_mi() is True
    assert MaKesisim().cikis_var_mi() is True
    from motor.strateji.swing.bant_donus import BantDonus
    assert BantDonus(hedef_tipi="yok").cikis_var_mi() is False
    assert BantDonus().cikis_var_mi() is True
    df = rastgele_mumlar(n=300)
    with pytest.raises(ValueError, match="ilk stop dışında çıkış yok"):
        backtest(df, DarAralikKirilim(hedef_r=0.0))
    backtest(df, DarAralikKirilim(hedef_r=0.0, cikis_ayarlari=CikisAyarlari(zaman_cikisi_mum=5)))


class _KosulluCikis(MaKesisim):
    varsayilan_parametreler = {**MaKesisim.varsayilan_parametreler, "var_cikis": True}

    def cikis_var_mi(self):
        return self.parametreler["var_cikis"]


def test_walk_forward_cikissiz_kombinasyonu_atlar(tmp_path):
    df = rastgele_mumlar(n=24 * 120, seed=3)
    s = _KosulluCikis()
    s.parametre_izgarasi = {"hizli": [5], "var_cikis": [False, True]}
    r = walk_forward(s, df, egitim_gun=40, test_gun=20, min_islem=1, isinma_mum=100,
                     deneme_kaydi_yolu=tmp_path / "k.jsonl")
    assert r["atlanan"] == [{"hizli": 5, "var_cikis": False}]
    assert all(p["secilen"]["var_cikis"] for p in r["pencereler"] if p["secilen"])


# ---------- 2) günlük limit pozisyonu kapatır ----------
def _gunluk_limit_senaryosu():
    # stop kayması %0.6: her stop ~1.29R*... kaybı; 3. pozisyon açıkken gün -%3'ü aşar
    satir = [(100, 100, 100, 100), (100, 100.5, 97, 99),
             (99, 100, 99, 100), (100, 100.5, 97, 99),
             (99, 100, 99, 100), (100, 100, 99.0, 99.0),
             (99, 99, 99, 99), (99, 99, 99, 99), (99, 99, 99, 99)]
    df = mumlar_yap(satir)
    girisler = {0: (1, 98.0, np.nan), 2: (1, 98.0, np.nan), 4: (1, 98.0, np.nan), 5: (1, 98.0, np.nan)}
    return df, girisler


def test_gunluk_limit_acik_pozisyonu_kapatir(monkeypatch):
    # Mekanizma testi: boyut eski (yalnız fiyat riski) formülle sabitlenir. Maliyet dahil risk (2026-11-09) ile her işlem ≤ %1 olduğundan
    # 2 stop + açık pozisyon -%3'e ulaşamaz; maliyet dahil boyutun kendisi test_maliyet_dahil_risk.py'de.
    import motor.backtest.motor as bm
    monkeypatch.setattr(bm, "maliyetli_risk_birim", lambda g, s, k, t: abs(g - s))
    df, girisler = _gunluk_limit_senaryosu()
    ay = dict(komisyon_taker_yuzde=0.0, kayma_bps=0.0, stop_kayma_bps=60.0)
    r = backtest(df, Hazir(sinyal_yap(df, girisler, cikislar=[7])), MotorAyarlari(**ay))
    assert len(r.islemler) == 3
    t = r.islemler.iloc[2]
    assert t.cikis_nedeni == "gunluk_limit"
    assert t.cikis_zamani == df.index[6]                          # limit mumundan sonraki açılış
    assert t.cikis_fiyati == pytest.approx(98.41)                  # 99*(1-0.006)=98.406 -> tick
    assert any(x["neden"] == "gunluk_kayip_limiti" for x in r.reddedilenler)   # aynı gün yeni giriş yok
    # olc modu: pozisyon kapanmaz, yalnız kayıt
    r2 = backtest(df, Hazir(sinyal_yap(df, girisler, cikislar=[7])), MotorAyarlari(**ay, limit_modu="olc"))
    assert r2.islemler.iloc[2].cikis_nedeni == "sinyal"
    assert any(o["tur"] == "gunluk_kayip" for o in r2.limit_olaylari)


# ---------- 3) kısmi kâr ----------
def _kismi_df():
    return mumlar_yap([(100, 100, 100, 100),
                       (100, 102.5, 99.5, 101),      # giriş 100; 1R=102 görülür
                       (101, 106.5, 100.5, 106),     # hedef 106
                       (106, 106, 106, 106)])


def test_kismi_kar_tek_satir_ve_hesap():
    df = _kismi_df()
    sig = sinyal_yap(df, {0: (1, 98.0, 106.0)})
    ca = CikisAyarlari(kismi=((1.0, 0.25),))
    r = backtest(df, Hazir(sig, ca), MotorAyarlari(**SIFIR))
    assert len(r.islemler) == 1
    t = r.islemler.iloc[0]
    # miktar 50; 12.5 @102 (+25) ; 37.5 @106 (+225)
    assert t.miktar == pytest.approx(50.0)
    assert t.kismi_sayisi == 1 and t.kismi_pnl == pytest.approx(25.0)
    assert t.brut_pnl == pytest.approx(250.0) and t.net_pnl == pytest.approx(250.0)
    assert t.cikis_nedeni == "hedef" and t.cikis_fiyati == pytest.approx(106.0)
    assert t.r == pytest.approx(250.0 / 100.0)
    assert r.ozsermaye.iloc[-1] == pytest.approx(10250.0)
    # taker %0.05: maliyet dahil risk (2026-11-09) -> miktar = 100 / (2 + 100·2·0.0005) = 47.619; kısmi 11.904 @102, kalan 35.715 @106
    # komisyon: giriş 2.38095 + kısmi 0.607104 + hedef 1.892895 = 4.880949
    r = backtest(df, Hazir(sig, ca), MotorAyarlari(komisyon_taker_yuzde=0.05, kayma_bps=0.0, stop_kayma_bps=0.0))
    t = r.islemler.iloc[0]
    assert t.miktar == pytest.approx(47.619)
    assert t.komisyon == pytest.approx(4.880949)
    assert t.kismi_pnl == pytest.approx(11.904 * 2 - 0.607104)
    assert t.net_pnl == pytest.approx(11.904 * 2 + 35.715 * 6 - 4.880949)


def test_kismi_ayni_mumda_stop_degerse_uygulanmaz():
    df = mumlar_yap([(100, 100, 100, 100), (100, 102.5, 97, 99), (99, 99, 99, 99)])
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)})
    r = backtest(df, Hazir(sig, CikisAyarlari(kismi=((1.0, 0.25),))), MotorAyarlari(**SIFIR))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "stop" and t.kismi_sayisi == 0 and t.kismi_pnl == 0.0
    assert t.net_pnl == pytest.approx(-100.0)


def test_kismi_step_asagi_ve_kalan_min_qty():
    kural = SembolKurallari(step_size=1.0, min_qty=1.0)
    df = _kismi_df()
    sig = sinyal_yap(df, {0: (1, 98.0, 106.0)})
    r = backtest(df, Hazir(sig, CikisAyarlari(kismi=((1.0, 0.25),))), MotorAyarlari(**SIFIR, kurallar=kural))
    t = r.islemler.iloc[0]
    # 50*0.25=12.5 -> 12 @102 (+24) ; 38 @106 (+228)
    assert t.kismi_pnl == pytest.approx(24.0) and t.brut_pnl == pytest.approx(252.0)
    # %100 kısmi: kalan 0 < min_qty -> tamamı kapanır
    r = backtest(df, Hazir(sig, CikisAyarlari(kismi=((1.0, 1.0),))), MotorAyarlari(**SIFIR, kurallar=kural))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "kismi_tam" and t.cikis_fiyati == pytest.approx(102.0)
    assert t.brut_pnl == pytest.approx(100.0) and len(r.islemler) == 1
    # oran yuvarlamada 0 olursa seviye atlanır
    r = backtest(df, Hazir(sig, CikisAyarlari(kismi=((1.0, 0.01),))), MotorAyarlari(**SIFIR, kurallar=kural))
    assert r.islemler.iloc[0].kismi_sayisi == 0


def test_kismi_funding_kalan_miktar_uzerinden():
    df = mumlar_yap([(100, 100, 100, 100), (100, 102.5, 99.5, 101), (100, 101, 99.5, 100),
                     (100, 100, 100, 100), (100, 100, 100, 100)])
    fd = pd.DataFrame({"oran": [0.001, 0.001]},
                      index=pd.DatetimeIndex(["2024-01-01 01:30", "2024-01-01 02:00"], tz="UTC", name="zaman"))
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)}, cikislar=[2])
    r = backtest(df, Hazir(sig, CikisAyarlari(kismi=((1.0, 0.25),))), MotorAyarlari(**SIFIR), funding=fd)
    t = r.islemler.iloc[0]
    # 01:30 -> tam miktar 50*100*0.001=5 ; 02:00 -> kalan 37.5*100*0.001=3.75
    assert t.funding == pytest.approx(8.75)
    assert t.net_pnl == pytest.approx(25.0 - 8.75)


def test_kismi_kapali_varsayilan_davranis_degismez():
    df = _kismi_df()
    sig = sinyal_yap(df, {0: (1, 98.0, 106.0)})
    t = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR)).islemler.iloc[0]
    assert t.kismi_sayisi == 0 and t.kismi_pnl == 0.0 and t.brut_pnl == pytest.approx(300.0)


# ---------- 6) metrikler ----------
def test_ozsermaye_acik_pozisyon_kz_icerir():
    df = mumlar_yap([(100, 100, 100, 100), (100, 101, 99.5, 101), (101, 101, 101, 101)])
    sig = sinyal_yap(df, {0: (1, 98.0, np.nan)})
    r = backtest(df, Hazir(sig), MotorAyarlari(**SIFIR))
    # 1. mum kapanışı: 50 adet * (101-100) = +50 gerçekleşmemiş
    assert r.ozsermaye.iloc[1] == pytest.approx(10050.0)


def test_en_iyi_yuzde5_haric_ve_gunluk_mtm():
    net = [100.0] + [10.0] * 9 + [-5.0] * 10
    k = len(net)
    zaman = pd.date_range("2024-01-01", periods=k + 1, freq="1h", tz="UTC")
    isl = pd.DataFrame({"net_pnl": net, "r": 1.0, "komisyon": 0.0, "funding": 0.0,
                        "giris_zamani": zaman[:k], "cikis_zamani": zaman[1:]})
    idx = pd.date_range("2024-01-01", periods=72, freq="1h", tz="UTC")
    oz = pd.Series(100.0, index=idx)
    oz.iloc[23] = 110.0                       # gün 1 sonu
    oz.iloc[30:36] = 50.0                     # gün 2 içi dip (görmezden gelinir)
    oz.iloc[47] = 99.0                        # gün 2 sonu
    oz.iloc[71] = 120.0                       # gün 3 sonu
    m = hesapla(isl, oz, 100.0)
    # 20 işlem -> en iyi 1 (100) çıkar: net 90-50=40, PF 90/50
    assert m["en_iyi_yuzde5_haric_net"] == pytest.approx(40.0)
    assert m["en_iyi_yuzde5_haric_pf"] == pytest.approx(1.8)
    assert m["gunluk_mtm_max_dusus"] == pytest.approx((110 - 99) / 110)


# ---------- 7) eleme ----------
def _wf(**m):
    taban = dict(net_getiri=0.2, profit_factor=1.5, islem_sayisi=80, en_iyi_yuzde5_haric_pf=1.1)
    return {"metrikler": {**taban, **m}}


def test_eleme():
    assert degerlendir(_wf()) == {"gecti": True, "nedenler": []}
    for kus, anahtar in [(dict(net_getiri=0.0), "net getiri"), (dict(profit_factor=1.19), "PF"),
                         (dict(islem_sayisi=49), "işlem"), (dict(en_iyi_yuzde5_haric_pf=0.89), "%5")]:
        s = degerlendir(_wf(**kus))
        assert not s["gecti"] and len(s["nedenler"]) == 1 and anahtar in s["nedenler"][0]
    assert degerlendir(_wf(profit_factor=1.2, islem_sayisi=50, en_iyi_yuzde5_haric_pf=0.9, net_getiri=1e-6))["gecti"]
    assert not degerlendir(_wf(profit_factor=float("nan")))["gecti"]
    assert not degerlendir({"metrikler": {}})["gecti"]
    assert degerlendir(_wf(profit_factor=1.0), Esikler(min_pf=1.0))["gecti"]


# ---------- 5) deneme kaydı ----------
def test_deneme_kaydi(tmp_path):
    yol = tmp_path / "alt" / "k.jsonl"
    assert deneme_kaydi.toplam_deneme(yol=yol) == 0
    df = rastgele_mumlar(n=24 * 120, seed=3)
    s = MaKesisim()
    s.parametre_izgarasi = {"hizli": [5, 9], "yavas": [21]}
    r = walk_forward(s, df, egitim_gun=40, test_gun=20, min_islem=1, isinma_mum=100,
                     sembol="BTCUSDT", deneme_kaydi_yolu=yol)
    walk_forward(s, df, egitim_gun=40, test_gun=20, min_islem=1, isinma_mum=100, deneme_kaydi_yolu=yol)
    satirlar = deneme_kaydi.oku(yol)
    assert len(satirlar) == 2
    k = satirlar[0]
    assert k["strateji"] == "swing__ma-kesisim" and k["sembol"] == "BTCUSDT" and k["aralik"] == "1h"
    assert k["kombinasyon_sayisi"] == 2 and k["pencere_sayisi"] == len(r["pencereler"])
    secilen = sum(1 for p in r["pencereler"] if p["secilen"])
    assert k["toplam_kosu"] == k["pencere_sayisi"] * 2 + secilen == r["toplam_kosu"]
    assert deneme_kaydi.toplam_deneme(yol=yol) == 2 * k["toplam_kosu"]
    assert deneme_kaydi.toplam_deneme("swing__ma-kesisim", yol) == 2 * k["toplam_kosu"]
    assert deneme_kaydi.toplam_deneme("yok", yol) == 0
