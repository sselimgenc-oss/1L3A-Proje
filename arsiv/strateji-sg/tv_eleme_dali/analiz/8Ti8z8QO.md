# MTF Momentum Stack + Stochastic (`8Ti8z8QO`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/8Ti8z8QO-StackLight-MTF-MTF-Momentum-Stack-Stochastic-Confluence/
- Kaynak: 146 satır Pine
- Zaman dilimi / pazar: 15m (çeviri) · kripto
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("MTF Momentum Stack + Stochastic", shorttitle="MTF-MomStack", overlay=false, pyramiding=3, default_qty_type=strategy.percent_of_equity, default_qty_value=10, initial_capital=100000, commission_type=strategy.commission.percent, commission_value=0.05, process_orders_on_close=true)
```

## Ne yapıyor
MTF Momentum Stack + Stochastic (8Ti8z8QO): 15dk/1s/4s RSI skorları (RSI>55 → +1, <45 → −1) aynı yöndeyse (3/−3) ve 15dk Stoch K/D kesişimi (+ 4s Stoch K>D, linreg yumuşatmalı) → giriş; stop 1.5 ATR, hedef 3 ATR; skor ters dönünce çık. (pyramiding=3 ek girişleri tek giriş olarak alındı.) Üst TF değerleri son kapanmış mumdan (lookahead yok).

## Koddan kanıt (satır: kod)
```
52: score1=request.security(syminfo.tickerid,tf1,f_score(),lookahead = barmerge.lookahead_off)
53: score2=request.security(syminfo.tickerid,tf2,f_score(),lookahead = barmerge.lookahead_off)
54: score3=request.security(syminfo.tickerid,tf3,f_score(),lookahead = barmerge.lookahead_off)
56: alignScore = score1+score2+score3
72: longTrigger = ta.crossover(k,d) and k<upLine and mtfK>mtfD
75: longCondition = fullBull and longTrigger and (direction!="Short Only")
89: strategy.entry("Long", strategy.long, qty=qty)
97: strategy.entry("Short", strategy.short, qty=qty)
101: strategy.exit("XL", "Long", stop=longStop, limit = longTarget)
102: strategy.exit("XS", "Short", stop=shortStop, limit = shortTarget)
105: strategy.close("Long", comment="Stack Flip")
108: strategy.close("Short", comment="Stack Flip")
133: table.cell(light, 0, 1, "●", text_color=f_dotColor(score1), text_size=size.large)
134: table.cell(light, 1, 1, "●", text_color=f_dotColor(score2), text_size=size.large)
```

## Repaint / lookahead kontrolü
`request.security(...,lookahead_off)`; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «çoklu zaman dilimi + pyramiding». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/mtf_stack.py` olarak çevrilip test edildi.
