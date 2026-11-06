"""scalp__heikin-ashi-donus: 15m Heikin Ashi renk dönüşü. Çekirdek swing `HeikinAshiDonus` ile aynıdır.

Fark: varsayılan trend_ma=100 (kart: "seviye/trend filtresi"), golgesiz=True ("gölgesiz güçlü mum"), onceki_n=2
(trend yavaşlaması: en az 2 ters renk mum), stop son 3 mumun ucu -/+ 0.25 ATR.
Kaynak kartlar: scalp__heikin-ashi-renk-donusu__lama (1m, stop = sinyal mumlarının ucu +/-3 puan, en çok 7 puan),
scalp__ha-renk-donusu__heikinashi (1m, stop 5-10 pip). Puan/pip -> ATR (stop_tampon_atr + stop_max_atr). Doji/topaç
dönüm mumu, açılıştan ilk 10-15 dk filtresi, haber filtresi kodlanmadı. 1m kaynaklı kartlar 15m'ye taşındığı için esinlenen uyarlamadır.
Negatif kanıt: arşiv §3 kısa TF dönüş denemeleri (5 dk) başarısız; 15m'de maliyet baskın.
"""
from motor.strateji.swing.heikin_ashi_donus import HeikinAshiDonus as _Swing


class HeikinAshiDonus(_Swing):
    ad = "scalp__heikin-ashi-donus"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "trend_ma": 100, "golgesiz": True}
    parametre_izgarasi = {
        "golgesiz": [True, False],
        "onceki_n": [1, 2, 3],
        "trend_ma": [0, 100, 200],
    }
