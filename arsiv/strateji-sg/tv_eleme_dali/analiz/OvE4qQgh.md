# Liquidity Sweep + Delta Absorption [PineGen AI] (`OvE4qQgh`)

- Yazar: PinegenAI · Link: https://www.tradingview.com/script/OvE4qQgh-Liquidity-Sweep-Delta-Absorption-PineGen-AI/
- Kaynak: 232 satır Pine
- Zaman dilimi / pazar: 15 dk–1 s (deltaTF alt dilim) · kripto/vadeli
- **Karar: ELE**

## strategy() bildirimi
```
34: strategy(title="Liquidity Sweep + Delta Absorption [PineGen AI]", shorttitle="LSDA [PineGen AI]", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=10, commission_type=strategy.commission.percent, commission_value=0.02, slippage=2, pyramiding=0, calc_on_every_tick=false)
```

## Ne yapıyor
Likidite süpürme (swing tepe/dibinin iğne ile taranması) + 'delta emilimi' (alt zaman dilimi mumlarından hesaplanan alıcı/satıcı hacim farkı) → ters yönde giriş, swing tabanlı stop, R hedef.

## Koddan kanıt (satır: kod)
```
90: ph = ta.pivothigh(high, swingLeft, swingRight)
91: pl = ta.pivotlow(low, swingLeft, swingRight)
104: [ltOpen, ltClose, ltVolume] = request.security_lower_tf(syminfo.tickerid, deltaTF, [open, close, volume])
204: strategy.entry("Long", strategy.long)
205: strategy.exit("Long Exit", from_entry="Long", stop=longStop, limit=longTarget)
213: strategy.entry("Short", strategy.short)
214: strategy.exit("Short Exit", from_entry="Short", stop=shortStop, limit=shortTarget)
```

## Repaint / lookahead kontrolü
Pivotlar `swingLeft/swingRight` ile onaylı. Delta `request.security_lower_tf` ile alt TF mumlarından.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — delta için alt zaman dilimi (tick/dakika) hacim ayrımı gerekir; yalnız OHLCV'den doğru üretilemez (emir akışı verisi).
