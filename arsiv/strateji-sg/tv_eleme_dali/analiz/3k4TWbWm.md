# China A-Share Long Trend Resonance System (CLR System) (`3k4TWbWm`)

- Yazar: p181342x · Link: https://tr.tradingview.com/script/3k4TWbWm/
- Kaynak: 419 satır Pine
- Zaman dilimi / pazar: ? · Çin A hisse
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("China A-Share Long Trend Resonance System (CLR System)",  overlay=true, pyramiding=0, default_qty_type=strategy.percent_of_equity, default_qty_value=100, calc_on_every_tick=true, process_orders_on_close=true)
```

## Ne yapıyor
Çin A-hisse uzun trend rezonansı: Çin borsa verisi/sembolleri.

## Koddan kanıt (satır: kod)
```
87: dTrend = request.security(syminfo.tickerid, "D", trend)
92: wHMA = request.security(syminfo.tickerid, "W", ta.hma(close, hmaLen))
94: wClose = request.security(syminfo.tickerid, "W", close)
126: strategy.entry("LONG", strategy.long)
```

## Repaint / lookahead kontrolü
—

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok (Çin A-hisse).
