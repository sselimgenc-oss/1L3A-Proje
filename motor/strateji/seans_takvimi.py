"""Seans takvimi: "günün son mumu" (gün sonu) tespiti için piyasa türü ve seans kapanış anı.

Neden: gün sonu eskiden yalnız "mumun kapanışı bir sonraki (UTC / seans_saat kaydırmalı) güne taşıyor mu" ile bulunuyordu.
7/24 kriptoda doğru; seanslı veride (ABD hissesi, BIST) gün gece yarısından çok önce biter, son mum hiç işaretlenmezdi;
24/5 vadeli/CFD (DK_XAU, DK_WTI, DK_SPX, ...) verisinde Cuma (hafta) ve tatil arifesi kapanışı kaçardı.

Kural (lookahead YOK): mum t, kapanış anı (açılış + mum süresi) günün bilinen SEANS KAPANIŞ anına ulaşıyor ya da onu
geçiyorsa günün son mumudur. Karar yalnız mumun kendi zamanından + sabit takvimden çıkar; sonraki mumun varlığına bakılmaz.
Kapanıştan sonra açılan (seans dışı) mumlar da işaretlenir (yeni giriş yok, açık pozisyon kapanır).

Piyasa türü indeksin ZAMAN AYAK İZİNDEN çıkarılır (fiyat kullanılmaz; sembolün yapısal özelliği = hangi saatlerde işlem
gördüğü). Strateji arayüzü sembol adını almadığı için bu yol seçildi. Kural yalnız olumlu kanıtla seanslı der; aksi kripto:
  - Cumartesi (UTC) mumu varsa                          -> kripto (7/24; davranış eskisiyle birebir)
  - tüm mumlar hafta içi, NY yerel 09:00-16:59, >=2 gün -> abd_hisse (NYSE 16:00 NY; erken kapanış 13:00 NY)
  - tüm mumlar hafta içi, İstanbul 09:00-17:59, >=2 gün -> bist (18:00 TR; yarım gün 12:30 TR)
  - Cumartesi yok ve ardışık iki mum arası >= 24 saat  -> vadeli_24_5 (CME benzeri: Cuma 17:00 NY hafta kapanışı,
    Büyük Cuma / 25 Aralık / 1 Ocak öncesi gün 17:00 NY; 24 Aralık, Şükran Günü ertesi ve Cumaya düşen ABD tatili
    (4 Temmuz, Juneteenth) 13:00 NY
    erken kapanış — gerçek CME saatinden biraz erken olabilir, güvenli yön)
  - diğer                                                 -> kripto
Takvim YAKLAŞIKTIR (önceden ilan edilen tatiller/yarım günler; ilan edilmemiş kapanış bilinmez). BIST yarım gün listesi
(dini bayram arifeleri) elle tutulur; yeni yıllar eklenmelidir (bkz. BIST_YARIM_GUNLER).
Veriden doğrulama (2026-11-08): DK_AAPL 1h son mum 19:00 UTC (yaz) / 20:00 UTC (kış), erken kapanış günleri 16:00/17:00;
BIST 30m/5m son mum 14:30/14:55 UTC (kapanış 15:00 UTC), arife günleri 09:30 UTC; DK_XAU/WTI/SPX Cuma son mum 20:00/21:00
UTC, Büyük Cuma arifesi 20:00, 24 Aralık 18:00, 31 Aralık 21:00 UTC.
"""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
from dateutil.easter import easter

KRIPTO, ABD_HISSE, BIST, VADELI = "kripto", "abd_hisse", "bist", "vadeli_24_5"
TURLER = (KRIPTO, ABD_HISSE, BIST, VADELI)
NY, IST = "America/New_York", "Europe/Istanbul"

# BIST yarım günleri (12:30 TR kapanış): 28 Ekim (Cumhuriyet Bayramı arifesi) kurala bağlı; dini bayram arifeleri burada.
BIST_YARIM_GUNLER = frozenset({
    date(2023, 4, 20), date(2023, 6, 27),
    date(2024, 4, 9), date(2024, 6, 15),
    date(2025, 3, 29), date(2025, 6, 5),
    date(2026, 3, 19), date(2026, 5, 26),
})


