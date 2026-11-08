"""Dersler (motor/canli/dersler.py) ve aylık rapor + paper kabul listesi (motor/canli/aylik_rapor.py): istatistik doğruluğu, durum kuralları,
TSİ ay kesimi, tanımsız eşiklerin işaretlenmesi, paper ve backtest yolları, pano yalnız biçimler."""
import json
import math

import pandas as pd
import pytest

from motor.canli import aylik_rapor as ar
from motor.canli import backtest_durum as bd
from motor.canli import dersler as ds
from motor.canli import durum as d
from motor.canli import pano
from motor.canli import paper as pp
from motor.canli import paper_durum as pdr
from testler.test_paper_motor import TAN, kural, sentetik

KIM = "swing__cci-esik|SOLUSDT|1d"
REF = {"n": 134, "isabet": 0.5, "ort_r": 0.17, "std_r": 0.78, "pf_r": 2.27, "cikis_paylari": {"sinyal": 0.9, "stop": 0.1}, "kaynak": "t"}


def _s(r, neden="sinyal", kim=KIM, zaman="2026-11-10T12:00:00Z", katki="1.00", sembol="SOLUSDT"):
    return {"zaman": zaman, "kimlik": kim, "sembol": sembol, "yon": "long", "giris_zamani": "2026-11-09T12:00:00Z", "cikis_zamani": zaman,
            "r": r, "net_pnl_yerel": f"{r:.2f}", "set_katki_usd": katki, "cikis_nedeni": neden}


# ---------------------------------------------------------------------------- istatistik doğruluğu
def test_binom_bilinen_degerler():
    assert ds.binom_p(5, 10, 0.5) == pytest.approx(1.0)
    assert ds.binom_p(9, 10, 0.5) == pytest.approx(0.021484375, rel=1e-6)       # 2 x 11/1024
    assert ds.binom_p(0, 10, 0.5) == pytest.approx(2 / 1024, rel=1e-6)
    assert ds.binom_p(0, 5, 0.0) == pytest.approx(1.0)
    assert ds.binom_p(1, 5, 0.0) == pytest.approx(0.0, abs=1e-12)


def test_t_dagilimi_p_degerleri():
    assert ds.t_p_iki_yonlu(1.0, 1) == pytest.approx(0.5, abs=1e-9)             # Cauchy
    assert ds.t_p_iki_yonlu(2.228139, 10) == pytest.approx(0.05, abs=1e-4)
    assert ds.t_p_iki_yonlu(2.0, 1e6) == pytest.approx(0.0455, abs=1e-3)        # ~normal
    assert ds.t_p_iki_yonlu(0.0, 5) == 1.0


def test_welch_ve_sifir_varyans():
    w = ds.welch(0.5, 1.0, 50, 0.0, 1.0, 50)
    assert w["t"] == pytest.approx(0.5 / math.sqrt(0.04), rel=1e-9) and 0.01 < w["p"] < 0.02
    assert ds.welch(1.0, 0.0, 10, 1.0, 0.0, 10) is None


# ---------------------------------------------------------------------------- durum kuralları
def test_ornek_az_testler_null_ve_neden():
    x = ds.degerlendir(KIM, [_s(1.0), _s(-1.0)], REF)
    assert x["durum"] == "ornek_az" and x["isabet_testi"] is None and x["ort_r_testi"] is None
    assert str(ds.MIN_ISLEM_DERS) in x["test_neden"] and x["durum_etiket"] == "örnek az"
    assert x["islem"] == 2 and x["isabet"] == 0.5          # betimleyici sayılar yine de verilir


def test_beklenti_icinde():
    r = [1.0, -0.5] * 20 + [0.5, -0.3] * 5                  # 50 işlem, isabet 0.5, ort ~0.19
    x = ds.degerlendir(KIM, [_s(v) for v in r], REF)
    assert x["durum"] == "icinde" and x["isabet_testi"]["p_deger"] > 0.05 and x["ort_r_testi"]["p_deger"] > 0.05


