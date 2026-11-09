"""scalp__cci-esik: 15m CCI eşik stratejisi. Çekirdek swing `CciEsik` ile aynıdır; yalnız varsayılanlar/ızgara farklı.

Varsayılan: mod="lambert" (CCI(14) ±100 kesişimi), EMA(100) trend filtresi (kart: "trend filtresi"), stop son 8 mumun
dibi/zirvesi -/+ 0.25 ATR (risk <= 3 ATR). Kaynak kartlar: scalp__cci-30-kirilim__busiere (1m/5m, CCI(9), ±30),
scalp__cci-100-kirilim__busiere (Lambert). Busiere'in pip/puan hedefleri yok; stoplar ATR'ye çevrildi (bkz. swing/cci_esik.py).
KODLANMADI: scalp__cci-zirve__busiere. 1m-5m kaynaklı kartlar 15m'ye taşındığı için "esinlenen" uyarlamadır.
Negatif kanıt: arşiv §3 kısa TF osilatör/dönüş denemeleri başarısız; scalp'te maliyet baskın.
"""
from motor.strateji.swing.cci_esik import CciEsik as _Swing


class CciEsik(_Swing):
    ad = "scalp__cci-esik"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler,
                               "cci_periyot": 14, "mod": "lambert", "trend_ma": 100, "stop_n": 8}
    parametre_izgarasi = {
        "cci_periyot": [9, 14, 20],
        "mod": ["lambert", "esik30"],
        "trend_ma": [0, 100, 200],
    }
