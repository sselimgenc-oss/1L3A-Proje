# BTCUSD Supertrend + EMA Trend Filter (1H) (`NgSIfKQx`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/NgSIfKQx-Bitcoin-SuperFlip-Supertrend-EMA-Trend-Following-Strategy/
- Kaynak: 154 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("BTCUSD Supertrend + EMA Trend Filter (1H)", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=25, commission_type=strategy.commission.percent, commission_value=0.075, slippage=1)
```

## Ne yapıyor
BTCUSD Supertrend + EMA Trend Filter 1H (NgSIfKQx): Supertrend(10,1.8) dönüşü + EMA200 filtresi; ters dönüşte pozisyon kapanır.

## Koddan kanıt (satır: kod)
```
76: strategy.entry("Long", strategy.long)
79: strategy.entry("Short", strategy.short)
82: strategy.close("Long")
84: strategy.close("Short")
89: strategy.exit("Long SL/TP", "Long", stop = entryPrice * (1 - slPct),
95: strategy.exit("Short SL/TP", "Short", stop = entryPrice * (1 + slPct),
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/st_ema_btc.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Yazar BTCUSD 1 saatlik için yazmış; kripto 1 saatlik (14 coin).
