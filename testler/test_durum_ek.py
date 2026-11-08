"""Motor yazıcı paketi (motor/canli/durum_ek.py): istatistik{}, cikis_nedenleri[], gunluk_kz_ajan[] (+ haftalık/aylık),
ajanlar[], enstrumanlar[], strateji_enstruman[], bekleyen_emirler[]; TSİ gün kesimi. Paper ve backtest yolları, pano birebir gösterimi."""
import json
import math
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from motor.canli import backtest_durum as bd
from motor.canli import durum as d
from motor.canli import durum_ek as ek
from motor.canli import pano
from motor.canli import paper as pp
from motor.canli import paper_durum as pdr
from motor.canli import paper_motor as pm
from testler.test_paper_motor import TAN, kural, sentetik

D = Decimal


# ---------------------------------------------------------------------------- TSİ gün kesimi
def test_tsi_gun_sinirlari():
    assert ek.tsi_gun("2026-11-07T20:59:59Z") == "2026-11-07"
    assert ek.tsi_gun("2026-11-07T21:00:00Z") == "2026-11-08"          # 00:00 TSİ
    # mum KAPANIŞI tam 00:00 TSİ ise özsermaye önceki güne aittir
    assert ek.kapanis_gunu("2026-11-07T21:00:00Z") == "2026-11-07"
    assert ek.kapanis_gunu("2026-11-07T21:00:01Z") == "2026-11-08"
    # yalın (tz'siz) zaman UTC sayılır
    assert ek.kapanis_gunu(pd.Timestamp("2026-11-07 23:00:00")) == "2026-11-08"


def test_hafta_ay_anahtari_tsi_gunune_gore():
    assert ek.hafta_anahtari("2026-11-02") == "2026-W45"               # pazartesi
    assert ek.hafta_anahtari("2026-11-08") == "2026-W45"               # pazar
    assert ek.hafta_anahtari("2026-11-09") == "2026-W46"
    assert ek.ay_anahtari("2026-11-30") == "2026-11"


# ---------------------------------------------------------------------------- istatistik
def _satir(r, pnl, kat=True, nedeni="stop", giris="2026-01-01T00:00:00Z", cikis="2026-01-01T10:00:00Z", kimlik="a|X|1h", sembol="X"):
    return {"zaman": cikis, "kimlik": kimlik, "sembol": sembol, "yon": "long", "giris_zamani": giris, "cikis_zamani": cikis,
            "r": r, "net_pnl_yerel": pnl, "set_katki_usd": pnl if kat else None, "cikis_nedeni": nedeni}


def _gunluk(n, getiri=None):
    out = []
    e = 10000.0
    for i in range(n):
        g = getiri[i] if getiri else (0.01 if i % 3 else -0.005)
        out.append({"gun": str((pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)).date()), "pnl": d.para(e * g), "getiri": g})
    return out


def test_istatistik_az_islemde_sqn_kelly_null_ve_neden():
    s = ek.istatistik([_satir(1.0, "10.00"), _satir(-0.5, "-5.00")], _gunluk(40))
    assert s["sqn"] is None and s["kelly_ceyrek"] is None
    assert f"{ek.MIN_ISLEM}" in s["istatistik_neden"] and "SQN" in s["istatistik_neden"]
    assert s["kazanc_kayip_orani"] == pytest.approx(2.0)
    assert s["beklenti_islem_basi"] == "2.50"


def test_istatistik_r_siz_satir_varsa_sqn_null_ve_neden():
    """Denetim: R'si olmayan satır varsa SQN nedensiz null kalmamalı (null + neden kuralı)."""
    sat = [_satir(1.0 if i % 2 else -0.5, "1.00") for i in range(ek.MIN_ISLEM + 5)] + [_satir(None, "0.00")]
    s = ek.istatistik(sat, _gunluk(40))
    assert s["sqn"] is None and "SQN ölçülmedi" in s["istatistik_neden"] and "1/" in s["istatistik_neden"]
    assert s["kelly_ceyrek"] is not None                                      # Kelly R'li işlemlerden (pay R listesi üzerinden)
    sabit = ek.istatistik([_satir(1.0, "1.00") for _ in range(ek.MIN_ISLEM)], _gunluk(40))
    assert sabit["sqn"] is None and "standart sapması sıfır" in sabit["istatistik_neden"]
    tam = ek.istatistik([_satir(1.0 if i % 2 else -0.5, "1.00") for i in range(ek.MIN_ISLEM)], _gunluk(40))
    assert tam["sqn"] is not None and "SQN" not in (tam["istatistik_neden"] or "")


