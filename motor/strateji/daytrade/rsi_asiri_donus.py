"""daytrade__rsi-asiri-donus: 1h RSI/DeMarker aşırı bölge dönüşü + UTC gün sonu çıkışı. Çekirdek swing `RsiAsiriDonus` ile aynıdır.

Fark: trend_ma=100 (EMA), stop son 6 mumun ucu, UTC gün sonu zorunlu çıkış. gosterge="demarker" (alt=30 -> 0.3/0.7) ızgarada.
Kaynak kart: swing__demarker-asiri-bolge__day (H1 TSLA; DeMarker 0.3 altı uzun / 0.7 üstü kısa, "aralıkta kullan, trendde aşırı bölgede
uzun kalır" uyarısı -> trend_ma ve adx_max filtreleri). Kitap DeMarker periyodu vermez -> 14. Stop: kart "aralık sınırı"
(destek altı); burada son 6 mumun dibi (yaklaşık). Bkz. swing/rsi_asiri_donus.py.
Negatif kanıt: arşiv §3 ortalamaya dönüş (1S RSI/BB geri çekilme PF<1) başarısız; tek yazar kartı.
"""
from motor.strateji.swing.rsi_asiri_donus import RsiAsiriDonus as _Swing


class RsiAsiriDonus(_Swing):
    ad = "daytrade__rsi-asiri-donus"
    stil = "daytrade"
    _gun_sonu = True
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "trend_ma": 100, "stop_n": 6}
    parametre_izgarasi = {
        "gosterge": ["rsi", "demarker"],
        "rsi_periyot": [7, 14],
        "alt": [20.0, 30.0],
        "trend_ma": [0, 100],
    }