def test_altinda_ve_ustunde_ve_cikis_sapmasi_metni():
    kotu = [_s(-1.0, "stop") for _ in range(35)] + [_s(0.3) for _ in range(5)]
    x = ds.degerlendir(KIM, kotu, REF)
    assert x["durum"] == "altinda" and x["ort_r_testi"]["yon"] == "altinda"
    stop = next(c for c in x["cikis_nedeni_sapmalari"] if c["neden"] == "stop")
    assert stop["anlamli"] and stop["pay"] == pytest.approx(35 / 40)
    assert any("'stop' çıkışları" in a and "beklenenden çok" in a for a in x["aciklamalar"])
    iyi = [_s(2.0) for _ in range(30)] + [_s(-0.5) for _ in range(10)]
    y = ds.degerlendir(KIM, iyi, REF)
    assert y["durum"] == "ustunde"


def test_gorulmemis_cikis_nedeni_ve_pf_none():
    x = ds.degerlendir(KIM, [_s(1.0, "kill_switch") for _ in range(40)], REF)
    assert x["pf_r"] is None and any("hiç görülmemişti" in a for a in x["aciklamalar"]) and any("PF (R) hesaplanamadı" in a for a in x["aciklamalar"])


def test_alarm_durumu_altina_ceker():
    r = [1.0, -0.5] * 20 + [0.5, -0.3] * 5
    nb = {"deger": -0.09, "bant": "p05_alti", "alarm": True}
    kon = {"8": {"net_getiri": nb, "max_dusus": {"deger": 0.01, "bant": "p25_p50", "alarm": False}}}
    x = ds.degerlendir(KIM, [_s(v) for v in r], REF, kon)
    assert x["durum"] == "altinda" and "alarm" in x["durum_neden"] and x["beklenti_penceresi"]["alarm"] is True


def test_referans_yok_null_ve_neden(tmp_path):
    x = ds.degerlendir("yok|X|1h", [], None)
    assert x["durum"] is None and "referansı yok" in x["durum_neden"]
    o = ds.olustur("paper", "2026-11-10T00:00:00Z", [KIM], [], referans_csv=tmp_path / "yok.csv")
    assert o["referans_neden"] and o["sayim"]["olculmedi"] == 1


def test_referans_csv_gercek_dosya():
    ref = ds.referans_oku()
    assert ref is not None and len(ref) == 7 and ref[KIM]["n"] == 134
    for v in ref.values():
        assert abs(sum(v["cikis_paylari"].values()) - 1.0) < 1e-9 and 0 < v["isabet"] < 1
    o = ds.olustur("paper", "2026-11-10T00:00:00Z", list(ref), [])
    assert o["sayim"]["ornek_az"] == 7 and {t["ad"] for t in o["tanimsiz_esikler"]} == {"dersler_asgari_islem", "dersler_alfa"}


# ---------------------------------------------------------------------------- aylık rapor
def _gun(g, pnl, getiri):
    return {"gun": g, "pnl": pnl, "getiri": getiri}


def test_aylik_tsi_kesimi_ve_toplamlar():
    # 2026-11-30 21:30Z = 2026-12-01 00:30 TSİ -> Aralık'a yazılır
    sat = [_s(1.0, zaman="2026-11-30T20:59:00Z", katki="10.00"), _s(-1.0, zaman="2026-11-30T21:30:00Z", katki="-4.00", kim="b|X|1h")]
    donem = [{"donem": "2026-11", "bas_gun": "2026-11-29", "bit_gun": "2026-11-30", "gun_sayisi": 2, "tamamlandi": True,
              "ajanlar": {"swing": {"pnl": "10.00", "getiri": 0.001}}, "toplam": {"pnl": "10.00", "getiri": 0.001}},
             {"donem": "2026-12", "bas_gun": "2026-12-01", "bit_gun": "2026-12-02", "gun_sayisi": 2, "tamamlandi": False,
              "ajanlar": {"swing": {"pnl": "-4.00", "getiri": -0.0004}}, "toplam": {"pnl": "-4.00", "getiri": -0.0004}}]
    gz = [_gun("2026-11-29", "20.00", 0.002), _gun("2026-11-30", "-10.00", -0.001), _gun("2026-12-01", "-4.00", -0.0004), _gun("2026-12-02", "0.00", 0.0)]
    a = ar.aylik(donem, gz, sat, None)
    assert a[0]["islem_sayisi"] == 1 and a[1]["islem_sayisi"] == 1
    assert a[0]["en_iyi_strateji"]["kimlik"] == KIM and a[1]["en_kotu_strateji"]["kimlik"] == "b|X|1h"
    assert a[0]["max_dusus"] == pytest.approx(0.001, rel=1e-6) and a[0]["en_kotu_gun"] == {"gun": "2026-11-30", "pnl": "-10.00"}
    assert a[0]["limit_olaylari"] is None and a[0]["getiri"] == 0.001


