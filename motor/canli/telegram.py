"""Telegram bildirimleri (sg-arge `copytrade/canli/telegram.py` uyarlaması): metin üretimi + gönderim.

Token ve chat_id YALNIZ ortam değişkenlerinden okunur: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (systemd EnvironmentFile; repoya girmez).
Biri yoksa HİÇBİR ŞEY GÖNDERİLMEZ ve bu loglanır (hata değil, açık bilgi). Gönderim hatası loglanır ve False döner; motoru durdurmaz.
Düz metin (parse_mode yok): kimlik/sembollerdeki özel karakterler sorun çıkarmaz. Mesaj 4096 karaktere kırpılır.
"""
from __future__ import annotations

import logging
import os
import time
from decimal import Decimal
from typing import Optional

log = logging.getLogger("paper.telegram")
TOKEN_ENV, CHAT_ENV = "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"
MAKS = 4096
EN_AZ_ARALIK_SN = 1.0                # iki mesaj arası alt sınır (Telegram: sohbet başına ~1 mesaj/sn)
_son_gonderim = [0.0]
_yok_loglandi = [False]


def yapilandirma(env=None) -> Optional[tuple]:
    env = os.environ if env is None else env
    token, chat = env.get(TOKEN_ENV, "").strip(), env.get(CHAT_ENV, "").strip()
    if not token or not chat:
        return None
    return token, chat


def gonder(metin: str, env=None, oturum=None, uyku=time.sleep, saat=time.monotonic) -> bool:
    """True: Telegram'a iletildi. False: yapılandırma yok (loglanır) ya da gönderim hatası (loglanır)."""
    y = yapilandirma(env)
    if y is None:
        if not _yok_loglandi[0]:
            log.warning("Telegram devre dışı: %s / %s ortam değişkenleri tanımlı değil; mesaj gönderilmiyor", TOKEN_ENV, CHAT_ENV)
            _yok_loglandi[0] = True
        log.info("telegram (gönderilmedi): %s", metin[:120].replace("\n", " | "))
        return False
    import requests
    token, chat = y
    gec = saat() - _son_gonderim[0]
    if gec < EN_AZ_ARALIK_SN:
        uyku(EN_AZ_ARALIK_SN - gec)
    try:
        r = (oturum or requests).post(f"https://api.telegram.org/bot{token}/sendMessage",
                                      data={"chat_id": chat, "text": metin[:MAKS], "disable_web_page_preview": "true"}, timeout=15)
    except Exception as e:  # noqa: BLE001  (ağ hatası loglanır; motor durmaz)
        log.error("Telegram gönderim ağ hatası: %r", e)
        return False
    _son_gonderim[0] = saat()
    if r.status_code != 200:
        log.error("Telegram gönderim başarısız: HTTP %s %s", r.status_code, r.text[:200])
        return False
    return True


# ---------------------------------------------------------------------------- metinler (hepsi durum dosyasındaki sayılardan)
def _p(x, isaretli=True) -> str:
    return "—" if x is None else (f"{x * 100:+.2f}%" if isaretli else f"{x * 100:.2f}%")


def _usd(s) -> str:
    return "—" if s is None else f"{Decimal(s):+,.2f}"


def olay_metni(tur: str, mesaj: str) -> str:
    simge = {"kill_switch": "KILL SWITCH", "gunluk_limit": "GÜNLÜK LİMİT", "ws_koptu": "BAĞLANTI", "veri_bosluk": "VERİ",
             "beklenti_alarmi": "BEKLENTİ ALARMI", "ayar_yenileme": "AYAR", "islem": "İŞLEM"}.get(tur, tur.upper())
    return f"[1L3A paper] {simge}: {mesaj}"


def islem_metni(satir: dict) -> str:
    return (f"[1L3A paper] İŞLEM KAPANDI: {satir['kimlik']} {satir['sembol']} {satir['yon']} "
            f"{satir['giris_fiyati']} -> {satir['cikis_fiyati']} · net {_usd(satir['net_pnl_yerel'])} USD · "
            f"R {satir['r'] if satir['r'] is not None else '—'} · {satir['cikis_nedeni']}")


def ozet_metni(o: dict) -> str:
    """paper_durum.olustur çıktısından günlük özet (pano.telegram_metni ile aynı sayılar: aynı dosyalardan)."""
    oz, st, sg = o["ozet"], o["stratejiler"], o["saglik"]
    r = oz["risk"]
    s = [f"[1L3A paper] {oz['zaman'][:16].replace('T', ' ')} UTC",
         f"Özsermaye {oz['ozsermaye']} ({_p(oz['toplam_getiri'])}) · bugün {_usd(oz['gun_pnl'])} · hafta {_usd(oz.get('hafta_pnl'))}",
         f"Zirveden düşüş {_p(oz['zirveden_dusus'], False)} (kill %{r['kill_switch']['limit'] * 100:.0f}) · "
         f"kaldıraç {r['kaldirac']['deger'] if r['kaldirac']['deger'] is None else round(r['kaldirac']['deger'], 2)}x · "
         f"günlük kayıp {_p(r['gunluk_kayip']['deger'], False)}/{_p(r['gunluk_kayip']['limit'], False)}",
         f"Açık {oz['sayaclar']['acik_pozisyon']} · kapanan {oz['sayaclar']['kapanan_islem']}"]
    for x in st["stratejiler"]:
        s.append(f"- {x['kimlik'].split('|')[0]} {_usd(x['ozsermaye_katkisi'])} · {x['islem_sayisi']} işlem")
    for c in o["ekstra"]["icgoruler"]["cumleler"]:
        s.append(f"* {c}")
    for u in sg["uyarilar"]:
        s.append(f"! {u}")
    if sg["durum"] != "ok":
        s.append(f"! DURUM: {sg['durum']}")
    return "\n".join(s)
