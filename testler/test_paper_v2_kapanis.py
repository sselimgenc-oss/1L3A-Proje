"""Paper v2 seti: kapanış turu paper adayları (6 kayıt, 16 hesap; kullanıcı onayı 2026-11-14). Sentetik veri; ağ/gerçek veri yok.
Kapsam: set yükleme + dondurulmuş liste doğrulaması, imza, mevcut 10'un DEĞİŞMEDİĞİ, fail-closed, azalan ROI / geri çekilme çıkışının
backtest ile eşdeğerliği, 10 -> 16 hesap geçişi (mevcut durum korunur, yeni hesaplar sıfırdan)."""
import copy
import json
import shutil
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import tarama
from motor.canli import paper as pp
from motor.canli import paper_esleme as es
from motor.canli import paper_motor as pm
from motor.canli import paper_v2 as v2
from motor.canli import paper_veri as pv
from motor.canli.paper_motor import PaperDesteklemiyorHatasi
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.temel import Strateji
from testler.test_paper_v2 import OrtalamaTrend, SEM, islem_ozeti, kos, sentetik, set_, tanim, veri

KOK = Path(__file__).resolve().parents[1]
ESKI_IMZA = "985f914d0bb6b643"                      # 2026-11-10'daki 10'lu setin imzası (sunucudaki mevcut durum dosyasında yazılı)
KAPANIS_KIMLIKLER = ["HAM:X005:664#v1", "HAM:X005:705", "HAM:X005:301#v1", "HAM:X005:138#v3", "HAM:B001:670#v1", "HAM:B001:574#v1"]


# ---------------------------------------------------------------------------- set yükleme + doğrulama
def test_set_16_kayit_6_kapanis_etiketli():
    s = v2.set_yukle()
    assert len(s["stratejiler"]) == 16 and "kapanis_aday" in s["etiketler"]
    kap = [k for k in s["stratejiler"] if v2.kapanis_mi(k)]
    assert [k["kimlik"] for k in kap] == KAPANIS_KIMLIKLER
    assert all(k["etiket"] == "kapanis_aday" and k["evren"] == "kripto13" and k["tur"] == "tek" for k in kap)
    assert [(k["tf"], k["liste"]) for k in kap] == [("1d", "kosu_listesi_asama1.csv")] * 2 + [("4h", "kosu_listesi_asama1.csv"),
                                                                                              ("1d", "kosu_listesi_asama1.csv"),
                                                                                              ("5m", "kosu_listesi_asama2.csv"),
                                                                                              ("5m", "kosu_listesi_asama2.csv")]
    assert not any(v2.kapanis_mi(k) for k in s["stratejiler"][:10])


def _kopya_dizin(tmp_path) -> Path:
    d = tmp_path / "kapanis"
    d.mkdir()
    for a in ("kosu_listesi_asama1.csv", "kosu_listesi_asama2.csv"):
        shutil.copy(KOK / "sonuclar/kapanis" / a, d / a)
        shutil.copy(KOK / "sonuclar/kapanis" / (a + ".sha256"), d / (a + ".sha256"))
    return d


