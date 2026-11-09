# EE Sweep Return — STRATEGY v1 (`7OLnQI4B`)

- Yazar: everevolving365 · Link: https://tr.tradingview.com/script/7OLnQI4B-STRATEGY-SCRIPT-Sweep-Return-v1/
- Kaynak: 188 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("EE Sweep Return — STRATEGY v1", "STRATEGY SCRIPT Sweep Return v1", overlay                 = true, process_orders_on_close = true, calc_on_every_tick      = false, pyramiding              = 0, initial_capital         = 50000, default_qty_type        = strategy.fixed, default_qty_value       = 1, commission_type         = strategy.commission.cash_per_contract, commission_value        = 2.00, slippage        
```

## Ne yapıyor
Chicago saati 08:30–09:30 açılış aralığı süpürme-dönüş (50 puan TP / 25 puan SL).

## Koddan kanıt (satır: kod)
```
20: orSess  = input.session("0830-0930",      "Opening range", group = "Session")
48: inOR  = not na(time(timeframe.period, orSess,  tz))
133: strategy.entry("SR Long", strategy.long, comment = "L w" + tag)
137: strategy.entry("SR Short", strategy.short, comment = "S w" + tag)
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
