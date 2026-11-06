# Vol-Target Trend Engine (`2wyXTTMc`)

- Yazar: mateosandoval1025 · Link: https://www.tradingview.com/script/2wyXTTMc-Vol-Target-Trend-Engine/
- Kaynak: 89 satır Pine
- Zaman dilimi / pazar: 1g · ABD ETF (TQQQ)/hisse
- **Karar: AL**

## strategy() bildirimi
```
26: strategy("Vol-Target Trend Engine", shorttitle="VTTE", overlay=true, initial_capital=10000, commission_type=strategy.commission.percent, commission_value=0.05, slippage=1, pyramiding=500, process_orders_on_close=true, calc_on_every_tick=false)
```

## Ne yapıyor
SMA200 üstü rejimde hedef maruziyet=min(1, %45/20g gerçekleşen oynaklık); haftalık yeniden dengeleme; rejim kapanınca tam çıkış (strategy.order ile kısmi ekleme/azaltma).

## Koddan kanıt (satır: kod)
```
32: targetVol = input.float(45.0,"Target annualized vol (%)",     minval=5,  step=1.0)
38: realVol = ta.stdev(retD, volLen) * math.sqrt(252) * 100.0
40: regime  = close > smaReg
42: frac      = math.min(1.0, targetVol / math.max(realVol, 1.0))
47: weekTurn   = timeframe.change("1W")
51: if weekTurn or regimeFlip or overExp
53: strategy.close_all(comment="regime off")
56: strategy.order("Add",  strategy.long,  qty=delta,  comment="scale up")
58: strategy.order("Trim", strategy.short, qty=-delta, comment="de-risk")
83: table.cell(tb, 1, 1, str.tostring(realVol, "#.0") + "%", text_color=hdrCol, text_size=size.small)
89: table.cell(tb, 1, 4, str.tostring(targetVol, "#") + "%", text_color=hdrCol, text_size=size.small)
```

## Repaint / lookahead kontrolü
`request.security` yok; haftalık tetik `timeframe.change("1W")`. Repaint yok.

## Karar ve gerekçe
Aday. Yaklaşık çeviri: yeniden dengeleme (kısmi ekle/azalt) motorda yok; rejim girişinde hedef maruziyet kadar boyutlanıp rejim bitince çıkılıyor.
