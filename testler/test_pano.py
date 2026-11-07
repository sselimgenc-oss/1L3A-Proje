"""Pano testleri: pano hesap yapmaz (durum dosyasındaki sayıları aynen gösterir), bayat veri/eksik dosya uyarıları, Telegram metni."""
import json
import re
from datetime import datetime, timezone

import pytest

from motor.canli import durum as d
from motor.canli import pano
from motor.canli.pano import tsi
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
    p["ozet"]["baslangictan_pnl"] = "999.99"           # şerit bu alanı okur (sözleşme: toplam_pnl ile aynı sayı)
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
    assert "<table" not in h.replace('<div class="tw"><table', "")                                       # her tablo kendi kaydırma kutusunda
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



# ---------------------------------------------------------------- Aşama 4 genişletmesi: ek dosyalar, şerit, bayatlık bandı, TSİ
BL = {"ucret": "0.37", "kayma": "0.14", "funding": "-0.04", "toplam": "0.48"}
POZ = {"kimlik": "a|BTCUSDT|1h", "sembol": "BTCUSDT", "yon": "long", "miktar": "0.5", "giris_fiyati": "100.00", "mark_fiyat": "103.00",
       "giris_zamani": "2026-01-05T09:00:00Z", "stop": "95.00", "kz": "1.50", "kz_oran": 0.03, "nominal": "51.50", "kasaya_orani": 0.005, "stop_riski": "2.50"}


def genis_durum(kaynak="paper", yz="2026-01-05T12:05:00Z", hafta="-41.60", ek=True):
    p = ornek_durum(kaynak=kaynak)
    p["ozet"].update({"hafta_pnl": hafta, "hafta_pnl_neden": None if hafta else "7 gün dolmadı (4 gün)",
                      "gunluk_kz": [{"gun": "2026-01-03", "pnl": "-16.38", "getiri": -0.0016}, {"gun": "2026-01-04", "pnl": "31.69", "getiri": 0.0031}],
                      "dusus_serisi": [{"gun": "2026-01-03", "dusus": 0.0016}, {"gun": "2026-01-04", "dusus": 0.0}]})
    p["stratejiler"]["stratejiler"][0].update({"performans": {"islem": 7, "kazanma_orani": 0.4286, "ort_kar": "41.52", "ort_zarar": "-10.42", "net": "20.68", "pf": 1.99},
                                               "ayar": "izgara:k1=0.7", "sonraki_yenileme": "2026-01-12T00:00:00Z", "durum": "calisiyor", "kol_payi": 0.5})
    if ek:
        z = lambda ad: d._zarf(ad, kaynak, "2026-01-05T12:00:00Z")          # noqa: E731
        p["ekstra"] = {
            "maruziyet": {**z("maruziyet"), "semboller": [{"sembol": "BTCUSDT", "net_nominal": "51.50", "brut_nominal": "51.50", "net_oran": 0.005, "brut_oran": 0.005}],
                          "toplam_brut_nominal": "51.50", "toplam_net_nominal": "51.50", "kaldirac": 0.0051, "kullanilan_teminat": "17.17",
                          "teminat_notu": "brüt / 3x", "acik_stop_riski": {"deger": "2.50", "oran": 0.00024, "limit": 0.05}, "pozisyonlar": [POZ]},
            "maliyet": {**z("maliyet"), "toplam": {"son24s": BL, "tum": {"ucret": "13.92", "kayma": "5.94", "funding": "-0.46", "toplam": "19.40"}},
                        "stratejiler": {"a|BTCUSDT|1h": {"son24s": BL, "tum": {"ucret": "7.78", "kayma": "3.09", "funding": "0.08", "toplam": "10.96"}}}, "not": "ücret = taker"},
            "reddedilen": {**z("reddedilen"), "son24s": {"kirpildi:risk": 2}, "tum": {"kirpildi:risk": 3, "reddedildi:min_qty": 5},
                           "son": [{"zaman": "2026-01-05T11:00:00Z", "tur": "kirpildi", "neden": "risk", "kimlik": "a|BTCUSDT|1h", "sembol": "BTCUSDT"}]},
            "olaylar": [{"zaman": "2026-01-05T10:00:00Z", "tur": "ws_koptu", "mesaj": "bağlantı koptu"}, {"zaman": "2026-01-05T11:00:00Z", "tur": "kill_switch", "mesaj": "kill yok <b>"}],
            "icgoruler": {**z("icgoruler"), "cumleler": ["En iyi strateji a +43.74 USD.", "Açık 1 pozisyonun 1 tanesi kârda."]}}
    return p


