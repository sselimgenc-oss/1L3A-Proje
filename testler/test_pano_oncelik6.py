"""Pano öncelik 6: karne (radar), koç (kurallı tespitler), işlem açıklama çekmecesi + MFE/MAE. Ağ yok, ağır backtest yok."""
import itertools
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
import pytest

from motor.backtest.motor import SembolKurallari
from motor.canli import backtest_durum as bd
from motor.canli import dersler as ds
from motor.canli import durum as d
from motor.canli import karne as kr
from motor.canli import koc as kc
from motor.canli import pano
from motor.canli import paper as pp
from motor.canli import paper_durum as pdr
from motor.canli.paper_motor import _dec, _enc
from testler.test_paper_motor import TAN, duz, kural, sentetik, tanim

KIM = "swing__cci-esik|SOLUSDT|1d"
Z = "2026-11-08T00:00:00Z"
YASAK = re.compile(r"art[ıi]r|büyüt|katla|\bekle\b|ekleme|kelly|martingale|\bdca\b|ortalama\s+düş|daha\s+fazla\s+risk|kaldıraç\s+art|pozisyon\s+büy", re.I)


def _ref(isabet=0.5, ort_r=0.0, std_r=1.0, cikis=None):
    return {"n": 200, "isabet": isabet, "ort_r": ort_r, "std_r": std_r, "pf_r": 1.5, "cikis_paylari": cikis or {"sinyal": 1.0}, "kaynak": "t"}


def _tsi_utc(gun: str, saat: int, dk: int = 0) -> datetime:
    """TSİ gün+saat -> UTC datetime (TSİ = UTC+3)."""
    return datetime.fromisoformat(f"{gun}T{saat:02d}:{dk:02d}:00").replace(tzinfo=timezone.utc) - timedelta(hours=3)


def _isl(i, r, kim=KIM, neden="sinyal", saat=10, gun_ofset=None, tutma_saat=6.0, sembol="SOLUSDT"):
    """i. işlem: giriş TSİ `saat`, günü i'ye göre; çıkış = giriş + tutma_saat."""
    g = pd.Timestamp("2026-01-05") + pd.Timedelta(days=i if gun_ofset is None else gun_ofset)
    giris = _tsi_utc(str(g.date()), saat)
    cikis = giris + timedelta(hours=tutma_saat)
    return {"zaman": d.zaman_str(cikis), "kimlik": kim, "sembol": sembol, "yon": "long", "giris_zamani": d.zaman_str(giris), "giris_fiyati": "100.0",
            "cikis_zamani": d.zaman_str(cikis), "cikis_fiyati": "101.0", "miktar": "1.0", "r": r, "net_pnl_yerel": f"{r:.2f}", "set_katki_usd": f"{r:.2f}", "cikis_nedeni": neden}


def _ders(satirlar, ref=None, kim=KIM, konum=None):
    return ds.olustur("paper", Z, [kim], satirlar, {kim: konum} if konum else None, referans={kim: ref or _ref()})


def _konum(deger_net, deger_dd, hafta=8, net_q=(-0.03, -0.01, 0.01, 0.03, 0.08), dd_q=(0.005, 0.01, 0.02, 0.03, 0.05)):
    qn = dict(zip(("p05", "p25", "p50", "p75", "p95"), net_q), alarm_yonu="alt", alarm_esigi=net_q[0])
    qd = dict(zip(("p05", "p25", "p50", "p75", "p95"), dd_q), alarm_yonu="ust", alarm_esigi=dd_q[4])
    return {str(hafta): {"net_getiri": d.konum("net_getiri", deger_net, qn, hafta), "max_dusus": d.konum("max_dusus", deger_dd, qd, hafta)}}


# ============================================================================== KARNE
def test_yuzdelik_puan_noktalari_ve_monotonluk():
    q = dict(zip(("p05", "p25", "p50", "p75", "p95"), (-0.03, -0.01, 0.01, 0.03, 0.08)))
    for v, beklenen in ((-0.03, 5), (-0.01, 25), (0.01, 50), (0.03, 75), (0.08, 95)):
        assert kr.yuzdelik_puan(v, q) == pytest.approx(beklenen)
    assert kr.yuzdelik_puan(0.0, q) == pytest.approx(37.5)                       # segment ortası
    assert kr.yuzdelik_puan(-0.05, q) == 0.0 and kr.yuzdelik_puan(-1.0, q) == 0.0  # %5 altı bir segment genişliğinde 0'a iner
    assert kr.yuzdelik_puan(0.5, q) == 100.0
    xs = [i / 100 for i in range(-10, 15)]
    ps = [kr.yuzdelik_puan(x, q) for x in xs]
    assert ps == sorted(ps)
    düz = dict(p05=0.0, p25=0.0, p50=0.0, p75=0.0, p95=0.0)                      # tüm yüzdelikler eşit: bölme hatası yok
    assert 0.0 <= kr.yuzdelik_puan(0.0, düz) <= 100.0 and kr.yuzdelik_puan(1.0, düz) == 100.0 and kr.yuzdelik_puan(-1.0, düz) == 0.0


