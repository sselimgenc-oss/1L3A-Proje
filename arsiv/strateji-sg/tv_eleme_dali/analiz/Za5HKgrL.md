# ICT 10AM First FVG Daily Strategy (`Za5HKgrL`)

- Yazar: mehmettopbas_ · Link: https://tr.tradingview.com/script/Za5HKgrL-ICT-10AM-First-FVG-Daily-Strategy/
- Kaynak: 317 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("ICT 10AM First FVG Daily Strategy", overlay=true, pyramiding=0, initial_capital=100000, default_qty_type=strategy.fixed, default_qty_value=1, commission_type=strategy.commission.cash_per_contract, commission_value=0, calc_on_order_fills=true, process_orders_on_close=false, margin_long=1, margin_short=1, max_boxes_count=100, max_lines_count=500, max_labels_count=500)
```

## Ne yapıyor
10:00 NY ilk FVG (1–5 dk).

## Koddan kanıt (satır: kod)
```
22: int startHour = input.int(10, "Setup start hour", minval=0, maxval=23, group=GROUP_SESSION)
36: int nyHour = hour(time, timezoneInput)
42: int nyMinutes = nyHour * 60 + nyMinute
48: bool atStart = nyHour == startHour and nyMinute == 0
49: bool inSetupWindow = nyHour >= startHour and nyHour < endHour
50: bool atOrAfterEnd = nyHour >= endHour
55: bool fvgGeneratorInsideWindow = hour(time[1], timezoneInput) >= startHour and hour(time[1], timezoneInput) < endHour
175: strategy.entry("Daily Long", strategy.long, qty=orderQty, limit=entryPrice)
178: strategy.entry("Daily Short", strategy.short, qty=orderQty, limit=entryPrice)
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
