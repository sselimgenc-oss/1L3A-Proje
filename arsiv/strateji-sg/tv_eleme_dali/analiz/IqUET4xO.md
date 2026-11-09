# Fractal Breakout Trend Following Strategy (`IqUET4xO`)

- Yazar: Skyrexio · Link: https://www.tradingview.com/script/IqUET4xO-Fractal-Breakout-Trend-Following-Strategy/
- Kaynak: 160 satır Pine
- Zaman dilimi / pazar: 4s · kripto (BTC)
- **Karar: AL**

## strategy() bildirimi
```
9: strategy(title = "Fractal Breakout Trend Following Strategy",  shorttitle = "Fractal Strategy", overlay = true, format = format.inherit, pyramiding = 1, calc_on_order_fills = false, calc_on_every_tick = true, default_qty_type = strategy.percent_of_equity, default_qty_value = 30, initial_capital = 10000, currency = currency.NONE, commission_type = strategy.commission.percent, commission_value = 0.1, slippage = 5)
```

## Ne yapıyor
Alligator dişinin üstündeki yukarı fraktal + ATR yüzdelik ort.≤50 → fraktal seviyesine stop-giriş; stop = max(giriş−%3, aşağı fraktal).

## Koddan kanıt (satır: kod)
```
38: var float upFractalActivationLevel    = na
74: upFractalPrice = ta.pivothigh(2, 2)
79: downFractalPrice = ta.pivotlow(2, 2)
92: atrAvg = array.avg(atrValues)
110: upFractalActivationLevel := upFractalLevel
112: upFractalActivationLevel := na
138: longCondition = not na(upFractalActivationLevel) and atrAvg <= atrThreshold
144: strategy.entry(id = "entry1", direction = strategy.long, stop=upFractalActivationLevel, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"
147: strategy.exit(id = "entry1", stop=stopLossLevel, alert_message = '{\n"base": "' + syminfo.basecurrency + '",\n"quote": "' + syminfo.currency + '",\n"p
```

## Repaint / lookahead kontrolü
`ta.pivothigh(2,2)` 2 mum gecikmeli onay → seviye ancak onaylı fraktaldan sonra kullanılıyor; repaint yok. calc_on_every_tick yalnız canlı.

## Karar ve gerekçe
Aday. Bekleyen stop emri bir mum geçerli (Pine'da kalıcı).
