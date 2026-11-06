"""swing__elmas-formasyon — elmas (diamond) tepe/dip formasyonu kırılımı.

Kural (çekirdek: formasyon_b3.elmas_cekirdek, yukarı kırılım long; aşağı kırılım aynada short): t'den önceki
`pencere` mum 4 çeyreğe bölünür (Q = pencere//4); çeyrek aralığı q = max(yüksek) - min(düşük).
  Sol yarı GENİŞLEYEN: q2 >= genis_oran*q1. Sağ yarı DARALAN: q3 >= genis_oran*q4 ve q4 <= daralma_oran*max(q2,q3).
  Formasyon yüksekliği H = tüm pencere aralığı >= min_yuk_atr*ATR. Tetik: kapanış son çeyreğin tepesinin (aşağıda dibinin)
  tampon_atr*ATR ötesine çıkar. Stop: son çeyreğin karşı ucu (stop_modu="son") veya tüm formasyonun karşı ucu ("uc"),
  - tampon. Hedef: kırılım kapanışı +/- hedef_olcu * H (Bulkowski: elmas dip %63, elmas tepe %69 ölçü kuralı;
  varsayılan 0.65). Sinyaller Q mum aralıklı.
Kaynak kartlar: elmas-ust-asagi-kirilim__bulkowski, elmas-alt-yukari-kirilim__bulkowski.
Varsayımlar: elmas "görme" -> çeyrek aralığı genişleme/daralma yaklaşığı (genişleyen+daralan üçgen); çizgi
  sınırları yerine son çeyreğin yüksek/düşük aralığı kullanıldı; önceki trend ve "sektör/pazar trendi" filtresi yok.
  Bulkowski kırılımda "ertesi gün açılış" der -> motor zaten sonraki mum açılışında girer.
Çelişkiler: kartlar elmas üstü (aşağı) ve altı (yukarı) için farklı ölçü yüzdeleri verir (69/63); tek parametre.
Negatif kanıt: çok nadir formasyon (Bulkowski'de az örnek); istatistik günlük hisse; kırılım sonrası "yetersiz vuruş"
  (hedefe ulaşmama) ve geri dönüş yorumu kartta belirsiz. Kripto doğrulaması yok.
"""
import pandas as pd

from motor.strateji.formasyon_b3 import FormasyonTaban, elmas_cekirdek


class ElmasFormasyon(FormasyonTaban):
    ad = "swing__elmas-formasyon"
    stil = "swing"
    varsayilan_parametreler = {
        "pencere": 40, "genis_oran": 1.4, "daralma_oran": 0.6, "min_yuk_atr": 3.0, "tampon_atr": 0.1,
        "stop_modu": "son", "hedef_olcu": 0.65, "min_rr": 1.0, "atr_periyot": 14, "long": True, "short": True,
    }
    parametre_izgarasi = {
        "pencere": [24, 40, 60],
        "hedef_olcu": [0.5, 0.65, 0.8],
        "daralma_oran": [0.4, 0.6, 0.8],
    }

    def cekirdek(self, m: pd.DataFrame):
        return elmas_cekirdek(m, self.parametreler)

    def cikis_var_mi(self) -> bool:
        return self.parametreler["hedef_olcu"] > 0
