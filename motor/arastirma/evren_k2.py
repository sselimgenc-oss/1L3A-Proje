"""K2 (rastgele giriş) için hızlı tek-işlem simülatörü — stratejinin ÇIKIŞ KURALLARIYLA (ON_KAYIT Güncelleme 5.3).

Önceki uygulama (saglamlik._tek_islem_r) yalnız ilk ATR stopu + sabit tutma süresi kullanıyordu; stratejinin kâr hedefi,
iz süren stop, başabaş ve sinyal (çıkış) kuralları rastgele girişte YOKTU. Burada rastgele girişe şu çıkışlar uygulanır
(motorla aynı sıra: stop_gap, hedef_gap, stop, hedef; sinyal/zaman çıkışı sonraki açılışta):
  - ilk stop: giriş öncesi mumun kapanışı -/+ mult x ATR14 (mult = gerçek işlemin stop_mesafe/ATR'si),
  - kâr hedefi: stratejinin sinyallerindeki hedef/risk oranının medyanı (yoksa CikisAyarlari.sabit_r_hedefi),
  - iz süren ATR stopu (atr_iz_suren_k) ve başabaşa çekme (basabas_r_esigi),
  - stratejinin kendi `cikis`/`cikis_long`/`cikis_short` sinyalleri (aynı ayar, aynı veri; durumsuz boolean diziler),
  - azami tutma süresi = gerçek işlemin tutma süresi (zaman çıkışı, ON_KAYIT "aynı tutma süresi").
DESTEKLENMEYEN gelişmiş modüller (kismi, stop_basamaklari, azalan_roi, geri_cekilme, kar_rsi, elder, agresif_iz, bekleme)
rastgele girişte UYGULANMAZ; `desteklenmeyen()` listeler ve sonuç satırına yazılır (K2 o strateji için yaklaşıktır).
Funding rastgele girişte yoktur (gerçek işlemlerde var): K2 yönü hafif iyimser/kötümser olabilir, p'yi sistematik değiştirmez.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def desteklenmeyen(ca) -> list:
    out = []
    for ad in ("kismi", "stop_basamaklari", "azalan_roi", "kar_rsi_esikleri"):
        if getattr(ca, ad, ()):
            out.append(ad)
    for ad in ("geri_cekilme_yuzde", "elder_guvenli_bolge_k", "agresif_iz_atr_k", "stop_sonrasi_bekleme_mum"):
        if getattr(ca, ad, None):
            out.append(ad)
    return out


def cikis_bilgisi(strateji, hazir: pd.DataFrame) -> dict:
    """Stratejinin ham sinyallerinden rastgele girişte kullanılacak çıkış verisi (hazir: funding sütunu eklenmiş mumlar)."""
    sig = strateji.sinyaller(hazir)
    n = len(hazir)

    def bol(c):
        return sig[c].fillna(False).to_numpy(dtype=bool) if c in sig.columns else np.zeros(n, dtype=bool)
    ex = bol("cikis")
    ca = strateji.cikis_ayarlari
    hedef_r = math.nan
    if "hedef" in sig.columns:
        y = sig["yon"].to_numpy(dtype=int)
        hd = sig["hedef"].to_numpy(dtype=float)
        st = sig["stop"].to_numpy(dtype=float)
        c = hazir["kapanis"].to_numpy(dtype=float)
        m = (y != 0) & np.isfinite(hd) & np.isfinite(st) & (np.abs(c - st) > 0)
        if m.any():
            oran = (y[m] * (hd[m] - c[m])) / np.abs(c[m] - st[m])
            oran = oran[oran > 0]
            if len(oran):
                hedef_r = float(np.median(oran))
    if not (hedef_r > 0) and ca.sabit_r_hedefi:
        hedef_r = float(ca.sabit_r_hedefi)
    return {"ex_long": ex | bol("cikis_long"), "ex_short": ex | bol("cikis_short"), "hedef_r": hedef_r,
            "iz_k": ca.atr_iz_suren_k, "iz_periyot": ca.atr_periyot, "be_r": ca.basabas_r_esigi,
            "desteklenmeyen": desteklenmeyen(ca)}


def _ilk(maske) -> int:
    """İlk True'nun indeksi, yoksa büyük sayı."""
    return int(np.argmax(maske)) if maske.any() else 1 << 60


