"""K2 (rastgele giriş) için hızlı tek-işlem simülatörü — stratejinin ÇIKIŞ KURALLARIYLA (ON_KAYIT Güncelleme 5.3).

Önceki uygulama (saglamlik._tek_islem_r) yalnız ilk ATR stopu + sabit tutma süresi kullanıyordu; stratejinin kâr hedefi,
iz süren stop, başabaş ve sinyal (çıkış) kuralları rastgele girişte YOKTU. Burada rastgele girişe şu çıkışlar uygulanır
(motorla aynı sıra: stop_gap, hedef_gap, stop, hedef; sinyal/zaman çıkışı sonraki açılışta):
  - ilk stop: giriş öncesi mumun kapanışı -/+ mult x ATR14 (mult = gerçek işlemin stop_mesafe/ATR'si),
  - kâr hedefi: stratejinin sinyallerindeki hedef/risk oranının medyanı (yoksa CikisAyarlari.sabit_r_hedefi),
  - iz süren ATR stopu (atr_iz_suren_k) ve başabaşa çekme (basabas_r_esigi),
  - stratejinin kendi `cikis`/`cikis_long`/`cikis_short` sinyalleri (aynı ayar, aynı veri; durumsuz boolean diziler),
  - azami tutma süresi = gerçek işlemin tutma süresi (zaman çıkışı, ON_KAYIT "aynı tutma süresi").
GÜNCELLEME (kapanış kapı 6): gelişmiş modüller de uygulanır (mum mum `_genis`, motor.py ile AYNI sıra/fiyat/komisyon/kayma):
kismi, kismi_yuzde, stop_basamaklari, azalan_roi, geri_cekilme_yuzde(+min), kar_rsi_esikleri, yalniz_karda_cikis(+min),
min_tutma_mum, yasa_bagli_zarar_cikisi, kapanis_chandelier_k, elder_guvenli_bolge_k, agresif_iz_*, ve stratejinin
`pozisyon_cikisi` kancası. Yeni modül kapalıyken (ek=None) eski hızlı/yavaş yol BİT-BİT aynıdır.
Tek DESTEKLENMEYEN: stop_sonrasi_bekleme_mum (önceki GERÇEK işlemin stopuna bağlı bir GİRİŞ filtresidir; tek rastgele işlemde
"önceki stop" yoktur). `desteklenmeyen()` onu listeler; sonuç satırına yazılır. Funding rastgele girişte yoktur.
Funding rastgele girişte yoktur (gerçek işlemlerde var): K2 yönü hafif iyimser/kötümser olabilir, p'yi sistematik değiştirmez.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from motor.strateji import cikislar as cks
from motor.strateji import gostergeler as gst


def desteklenmeyen(ca) -> list:
    """Rastgele girişte UYGULANAMAYAN çıkış alanları (yalnız stop_sonrasi_bekleme_mum; bkz. modül başlığı)."""
    return [ad for ad in ("stop_sonrasi_bekleme_mum",) if getattr(ca, ad, None)]


def desteklenmeyen_eski(ca) -> list:
    """ESKİ liste: yalnız ilk stop + tutma süresi + (hedef/iz/başabaş/sinyal) uygulayan simülatörlerin (v3.rastgele) desteklemedikleri."""
    out = []
    for ad in ("kismi", "stop_basamaklari", "azalan_roi", "kar_rsi_esikleri", "yasa_bagli_zarar_cikisi", "kismi_yuzde"):
        if getattr(ca, ad, ()):
            out.append(ad)
    for ad in ("geri_cekilme_yuzde", "elder_guvenli_bolge_k", "agresif_iz_atr_k", "stop_sonrasi_bekleme_mum",
               "kapanis_chandelier_k", "min_tutma_mum"):
        if getattr(ca, ad, None):
            out.append(ad)
    if getattr(ca, "yalniz_karda_cikis", False):
        out.append("yalniz_karda_cikis")
    return out


_YENI_ALANLAR = ("kismi", "kismi_yuzde", "stop_basamaklari", "azalan_roi", "kar_rsi_esikleri", "yasa_bagli_zarar_cikisi",
                 "geri_cekilme_yuzde", "elder_guvenli_bolge_k", "agresif_iz_atr_k", "kapanis_chandelier_k", "min_tutma_mum",
                 "yalniz_karda_cikis")


def _ek_hazirla(ca, kanca, hazir: pd.DataFrame):
    """Yeni modüllerden biri (ya da kanca) açıksa mum-mum simülatörün ön hesapları (listeler: skaler erişim hızlı); yoksa None."""
    if not (kanca is not None or any(getattr(ca, ad, None) for ad in _YENI_ALANLAR)):
        return None
    hh, ll, cc = hazir["yuksek"], hazir["dusuk"], hazir["kapanis"]
    n = len(hazir)
    nan_l = [math.nan] * n
    return {"ca": ca, "kanca": kanca,
            "o": hazir["acilis"].to_numpy(dtype=float).tolist(), "h": hh.to_numpy(dtype=float).tolist(),
            "l": ll.to_numpy(dtype=float).tolist(), "c": cc.to_numpy(dtype=float).tolist(),
            "atr": (gst.atr(hh, ll, cc, ca.atr_periyot).to_numpy(dtype=float).tolist()
                    if (ca.atr_iz_suren_k or ca.agresif_iz_atr_k) else nan_l),
            "atr_kc": (gst.atr(hh, ll, cc, ca.kapanis_chandelier_periyot).to_numpy(dtype=float).tolist()
                       if ca.kapanis_chandelier_k else nan_l),
            "rsi": (gst.rsi(cc, ca.rsi_periyot).to_numpy(dtype=float).tolist() if ca.kar_rsi_esikleri else nan_l),
            "elder": {}}


def _elder_dizi(ek, yon: int):
    """Elder güvenli bölge stopu her mum için (pozisyondan bağımsız; yöne göre) — tembel, önbellekli."""
    d = ek["elder"].get(yon)
    if d is None:
        ca = ek["ca"]
        ref = ek["l"] if yon == 1 else ek["h"]
        d = [cks.elder_guvenli_bolge(ref, i, ca.elder_n1, ca.elder_n2, ca.elder_guvenli_bolge_k, yon) for i in range(len(ref))]
        ek["elder"][yon] = d
    return d


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
            "desteklenmeyen": desteklenmeyen(ca), "ek": _ek_hazirla(ca, getattr(strateji, "pozisyon_cikisi", None), hazir)}


def _ilk(maske) -> int:
    """İlk True'nun indeksi, yoksa büyük sayı."""
    return int(np.argmax(maske)) if maske.any() else 1 << 60


