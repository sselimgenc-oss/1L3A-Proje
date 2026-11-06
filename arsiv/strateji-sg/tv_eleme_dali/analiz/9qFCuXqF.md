# [3Commas] Turtle Strategy (`9qFCuXqF`)

- Yazar: 3Commas · Link: https://www.tradingview.com/script/9qFCuXqF-3Commas-Turtle-Strategy/
- Kaynak: 342 satır Pine
- Zaman dilimi / pazar: 4s · kripto (ETH)
- **Karar: AL**

## strategy() bildirimi
```
6: strategy(title                        = "[3Commas] Turtle Strategy" , overlay                      = true , pyramiding                   = 0 , calc_on_order_fills          = false , calc_on_every_tick           = true , default_qty_type             = strategy.percent_of_equity , default_qty_value            = 1 , initial_capital              = 10000 , slippage                     = 5 , commission_type              = 
```

## Ne yapıyor
20 mumluk Donchian kırılımı (+20 mum ofsetli kanal üstü) long/short; 10 mumluk dip/tepeyle sıkılaşan izleyen çıkış; TP kapalı.

## Koddan kanıt (satır: kod)
```
10: , calc_on_every_tick           = true
26: var menu_buy       = "🟢 Long"
27: var menu_sel       = "🔴 Short"
53: tp_buy = _tp_use?close * (1 + _tp_percent / 100) : na
54: tp_sel = _tp_use?close * (1 - _tp_percent / 100) : na
71: var inbuy  = false
72: var insel  = false
75: buy  = buy_fast and close>upper_slow[1] and not inbuy
76: sel  = sel_fast and close<lower_slow[1] and not insel
91: var exit_buy_level = float(na)
92: var exit_sel_level = float(na)
103: exit_buy_level:= math.max(nz(exit_buy_level,10e-10), lower_exit)
104: sl:= exit_buy_level
108: exit_sel_level:= math.min(nz(exit_sel_level,10e+10), upper_exit)
```

## Repaint / lookahead kontrolü
`calc_on_every_tick=true` yalnız canlı veri etkiler; tarihçede sinyaller `barstate.isconfirmed`. Repaint yok. 3Commas DCA bot alanları yalnız alarm metni.

## Karar ve gerekçe
Aday (kesin eleme nedeni yok: DCA botuna sinyal gönderen alanlar stratejinin mantığında değil).
