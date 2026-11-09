# Universal Aggressive Trend MACD v3.3 - Trailing TP (`UVosPbFA`)

- Yazar: finnp17 · Link: https://tr.tradingview.com/script/UVosPbFA-Universal-Aggressive-Trend-MACD-v3-3-Trailing-TP/
- Kaynak: 437 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy( "Universal Aggressive Trend MACD v3.3 - Trailing TP", overlay = true, process_orders_on_close = true, calc_on_every_tick = false, initial_capital = 1000, default_qty_type = strategy.percent_of_equity, default_qty_value = 100, pyramiding = 0 )
```

## Ne yapıyor
Universal Aggressive Trend MACD v3.3 (UVosPbFA): MACD(14,39,9) kesişimi 10 mum içinde 'taze' (ya da 5 mumluk zirve kırılımı devam girişi) + EMA99 trend & eğim + ADX(11)>20 + hacim>0.6×SMA22 → giriş (3 mum bekleme); acil stop 2.5 ATR; peak kâr ≥%0.5 olunca kârın %3'ünden fazlası geri verilirse çık (izleyen TP). process_orders_on_close.

## Koddan kanıt (satır: kod)
```
266: strategy.close("Long", comment = "Long Trailing TP")
269: strategy.close("Short", comment = "Short Trailing TP")
276: strategy.close("Long", comment = "Long MACD Reverse")
279: strategy.close("Short", comment = "Short MACD Reverse")
286: strategy.entry("Long", strategy.long, comment = "Long")
297: strategy.entry("Short", strategy.short, comment = "Short")
316: strategy.exit(
323: strategy.exit(
344: totalClosed = strategy.closedtrades
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/macd_aggr.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş (Almanca arayüz, 'Kerzen'); saatlik.