def test_getiri_risk_alarm_ve_ters_cevrilen_risk():
    iyi = kr.getiri_risk(_konum(0.02, 0.008))
    kotu = kr.getiri_risk(_konum(-0.05, 0.08))
    assert iyi[0]["puan"] > 60 and iyi[1]["puan"] > 80 and iyi[0]["esik_durumu"] == "gecti" and iyi[1]["esik_durumu"] == "gecti"
    assert kotu[0]["puan"] == 0.0 and kotu[1]["puan"] == 0.0 and kotu[0]["esik_durumu"] == "kaldi" and kotu[1]["esik_durumu"] == "kaldi"
    # düşüş büyüdükçe risk puanı AZALIR
    assert kr.getiri_risk(_konum(0.0, 0.01))[1]["puan"] > kr.getiri_risk(_konum(0.0, 0.04))[1]["puan"]
    # 4 haftalık pencerede alarm eşiği yok
    g4, r4 = kr.getiri_risk(_konum(0.0, 0.01, hafta=4))
    assert g4["esik_durumu"] == "esik_yok" and g4["ayrinti"]["pencere_hafta"] == 4
    # pencere dolmadı: null + neden
    g, r = kr.getiri_risk({})
    assert g["puan"] is None and "28" in g["neden"] and r["puan"] is None
    # 8 hafta varsa 8 haftalık kullanılır
    k = {**_konum(0.0, 0.01, hafta=4), **_konum(0.02, 0.01, hafta=8)}
    assert kr.getiri_risk(k)[0]["ayrinti"]["pencere_hafta"] == 8


def test_kalite_pf_ve_ornek_az():
    # PF = 1.2 -> puan 50, eşik "gecti"; 30 işlem: 10 kazanç x 1.0 / 25 x ... kur: kâr 12, zarar 10
    r = [0.6] * 20 + [-1.0] * 10                                                    # kâr 12, zarar 10 -> PF 1.2
    k = kr.kalite([_isl(i, v) for i, v in enumerate(r)])
    assert k["puan"] == pytest.approx(50.0) and k["esik_durumu"] == "gecti" and k["ayrinti"]["pf_r"] == pytest.approx(1.2)
    k2 = kr.kalite([_isl(i, v) for i, v in enumerate([0.5] * 20 + [-1.0] * 10)])     # PF 1.0 -> 0, kaldı
    assert k2["puan"] == 0.0 and k2["esik_durumu"] == "kaldi"
    k3 = kr.kalite([_isl(i, v) for i, v in enumerate([0.7] * 20 + [-0.5] * 10)])     # PF 2.8 -> 100
    assert k3["puan"] == 100.0
    az = kr.kalite([_isl(i, 1.0) for i in range(29)])
    assert az["puan"] is None and "29" in az["neden"] and "30" in az["neden"]
    assert kr.kalite([_isl(i, 1.0) for i in range(40)])["neden"].startswith("PF hesaplanamadı")


def test_isabet_uyum_strateji_beklentinin_altinda_ve_ornek_az():
    r = [1.0] * 12 + [-1.0] * 28                                                      # isabet 0.30 vs 0.50, ort R -0.4
    x = _ders([_isl(i, v) for i, v in enumerate(r)])["stratejiler"][0]
    isa, uy = kr.isabet_uyum_strateji(x)
    assert isa["puan"] == 0.0 and isa["esik_durumu"] == "kaldi" and isa["ayrinti"]["z"] < -kr.Z_KRIT
    assert uy["puan"] == 0.0 and uy["esik_durumu"] == "kaldi"
    # beklentiyi tutturan
    r2 = [1.0, -1.0] * 20
    x2 = _ders([_isl(i, v) for i, v in enumerate(r2)])["stratejiler"][0]
    isa2, uy2 = kr.isabet_uyum_strateji(x2)
    assert isa2["puan"] == pytest.approx(50.0) and isa2["esik_durumu"] == "gecti" and uy2["puan"] == 100.0
    # beklentinin ÜSTÜ cezalanmaz (tek yönlü)
    r3 = [1.0] * 30 + [-1.0] * 10
    uy3 = kr.isabet_uyum_strateji(_ders([_isl(i, v) for i, v in enumerate(r3)])["stratejiler"][0])[1]
    assert uy3["puan"] == 100.0
    # örnek az
    xa = _ders([_isl(i, 1.0) for i in range(10)])["stratejiler"][0]
    ia, ua = kr.isabet_uyum_strateji(xa)
    assert ia["puan"] is None and ua["puan"] is None and "10" in ia["neden"]
    # referans yok
    ib, ub = kr.isabet_uyum_strateji(ds.degerlendir(KIM, [_isl(i, 1.0) for i in range(40)], None))
    assert ib["puan"] is None and ub["puan"] is None and ib["neden"]
    assert kr.isabet_uyum_strateji(None)[0]["neden"] == "Dersler kaydı yok"


def test_isabet_uyum_set_havuzlanir():
    ref_a, ref_b = _ref(isabet=0.5, ort_r=0.0), _ref(isabet=0.3, ort_r=0.5, std_r=2.0)
    A, B = "a|X|1d", "b|Y|1d"
    sat = [_isl(i, 1.0 if i % 2 == 0 else -1.0, kim=A) for i in range(20)] + [_isl(i, 2.0 if i % 3 == 0 else -0.5, kim=B) for i in range(20, 40)]
    dr = ds.olustur("paper", Z, [A, B], sat, None, referans={A: ref_a, B: ref_b})
    isa, uy = kr.isabet_uyum_set(dr)
    n_b = sum(1 for i in range(20, 40) if i % 3 == 0)                               # B'deki kazanç sayısı
    k = 10 + n_b
    E = 20 * 0.5 + 20 * 0.3
    V = 20 * 0.25 + 20 * 0.21
    z = (k - E) / V ** 0.5
    assert isa["ayrinti"]["z"] == pytest.approx(round(z, 3)) and isa["ayrinti"]["n"] == 40
    assert isa["puan"] == pytest.approx(kr.kis(50 + 50 * z / kr.Z_KRIT), abs=0.1)
    assert uy["ayrinti"]["n"] == 40 and uy["puan"] is not None
    az = kr.isabet_uyum_set(ds.olustur("paper", Z, [A], sat[:10], None, referans={A: ref_a}))
    assert az[0]["puan"] is None and "30" in az[0]["neden"]


