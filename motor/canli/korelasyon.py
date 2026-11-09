"""Stratejiler arası günlük getiri korelasyonu (pano öncelik 5c). Hesap BURADA (motor tarafı); pano yalnız biçimler.

Seri = stratejinin günlük katkı getirisi (o günün net K/Z'si ÷ önceki gün sonu özsermaye; gün kesimi paper'da TSİ, backtestte UTC ızgarası). İşlem olmayan gün 0'dır.
Pearson korelasyonu, her çift için ORTAK günlerde (iki serinin de dolu olduğu günler). Kurallar:
  - ortak gün < MIN_ORTAK_GUN (30; kullanıcının görev tanımı, durum_ek.MIN_GUN ile aynı "yeterli örnek" sınırı): hücre null + neden.
    HİÇ çift 30 ortak güne ulaşmadıysa tüm matris null + neden.
  - iki seriden biri sabitse (hiç işlem/getiri yok, varyans 0): hücre null + neden (korelasyon tanımsız).
  - güven aralığı: Fisher z, %95 (ortak gün > 3 ise).
EŞİK YOK: projede tanımlı bir "yüksek korelasyon" eşiği yoktur; uyarı/alarm üretilmez, yalnız bilgi. (Eski panonun 0.6/0.7 eşikleri alınmadı.)
Not: günlük getiri korelasyonu eşzamanlı hareketi ölçer; ortak zarar/ortak düşüş korelasyonu (pano_envanteri F41) kapsam dışıdır.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

from motor.canli import durum as d

MIN_ORTAK_GUN = 30
Z95 = 1.959963984540054


def katki_serileri(kumulatif: dict, ozs_gun: dict, baslangic: float) -> dict:
    """{kimlik: {gun: gün sonu kümülatif net K/Z}}, {gun: gün sonu özsermaye} -> {kimlik: Series (gün metni indeksli, günlük katkı getirisi)}.
    Takvim günleri doldurulur (kümülatif ileri taşınır; kayıt olmayan gün K/Z 0). Önceki gün özsermayesi yoksa başlangıç sermayesi kullanılır."""
    if not ozs_gun:
        return {}
    gunler = pd.date_range(min(ozs_gun), max(ozs_gun), freq="D")
    ozs = pd.Series({pd.Timestamp(g): float(e) for g, e in ozs_gun.items()}).reindex(gunler).ffill()
    onceki = ozs.shift(1)
    onceki.iloc[0] = float(baslangic)
    out = {}
    for k, seri in kumulatif.items():
        kum = pd.Series({pd.Timestamp(g): float(v) for g, v in seri.items()}).reindex(gunler).ffill().fillna(0.0)
        s = kum.diff()
        s.iloc[0] = kum.iloc[0]
        r = s / onceki
        r.index = [str(x.date()) for x in gunler]
        out[k] = r
    return out


def _fisher(r: float, n: int):
    if n <= 3 or abs(r) >= 1.0:
        return None
    z, se = math.atanh(r), 1.0 / math.sqrt(n - 3)
    return [float(math.tanh(z - Z95 * se)), float(math.tanh(z + Z95 * se))]


def hesapla(seriler: dict, kaynak: str, zaman: str, gun_kesimi: str, min_ortak: int = MIN_ORTAK_GUN) -> dict:
    """seriler: {kimlik: pd.Series (gün metni indeksli, günlük getiri; NaN = o gün yok)}. -> korelasyon.json içeriği."""
    kimlikler = sorted(seriler)
    n = len(kimlikler)
    govde = {**d._zarf("korelasyon", kaynak, zaman), "gun_kesimi": gun_kesimi, "min_ortak_gun": min_ortak, "yontem": "Pearson, ortak günlerde; Fisher z %95 aralığı",
             "esik": None, "esik_notu": "Projede tanımlı bir korelasyon eşiği yok: uyarı üretilmez, yalnız bilgi.",
             "kimlikler": kimlikler, "matris": None, "ortak_gun": None, "guven_araligi": None, "hucre_neden": [], "neden": None, "ozet": None}
    if n < 2:
        govde["neden"] = f"en az 2 strateji gerekir ({n} var)"
        return govde
    df = pd.DataFrame({k: seriler[k] for k in kimlikler})
    matris = [[None] * n for _ in range(n)]
    ortak = [[0] * n for _ in range(n)]
    aralik = [[None] * n for _ in range(n)]
    nedenler = []
    for i in range(n):
        for j in range(n):
            a, b = kimlikler[i], kimlikler[j]
            ikili = df[[a, b]].dropna() if i != j else df[[a]].dropna().rename(columns={a: a})
            m = len(ikili)
            ortak[i][j] = int(m)
            if i == j:
                matris[i][j] = 1.0 if m >= min_ortak and float(np.std(ikili[a])) > 0 else None
                if matris[i][j] is None:
                    nedenler.append({"a": a, "b": b, "neden": f"ortak gün {m} < {min_ortak}" if m < min_ortak else "seri sabit (varyans 0)"})
                continue
            if m < min_ortak:
                nedenler.append({"a": a, "b": b, "neden": f"ortak gün {m} < {min_ortak}"})
                continue
            xa, xb = ikili[a].to_numpy(dtype=float), ikili[b].to_numpy(dtype=float)
            if np.std(xa) == 0 or np.std(xb) == 0:
                nedenler.append({"a": a, "b": b, "neden": "seri sabit (hiç işlem/getiri yok, varyans 0): korelasyon tanımsız"})
                continue
            r = float(np.corrcoef(xa, xb)[0, 1])
            matris[i][j], aralik[i][j] = d.sayi(r), _fisher(r, m)
    govde["ortak_gun"], govde["hucre_neden"] = ortak, nedenler
    cift = [(matris[i][j], kimlikler[i], kimlikler[j]) for i in range(n) for j in range(i + 1, n) if matris[i][j] is not None]
    if not cift:
        en_cok = max((ortak[i][j] for i in range(n) for j in range(i + 1, n)), default=0)
        govde["neden"] = (f"hiçbir stratejide çifti için {min_ortak} ortak gün yok (en çok {en_cok} gün)" if en_cok < min_ortak
                          else "hiçbir çiftte korelasyon hesaplanamadı (seriler sabit: işlem yok)")
        return govde
    govde["matris"], govde["guven_araligi"] = matris, aralik
    en = max(cift, key=lambda c: c[0])
    govde["ozet"] = {"cift_sayisi": len(cift), "olculemeyen_cift": n * (n - 1) // 2 - len(cift),
                     "ort_mutlak": d.sayi(float(np.mean([abs(c[0]) for c in cift]))),
                     "en_yuksek": {"a": en[1], "b": en[2], "korelasyon": en[0]}, "en_dusuk": (lambda c: {"a": c[1], "b": c[2], "korelasyon": c[0]})(min(cift, key=lambda c: c[0]))}
    return govde
