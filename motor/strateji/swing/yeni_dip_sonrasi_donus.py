"""swing__yeni-dip-sonrasi-donus — uzun vadeli yeni dipten sonra ilk tek mumluk düzeltmede dönüş (4h/1d).

Kural (çekirdek `formasyon_b4.YeniDipDonusTaban`):
  Yeni dip: son maks_sure mumdaki en düşük, son dip_pencere mumun en düşüğüne eşit/altında (N-mumluk yeni dip; kart: 6 ay /
  N=10-120). Sert yükseliş: dip ile düzeltme öncesi mum yüksek arası >= itki_atr*ATR. İlk itiş: dipten sonra en az itis_mum
  ardışık yüksek-tepe+yüksek-dip mumu (Bulkowski: >=2 gün). Düzeltme mumu j: daha düşük tepe ve daha düşük dip. Tetik:
  gecerlilik (2) mum içinde kapanış düzeltme mumunun yükseğinin üstüne çıkar; düzeltme dibinin altında kapanış kurulumu
  iptal eder. Stop = düzeltme dibi - tampon_atr*ATR; hedef = hedef_r*R (kart 2R). Short: ayna (yeni tepe sonrası ilk tek mumluk tepki).
Stil (swing): 4h/1d; dip_pencere 120 mum (1d ~ 6 ay). Crane 'Peg Leg' (20 gün tepe, 3 gün kuralı) ve 'Major Reversal' (10 günlük dip + 3 düşüş günü) aynı çekirdeğe oturmadığı için KODLANMADI.
Kaynak kartlar: swing__first-thrust__landry, daytrade__ilk-itis-modeli__bulkowski; swing__peg-leg__crane ve swing__major-reversal__crane kodlanmadı.
Varsayımlar / ölçülebilir yaklaşık tanım: 'Sert' yükseliş eşiği kartta yok -> itki_atr. Bulkowski: giriş kuralı geri çekilme mumunun yükseğinin 1 kuruş üstü; kapanış-bazlı onay ile yaklaşıldı. Piyasa/sektör filtresi, kısmi kâr (Landry Primer) kodlanmadı.
Çelişkiler: Bulkowski çıkış önerisi yok (yalnız test; kendi stop'u performansı bozmuş); Landry stop yok. Burada düzeltme dibi stop + R hedefi.
Negatif kanıt: Bulkowski: 5 günlük zaman çıkışı 'umut verici değil' (-%1,3..+%0,8). Ayrıca 6 ay penceresi kitapta en iyi sonuç için seçilmiş (veri avı).
"""
from motor.strateji.formasyon_b4 import YeniDipDonusTaban


class YeniDipSonrasiDonus(YeniDipDonusTaban):
    ad = "swing__yeni-dip-sonrasi-donus"
    stil = "swing"
    varsayilan_parametreler = {**YeniDipDonusTaban.varsayilan_parametreler,
                               "dip_pencere": 120,
                               "itki_atr": 3.0,
                               }
    parametre_izgarasi = {
        "dip_pencere": [60, 120, 180],
        "itki_atr": [2.0, 3.0, 4.0],
        "hedef_r": [1.5, 2.0, 3.0],
    }
