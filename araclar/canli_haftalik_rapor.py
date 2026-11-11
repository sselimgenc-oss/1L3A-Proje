"""Haftalık canlı rapor (SALT OKUNUR): `python -m araclar.canli_haftalik_rapor --canli-durum DIZIN [--paper-durum DIZIN] [--bitis TARIH] [--cikti DOSYA.md]`.

Borsaya bağlanmaz, emir vermez, hiçbir şeyi değiştirmez. YALNIZ canlı servisin ve paper servisinin diske yazdığı dosyaları okur:
  DIZIN/canli/yurutucu_*.json     strateji başına yürütücü durumu (zirve, kill, açık pozisyon kayıtları)
  DIZIN/canli/hesap_durumu.json   hesap toplamı: Σ min(borsa özsermayesi, tahsis) ve ortak zirve (açık pozisyon K/Z dahil: borsanın marj bakiyesi)
  DIZIN/canli/haftalik_karsilastirma.json  (varsa) {sid: {canli_maliyet_bps, model_maliyet_bps, eslesme_orani, islem_sayisi}}  (risk_adim_kontrol ile aynı sözleşme)
  DIZIN/canli/islemler.jsonl      (varsa) GERÇEK canlı kapanan işlemler (durum sözleşmesi biçimi, `r` alanı ile). BUGÜN YÜRÜTÜCÜ BUNU YAZMIYOR.
  DIZIN/olaylar.jsonl, islemler.jsonl, maliyet.json, saglik.json   canlı servisin İÇİNDEKİ paper motorunun çıktıları (niyetler; canlı dolum DEĞİL)
  --paper-durum DIZIN             bağımsız paper servisi (yalnız paper'daki stratejiler için bilgi)
  --ayar DOSYA                    (isteğe bağlı) canli_ayar.json: tahsis_usd ve islem_risk buradan okunur (yürütücü bunları durum dosyasına yazmıyor)
Yürütücünün yazmadığı alan raporda "veri yok (yürütücü yazmıyor)" diye görünür; uydurma yok.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from motor.canli.borsa.risk_adim_kontrol import HATA_TURLERI

# ============================================================================ SABİTLER
# Kaynak (hepsi): "1L3A v2 planı (2026-11-11, kullanıcı onaylı)". Eşik değiştirmek plan değişikliğidir: kullanıcıya sorulur.
BUYUME_FRENI_DUSUS = 0.10              # toplam canlı sermaye zirveden düşüş >= %10 -> büyüme freni (yeni kademe/para ekleme durur)
HEDEF_ASILDI_DUSUS = 0.15              # >= %15 -> hedef aşıldı
HESAP_KILL_DUSUS = 0.20                # -%20 hesap kill (kodda; burada yalnız bilgi satırı)
MALIYET_ORAN_UYARI = 1.5               # gerçek (kayma+komisyon) / model > 1,5 -> uyarı
E0V1EN_ILK_ISLEM = 30                  # e0v1en: ilk 30 işlemde maliyet oranı > 1,5 -> EMEKLİLİK ölçütü
ESLESME_HEDEF = 0.95                   # canlı-paper eşleşme hedefi
E0V1EN_PENCERE = 60                    # son 60 kapanan işlemin ΣR'si
E0V1EN_UYARI_R = -10.0                 # ΣR <= -10R -> UYARI
E0V1EN_EMEKLILIK_R = -15.0             # ΣR <= -15R -> EMEKLİLİK
EWO_BANT_ALT_R, EWO_BANT_UST_R = -7.0, 33.0     # ewo-ema-ofset 12 aylık beklenti bandı (R)
EWO_BANT_AY = 12
EWO_INCELEME_R = -15.0                 # kümülatif R <= -15R -> EMEKLİLİK İNCELEMESİ
EWO_BANT_USD_250 = (-26, 125)          # 250 USD tahsis ve %1,5 işlem riskinde yaklaşık USD karşılığı (plan metni)
HAFTA_GUN = 7
OLAY_KAYIT_SINIRI = 50                 # olaylar.jsonl yalnız SON 50 olayı tutar (DURUM_SOZLESMESI.md)
S_E0V1EN, S_EWO = "dis__e0v1en", "dis__ewo-ema-ofset"
YOK = "veri yok (yürütücü yazmıyor)"
KAYNAK_MALIYET = ("paper motorunun maliyet modeli (motor/portfoy/motor.py: taker ücreti + kayma/stop kayması; "
                  "paper maliyet.json ya da haftalik_karsilastirma.json model_maliyet_bps)")
# ============================================================================


def _zaman(s) -> Optional[datetime]:
    if s in (None, ""):
        return None
    d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


class Okuyucu:
    """Dosya okuyucu: yok = None (rapor 'veri yok' der); bozuk dosya = okuma_hatalari listesine AÇIK kayıt (rapora basılır)."""

    def __init__(self):
        self.hatalar: list = []

    def json(self, yol: Path):
        if not yol.exists():
            return None
        try:
            return json.loads(yol.read_text(encoding="utf-8"))
        except ValueError as e:
            self.hatalar.append(f"{yol}: bozuk JSON ({e})")
            return None

    def jsonl(self, yol: Path) -> Optional[list]:
        if not yol.exists():
            return None
        out = []
        for no, s in enumerate(yol.read_text(encoding="utf-8").splitlines(), 1):
            if not s.strip():
                continue
            try:
                out.append(json.loads(s))
            except ValueError as e:
                self.hatalar.append(f"{yol} satır {no}: bozuk JSON ({e})")
        return out


def _kimlik_sid(kimlik: str) -> str:
    return str(kimlik).split("|")[0]


def _r_listesi(islemler: Optional[list], sid: str) -> list:
    """[(cikis_zamani, r|None)] çıkış sırasıyla."""
    out = [(_zaman(x.get("cikis_zamani") or x.get("zaman")), x.get("r")) for x in (islemler or []) if _kimlik_sid(x.get("kimlik", "")) == sid]
    return sorted(out, key=lambda t: (t[0] is None, t[0]))


def son_n_r(liste: list, n: int) -> dict:
    """Son n kapanan işlemin ΣR'si. -> {islem, sayi_r, toplam_r (n kadar değilse de mevcut), yeterli}"""
    son = liste[-n:]
    rler = [float(r) for _, r in son if r is not None]
    return {"islem": len(liste), "pencere": len(son), "r_olan": len(rler), "toplam_r": round(sum(rler), 4), "yeterli": len(liste) >= n and len(rler) == len(son)}


