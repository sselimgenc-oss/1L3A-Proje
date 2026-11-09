"""daytrade__aralik-ticareti: yatay aralıkta alt sınırdan al, üst sınırdan sat; gün sonunda kapanır (1h).

Çekirdek swing `AralikTicareti` ile aynıdır (türetildi): aralık = önceki `pencere` mumun Donchian
üst/alt sınırı, genişlik >= min_genislik_atr*ATR, ADX < adx_esik (yatay), sınıra yakın tepki mumu,
hedef karşı sınır, stop aralık dibi/tepesi ötesi (veya "yarim_aralik"). Day trade'e özgü: 1h varsayılanları
(pencere 24 mum = 1 gün) ve seansın son mumunda giriş yok + zorunlu `cikis` (UTC gün sonu).
Kaynak kartlar: daytrade__aralik-ticareti-yatay__derr (gün içi H/L aralığı, gün sonundan önce kapat),
  swing__aralik-hedef-stop__heikinashi (1h, 2 dokunuş, hedef karşı sınır, stop aralığın yarısı),
  swing__aralik-sinirlari-ters__day (H1, sınır kırılınca işlem terk).
Varsayımlar: Derr'in "gün içi en yüksek/düşük" aralığı yerine Donchian penceresi; "2 önemli dokunuş" kodlanmadı;
  Heikin Ashi'nin 90 pip'te stopu kısaltma kuralı (iz süren stop) kodlanmadı.
Çelişki: kanonik taslaktaki "RSI/Stokastik aşırı satım" kartlarda ortak çekirdek değil; kodlanmadı.
Negatif kanıt: aile kaydında sayısal kanıt yok; aralık kırılırsa zarar büyük (Day kartı: sınır kırılınca terk).
"""
from motor.strateji.gostergeler_b1 import GunSonu
from motor.strateji.swing.aralik_ticareti import AralikTicareti as _Swing


class AralikTicareti(GunSonu, _Swing):
    ad = "daytrade__aralik-ticareti"
    stil = "daytrade"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "pencere": 24, "min_genislik_atr": 3.0,
                               "seans_saat": 0.0}
    parametre_izgarasi = {
        "pencere": [24, 48, 96],
        "bant": [0.1, 0.2, 0.3],
        "adx_esik": [0.0, 20.0, 25.0],
    }
