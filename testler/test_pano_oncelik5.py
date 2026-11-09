"""Pano öncelik 5: beklenti konisi, kıyas serileri, korelasyon, yoğunlaşma. Ağ yok, ağır backtest yok."""
import csv
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest
from testler.conftest import KILIT_ISLEM_NEDEN, kilit_islemleri_var

from motor.canli import durum as d
from motor.canli import kiyas as ky
from motor.canli import koni as kn
from motor.canli import korelasyon as kr
from motor.canli import pano
from motor.canli import yogunlasma as yg


def _havuz(tmp_path, gun=200, bas="2024-01-01", tohum=1, bosluk_sonrasi=0):
    rng = np.random.default_rng(tohum)
    ix = pd.date_range(bas, periods=gun, freq="D")
    yol = tmp_path / "havuz.csv"
    with open(yol, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(("gun", "ret"))
        for t, r in zip(ix, rng.normal(0.0005, 0.005, gun)):
            w.writerow((str(t.date()), repr(float(r))))
    return yol, ix


# ------------------------------------------------------------------ (a) koni
def test_koni_tohum_sabit_ve_yeniden_uretilebilir(tmp_path):
    yol, ix = _havuz(tmp_path)
    baz = str(ix[-1].date())
    a = kn.olustur("paper", "2026-11-08T00:00:00Z", baz, None, havuz_yolu=yol, sha_kayitli=None, n=500)
    b = kn.olustur("paper", "2026-11-09T00:00:00Z", baz, None, havuz_yolu=yol, sha_kayitli=None, n=500)
    assert a["koni"] == b["koni"] and a["koni"][0]["p50"] == 0.0 and len(a["koni"]) == kn.UFUK_GUN + 1
    assert all(r["p05"] <= r["p25"] <= r["p50"] <= r["p75"] <= r["p95"] for r in a["koni"])
    assert a["tohum"] == 42 and a["blok_gun"] == 14


def test_koni_gerceklesen_veriyle_degismez_ve_havuz_baz_gunden_sonrasini_almaz(tmp_path):
    yol, ix = _havuz(tmp_path)
    baz = str(ix[99].date())                                    # baz günden sonraki 100 gün havuza girmemeli
    k0 = kn.olustur("paper", "z", baz, None, havuz_yolu=yol, sha_kayitli=None, n=300)
    gz = [{"gun": baz, "getiri": 0.0}, {"gun": str(ix[100].date()), "getiri": 0.5}]
    k1 = kn.olustur("paper", "z", baz, gz, havuz_yolu=yol, sha_kayitli=None, n=300)
    assert k0["koni"] == k1["koni"]                             # gerçekleşen değer koniyi oynatmaz
    assert k1["havuz"]["gun_sayisi"] == 100 and k1["havuz"]["bit"] == baz and k1["havuz"]["baz_gun_sonrasi_cikarilan"] == 100
    # baz günden sonrasını değiştir: koni aynı kalır (lookahead yok)
    satirlar = list(csv.reader(open(yol)))
    for s in satirlar[101:]:
        s[1] = "0.9"
    with open(yol, "w", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(satirlar)
    assert kn.olustur("paper", "z", baz, None, havuz_yolu=yol, sha_kayitli=None, n=300)["koni"] == k0["koni"]
    assert k1["konum"]["bant"] == "p95_ustu" and 0.99 < k1["konum"]["yuzdelik_sira"] <= 1.0


def test_koni_sha_uyusmuyor_ve_havuz_yok_ve_kisa_havuz_null_neden(tmp_path):
    yol, ix = _havuz(tmp_path)
    k = kn.olustur("paper", "z", str(ix[-1].date()), None, havuz_yolu=yol, sha_kayitli="0" * 64, n=100)
    assert k["koni"] is None and "uyuşmuyor" in k["koni_neden"] and k["havuz"]["dogrulama"] == "uyusmuyor"
    k = kn.olustur("paper", "z", "2026-01-01", None, havuz_yolu=tmp_path / "yok.csv", n=100)
    assert k["koni"] is None and "yok" in k["koni_neden"]
    k = kn.olustur("paper", "z", str(ix[5].date()), None, havuz_yolu=yol, sha_kayitli=None, n=100)       # yalnız 6 günlük havuz < blok 14
    assert k["koni"] is None and "blok" in k["koni_neden"]


def test_koni_konum_ufuk_disi_ve_gun_yok(tmp_path):
    yol, ix = _havuz(tmp_path)
    baz = str(ix[-1].date())
    k = kn.olustur("paper", "z", baz, [{"gun": baz, "getiri": 0.0}], havuz_yolu=yol, sha_kayitli=None, n=100)
    assert k["konum"] is None and "henüz yok" in k["konum_neden"]
    gz = [{"gun": str((ix[-1] + pd.Timedelta(days=g)).date()), "getiri": 0.001 * g} for g in range(0, 130)]
    k = kn.olustur("paper", "z", baz, gz, havuz_yolu=yol, sha_kayitli=None, n=100)
    assert k["konum"]["gun_no"] == kn.UFUK_GUN and k["konum"]["not"]


def test_gercek_havuz_kayitli_sha_ve_beklenti_araliklariyla_tutarli():
    k = kn.olustur("paper", "2026-11-08T00:00:00Z", "2026-11-06", None)
    assert k["havuz"]["dogrulama"] == "eslesti" and k["havuz"]["bit"] < "2026-11-07" and k["havuz"]["baz_gun_sonrasi_cikarilan"] == 0
    b = pd.read_csv(kn.KOK / "sonuclar" / "final" / "beklenti_araliklari.csv")
    s8 = b[(b.kimlik == "set") & (b.metrik == "net_getiri") & (b.pencere_hafta == 8)].iloc[0]
    g56 = k["koni"][56]
    assert abs(g56["p50"] - s8.p50) < 0.01 and abs(g56["p05"] - s8.p05) < 0.01 and abs(g56["p95"] - s8.p95) < 0.015


# ------------------------------------------------------------------ (b) kıyas
def _mumlar(dizin, sembol="BTCUSDT", tf="1h", bas="2026-11-01", gun=10, fiyat0=100.0):
    ix = pd.date_range(bas, periods=gun * 24, freq="h", tz="UTC", name="zaman")
    (dizin / sembol).mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"kapanis": fiyat0 * (1 + 0.001 * np.arange(len(ix)))}, index=ix).to_parquet(dizin / sembol / f"{tf}.parquet")


