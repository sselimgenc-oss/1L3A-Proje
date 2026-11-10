"""Seans takvimi: bayatlık denetimi (hisse hafta sonu/tatil yanlış kırmızı olmasın) ve TradFi mum süzgeci.

Sembol türleri: kripto (7/24), hisse (ABD hisseleri, NYSE seansı 09:30-16:00 New York, hafta içi, NYSE tatilleri; erken
kapanış 13:00), emtia (DK_XAU/WTI/COPPER: CME Globex benzeri; Pazar 18:00 NY -> Cuma 17:00 NY, günlük mola 17:00-18:00 NY;
1 Ocak, 25 Aralık ve Büyük Cuma kapalı). Takvim YAKLAŞIKTIR (tatil listesi koddadır; ilan edilmemiş kapanışlar bilinmez):
yanlış 'seans açık' kararı en kötü ihtimalle gereksiz bayat uyarısı, yanlış 'kapalı' kararı gizlenmiş bayatlık üretir; bu yüzden
bayatlık eşiği seans dakikasıyla sayılır ama kripto için duvar saatidir.

Binance TradFi perpetual'ları 7/24 işlem görür; Dukascopy tabanlı araştırma verisi yalnız seanslıdır. Strateji girdisini
araştırma verisiyle aynı yapıda tutmak için canlı TradFi mumları seans süzgecinden (`seans_maskesi`) geçirilir.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from dateutil.easter import easter

NY = ZoneInfo("America/New_York")
ABD_HISSELERI = ("DK_AAPL", "DK_MSFT", "DK_GOOGL", "DK_AMZN", "DK_NVDA", "DK_META", "DK_TSLA",
                 # v2 paper seti (evren 'genel' = 17 ABD hissesi): eski set 7 hissede kalmıştı; kalanlar kripto sayılıp 7/24 işlenirdi
                 "DK_AVGO", "DK_LLY", "DK_WMT", "DK_JPM", "DK_V", "DK_MU", "DK_AMD", "DK_XOM", "DK_JNJ", "DK_MA")
EMTIALAR = ("DK_XAU", "DK_WTI", "DK_COPPER", "DK_XAG", "DK_NATGAS")


def tur(sembol: str) -> str:
    if sembol in ABD_HISSELERI:
        return "hisse"
    if sembol in EMTIALAR:
        return "emtia"
    return "kripto"


def _n_gun(yil, ay, haftagunu, n) -> date:
    d = date(yil, ay, 1)
    d += timedelta(days=(haftagunu - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _son_gun(yil, ay, haftagunu) -> date:
    d = date(yil + (ay == 12), ay % 12 + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - haftagunu) % 7)


def _gozlenen(d: date) -> date:
    """Hafta sonuna denk gelen tatil: Cumartesi -> Cuma (NYSE), Pazar -> Pazartesi."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def nyse_tatilleri(yil: int) -> set:
    t = {_n_gun(yil, 1, 0, 3), _n_gun(yil, 2, 0, 3), easter(yil) - timedelta(days=2), _son_gun(yil, 5, 0),
         _n_gun(yil, 9, 0, 1), _n_gun(yil, 11, 3, 4)}
    for ay, gun in ((1, 1), (6, 19), (7, 4), (12, 25)):
        d = date(yil, ay, gun)
        if ay == 1 and d.weekday() == 5:          # 1 Ocak Cumartesi ise önceki yıl kapanmaz
            continue
        t.add(_gozlenen(d))
    return t


def erken_kapanis(d: date) -> bool:
    """13:00 NY erken kapanış: Şükran Günü ertesi, 24 Aralık (hafta içi), 3 Temmuz (4 Temmuz hafta içi ise)."""
    if d == _n_gun(d.year, 11, 3, 4) + timedelta(days=1):
        return True
    if d.month == 12 and d.day == 24 and d.weekday() < 5:
        return True
    return d.month == 7 and d.day == 3 and d.weekday() < 4


def _hisse_acik_dk_araligi(d: date):
    """NY yerel tarih d için (açılış_dk, kapanış_dk) NY gün dakikası veya None."""
    if d.weekday() >= 5 or d in nyse_tatilleri(d.year):
        return None
    return 570, (780 if erken_kapanis(d) else 960)


def seans_maskesi(sembol: str, index: pd.DatetimeIndex) -> np.ndarray:
    """Mum AÇILIŞ zamanları (UTC) için seans içinde mi? Kripto: hepsi True."""
    if len(index) == 0 or tur(sembol) == "kripto":
        return np.ones(len(index), dtype=bool)
    yer = index.tz_convert(NY)
    dk = (yer.hour * 60 + yer.minute).to_numpy()
    gunler = [d.date() for d in yer.normalize()]
    out = np.zeros(len(index), dtype=bool)
    if tur(sembol) == "hisse":
        onbellek = {}
        for i, d in enumerate(gunler):
            if d not in onbellek:
                onbellek[d] = _hisse_acik_dk_araligi(d)
            a = onbellek[d]
            out[i] = a is not None and a[0] <= dk[i] < a[1]
        return out
    hg = yer.weekday.to_numpy()
    for i, d in enumerate(gunler):
        kapali_gun = (d.month == 1 and d.day == 1) or (d.month == 12 and d.day == 25) or d == easter(d.year) - timedelta(days=2)
        if kapali_gun:
            continue
        if hg[i] == 5:
            continue
        if hg[i] == 4 and dk[i] >= 17 * 60:
            continue
        if hg[i] == 6 and dk[i] < 18 * 60:
            continue
        if hg[i] in (0, 1, 2, 3) and 17 * 60 <= dk[i] < 18 * 60:
            continue
        out[i] = True
    return out


def acik_dakika(sembol: str, a, b) -> int:
    """[a, b) aralığında piyasanın açık olduğu dakika sayısı (kripto: tüm dakikalar)."""
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    if b <= a:
        return 0
    if tur(sembol) == "kripto":
        return int((b - a).total_seconds() // 60)
    dk = pd.date_range(a.ceil("min"), b - pd.Timedelta(1, "min"), freq="1min") if b - a >= pd.Timedelta(1, "min") \
        else pd.DatetimeIndex([], tz="UTC")
    return int(seans_maskesi(sembol, dk).sum())


def bayatlik(sembol: str, tf: str, son_mum_acilis, simdi, esik_dk: int) -> tuple:
    """-> (bayatlik_dk, bayat). Yaş = son mum KAPANIŞINDAN beri geçen SEANS dakikası (kripto: duvar saati); negatif olmaz.
    Eşik `durum.bayat_esigi_dk(tf)`: 2 x mum süresi + 10 dk."""
    from motor.veri.depo import aralik_suresi
    kapanis = pd.Timestamp(son_mum_acilis) + aralik_suresi(tf)
    simdi = pd.Timestamp(simdi)
    dk = acik_dakika(sembol, kapanis, simdi)
    return dk, dk > esik_dk
