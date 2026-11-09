"""Paper durum dosyaları: şema, ek alanlar (yazildi_zaman, maruziyet, maliyet, reddedilen, olaylar, performans, içgörüler),
sayıların dosyalar arası tutarlılığı, bayatlık (seans), beklenti alarmı, backtest_durum null+neden."""
import json
from decimal import Decimal

import pandas as pd
import pytest
from testler.conftest import KILIT_ISLEM_NEDEN, kilit_islemleri_var

from motor.canli import backtest_durum as bd
from motor.canli import durum as d
from motor.canli import paper as pp
from motor.canli import paper_durum as pdr
from motor.canli import paper_sinyal as psg
from motor.canli import telegram as tg
from testler.test_paper_motor import TAN, kural, sentetik


@pytest.fixture(scope="module")
def kosu(tmp_path_factory):
    tans = [TAN["swing__cci-esik|SOLUSDT|1d"], TAN["pf__kesit_ls|kripto|1d"]]
    mum = {("SOLUSDT", "1d"): sentetik(520, "1d", 3, vol=0.04)}
    for k, s in enumerate(["BTCUSDT", "ETHUSDT"]):
        mum[(s, "1d")] = sentetik(520, "1d", 20 + k, vol=0.04)
    kur = {s: kural(s) for s in ("SOLUSDT", "BTCUSDT", "ETHUSDT")}
    ix = mum[("SOLUSDT", "1d")].index
    p = pp.tekrar_calistir(tans, mum, {}, kur, ix[380], ix[-1] + pd.Timedelta(days=1), kapat=False)
    simdi = ix[-1] + pd.Timedelta(days=1, minutes=5)
    sag = [{"sembol": s, "tf": tf, "son_mum_acilis": df.index[-1]} for (s, tf), df in mum.items()]
    dizin = tmp_path_factory.mktemp("durum")
    o = pdr.olustur(p, simdi, kaynak_saglik=sag, olaylar=[{"zaman": d.zaman_str(simdi), "tur": "ws_koptu", "mesaj": "x"}],
                    beklenti_csv=bd.BEKLENTI_CSV)
    d.yaz_hepsi(dizin, ozet=o["ozet"], stratejiler=o["stratejiler"], islemler=o["islemler"], saglik=o["saglik"],
                gecmis=o["gecmis"], ekstra=o["ekstra"])
    return p, o, dizin, simdi


def test_dosyalar_okunur_ve_yazildi_zaman_var(kosu):
    p, o, dizin, simdi = kosu
    veri, sorun = d.oku_hepsi(dizin)
    assert not sorun
    for ad in ("ozet", "stratejiler", "saglik", "gecmis"):
        assert veri[ad]["yazildi_zaman"] == veri["ozet"]["yazildi_zaman"]
    for ad in ("maruziyet", "maliyet", "reddedilen", "icgoruler"):
        e = d.ek_oku(dizin, ad)
        assert e["yazildi_zaman"] == veri["ozet"]["yazildi_zaman"]
    assert d.ek_oku(dizin, "olaylar")[0]["tur"] == "ws_koptu"


def test_ozet_ek_alanlari(kosu):
    p, o, dizin, simdi = kosu
    oz = o["ozet"]
    assert oz["baslangictan_pnl"] == oz["toplam_pnl"]
    assert len(oz["gunluk_kz"]) <= 60 and [x["gun"] for x in oz["gunluk_kz"]] == [x["gun"] for x in oz["dusus_serisi"]]
    assert oz["hafta_pnl"] is not None and oz["hafta_pnl_neden"] is None
    # son 60 günün K/Z toplamı = özsermaye farkı (gecmis noktalarından)
    nk = o["gecmis"]["noktalar"]
    once = next(x for x in nk if x["gun"] == oz["gunluk_kz"][0]["gun"])
    onceki = nk[nk.index(once) - 1]
    assert abs(sum(Decimal(x["pnl"]) for x in oz["gunluk_kz"]) - (Decimal(nk[-1]["ozsermaye"]) - Decimal(onceki["ozsermaye"]))) <= Decimal("0.05")
    assert oz["sayaclar"]["kapanan_islem"] == len(o["islemler"])


