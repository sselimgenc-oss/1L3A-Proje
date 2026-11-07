"""Mumları üst zaman dilimine birleştirme (UTC sınırlarına hizalı)."""
from __future__ import annotations

import pandas as pd

from motor.veri.depo import aralik_suresi


def yeniden_ornekle(df: pd.DataFrame, hedef: str, kaynak: str = "5m",
                    eksikleri_at: bool = False, esik_orani: float | None = None,
                    yerel: tuple[str, int] | None = None) -> pd.DataFrame:
    """OHLCV'yi `kaynak` aralığından `hedef` aralığına birleştirir.

    Çıktı sözleşmedeki sütunlara ek olarak `eksik` (bool) sütunu taşır: periyottaki
    kaynak mum sayısı beklenenden azsa True (ör. 1h için 12'den az 5m mum).
    Hiç mumu olmayan periyotlar çıktıda yer almaz. eksikleri_at=True ise eksik
    periyotlar atılır.

    SEANSLI PİYASALAR (hisse/emtia; 24/7 olmayan): `esik_orani` verilirse "eksik" tanımı değişir: periyottaki kaynak
    mum sayısı, tüm periyotların MEDYAN sayısının `esik_orani` katından azsa eksiktir (kısmi seans periyotları -
    yarım saatlik ilk mum, yarım gün, hisse 1d'si - tutulur). `yerel=(saat_dilimi, saat)` verilirse 2h..<1d hedefler
    periyot sınırlarını o saat diliminde `saat`'e hizalar (DST doğru; ör. ("America/New_York", 9): 4h kovaları
    09-13, 13-17 NY). Çıktı indeksi yine UTC. Varsayılanlarda (None) davranış değişmez (kripto)."""
    kaynak_s, hedef_s = aralik_suresi(kaynak), aralik_suresi(hedef)
    if hedef_s < kaynak_s or hedef_s % kaynak_s != pd.Timedelta(0):
        raise ValueError(f"{kaynak} -> {hedef} birleştirilemez")
    beklenen = int(hedef_s / kaynak_s)
    if yerel is not None and pd.Timedelta(2, "h") <= hedef_s < pd.Timedelta(1, "D"):
        zon, saat = yerel
        kayma = pd.Timedelta(saat, "h")
        yer = df.index.tz_convert(zon).tz_localize(None)
        anahtar = ((yer - kayma).floor(hedef_s) + kayma).tz_localize(zon, ambiguous="NaT", nonexistent="shift_forward")
        anahtar = anahtar.tz_convert("UTC")
        df = df[~anahtar.isna()]
        g = df.groupby(anahtar[~anahtar.isna()])
    else:
        g = df.groupby(df.index.floor(hedef_s))
    cikti = pd.DataFrame({
        "acilis": g["acilis"].first(),
        "yuksek": g["yuksek"].max(),
        "dusuk": g["dusuk"].min(),
        "kapanis": g["kapanis"].last(),
        "hacim": g["hacim"].sum(),
        "quote_hacim": g["quote_hacim"].sum(),
        "islem_sayisi": g["islem_sayisi"].sum().astype("int64"),
    })
    sayi = g["acilis"].count()
    if esik_orani is None:
        cikti["eksik"] = sayi < beklenen
    else:
        cikti["eksik"] = sayi < esik_orani * sayi.median()
    cikti.index.name = "zaman"
    if eksikleri_at:
        cikti = cikti[~cikti["eksik"]].drop(columns="eksik")
    return cikti


# Seanslı (24/7 olmayan) Dukascopy sembolleri: "DK_" öneki. ABD hisseleri NY 09:00'a hizalı 4h kovası kullanır.
ABD_HISSELERI = ("DK_AAPL", "DK_MSFT", "DK_GOOGL", "DK_AMZN", "DK_NVDA", "DK_META", "DK_TSLA")
SEANS_ESIK_ORANI = 0.25


def _seans_ayari(sembol: str) -> dict:
    if not sembol.startswith("DK_"):
        return {}          # kripto (24/7): eski davranış, tam dolu periyot şartı
    ayar: dict = {"esik_orani": SEANS_ESIK_ORANI}
    if sembol in ABD_HISSELERI:
        ayar["yerel"] = ("America/New_York", 9)
    return ayar


def tf_mumlari(sembol: str, tf: str, baslangic=None, bitis=None, dizin=None) -> pd.DataFrame:
    """Araştırma için `tf` mumları (eksikleri atılmış). Kaynak: 5m dosyası varsa 5m; yoksa ve tf >= 1h ise 1h dosyası
    (Dukascopy aylık saatlik mod, bkz. motor/veri/dukascopy.py); 1h dosyası var ama tf < 1h ise AÇIK HATA (ValueError).
    Hiçbiri yoksa FileNotFoundError. Okuma yalnız depo.mum_oku ile (kilit_ac yok: kilitli dönem kesilir).
    Seanslı semboller (DK_*) için `yeniden_ornekle`nin seans modu kullanılır (kısmi seans mumları tutulur, ABD
    hisselerinde 4h NY 09:00'a hizalı; 1d = UTC günü = seans günü)."""
    from motor.veri import depo   # döngüsel içe aktarmayı önlemek için yerel
    ek = _seans_ayari(sembol)
    # Kaynak sabitleme (lider kararı 2026-11-07, karar 26 günlüğü): DK_ sembollerinde tf >= 1h ise HER ZAMAN 1h dosyası
    # kullanılır. Dakikalık indirme sürerken 5m dosyası sonradan ortaya çıkıp kaynağı değiştirmesin (tekrarlanabilirlik),
    # ayrıca 1h dosyası tam (5m'de indirilemeyen günler var). 5m yalnız tf < 1h için.
    if (sembol.startswith("DK_") and depo.aralik_suresi(tf) >= pd.Timedelta(1, "h")
            and depo.mum_yolu(sembol, "1h", dizin).exists()):
        return yeniden_ornekle(depo.mum_oku(sembol, "1h", baslangic, bitis, dizin=dizin), tf, kaynak="1h",
                               eksikleri_at=True, **ek)
    if depo.mum_yolu(sembol, "5m", dizin).exists():
        return yeniden_ornekle(depo.mum_oku(sembol, "5m", baslangic, bitis, dizin=dizin), tf, kaynak="5m",
                               eksikleri_at=True, **ek)
    if depo.mum_yolu(sembol, "1h", dizin).exists():
        if depo.aralik_suresi(tf) < pd.Timedelta(1, "h"):
            raise ValueError(f"{sembol}: 5m verisi yok, yalnız 1h var; {tf} bu kaynaktan üretilemez (tf >= 1h olmalı)")
        return yeniden_ornekle(depo.mum_oku(sembol, "1h", baslangic, bitis, dizin=dizin), tf, kaynak="1h",
                               eksikleri_at=True, **ek)
    return depo.mum_oku(sembol, "5m", baslangic, bitis, dizin=dizin)   # FileNotFoundError (açık mesaj)
