"""Dukascopy'den SPX ve Brent (UKOIL) saatlik verisi (2010 → 2025-11-01 hariç).

Ana proje modülü (motor/veri/dukascopy.py) DEĞİŞTİRİLMEZ; sembol eşlemesi yalnızca bu süreçte
(runtime) eklenir. Veri, indiricinin kendi önbellek ve yeniden deneme mantığıyla yazılır:
  veri/mumlar/_ham/dukascopy/<SEMBOL>/...   (ham önbellek)
  veri/mumlar/DK_SPX/1h.parquet, veri/mumlar/DK_UKOIL/1h.parquet

Kullanım: python sonuclar/haiku_arge/dk_indir.py
"""
from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

import motor.veri.dukascopy as dk  # noqa: E402

# Dukascopy adları (doğrulanacak: fiyat ölçeği NOKTA ilk veriyle TradingView ile karşılaştırılır)
dk.SEMBOLLER["DK_SPX"] = "USA500IDXUSD"
dk.SEMBOLLER["DK_UKOIL"] = "BRENTCMDUSD"
dk.NOKTA.setdefault("DK_SPX", 1000)
dk.NOKTA.setdefault("DK_UKOIL", 1000)

if __name__ == "__main__":
    # Bitiş 2025-10-31 (hariç): 2025-11 aylık dosyası hiç istenmez (kilit). Bedeli: 31 Ekim saatleri düşer.
    sys.exit(dk.main(["--semboller", "DK_SPX", "DK_UKOIL", "--aralik", "1h",
                      "--baslangic", "2010-01", "--bitis", "2025-10-31"]))
