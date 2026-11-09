"""scalp__bant-donus: Bollinger(40,2) dışından dönüş + RSI(5) + ADX<25, karşı banda hedef (15m).

Çekirdek swing `BantDonus` ile aynıdır (türetildi); scalp'e özgü: BB 40/2, RSI(5)<30 / >70 (dışarı çıkış
mumunda), ADX(14)<25, hedef_tipi="karsi" (Stevenson/Carson: karşı banda ulaşınca çıkış), 15m.
Kural: önceki kapanış bant dışında + RSI(5) aşırı; şimdiki kapanış bant içinde; long/short; stop = çıkış ve tetik
mumunun karşı ucu -/+ tampon*ATR (kartlar: son salınım dibi/zirvesi); hedef karşı (veya orta) bant.
Kaynak kartlar: scalp__bollinger40-rsi5-adx__stevenson ve scalp__bollinger40-rsi5-adx-kopya__carson (aynı kural,
  kopya), scalp__geri-cekilme-bollinger__connell + scalp__bollinger-meta-scalper__ellis (1m/5m forex; band dışı ->
  orta çizgi yönüne; stop bant genişliğinin yarısı, hedef bant genişliğinin %5'i -> hedef_tipi='orta' ile yaklaşık),
  scalp__rsi5-keltner-ema200__stevenson (Keltner 1.5 ATR + EMA200: KODLANMADI, Keltner kanalı yok),
  daytrade__keltner-dis-stokastik-asiri-satim__backus (hipotez, Keltner: KODLANMADI).
PİP -> ATR: Connell/Ellis sabit pip hedefleri bant genişliği yüzdesine dayanır; burada orta bant hedefi kullanıldı.
Varsayımlar: "RSI aşırı bölgeden çıkınca giriş" -> dışarı çıkış mumundaki RSI(5) aşırı + şimdiki kapanış içeride;
  trend_ma kapalı (EMA200 filtresi yalnız Keltner kartında).
Negatif kanıt: arşiv (arsiv/OZET.md §3): kısa TF + ortalamaya dönüş (1S RSI/BB geri çekilme PF<1) ve `scalp__bant-donus`
  başarısız listesinde. Kısa TF'de komisyon baskın. Zayıf prior ile test edilir.
"""
from motor.strateji.swing.bant_donus import BantDonus as _Swing


class BantDonus(_Swing):
    ad = "scalp__bant-donus"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "bb_periyot": 40, "bb_sapma": 2.0,
                               "rsi_periyot": 5, "rsi_esik": 30.0, "adx_esik": 25.0, "hedef_tipi": "karsi"}
    parametre_izgarasi = {
        "bb_periyot": [20, 40],
        "bb_sapma": [2.0, 2.5],
        "rsi_esik": [0.0, 20.0, 30.0],
        "hedef_tipi": ["orta", "karsi"],
    }