def test_kapanis_dogrulama_sha_kimlik_tf_etiket_acik_hata(tmp_path):
    s = v2.set_yukle()
    d = _kopya_dizin(tmp_path)
    yol = tmp_path / "set.json"
    yol.write_text(json.dumps(s))
    assert v2.set_yukle(yol, kapanis_dizin=d)["ad"] == v2.SET_ADI                          # temiz kopya geçer
    # SHA tutmuyor (liste dondurulduktan sonra değiştirilmiş)
    (d / "kosu_listesi_asama2.csv").write_text((d / "kosu_listesi_asama2.csv").read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(v2.PaperV2Hatasi, match="doğrulanamadı"):
        v2.set_yukle(yol, kapanis_dizin=d)
    # kimlik listede yok
    s2 = copy.deepcopy(s)
    s2["stratejiler"][10]["kimlik"] = "HAM:X005:99999"
    yol.write_text(json.dumps(s2))
    with pytest.raises(v2.PaperV2Hatasi, match="içinde yok"):
        v2.set_yukle(yol)
    # tf uyuşmuyor
    s3 = copy.deepcopy(s)
    s3["stratejiler"][10]["tf"] = "4h"
    yol.write_text(json.dumps(s3))
    with pytest.raises(v2.PaperV2Hatasi, match="uyuşmuyor"):
        v2.set_yukle(yol)
    # yanlış etiket / etiketin havuz kaydına verilmesi
    s4 = copy.deepcopy(s)
    s4["stratejiler"][10]["etiket"] = "iyi_gorundu"
    yol.write_text(json.dumps(s4))
    with pytest.raises(v2.PaperV2Hatasi, match="kapanis_aday"):
        v2.set_yukle(yol)
    s5 = copy.deepcopy(s)
    s5["stratejiler"][0]["etiket"] = "kapanis_aday"
    yol.write_text(json.dumps(s5))
    with pytest.raises(v2.PaperV2Hatasi, match="yalnız kapanış kaydına"):
        v2.set_yukle(yol)
    # izin verilmeyen liste
    s6 = copy.deepcopy(s)
    s6["stratejiler"][10]["liste"] = "baska.csv"
    yol.write_text(json.dumps(s6))
    with pytest.raises(v2.PaperV2Hatasi, match="zorunlu"):
        v2.set_yukle(yol)


# ---------------------------------------------------------------------------- imza ve mevcut 10'un değişmediği
def test_imza_degisti_onceki_imza_eski_10lu_ile_ayni():
    s = v2.set_yukle()
    assert v2.set_imzasi(s) != ESKI_IMZA
    assert v2.onceki_set_imzasi(s) == ESKI_IMZA                       # kapanış kayıtları çıkarılınca imza, sunucudaki kayıtlı imzayla BİREBİR aynı
    assert len(v2.onceki_set(s)["stratejiler"]) == 10


def test_mevcut_10_hesabin_tanimlari_degismedi():
    s = v2.set_yukle()
    tum = v2.tanimlari_yukle(s)
    eski = v2.tanimlari_yukle(v2.onceki_set(s))
    assert len(tum) == 16 and len(eski) == 10
    for a, b in zip(tum[:10], eski):
        assert (a.kimlik, a.kol, a.tf, tuple(a.evren), a.etiket, a.ayar, a.grup_payi, a.ajan) == (b.kimlik, b.kol, b.tf, tuple(b.evren), b.etiket, b.ayar, b.grup_payi, b.ajan)
        assert type(a.nesne) is type(b.nesne) and getattr(a.nesne, "parametreler", None) == getattr(b.nesne, "parametreler", None)
        assert getattr(a.nesne, "cikis_ayarlari", None) == getattr(b.nesne, "cikis_ayarlari", None)
        assert v2.hesap_ayarlari(a, s) == v2.hesap_ayarlari(b, v2.onceki_set(s))
    assert [t.kimlik for t in tum[10:]] == KAPANIS_KIMLIKLER


def test_16_hesap_kapanis_tanimlari_listeden_ayni_kasa_ayni_s():
    import csv
    s = v2.set_yukle()
    tans = {t.kimlik: t for t in v2.tanimlari_yukle(s)}
    from motor.arastirma.v2 import sabit
    satirlar = {}
    for a in ("kosu_listesi_asama1.csv", "kosu_listesi_asama2.csv"):
        with open(KOK / "sonuclar/kapanis" / a, newline="", encoding="utf-8") as f:
            satirlar.update({r["kimlik"]: r for r in csv.DictReader(f)})
    for k in KAPANIS_KIMLIKLER:
        t, r = tans[k], satirlar[k]
        assert t.kol == "tek_evren" and t.tf == r["tf"] and t.etiket == "kapanis_aday" and t.grup_payi == Decimal(1)
        assert tuple(t.evren) == sabit.evren_listesi("kripto") and len(t.evren) == 13
        par = json.loads(r["parametreler"])
        assert all(getattr(t.nesne, "parametreler", {}).get(a, v) == v for a, v in par.items() if a != "cikis_ayarlari")
        ay = v2.hesap_ayarlari(t, s)
        assert ay.baslangic_sermaye == 10000 and ay.risk_yuzde == 0.5 and ay.limit_modu == "uygula"
    assert len({t.kimlik for t in tans.values()}) == 16


# ---------------------------------------------------------------------------- fail-closed + hangi çıkış alanları
def test_kapanis_stratejilerinin_cikis_alanlari_ve_destek():
    """4 X005 kaydı varsayılan çıkış ayarlı; iki NASOS (5m) azalan_roi + geri çekilme kullanır (paper motoru artık uygular). Kanca yok."""
    import dataclasses
    tans = {t.kimlik: t for t in v2.tanimlari_yukle()}
    varsayilan = CikisAyarlari()
    for k in KAPANIS_KIMLIKLER:
        ca = tans[k].nesne.cikis_ayarlari
        fark = {f.name for f in dataclasses.fields(ca) if getattr(ca, f.name) != getattr(varsayilan, f.name)}
        assert fark <= {"azalan_roi", "geri_cekilme_yuzde", "geri_cekilme_min_kar_yuzde"}, (k, fark)
        assert (len(fark) == 3) == k.startswith("HAM:B001:"), (k, fark)
        assert getattr(tans[k].nesne, "pozisyon_cikisi", None) is None
        assert pm.desteklenmeyen_cikis_alanlari(ca) == []


def test_fail_closed_kapanis_stratejisi_desteklenmeyen_alan_ve_kanca_adiyla(monkeypatch):
    from araclar import kapanis_kosu_listesi as kl
    kotu = OrtalamaTrend(cikis_ayarlari=CikisAyarlari(zaman_cikisi_mum=1000, stop_basamaklari=((1.0, 0.0),)))
    gercek = kl.strateji_kur

    def sahte(sinif, modul, par):
        return (kotu, False) if sinif == "kapanis__wavetrend-s0664" else gercek(sinif, modul, par)
    monkeypatch.setattr(kl, "strateji_kur", sahte)
    with pytest.raises(PaperDesteklemiyorHatasi, match=r"BAŞLAMAZ.*HAM:X005:664#v1: stop_basamaklari"):
        v2.tanimlari_yukle()

    class Kancali(OrtalamaTrend):
        ad = "test__kancali"

        def pozisyon_cikisi(self, d):
            return False
    t = tanim("kancali|x", SEM, Kancali())
    with pytest.raises(PaperDesteklemiyorHatasi, match=r"kancali\|x: pozisyon_cikisi"):
        v2.fail_closed_kontrol([t])


# ---------------------------------------------------------------------------- azalan ROI / geri çekilme: paper = backtest
class RoiGeriCekilme(Strateji):
    """Her zaman long (sinyal çıkışı yok): çıkışı yalnız azalan ROI / geri çekilme / stop belirler. Test stratejisi."""
    ad = "test__roi_geri_cekilme"
    stil = "swing"
    varsayilan_parametreler = {"roi": 0, "gc": 0}

    def cikis_var_mi(self):
        return True                                                               # çıkış kuralı CikisAyarlari'nda (azalan ROI / geri çekilme)

    def sinyaller(self, mumlar):
        c = mumlar["kapanis"]
        ma = c.rolling(5).mean()
        giris = ((c > ma) & (c.shift(1) <= ma.shift(1))).astype(int)               # yukarı kesişimde giriş
        return pd.DataFrame({"yon": giris, "stop": c * 0.93, "hedef": np.nan, "cikis": False}, index=mumlar.index)


def _roi_tan(ca):
    return psg_tek_grafik(None, RoiGeriCekilme(cikis_ayarlari=ca))


@pytest.mark.parametrize("ca,neden", [
    (CikisAyarlari(azalan_roi=((0, 6.0), (3, 3.0), (6, 0.0))), "roi"),
    (CikisAyarlari(geri_cekilme_yuzde=2.0, geri_cekilme_min_kar_yuzde=3.0), "geri_cekilme"),
    (CikisAyarlari(azalan_roi=((0, 12.0), (8, 1.0)), geri_cekilme_yuzde=1.5, geri_cekilme_min_kar_yuzde=2.0), None),
])
def test_azalan_roi_ve_geri_cekilme_paper_backtest_ile_ayni_islemler(ca, neden):
    toplam = 0
    nedenler = set()
    for seed in (3, 4, 5):
        t = _roi_tan(ca)
        m = sentetik(500, seed=seed, p0=100.0, vol=0.03)
        r = es.tek_esle(t, m, None, {"BTCUSDT": tarama.VARSAYILAN_KURAL}, m.index[250])
        assert r["n_backtest"] == r["n_paper"], r["farklar"][:3]
        assert r["tam_esit_zaman_haric"], r["farklar"][:3]
        assert r["max_mutlak_fark"] <= 1e-9
        toplam += r["n_backtest"]
        p = pp.tekrar_calistir([es.izole(t)], {("BTCUSDT", "1d"): m}, {}, {"BTCUSDT": tarama.VARSAYILAN_KURAL}, m.index[250], None, None, None,
                               tetikleyen_hemen_kapat=False)
        nedenler |= {x["cikis_nedeni"] for x in p.motor.islemler}
    assert toplam >= 6
    if neden:
        assert neden in nedenler, nedenler                          # çıkış gerçekten bu kuraldan geldi (stop/veri sonu değil)
    else:
        assert nedenler & {"roi", "geri_cekilme"}


def test_cikis_ayari_bos_stratejide_ek_kod_hicbir_sey_yapmaz():
    """Varsayılan çıkış ayarı: ek _karar_sinyal dalı çalışmaz -> mevcut stratejilerin işlemleri aynı kalır (kasalar tek_evren = tek_grafik testi de geçer)."""
    t = _roi_tan(CikisAyarlari())
    m = sentetik(500, seed=3, p0=100.0, vol=0.03)
    r = es.tek_esle(t, m, None, {"BTCUSDT": tarama.VARSAYILAN_KURAL}, m.index[250])
    assert r["n_backtest"] == r["n_paper"] and r["tam_esit_zaman_haric"]


def test_tek_evren_kasa_roi_stratejisinde_tek_grafik_ile_ayni():
    ca = CikisAyarlari(azalan_roi=((0, 6.0), (3, 3.0), (6, 0.0)), geri_cekilme_yuzde=2.0, geri_cekilme_min_kar_yuzde=3.0)
    nesne = RoiGeriCekilme(cikis_ayarlari=ca)
    mum = {("BTCUSDT", "1d"): sentetik(300, seed=3, p0=100.0, vol=0.03)}
    ix = mum[("BTCUSDT", "1d")].index
    t = tanim("a", ["BTCUSDT"], nesne)
    kurallar = v2.kurallar_tekrar([t])
    ay = v2.hesap_ayarlari(t, set_("a"))
    eski = es.izole(psg_tek_grafik(t, nesne))
    pe = pp.tekrar_calistir([eski], mum, {}, kurallar, ix[120], ix[-1] + pd.Timedelta(days=1), ay, {"1d": 300})
    h = kos([t], mum).hesaplar["a"]
    assert len(pe.motor.islemler) >= 3
    assert [(str(x["giris_zamani"]), str(x["cikis_zamani"]), x["miktar"], x["net_pnl"], x["cikis_nedeni"]) for x in pe.motor.islemler] == \
           [(str(x["giris_zamani"]), str(x["cikis_zamani"]), x["miktar"], x["net_pnl"], x["cikis_nedeni"]) for x in h.motor.islemler]


def psg_tek_grafik(t, nesne):
    from motor.canli import paper_sinyal as psg
    return psg.StratejiTanim("a|BTCUSDT|1d", "swing", "tek_grafik", nesne.ad, "BTCUSDT", "1d", "varsayilan", nesne, "g", Decimal(1))


def _cokus_mumu(n, seed, vol=0.002, aralik=350):
    """5m sentetik: düz yürüyüş + periyodik çöküş (20 mumda ~ -%27) ve toparlanma (NASOS dip-alım stratejileri yalnız böyle girer)."""
    rng = np.random.default_rng(seed)
    r = rng.normal(0, vol, n)
    for k in range(aralik // 2, n - 60, aralik):
        r[k:k + 20] -= 0.016
        r[k + 20:k + 45] += 0.005
    c = 100.0 * np.exp(np.cumsum(r))
    idx = pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC", name="zaman")
    o = np.r_[100.0, c[:-1]] * (1 + rng.normal(0, vol / 6, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol / 3, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol / 3, n)))
    return pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": c, "hacim": 1000.0, "quote_hacim": 1e5, "islem_sayisi": 10}, index=idx)


def test_gercek_kapanis_stratejileri_sentetik_mumda_paper_backtest_ile_ayni():
    """6 kapanış stratejisinin GERÇEK sınıf/parametreleri (NASOS: azalan ROI + geri çekilme dahil), tek sembol, sentetik mum: aynı işlemler."""
    fr = {"1d": "D", "4h": "4h"}
    n_tf = {"1d": 500, "4h": 1200}
    vol = {"1d": 0.03, "4h": 0.015}
    toplam = {}
    for t in v2.tanimlari_yukle()[10:]:
        alt = t.alt_tanim("BTCUSDT")
        for seed in (1, 2) if t.tf != "5m" else (1,):
            if t.tf == "5m":
                n = 1500
                m = _cokus_mumu(n, seed)
            else:
                n = n_tf[t.tf]
                m = sentetik(n, seed=seed, p0=100.0, vol=vol[t.tf])
                m.index = pd.date_range("2024-01-01", periods=n, freq=fr[t.tf], tz="UTC", name="zaman")
            r = es.tek_esle(alt, m, None, {"BTCUSDT": tarama.VARSAYILAN_KURAL}, m.index[int(n * (0.2 if t.tf == "5m" else 0.6))])
            assert r["n_backtest"] == r["n_paper"], (t.kimlik, r["farklar"][:3])
            assert r["tam_esit_zaman_haric"], (t.kimlik, r["farklar"][:3])
            assert r["max_mutlak_fark"] <= 1e-9
            toplam[t.kimlik] = toplam.get(t.kimlik, 0) + r["n_backtest"]
    assert all(v > 0 for v in toplam.values()), toplam                      # her stratejide en az bir işlem karşılaştırıldı


# ---------------------------------------------------------------------------- 10 -> 16 hesap geçişi
def _yeni_set(eski: dict, *kapanis_kimlik) -> dict:
    y = copy.deepcopy(eski)
    for k in kapanis_kimlik:
        y["stratejiler"].append({"kaynak": "kapanis", "kimlik": k, "liste": "kosu_listesi_asama1.csv", "tf": "1d", "evren": "genel", "tur": "tek",
                                 "etiket": "kapanis_aday"})
    return y


def test_gecis_mevcut_hesaplar_korunur_yeni_hesap_sifirdan(tmp_path):
    mum = veri()
    ix = mum[("BTCUSDT", "1d")].index
    a, b = tanim("a", SEM, OrtalamaTrend(n=10)), tanim("b", SEM, OrtalamaTrend(n=20))
    c = tanim("c", ["ETHUSDT", "SOLUSDT"], OrtalamaTrend(n=15), etiket="kapanis_aday")
    s_eski = set_("a", "b")
    s_yeni = _yeni_set(s_eski, "c")
    assert v2.onceki_set_imzasi(s_yeni) == v2.set_imzasi(s_eski) and v2.set_imzasi(s_yeni) != v2.set_imzasi(s_eski)
    yol = tmp_path / "paper_state.json"
    # eski set: 150. günde dur, kaydet
    p1 = v2.kasalar_kur([a, b], mum, {}, s_eski, pencere={"1d": 300})
    p1.baslat(ix[120])
    p1.adim(ix[150])
    p1.kaydet(yol)
    # sürekli (kesintisiz) eski set referansı
    tam = v2.kasalar_kur([a, b], mum, {}, s_eski, pencere={"1d": 300})
    tam.baslat(ix[120])
    tam.adim(ix[-1] + pd.Timedelta(days=1))
    # yeni set (16'lı yapının küçük kopyası): mevcut yüklenir, c sıfırdan
    p2 = v2.kasalar_kur([a, b, c], mum, {}, s_yeni, pencere={"1d": 300})
    assert p2.yukle(yol) is True
    assert p2.yeni_hesaplar == ["c"]
    assert p2.yeni_hesaplari_baslat(ix[150]) == ["c"] and p2.yeni_hesaplar == []
    p2.adim(ix[-1] + pd.Timedelta(days=1))
    for k in ("a", "b"):
        assert islem_ozeti(p2.hesaplar[k]) == islem_ozeti(tam.hesaplar[k]) and len(islem_ozeti(tam.hesaplar[k])) >= 2
        assert p2.hesaplar[k].motor.ozsermaye() == tam.hesaplar[k].motor.ozsermaye()
    # c: 150. günde SIFIR kasayla başlamış gibi (tek başına aynı noktadan koşu ile aynı)
    tek_c = v2.kasalar_kur([c], mum, {}, _yeni_set(set_(), "c"), pencere={"1d": 300})
    tek_c.baslat(ix[150])
    tek_c.adim(ix[-1] + pd.Timedelta(days=1))
    assert islem_ozeti(p2.hesaplar["c"]) == islem_ozeti(tek_c.hesaplar["c"])
    assert p2.hesaplar["c"].motor.islemler == [] or all(pd.Timestamp(x["giris_zamani"]) >= ix[150] for x in p2.hesaplar["c"].motor.islemler)
    assert D0(p2.hesaplar["c"].ayarlar.baslangic_sermaye) == 10000
    # kayıt yeni imzayla yazılır; ikinci yükleme normal yoldan (geçiş yok)
    p2.kaydet(yol)
    d = json.loads(yol.read_text())
    assert d["set_imza"] == v2.set_imzasi(s_yeni) and set(d["hesaplar"]) == {"a", "b", "c"}
    p3 = v2.kasalar_kur([a, b, c], mum, {}, s_yeni, pencere={"1d": 300})
    assert p3.yukle(yol) is True and p3.yeni_hesaplar == []


def D0(x):
    return Decimal(str(x))


def test_gecis_yalniz_onceki_imzadan_baska_imza_ve_havuz_hesabi_eksikse_hata(tmp_path):
    mum = veri()
    ix = mum[("BTCUSDT", "1d")].index
    a, b = tanim("a", SEM), tanim("b", SEM, OrtalamaTrend(n=20))
    c = tanim("c", SEM, etiket="kapanis_aday")
    s_eski = set_("a", "b")
    yol = tmp_path / "paper_state.json"
    p1 = v2.kasalar_kur([a, b], mum, {}, s_eski, pencere={"1d": 300})
    p1.baslat(ix[120])
    p1.kaydet(yol)
    # başka imza (s değişti) -> geçiş değil, açık hata
    s_bozuk = _yeni_set(set_("a", "b", s=0.4), "c")
    with pytest.raises(v2.PaperV2Hatasi, match="set imzası"):
        v2.kasalar_kur([a, b, c], mum, {}, s_bozuk, pencere={"1d": 300}).yukle(yol)
    # önceki imza ama havuz hesabı (b) kayıtta yokmuş gibi: yalnız kapanış hesabı eksik olabilir
    d = json.loads(yol.read_text())
    del d["hesaplar"]["b"]
    yol.write_text(json.dumps(d))
    with pytest.raises(v2.PaperV2Hatasi, match="yalnız kapanış"):
        v2.kasalar_kur([a, b, c], mum, {}, _yeni_set(s_eski, "c"), pencere={"1d": 300}).yukle(yol)
    assert yol.exists()                                              # dosya asla silinmez
    # kapanış kaydı olmayan sette eksik hesap = eski davranış (imza zaten farklı olamaz): normal hata
    with pytest.raises(v2.PaperV2Hatasi, match="kayıtta şu hesaplar yok"):
        v2.kasalar_kur([a, b], mum, {}, s_eski, pencere={"1d": 300}).yukle(yol)


def test_canli_calistir_gecis_sahte_binance_yeni_hesap_sifirdan_mevcut_korunur(tmp_path, monkeypatch):
    from motor.canli import durum as dr
    from testler.test_paper_canli import SahteFapi
    monkeypatch.setattr(pv, "FapiIstemci", SahteFapi)
    monkeypatch.setitem(pp.PENCERE, "1d", 120)
    a = tanim("a", ["BTCUSDT", "ETHUSDT"], OrtalamaTrend(n=10), etiket="dogrulandi")
    b = tanim("b", ["SOLUSDT"], OrtalamaTrend(n=15))
    s_eski = set_("a", "b")
    monkeypatch.setattr(v2, "set_yukle", lambda *x, **k: s_eski)
    monkeypatch.setattr(v2, "tanimlari_yukle", lambda *x, **k: [a, b])
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    st1 = json.loads((tmp_path / "paper_state.json").read_text())
    assert set(st1["hesaplar"]) == {"a", "b"}
    # yeni set: kapanış hesabı "HAM:X005:7#v1" (dosya sistemi için güvenli olmayan karakterler içerir)
    c = tanim("HAM:X005:7#v1", ["SOLUSDT"], OrtalamaTrend(n=12), etiket="kapanis_aday")
    s_yeni = _yeni_set(s_eski, "HAM:X005:7#v1")
    a2, b2 = tanim("a", ["BTCUSDT", "ETHUSDT"], OrtalamaTrend(n=10), etiket="dogrulandi"), tanim("b", ["SOLUSDT"], OrtalamaTrend(n=15))
    monkeypatch.setattr(v2, "set_yukle", lambda *x, **k: s_yeni)
    monkeypatch.setattr(v2, "tanimlari_yukle", lambda *x, **k: [a2, b2, c])
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    st2 = json.loads((tmp_path / "paper_state.json").read_text())
    assert set(st2["hesaplar"]) == {"a", "b", "HAM:X005:7#v1"} and st2["set_imza"] == v2.set_imzasi(s_yeni)
    assert st2["hesaplar"]["a"]["motor"]["nakit"] is not None
    veri_, sorun = dr.oku_hepsi(tmp_path)
    assert not sorun
    s = {x["kimlik"]: x for x in veri_["stratejiler"]["stratejiler"]}
    assert s["HAM:X005:7#v1"]["etiket"] == "kapanis_aday"
    assert (tmp_path / "hesaplar" / "HAM_X005_7_v1" / "ozet.json").exists() and (tmp_path / "hesaplar" / "a" / "ozet.json").exists()
    assert any(o["tur"] == "yeni_hesap" for o in dr.ek_oku(tmp_path, "olaylar"))
    # üçüncü başlatma: normal yükleme, yeni hesap olayı tekrarlanmaz
    n_olay = sum(1 for o in dr.ek_oku(tmp_path, "olaylar") if o["tur"] == "yeni_hesap")
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    assert sum(1 for o in dr.ek_oku(tmp_path, "olaylar") if o["tur"] == "yeni_hesap") == n_olay


def test_hesap_dizin_adi_guvenli():
    assert v2.hesap_dizin_adi("HAM:X005:664#v1") == "HAM_X005_664_v1"
    assert v2.hesap_dizin_adi("dis__lube") == "dis__lube" and v2.hesap_dizin_adi("pf__sabit_sepet") == "pf__sabit_sepet"
    s = v2.set_yukle()
    assert len({v2.hesap_dizin_adi(v2.hesap_adi(k)) for k in s["stratejiler"]}) == 16


def test_butunluk_16_hesap_kayitla_eslesir_ve_sert_limitler_ayni():
    from motor.canli import guven as gv
    mal = v2.cevrimdisi_maliyet_modeli()
    assert len(mal) == 16
    b = gv.butunluk("paper", "2026-11-14T00:00:00Z", None, profil="v2", maliyet=mal, onbellek_sn=0)
    assert b["genel_durum"] == "eslesti"
    assert gv.sert_limitler() is not None


# ---------------------------------------------------------------------------- canlı kapısı: kapanış adayı canlıya alınamaz
def test_canli_onkontrol_kapanis_adayini_reddeder_havuz_stratejisini_etkilemez():
    from types import SimpleNamespace as NS
    from motor.canli.borsa import calistir as cal
    from motor.canli.borsa.motor_kopru import CanliDesteklemiyorHatasi
    for k in KAPANIS_KIMLIKLER:
        with pytest.raises(CanliDesteklemiyorHatasi, match="kapanis_aday|12 hafta"):
            cal.onkontrol(NS(stratejiler=[NS(id=k)]))
    cal.onkontrol(NS(stratejiler=[NS(id="dis__e0v1en")]))              # mevcut havuz stratejisi: davranış aynı (hata yok)