def test_istatistik_az_gunde_sharpe_sortino_null():
    s = ek.istatistik([_satir(1.0, "10.00")], _gunluk(5))
    assert s["sharpe"] is None and s["sortino"] is None and "Sharpe" in s["istatistik_neden"]


def test_istatistik_degerleri_elle_hesapla_uyar():
    rng = np.random.default_rng(1)
    r = [float(x) for x in rng.normal(0.2, 1.0, 40)]
    sat = [_satir(round(x, 4), d.para(x * 10), cikis=f"2026-01-{1 + i % 28:02d}T12:00:00Z", giris=f"2026-01-{1 + i % 28:02d}T00:00:00Z")
           for i, x in enumerate(r)]
    gun = _gunluk(60, [0.01 if i % 4 else -0.02 for i in range(60)])
    s = ek.istatistik(sat, gun)
    rr = np.array([x["r"] for x in sat])
    assert s["sqn"] == pytest.approx(math.sqrt(40) * rr.mean() / rr.std(ddof=1))
    w = (rr > 0).mean()
    b = rr[rr > 0].mean() / -rr[rr < 0].mean()
    assert s["kelly_ceyrek"] == pytest.approx(0.25 * max(0.0, w - (1 - w) / b))
    g = np.array([x["getiri"] for x in gun])
    assert s["sharpe"] == pytest.approx(g.mean() / g.std(ddof=1) * math.sqrt(365))
    assert s["sortino"] == pytest.approx(g.mean() / math.sqrt((np.minimum(g, 0) ** 2).mean()) * math.sqrt(365))
    assert s["yesil_gun_orani"] == pytest.approx((g > 0).mean())
    assert s["ort_tutma_saat"] == pytest.approx(12.0)
    assert D(s["en_iyi_gun"]["pnl"]) == max(D(x["pnl"]) for x in gun)
    assert D(s["en_kotu_gun"]["pnl"]) == min(D(x["pnl"]) for x in gun)


def test_istatistik_seriler_zaman_sirasina_gore():
    pnl = ["1", "1", "1", "-1", "-1", "1"]
    sat = [_satir(1.0 if D(p) > 0 else -1.0, d.para(p), cikis=f"2026-01-0{i + 1}T12:00:00Z", giris=f"2026-01-0{i + 1}T00:00:00Z") for i, p in enumerate(pnl)]
    sat.reverse()                                                      # karışık sıra: motor kendisi sıralar
    s = ek.istatistik(sat, [])
    assert s["en_uzun_kazanc_serisi"] == 3 and s["en_uzun_kayip_serisi"] == 2
    assert s["en_iyi_gun"] is None and s["yesil_gun_orani"] is None


def test_istatistik_set_katkisi_olmayan_satirlar_para_alanini_yalniz_olcenden_alir():
    s = ek.istatistik([_satir(1.0, "10.00"), _satir(1.0, "999.00", kat=False)], [])
    assert s["beklenti_islem_basi"] == "10.00" and "1/2" in s["istatistik_neden"]


# ---------------------------------------------------------------------------- çıkış nedenleri
def test_cikis_nedenleri_pay_ve_net():
    sat = [_satir(1, "10.00", nedeni="hedef"), _satir(-1, "-4.00", nedeni="stop"), _satir(-1, "-6.00", nedeni="stop")]
    c, nt = ek.cikis_nedenleri(sat)
    assert nt is None
    assert [(x["neden"], x["islem"], x["net_pnl"]) for x in c] == [("stop", 2, "-10.00"), ("hedef", 1, "10.00")]
    assert sum(x["pay"] for x in c) == pytest.approx(1.0)


