"""Funding verisini stratejiye NEDENSEL taşıyan yardımcılar.

Strateji.sinyaller(mumlar) yalnız mumları alır. `funding_gerekli = True` olan stratejiler için araştırma katmanı
(tarama, wf_tarama, portföy) mum DataFrame'ine `funding_orani` sütunu ekler:

  funding_orani[t] = mum t'nin KAPANIŞ anında (açılış + mum süresi) bilinen SON funding oranı
                     (funding zamanı <= mum kapanışı; ileri doldurma; o ana kadar funding yoksa NaN).

Funding zamanı mum kapanışından sonraysa o mumda görünmez. Funding dosyası yoksa (DK_ semboller) açık hata verilir;
funding sessizce 0 sayılmaz. `funding_gerekli = False` stratejilerin girdisi DEĞİŞMEZ (aynı nesne döner).
Backtest motorunun funding muhasebesi (backtest(funding=...)) ayrıdır ve bu sütundan etkilenmez.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

SUTUN = "funding_orani"


class FundingYokHatasi(ValueError):
    """Strateji funding gerektiriyor ama sembolün funding verisi yok."""


def mum_suresi(index: pd.DatetimeIndex, aralik: Optional[str] = None) -> pd.Timedelta:
    """Mum süresi: `aralik` verilmişse o (ör. '4h'), yoksa indeksteki en küçük pozitif fark."""
    if aralik is not None:
        from motor.veri.depo import aralik_suresi
        return pd.Timedelta(aralik_suresi(aralik))
    if len(index) < 2:
        raise ValueError("mum süresi kestirilemiyor (en az 2 mum ya da aralik gerekli)")
    return pd.Timedelta((index[1:] - index[:-1]).min())


def funding_sutunu_ekle(mumlar: pd.DataFrame, fund: pd.DataFrame, aralik: Optional[str] = None) -> pd.DataFrame:
    """mumlar'ın kopyasına `funding_orani` ekler (bkz. modül açıklaması). Girdiler değiştirilmez."""
    kapanis = (mumlar.index + mum_suresi(mumlar.index, aralik)).as_unit("ns")
    out = mumlar.copy()
    if fund is None or len(fund) == 0:
        out[SUTUN] = np.nan
        return out
    f = fund["oran"].astype("float64").sort_index()
    f.index = f.index.as_unit("ns")
    f = f[~f.index.duplicated(keep="last")]
    sol = pd.DataFrame({"t": kapanis})
    sag = pd.DataFrame({"t": f.index, SUTUN: f.to_numpy()})
    birlesik = pd.merge_asof(sol, sag, on="t", direction="backward", allow_exact_matches=True)
    out[SUTUN] = birlesik[SUTUN].to_numpy()
    return out


def stratejiye_hazirla(strateji, mumlar: pd.DataFrame, fund: Optional[pd.DataFrame], sembol: str = "?",
                       aralik: Optional[str] = None) -> pd.DataFrame:
    """Stratejinin girdisi. funding_gerekli False ise `mumlar` AYNEN (aynı nesne) döner."""
    if not getattr(strateji, "funding_gerekli", False):
        return mumlar
    if fund is None:
        raise FundingYokHatasi(f"{strateji.ad}/{sembol}: strateji funding verisi gerektirir ama {sembol} için "
                               f"funding dosyası yok (funding=0 kabul edilmez)")
    return funding_sutunu_ekle(mumlar, fund, aralik)
