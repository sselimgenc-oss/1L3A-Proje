# Stepped trailing strategy example (`jjhUHcje`)

- Yazar: adolgov · Link: https://tr.tradingview.com/script/jjhUHcje-Stepped-trailing-strategy-example/
- Kaynak: 126 satır Pine
- Zaman dilimi / pazar: 1g (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
17: strategy("Stepped trailing strategy example", overlay=true)
```

## Ne yapıyor
TradingView'in örnek stratejisi: SMA(14) ile SMA(28) kesişimi (IHVPG6TS: yön değiştir + $ cinsinden profit/loss; jjhUHcje: yalnız long + kademeli iz süren stop örneği; xAEG4ZJG: yalnız belirli tarih/saat penceresinde işlem). Asıl konu emir mekaniği.

## Koddan kanıt (satır: kod)
```
20: if (crossover(sma(close, 14), sma(close, 28)))
21: strategy.entry("My Long Entry Id", strategy.long)
109: strategy.exit("x", loss = sl, profit = tp3, comment = "sl or tp3")
112: strategy.exit("x", stop = stopLevel, profit = tp3, comment = "breakeven or tp3")
117: strategy.exit("x", stop = stopLevel, trail_points = tp3, trail_offset = tp3-tp2, comment = "stop tp1 or trailing tp3 with offset tp2")
119: strategy.exit("x", stop = stopLevel, profit = tp3, comment = "tp1 or tp3")
```

## Repaint / lookahead kontrolü
Yalnız geçmiş SMA'lar. Repaint yok.

## Karar ve gerekçe
Önceki tur 'eğitim/şablon' diye elemişti; sinyal SMA(14/28) kesişimi gerçek bir kural → ortak sinyal `tv/stratejiler/ma_demo.py` ile test edildi (SL/TP/zaman penceresi örneklerinin kendileri çevrilmedi: sinyal aynı).