def tek_islem_r(o, h, l, c, atr, j, yon, hm, mult, kayma, stop_kayma, taker, ex=None, hedef_r=math.nan,
                iz_k=None, iz_atr=None, be_r=None, _dongu=False):
    """Tek rastgele işlem R'si (giriş j. mumun açılışı, sinyal j-1 kapanışı); stop geçersizse None.
    ex: bool dizisi (t. mumun kapanışında çıkış sinyali -> t+1 açılışında çıkış); hm: azami tutma (mum)."""
    giris = o[j] * (1 + yon * kayma)
    stop = c[j - 1] - yon * mult * atr[j - 1]
    risk = (giris - stop) * yon
    if not risk > 0:
        return None
    hedef = giris + yon * hedef_r * risk if (hedef_r == hedef_r and hedef_r > 0) else None
    son = j + hm
    n = len(o)
    cikis = None
    if iz_k is None and be_r is None and not _dongu:                           # hızlı yol: stop sabit -> vektörel
        if yon == 1:
            ks, kh = l[j:son] <= stop, (h[j:son] >= hedef) if hedef is not None else None
        else:
            ks, kh = h[j:son] >= stop, (l[j:son] <= hedef) if hedef is not None else None
        bs = _ilk(ks)
        bh = _ilk(kh) if kh is not None else 1 << 60
        be = _ilk(ex[j:son]) if ex is not None else 1 << 60       # kapanışta sinyal: bar be'nin sonrası
        olay = min(bs, bh, be)
        if olay == 1 << 60:
            cikis = o[son] * (1 - yon * kayma)
        elif bs == olay:
            gap = o[j + bs] <= stop if yon == 1 else o[j + bs] >= stop
            cikis = (o[j + bs] if gap else stop) * (1 - yon * stop_kayma)
        elif bh == olay:
            b = j + bh
            gap = o[b] >= hedef if yon == 1 else o[b] <= hedef
            cikis = o[b] if gap else hedef
        else:
            cikis = o[min(j + be + 1, n - 1)] * (1 - yon * kayma)
    else:                                                       # iz süren stop / başabaş: mum mum
        ekstrem = giris
        for b in range(j, son):
            if yon == 1:
                sg, sv = o[b] <= stop, l[b] <= stop
                hg = hedef is not None and o[b] >= hedef
                hv = hedef is not None and h[b] >= hedef
            else:
                sg, sv = o[b] >= stop, h[b] >= stop
                hg = hedef is not None and o[b] <= hedef
                hv = hedef is not None and l[b] <= hedef
            if sg:
                cikis = o[b] * (1 - yon * stop_kayma)
            elif hg:
                cikis = o[b]
            elif sv:
                cikis = stop * (1 - yon * stop_kayma)
            elif hv:
                cikis = hedef
            if cikis is not None:
                break
            ekstrem = max(ekstrem, h[b]) if yon == 1 else min(ekstrem, l[b])
            if iz_k is not None and iz_atr is not None and np.isfinite(iz_atr[b]):
                yeni = ekstrem - yon * iz_k * iz_atr[b]
                stop = max(stop, yeni) if yon == 1 else min(stop, yeni)
            if be_r is not None and yon * (ekstrem - giris) >= be_r * risk:
                stop = max(stop, giris) if yon == 1 else min(stop, giris)
            if ex is not None and ex[b]:
                cikis = o[min(b + 1, n - 1)] * (1 - yon * kayma)
                break
        if cikis is None:
            cikis = o[son] * (1 - yon * kayma)
    net = yon * (cikis - giris) - taker * (giris + cikis)
    return net / risk
