# EMA Trend + MTF Stochastic Strategy (`o9dV6uWc`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/o9dV6uWc-Trend-Trigger-EMA-Trend-Filter-MTF-Stochastic-Entry-with-ATR/
- Kaynak: 176 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("EMA Trend + MTF Stochastic Strategy", shorttitle="EMA+MTF Stoch", overlay=true, pyramiding=0, initial_capital=10000, currency=currency.USD, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.02)
```

## Ne yapıyor
EMA Trend + MTF Stochastic (o9dV6uWc): EMA38>EMA62 trendinde, üst zaman dilimi (4s) Stoch K 50'yi yukarı keserken ve yerel K>D → long (aşağı için tersi); stop 1.5 ATR, 1.5R'den sonra ATR izleyen stop, üst TF D çizgisi 80'i aşağı keserse / trend dönerse / 60 mumda çık. (1R'de başa-baş stopu modellenmedi.)

## Koddan kanıt (satır: kod)
```
38: mtfRes = timeframe.period == "1" ? "5" : timeframe.period == "5" ? "15" : timeframe.period == "15" ? "30" :
47: [mtfK, mtfD] = request.security(syminfo.tickerid, mtfRes, f_stoch(), lookahead=barmerge.lookahead_off)
56: stochLong  = ta.crossover(mtfK, 50) and k > 50 and ta.change(k, 1) > 0 and k > d and mtfK > mtfD
57: stochShort = ta.crossunder(mtfD, 50) and k < 50 and ta.change(k, 1) < 0 and k < d and mtfK < mtfD
59: longCondition  = stochLong  and (not requireTrend or trendUp)   and tradeDir != "Short Only"
60: shortCondition = stochShort and (not requireTrend or trendDown) and tradeDir != "Long Only"
103: strategy.entry("Long", strategy.long, qty=qty)
110: strategy.entry("Short", strategy.short, qty=qty)
130: strategy.exit("Long Exit", from_entry="Long", stop=stopLevel)
132: strategy.close("Long", comment="Stoch Fade")
134: strategy.close("Long", comment="Trend Flip")
137: strategy.exit("Short Exit", from_entry="Short", stop=stopLevel)
139: strategy.close("Short", comment="Stoch Fade")
141: strategy.close("Short", comment="Trend Flip")
```

## Repaint / lookahead kontrolü
`request.security(...,lookahead_off)` üst TF stokastik; çeviride son kapanmış mum.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/ema_mtf_stoch.py` olarak çevrilip test edildi.