def test_hafta_pnl_null_ve_neden_yedi_gun_dolmadiysa():
    tans = [TAN["swing__cci-esik|SOLUSDT|1d"]]
    m = sentetik(420, "1d", 3, vol=0.04)
    p = pp.tekrar_calistir(tans, {("SOLUSDT", "1d"): m}, {}, {"SOLUSDT": kural("SOLUSDT")}, m.index[400], m.index[404] + pd.Timedelta(days=1), kapat=False)
    o = pdr.olustur(p, m.index[404] + pd.Timedelta(days=1, minutes=5), kaynak_saglik=[])
    assert o["ozet"]["hafta_pnl"] is None and "7 gün" in o["ozet"]["hafta_pnl_neden"]


def test_strateji_katki_toplami_ozsermayeyi_tutar_ve_performans(kosu):
    p, o, dizin, simdi = kosu
    kat = sum((Decimal(s["ozsermaye_katkisi"]) for s in o["stratejiler"]["stratejiler"]), Decimal(0))
    assert abs(kat - Decimal(o["ozet"]["toplam_pnl"])) < Decimal("0.05")
    for s in o["stratejiler"]["stratejiler"]:
        pf = s["performans"]
        assert pf["islem"] == s["islem_sayisi"]
        if s["islem_sayisi"]:
            assert pf["ort_zarar"] is None or Decimal(pf["ort_zarar"]) < 0
            satir_net = [Decimal(x["net_pnl_yerel"]) for x in o["islemler"] if x["kimlik"] == s["kimlik"]]
            # pf["net"] yuvarlanmamış toplamın yuvarlanmışı, satırlar tek tek yuvarlanmış: fark en çok yarım kuruş x satır
            assert abs(Decimal(pf["net"]) - sum(satir_net, Decimal(0))) <= Decimal("0.005") * len(satir_net) + Decimal("0.005")


def test_maliyet_dokumu_tutarli(kosu):
    p, o, dizin, simdi = kosu
    mal = o["ekstra"]["maliyet"]
    tum = mal["toplam"]["tum"]
    assert Decimal(tum["toplam"]) == Decimal(tum["ucret"]) + Decimal(tum["kayma"]) + Decimal(tum["funding"])
    assert sum((Decimal(v["tum"]["ucret"]) for v in mal["stratejiler"].values()), Decimal(0)) == Decimal(tum["ucret"])
    # ücret = işlemlerin komisyon toplamı (kapanan) + açık pozisyonların giriş komisyonu
    kom = sum((Decimal(repr(x["komisyon"])) for x in p.motor.islemler), Decimal(0)) + sum((q.giris_kom for q in p.motor.acik.values()), Decimal(0))
    assert abs(kom - Decimal(tum["ucret"])) < Decimal("0.02")


def test_maruziyet_ve_acik_kz(kosu):
    p, o, dizin, simdi = kosu
    mr = o["ekstra"]["maruziyet"]
    assert len(mr["pozisyonlar"]) == len(p.motor.acik)
    brut = sum((Decimal(x["brut_nominal"]) for x in mr["semboller"]), Decimal(0))
    assert Decimal(mr["toplam_brut_nominal"]) == brut
    for q in mr["pozisyonlar"]:
        assert {"mark_fiyat", "kz", "kz_oran", "stop"} <= set(q)
    ac = [q for s in o["stratejiler"]["stratejiler"] for q in s["acik_pozisyonlar"]]
    assert sorted(x["kz"] for x in ac) == sorted(x["kz"] for x in mr["pozisyonlar"])
    assert mr["acik_stop_riski"]["oran"] == o["ozet"]["risk"]["acik_stop_riski"]["deger"]


def test_reddedilen_ve_icgoruler_sayilari_diger_alanlarla_ayni(kosu):
    p, o, dizin, simdi = kosu
    r = o["ekstra"]["reddedilen"]
    assert sum(r["tum"].values()) == o["ozet"]["sayaclar"]["reddedilen_giris"] + o["ozet"]["sayaclar"]["kirpilan_giris"]
    assert len(r["son"]) <= 20
    ic = o["ekstra"]["icgoruler"]["cumleler"]
    ap = o["ekstra"]["maruziyet"]["pozisyonlar"]
    karda = sum(1 for x in ap if Decimal(x["kz"]) > 0)
    if ap:
        assert any(f"Açık {len(ap)} pozisyonun {karda} tanesi kârda" in c for c in ic)
    assert any("maliyet" in c for c in ic)