def test_aylik_limit_olaylari_tsi_ayina():
    lim = [{"tur": "gunluk_kayip", "zaman": pd.Timestamp("2026-11-30T21:10:00Z")}, {"tur": "kill_switch", "zaman": "2026-11-15T10:00:00Z"}]
    donem = [{"donem": m, "bas_gun": f"{m}-01", "bit_gun": f"{m}-02", "gun_sayisi": 2, "tamamlandi": True, "ajanlar": {}, "toplam": {"pnl": "0.00", "getiri": 0.0}}
             for m in ("2026-11", "2026-12")]
    a = ar.aylik(donem, [], [], lim)
    assert a[0]["limit_olaylari"] == {"gunluk_kayip": 0, "kill_switch": 1} and a[1]["limit_olaylari"] == {"gunluk_kayip": 1, "kill_switch": 0}


def _risk(kill=False, kal=1.0, stop=0.02, gk=0.0):
    return {"gunluk_kayip": {"deger": gk, "limit": 0.03}, "kaldirac": {"deger": kal, "limit": 3.0}, "acik_stop_riski": {"deger": stop, "limit": 0.05},
            "kill_switch": {"dusus": 0.0, "limit": 0.2, "mesafe": 0.2, "tetiklendi": kill}}


def _kon(alarm=False):
    return {"8": {"net_getiri": {"deger": 0.01, "bant": "p25_p50", "alarm": alarm}, "max_dusus": {"deger": 0.01, "bant": "p25_p50", "alarm": False}}}


def _kabul(simdi="2026-11-20T00:00:00Z", bas="2026-11-07T00:00:00Z", risk=None, set_konum=None, strat_konum=None, limit=None, olaylar=None):
    return ar.kabul_listesi(simdi=pd.Timestamp(simdi), donem_bas=pd.Timestamp(bas), risk=risk or _risk(), sayaclar={"kill_olayi": 0, "gunluk_limit_olayi": 0, "kapanan_islem": 5},
                            set_konum=set_konum if set_konum is not None else {}, strat_konum=strat_konum or {}, dersler={"sayim": {"icinde": 0, "altinda": 1, "ustunde": 0, "ornek_az": 6}},
                            saglik_durum="ok", olaylar=olaylar or [], limit_olaylari=limit or [])


def _kalem(k, id_):
    return next(x for x in k["kalemler"] if x["id"] == id_)


def test_kabul_sure_erken_tarih_2027_01_02():
    k = _kabul()
    s = _kalem(k, "sure")
    assert s["durum"] == "bekliyor" and "2027-01-02" in s["neden"] and s["deger"] == "13 / 56 gün"
    assert _kalem(_kabul(simdi="2027-01-02T00:00:00Z"), "sure")["durum"] == "gecti"
    assert _kalem(_kabul(simdi="2027-01-01T23:59:00Z"), "sure")["durum"] == "bekliyor"


