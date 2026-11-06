# Flawless Victory Strategy (`i3Uc79fF`)

- Yazar: Trebor_Namor · Link: https://www.tradingview.com/script/i3Uc79fF-Flawless-Victory-Strategy-15min-BTC-Machine-Learning-Strategy/
- Kaynak: 136 satır Pine
- Zaman dilimi / pazar: 15dk · kripto (BTC)
- **Karar: AL**

## strategy() bildirimi
```
5: strategy(overlay=true, shorttitle="Flawless Victory Strategy", default_qty_type = strategy.percent_of_equity, initial_capital = 100000, default_qty_value = 100, pyramiding = 0, title="Flawless Victory Strategy", currency = 'USD')
```

## Ne yapıyor
BB(20,1σ) alt bandının altında + RSI>42 → long; üst bandın üstünde + RSI>70 → çık. v1 varsayılan (SL/TP yok).

## Koddan kanıt (satır: kod)
```
80: BBBuyTrigger1 = src1 < lower1
82: rsiBuyGuard1 = rsi > RSILowerLevel1
109: Buy_1 = BBBuyTrigger1 and rsiBuyGuard1
110: Sell_1 = BBSellTrigger1 and rsiSellGuard1
113: strategy.entry("Long", strategy.long, when = Buy_1, alert_message = "v1 - Buy Signal!")
122: strategy.entry("Long", strategy.long, when = Buy_2, alert_message = "v2 - Buy Signal!")
132: strategy.entry("Long", strategy.long, when = Buy_3, alert_message = "v2 - Buy Signal!")
```

## Repaint / lookahead kontrolü
Pine v4 betiği; security yok. Temiz.

## Karar ve gerekçe
Aday (varsayılan sürüm 1). Pine v4 `when=` sözdizimi; mantık basit.
