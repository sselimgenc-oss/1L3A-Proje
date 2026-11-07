"""Portföy backtest'i için çok sembollü veri yükleme. Okuma YALNIZ depo.mum_oku / funding_oku ile yapılır:
kilitli dönem (karar 20) depo tarafından kesilir; `kilit_ac` varsayılanı False'tur (yalnız onaylı kilitli dönem testi açar)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from motor.veri import depo
from motor.veri.yeniden_ornekle import yeniden_ornekle


def mum_yukle(sembol: str, tf: str, baslangic=None, bitis=None, dizin: Optional[Path] = None,
              eksikleri_at: Optional[bool] = None, kilit_ac: bool = False, gerekce: Optional[str] = None) -> pd.DataFrame:
    """tf mumları. Kaynak: 5m dosyası varsa 5m; yoksa ve tf >= 1h ise 1h. `eksikleri_at=None` (varsayılan): tf_mumlari
    ile aynı kural (DK_ seans modu, kripto eski kural). Açık True/False verilirse eski doğrudan yeniden örnekleme."""
    if eksikleri_at is None:
        # Tek-grafik araştırmasıyla aynı kaynak/seans kuralı (yeniden_ornekle.tf_mumlari): DK_ sembollerinde
        # seans modu (kısmi seans mumları tutulur, ABD hisselerinde 4h NY hizalı), kriptoda eski kural.
        from motor.veri.yeniden_ornekle import tf_mumlari
        return tf_mumlari(sembol, tf, baslangic, bitis, dizin=dizin, kilit_ac=kilit_ac, gerekce=gerekce)
    if depo.mum_yolu(sembol, "5m", dizin).exists():
        return yeniden_ornekle(depo.mum_oku(sembol, "5m", baslangic, bitis, dizin=dizin, kilit_ac=kilit_ac, gerekce=gerekce), tf, "5m", eksikleri_at)
    if depo.mum_yolu(sembol, "1h", dizin).exists():
        if depo.aralik_suresi(tf) < pd.Timedelta(1, "h"):
            raise ValueError(f"{sembol}: yalnız 1h var; {tf} üretilemez")
        return yeniden_ornekle(depo.mum_oku(sembol, "1h", baslangic, bitis, dizin=dizin, kilit_ac=kilit_ac, gerekce=gerekce), tf, "1h", eksikleri_at)
    return depo.mum_oku(sembol, "5m", baslangic, bitis, dizin=dizin, kilit_ac=kilit_ac, gerekce=gerekce)     # FileNotFoundError (açık mesaj)


def veri_yukle(semboller, tf: str, baslangic=None, bitis=None, dizin: Optional[Path] = None,
               kilit_ac: bool = False, gerekce: Optional[str] = None):
    """-> (veriler, fundingler): {sembol: mum DataFrame}, {sembol: funding DataFrame} (dosyası olanlar).
    Mum DataFrame'lerinde `eksik` sütunu (varsa) düşürülür."""
    veriler, fundingler = {}, {}
    for s in semboller:
        df = mum_yukle(s, tf, baslangic, bitis, dizin, kilit_ac=kilit_ac, gerekce=gerekce)
        veriler[s] = df.drop(columns="eksik") if "eksik" in df.columns else df
        if depo.funding_yolu(s, dizin).exists():
            fundingler[s] = depo.funding_oku(s, baslangic, bitis, dizin=dizin, kilit_ac=kilit_ac, gerekce=gerekce)
    return veriler, fundingler
