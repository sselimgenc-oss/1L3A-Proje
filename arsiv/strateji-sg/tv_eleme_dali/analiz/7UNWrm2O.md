# RSI-Adaptive T3 + Squeeze Momentum Strategy (`7UNWrm2O`)

- Yazar: PakunFX · Link: https://www.tradingview.com/script/7UNWrm2O-RSI-Adaptive-T3-Squeeze-Momentum-Strategy/
- Kaynak: 69 satır Pine
- Zaman dilimi / pazar: 30dk · kripto (BTC)
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("RSI-Adaptive T3 + Squeeze Momentum Strategy", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=100)
```

## Ne yapıyor
RSI'ye göre uzunluğu 5–50 arasında değişen T3 yön değiştirirken, sıkışma açık (BB, KC dışında) ve LazyBear momentumu aynı işaretliyse long/short, hep piyasada.

## Koddan kanıt (satır: kod)
```
23: len = math.round(minLen + (maxLen - minLen) * rsi_scale)
42: t3 = c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3
46: dev = multKC * ta.stdev(src, length)
57: sqzOff = (lowerBB < lowerKC) and (upperBB > upperKC)
63: longCondition = ta.crossover(t3, t3[1]) and val > 0 and sqzOff
```

## Repaint / lookahead kontrolü
Hepsi geçmiş mum; repaint yok. BB sapmasında Pine hatası: çarpan olarak `multKC` kullanılıyor (aynen taşındı).

## Karar ve gerekçe
Aday.