def test_kiyas_btc_al_tut_kapanmis_mum_ve_tsi_gun_kesimi(tmp_path):
    _mumlar(tmp_path)
    ay = tmp_path / "ayar.json"
    ay.write_text(json.dumps({"mevduat_yillik_oran": None}))
    gunler = ["2026-11-03", "2026-11-04"]
    k = ky.olustur("paper", "z", "2026-11-04T10:00:00Z", "2026-11-02", gunler, {"2026-11-03": 0.01, "2026-11-04": 0.02}, "Europe/Istanbul", "Europe/Istanbul",
                   veri_dizini=tmp_path, ayar_yolu=ay)
    btc = next(s for s in k["seriler"] if s["kimlik"] == "btc")
    # baz: 2026-11-02 sonu TSİ = 11-02 21:00 UTC; mum 20:00 açılış -> 21:00 kapanır (indeks 2*24+20 = 68); 11-03 sonu = 11-03 21:00 -> indeks 92
    f = lambda i: 100.0 * (1 + 0.001 * i)                                                     # noqa: E731
    assert btc["noktalar"][1]["getiri"] == pytest.approx(f(68) / f(44) - 1)
    # 11-04 günü bitmedi: simdi = 11-04 10:00 UTC -> son KAPANMIŞ mum 09:00 açılışlı (10:00 kapanış), indeks 3*24+9 = 81+... = 81? (11-04 00:00 = indeks 72*... )
    son = btc["noktalar"][2]["getiri"]
    assert son == pytest.approx(f(3 * 24 + 9) / f(44) - 1) and son > btc["noktalar"][1]["getiri"]
    assert k["seriler"][0]["kimlik"] == "paper" and k["seriler"][0]["noktalar"][0] == {"gun": "2026-11-02", "getiri": 0.0}


