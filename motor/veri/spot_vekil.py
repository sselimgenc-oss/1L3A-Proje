"""Kripto perp başlangıcından ÖNCESİ için SPOT 5m vekil verisi (data.binance.vision/data/spot).

ON_KAYIT GÜNCELLEME 5 madde 5: perp arşivi başlamadan önceki dönem spot USDT çifti ile doldurulur; funding yoktur
(0 kabul, işaretli). Spot kısmı veri/mumlar/<S>/kaynak.json ile işaretlenir:
  {"spot_vekil_baslangic": ..., "spot_vekil_bitis": <son spot mumun açılış zamanı>, "perp_baslangic": ...,
   "birlesim_fark_yuzde": <son spot kapanış -> ilk perp açılış %>, "bazis_medyan_yuzde": <ilk ay perp-spot medyan %>,
   "funding": "spot kısmında yok (0 kabul)", "spot_mum_sayisi": n}
Birleşim: perp_baslangic öncesindeki spot mumlar eklenir, perp'in kendisi asla değiştirilmez. Yeniden çalıştırmak güvenlidir.
CLI: python -m motor.veri.spot_vekil BTCUSDT ETHUSDT ... [--baslangic-ay 2017-01]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

from motor.veri.depo import MUM_DIZINI, mum_yolu
from motor.veri.indir import (_ay, _bos_mum, _yaz, birlestir, mum_csv_ayristir, s3_listele, zip_getir,
                              zip_icinden_csv)

SPOT_TABAN = "data/spot"
SPOT_HAM = "spot"


def kaynak_yolu(sembol: str, dizin: Path | None = None) -> Path:
    return (dizin or MUM_DIZINI) / sembol / "kaynak.json"


def kaynak_oku(sembol: str, dizin: Path | None = None) -> dict | None:
    y = kaynak_yolu(sembol, dizin)
    return json.loads(y.read_text(encoding="utf-8")) if y.exists() else None


def _spot_zip_getir(anahtar: str, ham: Path) -> bytes:
    # indir.zip_getir önbellek yolunu TABAN'a göre kurar; spot için ayrı alt dizin kullan
    import motor.veri.indir as ind
    eski = ind.TABAN
    ind.TABAN = SPOT_TABAN
    try:
        return zip_getir(anahtar, ham / SPOT_HAM)
    finally:
        ind.TABAN = eski


def spot_mumlari(sembol: str, bitis: pd.Timestamp, baslangic_ay: str | None = None,
                 dizin: Path | None = None, sessiz: bool = False) -> pd.DataFrame:
    """Spot 5m mumları, açılış zamanı < bitis. Aylık dosyalar; bitis ayı tamamlanmamışsa (aylık dosya var olsa da) kesilir."""
    dizin = dizin or MUM_DIZINI
    ham = dizin / "_ham"
    aylik = {re.search(r"(\d{4}-\d{2})\.zip$", k).group(1): k for k in
             s3_listele(f"{SPOT_TABAN}/monthly/klines/{sembol}/5m/{sembol}-5m-") if k.endswith(".zip")}
    parcalar = []
    for ad, k in sorted(aylik.items()):
        ay = _ay(ad + "-01")
        if baslangic_ay and ay < _ay(baslangic_ay + "-01"):
            continue
        if ay > _ay(bitis):
            continue
        parcalar.append(mum_csv_ayristir(zip_icinden_csv(_spot_zip_getir(k, ham))))
        if not sessiz:
            print(f"  {sembol} spot {ad} tamam", flush=True)
    df = birlestir(parcalar, _bos_mum)
    # Binance spot arşivinde 2018-02-09/10 bakım sonrası ~240 mum 5 dk ızgarasından kaymış (ör. 09:58:14.789): atılır.
    izgarada = (df.index.second == 0) & (df.index.microsecond == 0) & (df.index.minute % 5 == 0)
    df = df[izgarada]
    return df[df.index < bitis]


def spot_vekil_ekle(sembol: str, baslangic_ay: str = "2017-01", dizin: Path | None = None,
                    sessiz: bool = False) -> dict:
    """Perp parquet'inin başına spot vekil ekler; kaynak.json yazar. Dönen: kaynak.json içeriği (spot yoksa spot_mum_sayisi=0)."""
    dizin = dizin or MUM_DIZINI
    yol = mum_yolu(sembol, "5m", dizin)
    mevcut = pd.read_parquet(yol)
    eski = kaynak_oku(sembol, dizin)
    if eski and eski.get("perp_baslangic"):
        perp_ilk = pd.Timestamp(eski["perp_baslangic"])
    else:
        perp_ilk = mevcut.index[0]
    perp = mevcut[mevcut.index >= perp_ilk]
    spot = spot_mumlari(sembol, perp_ilk, baslangic_ay, dizin, sessiz)
    # ilk ay perp-spot bazisi (perp'in kendi ilk 30 günü ile aynı zamanlı spot)
    bazis = None
    try:
        pen = perp[perp.index < perp_ilk + pd.Timedelta(days=30)]
        sp_pen = spot_mumlari(sembol, perp_ilk + pd.Timedelta(days=30), _ay(perp_ilk).strftime("%Y-%m"), dizin, True)
        sp_pen = sp_pen[sp_pen.index >= perp_ilk]
        ort = pen["kapanis"].to_frame("p").join(sp_pen["kapanis"].rename("s"), how="inner")
        if len(ort) > 100:
            bazis = float(((ort["p"] / ort["s"] - 1) * 100).median())
    except Exception:
        bazis = None
    sonuc = {"perp_baslangic": str(perp_ilk), "spot_mum_sayisi": int(len(spot)),
             "funding": "spot kısmında yok (0 kabul)"}
    if len(spot):
        fark = float((perp["acilis"].iloc[0] / spot["kapanis"].iloc[-1] - 1) * 100)
        sonuc.update({"spot_vekil_baslangic": str(spot.index[0]), "spot_vekil_bitis": str(spot.index[-1]),
                      "birlesim_fark_yuzde": round(fark, 4), "bazis_medyan_yuzde": None if bazis is None else round(bazis, 4)})
        birlesik = birlestir([spot, perp], _bos_mum)  # perp sonra: çakışmada perp kazanır
        _yaz(birlesik.astype(mevcut.dtypes.to_dict()), yol)
    kaynak_yolu(sembol, dizin).write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


def main(argv=None):
    p = argparse.ArgumentParser(description="Perp öncesi spot vekil 5m ekle")
    p.add_argument("semboller", nargs="+")
    p.add_argument("--baslangic-ay", default="2017-01")
    a = p.parse_args(argv)
    for s in a.semboller:
        r = spot_vekil_ekle(s, a.baslangic_ay)
        print(s, r, flush=True)


if __name__ == "__main__":
    sys.exit(main())
