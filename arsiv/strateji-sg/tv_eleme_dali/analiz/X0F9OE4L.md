# EMA Ribbon Fan Angle Strategy (`X0F9OE4L`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/X0F9OE4L-Gradient-Ribbon-EMA-Ribbon-Slope-Acceleration-System/
- Kaynak: 144 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("EMA Ribbon Fan Angle Strategy", overlay=true, initial_capital=10000, default_qty_type=strategy.fixed, default_qty_value=1, commission_type=strategy.commission.percent, commission_value=0.05, slippage=1)
```

## Ne yapıyor
EMA Ribbon Fan Angle (X0F9OE4L): 5 EMA (8-55) yelpazesi açılırken + RSI + hacim filtresi; ATR×2 stop, 2R hedef, yelpaze kapanınca çıkış.

## Koddan kanıt (satır: kod)
```
103: strategy.entry("Long", strategy.long, qty=qty)
104: strategy.exit("Exit Long", "Long", stop=stopPrice, limit=takeProfitPrice)
112: strategy.entry("Short", strategy.short, qty=qty)
113: strategy.exit("Exit Short", "Short", stop=stopPrice, limit=takeProfitPrice)
116: strategy.close("Long", comment="Fan compression")
119: strategy.close("Short", comment="Fan compression")
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/ribbon_fan.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Yazar zaman dilimi belirtmemiş; 4 saatlik.
