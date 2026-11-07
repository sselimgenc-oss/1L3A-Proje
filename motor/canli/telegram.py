"""Telegram bildirimleri (sg-arge `copytrade/canli/telegram.py` uyarlaması): metin üretimi + gönderim.

Token ve chat_id YALNIZ ortam değişkenlerinden okunur: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (systemd EnvironmentFile; repoya girmez).
Biri yoksa HİÇBİR ŞEY GÖNDERİLMEZ ve bu loglanır (hata değil, açık bilgi). Gönderim hatası loglanır ve False döner; motoru durdurmaz.
parse_mode=HTML: dinamik her metin html.escape'lidir. Mesaj 4096 karakteri aşmaz (satır sınırında kısaltılır).
Telegram YENİ HESAP YAPMAZ: sayılar durum alanlarından aynen gelir, burada yalnız biçimlenir (tek istisna: işlem mesajında
tutar = fiyat x miktar ve K/Z % = net / giriş tutarı, durumdaki `kz_oran` ile aynı tanım).
Teknik olaylar (WS bağlandı/koptu, yeniden başlatma...) kullanıcıya GİTMEZ (yalnız log/olaylar.jsonl); `Bildirimci` yalnız sorun
sürerse tek uyarı verir ve aynı türden mesajı 30 dk içinde tekrarlamaz.
"""
from __future__ import annotations

import html
import logging
import os
import re
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Callable, Optional
from zoneinfo import ZoneInfo

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


def kirp(metin: str) -> str:
    """4096 sınırı: aşarsa son tam satırda keser (etiketler satır içinde kapalı olduğundan HTML bozulmaz)."""
    if len(metin) <= MAKS:
        return metin
    kes = metin[:MAKS - 1]
    n = kes.rfind("\n")
    return (kes[:n] if n > 0 else kes) + "…"


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
                                      data={"chat_id": chat, "text": kirp(metin), "parse_mode": "HTML",
                                            "disable_web_page_preview": "true"}, timeout=15)
    except Exception as e:  # noqa: BLE001  (ağ hatası loglanır; motor durmaz)
        log.error("Telegram gönderim ağ hatası: %r", e)
        return False
    _son_gonderim[0] = saat()
    if r.status_code != 200:
        log.error("Telegram gönderim başarısız: HTTP %s %s", r.status_code, r.text[:200])
        return False
    return True


# ---------------------------------------------------------------------------- biçim yardımcıları
TSI = ZoneInfo("Europe/Istanbul")
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
ETIKET = "📄 1L3A Paper"
ETIKET_SATIRI = f"<i>{ETIKET}</i>"
# final_set.json'daki 7 strateji; bilinmeyen kimlikte kimliğin kendisi gösterilir.
AD = {"dis__dual-thrust|ETHUSDT|30m": "Dual Thrust · ETH 30dk",
      "pf__kanarya|hisse_emtia|1d": "Kanarya · Hisse+Emtia",
      "pf__rotasyon|hepsi|1d": "Rotasyon · Tümü",
      "pf__kesit_ls|kripto|1d": "Kesit L/S · Kripto",
      "swing__cci-esik|SOLUSDT|1d": "CCI Eşik · SOL 1G",
      "swing__konsolidasyon-kirilim|SOLUSDT|4h": "Konsolidasyon Kırılımı · SOL 4S",
      "dis__fraktal-alligator-sky|DK_NVDA|4h": "Fraktal Alligator · NVDA 4S"}
NEDEN_TR = {"stop": "stop çalıştı", "hedef": "hedefe ulaştı", "kismi": "kısmi çıkış", "kismi_tam": "kısmi çıkışlar tamamlandı",
            "veri_sonu": "veri sonu", "sinyal": "sinyal kapandı", "hedef_sifir": "sinyal kapandı", "yon_degisim": "sinyal yön değiştirdi",
            "kucultme": "pozisyon küçültüldü", "kill_switch": "kill switch", "gunluk_limit": "günlük kayıp limiti",
            "gunluk_kayip_limiti": "günlük kayıp limiti", "isinma": "ısınma dönemi"}
TEKNIK = {"ws_baglandi", "ws_yeniden_baglandi", "ws_koptu", "ws_24sa_yenileme", "yeniden_baslatma", "veri_uyusmazlik"}


def ad(kimlik: str) -> str:
    return AD.get(kimlik, kimlik)


def e(x) -> str:
    return html.escape(str(x), quote=False)


def _ondalik(x) -> Optional[Decimal]:
    try:
        return None if x is None else Decimal(str(x))
    except (InvalidOperation, ValueError):
        return None


