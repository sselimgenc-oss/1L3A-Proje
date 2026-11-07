"""Portföy stratejileri paketi (karar 23c). Adlar `pf__<kisa-ad>`; kayıt: `tum_portfoy_stratejileri()`.

Aileler (15 sınıf): rotasyon, gem, sabit_sepet, trend_sepet, kanarya, kesit_ls, goreceli_guc, wq_alfa, cta, pairs,
ref_filtreli_long, btc_hedge, rsi_cift, rsi_tarama, ibs_donus. csv bağlantıları: `baglama.BAGLAMA`.
"""
from __future__ import annotations

from motor.portfoy.stratejiler.cta import Cta
from motor.portfoy.stratejiler.kesit import GoreceliGuc, KesitLS, WqAlfa
from motor.portfoy.stratejiler.pairs import Pairs
from motor.portfoy.stratejiler.rotasyon import Gem, Kanarya, Rotasyon, SabitSepet, TrendSepet
from motor.portfoy.stratejiler.sinyal import BtcHedge, IbsDonus, ReferansFiltreliLong, RsiCift, RsiTarama

SINIFLAR = (Rotasyon, Gem, SabitSepet, TrendSepet, Kanarya, KesitLS, GoreceliGuc, WqAlfa, Cta, Pairs,
            ReferansFiltreliLong, BtcHedge, RsiCift, RsiTarama, IbsDonus)


def tum_portfoy_stratejileri() -> dict:
    """{ad: sınıf} (ad = 'pf__...')."""
    s = {c.ad: c for c in SINIFLAR}
    if len(s) != len(SINIFLAR):
        raise ValueError("yinelenen portföy strateji adı")
    return s


def sinif_al(ad: str):
    try:
        return tum_portfoy_stratejileri()[ad]
    except KeyError:
        raise KeyError(f"bilinmeyen portföy stratejisi: {ad}") from None
