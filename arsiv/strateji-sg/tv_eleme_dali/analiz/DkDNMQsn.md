# Cluster Breakout Strategy v8 (Partial+BE) (`DkDNMQsn`)

- Yazar: ruchiragrawal · Link: https://tr.tradingview.com/script/DkDNMQsn-Cluster-Breakout-Strategy-v6-Robust/
- Kaynak: 290 satır Pine
- Zaman dilimi / pazar: gün içi (1–15 dk) · NSE
- **Karar: ELE**

## strategy() bildirimi
```
38: strategy("Cluster Breakout Strategy v8 (Partial+BE)", overlay=true, initial_capital=100000, default_qty_type=strategy.fixed, default_qty_value=2, process_orders_on_close=true, slippage=2, commission_type=strategy.commission.percent, commission_value=0.02, max_lines_count=100, max_labels_count=300)
```

## Ne yapıyor
Kümelenme (10 mumluk dar aralık ≤2 ATR, oynaklık daralıyor) kırılımı + güçlü kapanış + hacim 1.3×; seans 09:15–15:30 Asya/Kalküta, seans sonu zorunlu kapanış; %0.5 stop, %1 ilk hedefte yarı kapanış + başa-baş taşıma, ikinci hedef 2×; en çok 3 giriş/gün, 20 mum azami tutma.

## Koddan kanıt (satır: kod)
```
63: sess = input.session("0915-1530", "Session (HHMM-HHMM)", group="Session", tooltip="NSE 0915-1530 | MCX 0900-2330 | Forex 0000-2359")
64: tz   = input.string("Asia/Kolkata", "Timezone", group="Session")
65: exitEod = input.bool(true, "Close open trade at session end", group="Session")
66: maxTradesPerDay = input.int(3, "Max entries per day", group="Session")
148: canTrade   = inSession and tradesToday < maxTradesPerDay and not inCooldown
168: strategy.entry("Long", strategy.long, qty=orderSize)
185: strategy.entry("Short", strategy.short, qty=orderSize)
248: if exitEod and not sessionNow and strategy.position_size != 0
```

## Repaint / lookahead kontrolü
Repaint yok (kapanışa dayalı).

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok — NSE seans penceresi (09:15–15:30 IST) ve seans sonu kapanışı ≤15 dk veri ister; Yahoo gün içi 60 gün (Aşama-1 kuralı). `maxTradesPerDay`, `exitEod` ile gün içi sistem.
