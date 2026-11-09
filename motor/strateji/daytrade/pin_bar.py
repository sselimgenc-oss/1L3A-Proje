"""daytrade__pin-bar — aralık/seviye dönüşünde pin bar (1h), UTC gün sonu zorunlu çıkış.

Çekirdek swing `PinBar` (swing/pin_bar.py; formasyon_b3.pin_cekirdek) ile aynıdır, ondan türer. Farklar: aralik_n=24
(1h'de 1 gün), teyit_n=2 (Singhal: pin bar SONRASI giriş), ust_tf="4h" (kart üst filtre 4h/1G; htf.py ile EMA20 trend
uyumu), seviye_modu "aralik" veya "gun" (önceki UTC günün düşüğü/tepesi, Vezi); gun_sonu_uygula ile seans son mumunda
giriş yok ve cikis=True. Kural/stop/hedef için bkz. swing/pin_bar.py.
Kaynak kartlar: pin-bar-aralik-donus__singhal (15m aralık dönüşü), fitil-reddi-seviye__vezi (scalp kartı: önceki gün
  tepe/dip fitil reddi).
Varsayımlar: Singhal "1. pin bar'da değil 2./3.'de işlem" sayım kuralı çelişkili ve kodlanmadı (teyit mumu kullanıldı);
  Vezi'nin "30 pip" sabit stop üst sınırı ATR'ye çevrildi (maks_risk_atr), Asya seansı filtresi kaynaksız -> yok.
  Hedef: aralık karşı ucu (hedef_r=0) Singhal'a daha yakındır, varsayılan 2R (kartın R hedefi).
Çelişkiler: Singhal 15m, aile 1h varsayılanı; "ilk pin bar'da işlem yapma" ile "pin bar sonrası gir" aynı kartta çelişir.
Negatif kanıt: istatistik yok; gün içi tek mumlu fitil desenleri maliyet sonrası zayıf (arsiv/OZET.md §3: 1S/5dk geri
  çekilme-dönüş denemeleri PF<1).
"""
import pandas as pd

from motor.strateji.daytrade._ortak import gun_sonu_uygula
from motor.strateji.swing.pin_bar import PinBar as _Swing


class PinBar(_Swing):
    ad = "daytrade__pin-bar"
    stil = "daytrade"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler,
                               "aralik_n": 24, "teyit_n": 2, "ust_tf": "4h", "seans_saat": 0.0}
    parametre_izgarasi = {
        "fitil_oran": [2.0, 2.5, 3.0],
        "aralik_n": [12, 24, 48],
        "hedef_r": [1.5, 2.0, 3.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        return gun_sonu_uygula(super().sinyaller(mumlar), self.parametreler["seans_saat"])
