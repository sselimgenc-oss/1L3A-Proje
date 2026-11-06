# Template Trailing Strategy (Backtester) (`n8bgynWl`)

- Yazar: jason5480 · Link: https://tr.tradingview.com/script/n8bgynWl-Template-Trailing-Strategy-Backtester/
- Kaynak: 2247 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
55: strategy(title = 'Template Trailing Strategy (Backtester)', shorttitle = 'TTSv53', pyramiding = 0, backtest_fill_limits_assumption = 1, default_qty_type = strategy.percent_of_equity, default_qty_value = 10, initial_capital = 100000, slippage = 3, commission_type = strategy.commission.percent, commission_value = 0.1, close_entries_rule = 'ANY', margin_long = 0, margin_short = 0, max_lines_count = 500, max_labels_count
```

## Ne yapıyor
Trailing şablon/backtester (2246 satır): giriş türleri ve izleyen emirler için altyapı; sinyal harici.

## Koddan kanıt (satır: kod)
```
55: strategy(title = 'Template Trailing Strategy (Backtester)',
377: atrMethod = input.enum(defval = UpdateMethod.static, title = 'ATR Mtd', tooltip = 'The method to calculate the ATR used for the trailing. Use the ATR 
385: stdevMethod = input.enum(defval = UpdateMethod.static, title = 'StDev Mtd', tooltip = 'The method to calculate the standard deviation used for the tra
504: entryDistMul = input.float(defval = 1.0, title = '  Tgt Dist Mul|Len​', minval = 0.01, step = 0.05, tooltip = 'The distance multiplier or length to de
531: entryTrailBarrier = input.enum(defval = TrailBarrier.front, title = '  Barrier​​', tooltip = 'The price reference that will be used for the entry trai
795: shortStopLossDistMul = input.float(defval = 3.0, title = '​​​​​​​​​​​​​​​​​​​​​​​​​​', minval = 0.05, step = 0.05, tooltip = 'The distance multiplier 
807: stopLossMoveActMode = input.enum(defval = MoveActMode.off, title = 'Move Activation Mode', tooltip = 'Move the stop loss to the entry price (a.k.a bre
818: stopLossTrailActMode = input.enum(defval = TrailActMode.off, title = 'Trail Activation Mode', tooltip = 'Enables the trailing for the stop loss from t
819: stopLossTrailTPActNum = input.int(defval = 1, title = '  Act Take Profit #​​', minval = 1, tooltip = 'The Take Profit number (up to the "𝐓𝐚𝐤𝐞 𝐏𝐫𝐨𝐟𝐢𝐭 𝐓
820: stopLossTrailBarrier = input.enum(defval = TrailBarrier.rear, title = '  Barrier​​​', tooltip = 'The price reference that will be used for the stop lo
822: stopLossStepTrailDistEnabled = input.bool(defval = false, title = 'Trail Step Mode', tooltip = 'When stop loss trailining is activated the distance wi
972: exitDistMul = input.float(defval = 1.0, title = '  Tgt Dist Mul|Len​​', minval = 0.01, step = 0.05, tooltip = 'The distance multiplier to define the e
995: exitTrailBarrier = input.enum(defval = TrailBarrier.front, title = '  Barrier​​​​', tooltip = 'The price reference that will be used for the exit trai
1310: takeProfitTrailEnabled = input.bool(defval = false, title = 'Enable Trail⚠️💹', tooltip = 'Enable or disable the trailing for take profit. WARNING! Thi
```

## Repaint / lookahead kontrolü
—

## Karar ve gerekçe
KESİN ELEME: altyapı/şablon.