def yaz_genis(dizin, **kw):
    p = genis_durum(**kw)
    d.yaz_hepsi(dizin, **p, yazildi=d.zaman_oku(kw.get("yz", "2026-01-05T12:05:00Z")))
    return p


def test_serit_her_sekmede_ve_sayilar_birebir(tmp_path):
    p = yaz_genis(tmp_path)
    h, _, _ = _html(tmp_path)
    o = p["ozet"]
    serit = h[h.index('class="izgara serit"'):h.index('class="sekme-kok"')]
    for b in (pano.f_para(o["ozsermaye"]), pano.f_para(o["gun_pnl"], True), pano.f_para("-41.60", True), pano.f_para(o["baslangictan_pnl"], True),
              pano.f_yuzde(o["zirveden_dusus"]), "Açık pozisyon", pano.f_para("51.50")):
        assert b in serit, b
    assert h.index('class="izgara serit"') < h.index('class="tabs"')                    # sekmelerin üstünde (sekmeye bağlı değil)
    assert "Bu hafta" in serit


def test_hafta_null_tire_ve_neden(tmp_path):
    yaz_genis(tmp_path, hafta=None)
    h, _, _ = _html(tmp_path)
    assert "7 gün dolmadı (4 gün)" in h
    serit = h[h.index('class="izgara serit"'):h.index('class="sekme-kok"')]
    assert re.search(r'Bu hafta</div><div class="d ">—</div><div class="alt">7 gün dolmadı', serit)


def test_bayatlik_bandi_yalniz_paper_ve_data_zaman_dogru(tmp_path):
    yaz_genis(tmp_path, yz="2026-01-05T12:05:00Z")
    h, _, _ = _html(tmp_path)
    assert 'id="bayat"' in h and 'data-zaman="2026-01-05T12:05:00Z"' in h and 'data-esik-dk="60"' in h and " hidden " in h
    assert "VERİ BAYAT: son güncelleme" in h and "sistem durmuş olabilir" in h
    assert "~15 dakikada bir yenilenir" in h
    assert "Date.now()" in h                                                              # tarayıcı tarafı kontrol
    bt = tmp_path / "bt"
    p = genis_durum(kaynak="backtest")
    p["ozet"]["donem"] = {"bas": "2026-01-01T00:00:00Z", "bit": "2026-01-05T00:00:00Z"}
    d.yaz_hepsi(bt, **p, yazildi=d.zaman_oku("2026-01-05T12:05:00Z"))
    hb, _, _ = _html(bt)
    assert 'id="bayat"' not in hb and "dakikada bir yenilenir" not in hb and "BACKTEST" in hb


def test_tsi_gosterimi(tmp_path):
    assert tsi("2026-01-05T12:00:00Z") == "2026-01-05 15:00" and tsi("2026-07-01T23:30:00Z") == "2026-07-02 02:30" and tsi(None) == "—"
    yaz_genis(tmp_path)
    h, _, _ = _html(tmp_path)
    assert "2026-01-05 15:10 TSİ" in h and "TSİ" in h and " UTC" not in h              # SIMDI 12:10Z -> 15:10 TSİ


