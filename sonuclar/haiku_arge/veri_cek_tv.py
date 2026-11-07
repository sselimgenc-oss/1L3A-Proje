"""5 enstrüman verisini borsapy (TradingView sağlayıcısı) üzerinden çekip parquet'e yazar.

Kullanım: python sonuclar/haiku_arge/veri_cek_tv.py
Çıktı: veri/mumlar/<SEMBOL>/<aralik>.parquet (gitignore'lu, repoya girmez).

Kurallar (VERI_SOZLESMESI.md ile uyumlu):
- İndeks UTC, mumun açılış zamanı; sütunlar acilis, yuksek, dusuk, kapanis, hacim, quote_hacim, islem_sayisi.
- KİLİT: 2025-11-01 00:00 UTC ve sonrası yazılmaz (istek de bu bitişle yapılır, sonra ayrıca kesilir).
- 1d için TradingView'in yerel gün zamanı, o yerel tarihin UTC gece yarısına yazılır (günlük mum sınırı).
- quote_hacim = hacim * kapanış (yaklaşık), islem_sayisi = 0 (bilinmiyor).
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
from motor.veri.depo import MUM_DIZINI  # noqa: E402

KILIT = pd.Timestamp("2025-11-01", tz="UTC")
BASLANGIC = dt.datetime(2010, 1, 1)
BITIS = dt.datetime(2025, 11, 1)  # hariç

# bizim sembol -> {aralık: (TradingView borsa, TradingView sembolü)}; XU30 ayrı yolda (borsapy Index)
# Kaynak kısıtları (sınanmış): altında 1h yok (4h 2023-01'den); SPX 1h 2023-01'den; UKOIL 1h 2025-01'den (TV bar sınırı).
SEMBOLLER = {
    "XAUUSD": {"1d": ("OANDA", "XAUUSD"), "4h": ("OANDA", "XAUUSD")},
    "UKOIL": {"1d": ("TVC", "UKOIL"), "1h": ("TVC", "UKOIL")},
    "SPX": {"1d": ("SP", "SPX"), "1h": ("SP", "SPX")},
    "XU30": {"1d": None, "1h": None},
}


def _cek(exchange, symbol: str, aralik: str) -> pd.DataFrame:
    if symbol == "XU030":  # BIST 30 endeksi (borsapy Index)
        from borsapy import Index

        return Index("XU030").history(start=BASLANGIC, end=BITIS, interval=aralik)
    from borsapy._providers.tradingview import get_tradingview_provider

    p = get_tradingview_provider()
    return p.get_history(symbol, interval=aralik, start=BASLANGIC, end=BITIS, exchange=exchange)


def _donustur(df: pd.DataFrame, aralik: str) -> pd.DataFrame:
    if df.empty:
        raise RuntimeError("boş yanıt")
    d = df.copy()
    idx = d.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    if aralik == "1d":
        # yerel gün tarihi -> UTC gece yarısı
        idx = pd.DatetimeIndex([pd.Timestamp(t.date(), tz="UTC") for t in idx.tz_convert(idx.tz)], name="zaman")
    else:
        idx = idx.tz_convert("UTC").rename("zaman")
    out = pd.DataFrame({
        "acilis": d["Open"].astype("float64").values,
        "yuksek": d["High"].astype("float64").values,
        "dusuk": d["Low"].astype("float64").values,
        "kapanis": d["Close"].astype("float64").values,
        "hacim": d["Volume"].astype("float64").values,
    }, index=idx)
    out["quote_hacim"] = out["hacim"] * out["kapanis"]
    out["islem_sayisi"] = 0
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out = out[out.index < KILIT]  # kilit kesimi
    return out.astype({"islem_sayisi": "int64"})


def main() -> int:
    hatalar = []
    manifest = []
    for sembol, araliklar in SEMBOLLER.items():
        for aralik, kaynak in araliklar.items():
            if sembol == "XU30":
                ex, tv = "BIST", "XU030"
            else:
                ex, tv = kaynak
            try:
                df = _donustur(_cek(ex, tv, aralik), aralik)
            except Exception as e:  # görünür: listeye yazılır, sessizce atlanmaz
                hatalar.append(f"{sembol} {aralik}: {type(e).__name__}: {str(e)[:200]}")
                print(hatalar[-1])
                continue
            yol = MUM_DIZINI / sembol / f"{aralik}.parquet"
            yol.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(yol)
            kaynak_adi = f"borsapy/{ex}:{tv}"
            manifest.append({"sembol": sembol, "aralik": aralik, "kaynak": kaynak_adi, "satir": len(df),
                             "ilk": str(df.index.min()), "son": str(df.index.max())})
            print(f"{sembol} {aralik}: {len(df)} mum, {df.index.min()} -> {df.index.max()}")
    if manifest:
        pd.DataFrame(manifest).to_csv(KOK / "sonuclar" / "haiku_arge" / "veri_manifest.csv", index=False)
    if hatalar:
        print("HATALAR:")
        print("\n".join(hatalar))
    return 0 if not hatalar else 1


if __name__ == "__main__":
    sys.exit(main())
