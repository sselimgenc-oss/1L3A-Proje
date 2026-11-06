"""scalp__ardisik-bar-tukenme: 3-5 ardışık aynı yönlü mum sonrası ters yönde giriş (15m).

Çekirdek swing `ArdisikBarTukenme` ile aynıdır (türetildi); scalp'e özgü: 15m varsayılanları (seri_n 3, tetik "kirilim", hedef 2R) ve ızgara.
Kural: son seri_n mum ardışık düşüş mumu (kapanış<açılış) ve sonraki mum serinin son mumunun zirvesi üstünde kapanır -> long (ayna short);
stop seri dibi -/+ tampon*ATR; hedef hedef_r*R. Gün sonu zorunluluğu yok.
Kaynak kart (tek): scalp__iki-mum-kurulumu__grail (Forex, 15dk-1S; iki mum yukarı trendli, 2. mum 1.'den büyük, 2. mumun yüksek-kapanış
  mesafesi 1.'den belirgin büyük -> 3. mumun açılışında SAT; sabit pip hedefi (15dk 1 pip), yazar stop kullanmaz). Bu tek kart sınıfla İFADE
  EDİLEMEZ: iki mumlu boyut/kapanış-mesafesi koşulu ve sabit pip hedefi yok -> kart ayarı verilmedi. Aile çekirdeği (3-5 ardışık mum) swing kartlarından.
Varsayımlar: kartın hedefi (sabit pip) ATR/R hedefiyle değiştirildi; seri 3-5 mum (kanon).
Negatif kanıt: yok; kısa TF'de ardışık mum tükenmesi (karşı-trend) komisyon baskınken zayıf prior ile test edilir (arsiv/OZET.md §3: kısa TF başarısız).
"""
from motor.strateji.swing.ardisik_bar_tukenme import ArdisikBarTukenme as _Swing


class ArdisikBarTukenme(_Swing):
    ad = "scalp__ardisik-bar-tukenme"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "seri_n": 3, "tetik": "kirilim", "hedef_r": 2.0}
    parametre_izgarasi = {
        "seri_n": [3, 4, 5],
        "tetik": ["seri_sonu", "kirilim"],
        "hedef_r": [1.5, 2.0, 3.0],
    }
