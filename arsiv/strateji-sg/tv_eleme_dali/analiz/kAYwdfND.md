# Simplified 30m Event Strategy - Reverse (`kAYwdfND`)

- Yazar: mbdalq · Link: https://www.tradingview.com/script/kAYwdfND/
- Kaynak: 63 satır Pine
- Zaman dilimi / pazar: 5 dk (altı 30 dk request.security) · belirsiz: minRange=5 puan → endeks/altın vadeli
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("Simplified 30m Event Strategy - Reverse", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=10, pyramiding=1)
```

## Ne yapıyor
30 dk tepe/dip pivotlarından destek-direnç alır; 5 dk mumda `delta = close>open ? volume : -volume` ve fiyatın son 30 dk dibinin üstünde olması durumunda TERS yönde (delta<0 iken long) girer, 6 mum sonra çıkar (zaman çıkışı). Yüzde 10 sermaye.

## Koddan kanıt (satır: kod)
```
7: exitBars = input.int(6, "Exit after X bars (5min)")
10: high30  = request.security(syminfo.tickerid, "30", high)
11: low30   = request.security(syminfo.tickerid, "30", low)
12: close30 = request.security(syminfo.tickerid, "30", close)
15: ph30 = ta.pivothigh(high30, left, right)
16: pl30 = ta.pivotlow(low30, left, right)
48: if longBarCount >= exitBars
49: strategy.close("Long")
50: if shortBarCount >= exitBars
51: strategy.close("Short")
55: strategy.entry("Long", strategy.long)
57: strategy.entry("Short", strategy.short)
```

## Repaint / lookahead kontrolü
`request.security(...,"30", high)` lookahead parametresiz (varsayılan off). 30 dk pivot ph30/pl30 `ta.pivothigh(left=2,right=3)` ile 3 mum gecikmeli onaylanıyor (repaint değil). Asıl sorun veri.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — 5 dk geçmişi (endeks/altın vadeli) Yahoo'da 60 günle sınırlı, 164+92 betikte tek sembol belirtilmemiş; 6 mumluk (30 dk) tutma = gün içi, ≥300 işlem kuralı bu veriyle sağlanamaz.
