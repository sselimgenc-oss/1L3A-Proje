# Trend Structure Scale-In (`bajhb6V9`)

- Yazar: Tomukasss · Link: https://tr.tradingview.com/script/bajhb6V9-Trend-Structure-Scale-In/
- Kaynak: 145 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
5: strategy("Trend Structure Scale-In", overlay=true, max_boxes_count=500, max_lines_count=500, max_labels_count=500, initial_capital=100000, default_qty_type=strategy.percent_of_equity)
```

## Ne yapıyor
Trend yönünde engulfing + pivot bölgesi dokunuşunda 5 kademeli ekleme; ek girişler fiyat ORTALAMANIN ALTINDAYKEN (`close < avgPrice`) ve %0.5/0.5/1/2/4 artan boyutla yapılıyor; sabit %2 hedef, stop yok.

## Koddan kanıt (satır: kod)
```
90: pct := 0.005
93: pct := 0.005
96: pct := 0.01
99: pct := 0.02
102: pct := 0.04
110: strategy.entry("B1", strategy.long, qty)
112: else if isLong and numTrades < 5 and close < avgPrice
113: strategy.entry(entryId, strategy.long, qty)
118: strategy.entry("S1", strategy.short, qty)
121: strategy.entry(entryId, strategy.short, qty)
```

## Repaint / lookahead kontrolü
Repaint yok.

## Karar ve gerekçe
KESİN ELEME: ortalama düşürme + katlanan boyut (B2).
