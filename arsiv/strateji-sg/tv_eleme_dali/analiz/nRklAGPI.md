# 3% max drawdown - Performs just as good as Nasdaq — Strategy by finnick1111 (`nRklAGPI`)

- Yazar: finnick1111 · Link: https://tr.tradingview.com/script/nRklAGPI-3-max-drawdown-Performs-just-as-good-as-Nasdaq/
- Kaynak: 162 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · QQQ
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("", overlay = true, default_qty_type = strategy.fixed, default_qty_value = 0, currency = currency.USD, initial_capital = 7500, pyramiding = 0, calc_on_order_fills = false)
```

## Ne yapıyor
3% max drawdown (nRklAGPI): QQQ'da long-only makro sistem. Giriş: SPY dibi 4 gün üst üste EMA21 üstü, QQQ dibi EMA10/21 üstü, son 3 gün üst üste düşüş yok, SPY ADX(13)>16 — ya da BTC yükseliş + SPY>SMA7 yardımı; SPY son 116 mumda ATH yapmışsa. Çıkış: zarardaki işlemde QQQ<EMA21 ve SPY<SMA7; kârdaki işlemde (SPY SMA7<SMA107[1] ve zayıf) ya da (%3.5 stop altı + SMA50 altı). (Betikteki çöküş-bekleme mantığı, eşik %20 yüzde değil oran olarak yazıldığından hiç tetiklenmez; çıkarıldı.)

## Koddan kanıt (satır: kod)
```
5: crashTriggerPerc = input.float(20.0, "Crash Trigger Drop From SPX ATH (%)", minval = 1.0, step = 0.5) / 100
9: spxClose = request.security("SPY", "D", close)
10: spxLow = request.security("SPY", "D", low)
16: qqqClose = request.security("QQQ", "D", close)
17: qqqLow = request.security("QQQ", "D", low)
22: btcClose = request.security("INDEX:BTCUSD", "D", close)
23: btcLow = request.security("INDEX:BTCUSD", "D", low)
63: spxCrash20Plus = not na(spxAllTimeHigh) and spxDrawdownFromAth >= crashTriggerPerc
102: spxAdxValue = request.security("SPX", "D", getADX())
105: longCondition = spxLowAbove21Ema4daysInARow and qqqLowAboveKeyEmas and qqqNotShowingWeakness and isTrending
125: exitCondition = not forceRecoveryHold and (losingTradeFastExit or winningTradeNormalExit)
```

## Repaint / lookahead kontrolü
Üç dış sembol `request.security(..., "D", close)` (lookahead parametresiz = off); günlük grafikte aynı mumda.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/qqq_macro.py` olarak çevrilip test edildi. Betikteki çöküş-eşiği (%20) oran olarak karşılaştırıldığından hiç tetiklenmez: çıkarıldı.
