"""swing__witch-hat — Landry 'Witch Hat': pivot tepeden sert düşüş, tepeye dönüş, dünkü düşüğün altında short (4h/1d).

Kural (çekirdek `formasyon_b4.WitchHatTaban`):
  Short (kitabın kuralı): düşüş trendi (kapanış < EMA(trend_ema) ve EMA düşüyor), onaylı pivot tepe P (1 mum sol/sağ),
  pivottan en az min_mesafe en çok maks_mesafe mum sonra fiyat P'ye yakın ('brim': önceki mumun yükseği >= P - yakin_atr*ATR),
  pivot ile bu mum arasında en az hareket_atr*ATR sert düşüş (tepenin 'şapka ucu' = o aralığın en düşüğü M), ve mum dünkü
  düşüğün altında kapanır. Stop = max(P, dünkü yüksek) + tampon_atr*ATR (kart: brim 0.10 üstü veya 4. mum yükseği, hangisi
  yüksekse); hedef = M ('şapka ucu', eski dipler; hedef-giriş >= min_rr*risk). Aynı pivottan tek işlem. Long: ayna (kitap:
  'alışlar tersidir'; mikro versiyon tercih ediliyor ama ölçü yok).
Stil (swing): 4h/1d (kart: 1d).
Kaynak kartlar: swing__witch-hats__landry
Varsayımlar / ölçülebilir yaklaşık tanım: 'Sert' ve 'yakın' kartta tanımsız -> hareket_atr ve yakin_atr parametreleri. Giriş 'dünkü düşüğün 0.10 altı' stop emri yerine kapanış-bazlı (kapanış < dünkü düşük). Kısmi kâr (yarısı 1R'de) CikisAyarlari.kismi ile; piyasa/sektör filtresi ve gap kâr alma kodlanmadı. Pivot tanımı 1 mum sol-sağ (kart).
Çelişkiler: Kart long için 'mikro' versiyonu tercih eder; burada simetrik tam ayna long da üretilir (long=False ile kapatılır).
Negatif kanıt: Ailede sayısal kanıt yok; tek kitap (Landry) ve görsel örnekler.
"""
from motor.strateji.formasyon_b4 import WitchHatTaban


class WitchHat(WitchHatTaban):
    ad = "swing__witch-hat"
    stil = "swing"
    varsayilan_parametreler = {**WitchHatTaban.varsayilan_parametreler,
                               "hareket_atr": 5.0,
                               "yakin_atr": 0.5,
                               "maks_mesafe": 40,
                               }
    parametre_izgarasi = {
        "hareket_atr": [3.0, 5.0, 8.0],
        "yakin_atr": [0.25, 0.5, 1.0],
        "maks_mesafe": [20, 40, 60],
    }
