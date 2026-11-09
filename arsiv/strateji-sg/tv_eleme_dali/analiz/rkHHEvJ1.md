# VWAP 3rd SD Mean Reversion - BUY/SELL + Exits (`rkHHEvJ1`)

- Yazar: Bull-and-Wolf · Link: https://tr.tradingview.com/script/rkHHEvJ1-Bull-Wolf-Nifty-Indicator/
- Kaynak: 226 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
3: strategy("VWAP 3rd SD Mean Reversion - BUY/SELL + Exits", overlay=true, initial_capital=25000, pyramiding=0, default_qty_type=strategy.cash, default_qty_value=25000, commission_type=strategy.commission.cash_per_contract, commission_value=0.0035, slippage=2, calc_on_every_tick=true, calc_on_order_fills=false, process_orders_on_close=true, margin_long=0, margin_short=0, max_labels_count=500)
```

## Ne yapıyor
VWAP 3. standart sapma ortalamaya dönüş (gün içi).

## Koddan kanıt (satır: kod)
```
46: if not timeframe.isintraday
150: strategy.entry("VWAP Long", strategy.long, qty=qtyLong, limit=entryLong,
167: strategy.entry("VWAP Short", strategy.short, qty=qtyShort, limit=entryShort,
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
