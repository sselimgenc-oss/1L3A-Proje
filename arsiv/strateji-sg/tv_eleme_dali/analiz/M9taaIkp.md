# Oscillator Evaluator (Analysis tool) (`M9taaIkp`)

- Yazar: mks17 · Link: https://tr.tradingview.com/script/M9taaIkp-Oscillator-Evaluator-Analysis-tool/
- Kaynak: 638 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
7: strategy(title='Oscillator Evaluator (Analysis tool)', shorttitle='Oscillator Evaluator', precision=3, initial_capital=700, pyramiding=500, default_qty_value=500, default_qty_type=strategy.cash, commission_type=strategy.commission.percent, commission_value=0.1, calc_on_every_tick=false, calc_on_order_fills=false, max_bars_back=600, overlay=false)
```

## Ne yapıyor
Osilatör değerlendirme aracı: seçilen osilatörün sinyallerini pyramiding=500 ile arka arkaya işleyen analiz aracı.

## Koddan kanıt (satır: kod)
```
7: strategy(title='Oscillator Evaluator (Analysis tool)', shorttitle='Oscillator Evaluator', precision=3, initial_capital=700, pyramiding=500, default_qt
327: var pyramiding = 0  //To know the current pyramiding
604: strategy.entry("Short", false, oca_name="oca_short", oca_type=strategy.oca.reduce, when=shortentry == 1)
608: strategy.entry("Long", true, oca_name="oca_long", oca_type=strategy.oca.reduce, when=longentry == 1)
```

## Repaint / lookahead kontrolü
—

## Karar ve gerekçe
KESİN ELEME: analiz aracı (pyramiding=500; ayarlanabilir sinyal seçici).
