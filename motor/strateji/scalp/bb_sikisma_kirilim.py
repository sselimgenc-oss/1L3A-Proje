"""scalp__bb-sikisma-kirilim: Bollinger bant genişliği sıkışması sonrası hacimli bant dışı kırılım (15m).

Çekirdek `swing__bb-sikisma-kirilim` sınıfından türetildi (aynı mekanik; gün sonu zorunluluğu yok):
sıkışma = bw son `sikisma_pencere` mumdaki alt `sikisma_yuzdelik` yüzdeliğinde; kapanış bandı İLK kez dışa kırınca
yönde giriş; hacim > hacim_k*ortalama; stop orta bant veya sıkışma kutusunun karşı ucu; hedef hedef_r*R
(kart örnekleri 1:3.8, 1:5.1 -> 3R varsayılan); orta bant geri kesişiminde `cikis`. Scalp'e özgü: 15m varsayılanları
(sikisma_pencere 96, hacim_k 1.5, hedef_r 3).
Kaynak kart (tek): scalp__kopus__uko (destek/direnç veya aralık kopuşu, mum kapanışı teyidi, Bollinger/ATR ile
  volatilite artışı, hacim artışı; eşik YOK). Bollinger sıkışması karttaki "volatilite artışı" ifadesinden türetilen
  bir yorumdur (kart sıkışmayı söylemez) -> kart ayarı yaklaşıktır.
Varsayımlar: tüm sayısal eşikler tarafımızdan (kanon: son 20-120 mumun alt %10-20'si); "geri çekilmede alternatif
  giriş" kodlanmadı (bkz. scalp__kirilim-geri-test).
Negatif kanıt: kırılım sistemlerinde sahte kırılım yüksek (aile kayıtlarında Scheier/Bulkowski); kısa TF'de maliyet baskın.
"""
from motor.strateji.swing.bb_sikisma_kirilim import BbSikismaKirilim as _Swing


class BbSikismaKirilim(_Swing):
    ad = "scalp__bb-sikisma-kirilim"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "sikisma_pencere": 96, "hacim_k": 1.5,
                               "hedef_r": 3.0}
    parametre_izgarasi = {
        "sikisma_pencere": [60, 120],
        "sikisma_yuzdelik": [10.0, 20.0],
        "stop_modu": ["orta", "kutu"],
        "hedef_r": [2.0, 3.0, 0.0],
    }
