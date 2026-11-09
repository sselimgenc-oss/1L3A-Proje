"""daytrade__renko-sr — Renko tuğla dönüşü + RSI/StochRSI aşırı bölge + destek/direnç (1h), UTC gün sonu zorunlu çıkış.

Kural (çekirdek: formasyon_b3.renko_cekirdek, long; short aynada): ATR kutulu Renko (kutu = renko_k*ATR(14); devam 1,
dönüş 2 tuğla, nedensel). Long: bu mumda Renko kırmızıdan yeşile DÖNÜŞ tuğlası oluştu; son `onay_n` mumda RSI(14) <=
rsi_alt ve Stokastik RSI %K(14,14,3) <= stoch_alt (aşırı satım) görüldü; destek: son onay_n mumun düşüğü, ondan önceki
`sr_n` mumun düşüğüne <= tol_atr*ATR yakın/altında ("uzun vadeli destek bölgesi"). Short: ayna (RSI >= 100-rsi_alt...).
Stop: son stop_n mumun dibi - tampon_atr*ATR ("swing dip altı"; risk > maks_risk_atr*ATR ise işlem yok).
Hedef: hedef_r * risk (kart: min 1:3). ust_tf doluysa üst TF EMA(ust_ema) uyumu (htf.py). gun_sonu_uygula uygulanır.
Kaynak kartlar: renko-atr14-rsi-stokastik__singhal (tek kart).
Varsayımlar: RSI/StochRSI eşikleri kartta yok -> 35 / 20 (ve aynası 65 / 80); üç onayın AYNI mumda olması çok seyrek
  olacağından `onay_n` mumluk pencere; Renko tuğla boyu ATR sabiti yerine oluşma anındaki ATR (nedensel);
  "mum grafiğinde aynı fiyat seviyesinde giriş" -> Renko dönüş mumunun kapanışı. Kart 15m; aile varsayılanı 1h.
Çelişkiler: yok (tek kart). Renko'nun mum zamanı olmadığından standart backtest ile birebir örtüşmez (yaklaşık).
Negatif kanıt: kazanma oranı/istatistik yok; çok koşullu giriş az işlem üretir (otomatik ≥50 işlem şartı zor olabilir).
  arsiv/OZET.md §3: RSI/BB ortalamaya dönüş (1S, 4S) maliyet sonrası PF<1.
"""
import pandas as pd

from motor.strateji.daytrade._ortak import gun_sonu_uygula
from motor.strateji.formasyon_b3 import FormasyonTaban, renko_cekirdek


class RenkoSr(FormasyonTaban):
    ad = "daytrade__renko-sr"
    stil = "daytrade"
    varsayilan_parametreler = {
        "renko_k": 1.0, "rsi_periyot": 14, "rsi_alt": 35.0, "stoch_alt": 20.0, "onay_n": 6, "sr_n": 48,
        "tol_atr": 0.5, "stop_n": 10, "tampon_atr": 0.25, "maks_risk_atr": 5.0, "hedef_r": 3.0,
        "ust_tf": "", "ust_ema": 20, "atr_periyot": 14, "seans_saat": 0.0, "long": True, "short": True,
    }
    parametre_izgarasi = {
        "renko_k": [0.75, 1.0, 1.5],
        "sr_n": [24, 48, 96],
        "hedef_r": [2.0, 3.0, 4.0],
    }

    def cekirdek(self, m: pd.DataFrame):
        return renko_cekirdek(m, self.parametreler)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        return gun_sonu_uygula(super().sinyaller(mumlar), self.parametreler["seans_saat"])

    def cikis_var_mi(self) -> bool:
        return self.parametreler["hedef_r"] > 0
