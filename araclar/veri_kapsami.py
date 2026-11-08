"""veri/mumlar altındaki parquet'lerin kapsam tablosu -> sonuclar/evren/veri_kapsami_2017.md.
Sütunlar: sembol, tf, ilk, son, mum sayısı, eksik oranı (yalnız 24/7 kripto), >%20 sıçrama sayısı, spot vekil aralığı.
Kullanım: python araclar/veri_kapsami.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
from motor.veri.depo import aralik_suresi  # noqa: E402

DIZIN = KOK / "veri" / "mumlar"
CIKTI = KOK / "sonuclar" / "evren" / "veri_kapsami_2017.md"
SINIF_KRIPTO = lambda s: s.endswith("USDT") and not s.startswith("DK_")  # noqa: E731


def satir(sembol: str, tf: str) -> dict:
    df = pd.read_parquet(DIZIN / sembol / f"{tf}.parquet")
    adim = aralik_suresi(tf)
    n = len(df)
    r = {"sembol": sembol, "tf": tf, "ilk": df.index[0], "son": df.index[-1], "n": n}
    if SINIF_KRIPTO(sembol):
        beklenen = int((df.index[-1] - df.index[0]) / adim) + 1
        r["eksik"] = f"{(1 - n / beklenen) * 100:.3f}%"
    else:
        r["eksik"] = "seanslı"
    if tf != "1d":
        getiri = df["kapanis"].pct_change().abs()
        ac = (df["acilis"] / df["kapanis"].shift() - 1).abs()
        r["sicrama"] = int(((getiri > 0.2) | (ac > 0.2)).sum())
    else:
        r["sicrama"] = int((df["kapanis"].pct_change().abs() > 0.2).sum())
    fark = df.index.to_series().diff()
    r["buyuk_bosluk"] = int((fark > pd.Timedelta(days=7)).sum())
    r["tekrar"] = int(df.index.duplicated().sum())
    return r


def main():
    satirlar = []
    for d in sorted(p for p in DIZIN.iterdir() if p.is_dir() and not p.name.startswith("_")):
        for f in sorted(d.glob("*.parquet")):
            if f.stem == "funding":
                continue
            satirlar.append(satir(d.name, f.stem))
    L = ["# Veri kapsamı (2017 hedefi)", "",
         "`python araclar/veri_kapsami.py` ile üretilir. Eksik oranı yalnız 24/7 kriptoda anlamlı (seanslı piyasalarda 'seanslı').",
         "Sıçrama = tek mumda >%20 değişim (kapanış veya açılış boşluğu). Büyük boşluk = ardışık iki mum arası >7 gün.", "",
         "| sembol | tf | ilk | son | mum | eksik | sıçrama>%20 | boşluk>7g | tekrar | spot vekil |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in satirlar:
        k = DIZIN / r["sembol"] / "kaynak.json"
        spot = ""
        if k.exists() and r["tf"] == "5m":
            j = json.loads(k.read_text(encoding="utf-8"))
            if j.get("spot_mum_sayisi"):
                spot = (f"{j['spot_vekil_baslangic'][:16]} -> {j['spot_vekil_bitis'][:16]} ({j['spot_mum_sayisi']} mum; "
                        f"birleşim {j['birlesim_fark_yuzde']:+.2f}%, bazis {j['bazis_medyan_yuzde']}%)")
            else:
                spot = "yok (spot geçmişi perp'ten sonra)"
        L.append(f"| {r['sembol']} | {r['tf']} | {str(r['ilk'])[:16]} | {str(r['son'])[:16]} | {r['n']} | {r['eksik']} | "
                 f"{r['sicrama']} | {r['buyuk_bosluk']} | {r['tekrar']} | {spot} |")
    CIKTI.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"{len(satirlar)} satır -> {CIKTI}")


if __name__ == "__main__":
    main()
