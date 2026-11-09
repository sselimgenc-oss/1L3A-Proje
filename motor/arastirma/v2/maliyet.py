"""v2 maliyet tablosu ve TradFi funding (ON_KAYIT_V2 1.2).

v2 tablosu = v1 `maliyet_tablosu.csv` (içeriği aynen) + `funding_long_8s_oran` sütunu; `sonuclar/evren/v2/maliyet_tablosu_v2.csv`
(+ .sha256). v1 tablosu ve hash'i DOKUNULMAZ: v1 koşuları `evren_maliyet.TABLO_YOLU`'nu kullanmaya devam eder; v2 her yerde
`yol=` ile bu tabloyu verir ve v2 çıktılarına v2 tablosunun sha256'sını yazar.

Funding uygulaması (motor/backtest DEĞİŞTİRİLMEDEN, işlem sonrası): DK_ sembolünde LONG işlem, tutulan her 8 saat için
nominal (miktar × giriş fiyatı) × oran öder; süre = (çıkış − giriş) / 8 saat, TAKVİM süresi (hafta sonu/seans dışı dahil).
SHORT'a gelir yazılmaz (0). Maliyet çarpanı (×2) funding'i çarpmaz. Kısmi çıkışlarda tüm süre ilk miktar üzerinden alınır
(tutucu). Kripto: motorun gerçek funding serisi aynen (bu modül dokunmaz).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from motor.arastirma import evren_maliyet
from motor.arastirma.v2 import sabit


def tablo_yolu(cikti=None) -> Path:
    return Path(cikti or sabit.CIKTI) / sabit.TABLO_V2_AD


def v2_tablosu_uret() -> pd.DataFrame:
    """v1 tablosu + funding sütunu (deterministik). v1 tablosunun hash'i kendi .sha256'sına uymuyorsa açık hata."""
    v1 = evren_maliyet.TABLO_YOLU
    beklenen = v1.with_suffix(".sha256").read_text().strip()
    if evren_maliyet.tablo_hash(v1) != beklenen:
        raise RuntimeError("v1 maliyet tablosu .sha256 ile uyuşmuyor; v2 tablosu üretilmez")
    d = pd.read_csv(v1)
    d[sabit.FUNDING_SUTUNU] = np.where(d["sembol"].str.startswith("DK_"), sabit.FUNDING_LONG_8S_ORAN, 0.0)
    return d


def tabloyu_hazirla(cikti=None) -> Path:
    """Yoksa yazar; varsa içeriğin yeniden üretilenle BAYT BAYT aynı olduğunu doğrular (değişmişse açık hata)."""
    yol = tablo_yolu(cikti)
    yeni = v2_tablosu_uret().to_csv(index=False)
    if yol.exists():
        if yol.read_text() != yeni:
            raise RuntimeError(f"{yol.name} üretilenle uyuşmuyor (tablo sabit olmalı)")
    else:
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(yeni)
    yol.with_suffix(".sha256").write_text(evren_maliyet.tablo_hash(yol) + "\n")
    return yol


def funding_maliyeti_usd(yon, miktar, giris_fiyati, giris_zamani, cikis_zamani, oran_8s) -> np.ndarray:
    """İşlem başına funding gideri ($; pozitif = ödenen). Yalnız LONG öder; short 0. oran_8s skaler ya da dizi."""
    yon = np.asarray(yon)
    sure = (pd.DatetimeIndex(cikis_zamani) - pd.DatetimeIndex(giris_zamani)) / pd.Timedelta(hours=sabit.FUNDING_PERIYOT_SAAT)
    nominal = np.asarray(miktar, dtype=float) * np.asarray(giris_fiyati, dtype=float)
    return np.where(yon > 0, nominal * np.asarray(oran_8s, dtype=float) * np.asarray(sure, dtype=float), 0.0)
