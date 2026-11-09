# Sequence Snap | RSI-Confirmed Reversal Scalper (`49jNhJXM`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/49jNhJXM-Sequence-Snap-RSI-Confirmed-Reversal-Scalper/
- Kaynak: 220 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
7: strategy( "Sequence Snap | RSI-Confirmed Reversal Scalper", overlay = true, pyramiding = 0, initial_capital = 50000, currency = currency.USD, default_qty_type = strategy.percent_of_equity, default_qty_value = 20, commission_type = strategy.commission.percent, commission_value = 0.05, slippage = 1, margin_long = 5, margin_short = 5 )
```

## Ne yapıyor
Sequence Snap (49jNhJXM): kırmızı ana mumdan sonra 5 ardışık yeşil mum (kapanışlar %0.05 toleransla artan, düşükler ana mum dibi üstünde) + RSI(14)>40 ve yükseliyor → long; stop ana mum dibi, hedef 1.5R. Yalnız long (short varsayılan kapalı).

## Koddan kanıt (satır: kod)
```
93: bool runIsBullish = true
97: runIsBullish := false
99: runIsBullish := false
103: runIsBullish := false
119: longSetup  = reversalWasDown and runIsBullish and rsiOkLong
123: if enableLongTrades and longSetup and strategy.position_size == 0
127: strategy.entry("Long", strategy.long)
134: strategy.entry("Short", strategy.short)
152: bgcolor(showFlash and longSetup and enableLongTrades ? color.new(colBull, 85) : na, title = "Long Entry Flash")
157: showSignal and enableLongTrades and longSetup and strategy.position_size == 0,
```

## Repaint / lookahead kontrolü
Yalnız geçmiş mum dizisi + RSI. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «scalper (5dk veri yok)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/seq_snap.py` olarak çevrilip test edildi. Betik 5 dk ile sınırlı değil (hiçbir saat/seans kodu yok), saatlik test edildi.
