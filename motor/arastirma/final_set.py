"""Final set tanımı (Aşama 2 kapanışı): `stratejiler/final_set.json`.

Kaynak: sonuclar/secim/oneri.csv (rol=secim, 7 satır) + sonuclar/kilit/{gruplar,secilen_ayarlar}.csv. SET DEĞİŞTİRİLMEZ;
bu modül yalnız mevcut kararı JSON'a döker ve doğrular.

Ağırlık / risk (kilit testindeki set yeniden oynatmasıyla AYNI; `secim.OynatmaAyari` + `kilit_testi.set_testi`):
  - tek_grafik kolu (swing 3 + daytrade 1): TEK hesapta olay sırasıyla yeniden oynatılır; her işlemde özsermayenin %1'i
    risk (bileşik), açık toplam stop riski <= %5, brüt <= 3x, günlük -%3, kill %20 (secim.yeniden_oyna). Strateji başına
    ayrı ağırlık YOKTUR (her strateji aynı %1 riskle, sinyal geldikçe girer) -> kol_ici_agirlik = None.
  - portfoy kolu (3 strateji): her biri kendi motorunda (karar 25: toplam stop riski <= %5) koşar; kol getirisi 3 stratejinin
    EŞİT ağırlıklı günlük ortalamasıdır -> kol_ici_agirlik = 1/3.
  - Kollar 50/50, günlük yeniden dengeli (secim.harmanla). İki kolun ORTAK limit kontrolü yok (kilit testinde de yoktu).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from motor.arastirma import secim as sec
from motor.arastirma import wf_portfoy as wfp
from motor.risk.limitler import SERT_LIMITLER

KOK = Path(__file__).resolve().parents[2]
YOL = KOK / "stratejiler" / "final_set.json"
KOL_PAYI = {"tek_grafik": 0.5, "portfoy": 0.5}
BEKLENEN_SATIR = 7


def kol_sec(ajan: str) -> str:
    return "portfoy" if ajan == "portfoy" else "tek_grafik"


def uret(kok: Path = KOK) -> dict:
    oneri = pd.read_csv(kok / "sonuclar" / "secim" / "oneri.csv")
    oneri = oneri[oneri["rol"] == "secim"].sort_values(["ajan", "sira"], kind="stable")
    gruplar = pd.read_csv(kok / "sonuclar" / "kilit" / "gruplar.csv").set_index("kimlik")
    ayar = pd.read_csv(kok / "sonuclar" / "kilit" / "secilen_ayarlar.csv").set_index("kimlik")
    n_portfoy = int((oneri["ajan"] == "portfoy").sum())
    stratejiler = []
    for o in oneri.itertuples():
        kol = kol_sec(o.ajan)
        g, a = gruplar.loc[o.kimlik], ayar.loc[o.kimlik]
        s = {"kimlik": o.kimlik, "ajan": o.ajan, "stil": g["stil"], "strateji": o.strateji, "sembol": o.sembol, "tf": o.tf,
             "kol": kol, "kol_payi": KOL_PAYI[kol],
             "kol_ici_agirlik": (1.0 / n_portfoy) if kol == "portfoy" else None,
             "islem_basi_risk": None if kol == "portfoy" else SERT_LIMITLER.islem_basi_max_risk_yuzde / 100.0,
             "toplam_stop_risk_butcesi": SERT_LIMITLER.portfoy_toplam_risk_yuzde / 100.0,
             "kilit_testi_ayari": a["secilen_ayar"], "wf_dosya": g["wf_dosya"]}
        if kol == "portfoy":
            s["evren_semboller"] = list(wfp.EVRENLER[o.sembol])
        stratejiler.append(s)
    return {
        "surum": 1,
        "aciklama": "Final set (7 strateji). Kaynak: sonuclar/secim/oneri.csv rol=secim. DEĞİŞTİRİLMEZ (kilit testi sonrası, DURUM.md).",
        "risk": {
            "tek_grafik": {"islem_basi_risk": SERT_LIMITLER.islem_basi_max_risk_yuzde / 100.0,
                           "toplam_stop_risk": SERT_LIMITLER.portfoy_toplam_risk_yuzde / 100.0,
                           "max_kaldirac": SERT_LIMITLER.max_kaldirac,
                           "gunluk_max_kayip": SERT_LIMITLER.gunluk_max_kayip_yuzde / 100.0,
                           "kill_switch": SERT_LIMITLER.kill_switch_dusus_yuzde / 100.0,
                           "yontem": "secim.yeniden_oyna (tek hesap, olay sırası); kilit_testi.set_testi ile aynı"},
            "portfoy": {"toplam_stop_risk": SERT_LIMITLER.portfoy_toplam_risk_yuzde / 100.0,
                        "max_kaldirac": SERT_LIMITLER.max_kaldirac,
                        "gunluk_max_kayip": SERT_LIMITLER.gunluk_max_kayip_yuzde / 100.0,
                        "kill_switch": SERT_LIMITLER.kill_switch_dusus_yuzde / 100.0,
                        "yontem": "kol getirisi = 3 stratejinin eşit ağırlıklı günlük ortalaması (karar 25 bütçesi, portföy motorunda)"},
            "kol_paylari": dict(KOL_PAYI),
            "harman": "günlük yeniden dengeli 50/50 (secim.harmanla); kollar arası ortak limit kontrolü YOK",
        },
        "stratejiler": stratejiler,
    }


def yaz(kok: Path = KOK, yol: Path = YOL) -> dict:
    d = uret(kok)
    dogrula(d, kok)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return d


def yukle(yol: Path = YOL) -> dict:
    d = json.loads(Path(yol).read_text(encoding="utf-8"))
    dogrula(d)
    return d


def dogrula(d: dict, kok: Path = KOK) -> None:
    """7 satır; kimlikler benzersiz; kol payları toplamı 1; oneri.csv (rol=secim) ile birebir aynı küme (dosya varsa)."""
    s = d["stratejiler"]
    if len(s) != BEKLENEN_SATIR:
        raise ValueError(f"final_set: {BEKLENEN_SATIR} strateji bekleniyordu, {len(s)} var")
    kimlikler = [x["kimlik"] for x in s]
    if len(set(kimlikler)) != len(kimlikler):
        raise ValueError("final_set: kimlikler benzersiz değil")
    if abs(sum(d["risk"]["kol_paylari"].values()) - 1.0) > 1e-12:
        raise ValueError("final_set: kol payları toplamı 1 değil")
    pf = [x for x in s if x["kol"] == "portfoy"]
    if pf and abs(sum(x["kol_ici_agirlik"] for x in pf) - 1.0) > 1e-9:
        raise ValueError("final_set: portföy kolu iç ağırlıkları toplamı 1 değil")
    for x in s:
        if x["kimlik"] != f"{x['strateji']}|{x['sembol']}|{x['tf']}":
            raise ValueError(f"final_set: kimlik alanlarla uyuşmuyor: {x['kimlik']}")
    oneri = kok / "sonuclar" / "secim" / "oneri.csv"
    if oneri.exists():
        o = pd.read_csv(oneri)
        o = set(o[o["rol"] == "secim"]["kimlik"])
        if o != set(kimlikler):
            raise ValueError(f"final_set oneri.csv (rol=secim) ile uyuşmuyor: fark {sorted(o ^ set(kimlikler))}")


if __name__ == "__main__":
    d = yaz()
    print(f"[final_set] {YOL}: {len(d['stratejiler'])} strateji")