def tr_sayi(x, ondalik: int = 2) -> str:
    """1234.5 -> '1.234,50'."""
    return f"{x:,.{ondalik}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def usd(x, isaretli: bool = False, ondalik: int = 2) -> str:
    """'1234.5' -> '1.234,50 $' (isaretli: '+1.234,50 $'); yok -> '—'."""
    v = _ondalik(x)
    if v is None:
        return "—"
    s = tr_sayi(abs(v), ondalik)
    isaret = ("−" if v < 0 else "+") if isaretli else ("−" if v < 0 else "")
    if isaretli and v == 0:
        isaret = "+"
    return f"{isaret}{s} $"


def yuzde(oran, isaretli: bool = True, ondalik: int = 2) -> str:
    """0.0125 -> '+%1,25'; isaretsiz '%1,25'."""
    v = _ondalik(oran)
    if v is None:
        return "—"
    s = "%" + tr_sayi(abs(v) * 100, ondalik)
    return (("−" if v < 0 else "+") + s) if isaretli else s


def fiyat(x) -> str:
    """Fiyat: büyüklüğe göre ondalık, gereksiz sıfırlar atılır (en az 2 ondalık)."""
    v = _ondalik(x)
    if v is None:
        return "—"
    n = 2 if abs(v) >= 1000 else 4 if abs(v) >= 1 else 6
    s = tr_sayi(v, n)
    ana, _, ond = s.partition(",")
    return ana + "," + (ond.rstrip("0").ljust(2, "0"))


def _tsi(zaman) -> datetime:
    z = datetime.fromisoformat(str(zaman).replace("Z", "+00:00"))
    return z.astimezone(TSI)


def tsi_saat(zaman) -> str:
    return _tsi(zaman).strftime("%d.%m %H:%M")


def tsi_gun(zaman) -> str:
    t = _tsi(zaman)
    return f"{t.day} {AYLAR[t.month - 1]}"


def _tr_ondalik(metin: str) -> str:
    """Motorun serbest metinlerindeki '%12.34' -> '%12,34'."""
    return re.sub(r"(%\d+)\.(\d+)", r"\1,\2", metin)


def _serbest(metin: str) -> str:
    """Motor/uyarı metni: kimlikler okunur ada çevrilir, sayı Türkçeleşir, HTML kaçışlanır."""
    for k in sorted(AD, key=len, reverse=True):
        metin = metin.replace(k, AD[k])
    return e(_tr_ondalik(metin))


def _em(yon: str) -> str:
    return "🟢" if yon == "long" else "🔴"


def _yon(yon: str) -> str:
    return f"{_em(yon)} {'long' if yon == 'long' else 'short'}"


# ---------------------------------------------------------------------------- mesajlar (hepsi durum dosyasındaki sayılardan)
def baslangic_metni(strateji_sayisi: int, kasa) -> str:
    return f"▶️ <b>Paper motoru çalışıyor</b> · {strateji_sayisi} strateji · kasa {usd(kasa, ondalik=0)}"


def islem_acildi_metni(poz: dict) -> str:
    """`paper_durum.acik_pozisyonlar` satırından."""
    g = [ETIKET_SATIRI, f"{_em(poz['yon'])} <b>İşlem açıldı</b> · {e(ad(poz['kimlik']))}",
         f"{e(poz['sembol'])} · {'long' if poz['yon'] == 'long' else 'short'} · giriş {fiyat(poz['giris_fiyati'])}",
         f"Tutar: {usd(poz.get('nominal'))} · stop {fiyat(poz.get('stop'))}"]
    if poz.get("giris_zamani"):
        g.append(f"🕐 {tsi_saat(poz['giris_zamani'])} TSİ")
    return "\n".join(g)


def islem_kapandi_metni(satir: dict) -> str:
    """`paper_durum._islem_satiri` çıktısından."""
    net = _ondalik(satir["net_pnl_yerel"])
    kar = net is not None and net > 0
    giris, miktar = _ondalik(satir.get("giris_fiyati")), _ondalik(satir.get("miktar"))
    tutar = giris * miktar if giris is not None and miktar is not None else None      # biçimlendirme türevi
    oran = net / tutar if net is not None and tutar else None
    r = _ondalik(satir.get("r"))
    neden = NEDEN_TR.get(satir["cikis_nedeni"], satir["cikis_nedeni"])
    yon = "long" if satir["yon"] == "long" else "short"
    g = [ETIKET_SATIRI, f"{'✅' if kar else '❌'} <b>İşlem kapandı</b> · {e(ad(satir['kimlik']))}",
         f"{_yon(yon)} · {e(satir['sembol'])}",
         f"Giriş {fiyat(satir['giris_fiyati'])} → çıkış {fiyat(satir['cikis_fiyati'])} · tutar {usd(tutar)}",
         f"K/Z: <b>{usd(net, True)}</b> ({yuzde(oran)}) · R {'—' if r is None else ('−' if r < 0 else '') + tr_sayi(abs(r), 2)}",
         f"Neden: {e(neden)}"]
    if satir.get("cikis_zamani"):
        g.append(f"🕐 {tsi_saat(satir['cikis_zamani'])} TSİ")
    return "\n".join(g)


