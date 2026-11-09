# Universal Strategy Feed (`gU6RDuh5`)

- Yazar: Options360 · Link: https://tr.tradingview.com/script/gU6RDuh5-Universal-Strategy-Feed/
- Kaynak: 171 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
11: strategy("Universal Strategy Feed", shorttitle = "UNI STRAT", overlay = true, default_qty_type      = strategy.fixed, default_qty_value     = 1, initial_capital       = 1000000, margin_long           = 100, margin_short          = 100, commission_type       = strategy.commission.percent, commission_value      = 0.05, pyramiding            = 0, calc_on_every_tick    = false, process_orders_on_close = true)
```

## Ne yapıyor
Universal Strategy Feed: başka göstergenin çıktısını (`input.source`) giriş/çıkış sinyali olarak okur.

## Koddan kanıt (satır: kod)
```
40: srcA   = input.source(ohlc4, "Source A  (primary / long)",            group = gSig)
41: srcB   = input.source(ohlc4, "Source B  (two-source modes / short)",  group = gSig)
42: src3   = input.source(ohlc4, "Source C  (third source, 3-source mode)", group = gSig)
98: goLong  = invert ? shortRaw : longRaw
99: goShort = invert ? longRaw  : shortRaw
119: tpFeed = input.source(ohlc4, "TP feed  (Feed mode -> e.g. AI.1U: Take Profit Hit)", group = gEx)
120: slFeed = input.source(ohlc4, "SL feed  (Feed mode -> e.g. AI.1U: Stop Loss Hit)",   group = gEx)
134: buy  = goLong  and inWindow and lastSig != 1
135: sell = goShort and inWindow and lastSig != -1 and not buy   // buy wins a same-bar tie
148: strategy.entry("Long", strategy.long, qty = qty)
150: strategy.entry("Short", strategy.short, qty = qty)
```

## Repaint / lookahead kontrolü
—

## Karar ve gerekçe
KESİN ELEME: altyapı — sinyal dış gösterge çıktısı (kendi mantığı yok).
