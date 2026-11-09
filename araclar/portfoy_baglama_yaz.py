"""stratejiler/portfoy_adaylari.csv'ye `pf_sinif` ve `pf_ayar` sütunlarını yazar (diğer sütunlara dokunmaz).

Kaynak: motor/portfoy/stratejiler/baglama.py. Birden çok bağlantısı olan satırda pf_sinif 'a | b', pf_ayar JSON dizisi
(aynı sırada) olur; tekte JSON nesnesi. Bağlanamayanlarda pf_sinif boş, pf_ayar 'BAĞLANAMADI: neden'.
Yalnız evrene_uyarlanabilir_mi = evet/kısmen satırları doldurulur. Kullanım: python araclar/portfoy_baglama_yaz.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

from motor.portfoy.stratejiler.baglama import BAGLAMA, BAGLANAMAYAN  # noqa: E402
from motor.portfoy.stratejiler import tum_portfoy_stratejileri  # noqa: E402

CSV = KOK / "stratejiler" / "portfoy_adaylari.csv"


def ayar_json(ayar: dict) -> dict:
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in ayar.items()}


def main():
    df = pd.read_csv(CSV, dtype=str, keep_default_na=False)
    for c in ("pf_sinif", "pf_ayar"):
        if c in df.columns:
            df = df.drop(columns=c)
    df["pf_sinif"], df["pf_ayar"] = "", ""
    siniflar = tum_portfoy_stratejileri()
    gruplar: dict = {}
    for b in BAGLAMA:
        gruplar.setdefault(b["satir"], []).append(b)
    hedef = set(df.index[df["evrene_uyarlanabilir_mi"].isin(["evet", "kısmen"])])
    for satir, kayitlar in gruplar.items():
        if satir not in hedef:
            raise SystemExit(f"satır {satir} evet/kısmen değil")
        ad = df.loc[satir, "ad"]
        for b in kayitlar:
            if not ad.startswith(b["ad_basi"]):
                raise SystemExit(f"satır {satir}: ad uyuşmuyor ({ad!r} !~ {b['ad_basi']!r})")
            if b["sinif"] not in siniflar:
                raise SystemExit(f"bilinmeyen sınıf {b['sinif']}")
        siniflar_s = [b["sinif"] for b in kayitlar]
        ayarlar = [ayar_json(b["ayar"]) | ({"not": b["not_"]} if b["not_"] else {}) for b in kayitlar]
        df.loc[satir, "pf_sinif"] = " | ".join(siniflar_s)
        df.loc[satir, "pf_ayar"] = json.dumps(ayarlar[0] if len(ayarlar) == 1 else ayarlar, ensure_ascii=False)
    for satir, (ad_basi, neden) in BAGLANAMAYAN.items():
        if satir not in hedef or not df.loc[satir, "ad"].startswith(ad_basi):
            raise SystemExit(f"bağlanamayan satır {satir} uyuşmuyor")
        df.loc[satir, "pf_ayar"] = f"BAĞLANAMADI: {neden}"
    eksik = [i for i in sorted(hedef) if i not in gruplar and i not in BAGLANAMAYAN]
    if eksik:
        raise SystemExit(f"bağlanmamış evet/kısmen satırlar: {eksik}")
    df.to_csv(CSV, index=False)
    print(f"yazıldı: {len(gruplar)} satır bağlandı, {len(BAGLANAMAYAN)} bağlanamadı, {len(hedef)} evet/kısmen")


if __name__ == "__main__":
    main()
