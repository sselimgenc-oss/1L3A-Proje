"""PBO (Probability of Backtest Overfitting) — CSCV (Bailey, Borwein, López de Prado, Zhu 2017).

Girdi: T satır (zaman, ör. günlük getiri) x N sütun (aday ayar/strateji) getiri matrisi.
Yöntem (CSCV): satırlar `n_blok` (çift, varsayılan 16) ardışık bloğa bölünür; blokların yarısı eğitim (IS), yarısı sınama (OOS)
olacak şekilde TÜM C(S, S/2) bölünme denenir (çok fazlaysa rastgele örnek). Her bölünmede IS'te en iyi metrikli sütun n*
seçilir, OOS'taki göreli sırası w = sıra/(N+1) (1 = en kötü) ve logit lambda = ln(w/(1-w)) hesaplanır.
PBO = P(lambda <= 0): IS'te seçilen adayın OOS'ta medyanın altında kalma olasılığı.

Metrik: Sharpe (ortalama/std; blok toplamlarından yeniden kurulur => bölünme başına O(N) iş, matris çarpımıyla vektörel).
Sütun sabit (std 0) ise metriği NaN sayılır ve IS'te asla seçilmez; böyle sütunlar baştan atılır.
"""
from __future__ import annotations

import itertools
import math

import numpy as np


def _bloklar(T: int, n_blok: int) -> list:
    """T satırı n_blok ardışık, yaklaşık eşit dilime ayırır (artan kalan satırlar baştaki bloklara dağıtılır). Artık satır atılmaz."""
    sinir = np.linspace(0, T, n_blok + 1).astype(int)
    return [(int(sinir[i]), int(sinir[i + 1])) for i in range(n_blok)]


def _sharpe(s1: np.ndarray, s2: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Blok toplamlarından (sum, sum kare, adet) Sharpe: matris satırı = bölünme. NaN: std 0 / adet < 2."""
    with np.errstate(divide="ignore", invalid="ignore"):
        ort = s1 / n
        var = (s2 - n * ort ** 2) / (n - 1)
        sh = ort / np.sqrt(var)
    sh[~np.isfinite(sh)] = np.nan
    sh[(var <= 1e-18)] = np.nan
    return sh


def _sira_yuzdesi(oos_metrik: np.ndarray, secilen: np.ndarray) -> np.ndarray:
    """Her bölünmede secilen sütunun OOS göreli sırası w in (0,1): (1 + #{daha küçük} + 0.5 * #{eşit, kendisi hariç}) / (N+1).
    NaN OOS metrikleri en kötü sayılır (en küçük)."""
    m = np.where(np.isnan(oos_metrik), -np.inf, oos_metrik)
    sec = m[np.arange(len(m)), secilen][:, None]
    kucuk = (m < sec).sum(axis=1)
    esit = (m == sec).sum(axis=1) - 1
    n = m.shape[1]
    return (1.0 + kucuk + 0.5 * esit) / (n + 1.0)


def pbo_cscv(getiri: np.ndarray, n_blok: int = 16, max_kombinasyon: int = 20000, tohum: int = 0, parca: int = 500) -> dict:
    """-> {'pbo', 'n_aday', 'n_kombinasyon', 'T', 'n_blok', 'lambda_medyan', 'oos_ort_secilen', 'tam_enumerasyon'}.
    pbo = nan: yeterli aday/satır yok (N < 2 ya da T < 2*n_blok). Deterministik (tohum)."""
    x = np.asarray(getiri, dtype=float)
    if x.ndim != 2:
        raise ValueError("getiri 2 boyutlu (T x N) olmalı")
    if n_blok < 2 or n_blok % 2:
        raise ValueError("n_blok çift ve >= 2 olmalı")
    T = x.shape[0]
    sonuc = {"pbo": math.nan, "n_aday": 0, "n_kombinasyon": 0, "T": T, "n_blok": n_blok, "lambda_medyan": math.nan,
             "oos_ort_secilen": math.nan, "tam_enumerasyon": True}
    x = np.nan_to_num(x, nan=0.0)
    sabit = x.std(axis=0) <= 1e-12
    x = x[:, ~sabit]
    N = x.shape[1]
    sonuc["n_aday"] = int(N)
    if N < 2 or T < 2 * n_blok:
        return sonuc
    b = _bloklar(T, n_blok)
    bn = np.array([e - a for a, e in b], dtype=float)
    B1 = np.stack([x[a:e].sum(axis=0) for a, e in b])               # (S, N)
    B2 = np.stack([(x[a:e] ** 2).sum(axis=0) for a, e in b])
    yarim = n_blok // 2
    toplam = math.comb(n_blok, yarim)
    if toplam <= max_kombinasyon:
        kombler = np.array(list(itertools.combinations(range(n_blok), yarim)), dtype=np.int16)
    else:
        rng = np.random.default_rng(tohum)
        gorulen, liste = set(), []
        while len(liste) < max_kombinasyon:
            c = tuple(sorted(rng.choice(n_blok, yarim, replace=False).tolist()))
            if c not in gorulen:
                gorulen.add(c)
                liste.append(c)
        kombler = np.array(liste, dtype=np.int16)
        sonuc["tam_enumerasyon"] = False
    K = len(kombler)
    ind = np.zeros((K, n_blok))
    ind[np.arange(K)[:, None], kombler] = 1.0                       # IS blokları
    lam, oos_sec = [], []
    for i in range(0, K, parca):
        g = ind[i:i + parca]
        o = 1.0 - g
        is_sh = _sharpe(g @ B1, g @ B2, (g @ bn)[:, None])
        oo_sh = _sharpe(o @ B1, o @ B2, (o @ bn)[:, None])
        is_m = np.where(np.isnan(is_sh), -np.inf, is_sh)
        sec = is_m.argmax(axis=1)
        w = _sira_yuzdesi(oo_sh, sec)
        lam.append(np.log(w / (1.0 - w)))
        oos_sec.append(oo_sh[np.arange(len(sec)), sec])
    lam = np.concatenate(lam)
    oos_sec = np.concatenate(oos_sec)
    sonuc.update(pbo=float((lam <= 0).mean()), n_kombinasyon=int(K), lambda_medyan=float(np.median(lam)),
                 oos_ort_secilen=float(np.nanmean(oos_sec)))
    return sonuc