def test_kabul_set_beklenti_ve_limit_ve_genel():
    assert _kalem(_kabul(), "set_beklenti")["durum"] == "bekliyor"
    assert _kalem(_kabul(set_konum=_kon(False)), "set_beklenti")["durum"] == "gecti"
    k = _kabul(set_konum=_kon(True))
    assert _kalem(k, "set_beklenti")["durum"] == "kaldi" and k["genel_durum"] == "kaldi"
    assert _kalem(_kabul(risk=_risk(kill=True)), "sert_limit")["durum"] == "kaldi"
    assert _kalem(_kabul(risk=_risk(kal=3.4)), "sert_limit")["durum"] == "kaldi"
    assert _kalem(_kabul(limit=[{"tur": "kill_switch", "zaman": "2026-11-12T00:00:00Z"}]), "sert_limit")["durum"] == "kaldi"
    ok = _kabul(limit=[{"tur": "gunluk_kayip", "zaman": "2026-11-12T00:00:00Z"}])
    assert _kalem(ok, "sert_limit")["durum"] == "gecti" and _kalem(ok, "gunluk_limit_olayi")["deger"] == "1"      # günlük limit: bilgi


def test_kabul_tamam_ama_tanimsizlar_isaretli():
    k = _kabul(simdi="2027-01-03T00:00:00Z", set_konum=_kon(False))
    assert k["genel_durum"] == "tamam" and "kabul kararı değildir" in k["genel_not"]
    for i in ("kesintisiz_calisma", "asgari_islem"):
        x = _kalem(k, i)
        assert x["durum"] == "tanimsiz" and "kullanıcıya sorulacak" in x["neden"]
    assert {t["ad"] for t in k["tanimsiz"]} >= {"kesintisiz_calisma", "asgari_islem", "strateji_alarmi_kabulu", "gunluk_limit_olayi", "dersler_durumu"}
    # eski pano eşikleri kullanılmıyor
    assert all("PSR" not in x["olcut"] and "%10" not in x["olcut"] for x in k["kalemler"])


def test_kabul_strateji_alarmi_bilgi_kalemi():
    k = _kabul(strat_konum={"a": _kon(True), "b": _kon(False)})
    x = _kalem(k, "strateji_alarmlari")
    assert x["durum"] == "bilgi" and x["deger"].startswith("1 / 2") and k["genel_durum"] == "bekliyor"


def test_backtest_kabul_listesi_null_ve_neden():
    r = ar.olustur(kaynak="backtest", zaman="2026-11-10T00:00:00Z", simdi=pd.Timestamp("2026-11-10", tz="UTC"), donem_bas=None, aylik_kz_ajan=[], gunluk_tam=[],
                   satirlar=[], risk=_risk(), sayaclar={}, set_konum={}, strat_konum={}, dersler={}, saglik_durum="ok", olaylar=None, limit_olaylari=None,
                   gun_kesimi="UTC (araştırma ızgarası)")
    assert r["kabul_listesi"] is None and "backtest" in r["kabul_listesi_neden"] and "UTC" in r["aylar_not"]


# ---------------------------------------------------------------------------- entegrasyon: paper + backtest + pano
@pytest.fixture(scope="module")
def paper(tmp_path_factory):
    tans = [TAN[KIM], TAN["pf__kesit_ls|kripto|1d"]]
    mum = {("SOLUSDT", "1d"): sentetik(520, "1d", 3, vol=0.04)}
    for k, s in enumerate(["BTCUSDT", "ETHUSDT"]):
        mum[(s, "1d")] = sentetik(520, "1d", 20 + k, vol=0.04)
    kur = {s: kural(s) for s in ("SOLUSDT", "BTCUSDT", "ETHUSDT")}
    ix = mum[("SOLUSDT", "1d")].index
    p = pp.tekrar_calistir(tans, mum, {}, kur, ix[380], ix[-1] + pd.Timedelta(days=1), kapat=False)
    simdi = ix[-1] + pd.Timedelta(days=1, minutes=5)
    sag = [{"sembol": s, "tf": tf, "son_mum_acilis": df.index[-1]} for (s, tf), df in mum.items()]
    o = pdr.olustur(p, simdi, kaynak_saglik=sag, beklenti_csv=bd.BEKLENTI_CSV)
    dizin = tmp_path_factory.mktemp("durum")
    d.yaz_hepsi(dizin, ozet=o["ozet"], stratejiler=o["stratejiler"], islemler=o["islemler"], saglik=o["saglik"], gecmis=o["gecmis"], ekstra=o["ekstra"])
    return p, o, dizin


