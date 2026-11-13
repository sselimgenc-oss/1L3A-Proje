"""Kapanış AŞAMA 2 koşu listesi (ön kayıt ekleri 5–7). Robotic: `eleme/daraltma_asama2.csv` KOŞ kimlikleri; K3: `kod_k3_kod_1`.
Kaynak: ilgili kod dosyalarının VARYANTLAR listeleri. Kodlanamayanlar KODLANAMADI olarak ayrı dosyaya yazılır (aileye girmez,
ek 1). Çıktı: kosu_listesi_asama2.csv + .sha256 (dondurulur; değişiklik --yeniden-dondur) ve kosu_listesi_asama2_kodlanamadi.csv."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "araclar"))
import kapanis_kosu_listesi as kl  # noqa: E402

KAPANIS = kl.KAPANIS
G9 = [f"kod_g9_kod_{i}" for i in range(1, 8)] + ["kod_g9_kod_8b"]
K3 = ["kod_k3_kod_1"]


def _taban(kimlik: str) -> str:
    return re.sub(r"#v\d+$", "", kimlik)


def liste_uret() -> tuple:
    hedef = {r["kimlik"] for r in csv.DictReader(open(KAPANIS / "eleme" / "daraltma_asama2.csv", encoding="utf-8")) if r["karar"] == "KOŞ"}
    liste, kodlanamadi, gorulen = [], [], set()
    for katman, adlar in (("G9", G9), ("K3", K3)):
        for ad in adlar:
            mod = importlib.import_module(f"motor.strateji.kapanis.{ad}")
            for v in mod.VARYANTLAR:
                t = _taban(v["kimlik"])
                if katman == "G9" and t not in hedef:
                    continue
                gorulen.add(t)
                par = dict(v["parametreler"])
                yon = ("iki" if par["short"] else "long") if "short" in par else ""
                s = kl._bos_satir(kimlik=v["kimlik"], katman=katman, kaynak_id=t, sinif=v["sinif"], modul=v.get("modul", ""),
                                  parametreler=kl._json(par), tf=v["tf"], yon=yon, evren="kripto13",
                                  yaklasik="1" if v.get("yaklasik") else "", emin_degil="1" if v.get("emin_degil") else "",
                                  notlar=f"kaynak={ad}.py")
                liste.append(kl.coz_ve_isaretle(s))
            for k in getattr(mod, "KODLANAMADI", []):
                if katman == "K3" or k["kimlik"] in hedef:
                    gorulen.add(k["kimlik"])
                    kodlanamadi.append({"kimlik": k["kimlik"], "katman": katman, "neden": k.get("neden", ""), "dosya": ad})
    eksik = sorted(hedef - gorulen)
    if eksik:
        raise ValueError(f"daraltma KOŞ kimliği hiçbir kod dosyasında yok: {eksik}")
    kim = [s["kimlik"] for s in liste]
    if len(kim) != len(set(kim)):
        raise ValueError("kimlik tekil değil")
    return liste, kodlanamadi


def dondur(yeniden: bool = False) -> dict:
    liste, kod = liste_uret()
    govde = kl._yaz(KAPANIS / "x", kl.SUTUNLAR, liste)
    sha = hashlib.sha256(govde).hexdigest()
    yol = KAPANIS / "kosu_listesi_asama2.csv"
    if yol.exists() and not yeniden and hashlib.sha256(yol.read_bytes()).hexdigest() != sha:
        raise RuntimeError("aşama 2 listesi DONDURULMUŞ ve yeni üretim farklı; bilinçli değişiklik için --yeniden-dondur")
    yol.write_bytes(govde)
    yol.with_name(yol.name + ".sha256").write_text(f"{sha}  {yol.name}\n")
    (KAPANIS / "kosu_listesi_asama2_kodlanamadi.csv").write_bytes(kl._yaz(KAPANIS / "y", ["kimlik", "katman", "neden", "dosya"], kod))
    say = {}
    for s in liste:
        say[(s["katman"], s["durum"])] = say.get((s["katman"], s["durum"]), 0) + 1
    return {"satir": len(liste), "dagilim": say, "kodlanamadi": len(kod), "sha256": sha,
            "cozulemedi": [s["kimlik"] for s in liste if s["durum"] == "COZULEMEDI"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--yeniden-dondur", action="store_true")
    print(dondur(ap.parse_args().yeniden_dondur))
