# Liquidity Sweep Reversal Strategy (`GoeqO1ev`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/GoeqO1ev-Sweep-Reverse-Liquidity-Sweep-Reversal-Strategy/
- Kaynak: 349 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,emtia
- **Karar: AL**

## strategy() bildirimi
```
3: strategy("Liquidity Sweep Reversal Strategy", "Sweep Reversal Strategy", overlay = true, max_boxes_count = 600, max_lines_count = 500, max_labels_count = 300, default_qty_type = strategy.percent_of_equity, default_qty_value = 10, initial_capital = 10000, currency = currency.USD, commission_type = strategy.commission.percent, commission_value = 0.04, slippage = 1)
```

## Ne yapıyor
Liquidity Sweep Reversal (GoeqO1ev): 7/7 onaylı swing tepe/dipleri 'likidite seviyesi' olur (≥0.25 ATR aralıklı, 150 mum ömürlü); mum seviyeyi iğneyle aşıp içeride kapanırsa (hacim>1.3×SMA20, iğne/gövde≥1.5) süpürme sayılır; ertesi mum onay (orta noktanın ötesinde kapanış) → ters yönde giriş; stop iğne∓1.2 ATR, hedef 1.5R, %50'de başa-baş. Seans 12:00–16:00 UTC. Pivot onayı 7 mum gecikmeli (repaint yok).

## Koddan kanıt (satır: kod)
```
60: pivH = ta.pivothigh(high, pivotLen, pivotLen)
61: pivL = ta.pivotlow(low, pivotLen, pivotLen)
129: bool sweepHighSignal = false
147: sweepHighSignal := true
160: bool sweepLowSignal = false
178: sweepLowSignal := true
217: if sweepLowSignal
221: if sweepHighSignal
227: if sweepLowSignal and allowLongs and sessionOK
230: if sweepHighSignal and allowShorts and sessionOK
239: strategy.entry(isLong ? "Long" : "Short", isLong ? strategy.long : strategy.short)
240: strategy.exit(isLong ? "Long Exit" : "Short Exit", isLong ? "Long" : "Short", stop = sl, limit = tp)
273: strategy.exit(isLongPos ? "Long Exit" : "Short Exit", isLongPos ? "Long" : "Short",
```

## Repaint / lookahead kontrolü
Pivotlar `pivotLen` gecikmeli, seviye onaydan sonra kayıtlı; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «likidite süpürme pivot girişi (repaint riski); temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/sweep_rev.py` olarak çevrilip test edildi.
