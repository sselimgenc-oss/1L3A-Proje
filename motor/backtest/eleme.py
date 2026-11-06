"""Eleme ölçütü (karar 13): walk-forward OOS sonucunu eşiklerle değerlendirir."""
import math
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Esikler:
    min_net_getiri: float = 0.0            # OOS net getiri > bu (maliyet + funding dahil)
    min_pf: float = 1.2                    # OOS profit factor >=
    min_islem: int = 50                    # OOS işlem sayısı >=
    min_pf_en_iyi5_haric: float = 0.9      # "çökmez": en iyi %5 işlem çıkarılınca PF >= (lider varsayımı)


def _yok(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def degerlendir(wf_sonuc: dict, esikler: Optional[Esikler] = None) -> dict:
    """-> {"gecti": bool, "nedenler": [başarısız ölçütler]}"""
    e = esikler or Esikler()
    m = wf_sonuc.get("metrikler") or {}
    if not m:
        return {"gecti": False, "nedenler": ["OOS sonucu yok"]}
    nedenler = []

    def kontrol(ad, deger, ok, metin):
        if _yok(deger):
            nedenler.append(f"{ad} hesaplanamadı")
        elif not ok(deger):
            nedenler.append(metin.format(deger))

    kontrol("net_getiri", m.get("net_getiri"), lambda v: v > e.min_net_getiri,
            f"OOS net getiri {{:.4f}} <= {e.min_net_getiri}")
    kontrol("profit_factor", m.get("profit_factor"), lambda v: v >= e.min_pf,
            f"OOS PF {{:.3f}} < {e.min_pf}")
    kontrol("islem_sayisi", m.get("islem_sayisi"), lambda v: v >= e.min_islem,
            f"OOS işlem {{}} < {e.min_islem}")
    kontrol("en_iyi_yuzde5_haric_pf", m.get("en_iyi_yuzde5_haric_pf"), lambda v: v >= e.min_pf_en_iyi5_haric,
            f"en iyi %5 hariç PF {{:.3f}} < {e.min_pf_en_iyi5_haric}")
    return {"gecti": not nedenler, "nedenler": nedenler}