def test_cikis_nedenleri_karisik_birim_toplanmaz():
    c, nt = ek.cikis_nedenleri([_satir(1, "10.00", nedeni="stop"), _satir(1, "5.00", kat=False, nedeni="stop"), _satir(1, "2.00", nedeni="hedef")])
    kay = {x["neden"]: x for x in c}
    assert kay["stop"]["net_pnl"] is None and kay["hedef"]["net_pnl"] == "2.00" and nt


# ---------------------------------------------------------------------------- dönemsel getiri (saf fonksiyon)
def test_gunluk_kz_ajan_toplam_ve_donem_gruplama():
    bas = D("1000")
    gunler = [str((pd.Timestamp("2026-10-30") + pd.Timedelta(days=i)).date()) for i in range(14)]   # 30 Eki (Cum) .. 12 Kas
    sw = {g: D(i + 1) for i, g in enumerate(gunler)}                   # kümülatif +1/gün
    dt = {g: D(2 * (i + 1)) for i, g in enumerate(gunler)}             # kümülatif +2/gün
    ozs = {g: bas + sw[g] + dt[g] for g in gunler}
    out = ek.gunluk_kz_ajan({"s|X|1d": sw, "t|Y|1h": dt}, {"s|X|1d": "swing", "t|Y|1h": "daytrade"}, gunler, bas, ozs)
    assert all(D(x["toplam"]["pnl"]) == D("3.00") for x in out["gunluk"])
    assert all(x["ajanlar"]["swing"]["pnl"] == "1.00" and x["ajanlar"]["daytrade"]["pnl"] == "2.00" for x in out["gunluk"])
    assert out["gunluk"][0]["ajanlar"]["swing"]["getiri"] == pytest.approx(0.001)         # pnl / başlangıç
    h = {x["donem"]: x for x in out["haftalik"]}
    assert h["2026-W44"]["gun_sayisi"] == 3 and h["2026-W44"]["bas_gun"] == "2026-10-30" and h["2026-W44"]["toplam"]["pnl"] == "9.00"
    assert h["2026-W45"]["gun_sayisi"] == 7 and h["2026-W45"]["tamamlandi"] and not h["2026-W46"]["tamamlandi"]
    a = {x["donem"]: x for x in out["aylik"]}
    assert a["2026-10"]["gun_sayisi"] == 2 and a["2026-10"]["tamamlandi"] and a["2026-11"]["gun_sayisi"] == 12 and not a["2026-11"]["tamamlandi"]
    assert sum(D(x["toplam"]["pnl"]) for x in out["aylik"]) == ozs[gunler[-1]] - bas


# ---------------------------------------------------------------------------- kırılımlar (saf fonksiyon)
def test_kirilimlar_toplamlar_ve_null_hucre():
    st = [{"kimlik": "a__x|BTCUSDT|1h", "ajan": "swing", "ozsermaye_katkisi": "30.00"},
          {"kimlik": "pf__y|kripto|1d", "ajan": "portfoy", "ozsermaye_katkisi": "-5.00"}]
    sat = [_satir(1, "20.00", kimlik="a__x|BTCUSDT|1h", sembol="BTCUSDT"), _satir(-1, "-10.00", kimlik="a__x|BTCUSDT|1h", sembol="BTCUSDT"),
           _satir(1, "7.00", kimlik="pf__y|kripto|1d", sembol="ETHUSDT"), _satir(-1, "-3.00", kimlik="pf__y|kripto|1d", sembol="BTCUSDT")]
    hucre = {("a__x|BTCUSDT|1h", "BTCUSDT"): D("30"), ("pf__y|kripto|1d", "ETHUSDT"): D("8"), ("pf__y|kripto|1d", "BTCUSDT"): D("-13")}
    k = ek.kirilimlar(st, sat, hucre, D("1000"), [{"kimlik": "pf__y|kripto|1d", "sembol": "ETHUSDT"}])
    assert sum(D(a["ozsermaye_katkisi"]) for a in k["ajanlar"]) == D("25.00")
    assert sum(D(e["ozsermaye_katkisi"]) for e in k["enstrumanlar"]) == D("25.00")
    assert sum(D(m["ozsermaye_katkisi"]) for m in k["strateji_enstruman"]) == D("25.00")
    e = {x["sembol"]: x for x in k["enstrumanlar"]}
    assert e["BTCUSDT"]["strateji_sayisi"] == 2 and e["BTCUSDT"]["islem_sayisi"] == 3 and e["ETHUSDT"]["acik_pozisyon"] == 1
    a = {x["ajan"]: x for x in k["ajanlar"]}
    assert a["swing"]["pf"] == pytest.approx(2.0) and a["swing"]["kazanma_orani"] == 0.5 and a["portfoy"]["acik_pozisyon"] == 1
    # ölçülmeyen hücre -> toplamlar uydurulmaz
    hucre[("pf__y|kripto|1d", "ETHUSDT")] = None
    k2 = ek.kirilimlar(st, sat, hucre, D("1000"), [])
    e2 = {x["sembol"]: x for x in k2["enstrumanlar"]}
    assert e2["ETHUSDT"]["ozsermaye_katkisi"] is None and e2["ETHUSDT"]["katki_neden"] and e2["BTCUSDT"]["ozsermaye_katkisi"] == "17.00"
    assert any(m["ozsermaye_katkisi"] is None and m["katki_neden"] for m in k2["strateji_enstruman"])