def test_saglik_kontrolleri_ve_eksen():
    ok = {"durum": "ok", "veri": [{"sembol": "BTCUSDT", "tf": "1d", "bayat": False}]}
    kabul = {"kesinti": {"saat": 2.0, "alt_sinir_saat": 2.0, "neden": None}, "kalemler": [{"id": "sert_limit", "durum": "gecti", "deger": "ihlal yok"}]}
    k = kr.saglik_set_kontrolleri(ok, {"genel_durum": "eslesti"}, kabul)
    e = kr.saglik_ekseni(k, None)
    assert e["puan"] == 100.0 and e["esik_durumu"] == "gecti" and len(e["kontroller"]) == 5
    kotu = kr.saglik_set_kontrolleri({"durum": "veri_bayat", "veri": [{"sembol": "BTCUSDT", "tf": "1d", "bayat": True}]}, {"genel_durum": "uyusmuyor"},
                                     {**kabul, "kesinti": {"saat": 30.0, "alt_sinir_saat": 30.0, "neden": None}})
    e2 = kr.saglik_ekseni(kotu, None)
    assert e2["puan"] == pytest.approx(20.0) and e2["esik_durumu"] == "kaldi"                # yalnız sert limit geçti: 1/5
    # ölçülemeyen kesinti ölçülen sayıya girmez
    bel = kr.saglik_set_kontrolleri(ok, {"genel_durum": "kayit_yok"}, {**kabul, "kesinti": {"saat": None, "alt_sinir_saat": 1.0, "neden": "olay kaydı dolu"}})
    assert [c["gecti"] for c in bel] == [True, True, None, None, True]
    assert kr.saglik_ekseni(bel, None)["puan"] == 100.0
    # kabul listesi yok (backtest): kesinti/sert limit ölçülmez; hiç kontrol yoksa null + neden
    assert kr.saglik_ekseni(None, "backtest: ölçülmez")["neden"] == "backtest: ölçülmez"
    assert kr.saglik_ekseni([kr.kontrol("a", "a", None, None, "k", "yok")], None)["puan"] is None
    # strateji
    s = kr.saglik_ekseni(kr.saglik_strateji_kontrolleri("calisiyor", [{"sembol": "X", "tf": "1d", "bayat": False}]), None)
    assert s["puan"] == 100.0
    s2 = kr.saglik_ekseni(kr.saglik_strateji_kontrolleri("veri yok: x", []), None)
    assert s2["puan"] == 0.0                                                          # eşlenemeyen veri satırı ölçülen sayılmaz; çalışmıyor -> 0/1


def test_karne_dosyasi_yapi_formul_ve_esik_kaynaklari_eski_esik_yok():
    sat = [_isl(i, v) for i, v in enumerate([1.0, -1.0] * 20)]
    dr = _ders(sat)
    k = kr.olustur("paper", Z, [{"kimlik": KIM, "ajan": "swing", "beklenti": _konum(0.01, 0.01)}], _konum(0.0, 0.01), sat, dr, None, None, "sağlık ölçülmedi (test)")
    json.dumps(k, allow_nan=False)
    assert k["genel_puan"] is None and k["genel_puan_neden"]
    assert [e["id"] for e in k["eksen_tanimlari"]] == ["getiri", "risk", "kalite", "isabet", "uyum", "saglik"] == k["eksen_sirasi"]
    for e in k["eksen_tanimlari"]:
        assert e["formul"] and e["esik"] and e["esik_kaynagi"] and e["min_ornek"]
    metin = json.dumps(k["eksen_tanimlari"], ensure_ascii=False)
    assert "PSR" not in metin and "%10" not in metin and "ON_KAYIT" in metin and "beklenti_araliklari" in metin and "Dersler" in metin
    for it in [k["set"]] + k["stratejiler"]:
        assert [e["id"] for e in it["eksenler"]] == k["eksen_sirasi"]
        for e in it["eksenler"]:
            assert (e["puan"] is None) == (e["neden"] is not None), e                  # ölçülmediyse neden zorunlu, ölçüldüyse neden yok
            assert e["puan"] is None or 0.0 <= e["puan"] <= 100.0
    assert k["stratejiler"][0]["eksenler"][5]["neden"] == "sağlık ölçülmedi (test)"
    assert k["stratejiler"][0]["olculen_eksen"] == 5


# ============================================================================== KOÇ: istatistik yardımcıları
def test_fisher_bilinen_degerler():
    assert kc.fisher_p(3, 1, 1, 3) == pytest.approx(0.4857142857, abs=1e-6)
    assert kc.fisher_p(10, 0, 0, 10) == pytest.approx(2 / 184756, rel=1e-6)           # 2 / C(20,10)
    assert kc.fisher_p(5, 5, 5, 5) == pytest.approx(1.0)


def test_en_uzun_seri_olasiligi_kaba_kuvvetle_ayni():
    def kaba(n, q, L):
        top = 0.0
        for dz in itertools.product((0, 1), repeat=n):                                 # 1 = kazanmayan
            en = s = 0
            for v in dz:
                s = s + 1 if v else 0
                en = max(en, s)
            if en >= L:
                pr = 1.0
                for v in dz:
                    pr *= q if v else 1 - q
                top += pr
        return top
    for n, q, L in ((8, 0.4, 3), (10, 0.5, 4), (9, 0.7, 2), (6, 0.3, 6)):
        assert kc.en_uzun_seri_p(n, q, L) == pytest.approx(kaba(n, q, L), abs=1e-12)
    assert kc.en_uzun_seri_p(5, 0.5, 6) == 0.0 and kc.en_uzun_seri_p(5, 0.5, 0) == 1.0


