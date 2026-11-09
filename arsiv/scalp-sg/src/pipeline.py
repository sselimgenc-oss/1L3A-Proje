"""Tüm akış: (gerekirse veri indir) → her strateji × grup için optimizasyon → sonuç raporu.

    python -m src.pipeline            # tümü
    python -m src.pipeline --skip-download
Çıktılar: sonuclar/opt_<S>_<grup>.csv, sonuclar/secilen_parametreler.json, SONUC.md
"""
import argparse
import json
import os
from datetime import datetime, timezone

import pandas as pd

from src import backtest as bt
from src.config import GROUPS
from src.optimize import choose, optimize
from src.run import available, run_all

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "sonuclar")
NAMES = {"S1": "Trend Geri Çekilme (EMA+Stokastik)", "S2": "Trend Yönlü Ortalamaya Dönüş (BB+RSI)",
         "S3": "Sıkışma Kırılımı (Volman+MTF)"}


def fmt(s):
    return (f"| {s['n']} | {s['win']*100:.1f}% | {s['pf']:.2f} | {s['avgR']:+.3f} | {s['totR']:+.1f} | {s['maxdd']:.1f} |"
            if s["n"] else "| 0 | - | - | - | - | - |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--strategies", nargs="+", default=["S1", "S2", "S3"])
    ap.add_argument("--groups", nargs="+", default=list(GROUPS))
    a = ap.parse_args()
    if not a.skip_download:
        from src import data
        import sys
        sys.argv = ["data", "--groups", *a.groups]
        data.main()
    os.makedirs(OUT, exist_ok=True)
    chosen, lines = {}, []
    for s in a.strategies:
        for g in a.groups:
            if not available([g]):
                continue
            min_n = 60 if g in ("bist", "mag7", "commodity") else 150
            df = optimize(s, [g], min_n)
            if not len(df):
                continue
            df.to_csv(os.path.join(OUT, f"opt_{s}_{g}.csv"), index=False)
            best, passed = choose(df, min_n)
            p = json.loads(best["params"])
            chosen[f"{s}_{g}"] = dict(params=p, is_passed=bool(passed))
            tr = run_all(s, p, [g])
            tr.to_csv(os.path.join(OUT, f"islemler_{s}_{g}.csv"), index=False)
            si, so = bt.stats(tr[~tr.oos]), bt.stats(tr[tr.oos])
            ok = so["n"] > 0 and so["win"] >= 0.45 and so["pf"] >= 1.3
            lines.append(f"| {s} | {g} | IS {fmt(si)} {'✅' if passed else '❌'} |")
            lines.append(f"| {s} | {g} | **OOS** {fmt(so)} {'✅' if ok else '❌'} |")
            print(f"{s} {g} IS={si} OOS={so}", flush=True)
    with open(os.path.join(OUT, "secilen_parametreler.json"), "w") as f:
        json.dump(chosen, f, indent=2, ensure_ascii=False)
    with open(os.path.join(ROOT, "SONUC.md"), "w") as f:
        f.write(f"# Backtest Sonuçları\n\n_Oluşturma: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC_\n\n")
        f.write("Strateji tanımları: `analiz/ortak_strateji_analizi.md`. Parametreler yalnızca IS (ilk %70) ile seçildi; "
                "OOS (son %30) hiç görülmemiş veridir. R = risk birimi (stop mesafesi), maliyetler dahil.\n\n")
        for k, v in NAMES.items():
            f.write(f"- **{k}** — {v}\n")
        f.write("\n| Strateji | Grup | Dönem | İşlem | Kazanma | PF | Ort. R | Toplam R | Maks DD (R) | Hedef |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        f.write("\n".join(lines) + "\n")
    print("SONUC.md yazıldı")


if __name__ == "__main__":
    main()