# ---------------------------------------------------------------------------- bekleyen emirler (saf fonksiyon)
def test_bekleyen_emirler_giris_hedef_cikis_kucultme():
    nan = float("nan")
    aralik = pd.Timedelta(hours=1)
    birim = SimpleNamespace(son_t=pd.Timestamp("2026-11-07 10:00", tz="UTC"), aralik=aralik)
    acik_poz = SimpleNamespace(stop=D("95"))
    kollar = [
        SimpleNamespace(kimlik="a|X|1h", sembol="X", birim="1h", giris_emri=(1, 95.0, nan, 0), hedef_emri=None, cikis_emri=None, kucult_emri=None),
        SimpleNamespace(kimlik="b|Y|1h", sembol="Y", birim="1h", giris_emri=(-1, 50.0, 40.0, 0), hedef_emri=None, cikis_emri=None, kucult_emri=None),
        SimpleNamespace(kimlik="pf|Z|1d", sembol="Z", birim="1h", giris_emri=None, hedef_emri=(1, D("0.25"), 90.0), cikis_emri=None, kucult_emri=None),
        SimpleNamespace(kimlik="pf|W|1d", sembol="W", birim="1h", giris_emri=None, hedef_emri=(0, D("0"), nan), cikis_emri=None, kucult_emri=None),
        SimpleNamespace(kimlik="c|V|1h", sembol="V", birim="1h", giris_emri=None, hedef_emri=None, cikis_emri="sinyal", kucult_emri=0.5),
        SimpleNamespace(kimlik="d|U|1h", sembol="U", birim="1h", giris_emri=(1, 1.0, nan, 0), hedef_emri=None, cikis_emri=None, kucult_emri=None),
    ]
    m = SimpleNamespace(tum_kollar=kollar, birimler={"1h": birim}, acik={"c|V|1h": acik_poz, "d|U|1h": acik_poz})
    b = ek.bekleyen_emirler(m)
    tur = {x["kimlik"]: [] for x in b}
    for x in b:
        tur[x["kimlik"]].append(x["tur"])
    assert tur == {"a|X|1h": ["giris"], "b|Y|1h": ["giris"], "pf|Z|1d": ["hedef_agirlik"], "pf|W|1d": ["hedef_agirlik"], "c|V|1h": ["cikis", "kucultme"]}
    assert "d|U|1h" not in tur                                          # açık pozisyon varken giriş emri yürütülmez
    g = next(x for x in b if x["kimlik"] == "a|X|1h")
    assert g["yon"] == "long" and g["stop"] == "95.0" and g["hedef"] is None and g["sinyal_zamani"] == "2026-11-07T11:00:00Z"
    assert next(x for x in b if x["kimlik"] == "b|Y|1h")["yon"] == "short"
    assert next(x for x in b if x["kimlik"] == "pf|W|1d")["yon"] == "kapat"