def test_paper_dersler_ve_rapor_dosyalari(paper):
    p, o, dizin = paper
    dr, ra = d.ek_oku(dizin, "dersler"), d.ek_oku(dizin, "aylik_rapor")
    assert dr["kaynak"] == "paper" and [x["kimlik"] for x in dr["stratejiler"]] == [t.kimlik for t in p.tanimlar]
    kz = {x["kimlik"]: x for x in o["stratejiler"]["stratejiler"]}
    for x in dr["stratejiler"]:
        assert x["islem"] == kz[x["kimlik"]]["islem_sayisi"]                              # aynı sayı, tek kaynak
    assert ra["gun_kesimi"] == "Europe/Istanbul" and ra["kabul_listesi"]["kalemler"]
    # aylık özet getirisi = ozet.aylik_kz_ajan toplam getirisi
    aylik = {m["donem"]: m for m in o["ozet"]["aylik_kz_ajan"]}
    for a in ra["aylar"]:
        assert a["getiri"] == aylik[a["ay"]]["toplam"]["getiri"] and a["pnl"] == aylik[a["ay"]]["toplam"]["pnl"]
    assert sum(a["islem_sayisi"] for a in ra["aylar"]) <= o["ozet"]["sayaclar"]["kapanan_islem"]
    sure = _kalem(ra["kabul_listesi"], "sure")                                            # sentetik koşu 140 gün: 56 günü aşar
    assert sure["durum"] == "gecti" and sure["deger"].endswith("/ 56 gün")


def test_backtest_dersler_ve_rapor_yazilir(tmp_path):
    bd.yaz(tmp_path)
    dr, ra = d.ek_oku(tmp_path, "dersler"), d.ek_oku(tmp_path, "aylik_rapor")
    assert dr["kaynak"] == "backtest" and len(dr["stratejiler"]) == 7 and "bağımsız bir sınav değildir" in dr["kaynak_not"]
    assert ra["kabul_listesi"] is None and ra["aylar"] and ra["aylar"][0]["limit_olaylari"] is None
    st = d.oku_stratejiler(tmp_path)
    isl = {x["kimlik"]: x["islem_sayisi"] for x in st["stratejiler"]}
    assert {x["kimlik"]: x["islem"] for x in dr["stratejiler"]} == isl


def test_pano_dersler_ve_rapor_sekmeleri_dosyadaki_sayilari_gosterir(paper):
    p, o, dizin = paper
    veri, sorun = pano.yukle(dizin)
    assert not sorun
    html = pano.html_olustur(veri, sorun, pd.Timestamp("2027-01-05", tz="UTC").to_pydatetime())
    assert 'id="t7"' in html and 'id="t8"' in html and "Paper kabul kontrol listesi" in html and "Dersler: canlı sonuç" in html
    for x in veri["dersler"]["stratejiler"]:
        assert pano.kisa_kimlik(x["kimlik"]) in html
    for kal in veri["aylik_rapor"]["kabul_listesi"]["kalemler"]:
        assert pano.esc(kal["ad"]) in html
    assert "TANIMSIZ" in html and "Kullanıcıya sorulacak" in html
    # eski motor (ek dosya yok): bölümler 'veri yok' der, sayfa kırılmaz
    veri2 = dict(veri, dersler=None, aylik_rapor=None)
    h2 = pano.html_olustur(veri2, sorun, pd.Timestamp("2027-01-05", tz="UTC").to_pydatetime())
    assert "dersler.json" in h2 and "aylik_rapor.json" in h2


def test_pano_bozuk_dersler_kirilmaz(paper):
    p, o, dizin = paper
    veri, sorun = pano.yukle(dizin)
    veri = dict(veri, dersler={"stratejiler": [{"x": 1}]}, aylik_rapor={"aylar": [{"ay": "2026-11"}], "kabul_listesi": None})
    html = pano.html_olustur(veri, sorun, pd.Timestamp("2027-01-05", tz="UTC").to_pydatetime())
    assert "beklenen biçimde değil" in html
