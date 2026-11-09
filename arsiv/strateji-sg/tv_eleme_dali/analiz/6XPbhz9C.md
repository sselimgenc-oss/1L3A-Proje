# Mean Reversion Setup LliterH (`6XPbhz9C`)

- Yazar: LliterH · Link: https://www.tradingview.com/script/6XPbhz9C/
- Kaynak: 125 satır Pine
- Zaman dilimi / pazar: 1g · ABD endeks (SPX), ayrıca Nasdaq/altın
- **Karar: AL**

## strategy() bildirimi
```
21: strategy( "Mean Reversion Setup LliterH", overlay           = true, initial_capital   = 100000, default_qty_type  = strategy.percent_of_equity, default_qty_value = 100, currency          = currency.USD)
```

## Ne yapıyor
10g tepe−2.5×25g ort. aralık altında kapanış + IBS<0.3 + SMA50 üstü → long; kapanış-bazlı sert stop (2 ATR); bacak 1 (%50) kapanış>önceki tepe, bacak 2 (%50) izleyen stop 1.5 ATR.

## Koddan kanıt (satır: kod)
```
61: float buyThreshold = highest10 - (multiplier * avgRange25)
62: float ibs          = (high == low) ? 0.0 : (close - low) / (high - low)
70: bool condIBS    = ibs < ibsMax
73: bool longCondition = condPrice and condIBS and condRegime and strategy.position_size == 0
96: bool hardStopFired = inPos and not na(hardStopLevel) and close <= hardStopLevel
97: bool leg1Fired     = inPos and not hardStopFired and close > high[1]
98: bool leg2Fired     = inPos and not hardStopFired and not leg1Fired and not na(trailLevel) and close <= trailLevel
107: if hardStopFired
111: if leg1Fired
112: strategy.close("Buy", qty_percent = 50, comment = "Leg 1 (50%)")
115: if leg2Fired
```

## Repaint / lookahead kontrolü
Tüm koşullar kapanışta; `strategy.close(qty_percent=50)`. Repaint yok.

## Karar ve gerekçe
Aday. Kısmi çıkış iki bacak olarak (olcek=0.5) modellendi; Pine'daki ardışık %50 azaltmalar tek sefer sayıldı.