# ---------------------------------------------------------------------------- paper yolu (entegrasyon)
@pytest.fixture(scope="module")
def kosu4h():
    t = TAN["swing__konsolidasyon-kirilim|SOLUSDT|4h"]
    m = sentetik(1500, "4h", 2, vol=0.02)
    kayit = []
    eski = pp.Paper.isle

    def isle(self, b, tt, mumlar, son_satir=False):
        eski(self, b, tt, mumlar, son_satir)
        kayit.append((tt + b.aralik, self.motor.ozs_son))
    pp.Paper.isle = isle
    try:
        p = pp.tekrar_calistir([t], {(t.sembol, t.tf): m}, {}, {t.sembol: kural(t.sembol)}, m.index[1000], m.index[-1] + pd.Timedelta(hours=4), kapat=False)
    finally:
        pp.Paper.isle = eski
    simdi = m.index[-1] + pd.Timedelta(hours=4, minutes=5)
    o = pdr.olustur(p, simdi, kaynak_saglik=[], beklenti_csv=bd.BEKLENTI_CSV)
    return p, o, kayit, simdi


def test_paper_tsi_gun_kapanisi_son_gozlemdir(kosu4h):
    p, o, kayit, simdi = kosu4h
    beklenen = {}
    for kap, e in kayit:
        beklenen[ek.kapanis_gunu(kap)] = e                             # sıralı: günün son gözlemi kazanır
    assert dict(p.motor.gun_kapanis_tsi) == beklenen
    assert set(p.motor.gun_kapanis_tsi) != set(p.motor.gun_kapanis)    # UTC günü serisi (risk limiti) ayrı korunur
    # gün sınırı: 20:00 UTC kapanışlı mum (23:00 TSİ) o TSİ gününün son 4h gözlemi
    d0 = sorted(beklenen)[3]
    son = [e for kap, e in kayit if ek.kapanis_gunu(kap) == d0][-1]
    assert beklenen[d0] == son


def test_paper_gunluk_kz_tsi_ve_ozet_tutarli(kosu4h):
    p, o, kayit, simdi = kosu4h
    oz = o["ozet"]
    assert oz["gun_kesimi"] == "Europe/Istanbul"
    nk = {x["gun"]: x["ozsermaye"] for x in o["gecmis"]["noktalar"]}
    assert set(x["gun"] for x in oz["gunluk_kz"]) <= set(nk)
    # günlük K/Z: TSİ günü kapanışları arasındaki fark
    kap = sorted(p.motor.gun_kapanis_tsi.items())
    for (g0, e0), (g1, e1) in zip(kap, kap[1:]):
        x = next((y for y in oz["gunluk_kz"] if y["gun"] == g1), None)
        if x:
            assert D(x["pnl"]) == D(d.para(e1 - e0))
    # ozet.gun_pnl: önceki TSİ gününün son özsermayesine göre
    bugun = str(simdi.tz_convert(ek.TSI).date())
    onc = max(g for g in p.motor.gun_kapanis_tsi if g < bugun)
    assert D(oz["gun_pnl"]) == D(d.para(p.motor.ozsermaye() - p.motor.gun_kapanis_tsi[onc]))