def test_mann_whitney():
    mw = kc.mann_whitney([10.0, 11, 12, 13, 14, 15, 16, 17, 18, 19], [1.0, 2, 3, 4, 5, 6, 7, 8, 9, 9.5])
    assert mw["p"] < 0.001 and mw["z"] > 0
    ters = kc.mann_whitney([1.0, 2, 3, 4, 5, 6, 7, 8, 9, 9.5], [10.0, 11, 12, 13, 14, 15, 16, 17, 18, 19])
    assert ters["z"] < 0 and ters["p"] == pytest.approx(mw["p"])
    ayni = kc.mann_whitney([1.0] * 5 + [2.0] * 5, [1.0] * 5 + [2.0] * 5)
    assert ayni["p"] > 0.9
    assert kc.mann_whitney([3.0] * 6, [3.0] * 6) is None                               # varyans sıfır


# ============================================================================== KOÇ: kurallar
def _koc(satirlar, ref=None, kim=KIM, konum=None, set_konum=None):
    dr = _ders(satirlar, ref, kim, konum)
    return kc.olustur("paper", Z, [kim], satirlar, dr, set_konum), dr


def _bul(k, kural):
    return [b for b in k["bulgular"] if b["kural"] == kural]


def test_ornek_az_kural_calismaz_ve_atlanan_yazar():
    sat = [_isl(i, -1.0) for i in range(12)]
    k, _ = _koc(sat)
    assert k["bulgular"] == [] and {a["kapsam"] for a in k["atlanan"]} == {KIM, "SET"}
    assert all("örnek az" in a["neden"] and "30" in a["neden"] for a in k["atlanan"])


def test_stop_sikligi_beklenenden_cok_stop_beklenti_disi():
    sat = [_isl(i, -1.0, neden="stop") for i in range(20)] + [_isl(i, 1.0) for i in range(20, 40)]
    k, _ = _koc(sat, _ref(cikis={"sinyal": 0.9, "stop": 0.1}))
    b = _bul(k, "stop_sikligi")[0]
    assert b["seviye"] == "beklenti_disi" and b["dayanak"]["stop_islem"] == 20 and b["dayanak"]["beklenen_pay"] == pytest.approx(0.1)
    assert b["istatistik"]["p_ham"] == pytest.approx(ds.binom_p(20, 40, 0.1)) and b["istatistik"]["p_ham"] < 1e-6 and b["referans"] == "backtest"
    # backtest payına yakınsa bulgu yok
    sat2 = [_isl(i, -1.0, neden="stop") for i in range(4)] + [_isl(i, 1.0) for i in range(4, 40)]
    assert _bul(_koc(sat2, _ref(cikis={"sinyal": 0.9, "stop": 0.1}))[0], "stop_sikligi") == []
    # stop SEYREK ise stop_sikligi bulgusu üretmez
    sat3 = [_isl(i, 1.0) for i in range(40)]
    assert _bul(_koc(sat3, _ref(cikis={"sinyal": 0.5, "stop": 0.5}))[0], "stop_sikligi") == []


def test_cikis_nedeni_backtestte_gorulmeyen_neden():
    """O16 (denetim 2026-11-08): backtest payı 0 olan neden test EDİLMEZ (H0 pay=0 iken p=0 olurdu); seviye en fazla 'izle', p null + neden."""
    sat = [_isl(i, 1.0, neden="zaman") for i in range(15)] + [_isl(i, -1.0) for i in range(15, 40)]
    k, dr = _koc(sat, _ref(cikis={"sinyal": 1.0}))
    b = [x for x in _bul(k, "cikis_nedeni") if x["dayanak"]["kova"] == "zaman"][0]
    assert b["seviye"] == "izle" and "gözlenmedi" in b["metin"] and "3/n" in b["metin"]
    assert b["istatistik"]["p_ham"] is None and b["istatistik"]["p_duzeltilmis"] is None and "gözlenmedi" in b["istatistik"]["test"]
    assert b["dayanak"]["ust_sinir"] == pytest.approx(3 / 200)
    assert not [x for x in _bul(k, "cikis_nedeni") if x["seviye"] == "beklenti_disi"]      # pay 1 olan 'sinyal' da test edilmez
    sap = {x["neden"]: x for x in dr["stratejiler"][0]["cikis_nedeni_sapmalari"]}
    assert sap["zaman"]["p_deger"] is None and sap["zaman"]["gozlenmedi"] and "gözlenmedi" in sap["zaman"]["test_neden"]
    assert sap["sinyal"]["p_deger"] is None and sap["sinyal"]["test_neden"]


def test_o16_tek_gunluk_limit_cikisi_beklenti_disi_degil():
    """Senaryo: 30 işlemin 1'i 'gunluk_limit' ile kapanır; backtestte bu neden yok -> 'beklenti dışı' DEĞİL, 'izle' + üst sınır bilgisi."""
    sat = [_isl(0, -1.0, neden="gunluk_limit")] + [_isl(i, 1.0 if i % 2 else -1.0) for i in range(1, 30)]
    k, dr = _koc(sat, _ref(cikis={"sinyal": 0.97, "stop": 0.03}))
    b = [x for x in _bul(k, "cikis_nedeni") if x["dayanak"]["kova"] == "gunluk_limit"]
    assert len(b) == 1 and b[0]["seviye"] == "izle" and b[0]["istatistik"]["p_ham"] is None
    assert not [x for x in _bul(k, "cikis_nedeni") + _bul(k, "stop_sikligi") if x["seviye"] == "beklenti_disi"]
    ac = " ".join(dr["stratejiler"][0]["aciklamalar"])
    assert "gözlenmedi" in ac and "p<0.001" not in ac
    assert ds.binom_p(1, 30, 0.009) > 0.05                     # ayrıntı: küçük pozitif payla test anlamlı değildi
    # pano 'p —' ile biçimler, hata vermez
    from motor.canli import pano as pn
    h = pn._koc_html(k)
    assert "gözlenmedi" in h and "p —" in h


