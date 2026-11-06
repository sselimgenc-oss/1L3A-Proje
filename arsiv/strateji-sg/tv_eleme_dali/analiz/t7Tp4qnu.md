# ORB Breakout - Scalping Strategy (`t7Tp4qnu`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/t7Tp4qnu-ORB-Pro-Session-Breakout-Scalper/
- Kaynak: 282 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
5: strategy("ORB Breakout - Scalping Strategy", overlay=true, fill_orders_on_standard_ohlc = true, max_lines_count = 500, max_boxes_count = 500, max_labels_count = 500, commission_type = strategy.commission.percent, commission_value = 0.05, slippage = 2)
```

## Ne yapıyor
5 dk ORB scalping.

## Koddan kanıt (satır: kod)
```
70: if not timeframe.isintraday
201: strategy.entry("Long", strategy.long, qty=longQty)
206: strategy.entry("Short",strategy.short, qty=shortQty)
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