def r_durum_e0v1en(o: dict) -> str:
    if o["pencere"] == 0:
        return "veri yok (kapanan işlem yok)"
    if not o["yeterli"]:
        return f"yetersiz örnek ({o['islem']}/{E0V1EN_PENCERE} işlem); mevcut ΣR {o['toplam_r']:+.2f}R"
    if o["toplam_r"] <= E0V1EN_EMEKLILIK_R:
        return f"EMEKLİLİK (son {E0V1EN_PENCERE} işlem ΣR {o['toplam_r']:+.2f}R <= {E0V1EN_EMEKLILIK_R:g}R)"
    if o["toplam_r"] <= E0V1EN_UYARI_R:
        return f"UYARI (son {E0V1EN_PENCERE} işlem ΣR {o['toplam_r']:+.2f}R <= {E0V1EN_UYARI_R:g}R)"
    return f"normal (son {E0V1EN_PENCERE} işlem ΣR {o['toplam_r']:+.2f}R)"


def ewo_konum(kum_r: float, gecen_gun: Optional[float]) -> dict:
    """12 aylık bandın geçen süreye orantılı karşılığı (YALNIZ bilgi) ve kümülatif R'nin bandaki yeri."""
    out = {"kumulatif_r": round(kum_r, 4), "bant_12ay_r": [EWO_BANT_ALT_R, EWO_BANT_UST_R], "bant_12ay_usd_250": list(EWO_BANT_USD_250)}
    if gecen_gun is None:
        out.update(sure_orani=None, orantili_bant_r=None, konum="süre bilinmiyor (--baslangic girilmedi, işlem tarihi yok)")
    else:
        oran = min(max(gecen_gun / (EWO_BANT_AY * 30.4375), 0.0), 1.0)
        alt, ust = EWO_BANT_ALT_R * oran, EWO_BANT_UST_R * oran
        konum = "bandın altında" if kum_r < alt else ("bandın üstünde" if kum_r > ust else "bant içinde")
        out.update(sure_orani=round(oran, 4), orantili_bant_r=[round(alt, 2), round(ust, 2)], konum=konum)
    out["inceleme"] = kum_r <= EWO_INCELEME_R
    return out


def dusus_durumu(zirve: float, toplam: float, kill: bool) -> dict:
    d = (zirve - toplam) / zirve if zirve > 0 else 0.0
    d = max(d, 0.0)
    mesajlar = []
    if d >= HEDEF_ASILDI_DUSUS:
        mesajlar.append("HEDEF AŞILDI (düşüş >= %15)")
    if d >= BUYUME_FRENI_DUSUS:
        mesajlar.append("BÜYÜME FRENİ: yeni kademe/para ekleme durur, kullanıcı gözden geçirir")
    if kill:
        mesajlar.append(f"HESAP KILL TETİKLENMİŞ (-%{HESAP_KILL_DUSUS * 100:g}; kalıcı, elle sıfırlama)")
    return {"guncel_dusus": round(d, 6), "mesajlar": mesajlar}


