"""Denetim 2026-11-08 (pano-durum) düzeltmeleri: sabit metin yerine motor JSON'u, takvim 'gun' alanı, data-gun kaçışı."""
from datetime import datetime, timezone

from motor.canli import pano


def _kz(gun, pnl="10.00", getiri=0.001):
    return {"gun": gun, "pnl": pnl, "getiri": getiri}


def _isl(zaman, gun=None):
    s = {"zaman": zaman, "kimlik": "a|BTCUSDT|1h", "sembol": "BTCUSDT", "yon": "long", "r": 1.0, "net_pnl_yerel": "5.00", "cikis_nedeni": "stop"}
    if gun is not None:
        s["gun"] = gun
    return s


# ---------------------------------------------------------------------------- 5: sabit limit / strateji sayısı metinleri
def test_limit_metinleri_ozet_risk_ten_yoksa_butunluk_yoksa_bilinmiyor():
    oz = {"risk": {"kill_switch": {"limit": 0.15}, "gunluk_kayip": {"limit": 0.025}, "kaldirac": {"limit": 2.5}}}
    assert pano.limit_metinleri({"ozet": oz}) == {"kill": "%15", "gunluk": "%2.5", "kaldirac": "2.5x"}
    bt = {"sanal": [{"id": "sert_limitler", "ayrinti": {"kill_switch_dusus_yuzde": 20.0, "gunluk_max_kayip_yuzde": 3.0, "max_kaldirac": 3.0}}]}
    assert pano.limit_metinleri({"butunluk": bt}) == {"kill": "%20", "gunluk": "%3", "kaldirac": "3x"}
    assert pano.limit_metinleri({}) == {"kill": "bilinmiyor", "gunluk": "bilinmiyor", "kaldirac": "bilinmiyor"}
    assert pano.limit_metinleri({"ozet": {"risk": None}, "butunluk": {"sanal": None}})["kill"] == "bilinmiyor"


def test_cikis_aciklamasi_ve_sozluk_sabit_yuzde_icermez():
    for v in pano.CIKIS_ACIKLAMA.values():
        assert "%20" not in v and "%3)" not in v
    assert all("3x" not in v for _, v in pano.SOZLUK)
    lim = {"kill": "%15", "gunluk": "%2.5", "kaldirac": "2.5x"}
    assert "zirveden %15 düşüş" in pano.cikis_aciklama("kill_switch", lim)
    assert "(%2.5)" in pano.cikis_aciklama("gunluk_limit", lim)
    assert "bilinmiyor" in pano.cikis_aciklama("kill_switch", None)
    assert any("Sert tavan 2.5x" in v for _, v in pano.sozluk(lim))
    assert any("Sert tavan bilinmiyor" in v for _, v in pano.sozluk(None))


def test_karne_set_basligi_strateji_sayisini_veriden_alir():
    eks = [{"ad": "Kâr", "puan": None, "neden": "yok", "esik_durumu": None, "ozet": None}]
    set_ = {"tur": "set", "kimlik": "SET", "islem": 10, "olculen_eksen": 0, "eksenler": eks}
    st = [{"tur": "strateji", "kimlik": f"s{i}|BTCUSDT|1h", "islem": 1, "olculen_eksen": 0, "eksenler": eks} for i in range(3)]
    h = pano._karne_kart(set_, 3)
    assert "SET (3 strateji birlikte)" in h and "7 strateji" not in h
    assert "SET (strateji sayısı bilinmiyor)" in pano._karne_kart(set_, None)
    kr = {"set": set_, "stratejiler": st, "eksen_tanimlari": [], "yontem": "y", "genel_puan_neden": "n"}
    assert "SET (3 strateji birlikte)" in pano._karne_html(kr)


# ---------------------------------------------------------------------------- 6 + 7: takvim
def test_takvim_gun_alani_olmayan_islem_utc_gunune_dusmez_ve_isaretlenir():
    kz = [_kz("2026-01-04"), _kz("2026-01-05")]
    # 2026-01-04 22:30 UTC = 2026-01-05 01:30 TSİ: motorun 'gun' alanı TSİ günü; UTC tarihine (01-04) düşmemeli
    isl = [_isl("2026-01-04T22:30:00Z", gun="2026-01-05"), _isl("2026-01-04T21:00:00Z")]       # ikincisinde gun yok
    h = pano._takvim(kz, isl, {}, "Europe/Istanbul")
    d4 = h.split('<div class="gd" data-gun="2026-01-04">')[1].split('<div class="gd"')[0]
    d5 = h.split('<div class="gd" data-gun="2026-01-05">')[1]
    assert "Bu gün kapanan işlem yok" in d4                                   # gun'suz satır UTC gününe (01-04) düşmedi
    assert "BTCUSDT" in d5
    assert "1 işlemde 'gun' alanı yok" in h
    assert "'gun' alanı yok" not in pano._takvim(kz, [isl[0]], {}, "Europe/Istanbul")


def test_takvim_data_gun_kacisli():
    kz = [{"gun": '2026"01-04', "pnl": "1.00", "getiri": 0.0}]
    h = pano._takvim(kz, [], {}, "Europe/Istanbul")
    assert 'data-gun="2026&quot;01-04"' in h and 'data-gun="2026"01-04"' not in h


def test_pano_ana_cikti_hata_vermez_limitler_bilinmiyorken():
    h = pano.html_olustur({}, ["ozet.json yok"], datetime(2026, 11, 8, tzinfo=timezone.utc))
    assert "<html" in h
