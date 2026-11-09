# Supertrend RG with TP (`DG9ePZuk`)

- Yazar: rgomescrypto · Link: https://tr.tradingview.com/script/DG9ePZuk-Supertrend-adapted-to-strategy/
- Kaynak: 232 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
11: strategy("Supertrend RG with TP", overlay = true,process_orders_on_close=true,commission_type=strategy.commission.percent,commission_value=InitCommission, currency=currency.USD,initial_capital=InitCapital,default_qty_type=strategy.cash, default_qty_value=InitPosition, calc_on_order_fills=CalcOnorderFills, calc_on_every_tick=CalcOnTick,pyramiding=InitPyramidMax)
```

## Ne yapıyor
Supertrend RG with TP (DG9ePZuk): KivancOzbilgic SuperTrend(10, 3, hl2) yön değişimini bir mum gecikmeyle (signal[1]) uygular (long/short); %8 stop, +%2 tetikten sonra %2.5 izleyen mum-dibi stopu (izleyen stop yaklaşık: tepeden %2.5).

## Koddan kanıt (satır: kod)
```
222: close_order = (close_long[1] or close_short[1] or close_TP_long or close_TP_short)
228: strategy.entry(TradeId + " Long", true, when=buySignal[1] and time_cond)
229: strategy.entry(TradeId + " Short", false, when=sellSignal[1] and time_cond)
230: strategy.close_all(when=close_order and time_cond)
```

## Repaint / lookahead kontrolü
Yalnız geçmiş; sinyal [1] gecikmeli.

## Karar ve gerekçe
Önceki tur gerekçesi: «kopya (Supertrend; tutulanlar var)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/st_rg.py` olarak çevrilip test edildi. SL/izleyen stop + 1 mum gecikmeli giriş içeren farklı strateji.
