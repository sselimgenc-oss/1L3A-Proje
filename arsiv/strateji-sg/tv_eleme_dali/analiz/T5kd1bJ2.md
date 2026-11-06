# RSI-Gauss-Velocity-Strategy-WiP (`T5kd1bJ2`)

- Yazar: RS374 · Link: https://www.tradingview.com/script/T5kd1bJ2-RSI-Gauss-Velocity-Strategy-WiP/
- Kaynak: 71 satır Pine
- Zaman dilimi / pazar: 1g (2014'ten) · kripto/ABD
- **Karar: AL**

## strategy() bildirimi
```
2: strategy(title="RSI-Gauss-Velocity-Strategy-WiP", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.1, slippage=3)
```

## Ne yapıyor
4 kutuplu Gauss filtresi yükseliyor + kapanış > filtre+1.414×filtrelenmiş TR + Stoch(RSI) K>D → long; çıkış: kapanış üst bandın altına geçer ya da eğim tükenmesi (kârdayken).

## Koddan kanıt (satır: kod)
```
20: f_filt9x(_a, _s, _i) =>
31: filtn = f_filt9x(alpha, hlc3, N)
32: filttr = f_filt9x(alpha, ta.tr(true), N)
40: slopeExhaustion = filtSlope < (slopeMean - slopeStd)
47: longCondition = gaussianGreen and (close > hband) and stochSignal and timeFilter
51: exitCondition = ta.crossunder(close, hband) or (slopeExhaustion and inProfit and (close < hband or close < hband[1]))
```

## Repaint / lookahead kontrolü
Gauss filtresi yalnız geçmiş mum (f[1..4]); security/pivot yok.

## Karar ve gerekçe
Aday. Pine filtresi sıfırdan başlıyor (nz) — birebir aynı başlangıç.
