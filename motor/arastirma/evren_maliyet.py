"""Evren testi maliyet tablosu (ON_KAYIT Güncelleme 5, madde 4).

Tablo: sonuclar/evren/maliyet_tablosu.csv (koşulardan ÖNCE yazılır ve sabitlenir; sha256'sı çıktılara yazılır).
Sütunlar: sembol, sinif, komisyon_oran (taraf başına), spread_kayma_oran (taraf başına; yarım spread + kayma), stop_kayma_oran
(stop/zorunlu çıkış tarafı), funding ("gercek_seri": motor funding.parquet'i işler; "yok": bu enstrümanda funding/gece finansmanı
modellenmiyor), bsmv_oran (komisyonun yüzdesi olarak ek vergi; BIST 0.05), efektif_komisyon_oran (= komisyon_oran*(1+bsmv_oran)),
tutucu ("evet": kesin bilinmiyor, yüksek tarafı seçildi), kaynak.

Motor eşlemesi (maliyet_ayarlari): komisyon_taker_yuzde = efektif_komisyon*100, kayma_bps = spread_kayma*1e4,
stop_kayma_bps = stop_kayma*1e4. `carpan` (K1 stres) komisyon ve kaymaları çarpar; funding çarpılmaz (gerçek seri).
Tabloda olmayan sembol AÇIK HATA verir (sessiz varsayılan yok).
"""
from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path

import pandas as pd

from motor.backtest.motor import MotorAyarlari

TABLO_YOLU = Path(__file__).resolve().parents[2] / "sonuclar" / "evren" / "maliyet_tablosu.csv"
SUTUNLAR = ["sembol", "sinif", "komisyon_oran", "spread_kayma_oran", "stop_kayma_oran", "funding", "bsmv_oran",
            "efektif_komisyon_oran", "tutucu", "kaynak"]
_ONB: dict = {}


def tablo_hash(yol=None) -> str:
    return hashlib.sha256(Path(yol or TABLO_YOLU).read_bytes()).hexdigest()


def yukle(yol=None) -> pd.DataFrame:
    yol = Path(yol or TABLO_YOLU)
    anahtar = (str(yol), yol.stat().st_mtime_ns)
    if anahtar not in _ONB:
        d = pd.read_csv(yol)
        eksik = [c for c in SUTUNLAR if c not in d.columns]
        if eksik:
            raise ValueError(f"maliyet tablosunda eksik sütun: {eksik}")
        if d["sembol"].duplicated().any():
            raise ValueError("maliyet tablosunda tekrarlı sembol")
        _ONB.clear()
        _ONB[anahtar] = d.set_index("sembol")
    return _ONB[anahtar]


def satir(sembol: str, yol=None) -> pd.Series:
    d = yukle(yol)
    if sembol not in d.index:
        raise KeyError(f"{sembol}: maliyet tablosunda yok ({Path(yol or TABLO_YOLU).name}); sessiz varsayılan kullanılmaz")
    return d.loc[sembol]


def sembol_maliyeti(sembol: str, carpan: float = 1.0, yol=None) -> tuple:
    """-> (taker_yuzde, maker_yuzde, kayma_bps, stop_kayma_bps), carpan uygulanmış."""
    if not carpan > 0:
        raise ValueError("carpan > 0 olmalı")
    r = satir(sembol, yol)
    taker = float(r["efektif_komisyon_oran"]) * 100.0
    maker = taker * (0.4 if r["sinif"] == "kripto" else 1.0)     # maker yalnız hedef_limit_emri açıkken kullanılır
    return (taker * carpan, maker * carpan, float(r["spread_kayma_oran"]) * 1e4 * carpan,
            float(r["stop_kayma_oran"]) * 1e4 * carpan)


def maliyet_ayarlari(sembol: str, kurallar, carpan: float = 1.0, yol=None) -> MotorAyarlari:
    """Tablodan MotorAyarlari (araştırma modu: limit_modu='olc'). carpan: komisyon ve kayma çarpanı (1.0 = tablo)."""
    taker, maker, kayma, stop = sembol_maliyeti(sembol, carpan, yol)
    v = MotorAyarlari(limit_modu="olc", kurallar=kurallar)
    return dataclasses.replace(v, komisyon_taker_yuzde=taker, komisyon_maker_yuzde=maker, kayma_bps=kayma,
                               stop_kayma_bps=stop)


