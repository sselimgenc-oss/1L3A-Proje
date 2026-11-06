"""swing__stokastik-donus: büyük trend yönünde Stokastik 20/80 aşırı bölge dönüşü (4h/1d).

Çekirdek `scalp__stokastik-donus` sınıfından türetildi (mekanik stil bağımsız): yavaş Stokastik (14,3,3);
long = kapanış > EMA(trend_ema), son `bolge_n` mumda %K<=20 ve %K, %D'yi yukarı kesti; short ayna. Stop = son
`stop_n` mum dibi/zirvesi -/+ tampon*ATR (en çok stop_max_atr ATR); hedef hedef_r*R; çıkış %K/%D ters kesişimi.
Swing'e özgü: trend_ema 100, stop_n 10, stop_max_atr 4, bolge_n 5.
Kaynak kartlar: swing__stokastik-asiri-satim-donus__boxer (1G; (14,3,3), yükselişte 20 altından dönüş, %K>%D;
  stop destek ihlali) -> kart ayarı verildi. swing__stokastik-kesisim-80-20__jordan (trend filtresiz, 80 üstünde
  alma; 20 altında satma) ve swing__stokastik-20-gecis__johnson (%K 20'yi yukarı kesince; %D kesişimi değil) ve
  swing__macd-stokastik-onay__johnson (MACD>0 + Stokastik) sınıfla İFADE EDİLEMEZ (trend filtresi zorunlu,
  MACD onayı yok) -> kodlanmadı.
Varsayımlar: "büyük trend" = EMA(trend_ema) konumu; Boxer'ın 50 üstü teyidi ve destek kırılımı teyidi yok;
  Boxer'ın alternatif (20,5,5)/(10,3,3) ayarları ızgara k_periyot ile yaklaşıktır.
Negatif kanıt: arşiv (arsiv/OZET.md §3) "Stokastik dönüşü" ve `*__stokastik-donus` başarısız listesinde.
"""
from motor.strateji.scalp.stokastik_donus import StokastikDonus as _Scalp


class StokastikDonus(_Scalp):
    ad = "swing__stokastik-donus"
    stil = "swing"
    varsayilan_parametreler = {**_Scalp.varsayilan_parametreler, "trend_ema": 100, "bolge_n": 5, "stop_n": 10,
                               "stop_max_atr": 4.0}
    parametre_izgarasi = {
        "trend_ema": [50, 100, 200],
        "k_periyot": [10, 14, 20],
        "hedef_r": [1.5, 2.0, 3.0],
    }
