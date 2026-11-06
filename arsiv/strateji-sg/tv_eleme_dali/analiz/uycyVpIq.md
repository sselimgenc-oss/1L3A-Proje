# Advanced Ichimoku Clouds Strategy Long and Short (`uycyVpIq`)

- Yazar: Skyrexio · Link: https://www.tradingview.com/script/uycyVpIq-Ichimoku-Clouds-Strategy-Long-and-Short/
- Kaynak: 207 satır Pine
- Zaman dilimi / pazar: ? · kripto
- **Karar: AL**

## strategy() bildirimi
```
10: strategy(title = "Advanced Ichimoku Clouds Strategy Long and Short",  shorttitle = "Ichimoku Strategy Long and Short", overlay = true, format = format.inherit, pyramiding = 1, calc_on_order_fills = false, calc_on_every_tick = true, default_qty_type = strategy.percent_of_equity, default_qty_value = 100, initial_capital = 10000, currency = currency.NONE, commission_type = strategy.commission.percent, commission_value =
```

## Ne yapıyor
Varsayılan: Tenkan/Kijun yukarı kesişimde long (tüm bulut konumları), 'Bearish Weak' çıkışı (aşağı kesişim Tenkan her iki bulut çizgisinin üstündeyken).

## Koddan kanıt (satır: kod)
```
37: entrySignalOptionsLong = input.string("Bullish All", "Select Entry Signal (Long)", options = ["None", "Bullish Strong", "Bullish Neutral", "Bullish We
38: exitSignalOptionsLong = input.string("Bearish Weak", "Select Exit Signal (Long)", options = ["None", "Bearish Strong", "Bearish Neutral", "Bearish Wea
82: displacedSenkouA = senkouA[displacement - 1]
83: displacedSenkouB = senkouB[displacement - 1]
94: bullishSignal = ta.crossover(tenkan, kijun)
99: strongBullishSignal = bullishSignalValues > displacedSenkouA and bullishSignalValues > displacedSenkouB
100: neutralBullishSignal = ((bullishSignalValues > displacedSenkouA and bullishSignalValues < displacedSenkouB) or (bullishSignalValues < displacedSenkouA
101: weakBullishSignal = bullishSignalValues < displacedSenkouA and bullishSignalValues < displacedSenkouB
103: strongBearishSignal = bearishSignalValues < displacedSenkouA and bearishSignalValues < displacedSenkouB
104: neutralBearishSignal = ((bearishSignalValues > displacedSenkouA and bearishSignalValues < displacedSenkouB) or (bearishSignalValues < displacedSenkouA
105: weakBearishSignal = bearishSignalValues > displacedSenkouA and bearishSignalValues > displacedSenkouB
110: if entrySignalOptionsLong == "None"
112: else if entrySignalOptionsLong == "Bullish Strong"
114: else if entrySignalOptionsLong == "Bullish Neutral"
```

## Repaint / lookahead kontrolü
Repaint yok; bulut çizgileri displacement-1 kadar geçmişe (geleceğe değil).

## Karar ve gerekçe
Aday.