def maliyet_durumu(sid: str, k: dict, islem_sayisi: Optional[int]) -> dict:
    out = {"canli_bps": None, "model_bps": None, "oran": None, "durum": YOK, "islem_sayisi": islem_sayisi}
    try:
        c, m = float(k["canli_maliyet_bps"]), float(k["model_maliyet_bps"])
    except (KeyError, TypeError, ValueError):
        return out
    if m <= 0:
        out["durum"] = "model maliyeti 0: oran hesaplanamaz"
        return out
    oran = c / m
    out.update(canli_bps=c, model_bps=m, oran=round(oran, 4))
    out["durum"] = f"oran {oran:.2f}" + (f" > {MALIYET_ORAN_UYARI:g}: UYARI" if oran > MALIYET_ORAN_UYARI else " (uyarı yok)")
    if sid == S_E0V1EN:
        if islem_sayisi is None:
            out["emeklilik"] = "ilk 30 işlem ölçütü: işlem sayısı bilinmiyor"
        elif islem_sayisi < E0V1EN_ILK_ISLEM:
            out["emeklilik"] = f"ilk {E0V1EN_ILK_ISLEM} işlem ölçütü: henüz {islem_sayisi}/{E0V1EN_ILK_ISLEM} işlem" + (" (oran şimdiden > 1,5: dikkat)" if oran > MALIYET_ORAN_UYARI else "")
        else:
            out["emeklilik"] = (f"EMEKLİLİK ölçütü: ilk {E0V1EN_ILK_ISLEM} işlemde oran {oran:.2f} > {MALIYET_ORAN_UYARI:g}" if oran > MALIYET_ORAN_UYARI
                                else f"ilk {E0V1EN_ILK_ISLEM} işlem ölçütü geçildi (oran {oran:.2f})")
    return out


_ATLANAN_TURLER = ("canli_giris_atlandi", "min_tutar_alti", "canli_giris_hatasi", "canli_giris_blok")


def _atlama_nedeni(tur: str, mesaj: str) -> str:
    if tur == "min_tutar_alti":
        return "min tutar (borsa asgari emri)"
    if tur == "canli_giris_blok":
        return "art arda yürütücü hatası (giriş blok)"
    if tur == "canli_giris_hatasi":
        return "giriş emri hatası/dolmadı"
    m = mesaj.lower()
    for anahtar, ad in (("günlük kayıp", "günlük kayıp limiti"), ("sinyal barı", "gecikme (eski sinyal)"), ("zaten pozisyon", "borsada zaten pozisyon"),
                        ("risk_butcesi_dolu", "risk tavanı (toplam risk/brüt dolu)"), ("stop_cok_uzak", "stop çok uzak"), ("gecersiz_stop", "geçersiz stop"),
                        ("kasa_yok", "kasa yok")):
        if anahtar in m:
            return ad
    return "diğer: " + mesaj.split("]", 1)[-1].strip()[:70]


def eslesme_olaylardan(olaylar: Optional[list], sid: str, bas: datetime, bit: datetime) -> dict:
    """Her paper niyeti canlıda ya 'canli_emir_doldu' ya da bir atlama/hata olayı üretir. Olay kaydı yalnız SON 50 olay: pencere tam kapsanmıyorsa 'veri yok'."""
    out = {"doldu": None, "atlanan": None, "oran": None, "nedenler": {}, "aciklama": YOK}
    if olaylar is None:
        out["aciklama"] = "olaylar.jsonl yok"
        return out
    onek = f"[{sid}]"
    ilk = _zaman(olaylar[0]["zaman"]) if olaylar else None
    kesik = len(olaylar) >= OLAY_KAYIT_SINIRI and (ilk is None or ilk > bas)
    if kesik:
        out["aciklama"] = f"olaylar.jsonl yalnız son {OLAY_KAYIT_SINIRI} olayı tutar; pencere başı ({bas.date()}) kapsanmıyor: veri yok (yürütücü yazmıyor)"
        return out
    doldu, atl = 0, {}
    for o in olaylar:
        z = _zaman(o.get("zaman"))
        if z is None or not (bas < z <= bit) or not str(o.get("mesaj", "")).startswith(onek):
            continue
        if o.get("tur") == "canli_emir_doldu":
            doldu += 1
        elif o.get("tur") in _ATLANAN_TURLER:
            n = _atlama_nedeni(o["tur"], str(o.get("mesaj", "")))
            atl[n] = atl.get(n, 0) + 1
    top = doldu + sum(atl.values())
    out.update(doldu=doldu, atlanan=sum(atl.values()), nedenler=atl, aciklama="olaylardan (yalnız bu pencere)")
    out["oran"] = round(doldu / top, 4) if top else None
    return out


