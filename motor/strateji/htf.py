"""Üst zaman dilimi (HTF) hizalama — lookahead'siz.

ust_zaman(mumlar, aralik, fonk): alt TF mumlarını üst TF'ye çevirir, fonk(ust_df) hesaplar ve sonucu
alt TF indeksine, değeri YALNIZCA üst TF mumu KAPANDIKTAN sonra kullanılabilir olacak biçimde ileri doldurur.
  - Üst mum T'de açılıp D süre sürerse değeri T+D'den itibaren (T+D'de açılan alt mum dahil) geçerlidir.
    Örn. 1d mumu: değeri ertesi gün 00:00 UTC'den itibaren. 1w: Pazartesi 00:00 UTC hizalı, değeri
    sonraki Pazartesi 00:00'dan itibaren.
  - Eksik (kaynak mumu beklenenden az) üst mumlar atılır; veri başında/sonunda kısmi kalan mum da dahil.
    SEANSLI veri (hisse/BIST/emtia: kapsanan sürede kaynak mumlarının %90'ından azı mevcut) için "eksik" =
    medyanın %25'inden az kaynak mumu (yeniden_ornekle.SEANS_ESIK_ORANI ile aynı kural). Aksi halde seanslı
    piyasalarda tüm günlük/haftalık mumlar eksik sayılıp atılıyor ve HTF süzgeci hep NaN kalıyordu (2026-11-07 düzeltmesi).
    Lookahead açısından fark yok: değer her durumda üst mum süresi dolduktan sonra kullanılır.
  - İlk üst mum kapanmadan önceki alt satırlar NaN olur.
Alt TF mumlar fonk'a hiç verilmez; fonk yalnız tamamlanmış üst TF mumlarını görür.
"""
import pandas as pd

from motor.strateji.seans_takvimi import mum_suresi
from motor.veri.depo import aralik_suresi
from motor.veri.yeniden_ornekle import yeniden_ornekle

_OPSIYONEL = ["hacim", "quote_hacim", "islem_sayisi"]
_HAFTA = pd.Timedelta(days=7)


def _aralik_str(td: pd.Timedelta) -> str:
    for birim, k in (("d", pd.Timedelta(days=1)), ("h", pd.Timedelta(hours=1)), ("m", pd.Timedelta(minutes=1))):
        if td % k == pd.Timedelta(0):
            return f"{int(td / k)}{birim}"
    raise ValueError(f"Alt TF aralığı tespit edilemedi: {td}")


_SEANS_ESIK_ORANI = 0.25


def _seansli_seri(index: pd.DatetimeIndex, anahtar, kaynak_s: pd.Timedelta) -> pd.Series:
    """NEDENSEL seans sınıflaması (B02): her üst periyot k için, YALNIZ k'nın sonuna kadarki veriyle: gözlenen kaynak mumu sayısı
    (kümülatif) beklenenin (ilk mumdan k'nın son gözlemine kadar) %90'ından azsa seanslı (kripto ~%100; emtia ~%68, BIST ~%24,
    ABD hisse ~%19). Eskiden tüm serinin doluluğu kullanılıyordu: sonradan veri eklenince geçmiş değer değişiyordu."""
    anahtar = pd.DatetimeIndex(anahtar)
    sayi = pd.Series(1, index=index).groupby(anahtar).sum()
    son = pd.Series(index, index=index).groupby(anahtar).max()
    beklenen = (son - index[0]) / kaynak_s + 1
    return sayi.cumsum() < 0.9 * beklenen


def _eksik(sayi: pd.Series, beklenen: int, seansli: pd.Series) -> pd.Series:
    """Üst periyot eksik mi? `seansli`: periyot indeksli bool Series (nedensel, _seansli_seri). 24/7: tam doluluk şartı.
    Seanslı: önceki periyotların EXPANDING medyanının %25'inden az (geçmiş yoksa eksik sayılmaz); gelecek veri hiçbir
    periyotun bayrağını değiştirmez."""
    onceki = sayi.expanding().median().shift(1).fillna(sayi)
    seans_eksik = sayi < _SEANS_ESIK_ORANI * onceki
    return seans_eksik.where(seansli.reindex(sayi.index).fillna(False).astype(bool), sayi < beklenen)


def _haftalik(df: pd.DataFrame, kaynak_s: pd.Timedelta) -> pd.DataFrame:
    gun = df.index.floor("D")
    hafta = gun - pd.to_timedelta(gun.dayofweek, unit="D")      # Pazartesi 00:00 UTC
    g = df.groupby(hafta)
    c = pd.DataFrame({
        "acilis": g["acilis"].first(), "yuksek": g["yuksek"].max(),
        "dusuk": g["dusuk"].min(), "kapanis": g["kapanis"].last(),
        "hacim": g["hacim"].sum(), "quote_hacim": g["quote_hacim"].sum(),
        "islem_sayisi": g["islem_sayisi"].sum().astype("int64"),
    })
    c["eksik"] = _eksik(g["acilis"].count(), int(_HAFTA / kaynak_s), _seansli_seri(df.index, hafta, kaynak_s))
    c.index.name = "zaman"
    return c


def ust_zaman(mumlar: pd.DataFrame, aralik: str, fonk):
    """-> mumlarla aynı indeksli Series/DataFrame (fonk'un döndürdüğü türde)."""
    if len(mumlar) < 2:
        raise ValueError("En az 2 mum gerekli")
    kaynak_s = mum_suresi(mumlar.index)
    ust_s = _HAFTA if aralik == "1w" else aralik_suresi(aralik)
    if ust_s <= kaynak_s or ust_s % kaynak_s != pd.Timedelta(0):
        raise ValueError(f"{aralik} üst TF olarak kullanılamaz (alt TF {kaynak_s})")

    df = mumlar.copy()
    for c in _OPSIYONEL:
        if c not in df.columns:
            df[c] = 0.0
    if aralik == "1w":
        ust = _haftalik(df, kaynak_s)
    else:
        ust = yeniden_ornekle(df, aralik, _aralik_str(kaynak_s))
        anahtar = df.index.floor(ust_s)
        sayi = df.groupby(anahtar)["acilis"].count()
        ust["eksik"] = _eksik(sayi, int(ust_s / kaynak_s), _seansli_seri(df.index, anahtar, kaynak_s)).reindex(ust.index).fillna(True)
    ust = ust[~ust["eksik"]].drop(columns="eksik")

    sonuc = fonk(ust)
    sonuc = sonuc.copy()
    sonuc.index = sonuc.index + ust_s           # kapanış anından itibaren kullanılabilir
    sonuc = sonuc.reindex(mumlar.index, method="ffill")
    return sonuc
