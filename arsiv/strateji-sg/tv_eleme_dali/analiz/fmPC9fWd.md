# OBS Volume Spike Reaction Fade [NQ] (`fmPC9fWd`)

- Yazar: TurkishTraderUsa_ · Link: https://tr.tradingview.com/script/fmPC9fWd-OBS-Volume-Spike-Reaction-Fade-NQ/
- Kaynak: 347 satır Pine
- Zaman dilimi / pazar: 5dk–15dk · vadeli/altın/hisse gün içi
- **Karar: ELE**

## strategy() bildirimi
```
13: strategy("OBS Volume Spike Reaction Fade [NQ]", shorttitle="OBS", overlay=true, initial_capital=100000, default_qty_type=strategy.fixed, default_qty_value=1, pyramiding=1,            // first-fill-wins: only one leg can be live per reaction bar calc_on_every_tick=false, process_orders_on_close=false, commission_type=strategy.commission.cash_per_contract, commission_value=1.50, slippage=1, // v6 defaults margin to 100
```

## Ne yapıyor
NQ hacim şoku tepki (Chicago saati).

## Koddan kanıt (satır: kod)
```
107: ctHour = hour(time, "America/Chicago")
109: ctTotalMin = ctHour * 60 + ctMin
257: strategy.entry("OBS_LONG", strategy.long, limit=entryL25, oca_name="OBS_RXN", oca_type=strategy.oca.cancel, comment="OBS long L25")
264: strategy.entry("OBS_SHORT", strategy.short, limit=entryH25, oca_name="OBS_RXN", oca_type=strategy.oca.cancel, comment="OBS short H25")
```

## Repaint / lookahead kontrolü
Seans/zaman damgasına dayalı gün içi mantık; repaint değil, VERİ sorunu.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — gün içi seans (≤15 dk) geçmişi Yahoo'da yalnız 60 gündür (Aşama-1 kuralı), ≥300 işlem/gün içi eşiği bu veriyle sağlanamaz.
