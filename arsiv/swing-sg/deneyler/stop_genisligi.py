"""Stop genişliği deneyi: Trend Molası (S1) ve tüm sistem, dar stop seçenekleriyle.

Varyantlar: mevcut (min(4 gün dibi, kapanış−1 ATR) − 0,5 ATR), daha dar ATR tamponu, stop'u %X ile sınırlama,
stop mesafesi %X'i aşan işlemleri hiç açmama. Risk her durumda işlem başına %1 (pozisyon büyüklüğü stop'a göre).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swing.ayarlar import S1, S2, S3, SINIFLAR  # noqa: E402
from swing.calistir import OOS_BASLANGIC, islemler, veriler  # noqa: E402
from swing.motor import calistir, istatistik, portfoy  # noqa: E402
from swing.stratejiler import s1_geri_cekilme  # noqa: E402
from swing.veri import ENDEKS_VERI, MALIYET  # noqa: E402


def s1_varyant(tavan=None, atla=None, stop_atr=1.0):
    out = []
    for ad, (df, sinif) in veriler().items():
        if sinif not in SINIFLAR["S1_geri_cekilme"]:
            continue
        sig = s1_geri_cekilme(df, {**S1, "stop_atr": stop_atr, "_endeks": ENDEKS_VERI.get(sinif)})
        c = df["Close"]
        mes = (c - sig["stop_long"]) / c
        if tavan:  # stop en fazla %tavan uzakta
            sig["stop_long"] = np.maximum(sig["stop_long"], c * (1 - tavan))
        if atla:  # stop %atla'dan uzaksa işlem açma
            sig.loc[mes > atla, "long"] = False
        out += calistir(ad, sinif, df, sig, MALIYET[sinif], "S1_geri_cekilme")
    return out


def satir(ad, tr, diger):
    o = [t for t in tr if t.giris_tarih >= OOS_BASLANGIC]
    s, so = istatistik(tr), istatistik(o)
    mes = np.median([abs(t.giris - t.stop0) / t.giris for t in tr if t.sinif == "kripto"]) * 100
    p = portfoy(tr + diger)
    po = portfoy(o + [t for t in diger if t.giris_tarih >= OOS_BASLANGIC])
    print(f"{ad:34s} kripto stop medyanı %{mes:4.1f} | n={s['islem']:4d} KO %{s['kazanma_orani']*100:4.1f} PF {s['kar_faktoru']:.2f} "
          f"ortR {s['ort_R']:+.2f} | 2023+ KO %{so['kazanma_orani']*100:4.1f} ortR {so['ort_R']:+.2f} | "
          f"SİSTEM yıllık %{p['yillik_getiri']*100:4.1f} düşüş %{p['max_dusus']*100:5.1f} Sh {p['sharpe_aylik']:.2f} | 2023+ Sh {po['sharpe_aylik']:.2f}")


if __name__ == "__main__":
    diger = islemler("S2_kirilim", S2, SINIFLAR["S2_kirilim"]) + islemler("S3_asiri_satim", S3, SINIFLAR["S3_asiri_satim"])
    satir("Mevcut (1 ATR tampon)", s1_varyant(), diger)
    satir("Tampon 0,5 ATR", s1_varyant(stop_atr=0.5), diger)
    satir("Tampon yok", s1_varyant(stop_atr=0.0), diger)
    for x in (0.08, 0.10, 0.15):
        satir(f"Stop en fazla %{x*100:.0f}", s1_varyant(tavan=x), diger)
    for x in (0.10, 0.15):
        satir(f"Stop %{x*100:.0f}'dan uzaksa işlem yok", s1_varyant(atla=x), diger)
