# XAU Clear EMA ATR Strategy TP SL Voice V6 (`zudiHFjK`)

- Yazar: ionplesu88 · Link: https://tr.tradingview.com/script/zudiHFjK-XAU-Clear-EMA-ATR-Strategy-TP-SL-Voice-V6/
- Kaynak: 134 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("XAU Clear EMA ATR Strategy TP SL Voice V6", overlay=true, max_labels_count=100, process_orders_on_close=true)
```

## Ne yapıyor
XAU 15 dk EMA-ATR (sesli uyarı).

## Koddan kanıt (satır: kod)
```
66: strategy.entry("BUY", strategy.long)
76: alert("MALE VOICE BUY XAUUSD. Entry " + str.tostring(entry, format.mintick) + ". Stop loss " + str.tostring(sl, format.mintick), alert.freq_once_per_b
93: strategy.entry("SELL", strategy.short)
103: alert("MALE VOICE SELL XAUUSD. Entry " + str.tostring(entry, format.mintick) + ". Stop loss " + str.tostring(sl, format.mintick), alert.freq_once_per_
133: alertcondition(buySignal, title="VOICE BUY", message="MALE VOICE BUY XAUUSD")
134: alertcondition(sellSignal, title="VOICE SELL", message="MALE VOICE SELL XAUUSD")
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
