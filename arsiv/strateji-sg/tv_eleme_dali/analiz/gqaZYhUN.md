# Momentum Exhaustion Breakout (`gqaZYhUN`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/gqaZYhUN-Momentum-Bands-Breakout/
- Kaynak: 111 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Momentum Exhaustion Breakout", overlay=true, initial_capital=100000, default_qty_type=strategy.fixed, pyramiding=0, commission_type=strategy.commission.percent, commission_value=0.05, slippage=1)
```

## Ne yapıyor
Momentum Exhaustion Breakout (gqaZYhUN): 20 bar zirve kırılımı + hacim 1.5× + EMA20>EMA50 + RSI ivmesi → long; düşüş trendinde zayıf RSI ile kırılım → 'fade' short. ATR×1.5 stop + ATR×1.5 izleyen stop.

## Koddan kanıt (satır: kod)
```
62: strategy.entry("Long", strategy.long, qty=qty)
65: strategy.entry("Fade Short", strategy.short, qty=qty)
70: strategy.exit("Exit Long", "Long", stop=stopLong,
75: strategy.exit("Exit Short", "Fade Short", stop=stopShort,
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/mom_exhaust.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 1 saatlik.
