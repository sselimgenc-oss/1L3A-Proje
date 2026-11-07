"""Telegram mesajları: biçim (HTML geçerli/kaçışlı, TSİ, Türkçe sayı), teknik olaylar gitmez, sel koruması, 4096 sınırı."""
import re
from html.parser import HTMLParser

import pytest

from motor.canli import telegram as tg


class _Kontrol(HTMLParser):
    def __init__(self):
        super().__init__()
        self.yigin, self.hata = [], False

    def handle_starttag(self, t, a):
        self.yigin.append(t)

    def handle_endtag(self, t):
        if not self.yigin or self.yigin.pop() != t:
            self.hata = True


def html_gecerli(m: str) -> bool:
    k = _Kontrol()
    k.feed(m)
    k.close()
    return not k.hata and not k.yigin and len(m) <= 4096 and not re.search(r"<(?!/?(b|i)>)", m)


KAPANAN = {"zaman": "2026-11-07T16:55:00Z", "kimlik": "dis__dual-thrust|ETHUSDT|30m", "sembol": "ETHUSDT", "yon": "long",
           "giris_zamani": "2026-11-07T10:00:00Z", "giris_fiyati": "2450.5", "cikis_zamani": "2026-11-07T16:55:00Z",
           "cikis_fiyati": "2512.75", "miktar": "2", "r": 1.5, "net_pnl_yerel": "120.30", "set_katki_usd": "120.30", "cikis_nedeni": "hedef"}
ACIK = {"kimlik": "pf__kesit_ls|kripto|1d", "sembol": "SOLUSDT", "yon": "short", "miktar": "10", "giris_fiyati": "150.25", "mark_fiyat": "148",
        "giris_zamani": "2026-11-07T00:00:00Z", "stop": "160", "kz": "22.5", "kz_oran": 0.015, "nominal": "1480.00", "kasaya_orani": 0.15,
        "stop_riski": "100"}


def ozet(**ek):
    st = [{"kimlik": "dis__dual-thrust|ETHUSDT|30m", "ozsermaye_katkisi": "120.30", "islem_sayisi": 3, "acik_pozisyonlar": [], "durum": "calisiyor"},
          {"kimlik": "pf__kesit_ls|kripto|1d", "ozsermaye_katkisi": "-40.00", "islem_sayisi": 1, "acik_pozisyonlar": [ACIK], "durum": "calisiyor"}]
    st += [{"kimlik": k, "ozsermaye_katkisi": "0.00", "islem_sayisi": 0, "acik_pozisyonlar": [], "durum": "calisiyor"}
           for k in ("pf__rotasyon|hepsi|1d", "pf__kanarya|hisse_emtia|1d", "swing__cci-esik|SOLUSDT|1d")]
    oz = {"zaman": "2026-11-07T16:55:00Z", "ozsermaye": "10080.30", "gun_pnl": "80.30", "gun_getiri": 0.0081, "hafta_pnl": None,
          "toplam_pnl": "80.30", "toplam_getiri": 0.00803, "zirveden_dusus": 0.012,
          "risk": {"gunluk_kayip": {"deger": 0.0, "limit": 0.03}, "kill_switch": {"limit": 0.2}}}
    return {"ozet": oz, "stratejiler": {"stratejiler": st}, "saglik": {"uyarilar": ek.get("uyarilar", []), "durum": ek.get("durum", "ok")}}


def test_sayi_bicimi():
    assert tg.usd("1234.5") == "1.234,50 $" and tg.usd("-5", True) == "−5,00 $" and tg.usd("0", True) == "+0,00 $"
    assert tg.yuzde(0.0125) == "+%1,25" and tg.yuzde(-0.2, False, 0) == "%20" and tg.yuzde(None) == "—"
    assert tg.fiyat("2450.5") == "2.450,50" and tg.fiyat("0.0123") == "0,0123" and tg.fiyat("150.25") == "150,25"


def test_tsi_ve_ad():
    assert tg.tsi_saat("2026-11-07T16:55:00Z") == "07.11 19:55" and tg.tsi_gun("2026-11-07T16:55:00Z") == "7 Kasım"
    assert tg.ad("dis__dual-thrust|ETHUSDT|30m") == "Dual Thrust · ETH 30dk" and tg.ad("bilinmeyen|X|1d") == "bilinmeyen|X|1d"
    from motor.canli import paper_sinyal  # noqa: F401
    import json
    from pathlib import Path
    kimlikler = [s["kimlik"] for s in json.loads((Path(__file__).parent.parent / "stratejiler" / "final_set.json").read_text(encoding="utf-8"))["stratejiler"]]
    assert len(kimlikler) == 7 and all(k in tg.AD for k in kimlikler)


def test_islem_kapandi_kar_ve_zarar():
    m = tg.islem_kapandi_metni(KAPANAN)
    assert html_gecerli(m) and "✅" in m and "🟢 long" in m and "Dual Thrust · ETH 30dk" in m
    assert "2.450,50 → çıkış 2.512,75" in m and "tutar 4.901,00 $" in m and "+120,30 $" in m and "+%2,45" in m
    assert "R 1,50" in m and "hedefe ulaştı" in m and "19:55 TSİ" in m
    z = tg.islem_kapandi_metni({**KAPANAN, "yon": "short", "net_pnl_yerel": "-50.00", "cikis_nedeni": "stop", "r": -1.0})
    assert "❌" in z and "🔴 short" in z and "−50,00 $" in z and "stop çalıştı" in z and html_gecerli(z)


