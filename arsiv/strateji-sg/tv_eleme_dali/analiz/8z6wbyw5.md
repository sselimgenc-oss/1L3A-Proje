# DIY Custom Strategy Builder  [ZP] - v1 (Strategy) (`8z6wbyw5`)

- Yazar: maris_schmidlin · Link: https://www.tradingview.com/script/8z6wbyw5/
- Kaynak: 4619 satır Pine
- Zaman dilimi / pazar: herhangi · herhangi
- **Karar: ELE**

## strategy() bildirimi
```
5: strategy(title='DIY Custom Strategy Builder  [ZP] - v1 (Strategy)', shorttitle="DIY Strategy [ZP]", overlay=true, max_bars_back=5000, max_lines_count=500, max_boxes_count=500, max_labels_count=500, pyramiding=0, default_qty_type=strategy.percent_of_equity, default_qty_value=10, initial_capital=10000, commission_type=strategy.commission.percent, commission_value=0.04, process_orders_on_close=true, calc_on_every_tick=f
```

## Ne yapıyor
'DIY Custom Strategy Builder': kullanıcının göstergeleri seçip kendi giriş kurallarını kurduğu şablon (4618 satır). Kendi başına bir strateji mantığı yok; varsayılanlar boş.

## Koddan kanıt (satır: kod)
```
113: signalexpiry = input.int(defval=3,  title='Signal Expiry Candle Count',group=setup_group, inline='expiry',tooltip="Number of candles to wait for all i
128: strat_group = "████████ Strategy Settings ████████"
129: rr_ratio = input.float(defval=1.5, title='Take Profit RR Ratio', minval=1.0, maxval=20.0, step=0.5, group=strat_group, tooltip="Risk:Reward Verhältnis
130: sl_swing_len = input.int(defval=5, title='SL Swing Lookback', minval=2, maxval=50, group=strat_group, tooltip="Anzahl Bars für die Swing-Erkennung zur
131: sl_timeframe = input.timeframe(defval="", title='SL Swing Timeframe', group=strat_group, tooltip="Timeframe fuer Swing-Erkennung. Leer = Chart-Timefra
132: use_atr_fallback = input.bool(defval=true, title='ATR Fallback wenn kein Swing', group=strat_group, tooltip="Wenn kein gültiger Swing gefunden wird, v
133: atr_mult_sl = input.float(defval=1.5, title='ATR Multiplier für Fallback SL', minval=0.5, maxval=5.0, step=0.5, group=strat_group, tooltip="ATR-Multip
839: [_securityPivots, _securityPivotCounter] = request.security(syminfo.tickerid, pivotTimeframe, [securityPivotPointsArray, pivotTimeframeChangeCounter(s
1398: for i = 0 to signalexpiry - 1
1798: "Earnings"  => not na(request.earnings(syminfo.tickerid, earnings.actual, barmerge.gaps_on, barmerge.lookahead_on, ignore_invalid_symbol=true))
1799: "Dividends" => not na(request.dividends(syminfo.tickerid, dividends.gross, barmerge.gaps_on, barmerge.lookahead_on, ignore_invalid_symbol=true))
1800: "Splits"    => not na(request.splits(syminfo.tickerid, splits.denominator, barmerge.gaps_on, barmerge.lookahead_on, ignore_invalid_symbol=true))
2975: pvsra_imnt(sresolution,sseries) => request.security(override_imnt ? pvsra_sym : syminfo.tickerid ,sresolution,sseries, barmerge.gaps_off,barmerge.look
3466: request.security(overrideSymbolX ? pvsraSymbolX : tickerIdX, '', volume, barmerge.gaps_off, barmerge.lookahead_off)
```

## Repaint / lookahead kontrolü
5 adet `lookahead_on`, 20 `request.security` (kullanıcı seçimine bağlı).

## Karar ve gerekçe
KESİN ELEME: strateji değil, altyapı/şablon — kodun varsayılan ayarları anlamlı bir sinyal üretmez (yazarın kendi test sonucu da yok).
