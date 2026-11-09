"""D10-B (kuyruk yeni_aile satırlarının kodu, b payı) için göstergeler / yardımcılar. Hepsi nedensel: t. satır yalnız t. mum
kapanışına kadar olan veriyi kullanır. Paylaşılan dosyalara dokunulmaz.

  haftalik_ust, gun_ust      alt TF mumlarından (günlük / saatlik) tamamlanmış hafta / gün özeti; değer yalnız bar KAPANDIKTAN
                             sonra (hafta: sonraki Pazartesi 00:00 UTC, gün: ertesi gün 00:00 UTC) kullanılabilir. htf.ust_zaman'dan
                             farkı: hafta/gün "eksik mi" diye mum SAYMAZ (hisse/BIST gibi haftada 5 günlü veride de çalışır).
  ibs, verimlilik_orani      mum içi kapanış gücü; Kaufman verimlilik oranı.
  adl, obv                   Chaikin birikim/dağılım çizgisi ve OBV (kümülatif; farkları nedensel).
  pivot_noktalari            onaylı pivot: değer, pivot `n` mum SONRA (onay anında) görünür.
  boga_yutan, ayi_yutan      yutan mum.
  paskalya_kalan_gun         mumun gününden o yılın Paskalya Pazarı'na kalan takvim günü.
"""
import numpy as np
import pandas as pd
from dateutil.easter import easter


def _gun_baslangici(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.floor("D")


def _ozet_ohlcv(m: pd.DataFrame, anahtar) -> pd.DataFrame:
    g = m.groupby(anahtar)
    veri = {"acilis": g["acilis"].first(), "yuksek": g["yuksek"].max(), "dusuk": g["dusuk"].min(),
            "kapanis": g["kapanis"].last()}
    veri["hacim"] = g["hacim"].sum() if "hacim" in m.columns else pd.Series(0.0, index=veri["acilis"].index)
    return pd.DataFrame(veri)


def _hizala(sonuc, m: pd.DataFrame, sure: pd.Timedelta):
    sonuc = sonuc.copy()
    sonuc.index = sonuc.index + sure           # kapanış anından itibaren kullanılabilir
    return sonuc.reindex(m.index, method="ffill")


def haftalik_ust(m: pd.DataFrame, fonk):
    """Mumları Pazartesi 00:00 UTC hizalı haftalara toplar, fonk(hafta_df) hesaplar, sonucu alt TF indeksine taşır.
    Hafta W'nin değeri W+7 gününden (sonraki Pazartesi 00:00 UTC) itibaren geçerlidir; kapanmamış hafta asla görülmez."""
    gun = _gun_baslangici(m.index)
    hafta = gun - pd.to_timedelta(gun.dayofweek, unit="D")
    return _hizala(fonk(_ozet_ohlcv(m, hafta)), m, pd.Timedelta(days=7))


def gun_ust(m: pd.DataFrame, fonk):
    """Mumları UTC günlerine toplar (saatlik/30dk veri için), fonk(gun_df) hesaplar; gün D'nin değeri D+1 00:00 UTC'den
    itibaren geçerlidir."""
    return _hizala(fonk(_ozet_ohlcv(m, _gun_baslangici(m.index))), m, pd.Timedelta(days=1))


def ibs(m: pd.DataFrame) -> pd.Series:
    """Internal Bar Strength: (kapanış - dip) / (zirve - dip); aralık 0 ise NaN."""
    aralik = (m["yuksek"] - m["dusuk"]).where(m["yuksek"] > m["dusuk"])
    return (m["kapanis"] - m["dusuk"]) / aralik


def verimlilik_orani(kapanis: pd.Series, n: int) -> pd.Series:
    """Kaufman ER: |c - c[n önce]| / son n kapanış farkının mutlak toplamı (0..1)."""
    gurultu = kapanis.diff().abs().rolling(n, min_periods=n).sum()
    return (kapanis - kapanis.shift(n)).abs() / gurultu.where(gurultu > 0)


def adl(m: pd.DataFrame) -> pd.Series:
    """Chaikin birikim/dağılım çizgisi: kümülatif ((C-L)-(H-C))/(H-L) x hacim. Aralık 0 ise katkı 0."""
    aralik = (m["yuksek"] - m["dusuk"]).where(m["yuksek"] > m["dusuk"])
    mfm = (((m["kapanis"] - m["dusuk"]) - (m["yuksek"] - m["kapanis"])) / aralik).fillna(0.0)
    return (mfm * m["hacim"]).cumsum()


def obv(m: pd.DataFrame) -> pd.Series:
    """On-balance volume: kapanış artarsa +hacim, düşerse -hacim."""
    yon = np.sign(m["kapanis"].diff()).fillna(0.0)
    return (yon * m["hacim"]).cumsum()


def pivot_noktalari(seri: pd.Series, n: int, tepe: bool) -> pd.Series:
    """t. satırda: t-n. mum, solundaki n ve sağındaki n mumdan uçsa (tepe: en yüksek, aksi en düşük) onun değeri (onay
    anı t), değilse NaN. Pivot n mum gecikmeyle görünür (lookahead yok)."""
    n = int(n)
    w = 2 * n + 1
    uc = seri.rolling(w, min_periods=w).max() if tepe else seri.rolling(w, min_periods=w).min()
    aday = seri.shift(n)
    return aday.where(aday == uc)


def boga_yutan(m: pd.DataFrame) -> pd.Series:
    o, c = m["acilis"], m["kapanis"]
    return (c > o) & (c.shift(1) < o.shift(1)) & (c >= o.shift(1)) & (o <= c.shift(1))


def ayi_yutan(m: pd.DataFrame) -> pd.Series:
    o, c = m["acilis"], m["kapanis"]
    return (c < o) & (c.shift(1) > o.shift(1)) & (c <= o.shift(1)) & (o >= c.shift(1))


def paskalya_kalan_gun(index: pd.DatetimeIndex) -> np.ndarray:
    """Mumun (UTC) gününden o yılın Paskalya Pazarı'na kalan takvim günü (Pazar=0, Kutsal Perşembe=3). Takvim bilgisi
    gelecek FİYATI değildir (lookahead yok)."""
    gun = index.tz_localize(None) if index.tz is not None else index
    gun = gun.normalize()
    pask = {int(y): pd.Timestamp(easter(int(y))) for y in np.unique(gun.year)}
    hedef = pd.DatetimeIndex([pask[int(y)] for y in gun.year])
    return np.asarray((hedef - gun).days)
