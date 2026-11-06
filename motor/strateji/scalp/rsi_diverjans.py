"""scalp__rsi-diverjans: 15m RSI/CCI diverjansı + teyit. Çekirdek swing `RsiDiverjans` ile aynıdır.

Fark: pivot_k=3 (15m'de ~45 dk onay gecikmesi), max_aralik=40 mum, teyit_n=4, teyit="mum", bb_sart=True (singhal: dip alt Bollinger'ın altında),
hedef_tipi="orta_bant" (kanonik: orta bant/MA veya 2R; singhal: karşı bant -> yaklaşık orta bant). Izgara osilator'ı (rsi/cci) içerir.
Kaynak kartlar: daytrade__rsi-diverjans-bollinger-1dk__singhal, scalp__cci-ayrisma__busiere, scalp__rsi-diverjans-filtreli__carson
(tescilli gösterge, yaklaşık). KODLANMADI: Carson'ın otomatik gösterge etiketleri birebir. 1m kaynaklı kartlar 15m'ye taşındı.
Negatif kanıt: arşiv §3 kısa TF dönüş/osilatör denemeleri başarısız; scalp'te maliyet baskın.
"""
from motor.strateji.swing.rsi_diverjans import RsiDiverjans as _Swing


class RsiDiverjans(_Swing):
    ad = "scalp__rsi-diverjans"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "max_aralik": 40, "teyit_n": 4, "teyit": "mum",
                               "bb_sart": True, "hedef_tipi": "orta_bant"}
    parametre_izgarasi = {
        "pivot_k": [2, 3, 5],
        "osilator": ["rsi", "cci"],
        "teyit": ["ema", "mum"],
        "hedef_tipi": ["r", "orta_bant"],
    }