def test_bayatlik_seans_ve_dosya_esigi(kosu):
    p, o, dizin, simdi = kosu
    sg = o["saglik"]
    assert sg["bayat_denetimi"] and sg["dosya_esik_dk"] == pdr.DOSYA_ESIK_DK
    assert all(v["bayatlik_dk"] >= 0 for v in sg["veri"])
    # kripto: son mum kapanışından 5 dk -> bayat değil
    assert not any(v["bayat"] for v in sg["veri"])
    # veri 3 gün durursa bayat
    x = pdr.saglik_olustur(p, simdi + pd.Timedelta(days=3), [{"sembol": "BTCUSDT", "tf": "1d", "son_mum_acilis": simdi - pd.Timedelta(days=1)}], [], None)
    assert x["veri"][0]["bayat"] and x["durum"] == "veri_bayat"


def test_beklenti_alarmi_uyariya_yazilir():
    """8 hafta pencere dolu ve getiri alarm eşiğinin altındaysa saglik.uyarilar'a BEKLENTİ ALARMI yazılır (motor yazar)."""
    t = TAN["swing__cci-esik|SOLUSDT|1d"]
    m = sentetik(700, "1d", 3, vol=0.03)
    # sürekli düşen fiyat: long stratejisi zarar yazar
    m[["acilis", "yuksek", "dusuk", "kapanis"]] = m[["acilis", "yuksek", "dusuk", "kapanis"]].mul(__import__("numpy").exp(-0.01 * __import__("numpy").arange(len(m))), axis=0)
    p = pp.tekrar_calistir([t], {("SOLUSDT", "1d"): m}, {}, {"SOLUSDT": kural("SOLUSDT")}, m.index[500], None, kapat=False)
    o = pdr.olustur(p, m.index[-1] + pd.Timedelta(days=1, minutes=5), kaynak_saglik=[])
    kon = o["stratejiler"]["stratejiler"][0]["beklenti"].get("8")
    assert kon is not None
    alarm = kon["net_getiri"]["alarm"] or kon["max_dusus"]["alarm"]
    assert alarm == any("BEKLENTİ ALARMI" in u for u in o["saglik"]["uyarilar"])


def test_veri_yok_stratejisi_isaretlenir_ve_calistirilmaz():
    t = psg.tanimlari_yukle(ayar_kaynagi="kilit")
    nv = [x for x in t if x.kimlik.startswith("dis__fraktal")][0]
    nv.veri_yok = "DK_NVDA: Binance'te yok"
    m = sentetik(420, "1d", 3)
    c = TAN["swing__cci-esik|SOLUSDT|1d"]
    p = pp.tekrar_calistir([c, nv], {("SOLUSDT", "1d"): m}, {}, {"SOLUSDT": kural("SOLUSDT")}, m.index[400], None, kapat=False)
    o = pdr.olustur(p, m.index[-1] + pd.Timedelta(days=1, minutes=5), kaynak_saglik=[])
    s = {x["kimlik"]: x for x in o["stratejiler"]["stratejiler"]}
    assert s[nv.kimlik]["durum"].startswith("veri yok") and s[nv.kimlik]["islem_sayisi"] == 0
    assert any("VERİ YOK" in u for u in o["saglik"]["uyarilar"])


@pytest.mark.gercek_veri(kilit_islemleri_var(), reason=KILIT_ISLEM_NEDEN)
def test_backtest_durum_genisletme_null_ve_neden(tmp_path):
    out = bd.olustur()
    oz = out["ozet"]
    assert "gunluk_kz" in oz and "dusus_serisi" in oz and oz["baslangictan_pnl"] == oz["toplam_pnl"]
    e = out["ekstra"]
    assert e["maruziyet"]["toplam_brut_nominal"] is None and e["maruziyet"]["olculmedi_neden"]
    assert e["maliyet"]["toplam"] is None and e["maliyet"]["olculmedi_neden"]
    d.yaz_hepsi(tmp_path, ozet=out["ozet"], stratejiler=out["stratejiler"], islemler=out["islemler"], saglik=out["saglik"],
                gecmis=out["gecmis"], ekstra=e)
    assert d.ek_oku(tmp_path, "maliyet")["yazildi_zaman"]


def test_ek_dosya_yoksa_none(tmp_path):
    assert d.ek_oku(tmp_path, "maliyet") is None


def test_telegram_ozet_metni_durum_sayilariyla(kosu):
    p, o, dizin, simdi = kosu
    metin = tg.ozet_metni(o)
    assert tg.usd(o["ozet"]["ozsermaye"]) in metin and "1L3A Paper" in metin and "Günlük özet" in metin
