"""CANLI_LIMITLER (kullanıcı kararı 2026-11-11): saf fonksiyonlar, yürütücü entegrasyonu, hesap kill; SERT_LIMITLER'in DEĞİŞMEDİĞİ."""
import dataclasses
import inspect
import json
from decimal import Decimal as D

import pandas as pd
import pytest

from motor.canli.borsa import calistir as cal
from motor.canli.borsa import canli_limitler as cl
from motor.canli.borsa import canli_yurutucu, kurallar
from motor.canli.borsa.canli_limitler import CANLI_LIMITLER as L
from motor.canli.borsa.canli_yurutucu import Ayar, Yurutucu
from motor.risk.limitler import SERT_LIMITLER
from testler.test_canli_borsa import ARALIK, T0, Ortam, Sahte, ac_niyeti, bilgi, gor

KMT = dict(stop_kayma=D("0.0005"), taker=D("0.0005"))
ADIM = dict(adim=D("0.001"), min_qty=D("0.001"), min_tutar=D(100))


def hesap(kasa=1000, giris=50000, stop=49000, **kw):
    return cl.miktar_hesapla(kasa=D(kasa), yon=1, giris=D(giris), stop=D(stop), **KMT, **ADIM, **kw)


def test_kural_degerleri_ve_dondurulmus():
    assert (L.islem_basi_max_kayip_oran, L.islem_basi_max_marj_oran, L.islem_basi_max_nominal_kat, L.toplam_stop_riski_oran,
            L.brut_nominal_kat, L.gunluk_max_kayip_oran, L.strateji_kill_oran, L.hesap_kill_oran) == (0.03, 0.5, 1.5, 0.06, 1.5, 0.06, 0.30, 0.20)
    assert (L.stop_yakin_siniri_oran, L.kaldirac_yakin, L.kaldirac_uzak) == (0.15, 3, 2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        L.islem_basi_max_kayip_oran = 1


def test_dar_stop_nominal_tavani_baglar():
    s = hesap(stop=49950)                                  # stop %0.1: kayıp tavanı büyük (~0.17), nominal tavanı 0.03
    assert s.neden is None and s.qty == D("0.030") and s.baglayan in ("nominal", "marj") and s.kaldirac == 3
    assert s.qty * 50000 <= D("1.5") * 1000


def test_genis_stop_kayip_tavani_baglar():
    s = hesap(stop=45000)                                  # stop %10: 30/(5000+75) = 0.00591 -> 0.005
    assert s.baglayan == "kayip" and s.qty == D("0.005") and s.kaldirac == 3
    kayip = s.qty * (D(5000) + D(50000) * D("0.0015"))
    assert kayip <= D("0.03") * 1000


def test_min_tutar_alti_atlanir_yukari_yuvarlanmaz():
    s = hesap(kasa=50)                                     # ham 0.0014 -> 0.001 -> tutar 50 < 100
    assert s.qty == 0 and s.neden == "min_tutar_alti" and "YUKARI YUVARLANMAZ" in s.ayrinti
    s2 = cl.miktar_hesapla(kasa=D(1000), yon=1, giris=D(50000), stop=D(49000), **KMT, adim=D("0.001"), min_qty=D("0.05"), min_tutar=D(5))
    assert s2.neden == "min_tutar_alti" and s2.qty == 0


def test_kaldirac_siniri_yuzde_15():
    assert cl.kaldirac_sec(D("0.10")) == 3 and cl.kaldirac_sec(D("0.15")) == 3      # sınır dahil 3x
    assert cl.kaldirac_sec(D("0.1501")) == 2 and cl.kaldirac_sec(D("0.25")) == 2
    assert hesap(stop=42500).kaldirac == 3                 # tam %15
    assert hesap(stop=42450).kaldirac == 2                 # %15.1


def test_marj_en_cok_yuzde_50():
    s = hesap(kasa=10000, stop=40000)          # stop %20 -> 2x; kayıp tavanı 300/10075 = 0.0297 -> 0.029 (nominal 1450 << 1.0x kasa)
    assert s.kaldirac == 2 and s.baglayan == "kayip" and s.qty == D("0.029")
    assert s.qty * 50000 / 2 <= D("0.5") * 10000
    s3 = hesap(stop=49000)                     # 3x: marj = nominal/3 <= %50
    assert s3.qty * 50000 / s3.kaldirac <= D("0.5") * 1000
    # marj tavanı (2x: nominal <= 1.0x kasa) saf fonksiyonda da bağlayıcıdır (kayıp tavanı bunu hep gevşek bırakır, yine de korunur):
    assert cl.limit_ihlalleri(qty=D("0.027"), giris=D(50000), stop=D(41000), kasa=D(1000), kaldirac=2, **KMT)


def test_toplam_stop_riski_yuzde_6():
    s = hesap(diger_stop_riski=D(55))
    assert s.baglayan == "toplam_risk" and s.qty == D("0.004")
    assert hesap(diger_stop_riski=D(60)).neden == "risk_butcesi_dolu"
    assert cl.limit_ihlalleri(qty=D("0.001"), giris=D(50000), stop=D(49000), kasa=D(1000), kaldirac=3, diger_stop_riski=D(60), **KMT)


def test_brut_nominal_1_5x():
    s = hesap(diger_brut=D(1400))
    assert s.baglayan == "brut" and s.qty == D("0.002")
    assert hesap(diger_brut=D(1500)).neden == "risk_butcesi_dolu"
    assert any("brut" in x for x in cl.limit_ihlalleri(qty=D("0.002"), giris=D(50000), stop=D(49990), kasa=D(1000), kaldirac=3, diger_brut=D(1450), **KMT))


def test_limit_ihlalleri_marj_ve_kayip_yuvarlama_sonrasi():
    assert cl.limit_ihlalleri(qty=D("0.027"), giris=D(50000), stop=D(49000), kasa=D(1000), kaldirac=3, **KMT) == []
    assert any("islem_marj" in x for x in cl.limit_ihlalleri(qty=D("0.027"), giris=D(50000), stop=D(49000), kasa=D(1000), kaldirac=2, **KMT))
    assert any("islem_basi_kayip" in x for x in cl.limit_ihlalleri(qty=D("0.029"), giris=D(50000), stop=D(49000), kasa=D(1000), kaldirac=3, **KMT))


# ----------------------------------------------------------------------------- günlük / strateji kill
def yeni_durum():
    return {"zirve": None, "gun": None, "gun_basi": None, "kill": False, "kill_neden": None, "gun_blok": False}


def test_gunluk_eksi_6_blok_ve_ertesi_utc_gunu_sifirlanir():
    d = yeni_durum()
    assert cl.gunluk_kill_guncelle(d, D(1000), "2026-11-11") == []
    assert cl.gunluk_kill_guncelle(d, D(950), "2026-11-11") == [] and not d["gun_blok"]        # -%5
    o = cl.gunluk_kill_guncelle(d, D(940), "2026-11-11")                                       # -%6
    assert d["gun_blok"] and not d["kill"] and len(o) == 1
    cl.gunluk_kill_guncelle(d, D(940), "2026-11-12")
    assert not d["gun_blok"] and d["gun_basi"] == "940"                                        # ertesi UTC günü, yeni gün başı kasa


def test_strateji_kill_eksi_30_zirveden_ve_kalici():
    d = yeni_durum()
    cl.gunluk_kill_guncelle(d, D(1000), "2026-11-11")
    cl.gunluk_kill_guncelle(d, D(1200), "2026-11-12")                                          # zirve 1200
    cl.gunluk_kill_guncelle(d, D(900), "2026-11-13")                                           # -%25: kill yok (günlük -%25 ama kill değil)
    assert not d["kill"]
    cl.gunluk_kill_guncelle(d, D(840), "2026-11-14")                                           # -%30 zirveden
    assert d["kill"] and d["kill_neden"] == "kill_switch"
    cl.gunluk_kill_guncelle(d, D(2000), "2026-11-20")                                          # toparlansa da kalkmaz
    assert d["kill"]


def test_strateji_kill_yurutucuda_kalici_yeniden_baslatmada(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    assert e.borsa.poz
    e.borsa.ozs = D("700")                                                                     # -%30
    e.y.adim(gor([]))
    assert e.y.durum["kill"] and e.borsa.poz == {} and e.borsa.acik == {}
    e.y = e.yeni()                                                                             # yeniden başlatma
    assert e.y.durum["kill"] is True
    n = len([c for c in e.borsa.cagrilar if c[0] == "piyasa"])
    e.borsa.ozs = D("5000")
    e.zaman[0] += pd.Timedelta(days=2)
    e.y.adim(gor([ac_niyeti(t=e.zaman[0] - ARALIK - pd.Timedelta(seconds=5))]))
    assert len([c for c in e.borsa.cagrilar if c[0] == "piyasa"]) == n


def test_gunluk_blok_kapatmaz_kill_kapatir(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    q = e.borsa.poz["BTCUSDT"]
    e.borsa.ozs = D("930")                                                                     # -%7: günlük blok
    e.y.adim(gor([]))
    assert e.y.durum["gun_blok"] and not e.y.durum["kill"] and e.borsa.poz == {"BTCUSDT": q} and e.borsa.acik   # pozisyon + stop yerinde
    e.borsa.ozs = D("690")                                                                     # -%31 zirveden: kill
    e.y.adim(gor([]))
    assert e.y.durum["kill"] and e.borsa.poz == {} and e.borsa.acik == {}


def test_yurutucu_kaldirac_stop_mesafesine_gore_ayarlanir(tmp_path):
    e = Ortam(tmp_path, ozs="1000", tahsis=1000)
    e.y.adim(gor([ac_niyeti(stop="49000")]))                                                   # %2 -> 3x
    assert ("hazirla", "BTCUSDT", 3) in e.borsa.cagrilar
    e2 = Ortam(tmp_path / "b", ozs="1000", tahsis=1000)
    (tmp_path / "b").mkdir()
    e2.y.adim(gor([ac_niyeti(stop="41000")]))                                                  # %18 -> 2x
    assert ("hazirla", "BTCUSDT", 2) in e2.borsa.cagrilar
    q = e2.borsa.poz["BTCUSDT"]
    assert q * 50000 <= D(1000) * D("1.0") and q * 50000 / 2 <= D(500)                         # marj <= %50 kasa


# ----------------------------------------------------------------------------- hesap kill
def iki_strateji(tmp_path, e1="1000", e2="1000"):
    y = {}
    borsalar = {}
    for sid, ozs in (("S1", e1), ("S2", e2)):
        b = Sahte(ozs)
        borsalar[sid] = b
        y[sid] = Yurutucu(sid, b, bilgi(), Ayar("testnet", D(1000)), tmp_path / f"{sid}.json", olay=lambda t, m: None,
                          saat=lambda: T0 + ARALIK, sembol_esle=lambda s: s)
    return y, borsalar


def test_hesap_kill_iki_stratejinin_toplami_eksi_20_ve_kalici(tmp_path):
    y, b = iki_strateji(tmp_path)
    yol = tmp_path / "hesap.json"
    h = cal.hesap_yukle(yol)
    assert cal.hesap_izle(y, h, yol) is None                                                   # zirve 2000
    b["S1"].ozs = D("850")                                                                     # toplam 1850: -%7.5 (S1 kendi başına -%15)
    assert cal.hesap_izle(y, h, yol) is None and not h["kill"]
    b["S2"].ozs = D("760")                                                                     # toplam 1610: -%19.5
    assert cal.hesap_izle(y, h, yol) is None
    b["S2"].ozs = D("750")                                                                     # toplam 1600: -%20
    m = cal.hesap_izle(y, h, yol)
    assert m and h["kill"] and all(v.durum["kill"] and v.durum["kill_neden"] == "hesap_kill" for v in y.values())
    h2 = cal.hesap_yukle(yol)                                                                  # yeniden başlatma: dosyadan
    assert h2["kill"] and h2["zirve"] == "2000"
    y2, b2 = iki_strateji(tmp_path, "5000", "5000")                                            # bakiye toparlansa da
    cal.hesap_izle(y2, h2, yol)
    assert all(v.durum["kill"] for v in y2.values())


def test_hesap_kill_tum_stratejileri_kapatir(tmp_path):
    y, b = iki_strateji(tmp_path)
    for sid, yy in y.items():
        yy.adim(gor([ac_niyeti(t=T0)]))
        assert b[sid].poz
    h = cal.hesap_yukle(tmp_path / "hesap.json")
    cal.hesap_izle(y, h)
    for sid in b:
        b[sid].ozs = D("750")
    cal.hesap_izle(y, h)
    for sid, yy in y.items():
        yy.adim(gor([]))
        assert b[sid].poz == {} and b[sid].acik == {}


def test_hesap_kill_strateji_kumesi_degisince_zirve_yeniden_baslar():
    h = {}
    cl.hesap_kill_guncelle(h, {"A": D(1000)})
    assert cl.hesap_kill_guncelle(h, {"A": D(1000), "B": D(100)}) is None and h["zirve"] == "1100"


# ----------------------------------------------------------------------------- SERT_LIMITLER değişmedi, paper onu kullanır
def test_sert_limitler_degismedi_ve_paper_motoru_kullanir():
    assert (SERT_LIMITLER.islem_basi_max_risk_yuzde, SERT_LIMITLER.gunluk_max_kayip_yuzde, SERT_LIMITLER.max_kaldirac,
            SERT_LIMITLER.kill_switch_dusus_yuzde, SERT_LIMITLER.portfoy_toplam_risk_yuzde) == (1.0, 3.0, 3.0, 20.0, 5.0)
    from motor.backtest import motor as bt
    from motor.canli import paper_motor as pm
    assert pm.SERT_LIMITLER is SERT_LIMITLER and bt.SERT_LIMITLER is SERT_LIMITLER
    assert "canli_limitler" not in inspect.getsource(pm) and "canli_limitler" not in inspect.getsource(bt)
    for mod in (canli_yurutucu, kurallar, cal):                                              # canlı yürütücü artık SERT_LIMITLER kullanmaz
        assert "SERT_LIMITLER" not in inspect.getsource(mod).replace("SERT_LIMITLER'i kullanmaya", "")


def test_canli_dosyalarinda_risk_sayisi_yok():
    for mod in (canli_yurutucu, kurallar):
        kaynak = inspect.getsource(mod)
        for yasak in ("0.03", "0.06", "0.25", "1.5", "0.15"):
            assert yasak not in kaynak.replace('D("0.0005")', ""), (mod.__name__, yasak)
