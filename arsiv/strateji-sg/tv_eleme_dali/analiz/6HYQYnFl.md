# [M4] ORB Real Version – MNQ (`6HYQYnFl`)

- Yazar: NoSlJr · Link: https://www.tradingview.com/script/6HYQYnFl-15-Min-ORB-Real-Version-MNQ/
- Kaynak: 338 satır Pine
- Zaman dilimi / pazar: 1 dk · MNQ vadeli
- **Karar: ELE**

## strategy() bildirimi
```
13: strategy(title="[M4] ORB Real Version – MNQ", shorttitle="ORB-Real", overlay=true, initial_capital=25000, default_qty_type=strategy.fixed, default_qty_value=1, commission_type=strategy.commission.cash_per_contract, commission_value=0.62, slippage=1)
```

## Ne yapıyor
MNQ (mikro Nasdaq vadeli) 1 dk ORB: ilk 30 dk aralığı, hacim patlaması + aralık dışı kapanış filtresi, iki kademeli kâr alma (%50 TP1, kalan TP2), gün sonu kapanış ve günlük 500 $ limit.

## Koddan kanıt (satır: kod)
```
69: etHour   = hour(time,   "America/New_York")
71: etTime   = etHour * 60 + etMin
202: strategy.entry("Long-BO", strategy.long, qty=contracts)
211: strategy.entry("Short-BO", strategy.short, qty=contracts)
220: strategy.entry("Long-RT", strategy.long, qty=contracts)
228: strategy.entry("Short-RT", strategy.short, qty=contracts)
239: strategy.exit("TP1-L", "Long-BO",  qty_percent=50, limit=entryTP1, stop=entryStop)
240: strategy.exit("TP1-LR","Long-RT",  qty_percent=50, limit=entryTP1, stop=entryStop)
244: strategy.exit("TP1-S", "Short-BO", qty_percent=50, limit=entryTP1, stop=entryStop)
245: strategy.exit("TP1-SR","Short-RT", qty_percent=50, limit=entryTP1, stop=entryStop)
249: strategy.exit("TP2-L", "Long-BO",  limit=entryTP2, stop=entryStop)
250: strategy.exit("TP2-LR","Long-RT",  limit=entryTP2, stop=entryStop)
253: strategy.exit("TP2-S", "Short-BO", limit=entryTP2, stop=entryStop)
254: strategy.exit("TP2-SR","Short-RT", limit=entryTP2, stop=entryStop)
```

## Repaint / lookahead kontrolü
Repaint belirtisi yok; kısmi çıkışlar `strategy.exit(qty_percent=50)`.

## Karar ve gerekçe
KESİN ELEME: 1 dk ölçeği (<1 dk-altı olmasa da 1 dk scalping) ve MNQ 1 dk geçmişi yok (görev kuralı: 1 dk altı/scalping, yeterli geçmiş yok).
