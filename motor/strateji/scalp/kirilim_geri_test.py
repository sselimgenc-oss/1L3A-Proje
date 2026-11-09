"""scalp__kirilim-geri-test: kırılan direnç/destek seviyesine geri test girişi (15m).

Çekirdek `swing__kirilim-geri-test` sınıfından türetildi (aynı mekanik): Donchian seviyesi kırılımı (giriş yok),
`pencere` mum içinde seviyeye `temas_atr*ATR` geri dönüş + seviyenin doğru tarafında tepki mumu kapanışı -> trend
yönünde giriş; stop = geri test mumu ucu/seviyenin ötesi -/+ tampon*ATR; hedef hedef_r*R (kart: "önceki hareket
kadar / 2R"). Scalp'e özgü: uzunluk 20, pencere 8 (15m'de 2 saat), ızgara 12-30 / 4-16.
Kaynak kart (tek): scalp__kirilim-sonrasi-geri-test__schroder (seviye kırılır, geri çekilip tutunursa geri çekilmede
  gir; kırılımı kovalama; yatay fazda işlem yok; stop sayısal değil).
Varsayımlar: sayısal eşikler (kırılım tamponu, temas toleransı, pencere) tarafımızdan; "yatay fazda işlem yok"
  filtresi kodlanmadı.
Negatif kanıt: Bulkowski geri dönüş oranı %54-58; Schroder: gün içi kırılımların çoğu sahte; arşivde kısa TF
  geri çekilme/dönüş (5 dk) denemeleri başarısız (arsiv/OZET.md §3).
"""
from motor.strateji.swing.kirilim_geri_test import KirilimGeriTest as _Swing


class KirilimGeriTest(_Swing):
    ad = "scalp__kirilim-geri-test"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "uzunluk": 20, "pencere": 8}
    parametre_izgarasi = {
        "uzunluk": [12, 20, 30],
        "pencere": [4, 8, 16],
        "hedef_r": [1.5, 2.0, 3.0],
    }