def test_paper_yeni_alanlar_birbiriyle_tutarli(kosu4h):
    p, o, kayit, simdi = kosu4h
    oz, st, mr = o["ozet"], o["stratejiler"], o["ekstra"]["maruziyet"]
    toplam = D(oz["toplam_pnl"])
    # ajanlar / enstrümanlar / matris toplamı = toplam K/Z
    for ad, alan in (("ajanlar", "ozsermaye_katkisi"), ("enstrumanlar", "ozsermaye_katkisi"), ("strateji_enstruman", "ozsermaye_katkisi")):
        assert abs(sum((D(x[alan]) for x in st[ad]), D(0)) - toplam) < D("0.05"), ad
    assert sum(x["islem_sayisi"] for x in st["enstrumanlar"]) == oz["sayaclar"]["kapanan_islem"] == sum(x["islem_sayisi"] for x in st["ajanlar"])
    assert sum(x["acik_pozisyon"] for x in st["enstrumanlar"]) == len(mr["pozisyonlar"])
    # dönemsel: gün gün stil K/Z toplamı = set günlük K/Z
    nk = {x["gun"]: x for x in oz["gunluk_kz"]}
    for x in oz["gunluk_kz_ajan"]:
        assert abs(sum(D(v["pnl"]) for v in x["ajanlar"].values()) - D(nk[x["gun"]]["pnl"])) < D("0.02"), x["gun"]
        assert D(x["toplam"]["pnl"]) == D(nk[x["gun"]]["pnl"])
    # haftalık/aylık toplam = tüm dönemin özsermaye farkı
    bas = D(p.ayarlar.baslangic_sermaye)
    son = p.motor.gun_kapanis_tsi[max(p.motor.gun_kapanis_tsi)]
    tum_gun = ek.gunluk_kz_ajan(p.strateji_gun_tsi, {t.kimlik: t.ajan for t in p.tanimlar}, sorted(p.motor.gun_kapanis_tsi), bas,
                                {g: D(e) for g, e in p.motor.gun_kapanis_tsi.items()})
    assert abs(sum(D(x["toplam"]["pnl"]) for x in tum_gun["aylik"]) - (son - bas)) < D("0.05")
    assert oz["haftalik_kz_ajan"] and oz["aylik_kz_ajan"]
    # istatistik / çıkış nedenleri
    assert oz["istatistik"]["islem_sayisi"] == len(o["islemler"])
    assert sum(x["islem"] for x in oz["cikis_nedenleri"]) == len(o["islemler"]) and oz["cikis_nedenleri_not"] is None
    assert D(sum((D(x["net_pnl"]) for x in oz["cikis_nedenleri"]), D(0))) == sum((D(x["set_katki_usd"]) for x in o["islemler"]), D(0))
    # bekleyen emirler maruziyet.json'da liste olarak vardır
    assert isinstance(mr["bekleyen_emirler"], list)
    assert all(x["tur"] in ("giris", "hedef_agirlik", "cikis", "kucultme") for x in mr["bekleyen_emirler"])


def test_paper_islem_satirinda_tsi_gunu(kosu4h):
    p, o, kayit, simdi = kosu4h
    assert o["islemler"], "sentetik veri işlem üretmeli"
    for s in o["islemler"]:
        assert s["gun"] == ek.tsi_gun(s["cikis_zamani"])


def test_paper_yazilir_okunur_ve_pano_birebir_gosterir(kosu4h, tmp_path):
    p, o, kayit, simdi = kosu4h
    d.yaz_hepsi(tmp_path, ozet=o["ozet"], stratejiler=o["stratejiler"], islemler=o["islemler"], saglik=o["saglik"], gecmis=o["gecmis"], ekstra=o["ekstra"])
    veri, sorun = d.oku_hepsi(tmp_path)
    assert not sorun
    from testler.test_pano import _html
    html, _, _ = _html(tmp_path)
    for alan in ("ozet.json → istatistik{}", "ozet.json → gunluk_kz_ajan[]", "ozet.json → cikis_nedenleri[]", "stratejiler.json → ajanlar[]",
                 "stratejiler.json → enstrumanlar[]", "stratejiler.json → strateji_enstruman[]", "maruziyet.json → bekleyen_emirler[]"):
        assert alan not in html, alan                                   # motor yazdı: "veri yok" kartı çıkmaz
    assert "TSİ günü" in html
    iyi = o["ozet"]["istatistik"]["en_iyi_gun"]
    assert iyi is None or pano.f_para(iyi["pnl"], True) in html