def tek_islem_r(o, h, l, c, atr, j, yon, hm, mult, kayma, stop_kayma, taker, ex=None, hedef_r=math.nan,
                iz_k=None, iz_atr=None, be_r=None, _dongu=False, ek=None, bilgi=None):
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
    if ek is not None:                                          # gelişmiş modüller / kanca: motorla aynı mum-mum yol
        return _genis(ek, j, yon, son, n, giris, stop, risk, hedef, kayma, stop_kayma, taker, ex, bilgi)
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


def _genis(ek, j, yon, son, n, giris, stop, risk, hedef, kayma, skayma, taker, ex, bilgi=None):
    """motor.backtest.motor.backtest ile AYNI sıra: (3) mum içi stop/hedef(+kısmi) -> (6) kapanışta stop güncelleme -> sinyal ->
    zaman -> roi -> geri çekilme -> kar_rsi -> yasa_zarar -> chandelier -> kanca; çıkış sonraki açılışta. Funding/tick/step yok."""
    ca = ek["ca"]
    O, H, L, C = ek["o"], ek["h"], ek["l"], ek["c"]
    atr, atr_kc, rsi = ek["atr"], ek["atr_kc"], ek["rsi"]
    kanca = ek["kanca"]
    elder = _elder_dizi(ek, yon) if ca.elder_guvenli_bolge_k else None
    kis = []
    for r_k, oran in sorted(ca.kismi):
        kis.append((giris + yon * r_k * risk, oran))
    if ca.kismi_yuzde:
        kis = sorted(kis + [(giris * (1 + yon * ky / 100.0), oran) for ky, oran in ca.kismi_yuzde], key=lambda e: e[0] * yon)
    kalan, gerc = 1.0, 0.0           # kalan oran; gerçekleşen parçaların Σ oran*(yön*(fiyat-giriş) - taker*fiyat)
    ekstrem = yuk = dus = giris
    ilk_stop = stop
    cikis = None
    cik_idx = son                    # bilgi["cikis_idx"]: motorun cikis_zamani konumu (anlık dolum b, bar-içi dolum b+1)
    for b in range(j, son):
        o, h, l, c = O[b], H[b], L[b], C[b]
        if yon == 1:
            sg, sv = o <= stop, l <= stop
            hg = hedef is not None and o >= hedef
            hv = hedef is not None and h >= hedef
        else:
            sg, sv = o >= stop, h >= stop
            hg = hedef is not None and o <= hedef
            hv = hedef is not None and l <= hedef
        cik = None
        ci_ = b + 1
        if sg:
            cik, ci_ = o * (1 - yon * skayma), b
        elif hg:
            cik, ci_ = o, b
        elif sv:
            cik = stop * (1 - yon * skayma)
        elif hv:
            cik = hedef
        if kis and (cik is None or (hv and not hg and not sg and not sv)):
            kalan_seviye = []
            for seviye, oran in kis:
                if hedef is not None and (seviye - hedef) * yon >= 0:
                    continue
                gorulen = (o >= seviye) if yon == 1 else (o <= seviye)
                vurdu = (h >= seviye) if yon == 1 else (l <= seviye)
                if not (gorulen or vurdu):
                    kalan_seviye.append((seviye, oran))
                    continue
                fiyat_k = o if gorulen else seviye
                qty = min(oran, kalan)
                if qty <= 0:
                    continue
                if kalan - qty < 1e-9:
                    cik, ci_ = fiyat_k, (b if gorulen else b + 1)
                    break
                gerc += qty * (yon * (fiyat_k - giris) - taker * fiyat_k)
                kalan -= qty
            kis = kalan_seviye
        if cik is not None:
            cikis, cik_idx = cik, ci_
            break
        tut = b - j + 1
        ekstrem = max(ekstrem, h) if yon == 1 else min(ekstrem, l)
        yuk, dus = max(yuk, h), min(dus, l)
        yeni = stop
        if ca.basabas_r_esigi:
            yeni = cks.basabasa_cek(yon, yeni, giris, ekstrem, risk, ca.basabas_r_esigi)
        if ca.atr_iz_suren_k:
            yeni = cks.iz_suren_stop(yon, yeni, ekstrem, atr[b], ca.atr_iz_suren_k)
        if ca.stop_basamaklari and risk > 0:
            yeni = cks.stop_basamagi(yon, yeni, giris, ekstrem, risk, ca.stop_basamaklari)
        if elder is not None:
            eld = elder[b]
            if not math.isnan(eld):
                yeni = max(yeni, eld) if yon == 1 else min(yeni, eld)
        if ca.agresif_iz_esigi and hedef is not None:
            yol = yon * (hedef - giris)
            if yol > 0 and yon * (ekstrem - giris) / yol >= ca.agresif_iz_esigi:
                yeni = cks.iz_suren_stop(yon, yeni, ekstrem, atr[b], ca.agresif_iz_atr_k)
        if (yeni - stop) * yon > 0:
            stop = yeni
        kar_c = cks.kar_yuzde(yon, giris, c)
        bek = False
        if (ex is not None and ex[b]) and ((ca.min_tutma_mum is None or tut >= ca.min_tutma_mum)
                                            and (not ca.yalniz_karda_cikis or kar_c > ca.yalniz_karda_min_kar_yuzde)):
            bek = True
        elif tut >= son - j:
            bek = True
        elif ca.azalan_roi and cks.azalan_roi_doldu(tut, kar_c, ca.azalan_roi):
            bek = True
        elif cks.geri_cekilme_doldu(cks.kar_yuzde(yon, giris, ekstrem), kar_c, ca.geri_cekilme_yuzde, ca.geri_cekilme_min_kar_yuzde):
            bek = True
        elif cks.kar_rsi_doldu(yon, kar_c, rsi[b], ca.kar_rsi_esikleri):
            bek = True
        elif ca.yasa_bagli_zarar_cikisi and cks.yasa_zarar_doldu(tut, kar_c, ca.yasa_bagli_zarar_cikisi):
            bek = True
        elif ca.kapanis_chandelier_k and cks.kapanis_chandelier_doldu(yon, c, ekstrem, atr_kc[b], ca.kapanis_chandelier_k):
            bek = True
        elif kanca is not None and kanca(cks.PozisyonDurumu(yon, giris, j, b, tut, yuk, dus, c, kar_c)):
            bek = True
        if bek:
            cikis = O[min(b + 1, n - 1)] * (1 - yon * kayma)
            cik_idx = min(b + 1, n - 1)
            break
    if cikis is None:
        cikis = O[son] * (1 - yon * kayma)
    if bilgi is not None:
        bilgi["cikis_idx"] = cik_idx
    net = gerc + kalan * yon * (cikis - giris) - taker * giris - taker * kalan * cikis
    return net / risk

