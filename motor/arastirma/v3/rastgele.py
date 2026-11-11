"""v3 rastgele-giriş testi (tek grafik; ON_KAYIT_V3 bölüm 2, 3 not "Destek ön şartı"; ON_KAYIT_V2 5.1'in v3 uyarlaması).

v2 `test._sembol_k2` stratejinin KENDİ çıkış sinyallerini (`cikis`, `cikis_long/short` boolean dizileri; gerçek geçmişin saatlerine
bağlı) rastgele girişe uygular ve tutma süresini `min(h, n-1-j)` ile kırpar: saat/seans tabanlı çıkışlı satırlarda (6-9) rastgele
işlemin tutma süresi (mum sayısı) KORUNMAZ. Bu yüzden v3'te ayrı değişken kullanılır (v2 dokunulmaz):
  - her gerçek işlem için enstrüman, yön, stop katı (stop mesafesi / ATR14, giriş öncesi mum) ve TUTMA SÜRESİ (mum sayısı) korunur;
  - giriş mumu, gerçek girişin UTC takvim çeyreği içinden tekdüze çekilir (alt_sinir verilirse çeyrek bunun altına inmez: eleme
    dönemi başlangıcından önceki mumlar çekilemez);
  - çıkış = ilk stop vuruşu (aynı motor kuralları) ya da tam `h` mum sonra açılış (zaman çıkışı); `j + h <= n-1` olmayan giriş mumu
    ADAY DEĞİLDİR (tutma süresi kırpılmaz). Gerçek girişin kendisi her zaman adaydır; aday kümesi boşsa açık hata.
İstatistik T = ΣR; p = (1 + #{sim >= gerçek}) / (B + 1) (v2 1.3). Maliyet ×1. Funding rastgele girişte yoktur (gerçekte DK_ long funding
ve kripto funding R'ye dahildir): gerçek R'ye karşı sim R'si hafif iyimser, yani test sıkıdır."""
from __future__ import annotations

import math
import zlib
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import evren_k2, saglamlik
from motor.arastirma.v2 import test as v2test
from motor.arastirma.v3 import sabit
from motor.strateji import gostergeler as gst


def sembol_simule(d: pd.DataFrame, mumlar: pd.DataFrame, ay, n_sim: int, rng, alt_sinir=None, ayrinti: Optional[list] = None) -> tuple:
    """Tek enstrüman: d = gerçek işlemler (giris_zamani, cikis_zamani, yon, stop_mesafe). -> (toplam_r (n_sim,), geçersiz, işlem*n_sim).
    ayrinti (liste) verilirse kabul edilen her (işlem k, giriş konumu j, tutma h) üçlüsü eklenir (testler)."""
    idx = mumlar.index
    o, h = mumlar["acilis"].to_numpy(float), mumlar["yuksek"].to_numpy(float)
    l, c = mumlar["dusuk"].to_numpy(float), mumlar["kapanis"].to_numpy(float)
    atr = gst.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], saglamlik.ATR_PERIYOT).to_numpy(float)
    n = len(mumlar)
    gj = idx.get_indexer(pd.DatetimeIndex(d["giris_zamani"]))
    if (gj < 0).any():
        raise ValueError(f"giriş zamanı mum indeksinde yok ({int((gj < 0).sum())}/{len(gj)})")
    hm_ = np.minimum(saglamlik.tutma_mum(idx, d["giris_zamani"], d["cikis_zamani"]), n - 1 - gj)   # veri sonuna taşan gerçek çıkış
    hm_ = np.maximum(hm_, 1)
    mesafe = d["stop_mesafe"].to_numpy(float)
    stop_med = float(np.nanmedian(mesafe)) if len(mesafe) else math.nan
    mesafe = np.where(np.isfinite(mesafe) & (mesafe > 0), mesafe, stop_med)
    with np.errstate(divide="ignore", invalid="ignore"):
        mult = mesafe / atr[np.maximum(gj - 1, 0)]
    gec = np.isfinite(mult) & (mult > 0)
    mult = np.where(gec, mult, np.median(mult[gec]) if gec.any() else 1.0)
    yon = d["yon"].to_numpy(int)
    qbas, qbit = v2test.ceyrek_sinirlari(d["giris_zamani"], alt_sinir)
    kayma, skayma, taker = ay.kayma_bps / 1e4, ay.stop_kayma_bps / 1e4, ay.komisyon_taker_yuzde / 100
    toplam = np.zeros(n_sim)
    gecersiz = 0
    yc = sabit.K2_YENIDEN_CEKIM
    for k in range(len(d)):
        lo = max(1, int(idx.searchsorted(qbas[k], "left")))
        hi = min(int(idx.searchsorted(qbit[k], "left")), n - int(hm_[k]))       # j + h <= n-1
        if hi <= lo:
            raise ValueError(f"işlem {k}: çeyrekte tutma süresine ({int(hm_[k])} mum) uygun giriş mumu yok")
        u = rng.random((n_sim, yc))
        j = np.clip((lo + np.floor(u * (hi - lo))).astype(np.int64), lo, hi - 1)
        onb: dict = {}

        def deger(jj: int) -> float:
            if jj in onb:
                return onb[jj]
            if not np.isfinite(atr[jj - 1]):
                v = math.nan
            else:
                r = evren_k2.tek_islem_r(o, h, l, c, atr, jj, int(yon[k]), int(hm_[k]), float(mult[k]), kayma, skayma, taker)
                v = math.nan if r is None else float(r)
            onb[jj] = v
            return v
        sonuc = np.full(n_sim, np.nan)
        secilen = np.full(n_sim, -1, dtype=np.int64)
        bekleyen = np.arange(n_sim)
        for e in range(yc):
            if not len(bekleyen):
                break
            jl = j[bekleyen, e]
            uj, ters = np.unique(jl, return_inverse=True)
            vals = np.array([deger(int(x)) for x in uj])[ters]
            ok = np.isfinite(vals)
            sonuc[bekleyen[ok]] = vals[ok]
            secilen[bekleyen[ok]] = jl[ok]
            bekleyen = bekleyen[~ok]
        gecersiz += int(len(bekleyen))
        toplam += np.where(np.isfinite(sonuc), sonuc, 0.0)
        if ayrinti is not None:
            ayrinti.extend((k, int(x), int(hm_[k])) for x in secilen if x >= 0)
    return toplam, gecersiz, int(len(d)) * n_sim


def simule(islemler: dict, veri_al, n_sim: int, tohum: int, alt_sinir=None) -> dict:
    """islemler: {sembol: işlem df}; veri_al(sembol) -> (mumlar, MotorAyarlari). Sembol başına RNG = default_rng([tohum, crc32(sembol)]).
    -> {'toplam_r': (n_sim,), 'n_gecersiz', 'n_islem'}"""
    toplam = np.zeros(n_sim)
    gecersiz = n_islem = 0
    for sembol in sorted(islemler):
        mumlar, ay = veri_al(sembol)
        rng = np.random.default_rng([tohum, zlib.crc32(sembol.encode())])
        t, g, ni = sembol_simule(islemler[sembol], mumlar, ay, n_sim, rng, alt_sinir)
        toplam += t
        gecersiz += g
        n_islem += ni
    return {"toplam_r": toplam, "n_gecersiz": gecersiz, "n_islem": n_islem}


def p_degeri(gercek: float, sim) -> float:
    """v2 1.3 (aynı işlev çağrılır)."""
    return v2test.p_degeri(gercek, sim)
