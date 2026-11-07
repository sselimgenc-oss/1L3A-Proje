"""Portföy backtest'i için çok sembollü veri yükleme. Okuma YALNIZ depo.mum_oku / funding_oku ile yapılır:
kilitli dönem (karar 20) depo tarafından kesilir; burada `kilit_ac` YOKTUR."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from motor.veri import depo
from motor.veri.yeniden_ornekle import yeniden_ornekle


def mum_yukle(sembol: str, tf: str, baslangic=None, bitis=None, dizin: Optional[Path] = None,
              eksikleri_at: Optional[bool] = None) -> pd.DataFrame:
    """tf mumları. Kaynak: 5m dosyası varsa 5m; yoksa ve tf >= 1h ise 1h. `eksikleri_at=None`: DK_ (seanslı TradFi)
    sembollerinde False (günlük/saatlik mumlar seans nedeniyle hep "eksik" görünür), diğerlerinde True."""
    if eksikleri_at is None:
        eksikleri_at = not sembol.startswith("DK_")
    if depo.mum_yolu(sembol, "5m", dizin).exists():
        return yeniden_ornekle(depo.mum_oku(sembol, "5m", baslangic, bitis, dizin=dizin), tf, "5m", eksikleri_at)
    if depo.mum_yolu(sembol, "1h", dizin).exists():
        if depo.aralik_suresi(tf) < pd.Timedelta(1, "h"):
            raise ValueError(f"{sembol}: yalnız 1h var; {tf} üretilemez")
        return yeniden_ornekle(depo.mum_oku(sembol, "1h", baslangic, bitis, dizin=dizin), tf, "1h", eksikleri_at)
    return depo.mum_oku(sembol, "5m", baslangic, bitis, dizin=dizin)     # FileNotFoundError (açık mesaj)


def veri_yukle(semboller, tf: str, baslangic=None, bitis=None, dizin: Optional[Path] = None):
    """-> (veriler, fundingler): {sembol: mum DataFrame}, {sembol: funding DataFrame} (dosyası olanlar).
    Mum DataFrame'lerinde `eksik` sütunu (varsa) düşürülür."""
    veriler, fundingler = {}, {}
    for s in semboller:
        df = mum_yukle(s, tf, baslangic, bitis, dizin)
        veriler[s] = df.drop(columns="eksik") if "eksik" in df.columns else df
        if depo.funding_yolu(s, dizin).exists():
            fundingler[s] = depo.funding_oku(s, baslangic, bitis, dizin=dizin)
    return veriler, fundingler