def test_islem_acildi():
    m = tg.islem_acildi_metni(ACIK)
    assert html_gecerli(m) and "🔴" in m and "Kesit L/S · Kripto" in m and "SOLUSDT" in m and "1.480,00 $" in m and "stop 160,00" in m and "03:00 TSİ" in m


def test_html_kacis():
    m = tg.islem_kapandi_metni({**KAPANAN, "kimlik": "<b>x</b>&y", "cikis_nedeni": "<script>"})
    assert "<script>" not in m and "&lt;script&gt;" in m and "&lt;b&gt;x&lt;/b&gt;&amp;y" in m
    u = tg.uyari_metni("binance_hata", "<i>hata</i> & %12.50")
    assert "&lt;i&gt;" in u and "%12,50" in u and html_gecerli(u)


def test_gunluk_ozet():
    m = tg.ozet_metni(ozet())
    assert html_gecerli(m) and "📊 <b>Günlük özet — 7 Kasım</b>" in m and "10.080,30 $" in m and "Bugün: +80,30 $ (+%0,81)" in m
    assert "Başlangıçtan beri: +80,30 $ (+%0,80)" in m and "Risk: günlük kayıp %0,0/%3 · kill mesafesi %20" in m
    assert "Açık pozisyonlar (1)" in m and "Kesit L/S · Kripto" in m and "3 strateji işlem bekliyor" in m
    assert "Rotasyon" not in m and "Dual Thrust · ETH 30dk: +120,30 $ · 3 işlem" in m and "hafta: — (7 gün dolmadı)" in m
    assert "🚨" not in m
    a = tg.ozet_metni(ozet(uyarilar=["BEKLENTİ ALARMI: swing__cci-esik|SOLUSDT|1d 4 hafta net getiri -%12.5"], durum="veri_bayat"))
    assert "🚨 <b>BEKLENTİ ALARMI: CCI Eşik · SOL 1G" in a and "-%12,5" in a and "veri bayat" in a and html_gecerli(a)


def test_ozet_4096():
    o = ozet(uyarilar=["x" * 300] * 40)
    assert len(tg.ozet_metni(o)) <= 4096
    assert len(tg.kirp("a\n" * 5000)) <= 4096


def test_uyarilar():
    for tur in ("kill_switch", "gunluk_limit", "veri_bosluk", "binance_hata", "ayar_yenileme", "beklenti_alarmi"):
        m = tg.uyari_metni(tur, "ornek mesaj")
        assert html_gecerli(m) and ("🚨" in m or "⚠️" in m) and "👉" in m
    assert "🚨" in tg.uyari_metni("kill_switch", "x") and tg.olay_metni("ws_koptu", "x") is None


def test_baslangic():
    assert tg.baslangic_metni(7, "10000.00") == "▶️ <b>Paper motoru çalışıyor</b> · 7 strateji · kasa 10.000 $"


class Sahte:
    def __init__(self):
        self.t, self.giden = 1000.0, []

    def saat(self):
        return self.t

    def gonder(self, m):
        self.giden.append(m)
        return True

    def bld(self):
        return tg.Bildirimci(self.gonder, self.saat)


def test_teknik_olaylar_gonderilmez():
    s = Sahte()
    b = s.bld()
    for tur in ("baslangic", "yeniden_baslatma", "ws_baglandi", "ws_koptu", "ws_yeniden_baglandi", "ws_24sa_yenileme", "veri_uyusmazlik"):
        b.olay(tur, "x")
    assert s.giden == []


def test_ws_10dk_sonra_tek_uyari():
    s = Sahte()
    b = s.bld()
    b.olay("ws_koptu", "x")
    s.t += 300
    b.olay("ws_koptu", "yeniden deneme")
    assert not b.kontrol() and s.giden == []
    s.t += 400
    assert b.kontrol() and len(s.giden) == 1 and "10 dakikadır" in s.giden[0]
    s.t += 60
    assert not b.kontrol() and len(s.giden) == 1


def test_ws_saatte_3_kopma():
    s = Sahte()
    b = s.bld()
    for _ in range(3):
        b.olay("ws_koptu", "x")
        s.t += 60
        b.olay("ws_yeniden_baglandi", "x")
        s.t += 60
    assert len(s.giden) == 1 and "3 kopma" in s.giden[0]


def test_sel_korumasi_30dk():
    s = Sahte()
    b = s.bld()
    b.olay("binance_hata", "a")
    s.t += 600
    b.olay("binance_hata", "b")
    assert len(s.giden) == 1
    b.olay("veri_bosluk", "farklı tür")
    assert len(s.giden) == 2
    s.t += 1300
    b.olay("binance_hata", "c")
    assert len(s.giden) == 3
    for _ in range(3):
        b.olay("kill_switch", "k")                   # kill switch her zaman gider
    assert len(s.giden) == 6
