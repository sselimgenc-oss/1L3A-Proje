# Stop loss and Take Profit in $$ example (`IHVPG6TS`)

- Yazar: adolgov · Link: https://tr.tradingview.com/script/IHVPG6TS-Stop-loss-and-Take-Profit-in-example/
- Kaynak: 35 satır Pine
- Zaman dilimi / pazar: 1g (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
8: strategy("Stop loss and Take Profit in $$ example", overlay=true)
```

## Ne yapıyor
TradingView'in örnek stratejisi: SMA(14) ile SMA(28) kesişimi (IHVPG6TS: yön değiştir + $ cinsinden profit/loss; jjhUHcje: yalnız long + kademeli iz süren stop örneği; xAEG4ZJG: yalnız belirli tarih/saat penceresinde işlem). Asıl konu emir mekaniği.

## Koddan kanıt (satır: kod)
```
12: longCondition = crossover(sma(close, 14), sma(close, 28))
14: strategy.entry("My Long Entry Id", strategy.long)
18: strategy.entry("My Short Entry Id", strategy.short)
25: strategy.exit("x", profit = p, loss = l)
```

## Repaint / lookahead kontrolü
Yalnız geçmiş SMA'lar. Repaint yok.

## Karar ve gerekçe
Önceki tur 'eğitim/şablon' diye elemişti; sinyal SMA(14/28) kesişimi gerçek bir kural → ortak sinyal `tv/stratejiler/ma_demo.py` ile test edildi (SL/TP/zaman penceresi örneklerinin kendileri çevrilmedi: sinyal aynı).
