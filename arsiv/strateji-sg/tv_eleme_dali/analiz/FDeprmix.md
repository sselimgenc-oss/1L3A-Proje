# Supertrend Donchian Breakout (`FDeprmix`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/FDeprmix-TrendLock-Multi-Timeframe-Supertrend-Donchian-Breakout/
- Kaynak: 123 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy("Supertrend Donchian Breakout", shorttitle = "STDB", overlay = true, initial_capital = 10000, default_qty_type = strategy.percent_of_equity, default_qty_value = 25, commission_type = strategy.commission.percent, commission_value = 0.05, slippage = 2, process_orders_on_close = true)
```

## Ne yapıyor
Supertrend Donchian Breakout (FDeprmix): Supertrend yükselişte + 4s HTF supertrend yükselişte + hacim 1.5×ort. → long (kırılım koşulu Pine'daki gibi close>alt kanal); ATR×2 stop, ATR×3 hedef, trend dönünce çıkış. Yalnız long.

## Koddan kanıt (satır: kod)
```
57: htf_dir=request.security(syminfo.tickerid,htf_input,htf_supertrend(),lookahead = barmerge.lookahead_off)
77: strategy.entry("Long",strategy.long)
80: strategy.entry("Short",strategy.short)
97: strategy.exit("Long Exit", "Long", stop = long_stop, limit = long_target)
99: strategy.close("Long")
103: strategy.exit("Short Exit", from_entry = "Short", stop = short_stop, limit = short_target)
105: strategy.close("Short", comment = "Trend Flip")
```

## Repaint / lookahead kontrolü
request.security kullanımı: satır 57: `htf_dir=request.security(syminfo.tickerid,htf_input,htf_supertrend(),lookahead = barmerge.lookahead_off)`. lookahead_off: tarihsel mumlarda önceki kapanmış HTF değeri; çeviride de son kapanmış HTF mum kullanıldı.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/st_donchian.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 1 saatlik (HTF 4s onayıyla uyumlu), yalnız long (Pine varsayılanı).
