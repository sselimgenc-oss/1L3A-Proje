"""daytrade__seviye-tepki — önceki gün yüksek/düşük ve diğer seviyelerde tepki (1h), gün sonu çıkışlı.

Kural (çekirdek `formasyon_b4.SeviyeTepkiTaban`):
  Destek seviyesi (seviye_tipi): 'onceki_seans' = önceki seansın en düşüğü; 'pivot' = son iki onaylı dip pivotu
  cift_tol_atr*ATR içinde ise (>=2 dokunuş) düşük olanı; 'yuvarlak' = fiyatın büyüklük basamağına göre yuvarlak
  (10^(basamak-1) * yuvarlak_carpan; örn. 60000 için 1000, 5 çarpanıyla 5000). Long: son tepki_pencere mumun dibi seviyeye
  tolerans_atr*ATR içinde (en fazla delik_atr*ATR altına delmiş), kapanış seviyenin üstünde ve tepki var: 'red' = yükseliş
  mumu + alt fitil >= fitil_oran*aralık; 'ha' = Heikin Ashi mumu kırmızıdan yeşile döner (seviye 3 mum içinde
  test edilmiş). Stop = min(dip, seviye) - tampon_atr*ATR (risk <= maks_risk_atr*ATR); hedef = hedef_r*R (sonraki seviye
  yerine sabit R). Short: ayna (direnç: önceki seans yükseği, tepe pivotları, yuvarlak sayı).
Stil (daytrade): 1h; varsayılan seviye = önceki UTC günün dibi/tepesi. UTC gün sonunda (daytrade/_ortak.gun_sonu_uygula) son mumda giriş yok ve açık pozisyon kapanır; seans_saat parametresi.
Kaynak kartlar: scalp__ak47-seviye-testi__vezi (15m, önceki gün dibi/tepe testi ve sıçrama; '3 vektörlü hareket' kodlanmadı), + aile kartları.
Varsayımlar / ölçülebilir yaklaşık tanım: Seviye seçimi kartlarda 'sezgisel': burada yalnız üç ölçülebilir kaynak. 'Sonraki seviye' hedefi yerine sabit R (kart: 1:3 / birkaç R). Çift dip teyidi pivot tipinde (>=2 dokunuş) var. Pip stopları (5-12 puan, 30 pip) ATR tamponuna çevrildi. HA kartlarındaki kısmi kâr/HA renk değişimi çıkışı kodlanmadı (CikisAyarlari).
Çelişkiler: Hedef kartta 'sonraki seviye' ile '1:3' birlikte; R hedefi seçildi. 50/100 puan kuralı varlığa bağlı -> ölçeğe göre yuvarlak.
Negatif kanıt: Aile kayıtlarında negatif kanıt yok, pozitif kanıt da anekdot (HA 1:3 RRR, Hogan 80-200 pip). Seviyeler kırılabilir.
"""
from motor.strateji.formasyon_b4 import SeviyeTepkiTaban


class SeviyeTepki(SeviyeTepkiTaban):
    ad = "daytrade__seviye-tepki"
    stil = "daytrade"
    varsayilan_parametreler = {**SeviyeTepkiTaban.varsayilan_parametreler,
                               "seviye_tipi": 'onceki_seans',
                               "seans_saat": 0.0,
                               "pivot_k": 3,
                               "tolerans_atr": 0.3,
                               }
    parametre_izgarasi = {
        "seviye_tipi": ['pivot', 'onceki_seans', 'yuvarlak'],
        "tolerans_atr": [0.1, 0.3, 0.5],
        "tepki_modu": ['red', 'ha'],
    }
