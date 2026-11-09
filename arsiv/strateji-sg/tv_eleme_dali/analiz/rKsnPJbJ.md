# Fib Confluence Scanner (`rKsnPJbJ`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/rKsnPJbJ-Fibonacci-Cloud-Multi-Timeframe-Fibonacci-Scanner/
- Kaynak: 112 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
4: strategy("Fib Confluence Scanner", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.05)
```

## Ne yapıyor
Fib Confluence Scanner (rKsnPJbJ): 20/50/100 mumluk aralıkların 15 fib seviyesinden en az biri kapanışa %0.5 yakınsa + EMA50 trend süzgeci → trend yönünde giriş; %1.5 stop, 2R hedef. (Pratikte seviyeler fiyatı sık kapsadığından filtre hafif.)

## Koddan kanıt (satır: kod)
```
36: fibLevels(len) =>
47: [a236, a382, a500, a618, a786] = fibLevels(lenA)
48: [b236, b382, b500, b618, b786] = fibLevels(lenB)
49: [c236, c382, c500, c618, c786] = fibLevels(lenC)
52: isNear(level) =>
55: confluenceCount = (isNear(a236) ? 1 : 0) + (isNear(a382) ? 1 : 0) + (isNear(a500) ? 1 : 0) + (isNear(a618) ? 1 : 0) + (isNear(a786) ? 1 : 0) +
56: (isNear(b236) ? 1 : 0) + (isNear(b382) ? 1 : 0) + (isNear(b500) ? 1 : 0) + (isNear(b618) ? 1 : 0) + (isNear(b786) ? 1 : 0) +
57: (isNear(c236) ? 1 : 0) + (isNear(c382) ? 1 : 0) + (isNear(c500) ? 1 : 0) + (isNear(c618) ? 1 : 0) + (isNear(c786) ? 1 : 0)
75: longCondition  = confluence and (not useTrendFilter or trendUp) and rsiLongOK  and longAllowed  and positionFree
76: shortCondition = confluence and (not useTrendFilter or trendDn) and rsiShortOK and shortAllowed and positionFree
93: plotshape(showMarks and longCondition,  "Long",  shape.triangleup,   location.belowbar, colUp,   size=size.small)
94: plotshape(showMarks and shortCondition, "Short", shape.triangledown, location.abovebar, colDown, size=size.small)
97: if longCondition
98: strategy.entry("Long", strategy.long, alert_message=msg_open_long)
```

## Repaint / lookahead kontrolü
Yalnız geçmiş aralıklar. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/fib_conf.py` olarak çevrilip test edildi.