islem_metni = islem_kapandi_metni


def ozet_metni(o: dict) -> str:
    """paper_durum.olustur çıktısından günlük özet (pano ile aynı dosyalar/sayılar)."""
    oz, st, sg = o["ozet"], o["stratejiler"]["stratejiler"], o["saglik"]
    r = oz["risk"]
    s = [ETIKET_SATIRI, f"📊 <b>Günlük özet — {tsi_gun(oz['zaman'])}</b>", "",
         f"💰 Kasa: <b>{usd(oz['ozsermaye'])}</b>",
         f"📅 Bugün: {usd(oz['gun_pnl'], True)} ({yuzde(oz.get('gun_getiri'))}) · hafta: "
         + (usd(oz.get('hafta_pnl'), True) if oz.get("hafta_pnl") is not None else "— (7 gün dolmadı)"),
         f"📈 Başlangıçtan beri: {usd(oz['toplam_pnl'], True)} ({yuzde(oz['toplam_getiri'])})",
         f"📉 Zirveden düşüş: {yuzde(oz['zirveden_dusus'], False)}",
         f"🛡 Risk: günlük kayıp {yuzde(r['gunluk_kayip']['deger'], False, 1)}/{yuzde(r['gunluk_kayip']['limit'], False, 0)} · "
         f"kill mesafesi {yuzde(r['kill_switch']['limit'], False, 0)}"]
    acik = [(x, p) for x in st for p in x["acik_pozisyonlar"]]
    if acik:
        s += ["", f"📂 <b>Açık pozisyonlar ({len(acik)})</b>"]
        for x, p in acik:
            s.append(f"{_em(p['yon'])} {e(ad(x['kimlik']))} · {e(p['sembol'])} · giriş {fiyat(p['giris_fiyati'])} · "
                     f"şimdi {usd(p['kz'], True)} ({yuzde(p.get('kz_oran'))})")
    aktif = [x for x in st if x["durum"] == "calisiyor" and (x["islem_sayisi"] or _ondalik(x["ozsermaye_katkisi"]) != 0)]
    bekleyen = [x for x in st if x["durum"] == "calisiyor" and x not in aktif]
    if aktif:
        s += ["", "🧩 <b>Stratejiler</b>"]
        for x in aktif:
            s.append(f"{'🟢' if _ondalik(x['ozsermaye_katkisi']) >= 0 else '🔴'} {e(ad(x['kimlik']))}: "
                     f"{usd(x['ozsermaye_katkisi'], True)} · {x['islem_sayisi']} işlem")
    if bekleyen:
        s += ["", f"💤 {len(bekleyen)} strateji işlem bekliyor"]
    uy = []
    for u in sg["uyarilar"]:
        sembol = "🚨" if "BEKLENTİ ALARMI" in u else "⚠️"
        uy.append(f"{sembol} <b>{_serbest(u)}</b>" if sembol == "🚨" else f"{sembol} {_serbest(u)}")
    if sg["durum"] != "ok":
        uy.append(f"⚠️ Sistem durumu: <b>{e(DURUM_TR.get(sg['durum'], sg['durum']))}</b>")
    if uy:
        s += [""] + uy
    return kirp("\n".join(s))


DURUM_TR = {"kill_switch": "kill switch devrede", "veri_bayat": "veri bayat", "uyari": "uyarı var"}

