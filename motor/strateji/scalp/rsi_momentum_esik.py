"""scalp__rsi-momentum-esik: 15m RSI-50 geçişi + 1h RSI aynı yönde (çift zaman dilimi). Çekirdek swing `RsiMomentumEsik` ile aynıdır.

Fark: ust_tf="1h" (kart: 5dk + 1sa RSI; min TF 15m olduğu için 15m + 1h), stop_n=8. Üst TF RSI'ı htf.ust_zaman ile yalnız
kapanmış 1h mumlarından alınır (lookahead yok). Kaynak kartlar: daytrade__cift-rsi-5dk-1sa__singhal (5m kaynaklı), scalp__triple-rsi-heikin-ashi__carson (KODLANMADI).
Bkz. swing/rsi_momentum_esik.py. Negatif kanıt: arşiv §3 kısa TF momentum/dönüş denemeleri başarısız; 15m'de maliyet baskın.
"""
from motor.strateji.swing.rsi_momentum_esik import RsiMomentumEsik as _Swing


class RsiMomentumEsik(_Swing):
    ad = "scalp__rsi-momentum-esik"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "ust_tf": "1h", "stop_n": 8}
    parametre_izgarasi = {
        "rsi_periyot": [9, 14],
        "esik": [50.0, 60.0],
        "hedef_r": [0.0, 2.0],
        "stop_n": [8, 16],
    }
