# Tomukas Wave VWAP DCA Scalper PRO Clean Confirmed (`xJ5iSXIS`)

- Yazar: Tomukasss · Link: https://tr.tradingview.com/script/xJ5iSXIS-Tomukas-Wave-VWAP-DCA-Scalper-PRO/
- Kaynak: 213 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
2: strategy("Tomukas Wave VWAP DCA Scalper PRO Clean Confirmed", overlay=true, pyramiding=4, process_orders_on_close=true, default_qty_type=strategy.percent_of_equity)
```

## Ne yapıyor
Tomukas Wave VWAP DCA: RSI/VWAP sinyalinde taban emir + ortalama düşüren ek emirler (pyramiding>1), ortalama maliyete göre çıkış.

## Koddan kanıt (satır: kod)
```
2: strategy("Tomukas Wave VWAP DCA Scalper PRO Clean Confirmed", overlay=true, pyramiding=4, process_orders_on_close=true, default_qty_type=strategy.perc
8: addStepPerc = input.float(1.0, "DCA Add Every % Against", step=0.1)
128: var int dcaCount = 0
132: dcaCount := 0
137: strategy.entry("L1", strategy.long, qty=0.5)
139: dcaCount := 1
142: strategy.entry("S1", strategy.short, qty=0.5)
144: dcaCount := 1
147: longAdd1  = strategy.position_size > 0 and dcaCount == 1 and close <= firstEntry * (1 - addStepPerc * 1 / 100)
148: longAdd2  = strategy.position_size > 0 and dcaCount == 2 and close <= firstEntry * (1 - addStepPerc * 2 / 100)
149: longAdd3  = strategy.position_size > 0 and dcaCount == 3 and close <= firstEntry * (1 - addStepPerc * 3 / 100)
150: longAdd4  = strategy.position_size > 0 and dcaCount == 4 and close <= firstEntry * (1 - addStepPerc * 4 / 100)
152: shortAdd1 = strategy.position_size < 0 and dcaCount == 1 and close >= firstEntry * (1 + addStepPerc * 1 / 100)
153: shortAdd2 = strategy.position_size < 0 and dcaCount == 2 and close >= firstEntry * (1 + addStepPerc * 2 / 100)
```

## Repaint / lookahead kontrolü
Repaint yok.

## Karar ve gerekçe
KESİN ELEME: DCA / ortalama düşürme (B2).
