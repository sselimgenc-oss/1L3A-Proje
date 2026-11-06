# Silver Always Long + Macro Exit + Flush Protection v2 (`mzv5SGie`)

- Yazar: CuriousMacroX · Link: https://tr.tradingview.com/script/mzv5SGie-Silver-Risk-Management-outperformed-Buy-Hold/
- Kaynak: 201 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · GUMUS,ALTIN
- **Karar: AL**

## strategy() bildirimi
```
9: strategy("Silver Always Long + Macro Exit + Flush Protection v2", overlay=true, initial_capital=10000, commission_type=strategy.commission.percent, commission_value=0.10, slippage=2, default_qty_type=strategy.percent_of_equity, default_qty_value=100, pyramiding=0, calc_on_every_tick=false, process_orders_on_close=true)
```

## Ne yapıyor
Silver Always Long + Macro Exit + Flush Protection v2 (mzv5SGie): gümüşte hep long; çıkış: kapanış EMA150 altı, ya da ABD 10Y faizi EMA50'nin %1.35 üstünde + 20 günlük tepe kırılımı (3 mum üst üste), ya da ani düşüş (1g −%4.5 / 2g −%8 / ATR şoku); yeniden giriş: faiz sakin, düşüş sonrası EMA75 üstü + oynaklık sakin. Kapanışta işlem (process_orders_on_close).

## Koddan kanıt (satır: kod)
```
74: dxyClose    = request.security(dxySymbol, timeframe.period, close, barmerge.gaps_off, barmerge.lookahead_off)
75: dxyEma      = request.security(dxySymbol, timeframe.period, ta.ema(close, dxyLen), barmerge.gaps_off, barmerge.lookahead_off)
76: dxyHighPrev = request.security(dxySymbol, timeframe.period, ta.highest(high[1], dxyBreakoutLookback), barmerge.gaps_off, barmerge.lookahead_off)
78: us10yClose    = request.security(us10ySymbol, timeframe.period, close, barmerge.gaps_off, barmerge.lookahead_off)
79: us10yEma      = request.security(us10ySymbol, timeframe.period, ta.ema(close, us10yLen), barmerge.gaps_off, barmerge.lookahead_off)
80: us10yHighPrev = request.security(us10ySymbol, timeframe.period, ta.highest(high[1], us10yBreakoutLookback), barmerge.gaps_off, barmerge.lookahead_off)
121: exitCondition = inTradeWindow and (silverTrendExit or macroStressPersist or flushShockNow)
123: entryCondition = inTradeWindow and strategy.position_size == 0 and not silverTrendExit and macroCalmPersist and flushRecoveryReady
126: strategy.close("Long")
129: strategy.entry("Long", strategy.long)
```

## Repaint / lookahead kontrolü
`request.security(...,lookahead_off)`; DXY/US10Y günlük veri.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/silver_macro.py` olarak çevrilip test edildi. Veri: ^TNX (Yahoo); DXY çıkışı varsayılanda kapalı.
