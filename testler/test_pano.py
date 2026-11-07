"""Pano testleri: pano hesap yapmaz (durum dosyasındaki sayıları aynen gösterir), bayat veri/eksik dosya uyarıları, Telegram metni."""
import json
import re
from datetime import datetime, timezone

import pytest

from motor.canli import durum as d
from motor.canli import pano
from testler.test_canli_durum import ornek_durum, yaz

SIMDI = datetime(2026, 1, 5, 12, 10, tzinfo=timezone.utc)


def _html(dizin, simdi=SIMDI):
    veri, sorun = pano.yukle(dizin)
    return pano.html_olustur(veri, sorun, simdi), veri, sorun


def test_her_sayi_durum_dosyasindakiyle_ayni(tmp_path):
    p = yaz(tmp_path)
    h, veri, _ = _html(tmp_path)
    o = p["ozet"]
    for beklenen in (pano.f_para(o["ozsermaye"]), pano.f_para(o["toplam_pnl"], True), pano.f_yuzde(o["toplam_getiri"], True),
                     pano.f_para(o["gun_pnl"], True), pano.f_yuzde(o["gun_getiri"], True), pano.f_yuzde(o["zirveden_dusus"]),
                     pano.f_yuzde(o["max_dusus"]), pano.f_para(o["baslangic_ozsermaye"]),
                     pano.f_yuzde(o["risk"]["gunluk_kayip"]["deger"]), pano.f_sayi(o["risk"]["kaldirac"]["deger"]),
                     pano.f_yuzde(o["risk"]["kill_switch"]["mesafe"]), pano.f_yuzde(o["risk"]["acik_stop_riski"]["deger"]),
                     pano.f_para(p["stratejiler"]["stratejiler"][0]["ozsermaye_katkisi"], True),
                     pano.f_yuzde(p["stratejiler"]["stratejiler"][0]["beklenti"]["8"]["net_getiri"]["deger"], True)):
        assert beklenen in h, beklenen


def test_pano_yeniden_hesaplamaz(tmp_path):
    """Dosya kasten TUTARSIZ yazılır: pano toplamı kendisi türetseydi farklı sayı çıkardı; dosyadaki değer aynen görünmeli."""
    p = ornek_durum()
    p["ozet"]["toplam_pnl"] = "999.99"                 # özsermaye-başlangıç farkı (250.55) ile çelişir
    p["ozet"]["toplam_getiri"] = 0.5
    p["ozet"]["zirveden_dusus"] = 0.123
    p["stratejiler"]["stratejiler"][0]["ozsermaye_katkisi"] = "1.11"
    d.atomik_yaz_json(tmp_path / "ozet.json", p["ozet"])
    d.atomik_yaz_json(tmp_path / "stratejiler.json", p["stratejiler"])
    d.atomik_yaz_json(tmp_path / "saglik.json", p["saglik"])
    d.atomik_yaz_json(tmp_path / "ozsermaye_gecmisi.json", p["gecmis"])
    d.atomik_yaz_jsonl(tmp_path / "islemler.jsonl", p["islemler"])
    h, _, _ = _html(tmp_path)
    assert "+999.99" in h and "+50.00%" in h and "12.30%" in h and "+1.11" in h
    assert "+250.55" not in h


def test_html_tek_dosya_mobil_tema(tmp_path):
    yaz(tmp_path)
    h, _, _ = _html(tmp_path)
    assert 'name="viewport"' in h and "width=device-width" in h
    assert "prefers-color-scheme:dark" in h and 'data-theme="dark"' in h
    assert not re.search(r'(src|href)="https?://', h) and "@import" not in h and "<link" not in h     # harici kaynak yok
    assert "<table" not in h                                                                            # yatay kaydırma riski yok
    assert "overflow-wrap:anywhere" in h


def test_html_kacis(tmp_path):
    p = ornek_durum()
    p["stratejiler"]["stratejiler"][0]["kimlik"] = "<script>alert(1)</script>"
    d.yaz_hepsi(tmp_path, **p)
    h, _, _ = _html(tmp_path)
    assert "<script>alert(1)</script>" not in h


def test_eksik_dosya_acik_hata_ve_uydurma_yok(tmp_path):
    h, veri, sorun = _html(tmp_path / "yok")
    assert len(sorun) == 5 and 'class="uyari kritik"' in h and "ozet.json" in h
    assert "Özsermaye" not in h and "0.00" not in h               # değer uydurulmaz
    assert "DURUM YOK" in pano.telegram_metni(veri, sorun, SIMDI)


