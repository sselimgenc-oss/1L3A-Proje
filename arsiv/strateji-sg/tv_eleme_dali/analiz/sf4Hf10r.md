# 8PM MGC 5M - $445 Risk $1000 Reward - DEFAULT (`sf4Hf10r`)

- Yazar: Edge-Session · Link: https://tr.tradingview.com/script/sf4Hf10r/
- Kaynak: 200 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("8PM MGC 5M - $445 Risk $1000 Reward - DEFAULT", shorttitle="8PM MGC $445/$1000 DEFAULT V6", overlay=true, initial_capital=100000, currency=currency.USD, pyramiding=1, calc_on_every_tick=false, calc_on_order_fills=true, max_boxes_count=500, max_lines_count=500, max_labels_count=500)
```

## Ne yapıyor
MGC (mikro altın vadeli) 5 dk, 20:00 NY aralık mumu, $445 risk / $1000 ödül.

## Koddan kanıt (satır: kod)
```
2: strategy("8PM MGC 5M - $445 Risk $1000 Reward - DEFAULT", shorttitle="8PM MGC $445/$1000 DEFAULT V6", overlay=true, initial_capital=100000, currency=c
5: grp_time = "TIME & RISK - MGC"
6: rangeTime = input.session("2000-2005", title="Range Candle Time (NY)", group=grp_time)
8: riskDollars = input.float(445, title="Risk Per Trade $ (MGC)", step=5, group=grp_time)
9: rewardDollars = input.float(1000, title="Reward Per Trade $ (MGC)", step=50, group=grp_time)
12: pointValueMGC = input.float(10, title="MGC Point Value $ (1$ = 10$)", group=grp_time)
38: isRangeCandle = not na(time("5", rangeTime, "America/New_York")) and isAllowedDay
85: rangeLabel := label.new(x=bar_index, y=rangeHigh, text="RANGE MGC " + str.tostring(rangeHigh) + " - " + str.tostring(rangeLow), style=label.style_labe
135: float qtyFloat = riskDollars / (riskDist * pointValueMGC)
141: strategy.entry(longId, strategy.long, qty=qty)
157: entryLabel := label.new(x=bar_index, y=close, text="◍ LONG MGC x" + str.tostring(qty) + " 445$->1000$", style=label.style_label_up, color=color.new(#0
170: float qtyFloat = riskDollars / (riskDist * pointValueMGC)
176: strategy.entry(shortId, strategy.short, qty=qty)
192: entryLabel := label.new(x=bar_index, y=close, text="◍ SHORT MGC x" + str.tostring(qty) + " 445$->1000$", style=label.style_label_down, color=color.new
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
