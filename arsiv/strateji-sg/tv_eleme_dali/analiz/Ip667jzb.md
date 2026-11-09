# Moving Average Crossover (`Ip667jzb`)

- Yazar: Decam9 · Link: https://tr.tradingview.com/script/Ip667jzb-Moving-Average-Crossover-Strategy/
- Kaynak: 164 satır Pine
- Zaman dilimi / pazar: 1g · hepsi
- **Karar: AL**

## strategy() bildirimi
```
5: strategy(title = "Moving Average Crossover", shorttitle = "MA Crossover Strategy", overlay=true, initial_capital = 100000,default_qty_type = strategy.percent_of_equity, default_qty_value = 10)
```

## Ne yapıyor
MA kesişimi: bkz. modül.

## Koddan kanıt (satır: kod)
```
98: fscrossup = ta.crossover(Fast,Slow)
99: fscrossdw = ta.crossunder(Fast,Slow)
113: (buycond =="Fast-Slow Crossing" and uptrend ? fscrossup:(buycond =="Fast-Trend Crossing" and uptrend ? ftcrossup:(buycond == "Slow-Trend Crossing" and
115: (buycond =="Fast-Slow Crossing"?fscrossup:(buycond=="Fast-Trend Crossing"?ftcrossup:stcrossup))
118: (sellcond =="Fast-Slow Crossing" and downtrend ? fscrossdw:(sellcond =="Fast-Trend Crossing" and downtrend ? ftcrossdw:(sellcond == "Slow-Trend Crossi
120: (sellcond =="Fast-Slow Crossing"?fscrossdw:(buycond=="Fast-Trend Crossing"?ftcrossdw:stcrossdw))
121: crossexitlong = (closebuy =="Fast-Slow Crossing"?fscrossdw:(closebuy=="Fast-Trend Crossing"?ftcrossdw:stcrossdw))
122: crossexitshort = (closeshort =="Fast-Slow Crossing"?fscrossup:(closeshort=="Fast-Trend Crossing"?ftcrossup:stcrossup))
132: golong  = crosslong  and islong  and (filterlong?totalfilter:true)
133: goshort = crossshort and isshort and (filtershort?totalfilter:true)
138: startprice = ta.valuewhen(condition=golong or goshort, source=close, occurrence=0)
139: pm = golong?1:goshort?-1:1/math.sign(strategy.position_size)
149: if golong and islong
150: strategy.entry("long",   strategy.long )
```

## Repaint / lookahead kontrolü
Yalnız geçmiş MA'lar.

## Karar ve gerekçe
Önceki 'kopya/genel' gerekçesi geçersiz; varsayılan ayarlarla çevrildi.
