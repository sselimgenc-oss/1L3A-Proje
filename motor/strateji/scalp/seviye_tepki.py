"""scalp__seviye-tepki — yuvarlak sayı / önceki gün seviyesinde Heikin Ashi dönüşü (15m).

Kural (çekirdek `formasyon_b4.SeviyeTepkiTaban`):
  Destek seviyesi (seviye_tipi): 'onceki_seans' = önceki seansın en düşüğü; 'pivot' = son iki onaylı dip pivotu
  cift_tol_atr*ATR içinde ise (>=2 dokunuş) düşük olanı; 'yuvarlak' = fiyatın büyüklük basamağına göre yuvarlak
  (10^(basamak-1) * yuvarlak_carpan; örn. 60000 için 1000, 5 çarpanıyla 5000). Long: son tepki_pencere mumun dibi seviyeye
  tolerans_atr*ATR içinde (en fazla delik_atr*ATR altına delmiş), kapanış seviyenin üstünde ve tepki var: 'red' = yükseliş
  mumu + alt fitil >= fitil_oran*aralık; 'ha' = Heikin Ashi mumu kırmızıdan yeşile döner (seviye 3 mum içinde
  test edilmiş). Stop = min(dip, seviye) - tampon_atr*ATR (risk <= maks_risk_atr*ATR); hedef = hedef_r*R (sonraki seviye
  yerine sabit R). Short: ayna (direnç: önceki seans yükseği, tepe pivotları, yuvarlak sayı).
Stil (scalp): 15m; varsayılan seviye = yuvarlak sayı + HA renk dönüşü (kitap: ilk yeşil HA mumda al); hedef 1.5R.
Kaynak kartlar: scalp__50-100-seviye__lama, scalp__destek-direnc-ha-donus__heikinashi, scalp__onceki-gun-swing-ha__heikinashi, scalp__yuvarlak-sayi-dip-ha__heikinashi, scalp__petrol-yuvarlak-seviye-araligi__schroder (kodlanmadı).
Varsayımlar / ölçülebilir yaklaşık tanım: Seviye seçimi kartlarda 'sezgisel': burada yalnız üç ölçülebilir kaynak. 'Sonraki seviye' hedefi yerine sabit R (kart: 1:3 / birkaç R). Çift dip teyidi pivot tipinde (>=2 dokunuş) var. Pip stopları (5-12 puan, 30 pip) ATR tamponuna çevrildi. HA kartlarındaki kısmi kâr/HA renk değişimi çıkışı kodlanmadı (CikisAyarlari).
Çelişkiler: Hedef kartta 'sonraki seviye' ile '1:3' birlikte; R hedefi seçildi. 50/100 puan kuralı varlığa bağlı -> ölçeğe göre yuvarlak.
Negatif kanıt: Aile kayıtlarında negatif kanıt yok, pozitif kanıt da anekdot (HA 1:3 RRR, Hogan 80-200 pip). Seviyeler kırılabilir.
"""
from motor.strateji.formasyon_b4 import SeviyeTepkiTaban


class SeviyeTepki(SeviyeTepkiTaban):
    ad = "scalp__seviye-tepki"
    stil = "scalp"
    varsayilan_parametreler = {**SeviyeTepkiTaban.varsayilan_parametreler,
                               "seviye_tipi": 'yuvarlak',
                               "tepki_modu": 'ha',
                               "seans_saat": 0.0,
                               "hedef_r": 1.5,
                               "tolerans_atr": 0.2,
                               }
    parametre_izgarasi = {
        "seviye_tipi": ['pivot', 'onceki_seans', 'yuvarlak'],
        "tolerans_atr": [0.1, 0.3, 0.5],
        "tepki_modu": ['red', 'ha'],
    }