def test_ek_bolumler_sayilar_birebir(tmp_path):
    p = yaz_genis(tmp_path)
    h, veri, sorun = _html(tmp_path)
    assert sorun == []
    e = p["ekstra"]
    o = p["ozet"]
    beklenen = [pano.f_para(x["pnl"], True) for x in o["gunluk_kz"]] + [pano.f_yuzde(x["dusus"]) for x in o["dusus_serisi"]]
    beklenen += [pano.f_para(POZ["nominal"]), pano.f_para(POZ["kz"], True), pano.f_yuzde(POZ["kz_oran"], True), "a · BTCUSDT · 1h", POZ["stop"], POZ["mark_fiyat"],
                 pano.f_para(POZ["stop_riski"]), pano.f_yuzde(e["maruziyet"]["semboller"][0]["brut_oran"]), pano.f_para("17.17"), pano.f_para("2.50")]
    perf = p["stratejiler"]["stratejiler"][0]["performans"]
    beklenen += [pano.f_para(perf["ort_kar"], True), pano.f_para(perf["ort_zarar"], True), pano.f_para(perf["net"], True), pano.f_sayi(perf["pf"]),
                 pano.f_yuzde(perf["kazanma_orani"], ondalik=1)]
    beklenen += [pano.f_para("13.92"), pano.f_para("5.94"), pano.f_para("-0.46", True), pano.f_para("19.40"), pano.f_para("0.37"), pano.f_para("0.48"), pano.f_para("10.96")]
    beklenen += ["kirpildi · risk", "reddedildi · min_qty", "ws_koptu", "bağlantı koptu", "2026-01-05 13:00", "En iyi strateji a +43.74 USD.", "Açık 1 pozisyonun 1 tanesi kârda."]
    for b in beklenen:
        assert b in h, b
    assert "<b>" not in h.split("kill yok")[1][:20] and "kill yok &lt;b&gt;" in h          # olay mesajı kaçışlı
    assert 'aria-label="zirveden düşüş"' in h and 'aria-label="günlük K/Z"' in h
    assert "<details" in h and 'class="kd"' in h and 'class="tw"' in h


def test_ek_dosya_yokken_kirilmaz(tmp_path):
    yaz_genis(tmp_path, ek=False)
    h, veri, sorun = _html(tmp_path)
    assert sorun == [] and veri["maruziyet"] is None and veri["olaylar"] is None
    for dosya in ("maruziyet.json", "maliyet.json", "reddedilen.json", "olaylar.jsonl", "icgoruler.json"):
        assert f"Veri yok: {dosya}" in h
    assert pano.f_para("51.50") not in h
    # tamamen eski görünüm (genişletme alanları da yok)
    yaz(tmp_path / "eski")
    h2, _, s2 = _html(tmp_path / "eski")
    assert s2 == [] and "Veri yok: maruziyet.json" in h2 and "motor bu alanı yazmıyor" in h2 and "Veri yok: dusus_serisi" in h2
    assert "BTCUSDT long" in h2                                                            # pozisyon stratejiler.json'dan


def test_bozuk_ek_dosya_acik_hata(tmp_path):
    yaz_genis(tmp_path)
    (tmp_path / "maliyet.json").write_text("{x", encoding="utf-8")
    h, _, sorun = _html(tmp_path)
    assert any("maliyet.json" in s and "bozuk" in s for s in sorun) and "Durum sorunu" in h and "Veri yok: maliyet.json" in h
    assert pano.main(["--durum", str(tmp_path)]) == 1


def test_bicim_uyumsuz_ek_bolum_sayfayi_kirmaz(tmp_path):
    p = genis_durum()
    p["ekstra"]["maliyet"]["toplam"] = {"son24s": {}}                                     # eksik alanlar
    p["ekstra"]["reddedilen"]["tum"] = {"kirpildi:risk": "x"}
    d.yaz_hepsi(tmp_path, **p)
    h, _, _ = _html(tmp_path)
    assert h.count("beklenen biçimde değil") >= 2 and "</html>" in h


def test_strateji_detayi_details_ve_js_siz(tmp_path):
    yaz_genis(tmp_path)
    h, _, _ = _html(tmp_path)
    bolum = h[h.index('<section class="n2">'):h.index('<section class="n3">')]
    assert "<details" in bolum and "izgara:k1=0.7" in bolum and "2026-01-12 03:00" in bolum      # sonraki yenileme TSİ
    assert "<script" not in bolum


def test_mobil_tasma_korumasi_css(tmp_path):
    yaz_genis(tmp_path)
    h, _, _ = _html(tmp_path)
    assert ".tw{overflow-x:auto" in h and "overflow-wrap:anywhere" in h and not re.search(r'(src|href)="https?://', h)
