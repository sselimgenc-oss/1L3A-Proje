"""D4 (EWMAC / gün içi momentum) için göstergeler. Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar veriyi kullanır.

  mum_gun_tahmin      günde kaç mum var (serinin ilk <=200 aralığından; sonraki veriye bağlı değil).
  ewmac_ham           (EWMA_hızlı - EWMA_yavaş) / (fiyat x günlük getiri std'si)   [Carver ham tahmini]
  ewmac_tahmin        ölçek sabitiyle çarpılmış, +-20'ye kırpılmış tek varyant tahmini.
  birlesik_tahmin     varyantların ortalaması x çeşitlendirme çarpanı, +-20 kırpılmış.
  seans_cerceve       gün içi momentum için seans/karar/çıkış mumu bayrakları (ABD hisse DST'li, UTC gün).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Carver'ın yayımlanmış tahmin ölçekleri (EWMAC hızlı/yavaş GÜN cinsinden). Sabit değerler: lookahead yok.
OLCEK = {(2, 8): 10.6, (4, 16): 7.5, (8, 32): 5.3, (16, 64): 3.75, (32, 128): 2.65, (64, 256): 1.87}
TAHMIN_SINIRI = 20.0


def varyantlari_coz(metin: str) -> list[tuple[int, int]]:
    """'16/64+32/128' -> [(16, 64), (32, 128)]. Ölçeği tanımlı olmayan çift ValueError."""
    sonuc = []
    for parca in str(metin).split("+"):
        h, y = (int(x) for x in parca.strip().split("/"))
        if (h, y) not in OLCEK:
            raise ValueError(f"EWMAC varyantı tanımsız: {h}/{y} (geçerli: {sorted(OLCEK)})")
        sonuc.append((h, y))
    if not sonuc:
        raise ValueError("En az bir varyant gerekli")
    return sonuc


def mum_gun_tahmin(index: pd.DatetimeIndex, gun_mum: int = 0) -> int:
    """Günde mum sayısı. gun_mum > 0 verilmişse o; 0 = ilk 200 mum aralığının medyanından (nedensel kestirim)."""
    if gun_mum and gun_mum > 0:
        return int(gun_mum)
    if len(index) < 3:
        return 1
    ilk = index[:201]
    medyan = float(np.median(np.asarray((ilk[1:] - ilk[:-1]) / pd.Timedelta(seconds=1))))
    return max(1, int(round(86400.0 / medyan))) if medyan > 0 else 1


def ewmac_ham(kapanis: pd.Series, hizli_gun: int, yavas_gun: int, gun_mum: int, std_gun: int = 25) -> pd.Series:
    """Ham tahmin. EMA aralıkları ve std penceresi GÜN x günlük_mum kadar mum; mum getiri std'si sqrt(gun_mum) ile
    günlük eşdeğere çevrilir (1d'de gun_mum=1: doğrudan günlük std)."""
    hz, ya, sw = int(hizli_gun) * gun_mum, int(yavas_gun) * gun_mum, int(std_gun) * gun_mum
    ema_h = kapanis.ewm(span=hz, adjust=False, min_periods=hz).mean()
    ema_y = kapanis.ewm(span=ya, adjust=False, min_periods=ya).mean()
    getiri = kapanis.pct_change()
    std = getiri.ewm(span=sw, adjust=False, min_periods=sw).std() * np.sqrt(gun_mum)
    payda = (kapanis * std).where(std > 0)
    return (ema_h - ema_y) / payda


def ewmac_tahmin(kapanis: pd.Series, hizli_gun: int, yavas_gun: int, gun_mum: int, std_gun: int = 25) -> pd.Series:
    ham = ewmac_ham(kapanis, hizli_gun, yavas_gun, gun_mum, std_gun)
    return (ham * OLCEK[(int(hizli_gun), int(yavas_gun))]).clip(-TAHMIN_SINIRI, TAHMIN_SINIRI)


def birlesik_tahmin(kapanis: pd.Series, varyantlar: list[tuple[int, int]], gun_mum: int,
                    cesit_carpani: float = 1.3, std_gun: int = 25) -> pd.Series:
    """Varyant tahminlerinin ortalaması x çeşitlendirme çarpanı, tekrar +-20. Herhangi bir varyant NaN ise NaN."""
    t = pd.concat([ewmac_tahmin(kapanis, h, y, gun_mum, std_gun) for h, y in varyantlar], axis=1)
    ort = t.mean(axis=1, skipna=False)
    return (ort * cesit_carpani).clip(-TAHMIN_SINIRI, TAHMIN_SINIRI)


# ------------------------------------------------------------------ gün içi seans
_NY = "America/New_York"


def seans_cerceve(index: pd.DatetimeIndex, seans: str, giris_dk: float) -> pd.DataFrame:
    """Seans bayrakları (hepsi saat aritmetiği; fiyat kullanmaz). index UTC açılış zamanıdır.

    sutunlar: sid (seans günü no), seans_ici (mum seansla çakışıyor), karar (giriş karar mumu: kapanışı
    seans_kapanisi - giris_dk'dan önceki SON mum), ac_gecikme_s / dur_s (açılış mumu kontrolü), kapanis_utc.
    Mum süresi yalnız geçmişten kestirilir (genişleyen minimum aralık) -> lookahead yok.
    seans="abd_hisse": 09:30-16:00 America/New_York (DST'ye göre UTC karşılığı değişir);
    seans="utc_gun": 00:00-24:00 UTC.
    """
    if seans not in ("abd_hisse", "utc_gun"):
        raise ValueError("seans 'abd_hisse' veya 'utc_gun' olmalı")
    n = len(index)
    idx = index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")
    fark = ((idx[1:] - idx[:-1]) / pd.Timedelta(seconds=1)).to_numpy() if n > 1 else np.array([])
    dur_s = np.r_[np.nan, np.minimum.accumulate(fark)] if n > 1 else np.full(n, np.nan)
    dur = pd.to_timedelta(dur_s, unit="s")
    kap_zaman = idx + dur

    if seans == "abd_hisse":
        yerel_gun = idx.tz_convert(_NY).tz_localize(None).normalize()
        ac = (yerel_gun + pd.Timedelta(hours=9, minutes=30)).tz_localize(_NY, nonexistent="shift_forward").tz_convert("UTC")
        kapanis = (yerel_gun + pd.Timedelta(hours=16)).tz_localize(_NY, nonexistent="shift_forward").tz_convert("UTC")
        sid = yerel_gun.values.astype("datetime64[D]").astype("int64")
    else:
        gun = idx.floor("D")
        ac, kapanis = gun, gun + pd.Timedelta(days=1)
        sid = gun.tz_localize(None).values.astype("datetime64[D]").astype("int64")

    gecerli = ~np.isnan(dur_s)
    seans_ici = np.asarray((kap_zaman > ac) & (idx < kapanis)) & gecerli
    hedef = kapanis - pd.Timedelta(minutes=float(giris_dk))
    karar = seans_ici & np.asarray((kap_zaman <= hedef) & (kap_zaman + dur > hedef))
    gecikme = pd.Series(np.where(seans_ici, np.asarray((idx - ac) / pd.Timedelta(seconds=1)), np.nan))
    ilk_gecikme = gecikme.groupby(sid).transform("first").to_numpy()
    return pd.DataFrame({
        "sid": sid, "seans_ici": seans_ici, "karar": karar,
        "ac_gecikme_s": ilk_gecikme, "dur_s": dur_s, "kapanis_utc": kapanis,
        "bar_kapanis": kap_zaman,
    }, index=index)
