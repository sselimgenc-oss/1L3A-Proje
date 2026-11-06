# How To Set Time Ranges (`xAEG4ZJG`)

- Yazar: allanster · Link: https://tr.tradingview.com/script/xAEG4ZJG-How-To-Set-Backtest-Time-Ranges/
- Kaynak: 56 satır Pine
- Zaman dilimi / pazar: 1g (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy(title = "How To Set Time Ranges", shorttitle = "Timed", overlay = true, precision = 8, max_bars_back = 200, pyramiding = 0, initial_capital = 100000,  currency = currency.NONE, default_qty_type = strategy.cash, default_qty_value = 100000, commission_type = "percent", commission_value = 0.27)
```

## Ne yapıyor
TradingView'in örnek stratejisi: SMA(14) ile SMA(28) kesişimi (IHVPG6TS: yön değiştir + $ cinsinden profit/loss; jjhUHcje: yalnız long + kademeli iz süren stop örneği; xAEG4ZJG: yalnız belirli tarih/saat penceresinde işlem). Asıl konu emir mekaniği.

## Koddan kanıt (satır: kod)
```
47: strategy.entry("L", strategy.long, when = isDate() and isTime(entryTime) and enterLong)  // enter "within window of dates and time" AND crossover
```

## Repaint / lookahead kontrolü
Yalnız geçmiş SMA'lar. Repaint yok.

## Karar ve gerekçe
Önceki tur 'eğitim/şablon' diye elemişti; sinyal SMA(14/28) kesişimi gerçek bir kural → ortak sinyal `tv/stratejiler/ma_demo.py` ile test edildi (SL/TP/zaman penceresi örneklerinin kendileri çevrilmedi: sinyal aynı).
