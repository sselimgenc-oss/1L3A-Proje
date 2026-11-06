"""Diskteki parquet verisini okuma (VERI_SOZLESMESI.md) ve boşluk raporu."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[2]
MUM_DIZINI = KOK / "veri" / "mumlar"

MUM_SUTUNLARI = ["acilis", "yuksek", "dusuk", "kapanis", "hacim", "quote_hacim", "islem_sayisi"]


def aralik_suresi(aralik: str) -> pd.Timedelta:
    """'5m', '1h', '4h', '1d' -> Timedelta."""
    birim = aralik[-1]
    try:
        n = int(aralik[:-1])
    except ValueError:
        raise ValueError(f"Geçersiz aralık: {aralik!r}") from None
    carpan = {"m": "min", "h": "h", "d": "D"}.get(birim)
    if carpan is None or n <= 0:
        raise ValueError(f"Geçersiz aralık: {aralik!r}")
    return pd.Timedelta(n, carpan)


def mum_yolu(sembol: str, aralik: str, dizin: Path | None = None) -> Path:
    return (dizin or MUM_DIZINI) / sembol / f"{aralik}.parquet"


def funding_yolu(sembol: str, dizin: Path | None = None) -> Path:
    return (dizin or MUM_DIZINI) / sembol / "funding.parquet"


def _utc(t):
    if t is None:
        return None
    t = pd.Timestamp(t)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _kes(df: pd.DataFrame, baslangic, bitis) -> pd.DataFrame:
    """[baslangic, bitis) aralığı (bitis hariç)."""
    b, e = _utc(baslangic), _utc(bitis)
    if b is not None:
        df = df[df.index >= b]
    if e is not None:
        df = df[df.index < e]
    return df


def mum_oku(sembol: str, aralik: str, baslangic=None, bitis=None,
            dizin: Path | None = None) -> pd.DataFrame:
    """Mum verisi; indeks UTC açılış zamanı. Aralık [baslangic, bitis)."""
    yol = mum_yolu(sembol, aralik, dizin)
    if not yol.exists():
        raise FileNotFoundError(f"Veri yok: {yol} (önce: python -m motor.veri.indir {sembol} --aralik {aralik})")
    return _kes(pd.read_parquet(yol), baslangic, bitis)


def funding_oku(sembol: str, baslangic=None, bitis=None,
                dizin: Path | None = None) -> pd.DataFrame:
    yol = funding_yolu(sembol, dizin)
    if not yol.exists():
        raise FileNotFoundError(f"Funding verisi yok: {yol} (önce: python -m motor.veri.indir {sembol} --funding)")
    return _kes(pd.read_parquet(yol), baslangic, bitis)


def bosluk_raporu(df: pd.DataFrame, aralik: str) -> list[tuple[pd.Timestamp, pd.Timestamp, int]]:
    """Eksik mum aralıkları: [(ilk_eksik_zaman, son_eksik_zaman, eksik_mum_sayisi), ...]."""
    if len(df) < 2:
        return []
    adim = aralik_suresi(aralik)
    idx = df.index
    farklar = idx[1:] - idx[:-1]
    sonuc = []
    for i in (farklar > adim).nonzero()[0]:
        adet = int(farklar[i] / adim) - 1
        sonuc.append((idx[i] + adim, idx[i + 1] - adim, adet))
    return sonuc
