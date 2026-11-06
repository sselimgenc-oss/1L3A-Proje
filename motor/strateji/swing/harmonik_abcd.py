"""swing__harmonik-abcd — ABCD harmonik deseni, D noktasında dönüş girişi.

Kural (çekirdek: formasyon_b3.abcd_cekirdek, boğa = long; ayı aynada short): nedensel zigzag pivotlarından ardışık
  A(tepe) B(dip) C(tepe, C<A). AB >= min_ab_atr*ATR; BC geri çekilmesi (C-B)/(A-B) in [bc_min, bc_maks]
  (varsayılan 0.382-0.886); D = C - ab_oran*(A-B) (ab_oran=1: AB=CD) ve D < B ("D, B'den daha düşük", Graham).
  C onaylandıktan sonra: düşük <= D + tol_atr*ATR ve boğa mumu D üstünde kapanır -> giriş (onaysız "D'de hemen al"
  yok; Graham: giriş hızlı yapılmamalı, dönüş onayı beklenir). Geçersiz: kapanış > A, kapanış < D - asim_atr*ATR,
  C'den maks_bekle mum geçti. Stop: min(düşük, D) - tampon_atr*ATR ("D noktasının ötesi").
  Hedef (kartta yok): D + hedef_oran*(A-D) — Carney/Pesavento tipik 0.382-0.618 AD düzeltmesi, varsayım.
Kaynak kartlar: abcd-deseni__graham (tek kart).
Varsayımlar: AB/CD eşitlik toleransı ve oranlar kartta yok -> yukarıdaki klasik harmonik oranlar; "trend yönü
  bilinmeli" filtresi koda eklenmedi; üç ABCD türü (klasik, AB=CD, uzantı) ab_oran parametresiyle (0.786/1/1.272).
Çelişkiler: kart giriş/stop/hedef vermiyor; hepsi bu dosyada varsayım.
Negatif kanıt: kanıt/istatistik yok. arsiv/OZET.md §3: Fibonacci / ölçülü hareket (OOS PF ≈ 0.85) başarısız —
  harmonik oranlar aynı aileden, düşük beklenti.
"""
import pandas as pd

from motor.strateji.formasyon_b3 import FormasyonTaban, abcd_cekirdek


class HarmonikAbcd(FormasyonTaban):
    ad = "swing__harmonik-abcd"
    stil = "swing"
    varsayilan_parametreler = {
        "pivot_yontemi": "zigzag", "pivot_k": 3, "zigzag_esik_k": 3.0, "atr_periyot": 14,
        "ab_oran": 1.0, "bc_min": 0.382, "bc_maks": 0.886, "min_ab_atr": 2.0, "tol_atr": 0.3,
        "asim_atr": 1.0, "maks_bekle": 60, "tampon_atr": 0.25, "hedef_oran": 0.618, "min_rr": 1.0,
        "long": True, "short": True,
    }
    parametre_izgarasi = {
        "ab_oran": [0.786, 1.0, 1.272],
        "hedef_oran": [0.382, 0.5, 0.618],
        "zigzag_esik_k": [2.0, 3.0, 4.0],
    }

    def cekirdek(self, m: pd.DataFrame):
        return abcd_cekirdek(m, self.parametreler)

    def cikis_var_mi(self) -> bool:
        return self.parametreler["hedef_oran"] > 0