# tür -> (emoji, başlık, ne yapılmalı)
UYARI = {"kill_switch": ("🚨", "Kill switch devrede", "Tüm işlemler durdu; panoya bakıp karar vermeden yeniden başlatma."),
         "gunluk_limit": ("⚠️", "Günlük kayıp limiti doldu", "Yapacak bir şey yok; yarın otomatik devam eder."),
         "veri_bosluk": ("⚠️", "Veri sorunu", "Sürerse panoda veri durumuna bak; ilgili sembolde işlem durabilir."),
         "veri_yok": ("⚠️", "Veri yok", "O strateji çalışmıyor; panoda veri durumuna bak."),
         "binance_hata": ("⚠️", "Binance hatası", "Motor kendisi yeniden dener; 30 dk sürerse sunucuyu kontrol et."),
         "ayar_yenileme": ("⚠️", "Ayar yenileme zamanı", "Önerilen ayarı incele; onayın olmadan uygulanmaz."),
         "beklenti_alarmi": ("🚨", "Beklenti alarmı", "Strateji beklentinin altında; panoda ilgili stratejiye bak."),
         "ws_sorunu": ("⚠️", "Canlı veri bağlantısı sorunlu", "Motor yeniden bağlanmayı dener; sürerse sunucuyu kontrol et.")}


def uyari_metni(tur: str, mesaj: str = "") -> str:
    emoji, baslik, yap = UYARI.get(tur, ("⚠️", tur.replace("_", " ").capitalize(), "Panoya bakın."))
    g = [ETIKET_SATIRI, f"{emoji} <b>{e(baslik)}</b>"]
    if mesaj:
        g.append(_serbest(mesaj[:300]))
    g.append(f"👉 {e(yap)}")
    return "\n".join(g)


def olay_metni(tur: str, mesaj: str) -> Optional[str]:
    """Teknik olay -> None (gönderilmez); diğerleri uyarı metni."""
    return None if tur in TEKNIK or tur in ("baslangic",) else uyari_metni(tur, mesaj)


# ---------------------------------------------------------------------------- olay yönlendirme (sel koruması + teknik olaylar)
ARALIK_SN = 30 * 60              # aynı türden uyarı en erken 30 dk sonra tekrar
WS_KOPUK_SN = 10 * 60            # bu süre yeniden bağlanamazsa tek uyarı
WS_KOPMA_SAYI, WS_KOPMA_PENCERE_SN = 3, 3600


class Bildirimci:
    """Motorun `bildirim(tur, mesaj)` geri çağrısı. Teknik olaylar yalnız loglanır; sorun sürerse tek ⚠️; tür başına 30 dk sel koruması."""

    def __init__(self, gonder_fn: Callable[[str], bool] = None, saat: Callable[[], float] = time.time):
        self.gonder = gonder_fn or gonder
        self.saat = saat
        self.son: dict = {}
        self.kopuk_since: Optional[float] = None
        self.kopuk_uyarildi = False
        self.kopmalar: list = []

    def _yolla(self, anahtar: str, metin: str, aralik: float = ARALIK_SN) -> bool:
        t = self.saat()
        if anahtar in self.son and t - self.son[anahtar] < aralik:
            log.info("telegram (tekrar, atlandı) %s", anahtar)
            return False
        self.son[anahtar] = t
        return self.gonder(metin)

    def olay(self, tur: str, mesaj: str) -> bool:
        t = self.saat()
        if tur == "ws_koptu":
            if self.kopuk_since is None:                       # yeni kopma dönemi (yeniden deneme hataları sayılmaz)
                self.kopuk_since = t
                self.kopmalar = [x for x in self.kopmalar if t - x < WS_KOPMA_PENCERE_SN] + [t]
                if len(self.kopmalar) >= WS_KOPMA_SAYI:
                    return self._yolla("ws_sorunu", uyari_metni("ws_sorunu", f"Son 1 saatte {len(self.kopmalar)} kopma."))
            return False
        if tur in ("ws_baglandi", "ws_yeniden_baglandi"):
            self.kopuk_since, self.kopuk_uyarildi = None, False
            return False
        if tur in TEKNIK or tur == "baslangic":
            return False
        metin = uyari_metni(tur, mesaj)
        if tur == "kill_switch":
            self.son[tur] = t
            return self.gonder(metin)
        return self._yolla(tur, metin)

    def kontrol(self) -> bool:
        """Her turda çağrılır: bağlantı 10 dk'dır yoksa tek uyarı."""
        if self.kopuk_since is not None and not self.kopuk_uyarildi and self.saat() - self.kopuk_since >= WS_KOPUK_SN:
            self.kopuk_uyarildi = True
            return self._yolla("ws_sorunu", uyari_metni("ws_sorunu", "10 dakikadır yeniden bağlanılamadı."))
        return False

    def mesaj(self, anahtar: str, metin: str, aralik: float = ARALIK_SN) -> bool:
        """Genel (özet/işlem dışı) gönderim için sel korumalı yol."""
        return self._yolla(anahtar, metin, aralik)
