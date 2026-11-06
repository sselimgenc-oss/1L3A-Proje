"""daytrade__ichimoku: 1h Ichimoku Tenkan/Kijun kesişimi + bulut. Çekirdek swing `Ichimoku` ile aynıdır.

Fark: mod="tk_bulut" (kart: Tenkan Kijun üstünde ve fiyat bulutun üstünde kapanırsa al), stop_tipi="span_a" (kart: Senkou Span A;
risk > stop_max_atr ATR ise yaklaştırılır), hedef_r=3.0 (kart: 1:3 "kolayca"), UTC gün sonu zorunlu çıkış.
Kaynak kart: daytrade__ichimoku-tenkan-kijun-bulut__singhal. 1d üst TF filtresi (kitap önerisi) kodlanmadı.
Not: 1h'de 9/26/52 yaklaşık 1 gün; gün sonu kuralı nedeniyle bulut/Kijun sinyalleri çoğunlukla gün içinde kapanır.
Negatif kanıt: aile kaydında yok; gün içi trend takibinde ORB benzeri denemeler maliyet sonrası zayıf (DURUM.md denetim notu); tek yazar.
"""
from motor.strateji.swing.ichimoku import Ichimoku as _Swing


class Ichimoku(_Swing):
    ad = "daytrade__ichimoku"
    stil = "daytrade"
    _gun_sonu = True
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler,
                               "mod": "tk_bulut", "stop_tipi": "span_a", "hedef_r": 3.0}
    parametre_izgarasi = {
        "tk_kesisim": [True, False],
        "stop_tipi": ["span_a", "kijun", "bulut"],
        "hedef_r": [1.5, 3.0],
        "kijun": [26, 52],
    }
