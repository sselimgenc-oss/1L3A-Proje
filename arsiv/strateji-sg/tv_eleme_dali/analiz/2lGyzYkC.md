# BEST Strategy Template (`2lGyzYkC`)

- Yazar: Daveatt · Link: https://tr.tradingview.com/script/2lGyzYkC-Ultimate-Strategy-Template/
- Kaynak: 389 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
18: strategy(title=SystemName, shorttitle=SystemName,  overlay=true, pyramiding=InitPyramidMax, initial_capital=InitCapital, default_qty_type=strategy.percent_of_equity, default_qty_value=InitPosition, commission_type=strategy.commission.percent, commission_value=InitCommission, calc_on_order_fills=CalcOnorderFills, precision=6, max_lines_count=500, max_labels_count=500)
```

## Ne yapıyor
Strateji şablonu: giriş koşulu `ext_source == 1` yani dışarıdan gelen sinyal; kendi sinyali yok.

## Koddan kanıt (satır: kod)
```
24: ext_source_ = input(close, type=input.source, title="Data source")
109: ext_source = nz(ext_source_)
112: bull = (ext_source == 1)
114: bear = (ext_source == -1)
117: exit_bull = custom_close and (ext_source == 2)
119: exit_bear = custom_close and (ext_source == -2)
324: longCondition = bull
326: strategy.entry("Long", strategy.long, alert_message="{{ticker}} Long Signal - Entry Price: " + tostring(close) + " Timeframe: {{interval}}")
332: strategy.entry("Short", strategy.short, alert_message="{{ticker}} Short Signal - Entry Price: " + tostring(close) + " Timeframe: {{interval}}")
```

## Repaint / lookahead kontrolü
—

## Karar ve gerekçe
KESİN ELEME: altyapı/şablon — sinyal dış kaynak (B2: strategy mantığı yok).
