"""Durağan blok bootstrap + Hansen (2005) SPA (ON_KAYIT_V2 5.5; YALNIZ RAPOR, kapı değil).

Kıyas = sıfır: d_{k,t} = x_{k,t} (satırın günlük MTM getirisi). Studentize istatistik T = max(0, max_k sqrt(n) d̄_k / ω̂_k);
ω̂_k durağan bootstrap'tan. p-değeri üç null-ortalama seçimi ile (bootstrap ortalaması d̄'den μ'ye kaydırılır): alt (μ^l = min(d̄,0)), tutarlı
(μ^c = d̄ · 1{t_k <= -sqrt(2 log log n)}), üst (μ^u = 0, en elverişsiz). Rapor edilen p = tutarlı olandır. Varyansı 0 olan (hiç işlem yapmayan) satır istatistikten çıkarılır ve sayılır.
Seri hizası: tüm satırların günlük serileri ortak takvime oturtulur; serisi olmayan günler 0 getiri (piyasada değil).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from motor.arastirma.v2 import sabit


def durgan_indeks(n: int, ort_blok: float, n_cekim: int, rng, parca: int = None):
    """Durağan bootstrap indeks matrisi parçaları (her biri (<=parca, n) int). Yeni blok olasılığı 1/ort_blok; blok sonu dairesel."""
    parca = parca or n_cekim
    p = 1.0 / ort_blok
    kalan = n_cekim
    t = np.arange(n)
    while kalan > 0:
        b = min(parca, kalan)
        yeni = rng.random((b, n)) < p
        yeni[:, 0] = True
        baslangic = rng.integers(0, n, size=(b, n))
        son_yeni = np.maximum.accumulate(np.where(yeni, t[None, :], 0), axis=1)
        taban = np.take_along_axis(baslangic, son_yeni, axis=1)
        yield (taban + (t[None, :] - son_yeni)) % n
        kalan -= b


def hansen_spa(seriler: dict, tohum: int, ort_blok: float = sabit.BOOT_BLOK_GUN, n_cekim: int = sabit.BOOT_CEKIM) -> dict:
    """seriler: {anahtar: günlük getiri Series (UTC gün indeksli)}. -> {'p', 'p_alt', 'p_ust', 'T', 'n_gun', 'n_model', 'n_sabit', 'en_iyi'}"""
    ad = sorted(seriler)
    bas = min(seriler[k].index.min() for k in ad)
    bit = max(seriler[k].index.max() for k in ad)
    gunler = pd.date_range(bas, bit, freq="D", tz="UTC")
    X = np.column_stack([seriler[k].reindex(gunler).fillna(0.0).to_numpy(dtype=float) for k in ad])
    n, K = X.shape
    dbar = X.mean(axis=0)
    rng = np.random.default_rng(tohum)
    parcalar = []
    for idx in durgan_indeks(n, ort_blok, n_cekim, rng, parca=sabit.BOOT_PARCA):
        parcalar.append(np.stack([X[i].mean(axis=0) for i in idx]))
    Db = np.concatenate(parcalar)                                   # (B, K)
    omega = np.sqrt(n * Db.var(axis=0, ddof=1))
    gecerli = omega > sabit.EPS
    if not gecerli.any():
        return {"p": 1.0, "p_alt": 1.0, "p_ust": 1.0, "T": 0.0, "n_gun": n, "n_model": K, "n_sabit": K, "en_iyi": ""}
    t = np.sqrt(n) * dbar[gecerli] / omega[gecerli]
    T = max(0.0, float(t.max()))
    esik = -math.sqrt(2.0 * math.log(math.log(n)))
    mu = {"alt": np.minimum(dbar[gecerli], 0.0), "tutarli": np.where(t <= esik, dbar[gecerli], 0.0), "ust": np.zeros(int(gecerli.sum()))}
    p = {}
    for ad_mu, m in mu.items():
        Z = np.sqrt(n) * (Db[:, gecerli] - dbar[gecerli][None, :] + m[None, :]) / omega[gecerli][None, :]   # null ortalaması m
        Tb = np.maximum(0.0, Z.max(axis=1))
        p[ad_mu] = float((Tb > T).mean())
    en = ad[int(np.flatnonzero(gecerli)[int(np.argmax(t))])]
    return {"p": p["tutarli"], "p_alt": p["alt"], "p_ust": p["ust"], "T": T, "n_gun": int(n), "n_model": int(K),
            "n_sabit": int(K - int(gecerli.sum())), "en_iyi": en}
