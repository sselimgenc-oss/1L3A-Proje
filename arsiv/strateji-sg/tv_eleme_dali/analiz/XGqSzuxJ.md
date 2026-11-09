# BTC Flip Bot V1 — MTF + SL-Flip (`XGqSzuxJ`)

- Yazar: jagadeeshmanne · Link: https://www.tradingview.com/script/XGqSzuxJ-BTC-MTF-Engulfing-Flip-Strategy-1H-2X/
- Kaynak: 389 satır Pine
- Zaman dilimi / pazar: 1s · kripto (BTC)
- **Karar: AL**

## strategy() bildirimi
```
32: strategy("BTC Flip Bot V1 — MTF + SL-Flip", overlay=true, initial_capital=5000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, pyramiding=0, calc_on_order_fills=false, calc_on_every_tick=false, process_orders_on_close=true, commission_type=strategy.commission.percent, commission_value=0.04, slippage=3, margin_long=0, margin_short=0, use_bar_magnifier=false)
```

## Ne yapıyor
1s BTC: günlük EMA50 + 4s RSI süzgeçleri, MACD+engulfing+hacim patlaması+yüksek ATR girişi; desen tabanlı stop; SL sonrası ters yön 'flip'; 24s bekleme.

## Koddan kanıt (satır: kod)
```
99: useSlFlip      = input.bool(true,   "Enable SL-flip", group=grpFlip,
111: dailyClose = request.security(syminfo.tickerid, "1D", close[1], lookahead=barmerge.lookahead_off)
112: dailyEma50 = request.security(syminfo.tickerid, "1D", ta.ema(close, 50)[1], lookahead=barmerge.lookahead_off)
113: rsi4h      = request.security(syminfo.tickerid, "240", ta.rsi(close, 14)[1], lookahead=barmerge.lookahead_off)
136: longStack  = rsi1h > rsiLongMin and macdLine > macdSignal and bullEngulfing and highVol and volOk
137: shortStack = rsi1h < rsiShortMax and macdLine < macdSignal and bearEngulfing and highVol and volOk
138: longSignal  = longStack and dailyBull and h4ConfBull
139: shortSignal = shortStack and dailyBear and h4ConfBear
151: var int pendingFlipSide = 0       // 0=none, 1=pending LONG, -1=pending SHORT
202: flipReady = useSlFlip and pendingFlipSide != 0 and strategy.position_size == 0 and not na(pendingFlipBar) and (bar_index - pendingFlipBar) >= flipWait
206: if pendingFlipSide == -1
214: strategy.entry("fS", strategy.short, qty=flipQty)
220: else if pendingFlipSide == 1
228: strategy.entry("fL", strategy.long, qty=flipQty)
```

## Repaint / lookahead kontrolü
`request.security(...,"1D", close[1], lookahead_off)` — `[1]` ek gecikme; repaint yok.

## Karar ve gerekçe
Aday. Kısmi kâr (6R'de %15) ve DD durdurma modellenmedi.
