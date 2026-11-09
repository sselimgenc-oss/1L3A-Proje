"""Olay tabanlı backtest motoru.

Kurallar (ileriye bakma hatasız):
- Sinyal t gününün kapanışında oluşur, giriş t+1 açılışında yapılır.
- Stop/hedef gün içi kontrol edilir; aynı gün ikisi de değerse önce stop varsayılır (muhafazakâr).
- Çıkış sinyali / süre dolumu kapanışta oluşur, çıkış ertesi açılışta yapılır.
- Her işleme iki yönlü maliyet (komisyon + kayma) uygulanır.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class Islem:
    varlik: str
    sinif: str
    strateji: str
    yon: int
    giris_tarih: pd.Timestamp
    giris: float
    stop0: float
    cikis_tarih: pd.Timestamp
    cikis: float
    neden: str
    gun: int
    getiri: float  # net, oran
    R: float
    kismi_tarih: pd.Timestamp = None  # kısmi kâr alındıysa tarihi ve fiyatı
    kismi_fiyat: float = None


def calistir(ad, sinif, df, sig, maliyet, strateji_adi):
    """sig: DataFrame; kolonlar long, short (bool), stop_long, stop_short (fiyat),
    exit_long, exit_short (bool), ve sabit parametreler sig.attrs içinde:
    hedef_R, iz_atr, max_gun, basabas_R."""
    o, h, l, c = (df[k].values for k in ("Open", "High", "Low", "Close"))
    idx = df.index
    a = sig["atr"].values
    L, S = sig["long"].values, sig["short"].values
    SL, SS = sig["stop_long"].values, sig["stop_short"].values
    XL, XS = sig["exit_long"].values, sig["exit_short"].values
    hedef_R = sig.attrs.get("hedef_R")
    iz_atr = sig.attrs.get("iz_atr")
    max_gun = sig.attrs.get("max_gun", 20)
    be_R = sig.attrs.get("basabas_R")
    kismi_R = sig.attrs.get("kismi_R")  # bu R'de pozisyonun kismi_oran'ı kapatılır, stop başabaşa çekilir
    kismi_oran = sig.attrs.get("kismi_oran", 0.5)
    LML = sig["limit_long"].values if "limit_long" in sig else None
    LMS = sig["limit_short"].values if "limit_short" in sig else None
    n = len(df)
    out = []
    t = 0
    while t < n - 1:
        yon = 1 if L[t] else (-1 if S[t] else 0)
        if yon == 0 or np.isnan(a[t]):
            t += 1
            continue
        e = o[t + 1]
        lim = (LML[t] if yon == 1 else LMS[t]) if LML is not None else np.nan
        if np.isfinite(lim):  # limit emirle giriş (yalnızca t+1 gününde geçerli)
            if (o[t + 1] - lim) * yon <= 0:
                e = o[t + 1]
            elif (l[t + 1] - lim if yon == 1 else lim - h[t + 1]) <= 0:
                e = lim
            else:
                t += 1
                continue
        stop = SL[t] if yon == 1 else SS[t]
        risk = (e - stop) * yon
        if not np.isfinite(risk) or risk <= 0 or risk / e > 0.5:
            t += 1
            continue
        stop0 = stop
        hedef = e + yon * hedef_R * risk if hedef_R else None
        kismi = e + yon * kismi_R * risk if kismi_R else None
        kismi_fiyat = None
        kismi_j = None
        ekstrem = e
        j = t + 1
        cikis = neden = None
        while j < n:
            if j > t + 1 and (o[j] - stop) * yon <= 0:
                cikis, neden = o[j], "stop"
                break
            if (l[j] - stop if yon == 1 else stop - h[j]) <= 0:
                cikis, neden = stop, "stop"
                break
            if kismi is not None and kismi_fiyat is None and \
                    ((h[j] >= kismi) if yon == 1 else (l[j] <= kismi)):
                kismi_fiyat = (max(o[j], kismi) if yon == 1 else min(o[j], kismi)) if j > t + 1 else kismi
                kismi_j = j
                stop = max(stop, e) if yon == 1 else min(stop, e)
            if hedef is not None and ((h[j] - hedef) * yon >= 0 if yon == 1 else (hedef - l[j]) >= 0):
                cikis = max(o[j], hedef) if yon == 1 else min(o[j], hedef)
                if j == t + 1:
                    cikis = hedef
                neden = "hedef"
                break
            # kapanış bazlı güncellemeler
            ekstrem = max(ekstrem, c[j]) if yon == 1 else min(ekstrem, c[j])
            if be_R and (c[j] - e) * yon >= be_R * risk:
                stop = max(stop, e) if yon == 1 else min(stop, e)
            if iz_atr and not np.isnan(a[j]):
                yeni = ekstrem - yon * iz_atr * a[j]
                stop = max(stop, yeni) if yon == 1 else min(stop, yeni)
            gun = j - t
            if (XL[j] if yon == 1 else XS[j]) or gun >= max_gun:
                if j + 1 < n:
                    cikis, neden = o[j + 1], ("sinyal" if gun < max_gun else "sure")
                    j += 1
                else:
                    cikis, neden = c[j], "veri_sonu"
                break
            j += 1
        if cikis is None:
            j = n - 1
            cikis, neden = c[j], "acik"
        brut = (cikis / e - 1) * yon
        if kismi_fiyat is not None:
            brut = kismi_oran * (kismi_fiyat / e - 1) * yon + (1 - kismi_oran) * brut
        net = brut - 2 * maliyet
        out.append(Islem(ad, sinif, strateji_adi, yon, idx[t + 1], e, stop0, idx[j], cikis, neden,
                         j - t, net, net * e / risk, idx[kismi_j] if kismi_j is not None else None, kismi_fiyat))
        t = j  # aynı gün yeni sinyal: çıkış günü kapanışından itibaren
    return out


def istatistik(trades):
    if not trades:
        return {"islem": 0}
    r = np.array([x.getiri for x in trades])
    R = np.array([x.R for x in trades])
    kaz = r[r > 0]
    kay = r[r <= 0]
    pf = kaz.sum() / -kay.sum() if len(kay) and kay.sum() < 0 else np.inf
    return {
        "islem": len(r),
        "kazanma_orani": len(kaz) / len(r),
        "ort_getiri": r.mean(),
        "ort_kazanc": kaz.mean() if len(kaz) else 0,
        "ort_kayip": kay.mean() if len(kay) else 0,
        "kar_faktoru": pf,
        "ort_R": R.mean(),
        "kar_faktoru_R": R[R > 0].sum() / -R[R <= 0].sum() if (R <= 0).any() and R[R <= 0].sum() < 0 else np.inf,
        "toplam_R": R.sum(),
        "ort_gun": np.mean([x.gun for x in trades]),
    }


def portfoy(trades, baslangic=100_000.0, risk=0.01, max_poz=10, max_agirlik=0.20, max_toplam=1.0, detay=False):
    """Sabit-oranlı risk ile portföy simülasyonu (kaldıraçsız).

    Her işlemde özsermayenin `risk` kadarı riske edilir; tek pozisyon özsermayenin `max_agirlik`
    oranını, açık pozisyonların toplamı `max_toplam` oranını aşamaz. Aynı anda en fazla `max_poz`
    pozisyon; aynı varlıkta aynı anda tek pozisyon. Sinyaller tarih ve varlık adına göre sıralanır."""
    if not trades:
        return {}
    ts = sorted(trades, key=lambda x: (x.giris_tarih, x.varlik))  # gelecek bilgisi kullanılmaz
    ozs = baslangic
    acik = []  # (cikis_tarih, pnl, agirlik, varlik)
    egri = []
    alinan = 0
    alinanlar = []  # detay=True: (islem, agirlik, giriş anındaki özsermaye, pnl)
    for tr in ts:
        acik.sort(key=lambda x: x[0])
        while acik and acik[0][0] <= tr.giris_tarih:
            d, pnl, _, _ = acik.pop(0)
            ozs += pnl
            egri.append((d, ozs))
        if len(acik) >= max_poz or any(x[3] == tr.varlik for x in acik):
            continue
        stop_mesafe = abs(tr.giris - tr.stop0) / tr.giris
        agirlik = min(risk / stop_mesafe, max_agirlik, max_toplam - sum(x[2] for x in acik))
        if agirlik < 0.02:
            continue
        pnl = ozs * agirlik * tr.getiri
        acik.append((tr.cikis_tarih, pnl, agirlik, tr.varlik))
        alinanlar.append((tr, agirlik, ozs, pnl))
        alinan += 1
    for d, pnl, _, _ in sorted(acik, key=lambda x: x[0]):
        ozs += pnl
        egri.append((d, ozs))
    e = pd.Series([v for _, v in egri], index=pd.DatetimeIndex([d for d, _ in egri])).groupby(level=0).last()
    yil = max((e.index[-1] - ts[0].giris_tarih).days / 365.25, 1e-9)
    tepe = e.cummax()
    dd = (e / tepe - 1).min()
    aylik = e.resample("ME").last().ffill().pct_change().dropna()
    sharpe = aylik.mean() / aylik.std() * np.sqrt(12) if aylik.std() > 0 else np.nan
    return {
        "alinan_islem": alinan,
        "son_ozsermaye": ozs,
        "toplam_getiri": ozs / baslangic - 1,
        "yillik_getiri": (ozs / baslangic) ** (1 / yil) - 1 if ozs > 0 else -1,
        "max_dusus": dd,
        "sharpe_aylik": sharpe,
        "egri": e,
        **({"alinanlar": alinanlar} if detay else {}),
    }
