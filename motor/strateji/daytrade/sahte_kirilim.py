"""daytrade__sahte-kirilim — Woods 'tıkanıklık giderme arızası' ruhunda aralık kırılımı başarısızlığı (1h), gün sonu çıkışlı.

Kural (çekirdek `formasyon_b4.SahteKirilimTaban`):
  Aralık = önceki `pencere` mumun Donchian üst/alt sınırı (kırılım mumu hariç); genişlik min/maks ATR katı arasında,
  (adx_esik>0 ise) ADX < adx_esik (yatay piyasa). Long: kırılım mumu j alt sınırın altına iner (fitil; kapanis_disi ile
  kapanış da dışarıda olmalı), en geç `geri_don_mum` mum sonra mum kapanışı sınırın ÜSTÜNE döner ve yükseliş mumudur
  (onay_mumu). Stop = sahte kırılımın en düşüğü (j..t) - tampon_atr*ATR; hedef = aralığın karşı ucu (hedef_modu='karsi')
  veya hedef_r*R; hedef-giriş < min_rr*risk ise işlem yok. min_dokunus>0: sınır en az o kadar ayrı dokunuşla doğrulanmış
  olmalı (bant = bant*genişlik). Aynı sahte kırılım tekrar sinyal vermez (geri_don_mum bekleme). Short: ayna (üst sınır).
Stil (daytrade): 1h; pencere 24 mum ~ 1 gün. UTC gün sonunda (daytrade/_ortak.gun_sonu_uygula) son mumda giriş yok ve açık pozisyon kapanır; seans_saat parametresi.
Kaynak kartlar: daytrade__tikanikligi-giderme-arizasi__woods (3+ mumluk tıkanıklık kırılımı hemen başarısız olur), daytrade__kaygi-bolgesi__woods (öznel, kodlanmadı).
Varsayımlar / ölçülebilir yaklaşık tanım: 'Kırılım' ve 'geri dönüş' kartlarda tanımsız; Donchian aralığı, ATR genişlik bandı ve 1-3 mumluk geri dönüş ile ölçüldü. Heikin Ashi renk teyidi, haber/katalizör yokluğu, doji teyidi ve ana trend tercihi KODLANMADI. Woods'un 'derhal başarısızlık' ölçütü yok -> geri_don_mum 1-3. Kâr hedefi Woods'ta yok (sonraki cilt): karşı uç / R hedefi bizim.
Çelişkiler: Woods tıkanıklık = 3+ mum iç içe; burada Donchian aralığı kullanıldı (daha genel).
Negatif kanıt: Aile kayıtlarında sayısal kanıt yok (HA kitabı 1:2-1:14 RRR örnekleri anekdot). Aralık gerçekten kırılırsa zarar stop kadardır; trend günlerinde sahte kırılım sinyalleri sık başarısız olur.
"""
from motor.strateji.formasyon_b4 import SahteKirilimTaban


class SahteKirilim(SahteKirilimTaban):
    ad = "daytrade__sahte-kirilim"
    stil = "daytrade"
    varsayilan_parametreler = {**SahteKirilimTaban.varsayilan_parametreler,
                               "pencere": 24,
                               "geri_don_mum": 3,
                               "seans_saat": 0.0,
                               "kapanis_disi": True,
                               }
    parametre_izgarasi = {
        "pencere": [16, 24, 48],
        "geri_don_mum": [1, 2, 3],
        "hedef_modu": ['karsi', 'r'],
    }
