# Technical Summary + Crowd Consensus — Triggon Lite (`U3mcySX9`)

- Yazar: Triggon_ · Link: https://tr.tradingview.com/script/U3mcySX9-Technical-Summay-Crowd-Consensus-Lite-Triggon/
- Kaynak: 517 satır Pine
- Zaman dilimi / pazar: ? · ?
- **Karar: ELE**

## strategy() bildirimi
```
23: strategy("Technical Summary + Crowd Consensus — Triggon Lite", shorttitle="TS+CC-Triggon", overlay=true, pyramiding=0, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.05, slippage=1, calc_on_every_tick=true, max_bars_back=500, max_labels_count=500)
```

## Ne yapıyor
Teknik özet + 'kalabalık görüşü' (crowd consensus) dış verisi.

## Koddan kanıt (satır: kod)
```
23: strategy("Technical Summary + Crowd Consensus — Triggon Lite", shorttitle="TS+CC-Triggon", overlay=true, pyramiding=0, default_qty_type=strategy.perce
36: [_o, _h, _l, _c, _v] = request.security(_sym, _tf, [open, high, low, close, volume], lookahead=barmerge.lookahead_off)
92: i_flip_mode    = input.string("At Least (≥)", "Required Consensus", group=G_SIG, options=["At Least (≥)", "At Most (≤)"], tooltip="At Least: only trad
93: i_flip_thr     = input.int (65,   "Threshold %", group=G_SIG, minval=0, maxval=100, tooltip="e.g. 'At Least' + 40 only trades flips with ≥40% consensu
94: i_show_lbl_pct = input.bool(true, "Show Consensus % on Labels",  group=G_SIG, tooltip="Appends each flip's consensus % to its change-label, and dims l
244: consensus_pct = float(math.max(total_buy, total_sell)) / float(safe_total) * 100.0
253: _tier = consensus_pct < i_thr_neut ? 0 : consensus_pct < i_thr_ext ? 1 : consensus_pct < i_thr_very ? 2 : 3
308: _signalOK = i_flip_mode == "At Least (≥)" ? consensus_pct >= i_flip_thr : consensus_pct <= i_flip_thr   // this bar's flip strong (or weak) enough to 
319: _lblPctTxt = i_show_lbl_pct ? "  " + str.tostring(math.round(consensus_pct)) + "%" : ""
360: strategy.entry("Long", strategy.long)
362: strategy.entry("Short", strategy.short)
443: cons_txt = "Consensus " + str.tostring(math.round(consensus_pct, 1)) + "%  ·  " + tier_desc
513: plot(consensus_pct, "Consensus Strength %", display=display.data_window)
```

## Repaint / lookahead kontrolü
—

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok (kalabalık/duygu verisi).
