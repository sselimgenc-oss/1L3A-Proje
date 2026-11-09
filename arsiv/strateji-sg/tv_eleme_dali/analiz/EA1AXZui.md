# VWAP Reversal Strategy V1 (`EA1AXZui`)

- Yazar: DerAndi72 · Link: https://tr.tradingview.com/script/EA1AXZui-VWAP-Reversal-Strategy-V1/
- Kaynak: 130 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
5: strategy("VWAP Reversal Strategy V1", overlay=true, default_qty_type=strategy.fixed, default_qty_value=1, initial_capital=10000, currency=currency.USD, margin_long=0, margin_short=0, calc_on_order_fills=true, calc_on_every_tick=true)
```

## Ne yapıyor
Seans VWAP ters dönüş (13:30–20:00 UTC).

## Koddan kanıt (satır: kod)
```
8: useTimeFilter     = input.bool(false, title="Trade only within session filter")
34: sessionStr        = input.session("1330-2000", title="Session (UTC, Symbol Timezone)")
50: sess      = time(timeframe.period, sessionStr)
51: inSession = not useTimeFilter or not na(sess)
105: strategy.entry("Long", strategy.long)
109: strategy.entry("Short", strategy.short)
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