# ---------------------------------------------------------------------------- tablonun üretimi (bir kez; sonra dosya sabit)
def _satirlar() -> list:
    S = []

    def ekle(sembol, sinif, kom, kayma_bps, stop_bps, funding, bsmv, tutucu, kaynak):
        S.append(dict(sembol=sembol, sinif=sinif, komisyon_oran=kom, spread_kayma_oran=kayma_bps / 1e4,
                      stop_kayma_oran=stop_bps / 1e4, funding=funding, bsmv_oran=bsmv,
                      efektif_komisyon_oran=round(kom * (1 + bsmv), 8), tutucu=tutucu, kaynak=kaynak))
    k_bin = "Binance USDⓈ-M taker %0.05 (VIP0, BNB indirimi yok). 2017-2019 spot vekil döneminde de aynı maliyet varsayılır (funding yok)."
    for s in ("BTCUSDT", "ETHUSDT"):
        ekle(s, "kripto", 0.0005, 2, 5, "gercek_seri", 0.0, "hayir", k_bin + " Kayma 2 bps / stop 5 bps = motorun önceki varsayılanı (en likit perp'ler).")
    for s in ("BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "TRXUSDT"):
        ekle(s, "kripto", 0.0005, 3, 8, "gercek_seri", 0.0, "evet", k_bin + " Büyük altcoin: kayma/stop-kayma BTC'den yüksek tutuldu (tahmin).")
    for s in ("ZECUSDT", "HYPEUSDT", "XLMUSDT", "BCHUSDT"):
        ekle(s, "kripto", 0.0005, 5, 12, "gercek_seri", 0.0, "evet", k_bin + " Daha ince derinlik: kayma 5 / stop 12 bps (tutucu tahmin).")
    k_dk = ("Komisyon: canlı yer Binance TradFi perp (karar 22) taker %0.05 varsayıldı, kesin ücret doğrulanmadı (tutucu). "
            "Kayma: Dukascopy/CFD tipik spread'inin yarısı + kayma; funding/gece finansmanı modellenmiyor.")
    for s in ("DK_AAPL", "DK_MSFT", "DK_GOOGL", "DK_AMZN", "DK_META", "DK_JPM", "DK_V", "DK_MA", "DK_WMT", "DK_JNJ", "DK_XOM"):
        ekle(s, "hisse", 0.0005, 3, 10, "yok", 0.0, "evet", k_dk + " ABD mega-cap hisse CFD: tipik toplam spread ~6 bps.")
    for s in ("DK_NVDA", "DK_TSLA", "DK_AVGO", "DK_LLY", "DK_AMD", "DK_MU"):
        ekle(s, "hisse", 0.0005, 4, 12, "yok", 0.0, "evet", k_dk + " Yüksek fiyat/oynaklık hisse CFD: tipik toplam spread ~8 bps.")
    ekle("DK_SPX", "hisse", 0.0005, 1.5, 4, "yok", 0.0, "evet", k_dk + " S&P 500 endeks CFD: toplam spread ~3 bps.")
    ekle("DK_XAU", "emtia", 0.0005, 1.5, 4, "yok", 0.0, "evet", k_dk + " XAUUSD: toplam spread ~3 bps.")
    ekle("DK_XAG", "emtia", 0.0005, 4, 10, "yok", 0.0, "evet", k_dk + " XAGUSD: toplam spread ~8 bps.")
    ekle("DK_WTI", "emtia", 0.0005, 4, 10, "yok", 0.0, "evet", k_dk + " WTI petrol CFD: toplam spread ~8 bps.")
    ekle("DK_COPPER", "emtia", 0.0005, 5, 12, "yok", 0.0, "evet", k_dk + " Bakır CFD: toplam spread ~10 bps (tahmin).")
    ekle("DK_NATGAS", "emtia", 0.0005, 8, 20, "yok", 0.0, "evet", k_dk + " Doğalgaz CFD: toplam spread ~16 bps (tahmin).")
    k_bist = ("BIST aracı kurum komisyonu ~%0.04 taraf başına (tipik, kuruma göre değişir) + BSMV (komisyonun %5'i). "
              "Spread: BIST 30 hisse tick'i ~%0.03-0.08; yarım spread + kayma.")
    for s in ("AKBNK", "ASELS", "BIMAS", "EREGL", "FROTO", "KCHOL", "SISE", "TCELL", "THYAO", "TUPRS"):
        ekle("BIST_" + s, "bist", 0.0004, 4, 12, "yok", 0.05, "evet", k_bist + " Likit BIST-30 hissesi.")
    for s in ("ASTOR", "EKGYO", "TRALT"):
        ekle("BIST_" + s, "bist", 0.0004, 6, 18, "yok", 0.05, "evet", k_bist + " Daha az likit / yüksek oynaklık: kayma 6 / stop 18 bps (tahmin).")
    ekle("BIST_XU030", "bist", 0.0004, 3, 10, "yok", 0.05, "evet", k_bist + " Endeks doğrudan işlem görmez (VİOP vekil); tutucu tahmin. Scalp evreninden çıkarıldı, yalnız bütünlük için.")
    return S


def tabloyu_yaz(yol=None) -> Path:
    yol = Path(yol or TABLO_YOLU)
    yol.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(_satirlar(), columns=SUTUNLAR).to_csv(yol, index=False)
    (yol.with_suffix(".sha256")).write_text(tablo_hash(yol) + "\n")
    return yol


if __name__ == "__main__":
    print(tabloyu_yaz(), tablo_hash())
