"""Portföy stratejileri paketi (karar 23c). Adlar `pf__<kisa-ad>`; kayıt: `tum_portfoy_stratejileri()`.

Aileler (15 sınıf): rotasyon, gem, sabit_sepet, trend_sepet, kanarya, kesit_ls, goreceli_guc, wq_alfa, cta, pairs,
ref_filtreli_long, btc_hedge, rsi_cift, rsi_tarama, ibs_donus. csv bağlantıları: `baglama.BAGLAMA`.
"""
from __future__ import annotations

from motor.portfoy.stratejiler.cta import Cta
from motor.portfoy.stratejiler.ek2 import GumusMakro, PcaStatArb
from motor.portfoy.stratejiler.kesit import GoreceliGuc, KesitLS, WqAlfa
from motor.portfoy.stratejiler.pairs import Pairs
from motor.portfoy.stratejiler.rotasyon import Gem, Kanarya, Rotasyon, SabitSepet, TrendSepet
from motor.portfoy.stratejiler.son1ay import SonBirAyE014, SonBirAyTrendRider
from motor.portfoy.stratejiler.sinyal import BtcHedge, IbsDonus, ReferansFiltreliLong, RsiCift, RsiTarama

SINIFLAR = (Rotasyon, Gem, SabitSepet, TrendSepet, Kanarya, KesitLS, GoreceliGuc, WqAlfa, Cta, Pairs,
            ReferansFiltreliLong, BtcHedge, RsiCift, RsiTarama, IbsDonus)
# son 1 ay açık kaynak adayları (stratejiler/ek_kaynaklar/son1ay_2026-11.md); csv bağlantısı yok.
# ek2: pca_statarb + gumus_makro (csv satır 9, 22; bağlama: ek2.BAGLAMA_EK2)
EK_SINIFLAR = (SonBirAyTrendRider, SonBirAyE014, PcaStatArb, GumusMakro)


def tum_portfoy_stratejileri() -> dict:
    """{ad: sınıf} (ad = 'pf__...')."""
    s = {c.ad: c for c in SINIFLAR + EK_SINIFLAR}
    if len(s) != len(SINIFLAR) + len(EK_SINIFLAR):
        raise ValueError("yinelenen portföy strateji adı")
    return s


def sinif_al(ad: str):
    try:
        return tum_portfoy_stratejileri()[ad]
    except KeyError:
        raise KeyError(f"bilinmeyen portföy stratejisi: {ad}") from None
