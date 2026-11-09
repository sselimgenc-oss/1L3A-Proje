# BB Power Oscillator + Squeeze Release (`M6uONKNI`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/M6uONKNI-Power-Surge-BB-Momentum-Squeeze-Release/
- Kaynak: 180 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("BB Power Oscillator + Squeeze Release", shorttitle="BB Power+Sqz", overlay=false, commission_type=strategy.commission.percent, commission_value=0.05, default_qty_type=strategy.cash, default_qty_value=1000, initial_capital=1000, currency=currency.USD)
```

## Ne yapıyor
BB Power Oscillator + Squeeze Release (M6uONKNI): Bollinger üstü/altı taşma gücü osilatörü (bull/bear, 14 mum) 50'yi yukarı keserse (sıkışma sonrası 10 mum içinde) long/short; stop 1.4 ATR(30), hedef 1.5R, 0.75R'de başa-baş + ATR(1.5) izleyen stop, 50 mumda çıkış.

## Koddan kanıt (satır: kod)
```
82: squeezeReleased = squeezeOff and squeezeOn[1]
85: if squeezeReleased
98: bull_cross = ta.crossover(bull, threshold)
99: bear_cross = ta.crossover(bear, threshold)
101: longCondition  = bull_cross and inReleaseWindow and strategy.position_size == 0
102: shortCondition = bear_cross and inReleaseWindow and strategy.position_size == 0
119: strategy.entry("Long", strategy.long, qty=qty)
127: strategy.entry("Short", strategy.short, qty=qty)
160: strategy.exit("Long Exit", "Long", stop=trailStop, limit=target)
172: strategy.exit("Short Exit", "Short", stop=trailStop, limit=target)
```

## Repaint / lookahead kontrolü
Yalnız geçmiş mum. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/bb_power.py` olarak çevrilip test edildi.
