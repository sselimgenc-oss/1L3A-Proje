"""daytrade__bant-donus: Bollinger bandı dışından içeri dönüş, orta banda hedef; gün sonunda kapanır (1h).

Çekirdek swing `BantDonus` ile aynıdır (türetildi): önceki kapanış bant dışında, şimdiki kapanış içinde (teyit),
long/short, stop = dışarı çıkış ve tetik mumunun karşı ucu -/+ tampon*ATR, hedef orta bant (veya karşı bant),
ADX<esik yatay filtresi, isteğe bağlı RSI(5) ve EMA trend filtresi. Day trade'e özgü: 1h varsayılanları ve
seans sonu giriş yok + zorunlu `cikis` (UTC gün sonu).
Kaynak kartlar: daytrade__bollinger-ema9-bant__singhal (30dk, BB 20/2, trend yönünde banttan tepki mumu,
  hedef karşı bant), swing__bollinger-bant-ihlal-ters__day (H1, BB 20/3 ihlali ters işlem, karşı banda çıkış).
Çelişki: Singhal trend yönünde bant tepkisi (trend_ma ile) alır; Day aralıkta ters (adx<25). Kartların ortak
  çekirdeği "bant dışından dönüş"; filtreler farklı olduğundan ikisi ayrı kart ayarı olarak verilir.
Varsayımlar: Singhal'ın "9 EMA ile bant mesafesi" koşulu kitapta net değil, kodlanmadı; "bant yakınında destek"
  = bant dışı kapanış + geri dönüş; trend = kapanış > EMA(trend_ma).
Negatif kanıt: arşiv (arsiv/OZET.md §3) 4S/1G ve 1S ortalamaya dönüşü (Bollinger/RSI) başarısız bulmuştur.
"""
from motor.strateji.gostergeler_b1 import GunSonu
from motor.strateji.swing.bant_donus import BantDonus as _Swing


class BantDonus(GunSonu, _Swing):
    ad = "daytrade__bant-donus"
    stil = "daytrade"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "adx_esik": 25.0, "hedef_tipi": "orta",
                               "seans_saat": 0.0}
    parametre_izgarasi = {
        "bb_periyot": [20, 30],
        "bb_sapma": [2.0, 2.5, 3.0],
        "adx_esik": [0.0, 25.0],
        "hedef_tipi": ["orta", "karsi"],
    }
