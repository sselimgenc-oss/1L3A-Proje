"""Örneklem-içi (IS, 2023 öncesi) ızgara araması; seçilen ayarlar örneklem-dışı (OOS, 2023+) doğrulanır."""
import itertools
import multiprocessing as mp

import numpy as np
import pandas as pd

from .calistir import OOS_BASLANGIC, islemler, veriler
from .motor import istatistik, portfoy


def _tek(arg):
    strateji, p, siniflar, anahtar, vals = arg
    tr = islemler(strateji, p, siniflar)
    a = istatistik([t for t in tr if t.giris_tarih < OOS_BASLANGIC])
    b = istatistik([t for t in tr if t.giris_tarih >= OOS_BASLANGIC])
    if not a.get("islem") or not b.get("islem"):
        return None
    pa = portfoy([t for t in tr if t.giris_tarih < OOS_BASLANGIC])
    pb = portfoy([t for t in tr if t.giris_tarih >= OOS_BASLANGIC])
    return {**dict(zip(anahtar, vals)),
            "IS_CAGR": pa["yillik_getiri"], "IS_DD": pa["max_dusus"],
            "OOS_CAGR": pb["yillik_getiri"], "OOS_DD": pb["max_dusus"],
            "IS_n": a["islem"], "IS_WR": a["kazanma_orani"], "IS_PF": a["kar_faktoru"], "IS_R": a["ort_R"],
            "OOS_n": b["islem"], "OOS_WR": b["kazanma_orani"], "OOS_PF": b["kar_faktoru"], "OOS_R": b["ort_R"]}


def tara(strateji, izgara, sabit=None, min_islem=80, siniflar=None):
    anahtar = list(izgara)
    veriler()  # süreçler çatallanmadan önce veriyi yükle
    isler = [(strateji, {**(sabit or {}), **dict(zip(anahtar, v))}, siniflar, anahtar, v)
             for v in itertools.product(*izgara.values())]
    with mp.get_context("fork").Pool() as havuz:
        rows = [r for r in havuz.map(_tek, isler, chunksize=1) if r]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # Skor yalnızca IS verisinden: beklenen R × sqrt(işlem sayısı), WR >= %45 şartı
    df["skor"] = np.where((df.IS_WR >= 0.45) & (df.IS_n >= min_islem), df.IS_R * np.sqrt(df.IS_n), -9)
    return df.sort_values("skor", ascending=False)


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
