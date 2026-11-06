"""daytrade__elliott-dalga — Elliott 2. ve 4. dalga düzeltme sonu girişi (1h), UTC gün sonu zorunlu çıkış.

Kural (çekirdek: formasyon_b3.elliott_cekirdek, long biçimi; short aynada): nedensel zigzag pivotları (ATR eşikli,
zigzag_esik_k). P0(dip) P1(tepe) P2(dip) [P3(tepe) P4(dip)] dizisi.
  Dalga 2 sonu: P2 > P0 (dalga 2 başlangıcı aşmaz), geri çekilme (P1-P2)/(P1-P0) in [r2_min, r2_maks], dalga 1
  >= min_dalga_atr*ATR -> P2 pivotunun ONAY mumunda giriş (zigzag onayı "düzeltme bitti" teyididir).
  Dalga 4 sonu (dalga=0 veya 4): ek olarak P3 > P1, dalga3 >= w3_oran*dalga1 ("dalga 3 en güçlü/uzun"), P4 > P1
  (dalga 4 dibi dalga 1 tepesinin altına inmez), geri çekilme (P3-P4)/(P3-P2) in [r4_min, r4_maks].
  Stop: swing dibi (P2/P4) - tampon_atr*ATR. Hedef: giriş + hedef_r * risk (kart: ideal 1:2). `dalga`: 0 = ikisi, 2, 4.
  Short: aynada (alçalan itki); kart short'u A-B-C düzeltmesi (B/C tepesinde satış) olarak anlatır — aynı
  "karşı-hamle tepesinde trend yönünde giriş" mantığı, ABC ayrımı yapılmaz.
Kaynak kartlar: elliott-dalga-2-4__singhal (giriş), bes-dalga-cikis__boxer (yalnız 5. dalga ÇIKIŞI).
Varsayımlar: dalga sayımı öznel -> zigzag pivotu + yukarıdaki sayısal kurallar; "yeşil mumun tepesinin üstü" tetiği
  zigzag onayı ile değiştirildi (onay = fiyatın dipten esik*ATR yükselmesi). Kural 3 (dalga 5 kısa/uzun) giriş için
  gereksiz, kodlanmadı. Boxer'ın "5. dalga tamamlanınca kapat" çıkışı giriş kuralı olmadığı için eklenmedi (1m kartı).
Çelişkiler: kart "dalga 3 en kısa değil" ile "en uzun" ifadelerini karıştırıyor; w3_oran=1.0 (dalga 3 >= dalga 1).
Negatif kanıt: Boxer kartında kazanma oranı yok; sayım öznel olduğu için ölçülebilir kenar kanıtı yok. arsiv/OZET.md §3:
  Fibonacci/ölçülü hareket denemeleri OOS PF ≈ 0.85 (benzer geri çekilme/ölçü mantığı) — umut düşük.
"""
import pandas as pd

from motor.strateji.daytrade._ortak import gun_sonu_uygula
from motor.strateji.formasyon_b3 import FormasyonTaban, elliott_cekirdek


class ElliottDalga(FormasyonTaban):
    ad = "daytrade__elliott-dalga"
    stil = "daytrade"
    varsayilan_parametreler = {
        "zigzag_esik_k": 2.5, "atr_periyot": 14, "dalga": 0, "r2_min": 0.382, "r2_maks": 0.786,
        "r4_min": 0.236, "r4_maks": 0.618, "w3_oran": 1.0, "min_dalga_atr": 2.0, "tampon_atr": 0.25,
        "hedef_r": 2.0, "seans_saat": 0.0, "long": True, "short": True,
    }
    parametre_izgarasi = {
        "zigzag_esik_k": [2.0, 3.0, 4.0],
        "hedef_r": [1.5, 2.0, 3.0],
        "r2_maks": [0.618, 0.786, 1.0],
    }

    def cekirdek(self, m: pd.DataFrame):
        return elliott_cekirdek(m, self.parametreler)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        return gun_sonu_uygula(super().sinyaller(mumlar), self.parametreler["seans_saat"])

    def cikis_var_mi(self) -> bool:
        return self.parametreler["hedef_r"] > 0