def _utc(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")


def _ayak_izi_uyar(yerel: pd.DatetimeIndex, saat_alt: int, saat_ust: int) -> bool:
    gunler = yerel.normalize()
    return (len(gunler.unique()) >= 2 and bool((yerel.weekday < 5).all())
            and bool(((yerel.hour >= saat_alt) & (yerel.hour <= saat_ust)).all()))


def seans_turu(index: pd.DatetimeIndex) -> str:
    """İndeksin zaman ayak izinden piyasa türü (kripto / abd_hisse / bist / vadeli_24_5). Fiyat kullanılmaz."""
    if len(index) < 2:
        return KRIPTO
    u = _utc(index)
    if bool((u.weekday == 5).any()):
        return KRIPTO
    if _ayak_izi_uyar(u.tz_convert(NY), 9, 16):
        return ABD_HISSE
    if _ayak_izi_uyar(u.tz_convert(IST), 9, 17):
        return BIST
    if bool(((u[1:] - u[:-1]) >= pd.Timedelta(hours=24)).any()):
        return VADELI
    return KRIPTO


# ------------------------------------------------------------------ takvim yardımcıları
def _n_gun(yil: int, ay: int, haftagunu: int, n: int) -> date:
    d = date(yil, ay, 1)
    d += timedelta(days=(haftagunu - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _sukran_ertesi(yil: int) -> date:
    return _n_gun(yil, 11, 3, 4) + timedelta(days=1)


def _nyse_erken_kapanis(d: date) -> bool:
    """13:00 NY erken kapanış: Şükran Günü ertesi, 24 Aralık (hafta içi), 3 Temmuz (Pzt-Per)."""
    if d == _sukran_ertesi(d.year):
        return True
    if d.month == 12 and d.day == 24 and d.weekday() < 5:
        return True
    return d.month == 7 and d.day == 3 and d.weekday() < 4


def _gozlenen(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def _vadeli_tam_kapali(d: date) -> bool:
    """CME benzeri tam kapalı gün: Büyük Cuma, 25 Aralık ve 1 Ocak (gözlenen)."""
    if d == easter(d.year) - timedelta(days=2):
        return True
    for ay, gun in ((12, 25), (1, 1)):
        for yil in (d.year - 1, d.year, d.year + 1):
            t = date(yil, ay, gun)
            if ay == 1 and t.weekday() == 5:      # 1 Ocak Cumartesi: önceki Cuma kapanmaz (NYSE/CME uygulaması)
                continue
            if _gozlenen(t) == d:
                return True
    return False


def _son_gun(yil: int, ay: int, haftagunu: int) -> date:
    d = date(yil + (ay == 12), ay % 12 + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - haftagunu) % 7)


@lru_cache(maxsize=None)
def _abd_tatilleri(yil: int) -> frozenset:
    """NYSE tatilleri (gözlenen gün). Juneteenth 2022'den itibaren."""
    t = {_n_gun(yil, 1, 0, 3), _n_gun(yil, 2, 0, 3), easter(yil) - timedelta(days=2), _son_gun(yil, 5, 0),
         _n_gun(yil, 9, 0, 1), _n_gun(yil, 11, 3, 4)}
    for ay, gun in ((1, 1), (6, 19), (7, 4), (12, 25)):
        if ay == 6 and yil < 2022:
            continue
        d = date(yil, ay, gun)
        if ay == 1 and d.weekday() == 5:
            continue
        t.add(_gozlenen(d))
    return frozenset(t)


def _tatil_cumasi(d: date) -> bool:
    """Cumaya düşen ABD tatili (4 Temmuz, Juneteenth, ...): CME erken durur, hafta sonuna kadar açılmaz."""
    return d.weekday() == 4 and d in _abd_tatilleri(d.year)


@lru_cache(maxsize=None)
def _kapanis_dakikasi(tur: str, d: date):
    """Yerel tarih d için seans kapanışı (yerel gün dakikası) veya None (o gün ek kapanış yok)."""
    if tur == ABD_HISSE:
        return 13 * 60 if _nyse_erken_kapanis(d) else 16 * 60
    if tur == BIST:
        yarim = d in BIST_YARIM_GUNLER or (d.month == 10 and d.day == 28)
        return 12 * 60 + 30 if yarim else 18 * 60
    if tur == VADELI:
        if d.weekday() >= 5 or _vadeli_tam_kapali(d):
            return None
        if (d.month == 12 and d.day == 24) or d == _sukran_ertesi(d.year) or _tatil_cumasi(d):
            return 13 * 60
        sonraki = d + timedelta(days=1)
        if d.weekday() == 4 or _vadeli_tam_kapali(sonraki):
            return 17 * 60
        return None
    raise ValueError(f"Bilinmeyen seans türü: {tur!r}")


def seans_kapanis_ani(index: pd.DatetimeIndex, tur: str) -> pd.DatetimeIndex:
    """Her mum için, mumun AÇILIŞ anının yerel tarihindeki seans kapanış anı (UTC). O gün ek kapanış yoksa NaT.
    Kripto için hepsi NaT."""
    u = _utc(index)
    if tur == KRIPTO:
        return pd.DatetimeIndex(np.full(len(u), np.datetime64("NaT"), dtype="datetime64[ns]"), tz="UTC")
    zon = IST if tur == BIST else NY
    yerel = u.tz_convert(zon)
    gunler = yerel.tz_localize(None).normalize()
    tekil = gunler.unique()
    degerler = []
    for g in tekil:
        dk = _kapanis_dakikasi(tur, g.date())
        degerler.append(pd.NaT if dk is None else (g + pd.Timedelta(minutes=dk)).tz_localize(zon).tz_convert("UTC"))
    tablo = pd.Series(pd.DatetimeIndex(degerler, tz="UTC"), index=tekil)
    return pd.DatetimeIndex(tablo.reindex(gunler).to_numpy(dtype="datetime64[ns]")).tz_localize("UTC")
