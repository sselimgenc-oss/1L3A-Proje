"""swing__trend-cizgisi-kanal — regresyon kanalı alt/üst çizgi tepkisi veya trend çizgisi kırılımı (4h/1d).

Kural (çekirdek `formasyon_b4.TrendCizgisiKanalTaban`):
  Kayan lineer regresyon kanalı (`regresyon` mumluk kapanış regresyonu; çizgiler ± kanal_sd*artık SD). Kanal 'temiz'
  sayılır: R2 >= r2_esik (üç noktalı doğrulanmış çizgi vekili) ve genişlik >= min_kanal_atr*ATR. mod='tepki': eğim
  >= min_egim_atr (pencere boyunca ATR cinsinden; egim_sart=False: eğim şartı yok), dip alt çizgiye tolerans_atr*ATR
  içinde, yeşil mum, kapanış çizginin üstünde -> long; stop = min(dip, alt çizgi) - tampon_atr*ATR; hedef = üst çizgi
  (karşı çizgi; hedef-giriş >= min_rr*risk). mod='kirilim': eğim <= -min_egim_atr (düşen kanal), kapanış üst çizgiyi yukarı
  kırar (önceki kapanış içerideydi), yeşil mum -> long; stop = regresyon orta çizgisi - tampon; hedef hedef_r*R.
  Short: ayna (düşen kanal üst çizgisinde tepki; yükselen kanal alt çizgisi aşağı kırılımı).
Stil (swing): 4h/1d; regresyon 50 mum.
Kaynak kartlar: swing__trend-cizgisi-yeniden-test__boxer, swing__yukselis-trend-cizgisi-tepki__jordan, swing__kanal-kirilimi__make, swing__kanal-sicrama__razaq, swing__trend-kanali-kanallama__kratter, daytrade__trend-cizgisi-kirilim__bulkowski, daytrade__kanal-dokunus__bulkowski.
Varsayımlar / ölçülebilir yaklaşık tanım: Çizgi seçimi kartlarda öznel: swing noktalarından çizilen çizgi yerine regresyon kanalı (kart 'optimize: regresyon 20-100, genişlik 1.5-2 SD'). Çizginin yeniden çizilmesi/iz süren stop, kanal açısı (45 derece) ve 'üçüncü dokunuş' dokunuş sayımı olarak değil R2 eşiği ile temsil edildi.
Çelişkiler: Bulkowski kanal stop'u '%5 altı', kitaplar 'çizginin ötesi'; ATR tamponu kullanıldı. Trend çizgisi kırılımı kartı 'yukarı çıkış = long, aşağı kırılım = çıkış'; burada kırılım ayrı mod ve R hedefi.
Negatif kanıt: Aile kayıtlarında negatif kanıt yok; pozitif kanıt (Bulkowski ULBI örneği, Boxer günlük %20) anekdot/tek hisse.
"""
from motor.strateji.formasyon_b4 import TrendCizgisiKanalTaban


class TrendCizgisiKanal(TrendCizgisiKanalTaban):
    ad = "swing__trend-cizgisi-kanal"
    stil = "swing"
    varsayilan_parametreler = {**TrendCizgisiKanalTaban.varsayilan_parametreler,
                               "regresyon": 50,
                               "kanal_sd": 2.0,
                               }
    parametre_izgarasi = {
        "regresyon": [30, 50, 80],
        "kanal_sd": [1.5, 2.0],
        "mod": ['tepki', 'kirilim'],
    }
