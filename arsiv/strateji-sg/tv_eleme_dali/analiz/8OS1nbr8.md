# inwCoin Martingale Strategy ( for Bitcoin ) (`8OS1nbr8`)

- Yazar: Real_inwCoin · Link: https://tr.tradingview.com/script/8OS1nbr8-inwCoin-Martingale-Strategy-for-Bitcoin/
- Kaynak: 224 satır Pine
- Zaman dilimi / pazar: ? · kripto
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("inwCoin Martingale Strategy ( for Bitcoin )", shorttitle="INWCOIN_MARTINGALE_BTC", overlay=true, pyramiding=100, initial_capital = 20000, commission_type = strategy.commission.percent, commission_value = 0.0,slippage=0)
```

## Ne yapıyor
Bitcoin martingale botu: zarar serisinden sonra üstel pozisyon artışı, pyramiding=100.

## Koddan kanıt (satır: kod)
```
2: strategy("inwCoin Martingale Strategy ( for Bitcoin )", shorttitle="INWCOIN_MARTINGALE_BTC", overlay=true, pyramiding=100, initial_capital = 20000, co
36: martingale_percent = input(10.0, type=input.float, title="Start Martingale if price drop with this Percent")
37: martingale_mult = input(2.0, type=input.float, title= "Martingale Multiplier")
165: BuyMore = pricePercent <= ( martingale_percent * -1 )
170: var countMartingale = 0.0    //martingale count
174: var unit_size_martingale = 0.0
183: unit_size_martingale := startUnitSize *  pow(martingale_mult,(countMartingale))
200: if (Buy and in_date_range and ( trade_side == "Both" or trade_side == "Long Only" ) and countMartingale == 0.0 and strategy.equity >= 0 )
201: strategy.entry("Long", strategy.long, qty=unit_size,when=strategy.position_size <= 0 )
202: countMartingale := 1
205: if (BuyMore and countMartingale > 0)
206: strategy.entry("Long", strategy.long, qty=unit_size_martingale,when=strategy.position_size > 0 and strategy.equity >= 0 )
207: countMartingale := countMartingale + 1
213: countMartingale := 0
```

## Repaint / lookahead kontrolü
Repaint yok.

## Karar ve gerekçe
KESİN ELEME: martingale (B2).
