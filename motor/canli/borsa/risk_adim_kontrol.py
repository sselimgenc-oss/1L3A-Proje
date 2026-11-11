"""15m risk artışı (6. hafta %2, 12. hafta %3) ŞARTLARININ salt-okunur raporu: `python -m motor.canli.borsa.risk_adim_kontrol --durum DIZIN`.

CANLI_PLAN.md: dört şartın HEPSİ tutarsa artış yapılabilir (kâr/zarar şart değil). Bu araç hiçbir şeyi DEĞİŞTİRMEZ ve artışı otomatik yapmaz:
operatör şartları görüp `stratejiler/canli_ayar.json` içindeki `islem_risk` değerini ELLE değiştirir.

Her strateji için dört şart, `evet` / `hayir` / `bilinmiyor` olarak (veri yoksa uydurma yok, `bilinmiyor`):
  1. sistem_hatasi_yok : DIZIN/olaylar.jsonl içinde bu stratejiye ait hata olayı (HATA_TURLERI) yok (--baslangic ile pencere)
  2. maliyet_orani_ok  : canlı kayma+komisyon <= modelin 1,5 katı
  3. eslesme_ok        : canlı işlemler paper ile >= %95 eşleşiyor
  4. kill_yok          : strateji ve hesap kill'i yok (DIZIN/canli/yurutucu_*.json, hesap_durumu.json)
2. ve 3. için canlı yürütücünün ölçüsü henüz durum dosyasına yazılmıyor: haftalık canlı-paper raporu DIZIN/canli/haftalik_karsilastirma.json
dosyasını şu biçimde yazarsa okunur (yoksa bilinmiyor):
  {"<strateji_id>": {"canli_maliyet_bps": 9.0, "model_maliyet_bps": 6.0, "eslesme_orani": 0.97}}
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

MALIYET_KAT, ESLESME_MIN = 1.5, 0.95
HATA_TURLERI = frozenset({
    "canli_yurutucu_hatasi", "canli_giris_blok", "canli_giris_hatasi", "canli_giris_belirsiz", "canli_stop_basarisiz", "canli_stop_hatasi",
    "canli_kapatma_hatasi", "canli_kill_hatasi", "canli_iptal_hatasi", "canli_risk_asimi", "canli_uyusmazlik", "kill_kapatilamadi",
})
EVET, HAYIR, BILINMIYOR = "evet", "hayir", "bilinmiyor"


def _json(yol: Path):
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _olaylar(yol: Path) -> Optional[list]:
    if not yol.exists():
        return None
    out = []
    try:
        for s in yol.read_text(encoding="utf-8").splitlines():
            if s.strip():
                out.append(json.loads(s))
    except (OSError, ValueError):
        return None
    return out


def _zaman_ok(z, baslangic: Optional[str]) -> bool:
    return baslangic is None or str(z) >= baslangic


def kontrol(dizin, baslangic: Optional[str] = None, stratejiler: Optional[list] = None) -> dict:
    """-> {strateji_id: {sistem_hatasi_yok, maliyet_orani_ok, eslesme_ok, kill_yok, hepsi}}; hiçbir dosyaya yazmaz."""
    dizin = Path(dizin)
    canli = dizin / "canli"
    durumlar = {}
    for y in sorted(canli.glob("yurutucu_*.json")):
        d = _json(y)
        if isinstance(d, dict) and d.get("strateji"):
            durumlar[d["strateji"]] = d
    hesap = _json(canli / "hesap_durumu.json")
    olaylar = _olaylar(dizin / "olaylar.jsonl")
    kars = _json(canli / "haftalik_karsilastirma.json")
    kars = kars if isinstance(kars, dict) else {}
    ids = sorted(set(durumlar) | set(stratejiler or []))
    out = {}
    for sid in ids:
        r = {}
        if olaylar is None:
            r["sistem_hatasi_yok"] = BILINMIYOR
        else:
            onek = f"[{sid}]"
            hata = [o for o in olaylar if o.get("tur") in HATA_TURLERI and str(o.get("mesaj", "")).startswith(onek) and _zaman_ok(o.get("zaman", ""), baslangic)]
            r["sistem_hatasi_yok"] = HAYIR if hata else EVET
        k = kars.get(sid) if isinstance(kars.get(sid), dict) else {}
        try:
            c, m = float(k["canli_maliyet_bps"]), float(k["model_maliyet_bps"])
            r["maliyet_orani_ok"] = EVET if c <= MALIYET_KAT * m else HAYIR
        except (KeyError, TypeError, ValueError):
            r["maliyet_orani_ok"] = BILINMIYOR
        try:
            r["eslesme_ok"] = EVET if float(k["eslesme_orani"]) >= ESLESME_MIN else HAYIR
        except (KeyError, TypeError, ValueError):
            r["eslesme_ok"] = BILINMIYOR
        d = durumlar.get(sid)
        if d is None:
            r["kill_yok"] = BILINMIYOR
        elif d.get("kill") or (isinstance(hesap, dict) and hesap.get("kill")):
            r["kill_yok"] = HAYIR
        else:
            r["kill_yok"] = EVET if hesap is not None else BILINMIYOR
        v = list(r.values())
        r["hepsi"] = HAYIR if HAYIR in v else (EVET if all(x == EVET for x in v) else BILINMIYOR)
        out[sid] = r
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="15m risk artışı şartlarını yazdırır (salt okunur; hiçbir şeyi değiştirmez).")
    ap.add_argument("--durum", required=True, help="canlı servis durum dizini")
    ap.add_argument("--baslangic", help="sistem hatası penceresi başı (ISO tarih, ör. 2026-12-15); verilmezse tüm olaylar")
    ap.add_argument("--ayar", help="yapılandırma dosyası (varsa o stratejiler de listelenir)")
    a = ap.parse_args(argv)
    ids = None
    if a.ayar:
        ids = [x["id"] for x in json.loads(Path(a.ayar).read_text(encoding="utf-8")).get("stratejiler", [])]
    sonuc = kontrol(a.durum, a.baslangic, ids)
    if not sonuc:
        print("strateji durumu bulunamadı:", a.durum)
        return 1
    print(f"{'strateji':28s} {'sistem_hatasi_yok':18s} {'maliyet<=1,5x':14s} {'eslesme>=%95':13s} {'kill_yok':9s} hepsi")
    for sid, r in sonuc.items():
        print(f"{sid:28s} {r['sistem_hatasi_yok']:18s} {r['maliyet_orani_ok']:14s} {r['eslesme_ok']:13s} {r['kill_yok']:9s} {r['hepsi']}")
    print("\nBu rapor yalnız bilgidir; risk artışı ELLE (canli_ayar.json islem_risk) yapılır. 'bilinmiyor' = veri yok: şart tutmuş sayılmaz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
