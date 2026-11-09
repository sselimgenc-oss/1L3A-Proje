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


@dataclass(frozen=True)
class PortfoyEsikleri:
    """Portföy (hedef ağırlık) stratejileri için eleme ölçütü (karar 24, kullanıcı onaylı 2026-11-07).
    İşlem sayısı yerine OOS süresi ve yeniden dengeleme sayısı; başarı Sharpe ve düşüşle ölçülür.
    (2026-11-07 güncelleme: "en iyi %5 gün hariç net > 0" kapısı KALDIRILDI; metrik raporlanır, yoğunlaşma sağlamlıkta ölçülür.)"""
    min_oos_gun: int = 1095                # OOS süresi >= 3 yıl
    min_yeniden_dengeleme: int = 20        # OOS yeniden dengeleme sayısı >=
    min_net_getiri: float = 0.0            # OOS net getiri > bu
    min_sharpe: float = 0.5                # OOS günlük Sharpe >=
    max_dusus: float = 0.20                # OOS max düşüş <=


def portfoy_degerlendir(wf_sonuc: dict, esikler: Optional[PortfoyEsikleri] = None) -> dict:
    """-> {"gecti": bool, "nedenler": [başarısız ölçütler]}. wf_sonuc["metrikler"] anahtarları: oos_gun,
    yeniden_dengeleme, net_getiri, sharpe, max_dusus."""
    e = esikler or PortfoyEsikleri()
    m = wf_sonuc.get("metrikler") or {}
    if not m:
        return {"gecti": False, "nedenler": ["OOS sonucu yok"]}
    nedenler = []

    def kontrol(ad, deger, ok, metin):
        if _yok(deger):
            nedenler.append(f"{ad} hesaplanamadı")
        elif not ok(deger):
            nedenler.append(metin.format(deger))

    kontrol("oos_gun", m.get("oos_gun"), lambda v: v >= e.min_oos_gun, f"OOS süresi {{}} gün < {e.min_oos_gun}")
    kontrol("yeniden_dengeleme", m.get("yeniden_dengeleme"), lambda v: v >= e.min_yeniden_dengeleme,
            f"yeniden dengeleme {{}} < {e.min_yeniden_dengeleme}")
    kontrol("net_getiri", m.get("net_getiri"), lambda v: v > e.min_net_getiri,
            f"OOS net getiri {{:.4f}} <= {e.min_net_getiri}")
    kontrol("sharpe", m.get("sharpe"), lambda v: v >= e.min_sharpe, f"OOS Sharpe {{:.3f}} < {e.min_sharpe}")
    kontrol("max_dusus", m.get("max_dusus"), lambda v: v <= e.max_dusus, f"OOS max düşüş {{:.3f}} > {e.max_dusus}")
    return {"gecti": not nedenler, "nedenler": nedenler}
