"""Yoğunlaşma (pano öncelik 5d): varlık sınıfı ve sembol bazında açık risk ile brüt maruziyet payı. Hesap BURADA (motor tarafı); pano yalnız biçimler.

Girdi: motorun açık pozisyon listesi (`maruziyet.pozisyonlar`: nominal, stop_riski, yon, kimlik) ve özsermaye. Sınıf: `paper_takvim.tur` (kripto | hisse | emtia).
  brut_oran      = sembol (sınıf) brüt nominali ÷ özsermaye        brut_pay       = brüt nominal ÷ toplam brüt nominal
  stop_riski_oran = stopa kadar açık risk ÷ özsermaye               stop_riski_pay = açık risk ÷ toplam açık risk
  hhi_brut       = Σ brut_pay² (Herfindahl; 1/hhi = "etkin sembol sayısı"), yalnız bilgi.
EŞİK: projede sembol/sınıf bazında tanımlı BİR YOĞUNLAŞMA EŞİĞİ YOKTUR. Tanımlı olanlar yalnız TOPLAM düzeydedir (SERT_LIMITLER: toplam açık stop riski ≤ %5,
kaldıraç ≤ 3x; bunlar risk bloğunda zaten izlenir). Bu yüzden `esikler` null, `uyarilar` boştur: eşik uydurulmaz; eşik kullanıcı kararıyla tanımlanırsa
buraya eklenir (DURUM.md'ye karar yazılarak). Eski panonun ≥3 hesap / >1.000 $ kuralı 10 bin dolarlık eski hesaba göreydi, alınmadı.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from motor.canli import durum as d
from motor.canli import paper_takvim as tk

SINIF_ADI = {"kripto": "Kripto", "hisse": "ABD hissesi", "emtia": "Emtia"}
ESIK_NEDENI = ("Projede sembol/sınıf bazında tanımlı yoğunlaşma eşiği yok (yalnız toplam düzeyde SERT_LIMITLER: açık stop riski ≤ %5, kaldıraç ≤ 3x). "
               "Eşik uydurulmadı: yalnız bilgi.")


def _oran(x: Decimal, payda: Decimal) -> Optional[float]:
    return d.sayi(x / payda) if payda > 0 else None


def olustur(kaynak: str, zaman: str, pozisyonlar: Optional[list], ozsermaye, olculmedi_neden: Optional[str] = None) -> dict:
    govde = {**d._zarf("yogunlasma", kaynak, zaman), "olculmedi_neden": olculmedi_neden, "ozsermaye": None, "toplam_brut_nominal": None,
             "toplam_stop_riski": None, "semboller": None, "siniflar": None, "en_buyuk_sembol": None, "en_buyuk_sinif": None, "hhi_brut": None,
             "etkin_sembol_sayisi": None, "esikler": {"sembol_pay": None, "sinif_pay": None, "neden": ESIK_NEDENI}, "uyarilar": [],
             "tanim": "brut_pay = brüt nominal ÷ toplam brüt; stop_riski_pay = stopa kadar açık risk ÷ toplam açık risk; oran = kasaya (özsermayeye) oran"}
    if pozisyonlar is None:
        govde["olculmedi_neden"] = olculmedi_neden or "açık pozisyon verisi yok"
        return govde
    E = Decimal(str(ozsermaye))
    govde["ozsermaye"] = d.para(E)
    sem = {}
    for p in pozisyonlar:
        s = sem.setdefault(p["sembol"], {"brut": Decimal(0), "net": Decimal(0), "risk": Decimal(0), "stratejiler": set(), "sinif": tk.tur(p["sembol"])})
        nom = Decimal(p["nominal"])
        s["brut"] += nom
        s["net"] += nom if p["yon"] == "long" else -nom
        s["risk"] += Decimal(p["stop_riski"])
        s["stratejiler"].add(p["kimlik"])
    brut_t = sum(s["brut"] for s in sem.values()) if sem else Decimal(0)
    risk_t = sum(s["risk"] for s in sem.values()) if sem else Decimal(0)
    govde["toplam_brut_nominal"], govde["toplam_stop_riski"] = d.para(brut_t), d.para(risk_t)

    def kayit(ad: str, s: dict, anahtar: str) -> dict:
        return {anahtar: ad, "brut_nominal": d.para(s["brut"]), "net_nominal": d.para(s["net"]), "brut_oran": _oran(s["brut"], E),
                "net_oran": _oran(s["net"], E), "brut_pay": _oran(s["brut"], brut_t), "stop_riski": d.para(s["risk"]),
                "stop_riski_oran": _oran(s["risk"], E), "stop_riski_pay": _oran(s["risk"], risk_t),
                "strateji_sayisi": len(s["stratejiler"]), "stratejiler": sorted(s["stratejiler"])}
    satirlar = [{**kayit(k, s, "sembol"), "sinif": s["sinif"]} for k, s in sorted(sem.items(), key=lambda kv: (-kv[1]["brut"], kv[0]))]
    sinif = {}
    for k, s in sem.items():
        c = sinif.setdefault(s["sinif"], {"brut": Decimal(0), "net": Decimal(0), "risk": Decimal(0), "stratejiler": set(), "semboller": set()})
        c["brut"] += s["brut"]
        c["net"] += s["net"]
        c["risk"] += s["risk"]
        c["stratejiler"] |= s["stratejiler"]
        c["semboller"].add(k)
    siniflar = [{**kayit(k, c, "sinif"), "ad": SINIF_ADI.get(k, k), "sembol_sayisi": len(c["semboller"])} for k, c in sorted(sinif.items(), key=lambda kv: (-kv[1]["brut"], kv[0]))]
    govde["semboller"], govde["siniflar"] = satirlar, siniflar
    if satirlar and brut_t > 0:
        govde["en_buyuk_sembol"] = {"sembol": satirlar[0]["sembol"], "brut_pay": satirlar[0]["brut_pay"]}
        govde["en_buyuk_sinif"] = {"sinif": siniflar[0]["sinif"], "brut_pay": siniflar[0]["brut_pay"]}
        hhi = float(sum((s["brut"] / brut_t) ** 2 for s in sem.values()))
        govde["hhi_brut"], govde["etkin_sembol_sayisi"] = d.sayi(hhi), d.sayi(1.0 / hhi)
    else:
        govde["olculmedi_neden"] = "açık pozisyon yok: yoğunlaşma tanımsız"
    return govde
