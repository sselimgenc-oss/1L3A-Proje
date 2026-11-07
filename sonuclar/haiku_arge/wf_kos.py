"""Elenen havuzun 5 enstrümanda walk-forward taraması (Ar-Ge kolu).

Havuz: sonuclar/haiku_arge/elenen_havuz.csv (hiçbir kilit öncesi WF koşusunda karar 13'ü geçmemiş stratejiler).
Yöntem: motor/arastirma/wf_tarama.py ile AYNI (pencere, ızgara, skor, karar 13). Tek fark: veri kaynağı yolu
(5 enstrüman) ve çıktı dizinleri sonuclar/haiku_arge/ altına alındı; ana projedeki dosyalar değişmez.

Enstrümanlar ve kaynak (motorun okuduğu klasör adları):
  BTCUSDT  : Binance arşivi (5m ve türevleri)
  DK_XAU   : Dukascopy 1h (≥1h TF'ler 1h'den türetilir)
  DK_SPX   : Dukascopy 1h (2011-09 →)
  DK_UKOIL : Dukascopy 1h (2010-12 →)
  XU30     : TradingView 1h (2024 →) ve 1d (2010 →); 1d için yalnız günlük dosya yüklenir (aşağıda)

Kullanım: python sonuclar/haiku_arge/wf_kos.py [--stil swing|daytrade|scalp] [--surec 4]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from motor.arastirma import wf_tarama  # noqa: E402
from motor.veri import depo  # noqa: E402
from motor.veri.yeniden_ornekle import tf_mumlari as _tf_mumlari_orij  # noqa: E402

CIKTI = KOK / "sonuclar" / "haiku_arge" / "wf"
DENEME = KOK / "sonuclar" / "haiku_arge" / "deneme_kaydi.jsonl"
HAVUZ = KOK / "sonuclar" / "haiku_arge" / "elenen_havuz.csv"
KILIT = "2025-11-01"

# Sembol → hangi stiller (kısa TF'ler yalnız BTC'de dakikalık veriyle mümkün)
SEMBOLLER = {
    "swing": ["BTCUSDT", "DK_XAU", "DK_SPX", "DK_UKOIL", "XU30"],
    "daytrade": ["BTCUSDT", "DK_XAU", "DK_SPX", "DK_UKOIL", "XU30"],
    "scalp": ["BTCUSDT"],
}


def tf_mumlari(sembol: str, tf: str, baslangic=None, bitis=None, dizin=None, **kw) -> pd.DataFrame:
    """XU30 günlük: motorun 5m/1h'den türeten yolu yerine günlük dosyanın kendisi (TradingView, 2010 →).
    Diğer tüm semboller motorun kendi yolunu kullanır."""
    if sembol == "XU30" and tf == "1d":
        df = depo.mum_oku("XU30", "1d", baslangic, bitis, dizin=dizin)
        return df
    return _tf_mumlari_orij(sembol, tf, baslangic, bitis, dizin=dizin, **kw)


# wf_tarama tf_mumlari'yi modül adıyla kullanıyor; fork'tan önce yamanır (işçiler de yamalı görür).
wf_tarama.tf_mumlari = tf_mumlari
wf_tarama.CIKTI_DIZINI = CIKTI


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stil", choices=["swing", "daytrade", "scalp"], default="swing")
    ap.add_argument("--surec", type=int, default=4)
    a = ap.parse_args()

    h = pd.read_csv(HAVUZ)
    stratejiler = sorted(h.loc[h.stil == a.stil, "strateji"].unique().tolist())
    etiket = f"haiku_elenen_{a.stil}"
    print(f"[kos] {etiket}: {len(stratejiler)} strateji x {SEMBOLLER[a.stil]}", flush=True)
    sonuc = wf_tarama.wf_tara(
        etiket, stratejiler=stratejiler, semboller=SEMBOLLER[a.stil], surec=a.surec,
        bitis=KILIT, izgara=True, cikti_dizini=CIKTI, deneme_kaydi_yolu=DENEME,
    )
    print(f"[kos] bitti: {len(sonuc)} satır, geçen {int(sonuc['gecti'].astype(str).str.lower().eq('true').sum()) if len(sonuc) else 0}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
