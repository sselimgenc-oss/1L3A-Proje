"""Canlı yürütücünün KAYIT (denetim) dosyaları. YALNIZ kayıt: işlem mantığına (sinyal, boyut, emir, stop, kill, mutabakat) dokunmaz.

Dosyalar (hepsi APPEND-ONLY, durum dizini altında `canli/`; satır başına bir JSON; her satır fsync'lenir):
  islemler.jsonl          her GERÇEK kapanan canlı pozisyon için bir satır (aşağıdaki alanlar)
  ozsermaye_gunluk.jsonl  strateji başına servis başlangıcında ve her UTC günü: özsermaye/tahsis/kasa/açık K/Z; tahsis değişimi ayrı
                          `sermaye_hareketi` satırı (60 -> 250 geçişi kâr sayılmasın); hesap toplamı + ortak zirve `hesap` satırı
  olaylar_arsiv.jsonl     yürütücünün HER olayı (dolan/atlanan sinyal ve neden dahil); paper'ın son-50 penceresi ayrıca sürer

`islemler.jsonl` alanları: sema, surum, zaman (= cikis_zamani), strateji, kol, sembol, yon (long|short), giris_zamani, cikis_zamani,
giris_fiyati / cikis_fiyati (dolum ağırlıklı ortalama, metin), miktar (girişte dolan toplam), stop_giris, stop_mesafesi_oran (giriş anında
|giriş-stop|/giriş), planlanan_risk_usd (giriş anındaki maliyet dahil stopta kayıp = kasa x risk_yuzde), komisyon_usd (null + komisyon_neden),
funding_usd (işaretli, negatif = ödenen; null + funding_neden), brut_pnl_usd (Binance realizedPnl toplamı), net_pnl_usd (= brüt - komisyon + funding;
komisyon yoksa null; funding yoksa funding HARİÇ ve net_funding_dahil=false), r (= net / planlanan risk), cikis_nedeni
(stop|hedef|strateji|kill|sistem|bilinmiyor), cikis_ayrinti, niyet_id (paper niyetinin belirleyici kimliği = giriş emri kimliği) + sinyal_zamani,
model_maliyet_bps, gercek_maliyet_bps, giris_kayma_bps, cikis_kayma_bps, kismi_cikis_sayisi, notlar[].

KISMİ KAPANIŞ: yürütücüde kısmi çıkış stratejisi yoktur; tek kısmi kapanış girişten hemen sonra sert limit nedeniyle yapılan `risk_azalt`
küçültmesidir. Bir pozisyonun yaşam döngüsü (sıfırdan sıfıra) TEK satırdır; tüm çıkış dolumları birleştirilir (cikis_fiyati ağırlıklı ortalama),
`kismi_cikis_sayisi` çıkış dolumu sayısını söyler (1'den büyükse parça parça kapanmıştır).

MALİYET ÖLÇÜSÜ (model ile AYNI kapsam): gercek_maliyet_bps = (komisyon + STOP çıkışlarında stop seviyesine göre kayma) / giriş nominali x 1e4;
model_maliyet_bps = (2 x taker + stop çıkışlarında stop_kayma) x 1e4 (motorun Niyet.taker / Niyet.stop_kayma değerleri = paper maliyet modeli).
Giriş kayması (dolum - karar anındaki mark) modelde karşılığı bu kayıtta bulunmadığı için AYRI alan (giris_kayma_bps), orana girmez.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Optional

D = Decimal
SEMA_ISLEM = "1l3a.canli.islem"
STABIL = ("USDT", "USDC", "BUSD", "FDUSD")
KAPAT_RE = re.compile(r"^(\S+) .*kapatıldı \((.*)\)$")
YAKIN_ORAN = D("0.01")                 # kapanış fiyatı stop/hedefe %1'den yakınsa o çıkış sayılır (stop-market kayması payı)
DENEME_SINIRI = 5                      # dolum geçmişi alınamazsa en çok bu kadar tur denenir; sonra boş alanlı satır yazılır


def satir_ekle(yol: Path, satir: dict) -> None:
    """Append-only: O_APPEND + flush + fsync. Hata YÜKSELİR (çağıran görünür uyarıya çevirir; sessiz yutulmaz)."""
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(satir, ensure_ascii=False, allow_nan=False, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def kapat_nedeni_cikar(mesaj: str) -> Optional[tuple]:
    """'canli_kapandi' olay metninden (borsa sembolü, neden)."""
    m = KAPAT_RE.match(mesaj)
    return (m.group(1), m.group(2)) if m else None


def cikis_sinifla(kapat_neden: Optional[str], cikis_fiyat: Optional[D], stop: Optional[D], hedef: Optional[D]) -> tuple:
    """-> (cikis_nedeni, ayrinti). Yürütücü kendi kapattıysa neden bilinir; borsada (stop/hedef emri) kapandıysa fiyat yakınlığından çıkarılır.
    Elle kapatma ayırt edilemez: 'bilinmiyor'."""
    if kapat_neden:
        n = kapat_neden.lower()
        if n in ("kill_switch", "hesap_kill"):
            return "kill", kapat_neden
        if n in ("stop_basarisiz", "risk_asimi", "risk_azalt"):
            return "sistem", kapat_neden
        if n == "stop_asildi" or ("stop" in n and "hedef" not in n):
            return "stop", kapat_neden
        if "hedef" in n or "target" in n:
            return "hedef", kapat_neden
        return "strateji", kapat_neden
    if cikis_fiyat is None:
        return "bilinmiyor", "çıkış fiyatı yok"
    uz = {}
    for ad, h in (("stop", stop), ("hedef", hedef)):
        if h and D(h) > 0:
            uz[ad] = abs(cikis_fiyat - D(h)) / D(h)
    if uz:
        ad = min(uz, key=lambda k: uz[k])
        if uz[ad] <= YAKIN_ORAN:
            return ad, f"borsa emri (fiyat {ad} seviyesine %{uz[ad] * 100:.3f} uzak)"
    return "bilinmiyor", "kapanış yürütücüden değil ve fiyat stop/hedefe yakın değil (elle olabilir)"


def _vwap(fills: list) -> Optional[D]:
    q = sum((f["miktar"] for f in fills), D(0))
    return sum((f["fiyat"] * f["miktar"] for f in fills), D(0)) / q if q > 0 else None


def yasam_dongusu(fills: list, yon: int, giris_emir_id: Optional[str], t0_ms: int) -> tuple:
    """Dolum listesinden bu pozisyonun (sıfırdan sıfıra) dolumları. -> (giris_dolumlari, cikis_dolumlari, tam_kapandi).
    Başlangıç: giriş emir kimliği biliniyorsa onun ilk dolumu, değilse t0'dan sonraki ilk giriş yönlü dolum. Sonra net miktar sıfıra dönene dek
    yürünür; sıfırdan sonraki dolumlar (aynı turda açılan sonraki pozisyon) dahil edilmez."""
    taraf = "BUY" if yon == 1 else "SELL"
    sirali = sorted(fills, key=lambda f: (f["zaman_ms"], f["id"]))
    bas = next((i for i, f in enumerate(sirali) if (f["emir_id"] == giris_emir_id if giris_emir_id else (f["yon"] == taraf and f["zaman_ms"] >= t0_ms))), None)
    if bas is None:
        return [], [], False
    net, girisler, cikislar = D(0), [], []
    for f in sirali[bas:]:
        isaret = 1 if f["yon"] == "BUY" else -1
        net += isaret * f["miktar"]
        (girisler if f["yon"] == taraf else cikislar).append(f)
        if net * yon <= 0:
            return girisler, cikislar, True
    return girisler, cikislar, False


def islem_satiri(kay: dict, fills: Optional[list], fills_neden: Optional[str], funding: Optional[D], funding_neden: Optional[str],
                 kapat_neden: Optional[str], cikis_zamani: str) -> Optional[dict]:
    """Saf hesap: kayıt + borsa dolumlarından `islemler.jsonl` satırı. fills None = dolum geçmişi alınamadı (alanlar null + neden).
    fills verilmiş ama giriş dolumu yok = giriş hiç dolmadı -> None (satır yazılmaz)."""
    yon = int(kay["yon"])
    notlar = list(kay.get("notlar", []))
    satir = {"sema": SEMA_ISLEM, "surum": 1, "zaman": cikis_zamani, "strateji": kay["strateji"], "kol": kay["kol"], "sembol": kay["bsembol"],
             "yon": "long" if yon == 1 else "short", "giris_zamani": kay.get("acilis_zaman"), "cikis_zamani": cikis_zamani,
             "stop_giris": kay.get("stop_giris"), "planlanan_risk_usd": kay.get("planlanan_risk_usd"), "niyet_id": kay.get("niyet_id"),
             "sinyal_zamani": kay.get("sinyal_zamani")}
    stop = D(kay["stop_giris"]) if kay.get("stop_giris") else None
    son_stop = D(kay["son_stop"]) if kay.get("son_stop") else stop
    hedef = D(kay["son_hedef"]) if kay.get("son_hedef") else None
    girisler = cikislar = []
    tam = False
    if fills is not None:
        girisler, cikislar, tam = yasam_dongusu(fills, yon, kay.get("giris_order_id"), int(kay.get("acilis_ms", 0)))
        if not girisler:
            return None
        if not tam:
            notlar.append("pozisyon dolum geçmişinde tam sıfırlanmamış görünüyor (kapanış dolumu eksik olabilir)")
    giris_px = _vwap(girisler) if girisler else (D(kay["giris_ort"]) if kay.get("giris_ort") else None)
    cikis_px = _vwap(cikislar) if cikislar else None
    miktar = sum((f["miktar"] for f in girisler), D(0)) if girisler else (D(kay["giris_qty"]) if kay.get("giris_qty") else None)
    satir.update(giris_fiyati=str(giris_px) if giris_px else None, cikis_fiyati=str(cikis_px) if cikis_px else None, miktar=str(miktar) if miktar else None)
    satir["stop_mesafesi_oran"] = float(abs(giris_px - stop) / giris_px) if (giris_px and stop) else None
    cikis, ayrinti = cikis_sinifla(kapat_neden, cikis_px, son_stop, hedef)
    satir.update(cikis_nedeni=cikis, cikis_ayrinti=ayrinti, kismi_cikis_sayisi=len(cikislar) if fills is not None else None)
    # --- komisyon / brüt / net
    komisyon = brut = None
    komisyon_neden = fills_neden
    if fills is not None:
        tum = girisler + cikislar
        yabanci = sorted({f["komisyon_varlik"] for f in tum if f["komisyon_varlik"] and f["komisyon_varlik"] not in STABIL and f["komisyon"] != 0})
        brut = sum((f["gercek_pnl"] for f in cikislar), D(0))
        if yabanci:
            komisyon_neden = f"komisyon USD cinsinden değil ({','.join(yabanci)}); dönüştürülmedi"
        else:
            komisyon, komisyon_neden = sum((f["komisyon"] for f in tum), D(0)), None
    satir.update(komisyon_usd=str(komisyon) if komisyon is not None else None, komisyon_neden=komisyon_neden,
                 funding_usd=str(funding) if funding is not None else None, funding_neden=None if funding is not None else funding_neden,
                 brut_pnl_usd=str(brut) if brut is not None else None)
    net = (brut - komisyon + (funding or D(0))) if (brut is not None and komisyon is not None) else None
    satir["net_pnl_usd"] = str(net) if net is not None else None
    satir["net_funding_dahil"] = funding is not None
    risk = D(kay["planlanan_risk_usd"]) if kay.get("planlanan_risk_usd") else None
    satir["r"] = float(net / risk) if (net is not None and risk and risk > 0) else None
    if satir["r"] is None:
        notlar.append("r hesaplanamadı: " + ("net PnL yok" if net is None else "planlanan risk kaydı yok"))
    # --- maliyet (model ile aynı kapsam) + giriş kayması
    taker, sk = D(kay.get("model_taker") or "0.0005"), D(kay.get("model_stop_kayma") or "0.0005")
    nominal = giris_px * miktar if (giris_px and miktar) else None
    model = (2 * taker + (sk if cikis == "stop" else 0)) * 10000
    cikis_kayma = (son_stop - cikis_px) * yon * miktar if (cikis == "stop" and cikis_px and son_stop and miktar) else D(0)
    satir["model_maliyet_bps"] = float(model)
    satir["gercek_maliyet_bps"] = float((komisyon + cikis_kayma) / nominal * 10000) if (komisyon is not None and nominal and cikis_px) else None
    ref = D(kay["mark_giris"]) if kay.get("mark_giris") else None
    satir["giris_kayma_bps"] = float((giris_px - ref) * yon / ref * 10000) if (giris_px and ref) else None
    satir["cikis_kayma_bps"] = float(cikis_kayma / nominal * 10000) if (nominal and cikis == "stop" and cikis_px) else None
    satir["veri_kaynagi"] = "userTrades" if fills is not None else "yok"
    satir["notlar"] = notlar
    return satir


@dataclass
class HesapKaydi:
    """calistir.py için: hesap toplamı + ortak zirve satırı (servis başlangıcında ve her UTC günü)."""
    yol: Path
    son_gun: Optional[str] = None

    def yaz(self, h: dict, simdi) -> bool:
        gun = str(simdi.date()) if hasattr(simdi, "date") else str(simdi)[:10]
        if self.son_gun == gun:
            return False
        satir_ekle(self.yol, {"tur": "hesap", "gun": gun, "zaman": simdi.isoformat() if hasattr(simdi, "isoformat") else str(simdi),
                              "neden": "servis_basi" if self.son_gun is None else "gun", "toplam": h.get("toplam"), "zirve": h.get("zirve"),
                              "kimlikler": h.get("kimlikler"), "kill": bool(h.get("kill"))})
        self.son_gun = gun
        return True