def sistem_sagligi(sid: str, durum: Optional[dict], olaylar: Optional[list], bas: datetime, bit: datetime) -> dict:
    out = {"stopsuz_pozisyon": None, "belirsiz_giris": None, "acik_kayit": None, "kill": None, "gun_blok": None,
           "hata_olaylari": None, "uyusmazlik_olaylari": None, "yeniden_baslatma": None}
    if durum is not None:
        pozlar = durum.get("pozlar", {})
        out.update(acik_kayit=len(pozlar), stopsuz_pozisyon=sum(1 for p in pozlar.values() if p.get("durum") == "acik" and not p.get("stop_id")),
                   belirsiz_giris=sum(1 for p in pozlar.values() if p.get("durum") == "gonderildi"), kill=bool(durum.get("kill")), gun_blok=bool(durum.get("gun_blok")))
    if olaylar is not None:
        onek = f"[{sid}]"
        sec = [o for o in olaylar if (z := _zaman(o.get("zaman"))) is not None and bas < z <= bit and str(o.get("mesaj", "")).startswith(onek)]
        hata: dict = {}
        for o in sec:
            if o.get("tur") in HATA_TURLERI:
                hata[o["tur"]] = hata.get(o["tur"], 0) + 1
        out.update(hata_olaylari=hata, uyusmazlik_olaylari=sum(1 for o in sec if o.get("tur") == "canli_uyusmazlik"))
    return out