def test_kiyas_mevduat_oran_yoksa_null_ve_kullanici_girmeli_oran_varsa_bilesik(tmp_path):
    _mumlar(tmp_path)
    ay = tmp_path / "ayar.json"
    k = ky.olustur("paper", "z", "2026-11-05T00:00:00Z", "2026-11-02", ["2026-11-03"], {"2026-11-03": 0.0}, "UTC", "UTC", veri_dizini=tmp_path, ayar_yolu=ay)
    m = k["seriler"][-1]
    assert m["kimlik"] == "mevduat" and m["yillik_oran"] is None and m["kullanici_girmeli"] is True and m["noktalar"] == [] and "kullanıcı oranı girmeli" in m["neden"]
    ay.write_text(json.dumps({"mevduat_yillik_oran": 0.365}))
    m = ky.olustur("paper", "z", "2026-11-05T00:00:00Z", "2026-11-02", ["2026-11-03"], {"2026-11-03": 0.0}, "UTC", "UTC", veri_dizini=tmp_path, ayar_yolu=ay)["seriler"][-1]
    assert m["kullanici_girmeli"] is False and m["noktalar"][1]["getiri"] == pytest.approx(1.365 ** (1 / 365) - 1)
    ay.write_text(json.dumps({"mevduat_yillik_oran": "yuzde40"}))
    with pytest.raises(ValueError):
        ky.ayar_oku(ay)
    assert ky.ayar_oku(tmp_path / "yok.json") == {"mevduat_yillik_oran": None}


def test_kiyas_veri_yok_ve_bayat_null_neden(tmp_path):
    _mumlar(tmp_path, "DK_SPX", bas="2026-11-01", gun=3)                         # 11-03 sonunda biter
    k = ky.olustur("paper", "z", "2026-11-12T00:00:00Z", "2026-11-02", ["2026-11-03", "2026-11-10"], {}, "UTC", "UTC", veri_dizini=tmp_path, ayar_yolu=tmp_path / "a.json")
    btc = next(s for s in k["seriler"] if s["kimlik"] == "btc")
    assert btc["noktalar"] == [] and "mum arşivi yok" in btc["neden"]
    spx = next(s for s in k["seriler"] if s["kimlik"] == "spx")
    assert spx["noktalar"][1]["getiri"] is not None and spx["noktalar"][2]["getiri"] is None and "güncel fiyat yok" in spx["neden"]


# ------------------------------------------------------------------ (c) korelasyon
def _seriler(n, tohum=3):
    rng = np.random.default_rng(tohum)
    ix = [str(t.date()) for t in pd.date_range("2026-01-01", periods=n, freq="D")]
    a = rng.normal(0, 0.01, n)
    return {"a": pd.Series(a, index=ix), "b": pd.Series(a * 2 + rng.normal(0, 0.001, n), index=ix), "c": pd.Series(-a, index=ix), "s": pd.Series(0.0, index=ix)}


def test_korelasyon_degerler_ve_sabit_seri_null():
    k = kr.hesapla(_seriler(60), "paper", "z", "Europe/Istanbul")
    ks = k["kimlikler"]
    i = {x: ks.index(x) for x in ks}
    assert k["matris"][i["a"]][i["b"]] > 0.99 and k["matris"][i["a"]][i["c"]] == pytest.approx(-1.0)
    assert k["matris"][i["a"]][i["s"]] is None and any(h["b"] == "s" and "sabit" in h["neden"] for h in k["hucre_neden"])
    assert k["ortak_gun"][0][1] == 60 and k["guven_araligi"][i["a"]][i["b"]][0] < k["matris"][i["a"]][i["b"]] < 1.0 + 1e-9
    assert k["esik"] is None and k["ozet"]["en_yuksek"]["korelasyon"] > 0.99


def test_korelasyon_30_gun_yoksa_null_ve_neden():
    k = kr.hesapla(_seriler(29), "paper", "z", "Europe/Istanbul")
    assert k["matris"] is None and "30" in k["neden"] and "29" in k["neden"]
    assert kr.hesapla(_seriler(30), "paper", "z", "x")["matris"] is not None
    assert kr.hesapla({"a": _seriler(40)["a"]}, "paper", "z", "x")["matris"] is None


def test_katki_serileri_onceki_gun_ozsermayesine_bolunur():
    kum = {"s1": {"2026-01-01": 100.0, "2026-01-03": 50.0}}
    r = kr.katki_serileri(kum, {"2026-01-01": 10100.0, "2026-01-02": 10100.0, "2026-01-03": 10050.0}, 10000.0)["s1"]
    assert list(r.index) == ["2026-01-01", "2026-01-02", "2026-01-03"]
    assert r["2026-01-01"] == pytest.approx(0.01) and r["2026-01-02"] == 0.0 and r["2026-01-03"] == pytest.approx(-50 / 10100)


# ------------------------------------------------------------------ (d) yoğunlaşma
def _poz(k, s, yon, nom, risk):
    return {"kimlik": k, "sembol": s, "yon": yon, "nominal": nom, "stop_riski": risk}


