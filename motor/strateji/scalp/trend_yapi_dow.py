"""scalp__trend-yapi-dow: 15m Dow yapısı kırılımı / çoklu TF mum uyumu. Çekirdek daytrade `TrendYapiDow` ile aynıdır, GÜN SONU yoktur.

Fark: mod="coklu_tf", tf_listesi=("30m","1h") (kart eseckal: M5/M15/M30/H1 -> min 15m kuralıyla 15m + 30m + 1h), ust_tf="1h", stop_n=8,
hedef_r=2.0. Kaynak kart: scalp__fiyat-eylemi-4-zaman-dilimi__eseckal (pip stop/hedef ATR'ye çevrildi). Kanonik yapı kırılımı
(daytrade kartları) mod="yapi" ile ızgarada. Bkz. daytrade/trend_yapi_dow.py (çelişkiler, kodlanmayanlar).
Negatif kanıt: arşiv §3 kısa TF kırılım/geri çekilme denemeleri (1S Donchian, 5 dk) başarısız; 15m'de maliyet baskın.
"""
from motor.strateji.daytrade.trend_yapi_dow import TrendYapiDow as _Gun


class TrendYapiDow(_Gun):
    ad = "scalp__trend-yapi-dow"
    stil = "scalp"
    _gun_sonu = False
    varsayilan_parametreler = {**_Gun.varsayilan_parametreler,
                               "mod": "coklu_tf", "tf_listesi": ("30m", "1h"), "ust_tf": "1h", "stop_n": 8}
    parametre_izgarasi = {
        "mod": ["yapi", "coklu_tf"],
        "pivot_k": [2, 3, 5],
        "hedef_r": [1.5, 2.0, 3.0],
    }
