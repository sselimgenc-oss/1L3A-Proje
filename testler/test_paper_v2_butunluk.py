"""Paper v2: bütünlük kontrolü v2 setine göre (guven profil 'v2') + evrenden düşen sembollerin tek satıra indirilmesi."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from motor.canli import durum as d
from motor.canli import guven as gv
from motor.canli import pano
from motor.canli import paper as pp
from motor.canli import paper_v2 as v2
from testler.test_paper_v2 import SEM, kos, tanim, veri

KOK = Path(__file__).resolve().parents[1]
NEDEN = "DK_JNJ Binance USDⓈ-M exchangeInfo'da yok"
SIMDI_PANO = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)


def _tanimlar(n=7, ekstra=None):
    out = []
    for i in range(n):
        t = tanim(f"dis__s{i}", SEM)
        t.disarida = {"DK_JNJ": NEDEN, "DK_MA": NEDEN.replace("JNJ", "MA")}
        if ekstra and i == 0:
            t.disarida.update(ekstra)
        out.append(t)
    return out


# ---------------------------------------------------------------------------- gruplama
def test_disarida_beklenen_semboller_tek_bilgi_satiri():
    bilgi, uyari = pp.disarida_metinleri(pp.disarida_gruplari(_tanimlar()))
    assert bilgi == "DK_JNJ, DK_MA: Binance'te karşılığı yok → 7 stratejinin evreninden çıkarıldı (beklenen, kalıcı)"
    assert uyari == []


def test_disarida_beklenmeyen_sembol_gizlenmez_uyari_kalir():
    g = pp.disarida_gruplari(_tanimlar(ekstra={"DK_AAPL": "AAPLUSDT durumu BREAK (TRADING değil)", "BTCUSDT": "yerel veri yok: FileNotFoundError"}))
    bilgi, uyari = pp.disarida_metinleri(g)
    assert "DK_AAPL" not in bilgi and "BTCUSDT" not in bilgi and "7 stratejinin" in bilgi
    assert len(uyari) == 2 and all(u.startswith("BEKLENMEYEN") for u in uyari)
    assert any("DK_AAPL" in u and "TRADING değil" in u and "dis__s0" in u for u in uyari)
    # beklenen sembol ama FARKLI neden (ör. artık listede ama durumu değişti) = beklenmeyen
    g2 = pp.disarida_gruplari(_tanimlar(1, ekstra={"DK_JNJ": "DK_JNJ durumu BREAK (TRADING değil)"}))
    assert not next(x for x in g2 if x["sembol"] == "DK_JNJ")["beklenen"]


def test_disarida_bildir_olay_telegrama_gitmez_beklenmeyen_gider():
    class Sahte:
        def __init__(self):
            self.uyarilar, self.olaylar = [], []

        def olay_ekle(self, tur, mesaj, zaman=None, bildir=True):
            self.olaylar.append((tur, mesaj, bildir))
    p = Sahte()
    pp.disarida_bildir(p, _tanimlar(ekstra={"DK_AAPL": "AAPLUSDT durumu BREAK (TRADING değil)"}), None)
    assert [o for o in p.olaylar if o[0] == "evren_bilgi"] == [("evren_bilgi", p.olaylar[0][1], False)] and len(p.olaylar) == 2
    assert p.olaylar[1][0] == "veri_yok" and p.olaylar[1][2] is True
    assert len(p.uyarilar) == 2 and p.uyarilar[0].startswith(pp.BILGI_ONEKI)


# ---------------------------------------------------------------------------- pano: bilgi düzeyi + SAĞLIK ayrıntısı
def _durum(tmp_path, tanimlar):
    mum = veri()
    p = kos(tanimlar, mum, kapat=False)
    pp.disarida_bildir(p, p.tanimlar, None)
    simdi = mum[("BTCUSDT", "1d")].index[-1] + pd.Timedelta(days=1)
    return p, simdi


def test_pano_dusen_semboller_bilgi_duzeyinde_tek_satir_ve_saglik_ayrintisi(tmp_path):
    tans = _tanimlar(3)
    p, simdi = _durum(tmp_path, tans)
    v2.durum_yaz(p, p.kaynak, tmp_path, simdi, kaynak_adi="paper", veri_dizini=tmp_path)
    sg = json.loads((tmp_path / "saglik.json").read_text())
    assert sg["uyarilar"] == [] or all("evrenden düşen" not in u for u in sg["uyarilar"])
    assert len(sg["bilgiler"]) == 1 and sg["bilgiler"][0].startswith("DK_JNJ, DK_MA:")
    assert [x["sembol"] for x in sg["evren_disi"]] == ["DK_JNJ", "DK_MA"] and sg["evren_disi"][0]["stratejiler"] == ["dis__s0", "dis__s1", "dis__s2"]
    veri_, sorun = pano.yukle(tmp_path)
    u = pano.uyarilar(veri_, sorun, SIMDI_PANO)
    dusen = [(sev, m) for sev, m in u if "DK_JNJ" in m]
    assert len(dusen) == 1 and dusen[0][0] == "bilgi"
    html = pano.html_olustur(veri_, sorun, SIMDI_PANO)
    assert "Evrenden düşen semboller" in html and "beklenen, kalıcı" in html
    oz = json.loads((tmp_path / "ozet.json").read_text())
    assert sum("DK_JNJ" in n for n in oz["notlar"]) == 1


def test_pano_beklenmeyen_dusme_uyari_kalir(tmp_path):
    tans = _tanimlar(2, ekstra={"DK_AAPL": "AAPLUSDT durumu BREAK (TRADING değil)"})
    p, simdi = _durum(tmp_path, tans)
    v2.durum_yaz(p, p.kaynak, tmp_path, simdi, kaynak_adi="paper", veri_dizini=tmp_path)
    veri_, sorun = pano.yukle(tmp_path)
    u = pano.uyarilar(veri_, sorun, SIMDI_PANO)
    assert any(sev == "uyari" and "BEKLENMEYEN" in m and "DK_AAPL" in m for sev, m in u)
    assert any(sev == "bilgi" and "DK_JNJ" in m for sev, m in u)


# ---------------------------------------------------------------------------- bütünlük: v2 profili
def test_v2_kaydi_depoyla_eslesir_ve_sert_limitler_degismedi():
    mal = v2.cevrimdisi_maliyet_modeli()
    assert len(mal) == 10
    b = gv.butunluk("paper", "2026-11-12T00:00:00Z", None, profil="v2", maliyet=mal, onbellek_sn=0)
    assert b["genel_durum"] == "eslesti", [(x["id"], x["durum"]) for x in b["dosyalar"] + b["sanal"] if x["durum"] != "eslesti"]
    ids = {x["id"]: x for x in b["dosyalar"]}
    assert ids["set_dosyasi"]["yol"] == "stratejiler/paper_v2_seti.json"
    assert ids["maliyet_tablosu"]["yol"] == "sonuclar/evren/v2/maliyet_tablosu_v2.csv"
    assert ids["maliyet_tablosu"]["kayit_kaynagi"] == "sonuclar/evren/v2/maliyet_tablosu_v2.sha256"
    # SERT_LIMITLER değişmedi: v2 kaydı ile eski kayıt aynı özeti taşır
    eski = json.loads((KOK / "sonuclar/final/butunluk_kayit.json").read_text())["sanal"]["sert_limitler"]["sha256"]
    yeni = json.loads((KOK / "sonuclar/final/butunluk_kayit_v2.json").read_text())["sanal"]["sert_limitler"]["sha256"]
    assert eski == yeni == gv.sha256_sozluk(gv.sert_limitler())


def test_v2_maliyet_degisirse_uyusmuyor_gizlenmez():
    mal = v2.cevrimdisi_maliyet_modeli()
    k = next(iter(mal))
    mal[k] = {**mal[k], "kayma_bps": (mal[k]["kayma_bps"] or 0) + 1.0}
    b = gv.butunluk("paper", "2026-11-12T00:00:00Z", None, profil="v2", maliyet=mal, onbellek_sn=0)
    assert b["genel_durum"] == "uyusmuyor" and next(x for x in b["sanal"] if x["id"] == "maliyet_modeli")["durum"] == "uyusmuyor"


def test_pano_v2_butunluk_eslesti_bant_yok(tmp_path):
    tans = _tanimlar(2)
    p, simdi = _durum(tmp_path, tans)
    p.butunluk_maliyet = lambda: v2.cevrimdisi_maliyet_modeli()          # sunucudaki gerçek 10 hesabın modeli (çevrimdışı eşdeğeri)
    v2.durum_yaz(p, p.kaynak, tmp_path, simdi, kaynak_adi="paper", veri_dizini=tmp_path)
    b = d.ek_oku(tmp_path, "butunluk")
    assert b["profil"] == "v2" and b["genel_durum"] == "eslesti" and b["sayim"]["uyusmuyor"] == 0
    veri_, sorun = pano.yukle(tmp_path)
    assert not any("Backtest bütünlüğü" in m for _, m in pano.uyarilar(veri_, sorun, SIMDI_PANO))
    html = pano.html_olustur(veri_, sorun, SIMDI_PANO)
    assert "kayıtlı sha256 ile uyuşmuyor" not in html and "paper_v2_seti.json" in html
    # hesap dizinlerindeki pano da aynı (hesap başına değil set başına model)
    bh = d.ek_oku(tmp_path / "hesaplar" / "dis__s0", "butunluk")
    assert bh["genel_durum"] == "eslesti"


def test_pano_v2_gercek_olmayan_hesaplar_uyusmuyor_gosterir(tmp_path):
    """Sentetik hesaplar (farklı maliyet modeli) kayıtla eşleşmez -> kontrol zayıflatılmadı."""
    p, simdi = _durum(tmp_path, _tanimlar(2))
    v2.durum_yaz(p, p.kaynak, tmp_path, simdi, kaynak_adi="paper", veri_dizini=tmp_path)
    assert d.ek_oku(tmp_path, "butunluk")["genel_durum"] == "uyusmuyor"
