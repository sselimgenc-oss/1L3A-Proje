# MACD Pullback Sniper | Trend + ADX Filtered Strategy (`V87nRt9v`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/V87nRt9v-MACD-Pullback-Sniper-Trend-ADX-Filtered-Strategy/
- Kaynak: 119 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy('MACD Pullback Sniper | Trend + ADX Filtered Strategy', overlay = false, initial_capital = 10000, commission_type = strategy.commission.percent, commission_value = 0.05, slippage = 2, pyramiding = 0, margin_long = 100, margin_short = 100)
```

## Ne yapıyor
MACD Pullback Sniper (V87nRt9v): MACD sinyali yukarı keser + fiyat>EMA200 + MACD<0 + ADX>20 → long (short için tersi); stop 2 ATR, hedef 2R; ters MACD kesişiminde çıkış.

## Koddan kanıt (satır: kod)
```
58: longSignal  = bullCross and trendLongOk and zeroLongOk and adxOk and inRange
59: shortSignal = bearCross and trendShortOk and zeroShortOk and adxOk and inRange and allowShort
78: strategy.exit('Long Exit', 'Long', stop = slLvl, limit = tpLvl)
82: strategy.exit('Short Exit', 'Short', stop = slLvl, limit = tpLvl)
88: if exitCross and bearCross and strategy.position_size > 0 and not shortSignal
89: strategy.close('Long', comment = 'MACD cross')
90: if exitCross and bullCross and strategy.position_size < 0 and not longSignal
91: strategy.close('Short', comment = 'MACD cross')
94: if longSignal and strategy.position_size <= 0
98: strategy.entry('Long', strategy.long, qty = q)
99: strategy.exit('Long Exit', 'Long', stop = close - atr * slMult, limit = close + atr * slMult * rrRatio)
101: if shortSignal and strategy.position_size >= 0
105: strategy.entry('Short', strategy.short, qty = q)
106: strategy.exit('Short Exit', 'Short', stop = close + atr * slMult, limit = close - atr * slMult * rrRatio)
```

## Repaint / lookahead kontrolü
Yalnız geçmiş mum. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/macd_sniper.py` olarak çevrilip test edildi.