def test_paper_durum_kaydet_yukle_tsi_serisi_korunur(tmp_path):
    t = TAN["swing__cci-esik|SOLUSDT|1d"]
    m = sentetik(520, "1d", 11, vol=0.03)
    kur = {t.sembol: kural(t.sembol)}
    yol = tmp_path / "s.json"
    a = pp.Paper([t], pp.TekrarKaynagi({(t.sembol, t.tf): m}, {}), kur, durum_yolu=yol)
    a.baslat(m.index[400])
    a.adim(m.index[460])
    a.kaydet()
    b = pp.Paper([t], pp.TekrarKaynagi({(t.sembol, t.tf): m}, {}), kur, durum_yolu=yol)
    assert b.yukle()
    assert b.motor.gun_kapanis_tsi == a.motor.gun_kapanis_tsi and b.strateji_gun_tsi == a.strateji_gun_tsi and not b.motor.tsi_aktarildi
    # eski durum dosyası (TSİ alanları yok): UTC serisi devralınır ve bayrak kalıcı olur
    j = json.loads(yol.read_text(encoding="utf-8"))
    del j["motor"]["gun_kapanis_tsi"], j["motor"]["tsi_aktarildi"], j["strateji_gun_tsi"]
    yol.write_text(json.dumps(j), encoding="utf-8")
    c = pp.Paper([t], pp.TekrarKaynagi({(t.sembol, t.tf): m}, {}), kur, durum_yolu=yol)
    assert c.yukle()
    assert c.motor.tsi_aktarildi and c.motor.gun_kapanis_tsi == c.motor.gun_kapanis and c.strateji_gun_tsi == c.strateji_gun
    o = pdr.olustur(c, m.index[460] + pd.Timedelta(minutes=5), kaynak_saglik=[])
    assert any("TSİ" in n for n in o["ozet"]["notlar"])


# ---------------------------------------------------------------------------- backtest yolu (gerçek kilit çıktıları)
@pytest.fixture(scope="module")
def bt():
    if not (Path(bd.KOK) / "sonuclar" / "kilit" / "sonuc.csv").exists():
        pytest.skip("sonuclar/kilit yok")
    return bd.olustur()


def test_backtest_yeni_alanlar_ve_tutarlilik(bt):
    oz, st = bt["ozet"], bt["stratejiler"]
    assert oz["gun_kesimi"] == ek.GUN_KESIMI_UTC_IZGARA
    toplam = D(oz["toplam_pnl"])
    assert abs(sum((D(a["ozsermaye_katkisi"]) for a in st["ajanlar"]), D(0)) - toplam) < D("0.05")
    assert sum(a["islem_sayisi"] for a in st["ajanlar"]) == oz["sayaclar"]["kapanan_islem"] == oz["istatistik"]["islem_sayisi"]
    assert sum(x["islem"] for x in oz["cikis_nedenleri"]) == oz["sayaclar"]["kapanan_islem"]
    # gün gün: stil toplamı = set günlük K/Z
    nk = {x["gun"]: x for x in oz["gunluk_kz"]}
    for x in oz["gunluk_kz_ajan"]:
        assert abs(sum(D(v["pnl"]) for v in x["ajanlar"].values()) - D(nk[x["gun"]]["pnl"])) < D("0.05"), x["gun"]
    # dönem toplamı tüm dönemi örter (aylık son 12 ay)
    assert all(x["gun_sayisi"] >= 1 for x in oz["aylik_kz_ajan"]) and oz["haftalik_kz_ajan"]
    # portföy kolunda sembol katkısı ölçülmez: null + neden (uydurma yok)
    pf = [x for x in st["strateji_enstruman"] if x["strateji"].startswith("pf__")]
    assert pf and all(x["ozsermaye_katkisi"] is None and x["katki_neden"] for x in pf)
    tek = [x for x in st["strateji_enstruman"] if not x["strateji"].startswith("pf__")]
    assert tek and all(x["ozsermaye_katkisi"] is not None for x in tek)
    assert bt["ekstra"]["maruziyet"]["bekleyen_emirler"] is None


def test_backtest_yazilir_ve_pano_gosterir(bt, tmp_path):
    d.yaz_hepsi(tmp_path, ozet=bt["ozet"], stratejiler=bt["stratejiler"], islemler=bt["islemler"], saglik=bt["saglik"], gecmis=bt["gecmis"], ekstra=bt["ekstra"])
    from testler.test_pano import _html
    html, _, _ = _html(tmp_path)
    for alan in ("ozet.json → istatistik{}", "ozet.json → gunluk_kz_ajan[]", "ozet.json → cikis_nedenleri[]", "stratejiler.json → ajanlar[]",
                 "stratejiler.json → enstrumanlar[]", "stratejiler.json → strateji_enstruman[]"):
        assert alan not in html, alan
    assert "maruziyet.json → bekleyen_emirler[]" in html                # backtestte emir kuyruğu ölçülmez: açıkça "veri yok"
    assert "UTC günü" in html
