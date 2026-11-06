# Сalculation a position size based on risk (`hoCPm5UY`)

- Yazar: adolgov · Link: https://tr.tradingview.com/script/hoCPm5UY-%D0%A1alculation-a-position-size-based-on-risk/
- Kaynak: 43 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
10: strategy("Сalculation a position size based on risk", overlay=true, margin_long=10, margin_short=10, currency = currency.NONE)
```

## Ne yapıyor
Pozisyon boyutu hesaplama örneği: `bar_index % 333` ve `% 444` anlarında rastgele long/short girişi.

## Koddan kanıt (satır: kod)
```
34: longCondition = bar_index % 333 == 0
36: strategy.entry("My Long Entry Id", strategy.long, qty = qty)
37: shortCondition = bar_index % 444 == 0
39: strategy.entry("My Short Entry Id", strategy.short, qty = qty)
```

## Repaint / lookahead kontrolü
Sinyal yok.

## Karar ve gerekçe
KESİN ELEME: gerçek bir giriş kuralı yok (bar sayacı modülo) — eğitim örneği.
