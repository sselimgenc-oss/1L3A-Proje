"""daytrade__stokastik-donus: trend yönünde Stokastik 20/80 aşırı bölge dönüşü; gün sonunda kapanır (1h).

Çekirdek `scalp__stokastik-donus` sınıfından türetildi (o da stil bağımsız mekaniktir): yavaş Stokastik %K/%D;
long = kapanış > EMA(trend_ema), son `bolge_n` mumda %K<=20 ve %K, %D'yi yukarı kesti (short ayna). Stop = son
`stop_n` mum dibi/zirvesi -/+ tampon*ATR (en çok stop_max_atr ATR); hedef hedef_r*R; çıkış: %K/%D ters kesişimi.
Day trade'e özgü: 1h varsayılanları ve UTC gün sonu zorunlu çıkışı.
Kaynak kart (tek): daytrade__williams-r-sma14__singhal (30dk; SMA14 üstünde Williams %R(14) -20 üstü aşırı alıma
  girip -50'ye geri dönüş + yeşil mum; stop swing dibi; hedef min 1:2). Williams %R = Stokastik %K ham - 100; ancak
  kartın "-50'ye geri dönüş" tetiği bu sınıfın "%K, %D'yi kesti" tetiğinden FARKLI -> kart sınıfla ifade edilemez,
  kart ayarı verilmedi. Aile kanonik kuralı (Stokastik 20/80 + trend) esas alındı.
Çelişki: kanonik taslak Stokastik der, tek day trade kartı Williams %R'dir (stiller arası kopya kanonik kural).
Negatif kanıt: arşiv (arsiv/OZET.md §3) "Stokastik dönüşü" ve `*__stokastik-donus` başarısız listesinde.
"""
from motor.strateji.gostergeler_b1 import GunSonu
from motor.strateji.scalp.stokastik_donus import StokastikDonus as _Scalp


class StokastikDonus(GunSonu, _Scalp):
    ad = "daytrade__stokastik-donus"
    stil = "daytrade"
    varsayilan_parametreler = {**_Scalp.varsayilan_parametreler, "trend_ema": 50, "stop_n": 8, "seans_saat": 0.0}
    parametre_izgarasi = {
        "trend_ema": [20, 50, 100],
        "k_periyot": [8, 14],
        "hedef_r": [1.0, 1.5, 2.0],
    }
