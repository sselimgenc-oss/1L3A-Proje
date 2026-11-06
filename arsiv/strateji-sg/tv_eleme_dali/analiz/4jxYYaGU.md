# Traling.SL.Target (`4jxYYaGU`)

- Yazar: Sharad_Gaikwad · Link: https://tr.tradingview.com/script/4jxYYaGU-Traling-SL-Target/
- Kaynak: 236 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
5: strategy("Traling.SL.Target", overlay=true, process_orders_on_close = true, max_labels_count = 500)
```

## Ne yapıyor
İz süren SL/hedef aracı: giriş `go_long/go_short` kullanıcı sinyaline bağlı.

## Koddan kanıt (satır: kod)
```
83: go_long = ta.crossover(fast_ema, slow_ema) and strategy.position_size == 0
84: go_short = ta.crossunder(fast_ema, slow_ema) and strategy.position_size == 0
132: if(go_long)
149: strategy.entry(id = 'Long', direction = strategy.long)
151: if(go_short)
168: strategy.entry(id = 'Short', direction = strategy.short)
184: label.new(go_long ? bar_index : na, go_long ? bar_index : na,
187: label.new(go_short ? bar_index : na, go_short ? bar_index : na,
```

## Repaint / lookahead kontrolü
—

## Karar ve gerekçe
KESİN ELEME: araç — kendi giriş sinyali yok, sinyal kullanıcıdan.