def rapor_uret(canli_durum, paper_durum=None, bitis: Optional[str] = None, ayar: Optional[str] = None, baslangic: Optional[str] = None,
               sunucu_gider_usd_ay: Optional[float] = None) -> dict:
    ok = Okuyucu()
    dizin = Path(canli_durum)
    canli = dizin / "canli"
    bit = (_zaman(bitis) + timedelta(days=1)) if bitis else datetime.now(timezone.utc)   # tarih verilirse o günün sonu
    bas = bit - timedelta(days=HAFTA_GUN)
    baslangic_z = _zaman(baslangic) if baslangic else None

    # --- dosyalar
    durumlar = {}
    for y in sorted(canli.glob("yurutucu_*.json")):
        d = ok.json(y)
        if isinstance(d, dict) and d.get("strateji"):
            durumlar[d["strateji"]] = d
    hesap = ok.json(canli / "hesap_durumu.json")
    kars = ok.json(canli / "haftalik_karsilastirma.json")
    kars = kars if isinstance(kars, dict) else {}
    canli_isl = ok.jsonl(canli / "islemler.jsonl")           # GERÇEK canlı işlemler (bugün yazılmıyor)
    olaylar = ok.jsonl(dizin / "olaylar.jsonl")
    paper_ic_isl = ok.jsonl(dizin / "islemler.jsonl")        # gömülü paper motoru (niyet) işlemleri: VEKİL
    mal = ok.json(dizin / "maliyet.json")
    saglik = ok.json(dizin / "saglik.json")
    ayar_d = ok.json(Path(ayar)) if ayar else None
    tahsis, islem_risk = {}, {}
    for s in (ayar_d or {}).get("stratejiler", []):
        tahsis[s["id"]] = Decimal(str(s["tahsis_usd"]))
        islem_risk[s["id"]] = Decimal(str(s.get("islem_risk", "0.015")))
    hesap_ids = set(hesap.get("kimlikler") or []) if isinstance(hesap, dict) else set()
    ids = sorted(set(durumlar) | set(tahsis) | set(kars) | hesap_ids | ({_kimlik_sid(x.get("kimlik", "")) for x in canli_isl} if canli_isl else set()))

    uyarilar: list = []
    eksik: list = []

    # --- 1-2. toplam ve düşüş
    toplam = {"baslangic_tahsis": None, "guncel_ozsermaye": None, "net_usd": None, "net_pct": None, "zirve": None, "dusus": None,
              "en_buyuk_dusus": YOK, "acik_pozisyon_dahil": None}
    if tahsis:
        toplam["baslangic_tahsis"] = float(sum(tahsis.values()))
    else:
        eksik.append("tahsis: --ayar verilmedi (yürütücü tahsisi durum dosyasına yazmıyor)")
    if isinstance(hesap, dict) and hesap.get("toplam") is not None:
        t = float(hesap["toplam"])
        toplam["guncel_ozsermaye"] = t
        z = float(hesap["zirve"]) if hesap.get("zirve") is not None else t
        toplam.update(zirve=z, acik_pozisyon_dahil=True, hesap_zaman=hesap.get("yazildi_zaman") or hesap.get("zaman"))
        if toplam["baslangic_tahsis"]:
            toplam["net_usd"] = round(t - toplam["baslangic_tahsis"], 2)
            toplam["net_pct"] = round(toplam["net_usd"] / toplam["baslangic_tahsis"], 6)
        dd = dusus_durumu(z, t, bool(hesap.get("kill")))
        toplam["dusus"] = dd
        uyarilar += dd["mesajlar"]
        if hesap.get("kimlikler") and tahsis and sorted(tahsis) != sorted(hesap["kimlikler"]):
            uyarilar.append(f"hesap_durumu.json kimlikleri ({hesap['kimlikler']}) ayar ({sorted(tahsis)}) ile farklı: toplam/zirve bu kadroya göre değil")
    else:
        eksik.append("canli/hesap_durumu.json yok ya da toplam yok: özsermaye/düşüş hesaplanamadı")
    toplam["en_buyuk_dusus_not"] = ("yürütücü en büyük düşüşü yazmıyor (yalnız ortak zirve ve güncel toplam); 'güncel düşüş' açık pozisyonları DAHİL eder (borsa marj bakiyesi). "
                                    "Dönemin en büyük düşüşü için haftalık raporların zirve/toplam değerleri birleştirilmeli.")
    sg = None
    if sunucu_gider_usd_ay is not None:
        sg = {"usd_ay": sunucu_gider_usd_ay, "not": "net sonuca DÜŞÜLMEDİ; ayrı satır"}
        if baslangic_z:
            sg["donem_usd"] = round(sunucu_gider_usd_ay * max((bit - baslangic_z).days, 0) / 30.4375, 2)
    toplam["sunucu_gideri"] = sg

    # --- süre
    ilk_islem = min([t for t, _ in _r_listesi(canli_isl, S_EWO) + _r_listesi(paper_ic_isl, S_EWO) if t], default=None)
    sure_bas = baslangic_z or ilk_islem
    gecen_gun = (bit - sure_bas).total_seconds() / 86400 if sure_bas else None

    # --- strateji bazında
    strat = {}
    for sid in ids:
        canli_r = _r_listesi(canli_isl, sid) if canli_isl is not None else None
        vekil_r = _r_listesi(paper_ic_isl, sid) if paper_ic_isl is not None else None
        n_canli = len(canli_r) if canli_r is not None else None
        if n_canli is None and isinstance(kars.get(sid), dict) and isinstance(kars[sid].get("islem_sayisi"), int):
            n_canli = kars[sid]["islem_sayisi"]
        s = {"tahsis_usd": float(tahsis[sid]) if sid in tahsis else None, "islem_risk": float(islem_risk[sid]) if sid in islem_risk else None,
             "guncel_kasa": YOK, "net_sonuc": YOK, "canli_islem_sayisi": n_canli}
        k = kars.get(sid) if isinstance(kars.get(sid), dict) else {}
        s["maliyet"] = maliyet_durumu(sid, k, n_canli)
        if mal and isinstance(mal.get("stratejiler", {}).get(sid), dict):
            t = mal["stratejiler"][sid]["tum"]
            s["maliyet"]["paper_model_usd"] = {"ucret": t["ucret"], "kayma": t["kayma"], "funding": t["funding"]}
        s["maliyet"]["model_kaynagi"] = KAYNAK_MALIYET
        if s["maliyet"]["oran"] is not None and s["maliyet"]["oran"] > MALIYET_ORAN_UYARI:
            uyarilar.append(f"{sid}: maliyet oranı {s['maliyet']['oran']:.2f} > {MALIYET_ORAN_UYARI:g}")
        if s["maliyet"].get("emeklilik", "").startswith("EMEKLİLİK"):
            uyarilar.append(f"{sid}: {s['maliyet']['emeklilik']}")
        # eşleşme
        es = eslesme_olaylardan(olaylar, sid, bas, bit)
        if isinstance(k, dict) and k.get("eslesme_orani") is not None:
            es.update(oran=float(k["eslesme_orani"]), aciklama="haftalik_karsilastirma.json")
        es["hedef"] = ESLESME_HEDEF
        es["durum"] = YOK if es["oran"] is None else ("hedefte" if es["oran"] >= ESLESME_HEDEF else f"HEDEF ALTINDA (< %{ESLESME_HEDEF * 100:g})")
        if es["durum"].startswith("HEDEF ALTINDA"):
            uyarilar.append(f"{sid}: canlı-paper eşleşme %{es['oran'] * 100:.1f} < %{ESLESME_HEDEF * 100:g}")
        s["eslesme"] = es
        s["saglik"] = sistem_sagligi(sid, durumlar.get(sid), olaylar, bas, bit)
        if s["saglik"]["stopsuz_pozisyon"]:
            uyarilar.append(f"{sid}: {s['saglik']['stopsuz_pozisyon']} STOPSUZ pozisyon kaydı")
        # R kuralları (canlı R yoksa 'veri yok'; vekil yalnız bilgi)
        if sid in (S_E0V1EN, S_EWO):
            kaynak_r = canli_r
            vekil = son_n_r(vekil_r, E0V1EN_PENCERE) if vekil_r else None
            if sid == S_E0V1EN:
                if kaynak_r is None:
                    s["emeklilik_kurali"] = {"durum": YOK, "vekil_paper": vekil, "vekil_durum": r_durum_e0v1en(vekil) if vekil else None}
                else:
                    o = son_n_r(kaynak_r, E0V1EN_PENCERE)
                    s["emeklilik_kurali"] = {**o, "durum": r_durum_e0v1en(o), "kaynak": "canlı kapanan işlemler"}
                    if o["yeterli"] and o["toplam_r"] <= E0V1EN_UYARI_R:
                        uyarilar.append(f"{sid}: {s['emeklilik_kurali']['durum']}")
            else:
                if kaynak_r is None:
                    s["ewo_bant"] = {"durum": YOK, "vekil_paper_kumulatif_r": round(sum(float(r) for _, r in (vekil_r or []) if r is not None), 4) if vekil_r else None}
                else:
                    kum = sum(float(r) for _, r in kaynak_r if r is not None)
                    s["ewo_bant"] = {**ewo_konum(kum, gecen_gun), "kaynak": "canlı kapanan işlemler", "r_olmayan": sum(1 for _, r in kaynak_r if r is None)}
                    if s["ewo_bant"]["inceleme"]:
                        uyarilar.append(f"{sid}: EMEKLİLİK İNCELEMESİ (kümülatif {kum:+.2f}R <= {EWO_INCELEME_R:g}R)")
                    if sid in tahsis and sid in islem_risk:
                        s["ewo_bant"]["r_basina_usd"] = float(tahsis[sid] * islem_risk[sid])
        strat[sid] = s

    # --- paper'a özel stratejiler
    paper = {}
    if paper_durum:
        pd_ = Path(paper_durum)
        pisl = ok.jsonl(pd_ / "islemler.jsonl")
        if pisl is None:
            eksik.append(f"{pd_}/islemler.jsonl yok: paper bilgisi yok")
        else:
            for sid in sorted({_kimlik_sid(x.get("kimlik", "")) for x in pisl}):
                if sid in strat:
                    continue
                lst = _r_listesi(pisl, sid)
                hafta = [r for t, r in lst if t and bas < t <= bit and r is not None]
                paper[sid] = {"islem": len(lst), "toplam_r": round(sum(float(r) for _, r in lst if r is not None), 4),
                              "hafta_islem": len(hafta), "hafta_r": round(sum(float(r) for r in hafta), 4)}

    # --- sistem düzeyi
    sistem = {"saglik_durum": saglik.get("durum") if isinstance(saglik, dict) else None, "saglik_uyari_sayisi": len(saglik.get("uyarilar", [])) if isinstance(saglik, dict) else None,
              "yeniden_baslatma_haftada": None, "olay_kaydi_kesik": None}
    if olaylar is not None:
        sistem["yeniden_baslatma_haftada"] = sum(1 for o in olaylar if o.get("tur") == "yeniden_baslatma" and (z := _zaman(o.get("zaman"))) is not None and bas < z <= bit)
        ilk = _zaman(olaylar[0]["zaman"]) if olaylar else None
        sistem["olay_kaydi_kesik"] = len(olaylar) >= OLAY_KAYIT_SINIRI and (ilk is None or ilk > bas)
    else:
        eksik.append("olaylar.jsonl yok: hata/yeniden başlatma/atlanan sinyal sayıları yok")
    if saglik is None:
        eksik.append("saglik.json yok")
    stopsuz_top = sum(s["saglik"]["stopsuz_pozisyon"] or 0 for s in strat.values())
    sistem["stopsuz_toplam"] = stopsuz_top

    # --- yürütücünün yazmadığı alanlar (sabit liste; rapor her seferinde basar)
    yazilmayan = []
    if canli_isl is None:
        yazilmayan += ["canlı kapanan işlem kaydı (R, giriş/çıkış fiyatı, net PnL): canli/islemler.jsonl yok",
                       "gerçek dolum kayması ve komisyon (canlı maliyet bps): haftalik_karsilastirma.json yok",
                       "strateji başına güncel kasa/net sonuç (yalnız hesap toplamı yazılıyor)",
                       "gerçek funding ödemesi"]
    if not kars:
        yazilmayan.append("canlı-paper eşleşme oranı (haftalik_karsilastirma.json yok; yalnız olaylar.jsonl'den, son 50 olay sınırıyla)")
    yazilmayan.append("dönemin en büyük düşüşü (yalnız güncel zirve ve toplam yazılıyor)")
    yazilmayan.append("tahsis/işlem riski (durum dosyasında yok; --ayar ile canli_ayar.json'dan okunur)")

    return {"sema": "1l3a.canli_haftalik_rapor", "surum": 1, "donem": {"bas": bas.isoformat(), "bit": bit.isoformat(), "kumulatif_baslangic": sure_bas.isoformat() if sure_bas else None},
            "toplam": toplam, "stratejiler": strat, "paper_stratejileri": paper, "sistem": sistem, "uyarilar": uyarilar, "yazilmayan_alanlar": yazilmayan,
            "eksik_dosyalar": eksik, "okuma_hatalari": ok.hatalar}


