"""Dersler için backtest işlem referansı (sonuclar/final/beklenti_islem_referansi.csv).

Kaynak: `beklenti_araliklari.csv` ile AYNI örneklem-dışı işlemler (walk-forward OOS + kilitli dönem; `motor.arastirma.beklenti.varliklar_yukle`).
Yeni backtest koşulmaz; mevcut parquet dosyaları okunur (bunlar repoda yok: gitignore). `veri_sonu` çıkışları (pencere sonu kesmesi) hariç tutulur.
Sütunlar: kimlik, n, isabet (r>0 payı), ort_r, std_r, pf_r (R tabanlı), cikis_paylari (JSON {neden: pay}), kaynak.
CLI: python -m motor.canli.dersler_referans
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from motor.arastirma import beklenti as bek
from motor.arastirma import final_set
from motor.canli import dersler as ders

KOK = Path(__file__).resolve().parents[2]
SUTUNLAR = ("kimlik", "n", "isabet", "ort_r", "std_r", "pf_r", "cikis_paylari", "kaynak")
DISLANAN = ("veri_sonu",)


def uret(kok: Path = KOK) -> list:
    set_ = final_set.yukle(kok / "stratejiler" / "final_set.json")
    v = bek.varliklar_yukle(set_, kok)
    satirlar = []
    for s in set_["stratejiler"]:
        k = s["kimlik"]
        isl = v[k]["islem"]
        isl = isl[~isl["cikis_nedeni"].isin(DISLANAN)]
        g = ders.r_ozet([float(x) for x in isl["r"].dropna()])
        pay = (isl["cikis_nedeni"].value_counts() / len(isl)).to_dict()
        satirlar.append({"kimlik": k, "n": g["n"], "isabet": g["isabet"], "ort_r": g["ort_r"], "std_r": g["std_r"],
                         "pf_r": g["pf_r"] if g["pf_r"] is not None else "", "cikis_paylari": json.dumps({a: float(b) for a, b in sorted(pay.items())}, ensure_ascii=False),
                         "kaynak": v[k]["kaynak"] + "; veri_sonu hariç"})
    return satirlar


def yaz(yol=ders.REFERANS_CSV, kok: Path = KOK) -> Path:
    satirlar = uret(kok)
    yol = Path(yol)
    with open(yol, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUTUNLAR, lineterminator="\n")
        w.writeheader()
        w.writerows(satirlar)
    return yol


if __name__ == "__main__":
    print(yaz())
