"""scalp__geri-cekilme-fiyat-eylemi — güçlü trendde 2-3 mumluk geri çekilme sonrası giriş (15m), 1h trend filtreli.

Kural (çekirdek `formasyon_b4.GeriCekilmeTaban`):
  Güçlü trend: kapanış > EMA(trend_ema), EMA yükseliyor (ema_egim_bak mumda), ADX >= adx_esik, (ust_tf doluysa üst TF
  kapanışı > üst EMA; ust_tf alt TF'nin tam katı değilse filtre atlanır). Zayıf geri çekilme: geri_min..geri_maks ardışık
  karşı mum (kapanış < açılış); zayif=True: iki ardışık karşı 'trend mumu' (gövde > %50 aralık) yok; geri çekilme derinliği
  (önceki tepeden dibe) <= maks_derinlik_atr*ATR. Giriş: yeşil mum, önceki (son karşı) mumun yükseğinin üstünde kapanır.
  Stop = geri çekilme dibi - tampon_atr*ATR; hedef = hedef_r*R (hedef_modu='r') veya önceki tepe ('tepe', >= min_rr).
  Short: ayna (düşüş trendi, karşı mumlar yeşil).
Stil (scalp): 15m; üst TF 1h EMA filtresi (kart: 1h); kısmi kâr + stopu girişe çekme CikisAyarlari ile.
Kaynak kartlar: scalp__trend-gunu-toparlanma__heikinashi, scalp__dusuk-hacimli-geri-cekilme__schroder (kodlanmadı), daytrade__iki-bacakli-geri-cekilme__singhal (iki bacaklı: kodlanmadı).
Varsayımlar / ölçülebilir yaklaşık tanım: 'Güçlü trend' = ADX + EMA şartı; 'zayıf geri çekilme' Woods ölçütleriyle (3+ ardışık karşı mum yok -> geri_maks, 2+ ardışık karşı trend mumu yok -> zayif). Kitaplardaki tik tabanlı stop emri girişi kapanış-bazlı onaya çevrildi. Silkelenme (önceki dip altına iğne) varyantı, Landry'nin persistent-pullback trend çizgisi şartı ve düşük hacimli geri çekilme (Schroder) KODLANMADI. İz süren/başabaş stop CikisAyarlari ile.
Çelişkiler: Woods kuralları vadeli 10-60 dk için; Landry 2-7 mum geri çekilme, Woods en çok 2 ardışık karşı mum + ikinci salınım; geri_min/geri_maks ızgara/varsayılanla 2-5 aralığı kapsanır. Hedef 'önceki tepe / 2R' -> iki mod.
Negatif kanıt: Ailede kanıt yok (HA kitabı yalnız piyasa hareketi örnekleri, başarı oranı yok).
"""
from motor.strateji.formasyon_b4 import GeriCekilmeTaban


class GeriCekilmeFiyatEylemi(GeriCekilmeTaban):
    ad = "scalp__geri-cekilme-fiyat-eylemi"
    stil = "scalp"
    varsayilan_parametreler = {**GeriCekilmeTaban.varsayilan_parametreler,
                               "geri_min": 2,
                               "geri_maks": 3,
                               "adx_esik": 25.0,
                               "ust_tf": '1h',
                               "hedef_r": 2.0,
                               }
    parametre_izgarasi = {
        "geri_min": [2, 3],
        "adx_esik": [20.0, 25.0, 30.0],
        "hedef_r": [1.5, 2.0, 3.0],
    }
