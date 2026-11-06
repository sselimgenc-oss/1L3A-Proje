# How to use Leverage and Margin in PineScript (`9Iwinz7I`)

- Yazar: Peter_O · Link: https://tr.tradingview.com/script/9Iwinz7I-How-to-use-Leverage-and-Margin-in-PineScript/
- Kaynak: 29 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
5: strategy(title="How to use Leverage and Margin in PineScript", overlay=false, pyramiding=100, default_qty_type = strategy.percent_of_equity, default_qty_value=3000, margin_long=1./30*50, margin_short=1./30*50)
```

## Ne yapıyor
Kaldıraç/marjin örneği: Stoch kesişimi + sabit 100 tick TP, pyramiding=100 (her sinyalde ekleme), stop yok.

## Koddan kanıt (satır: kod)
```
5: strategy(title="How to use Leverage and Margin in PineScript", overlay=false, pyramiding=100,
23: TP=input(100, title="Take Profit (in ticks)")
25: strategy.entry("Long", strategy.long, when=GoLong)
26: strategy.exit("tp_long", from_entry="Long", profit=TP)
27: strategy.entry("Short", strategy.short, when=GoShort)
28: strategy.exit("tp_short", from_entry="Short", profit=TP)
```

## Repaint / lookahead kontrolü
Repaint yok.

## Karar ve gerekçe
KESİN ELEME: eğitim örneği; kâr hedefi sembolün tick'ine bağlı mutlak 100 tick ve sınırsız ekleme (pyramiding=100) — stratejik kural yok.