def test_bozuk_dosya_uyari_digerleri_gosterilir(tmp_path):
    yaz(tmp_path)
    (tmp_path / "saglik.json").write_text("{x", encoding="utf-8")
    h, _, sorun = _html(tmp_path)
    assert any("saglik.json" in s and "bozuk" in s for s in sorun)
    assert "Durum sorunu" in h and pano.f_para("10250.55") in h


def test_bayat_veri_kirmizi_uyari(tmp_path):
    yaz(tmp_path, bayat=True)
    veri, sorun = pano.yukle(tmp_path)
    u = pano.uyarilar(veri, sorun, SIMDI)
    assert any(s == "kritik" and "VERİ BAYAT: BTCUSDT" in m for s, m in u)
    assert 'class="uyari kritik"' in pano.html_olustur(veri, sorun, SIMDI)


def test_dosya_yasi_bayat(tmp_path):
    yaz(tmp_path, zaman="2026-01-05T12:00:00Z", dosya_esik_dk=30)
    veri, sorun = pano.yukle(tmp_path)
    taze = pano.uyarilar(veri, sorun, datetime(2026, 1, 5, 12, 20, tzinfo=timezone.utc))
    eski = pano.uyarilar(veri, sorun, datetime(2026, 1, 5, 13, 0, tzinfo=timezone.utc))
    assert not any("durum dosyası" in m for _, m in taze)
    assert any(s == "kritik" and "durum dosyası 60 dk önce" in m for s, m in eski)


def test_backtest_kaynagi_bayat_sayilmaz_ama_belirtilir(tmp_path):
    p = ornek_durum(kaynak="backtest", zaman="2025-11-05T00:00:00Z")
    p["ozet"]["donem"] = {"bas": "2025-11-01T00:00:00Z", "bit": "2025-11-05T00:00:00Z"}
    p["saglik"]["dosya_esik_dk"] = None
    d.yaz_hepsi(tmp_path, **p)
    veri, sorun = pano.yukle(tmp_path)
    u = pano.uyarilar(veri, sorun, datetime(2027, 1, 1, tzinfo=timezone.utc))
    assert not any(s == "kritik" and "BAYAT" in m for s, m in u if "BEKLENTİ" not in m)
    assert any("BACKTEST" in m for s, m in u)


def test_kill_ve_alarm_uyarilari(tmp_path):
    p = ornek_durum()
    p["ozet"]["risk"]["kill_switch"]["tetiklendi"] = True
    d.yaz_hepsi(tmp_path, **p)
    veri, sorun = pano.yukle(tmp_path)
    m = " ".join(x for _, x in pano.uyarilar(veri, sorun, SIMDI))
    assert "KILL SWITCH" in m and "BEKLENTİ ALARMI" in m           # ornek_durum 8 hf net alarmı true


def test_telegram_metni_kisa_ve_ayni_sayilar(tmp_path):
    p = yaz(tmp_path)
    veri, sorun = pano.yukle(tmp_path)
    t = pano.telegram_metni(veri, sorun, SIMDI)
    assert len(t) < 700 and pano.f_para(p["ozet"]["ozsermaye"]) in t and pano.f_yuzde(p["ozet"]["gun_getiri"], True) in t
    assert "Set 8 hafta" in t


def test_cli_cikis_kodlari(tmp_path, capsys):
    yaz(tmp_path)
    assert pano.main(["--durum", str(tmp_path), "--simdi", "2026-01-05T12:10:00Z"]) == 2          # ornek durumda alarm var
    assert (tmp_path / "pano.html").exists()
    assert pano.main(["--durum", str(tmp_path / "yok"), "--cikti", str(tmp_path / "h.html")]) == 1
    assert (tmp_path / "h.html").exists()


def test_terminal_ozeti(tmp_path):
    yaz(tmp_path)
    veri, sorun = pano.yukle(tmp_path)
    t = pano.terminal_ozet(veri, sorun, SIMDI)
    assert "10,250.55" in t and "a · BTCUSDT · 1h" in t


def test_pano_hesap_yapmaz_kaynak_denetimi():
    """pano.py durum alanlarıyla aritmetik yapmamalı: toplam/oran türeten ifadeler yok (basit kaynak taraması)."""
    kaynak = open(pano.__file__, encoding="utf-8").read()
    for yasak in ("sum(", "statistics", "numpy", "pandas"):
        assert yasak not in kaynak