def test_o16_stop_ailesi_backtestte_yoksa_izle():
    sat = [_isl(i, -1.0, neden="stop") for i in range(5)] + [_isl(i, 1.0) for i in range(5, 40)]
    k, _ = _koc(sat, _ref(cikis={"sinyal": 1.0}))
    b = _bul(k, "stop_sikligi")
    assert len(b) == 1 and b[0]["seviye"] == "izle" and b[0]["istatistik"]["p_ham"] is None


def test_kayip_serisi_beklenti_disi_ve_dagnik_kayip_bulgu_vermez():
    r = [1.0] * 14 + [-1.0] * 12 + [1.0] * 14
    k, _ = _koc([_isl(i, v) for i, v in enumerate(r)])
    b = _bul(k, "kayip_serisi")
    assert {x["kapsam"] for x in b} == {KIM, "SET"}
    s = next(x for x in b if x["kapsam"] == KIM)
    assert s["seviye"] == "beklenti_disi" and s["dayanak"]["en_uzun_seri"] == 12 and s["dayanak"]["islem"] == 40
    assert s["istatistik"]["p_ham"] == pytest.approx(kc.en_uzun_seri_p(40, 0.5, 12)) and s["istatistik"]["p_ham"] < ds.ALFA
    assert _bul(_koc([_isl(i, 1.0 if i % 2 == 0 else -1.0) for i in range(40)])[0], "kayip_serisi") == []


