"""scalp__rsi-asiri-donus: 15m RSI aşırı bölge dönüşü. Çekirdek swing `RsiAsiriDonus` ile aynıdır.

Fark: rsi_periyot=7, trend_ma=100 (EMA, "trend yönü" filtresi), stop son 8 mumun ucu. Kart farkları parametreyle:
rsi7-aralik__stevenson -> rsi_periyot=7, adx_max=25; rsi-hacim-osilator-dip__singhal -> vo_esik=30, cikis_rsi=70 değil 50 (yaklaşık);
rsi-aralik-ticareti-1dk__schroder -> eşik/periyot belirtilmemiş (varsayılan). Bkz. swing/rsi_asiri_donus.py (tam açıklama, çelişkiler).
Negatif kanıt: arşiv §3 "1S RSI/BB geri çekilme (PF<1)", "5 dk geri çekilme/dönüş" başarısız; scalp'te maliyet baskın.
"""
from motor.strateji.swing.rsi_asiri_donus import RsiAsiriDonus as _Swing


class RsiAsiriDonus(_Swing):
    ad = "scalp__rsi-asiri-donus"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "rsi_periyot": 7, "trend_ma": 100, "stop_n": 8}
    parametre_izgarasi = {
        "rsi_periyot": [2, 7, 14],
        "alt": [20.0, 30.0],
        "trend_ma": [0, 100, 200],
    }
