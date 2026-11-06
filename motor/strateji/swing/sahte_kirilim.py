"""swing__sahte-kirilim — aralık sınırının sahte kırılımı, ters yönde giriş (4h/1d).

Kural (çekirdek `formasyon_b4.SahteKirilimTaban`):
  Aralık = önceki `pencere` mumun Donchian üst/alt sınırı (kırılım mumu hariç); genişlik min/maks ATR katı arasında,
  (adx_esik>0 ise) ADX < adx_esik (yatay piyasa). Long: kırılım mumu j alt sınırın altına iner (fitil; kapanis_disi ile
  kapanış da dışarıda olmalı), en geç `geri_don_mum` mum sonra mum kapanışı sınırın ÜSTÜNE döner ve yükseliş mumudur
  (onay_mumu). Stop = sahte kırılımın en düşüğü (j..t) - tampon_atr*ATR; hedef = aralığın karşı ucu (hedef_modu='karsi')
  veya hedef_r*R; hedef-giriş < min_rr*risk ise işlem yok. min_dokunus>0: sınır en az o kadar ayrı dokunuşla doğrulanmış
  olmalı (bant = bant*genişlik). Aynı sahte kırılım tekrar sinyal vermez (geri_don_mum bekleme). Short: ayna (üst sınır).
Stil (swing): 4h/1d; kart: 3-5 mumluk (4h) geri dönüş, en az iki dokunuşlu sınır (min_dokunus=2), kapanış dışarıda.
Kaynak kartlar: swing__sahte-kopus-ters-yon__heikinashi, swing__trend-kanali-sahte-kirilim__heikinashi (kanal sahte kırılımı ayrı kodlanmadı), daytrade__bozulmus-alcalan-ucgen__bulkowski / bozulmus-simetrik-ucgen (üçgen sahte kırılımı kodlanmadı).
Varsayımlar / ölçülebilir yaklaşık tanım: 'Kırılım' ve 'geri dönüş' kartlarda tanımsız; Donchian aralığı, ATR genişlik bandı ve 1-3 mumluk geri dönüş ile ölçüldü. Heikin Ashi renk teyidi, haber/katalizör yokluğu, doji teyidi ve ana trend tercihi KODLANMADI.
Çelişkiler: Hedef: kartta 'kısa vadede karşı sınır' vs 'uzun vadede karşı uç' (HA) ve 'min 1:2' çelişir; karşı sınır + min_rr ile uzlaştırıldı. Stop tamponu 'biraz' (sayı yok) -> 0.25 ATR.
Negatif kanıt: Aile kayıtlarında sayısal kanıt yok (HA kitabı 1:2-1:14 RRR örnekleri anekdot). Aralık gerçekten kırılırsa zarar stop kadardır; trend günlerinde sahte kırılım sinyalleri sık başarısız olur.
"""
from motor.strateji.formasyon_b4 import SahteKirilimTaban


class SahteKirilim(SahteKirilimTaban):
    ad = "swing__sahte-kirilim"
    stil = "swing"
    varsayilan_parametreler = {**SahteKirilimTaban.varsayilan_parametreler,
                               "pencere": 40,
                               "geri_don_mum": 3,
                               "min_dokunus": 2,
                               "kapanis_disi": True,
                               }
    parametre_izgarasi = {
        "pencere": [20, 40, 80],
        "geri_don_mum": [1, 2, 3],
        "min_dokunus": [0, 2],
    }