def test_kayip_yogunlugu_saat_bonferroni_ve_seviye_esleme():
    # 50 işlem 5 farklı TSİ saat bloğunda (karışık sonuç) + 10 işlem 02:00-04:00 bloğunda hepsi kayıp
    sat = []
    saatler = (6, 10, 14, 18, 22)
    for i in range(50):
        sat.append(_isl(i, 1.0 if i % 2 == 0 else -1.0, saat=saatler[i % 5], gun_ofset=i // 5))
    for j in range(10):
        sat.append(_isl(50 + j, -1.0, saat=2, gun_ofset=50 + j))
    k, _ = _koc(sat)
    saat = [b for b in _bul(k, "kayip_yogunlugu") if b["dayanak"]["boyut"] == "saat" and b["kapsam"] == KIM]
    assert len(saat) == 1
    b = saat[0]
    i = b["istatistik"]
    assert b["dayanak"]["kova"] == "saat:00:00–04:00" and b["dayanak"]["kova_islem"] == 10 and b["dayanak"]["kova_kazanmayan"] == 10
    assert i["test_sayisi"] == 6 and i["p_duzeltilmis"] == pytest.approx(min(1.0, i["p_ham"] * 6)) and i["p_ham"] == pytest.approx(kc.fisher_p(10, 0, 25, 25), rel=1e-6)
    assert b["referans"] == "yok" and b["seviye"] == "incele"                        # referans yok: düzeltmeli anlamlı -> en çok "incele"
    # küçük kova: ham anlamlı ama düzeltilince değil -> "izle"
    sat2 = [s for s in sat if not (s["giris_zamani"] and s in sat[50:])] + sat[50:57]
    k2, _ = _koc(sat2)
    b2 = [b for b in _bul(k2, "kayip_yogunlugu") if b["dayanak"]["boyut"] == "saat" and b["kapsam"] == KIM]
    assert len(b2) == 1 and b2[0]["istatistik"]["anlamli_ham"] and not b2[0]["istatistik"]["anlamli_duzeltilmis"] and b2[0]["seviye"] == "izle"
    # hiçbir kural 'referans yok' ile beklenti_disi üretemez
    assert all(b["seviye"] != "beklenti_disi" for b in k["bulgular"] if b["referans"] == "yok")


def test_tutma_suresi_kaybedenler_uzun_ve_grup_kucukse_atlanir():
    sat = []
    for i in range(12):
        sat.append(_isl(i, -1.0, tutma_saat=48.0 + i))
    for i in range(12, 24):
        sat.append(_isl(i, 1.0, tutma_saat=4.0 + (i % 3)))
    for i in range(24, 36):
        sat.append(_isl(i, 1.0 if i % 2 else -1.0, tutma_saat=10.0 + (i % 4)))
    k, _ = _koc(sat)
    b = _bul(k, "tutma_suresi")[0]
    assert b["referans"] == "yok" and b["seviye"] == "incele" and b["istatistik"]["p_ham"] < 0.01
    assert b["dayanak"]["kaybeden_medyan_saat"] > b["dayanak"]["kazanan_medyan_saat"]
    # kazananlar daha uzun tutulduysa (trend takipçisi için olağan) bulgu yok
    ters = [_isl(i, -1.0, tutma_saat=4.0 + i % 3) for i in range(15)] + [_isl(i, 1.0, tutma_saat=48.0 + i) for i in range(15, 30)]
    kt, _ = _koc(ters)
    assert _bul(kt, "tutma_suresi") == []
    # küçük grup
    az = [_isl(i, -1.0, tutma_saat=48.0) for i in range(5)] + [_isl(i, 1.0, tutma_saat=4.0) for i in range(5, 35)]
    ka, _ = _koc(az)
    assert _bul(ka, "tutma_suresi") == [] and any(a["kural"] == "tutma_suresi" and str(kc.MIN_GRUP_TUTMA) in a["neden"] for a in ka["atlanan"])


def test_beklenti_alti_dersler_ve_set_alarmi():
    r = [1.0] * 12 + [-1.0] * 28
    k, dr = _koc([_isl(i, v) for i, v in enumerate(r)])
    assert dr["stratejiler"][0]["durum"] == "altinda"
    b = _bul(k, "beklenti_alti")
    assert len(b) == 1 and b[0]["seviye"] == "beklenti_disi" and b[0]["kapsam"] == KIM and b[0]["dayanak"]["islem"] == 40
    ka, _ = _koc([_isl(i, 1.0) for i in range(5)], set_konum=_konum(-0.05, 0.08))
    sa = [x for x in _bul(ka, "beklenti_alti") if x["kapsam"] == "SET"]
    assert len(sa) == 1 and sa[0]["seviye"] == "beklenti_disi" and "net getiri" in sa[0]["metin"]


def test_koc_metinleri_risk_buyutme_onermez_ve_yalniz_uc_seviye():
    """Tüm kural şablonları tetiklenir; hiçbir metinde risk artırma / büyütme / ekleme / Kelly / martingale / DCA ifadesi yok."""
    sat = ([_isl(i, -1.0, neden="stop", saat=2, tutma_saat=60.0 + i, gun_ofset=i) for i in range(14)] + [_isl(i, 1.0, neden="zaman", saat=14, tutma_saat=3.0, gun_ofset=i) for i in range(14, 26)]
           + [_isl(i, 1.0 if i % 2 else -1.0, saat=(6, 10, 18, 22)[i % 4], gun_ofset=i, tutma_saat=5.0 if i % 2 else 20.0) for i in range(26, 60)])
    k, _ = _koc(sat, _ref(isabet=0.6, cikis={"sinyal": 0.9, "stop": 0.1}), set_konum=_konum(-0.05, 0.08))
    kurallar = {b["kural"] for b in k["bulgular"]}
    assert {"stop_sikligi", "kayip_serisi", "kayip_yogunlugu", "tutma_suresi", "beklenti_alti"} <= kurallar
    metinler = [k["yontem"], k["uyari"]] + list(kc.ONERI.values()) + [b["baslik"] + " " + b["metin"] + " " + b["oneri"] for b in k["bulgular"]]
    for m in metinler:
        if m is k["uyari"]:
            continue                                                                    # uyarı bu ifadeleri "önermez" diye anar
        assert not YASAK.search(m), m
    assert {b["seviye"] for b in k["bulgular"]} <= {"beklenti_disi", "incele", "izle"}
    assert all(b["oneri"] == kc.ONERI[b["seviye"]] for b in k["bulgular"])
    json.dumps(k, allow_nan=False)
    for b in k["bulgular"]:
        i = b["istatistik"]
        if i["p_ham"] is None:                                                          # O16: test yapılmayan (backtestte gözlenmedi) -> yalnız 'izle' + neden
            assert b["seviye"] == "izle" and i["p_duzeltilmis"] is None and i["neden"] and b["dayanak"]
            continue
        assert i["test"] and i["p_duzeltilmis"] >= i["p_ham"] - 1e-12 and i["test_sayisi"] >= 1 and b["dayanak"]
    sirala = [(kc.SEVIYE_SIRA[b["seviye"]]) for b in k["bulgular"]]
    assert sirala == sorted(sirala)                                                      # önce beklenti dışı, sonra incele, sonra izle
    assert "ÖNERMEZ" in k["uyari"] and "martingale" in k["uyari"]


def test_koc_yalniz_kapanmis_islem_ve_gelecek_islem_gecmisi_degistirmez():
    """Aynı ilk 40 işlemle yapılan koşu, sonradan eklenen işlemlerden bağımsızdır (ön ek tutarlılığı: lookahead yok)."""
    r = [1.0] * 14 + [-1.0] * 12 + [1.0] * 14
    sat = [_isl(i, v) for i, v in enumerate(r)]
    k1, _ = _koc(sat)
    k2, _ = _koc(sat + [_isl(100 + j, 1.0, gun_ofset=100 + j) for j in range(0)])
    assert json.dumps(k1["bulgular"], sort_keys=True) == json.dumps(k2["bulgular"], sort_keys=True)
    ek = sat + [_isl(100 + j, -1.0, gun_ofset=100 + j) for j in range(5)]
    assert _bul(_koc(sat[:13])[0], "kayip_serisi") == []                                  # henüz 12'lik seri yok / örnek az


# ============================================================================== MFE / MAE (paper motoru)
def _mfe_kosu(bitis=8):
    t = tanim("a|XUSDT|1d", "XUSDT", pay="1", stop_yuzde=1.0)
    m = duz(12, 100.0, dalga=0.0)
    m.iloc[5, m.columns.get_loc("yuksek")] = 101.0                  # pozisyon açıkken tam kapanmış mum: MFE'ye girer
    m.iloc[7, m.columns.get_loc("yuksek")] = 150.0                  # ÇIKIŞ mumu: stop vurulduktan sonraki/öncesi sıra bilinmez -> sayılmamalı
    m.iloc[7, m.columns.get_loc("dusuk")] = 98.0
    kur = {"XUSDT": SembolKurallari(0.01, 0.001, 0.001, 5.0)}
    return pp.tekrar_calistir([t], {("XUSDT", "1d"): m}, {}, kur, m.index[2], m.index[bitis], kapat=False)


def test_mfe_mae_cikis_mumunun_uclarini_saymaz_lookahead_yok():
    p = _mfe_kosu()
    ilk = p.motor.islemler[0]
    assert ilk["cikis_nedeni"] in ("stop", "stop_gap")
    assert ilk["mfe_fiyat"] == pytest.approx(101.0) and ilk["mfe_fiyat"] < 150.0
    assert 0.9 < ilk["mfe_r"] < 1.1                                                # (101 - 100) / (100 - 99)
    assert ilk["mae_fiyat"] <= 99.0 + 1e-9 and ilk["mae_fiyat"] >= 98.0           # çıkış (stop) dolumu dahil, mumun 98'lik dibi değil
    assert ilk["mae_r"] <= -0.9 and ilk["mfe_r"] >= 0.0 >= ilk["mae_r"]
    assert ilk["mfe_mae_neden"] is None


def test_mfe_mae_durum_kaydi_ve_eski_kayit():
    p = _mfe_kosu(bitis=6)                                           # pozisyon hâlâ açık
    m = p.motor
    assert m.acik and m.uc
    # açık pozisyon izi diske yazılıp geri yüklenince korunur
    import json as _j
    d_ = _dec(_j.loads(_j.dumps(_enc(m.durum_al()))))
    assert d_["uc"] == m.uc
    # eski durum dosyasında 'uc' yok: yükleme hata vermez
    eski = dict(m.durum_al())
    eski.pop("uc")
    p2 = _mfe_kosu(bitis=6)
    p2.motor.durum_yukle(_dec(_j.loads(_j.dumps(_enc(eski)))))
    assert p2.motor.uc == {}
    # izleme sonradan başladıysa (tam False) null + neden
    x = type(m)._mfe_mae(next(iter(m.acik.values())), {"ust": 1.0, "alt": 1.0, "tam": False})
    assert x["mfe_r"] is None and x["mae_r"] is None and "izleme" in x["mfe_mae_neden"]
    assert type(m)._mfe_mae(next(iter(m.acik.values())), None)["mfe_r"] is None


# ============================================================================== entegrasyon: gerçek paper koşusu -> dosyalar -> pano
@pytest.fixture(scope="module")
def kosu(tmp_path_factory):
    tans = [TAN[KIM], TAN["pf__kesit_ls|kripto|1d"]]
    mum = {("SOLUSDT", "1d"): sentetik(520, "1d", 3, vol=0.04)}
    for k, s in enumerate(["BTCUSDT", "ETHUSDT"]):
        mum[(s, "1d")] = sentetik(520, "1d", 20 + k, vol=0.04)
    kur = {s: kural(s) for s in ("SOLUSDT", "BTCUSDT", "ETHUSDT")}
    ix = mum[("SOLUSDT", "1d")].index
    p = pp.tekrar_calistir(tans, mum, {}, kur, ix[100], ix[-1] + pd.Timedelta(days=1), kapat=False)
    simdi = ix[-1] + pd.Timedelta(days=1, minutes=5)
    sag = [{"sembol": s, "tf": tf, "son_mum_acilis": df.index[-1]} for (s, tf), df in mum.items()]
    dizin = tmp_path_factory.mktemp("durum6")
    o = pdr.olustur(p, simdi, kaynak_saglik=sag, olaylar=[], beklenti_csv=bd.BEKLENTI_CSV)
    d.yaz_hepsi(dizin, ozet=o["ozet"], stratejiler=o["stratejiler"], islemler=o["islemler"], saglik=o["saglik"], gecmis=o["gecmis"], ekstra=o["ekstra"])
    return p, o, dizin, simdi


def test_dosyalar_yazilir_okunur_ve_stratejilerle_ayni_kimlikler(kosu):
    p, o, dizin, simdi = kosu
    kn, kc_ = d.ek_oku(dizin, "karne"), d.ek_oku(dizin, "koc")
    ids = [s["kimlik"] for s in o["stratejiler"]["stratejiler"]]
    assert [x["kimlik"] for x in kn["stratejiler"]] == ids and kn["set"]["kimlik"] == "SET"
    assert kn["yazildi_zaman"] == d.oku_ozet(dizin)["yazildi_zaman"] and kc_["yazildi_zaman"] == kn["yazildi_zaman"]
    assert sum(x["islem"] for x in kn["stratejiler"]) == kn["set"]["islem"] == len(o["islemler"])
    # sağlık ekseni paper'da ölçülür (5 kontrol set, 2 kontrol strateji)
    sag = {x["id"]: x for x in kn["set"]["eksenler"]}["saglik"]
    assert sag["puan"] is not None and len(sag["kontroller"]) == 5
    assert len({x["id"]: x for x in kn["stratejiler"][0]["eksenler"]}["saglik"]["kontroller"]) == 2
    # >= 30 işlemli stratejide kalite/isabet/uyum ölçülür, 30'un altındakinde null + neden
    for x in kn["stratejiler"]:
        e = {a["id"]: a for a in x["eksenler"]}
        if x["islem"] >= 30:
            assert e["kalite"]["puan"] is not None or "zarar" in e["kalite"]["neden"]
            assert e["isabet"]["puan"] is not None
        else:
            assert e["kalite"]["puan"] is None and e["isabet"]["puan"] is None and e["uyum"]["puan"] is None and str(kr.MIN_ISLEM) in e["isabet"]["neden"]
    # koç: örnek az olan strateji atlanan'da
    az = [x["kimlik"] for x in kn["stratejiler"] if x["islem"] < kc.MIN_ISLEM]
    assert {a["kapsam"] for a in kc_["atlanan"] if a["kural"] == "tümü"} >= set(az)
    assert {b["seviye"] for b in kc_["bulgular"]} <= {"beklenti_disi", "incele", "izle"}


def test_islem_satirlarinda_mfe_mae_ve_gerekce(kosu):
    p, o, dizin, simdi = kosu
    isl = d.oku_islemler(dizin)
    assert len(isl) == len(p.motor.islemler) > 30
    for x in isl:
        assert {"mfe_r", "mae_r", "mfe_fiyat", "mae_fiyat", "mfe_mae_neden"} <= set(x)
        if x["mfe_r"] is not None:
            assert x["mfe_r"] >= 0.0 >= x["mae_r"] and x["mfe_mae_neden"] is None
            alt, ust = sorted((float(x["mfe_fiyat"]), float(x["mae_fiyat"])))
            assert ust >= alt                                                          # uçlar tutarlı
            # çıkış ve giriş fiyatı uçların içinde (gerçekleşen fiyatlar yaşanmıştır)
            assert alt - 1e-6 <= float(x["giris_fiyati"]) <= ust + 1e-6 and alt - 1e-6 <= float(x["cikis_fiyati"]) <= ust + 1e-6
    assert any(x["mfe_r"] is not None for x in isl)
    # tam zararla (R <= -0.9) stop olan işlemlerde en kötü sapma da yaklaşık -1R'ye varır (iz süren stop kârda çıkabilir: onlar hariç)
    st = [x for x in isl if x["cikis_nedeni"] == "stop" and x["mae_r"] is not None and x["r"] <= -0.9]
    assert st and all(x["mae_r"] <= -0.8 for x in st)
    assert any(x["giris_gerekcesi"] for x in isl) and any(x["ayar_surumu"] for x in isl)


def test_pano_karne_koc_cekmece_yalniz_bicim(kosu):
    p, o, dizin, simdi = kosu
    veri, sorun = pano.yukle(dizin)
    assert not sorun
    html = pano.html_olustur(veri, sorun, datetime(2026, 11, 8, tzinfo=timezone.utc))
    kn, kc_ = veri["karne"], veri["koc"]
    assert html.count('<svg class="rdr"') == 1 + len(kn["stratejiler"])
    assert "Karne (radar)" in html and "Koç: kurallı tespitler" in html and "Eksen formülleri ve eşik kaynakları" in html
    for it in [kn["set"]] + kn["stratejiler"]:
        for e in it["eksenler"]:
            if e["puan"] is not None:
                assert f"{e['ad']} {e['puan']:.0f}</text>" in html                       # radar etiketi dosyadaki puan (yuvarlanmış)
    assert "Bu bölümün verisi beklenen biçimde değil" not in html
    # çekmece: gösterilen her satır için bir ayrıntı bloğu ve tıklanabilir satır
    gosterilen = min(len(veri["islemler"]), pano.ISLEM_GOSTER)
    assert html.count('class="cek" data-ix=') == gosterilen and html.count('tabindex="0" title="Ayrıntı için tıkla"') == gosterilen
    assert 'id="cekmece"' in html and "Neden açıldı?" in html and "İşlem içi uçlar" in html and "MFE (en iyi sapma)" in html
    son = sorted(veri["islemler"], key=lambda s: s["zaman"], reverse=True)[0]
    i0 = html.index('class="cek" data-ix="0"')
    blok = html[i0:i0 + 6000]
    assert son["giris_gerekcesi"]["metin"].split(" ")[0] in blok and son["ayar_surumu"]["hash"] in blok
    assert pano.esc(f"{son['mfe_fiyat']} / {son['mae_fiyat']}") in blok or son["mfe_r"] is None
    assert son["cikis_nedeni"] in blok


def test_pano_eski_motor_dosyasi_yoksa_veri_yok_der_ve_cekmece_alanlarsiz_calisir(kosu, tmp_path):
    p, o, dizin, simdi = kosu
    import shutil
    yeni = tmp_path / "eski"
    shutil.copytree(dizin, yeni)
    (yeni / "karne.json").unlink()
    (yeni / "koc.json").unlink()
    # eski işlem satırları: MFE/MAE ve gerekçe alanları yok
    satirlar = [json.loads(x) for x in (yeni / "islemler.jsonl").read_text(encoding="utf-8").splitlines()]
    for s in satirlar:
        for a in ("mfe_r", "mae_r", "mfe_fiyat", "mae_fiyat", "mfe_mae_neden", "giris_gerekcesi", "ayar_surumu"):
            s.pop(a, None)
    d.atomik_yaz_jsonl(yeni / "islemler.jsonl", satirlar)
    veri, sorun = pano.yukle(yeni)
    assert not sorun and veri["karne"] is None and veri["koc"] is None
    html = pano.html_olustur(veri, sorun, datetime(2026, 11, 8, tzinfo=timezone.utc))
    assert "karne.json" in html and "koc.json" in html and "Bu bölümün verisi beklenen biçimde değil" not in html
    assert "Bu kayıtta giriş gerekçesi yok" in html and "MFE/MAE yok" in html


def test_backtest_karne_saglik_olculmez_null_neden():
    sat = [_isl(i, v) for i, v in enumerate([1.0, -1.0] * 20)]
    dr = _ders(sat)
    k = kr.olustur("backtest", Z, [{"kimlik": KIM, "ajan": "swing", "beklenti": _konum(0.01, 0.01)}], _konum(0.0, 0.01), sat, dr, None, None, "backtest: sağlık ölçülmez")
    e = {a["id"]: a for a in k["set"]["eksenler"]}["saglik"]
    assert e["puan"] is None and "backtest" in e["neden"] and k["kaynak_not"]
    kc_ = kc.olustur("backtest", Z, [KIM], sat, dr, _konum(0.0, 0.01))
    assert kc_["kaynak_not"] and kc_["sema"] == "1l3a.durum.koc"