def test_yogunlasma_sinif_sembol_paylari_ve_esik_yok():
    y = yg.olustur("paper", "z", [_poz("a|BTCUSDT|1h", "BTCUSDT", "long", "3000.00", "100.00"), _poz("b|BTCUSDT|4h", "BTCUSDT", "short", "1000.00", "50.00"),
                                  _poz("c|DK_XAU|1d", "DK_XAU", "long", "4000.00", "50.00"), _poz("e|DK_NVDA|4h", "DK_NVDA", "long", "2000.00", "100.00")], "10000")
    b = next(x for x in y["semboller"] if x["sembol"] == "BTCUSDT")
    assert b["brut_nominal"] == "4000.00" and b["net_nominal"] == "2000.00" and b["brut_oran"] == pytest.approx(0.4) and b["brut_pay"] == pytest.approx(0.4)
    assert b["stop_riski_pay"] == pytest.approx(0.5) and b["strateji_sayisi"] == 2 and b["sinif"] == "kripto"
    sn = {x["sinif"]: x for x in y["siniflar"]}
    assert set(sn) == {"kripto", "emtia", "hisse"} and sn["emtia"]["brut_pay"] == pytest.approx(0.4) and y["toplam_brut_nominal"] == "10000.00"
    assert y["esikler"]["sembol_pay"] == 0.40 and y["esikler"]["sinif_pay"] is None and "2026-11-08" in y["esikler"]["neden"]
    assert [(u["sembol"], u["tur"]) for u in y["uyarilar"]] == [("BTCUSDT", "sembol_risk_payi")] and y["uyarilar"][0]["deger"] == pytest.approx(0.5) and y["uyarilar"][0]["esik"] == 0.40
    assert y["en_buyuk_sembol"]["brut_pay"] == pytest.approx(0.4) and y["etkin_sembol_sayisi"] == pytest.approx(1 / (0.4 ** 2 + 0.4 ** 2 + 0.2 ** 2))


def test_yogunlasma_uyari_tam_yuzde_40_uyarmaz_ustu_uyarir():
    def y_(r1, r2, r3):
        return yg.olustur("paper", "z", [_poz("a|BTCUSDT|1h", "BTCUSDT", "long", "1000.00", r1), _poz("b|DK_XAU|1d", "DK_XAU", "long", "1000.00", r2),
                                         _poz("c|DK_NVDA|4h", "DK_NVDA", "long", "1000.00", r3)], "10000")
    assert y_("40.00", "30.00", "30.00")["uyarilar"] == []                                  # tam %40: uyarı yok (kesin >)
    u = y_("41.00", "29.00", "30.00")["uyarilar"]                                           # %41 > %40
    assert len(u) == 1 and u[0]["sembol"] == "BTCUSDT" and u[0]["deger"] == pytest.approx(0.41) and "%40" in u[0]["mesaj"]
    assert {x["sembol"] for x in y_("45.00", "45.00", "10.00")["uyarilar"]} == {"BTCUSDT", "DK_XAU"}


def test_yogunlasma_uyari_pozisyon_yok_ve_sifir_risk_uyarmaz():
    assert yg.olustur("paper", "z", [], "10000")["uyarilar"] == []
    assert yg.olustur("paper", "z", [_poz("a|BTCUSDT|1h", "BTCUSDT", "long", "1000.00", "0.00")], "10000")["uyarilar"] == []


def test_yogunlasma_uyari_panoda_gorunur():
    y = yg.olustur("paper", "z", [_poz("a|BTCUSDT|1h", "BTCUSDT", "long", "1000.00", "80.00"), _poz("b|DK_XAU|1d", "DK_XAU", "long", "1000.00", "20.00")], "10000")
    h = pano._yogunlasma_html(y)
    assert 'class="uyari uyari"' in h and "BTCUSDT" in h and "%40" in h


def test_yogunlasma_pozisyon_yok_ve_olculmedi():
    y = yg.olustur("paper", "z", [], "10000")
    assert y["semboller"] == [] and y["en_buyuk_sembol"] is None and "yok" in y["olculmedi_neden"]
    y = yg.olustur("backtest", "z", None, "10000", "backtest ölçmez")
    assert y["semboller"] is None and y["olculmedi_neden"] == "backtest ölçmez"