# ---------------------------------------------------------------------------- markdown
def _p(x, nd=2):
    return YOK if x is None else f"{x:,.{nd}f}"


def markdown(r: dict) -> str:
    t, L = r["toplam"], []
    L += ["# Haftalık canlı rapor", "", f"Dönem: {r['donem']['bas'][:10]} → {r['donem']['bit'][:10]} (son 7 gün). Salt okunur; borsaya bağlanmadı.", ""]
    L += ["## Özet uyarılar"] + ([f"- {u}" for u in r["uyarilar"]] or ["- Uyarı yok."]) + [""]
    L += ["## 1. Dönem ve toplam",
          f"- Başlangıç tahsisi: {_p(t['baslangic_tahsis'])} USD" + ("" if t["baslangic_tahsis"] else " (--ayar verilmedi)"),
          f"- Güncel özsermaye (Σ min(özsermaye, tahsis)): {_p(t['guncel_ozsermaye'])} USD",
          f"- Net sonuç (komisyon ve funding düşülmüş; borsa bakiyesi): {_p(t['net_usd'])} USD" + (f" ({t['net_pct'] * 100:+.2f}%)" if t["net_pct"] is not None else "")]
    sg = t["sunucu_gideri"]
    L += [f"- Sunucu gideri (ayrı satır, net sonuca dahil değil): " + ("girilmedi" if sg is None else f"{sg['usd_ay']:g} USD/ay" + (f", dönem ≈ {sg['donem_usd']:g} USD" if "donem_usd" in sg else "")), ""]
    L += ["## 2. Düşüş"]
    if t["dusus"]:
        L += [f"- Zirve: {_p(t['zirve'])} USD; güncel düşüş: %{t['dusus']['guncel_dusus'] * 100:.2f} (açık pozisyon K/Z dahil)",
              f"- En büyük düşüş: {t['en_buyuk_dusus']}"]
        L += [f"- **{m}**" for m in t["dusus"]["mesajlar"]] or ["- Eşik uyarısı yok (büyüme freni %10, hedef aşıldı %15, hesap kill %20)."]
    else:
        L += [f"- {YOK}"]
    L += [f"- Not: {t['en_buyuk_dusus_not']}", ""]
    L += ["## 3. Maliyet (gerçek kayma+komisyon / model)", f"Model kaynağı: {KAYNAK_MALIYET}", ""]
    for sid, s in r["stratejiler"].items():
        m = s["maliyet"]
        L.append(f"- {sid}: {m['durum']}" + (f" (canlı {m['canli_bps']:g} bps, model {m['model_bps']:g} bps)" if m["oran"] is not None else ""))
        if "emeklilik" in m:
            L.append(f"  - {m['emeklilik']}")
        if "paper_model_usd" in m:
            pm = m["paper_model_usd"]
            L.append(f"  - paper modeli toplamı (bilgi): ücret {pm['ucret']}, kayma {pm['kayma']}, funding {pm['funding']} USD")
    L.append("")
    L += ["## 4. Canlı–paper eşleşmesi (hedef ≥ %95)"]
    for sid, s in r["stratejiler"].items():
        e = s["eslesme"]
        L.append(f"- {sid}: " + (f"%{e['oran'] * 100:.1f} ({e['durum']})" if e["oran"] is not None else e["durum"]) + f" — {e['aciklama']}")
        if e["doldu"] is not None:
            L.append(f"  - dolan {e['doldu']}, atlanan {e['atlanan']}" + (": " + ", ".join(f"{k} {v}" for k, v in e["nedenler"].items()) if e["nedenler"] else ""))
    L.append("")
    L += ["## 5. e0v1en emeklilik kuralı (son 60 işlem ΣR; ≤ −10R uyarı, ≤ −15R emeklilik)"]
    s = r["stratejiler"].get(S_E0V1EN)
    if s is None:
        L.append("- e0v1en kayıtlı değil.")
    else:
        e = s["emeklilik_kurali"]
        L.append(f"- {e['durum']}")
        if e.get("vekil_paper"):
            L.append(f"  - vekil (gömülü paper motoru, CANLI DEĞİL; yalnız bilgi): {e['vekil_durum']}")
    L.append("")
    L += ["## 6. ewo beklenti bandı (12 ay: −7R … +33R, 250 USD'de ≈ −26 … +125 USD; yalnız bilgi)"]
    s = r["stratejiler"].get(S_EWO)
    if s is None:
        L.append("- ewo-ema-ofset kayıtlı değil.")
    else:
        b = s["ewo_bant"]
        if b.get("durum") == YOK:
            L.append(f"- {YOK}" + (f"; vekil (gömülü paper, canlı değil): kümülatif {b['vekil_paper_kumulatif_r']:+.2f}R" if b.get("vekil_paper_kumulatif_r") is not None else ""))
        else:
            L.append(f"- Kümülatif {b['kumulatif_r']:+.2f}R; konum: {b['konum']}" + (f" (süre oranı {b['sure_orani'] * 100:.0f}%, orantılı bant {b['orantili_bant_r'][0]:+g} … {b['orantili_bant_r'][1]:+g}R)" if b["sure_orani"] is not None else ""))
            if b["inceleme"]:
                L.append(f"- **EMEKLİLİK İNCELEMESİ** (≤ {EWO_INCELEME_R:g}R)")
    L.append("")
    L += ["## 7. Sistem sağlığı", f"- Stopsuz pozisyon (toplam): {r['sistem']['stopsuz_toplam']}",
          f"- Yeniden başlatma (hafta): {_p(r['sistem']['yeniden_baslatma_haftada'], 0)}", f"- Servis sağlık durumu: {r['sistem']['saglik_durum'] or YOK}"]
    if r["sistem"]["olay_kaydi_kesik"]:
        L.append(f"- Dikkat: olaylar.jsonl yalnız son {OLAY_KAYIT_SINIRI} olayı tutar; hafta tam kapsanmıyor, aşağıdaki olay sayıları EKSİK olabilir.")
    for sid, s in r["stratejiler"].items():
        h = s["saglik"]
        L.append(f"- {sid}: açık kayıt {_p(h['acik_kayit'], 0)}, stopsuz {_p(h['stopsuz_pozisyon'], 0)}, belirsiz giriş {_p(h['belirsiz_giris'], 0)}, kill {h['kill']}, "
                 f"günlük blok {h['gun_blok']}, mutabakat/uyuşmazlık olayı {_p(h['uyusmazlik_olaylari'], 0)}, hata olayı {h['hata_olaylari'] if h['hata_olaylari'] is not None else YOK}")
    L.append("")
    if r["paper_stratejileri"]:
        L += ["## Yalnız paper'daki stratejiler (canlı değil)"]
        L += [f"- {sid}: {p['islem']} işlem, ΣR {p['toplam_r']:+.2f}; bu hafta {p['hafta_islem']} işlem, {p['hafta_r']:+.2f}R" for sid, p in r["paper_stratejileri"].items()]
        L.append("")
    L += ["## Yürütücünün yazmadığı / eksik alanlar"] + [f"- {x}" for x in r["yazilmayan_alanlar"]]
    L += [f"- (eksik dosya) {x}" for x in r["eksik_dosyalar"]] + [f"- (okuma hatası) {x}" for x in r["okuma_hatalari"]]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Haftalık canlı rapor (salt okunur; borsaya bağlanmaz, emir vermez).")
    ap.add_argument("--canli-durum", required=True, help="canlı servis durum dizini")
    ap.add_argument("--paper-durum", help="bağımsız paper servisi durum dizini")
    ap.add_argument("--bitis", help="dönem sonu (YYYY-MM-DD, o günün sonu dahil); verilmezse şimdi")
    ap.add_argument("--baslangic", help="canlı başlangıç tarihi (YYYY-MM-DD): ewo beklenti bandı süre oranı için")
    ap.add_argument("--ayar", help="canli_ayar.json (tahsis_usd, islem_risk)")
    ap.add_argument("--sunucu-gider-usd-ay", type=float, help="aylık sunucu gideri (USD); verilmezse 'girilmedi'")
    ap.add_argument("--cikti", help="markdown çıktı dosyası; aynı adla .json da yazılır. Yoksa ekrana basılır")
    a = ap.parse_args(argv)
    r = rapor_uret(a.canli_durum, a.paper_durum, a.bitis, a.ayar, a.baslangic, a.sunucu_gider_usd_ay)
    md = markdown(r)
    if a.cikti:
        yol = Path(a.cikti)
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(md, encoding="utf-8")
        yol.with_suffix(".json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"yazıldı: {yol} ve {yol.with_suffix('.json')}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
