# Sovereign Horizon Matrix (SHM) v8.0 (`wVNfdkHu`)

- Yazar: Kenpachi_ii · Link: https://tr.tradingview.com/script/wVNfdkHu-Sovereign-Horizon-Matrix-SHM-v8-0/
- Kaynak: 493 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Sovereign Horizon Matrix (SHM) v8.0", overlay=true, max_labels_count=500, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=80, pyramiding=0, commission_type=strategy.commission.percent, commission_value=0.075, slippage=30, margin_long=25, margin_short=33.3)
```

## Ne yapıyor
Sovereign Horizon Matrix v8.0 (wVNfdkHu): hızlı WMA(63) ve makro WMA(510) (ohlc4); kapanış ya da tepe/dip bu WMA'ları yukarı/aşağı keserse, kapanış > SMA(41) (aşağı için <) ve günlük RSI(33) (iki gün gecikmeli) 42–48 (long) / 46–52 (short) bandındaysa giriş; stop tetik mumunun dibi/tepesi ∓%3 (varsayılan 'Candle-Close Trail' modülü %77 mesafede olduğundan fiilen yalnız bu stop çalışır); ters sinyalde dön.

## Koddan kanıt (satır: kod)
```
114: rsi_val = request.security(syminfo.tickerid, rsi_tf, rsi_raw[1], barmerge.gaps_off, barmerge.lookahead_off)
333: strategy.entry("Buy", strategy.long)
339: strategy.entry("Sell", strategy.short)
428: strategy.exit("Long TP1", from_entry="Buy", qty_percent=tp1_qty_pct, limit=long_tp1, stop=mod1_sl_long)
430: strategy.exit("Long TP2", from_entry="Buy", qty_percent=tp2_qty_pct, limit=long_tp2, stop=mod1_sl_long)
432: strategy.exit("Long TP3", from_entry="Buy", qty_percent=tp3_qty_pct, limit=long_tp3, stop=mod1_sl_long)
436: strategy.exit("Short TP1", from_entry="Sell", qty_percent=tp1_qty_pct, limit=short_tp1, stop=mod1_sl_short)
438: strategy.exit("Short TP2", from_entry="Sell", qty_percent=tp2_qty_pct, limit=short_tp2, stop=mod1_sl_short)
440: strategy.exit("Short TP3", from_entry="Sell", qty_percent=tp3_qty_pct, limit=short_tp3, stop=mod1_sl_short)
455: strategy.exit("Long WMA Exit", from_entry="Buy", stop=active_mod2_sl_long)
458: strategy.exit("Short WMA Exit", from_entry="Sell", stop=active_mod2_sl_short)
470: strategy.exit("Long Candle Trail Exit", from_entry="Buy", stop=active_mod3_sl_long)
473: strategy.exit("Short Candle Trail Exit", from_entry="Sell", stop=active_mod3_sl_short)
479: strategy.exit("Long Guardrail", from_entry="Buy", stop=active_sl)
```

## Repaint / lookahead kontrolü
request.security kullanımı: satır 114: `rsi_val = request.security(syminfo.tickerid, rsi_tf, rsi_raw[1], barmerge.gaps_off, barmerge.lookahead_off)`. lookahead_off: tarihsel mumlarda önceki kapanmış HTF değeri; çeviride de son kapanmış HTF mum kullanıldı.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/shm.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. RSI'si günlük (1440) kilitli, WMA(510) uzun; gün içi grafik → saatlik.