# ------------------------------------------------------------------ durum yazımı + pano
def _ekler(tmp_path):
    yol, ix = _havuz(tmp_path)
    baz = str(ix[-1].date())
    gz = [{"gun": str((ix[-1] + pd.Timedelta(days=g)).date()), "getiri": 0.002 * g} for g in range(0, 6)]
    _mumlar(tmp_path / "m", bas=str((ix[-1] + pd.Timedelta(days=-1)).date()), gun=10)
    z = "2026-01-05T12:00:00Z"
    kon = kn.olustur("paper", z, baz, gz, havuz_yolu=yol, sha_kayitli=None, n=300)
    kiy = ky.olustur("paper", z, pd.Timestamp(gz[-1]["gun"], tz="UTC") + pd.Timedelta(hours=20), baz, [x["gun"] for x in gz[1:]], {x["gun"]: x["getiri"] for x in gz},
                     "UTC", "UTC", veri_dizini=tmp_path / "m", ayar_yolu=tmp_path / "a.json")
    kor = kr.hesapla(_seriler(40), "paper", z, "Europe/Istanbul")
    yog = yg.olustur("paper", z, [_poz("a|BTCUSDT|1h", "BTCUSDT", "long", "3000.00", "100.00")], "10000")
    return {"koni": kon, "kiyas": kiy, "korelasyon": kor, "yogunlasma": yog}


def test_durum_dosyalari_yazilir_okunur_ve_pano_ciziyor(tmp_path):
    from testler.test_pano import genis_durum
    p = genis_durum()
    p["ekstra"].update(_ekler(tmp_path))
    out = tmp_path / "durum"
    d.yaz_hepsi(out, **p)
    for ad in ("koni", "kiyas", "korelasyon", "yogunlasma"):
        assert d.ek_oku(out, ad)["sema"] == f"1l3a.durum.{ad}"
    veri, sorun = pano.yukle(out)
    h = pano.html_olustur(veri, sorun, datetime(2026, 1, 5, 12, 10, tzinfo=timezone.utc))
    for b in ("Beklenti konisi", "kn-med", 'class="cizgi kc1"', "Kıyas (aynı dönem)", "kullanıcı oranı girmeli", "Strateji korelasyonu", 'class="kor"',
              "Yoğunlaşma (sınıf / sembol)", "Kullanıcı kararı 2026-11-08", pano.f_yuzde(veri["koni"]["konum"]["getiri"], True)):
        assert b in h, b


def test_ek_dosya_yokken_veri_yok_der_ve_bozuk_bolum_kirmaz(tmp_path):
    from testler.test_pano import genis_durum
    p = genis_durum()
    d.yaz_hepsi(tmp_path, **p)
    veri, sorun = pano.yukle(tmp_path)
    h = pano.html_olustur(veri, sorun, datetime(2026, 1, 5, 12, 10, tzinfo=timezone.utc))
    for a in ("koni.json", "kiyas.json", "korelasyon.json", "yogunlasma.json"):
        assert a in h
    veri["koni"] = {"koni": [{"x": 1}], "ufuk_gun": 3}
    assert "beklenen biçimde değil" in pano.html_olustur(veri, sorun, datetime(2026, 1, 5, 12, 10, tzinfo=timezone.utc))


def test_koni_null_neden_panoda_gorunur(tmp_path):
    from testler.test_pano import genis_durum
    p = genis_durum()
    p["ekstra"]["koni"] = kn.olustur("paper", "2026-01-05T12:00:00Z", "2026-01-01", None, havuz_yolu=tmp_path / "yok.csv")
    d.yaz_hepsi(tmp_path, **p)
    veri, sorun = pano.yukle(tmp_path)
    assert "koni havuzu dosyası yok" in pano.html_olustur(veri, sorun, datetime(2026, 1, 5, 12, 10, tzinfo=timezone.utc))


@pytest.mark.gercek_veri(kilit_islemleri_var(), reason=KILIT_ISLEM_NEDEN)
def test_backtest_durum_dort_dosyayi_yazar_koni_donem_icini_dislar():
    from motor.canli import backtest_durum as bd
    e = bd.olustur()["ekstra"]
    assert e["koni"]["koni"] is not None and e["koni"]["havuz"]["bit"] < e["koni"]["gerceklesen"][0]["gun"]
    assert e["koni"]["havuz"]["baz_gun_sonrasi_cikarilan"] > 0 and e["yogunlasma"]["semboller"] is None and e["korelasyon"]["matris"] is not None
    assert [s["kimlik"] for s in e["kiyas"]["seriler"]] == ["paper", "btc", "spx", "mevduat"]
