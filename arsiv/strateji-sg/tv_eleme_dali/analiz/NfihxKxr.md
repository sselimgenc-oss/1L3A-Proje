# High Activity Penny Stock Strategy V6 (`NfihxKxr`)

- Yazar: Pridarasx · Link: https://tr.tradingview.com/script/NfihxKxr-High-Activity-Penny-Stock-Strategy-V6/
- Kaynak: 59 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("High Activity Penny Stock Strategy V6", overlay=true, initial_capital=1000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.1)
```

## Ne yapıyor
High Activity Penny Stock V6 (NfihxKxr): Supertrend(2.0, 10) yön dönüşünde + hacim>1.2×SMA20 + SMA50 filtresi → long/short; %10 hedef, %5 stop; Supertrend tersine dönünce kapat.

## Koddan kanıt (satır: kod)
```
20: bool exitOnFlip      = input.bool(true, "Exit on Trend Flip", group="Risk")
33: bool buySignal  = (stDirection < 0) and (stDirection[1] >= 0) and volOK and trendOK_Buy
34: bool sellSignal = (stDirection > 0) and (stDirection[1] <= 0) and volOK and trendOK_Sell
38: if buySignal
41: if sellSignal
46: strategy.exit("Exit Long", "Long", limit=strategy.position_avg_price * (1 + tpPercent/100), stop=strategy.position_avg_price * (1 - slPercent/100), co
47: strategy.exit("Exit Short", "Short", limit=strategy.position_avg_price * (1 - tpPercent/100), stop=strategy.position_avg_price * (1 + slPercent/100), 
50: if exitOnFlip
58: plotshape(buySignal, title="Buy", text="BUY", location=location.belowbar, color=color.green, style=shape.labelup, textcolor=color.white, size=size.sma
59: plotshape(sellSignal, title="Sell", text="SELL", location=location.abovebar, color=color.red, style=shape.labeldown, textcolor=color.white, size=size.
```

## Repaint / lookahead kontrolü
ta.supertrend yön değişimi; sabit TP/SL. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/penny_st.py` olarak çevrilip test edildi.
