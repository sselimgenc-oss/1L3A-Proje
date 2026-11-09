"""Performans metrikleri."""
import math

import numpy as np
import pandas as pd

YIL_SANIYE = 365.25 * 24 * 3600


def yillik_periyot(indeks: pd.DatetimeIndex) -> float:
    """Yılda gözlenen mum sayısı = (mum sayısı - 1) / kapsanan süre (yıl). Seanslı veride (hisse 1h ~1760/yıl, BIST
    ~2140, emtia ~6000) gerçek mum sıklığını verir; eski "yıl / medyan aralık" 7/24 varsayıyordu ve Sharpe/Sortino'yu
    hissede ~2.2 kat şişiriyordu. Delikli kripto verisinde eskisinden delik oranı kadar küçüktür (ör. %0.1 eksik mum
    -> Sharpe ~%0.05 küçük)."""
    if len(indeks) < 2:
        return np.nan
    saniye = (indeks[-1] - indeks[0]).total_seconds()
    return (len(indeks) - 1) * YIL_SANIYE / saniye if saniye > 0 else np.nan


def hesapla(islemler: pd.DataFrame, ozsermaye: pd.Series, baslangic_sermaye: float = None) -> dict:
    """Oranlar kesir olarak döner (0.1 = %10). max_dusus pozitif kesirdir."""
    bas = float(baslangic_sermaye if baslangic_sermaye is not None else ozsermaye.iloc[0])
    son = float(ozsermaye.iloc[-1])
    m = {"net_getiri": son / bas - 1.0}

    gun = (ozsermaye.index[-1] - ozsermaye.index[0]).total_seconds() / 86400 if len(ozsermaye) > 1 else 0
    m["cagr"] = (son / bas) ** (365.25 / gun) - 1.0 if gun > 0 and son > 0 else np.nan

    zirve = ozsermaye.cummax()
    m["max_dusus"] = float(((zirve - ozsermaye) / zirve).max())

    getiri = ozsermaye.pct_change().dropna()
    ppy = yillik_periyot(ozsermaye.index)
    std = getiri.std(ddof=1) if len(getiri) > 1 else np.nan
    m["sharpe"] = getiri.mean() / std * np.sqrt(ppy) if std and std > 0 else np.nan
    asagi = np.sqrt((np.minimum(getiri, 0.0) ** 2).mean()) if len(getiri) else np.nan
    m["sortino"] = getiri.mean() / asagi * np.sqrt(ppy) if asagi and asagi > 0 else np.nan

    # Günlük MTM düşüş: UTC gün sonu özsermaye değerleri (açık pozisyon K/Z'si dahil);
    # başlangıç sermayesi ilk zirve sayılır.
    gunluk = ozsermaye.groupby(ozsermaye.index.floor("D")).last()
    gz = pd.concat([pd.Series([bas]), gunluk.reset_index(drop=True)], ignore_index=True)
    m["gunluk_mtm_max_dusus"] = float(((gz.cummax() - gz) / gz.cummax()).max())

    k = len(islemler)
    m["islem_sayisi"] = k
    if k:
        net = islemler["net_pnl"]
        kazanc, kayip = net[net > 0].sum(), -net[net < 0].sum()
        m["profit_factor"] = kazanc / kayip if kayip > 0 else (np.inf if kazanc > 0 else np.nan)
        m["kazanma_orani"] = float((net > 0).mean())
        m["ortalama_r"] = float(islemler["r"].mean())
        m["beklenen_deger"] = float(net.mean())          # işlem başına ortalama net PnL
        # En iyi %5 işlem (net_pnl'e göre, yukarı yuvarlanır, en az 1) çıkarılınca kalan
        kes = max(1, math.ceil(0.05 * k))
        kalan = net.sort_values(ascending=False).iloc[kes:]
        m["en_iyi_yuzde5_haric_net"] = float(kalan.sum())
        kz, ky = kalan[kalan > 0].sum(), -kalan[kalan < 0].sum()
        m["en_iyi_yuzde5_haric_pf"] = float(kz / ky) if ky > 0 else (np.inf if kz > 0 else np.nan)
        m["toplam_komisyon"] = float(islemler["komisyon"].sum())
        m["toplam_funding"] = float(islemler["funding"].sum())   # pozitif = ödenen
        m["ortalama_tutma_saat"] = float(
            (islemler["cikis_zamani"] - islemler["giris_zamani"]).dt.total_seconds().mean() / 3600)
    else:
        for a in ["profit_factor", "kazanma_orani", "ortalama_r", "beklenen_deger", "ortalama_tutma_saat",
                  "en_iyi_yuzde5_haric_net", "en_iyi_yuzde5_haric_pf"]:
            m[a] = np.nan
        m["toplam_komisyon"] = 0.0
        m["toplam_funding"] = 0.0
    return m
