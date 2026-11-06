"""swing__supertrend-psar: Supertrend / Parabolik SAR yön değişiminde gir; çizgi aynı zamanda stop (4h/1d).

Çekirdek `scalp__supertrend-psar` sınıfından türetildi (mekanik stil bağımsız): gosterge "supertrend"|"psar"|"ikisi";
yön -1->+1 olunca long (ayna short); opsiyonel RSI filtresi (rsi_esik=60: long RSI>60, short RSI<40); stop =
çizgi; hedef_r (0: yok); çıkış: ters yön değişimi (`cikis`). Swing'e özgü: ATR 10, çarpan 3, 4h/1d.
Kaynak kartlar: swing__parabolik-sar-donus__make (D1; SAR taraf değiştirince giriş, ters değişimde çıkış) ->
  gosterge="psar"; daytrade__rsi-supertrend-pozisyonel__singhal (1d; Supertrend + RSI 60/40; çıkış Supertrend
  karşı tarafında kapanış) -> gosterge="supertrend", rsi_esik=60.
Fark: Singhal "Supertrend üstünde iken RSI 60'ı yukarı geçince" girer (RSI tetiği); sınıf "Supertrend dönüş
  mumunda RSI>60 ise" girer -> yaklaşık. Short yalnız türev segmentinde (kitap); kripto perpetual'da serbest.
Varsayımlar: Supertrend parametreleri Singhal'da belirtilmemiş (ATR 10, çarpan 3 varsayım); PSAR 0.02/0.2.
Negatif kanıt: aile kaydında yok; yatay piyasada çok sahte sinyal (Make uyarısı). Arşiv: tek kurallı trend sistemleri zayıf.
"""
from motor.strateji.scalp.supertrend_psar import SupertrendPsar as _Scalp


class SupertrendPsar(_Scalp):
    ad = "swing__supertrend-psar"
    stil = "swing"
    varsayilan_parametreler = {**_Scalp.varsayilan_parametreler}
    parametre_izgarasi = {
        "gosterge": ["supertrend", "psar", "ikisi"],
        "atr_periyot": [7, 10],
        "carpan": [2.0, 3.0],
        "rsi_esik": [0.0, 60.0],
    }
