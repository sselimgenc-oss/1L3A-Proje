"""scalp__aralik-ticareti: yatay aralıkta alt sınırdan al, üst sınırdan sat (15m).

Çekirdek swing `AralikTicareti` ile aynıdır (türetildi); scalp'e özgü yalnız varsayılanlar/ızgara:
pencere 40 mum (15m'de ~10 saat), min aralık genişliği 2.5 ATR, ADX < 25, hedef karşı sınır, stop aralık
dışı (stop_tampon_atr). Gün sonu zorunluluğu yok.
Kaynak kartlar: scalp__mini-aralik-5puan__lama (1m vadeli: kenara limit emir, hedef 5 puan, stop kenarın 5 puan dışı),
  scalp__aralik-sinirli__uko (destek/direnç sıçraması, hedef karşı sınır civarı).
PUAN -> ATR: Lama'nın sabit 5 puan hedefi karşı-sınır hedefiyle DEĞİŞTİRİLDİ (sınıf yalnız karşı sınır hedefi
  üretir); 5 puanlık stop tamponu ~stop_tampon_atr. Limit emir ile kenara pasif giriş değil, tepki mumu kapanışı.
Varsayımlar: aralık Donchian; Lama'nın "15 dk trend yok" bekleme kuralı ADX filtresiyle vekillenir;
  RSI/Stokastik onayı (Uko) kodlanmadı (kartta eşik yok).
Negatif kanıt: yok; kısa TF'de komisyon aralık genişliğine göre baskın olabilir (min_genislik_atr bunu sınırlar).
"""
from motor.strateji.swing.aralik_ticareti import AralikTicareti as _Swing


class AralikTicareti(_Swing):
    ad = "scalp__aralik-ticareti"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "pencere": 40, "min_genislik_atr": 2.5}
    parametre_izgarasi = {
        "pencere": [20, 40, 80],
        "bant": [0.1, 0.2, 0.3],
        "adx_esik": [0.0, 20.0, 25.0],
    }
