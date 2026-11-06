"""scalp__sahte-kirilim — aralık sınırında sahte kopuş (15m), ADX<25 yatay piyasa filtresi.

Kural (çekirdek `formasyon_b4.SahteKirilimTaban`):
  Aralık = önceki `pencere` mumun Donchian üst/alt sınırı (kırılım mumu hariç); genişlik min/maks ATR katı arasında,
  (adx_esik>0 ise) ADX < adx_esik (yatay piyasa). Long: kırılım mumu j alt sınırın altına iner (fitil; kapanis_disi ile
  kapanış da dışarıda olmalı), en geç `geri_don_mum` mum sonra mum kapanışı sınırın ÜSTÜNE döner ve yükseliş mumudur
  (onay_mumu). Stop = sahte kırılımın en düşüğü (j..t) - tampon_atr*ATR; hedef = aralığın karşı ucu (hedef_modu='karsi')
  veya hedef_r*R; hedef-giriş < min_rr*risk ise işlem yok. min_dokunus>0: sınır en az o kadar ayrı dokunuşla doğrulanmış
  olmalı (bant = bant*genişlik). Aynı sahte kırılım tekrar sinyal vermez (geri_don_mum bekleme). Short: ayna (üst sınır).
Stil (scalp): 15m; Stevenson kartı ADX<25 şartı adx_esik=25 ile; VWAP bandı/Stokastik/'Sahte Kopuş (Expo)' göstergesi kodlanmadı (algoritma kitapta yok), yerine Donchian sahte kırılımı kullanıldı.
Kaynak kartlar: scalp__sahte-kopus-vwap__stevenson (kısmen: yalnız ADX<25 + sahte kırılım mantığı).
Varsayımlar / ölçülebilir yaklaşık tanım: 'Kırılım' ve 'geri dönüş' kartlarda tanımsız; Donchian aralığı, ATR genişlik bandı ve 1-3 mumluk geri dönüş ile ölçüldü. Heikin Ashi renk teyidi, haber/katalizör yokluğu, doji teyidi ve ana trend tercihi KODLANMADI.
Çelişkiler: Stevenson çıkışı VWAP+1SD / ters sinyal; burada karşı uç hedefi + stop.
Negatif kanıt: Aile kayıtlarında sayısal kanıt yok (HA kitabı 1:2-1:14 RRR örnekleri anekdot). Aralık gerçekten kırılırsa zarar stop kadardır; trend günlerinde sahte kırılım sinyalleri sık başarısız olur.
"""
from motor.strateji.formasyon_b4 import SahteKirilimTaban


class SahteKirilim(SahteKirilimTaban):
    ad = "scalp__sahte-kirilim"
    stil = "scalp"
    varsayilan_parametreler = {**SahteKirilimTaban.varsayilan_parametreler,
                               "pencere": 32,
                               "geri_don_mum": 2,
                               "adx_esik": 25.0,
                               "tampon_atr": 0.2,
                               }
    parametre_izgarasi = {
        "pencere": [24, 32, 64],
        "geri_don_mum": [1, 2, 3],
        "adx_esik": [0.0, 25.0],
    }
