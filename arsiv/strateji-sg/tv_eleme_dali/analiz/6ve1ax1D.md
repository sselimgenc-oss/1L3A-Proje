# NQ/MNQ Super Scalper [BACKTEST] (`6ve1ax1D`)

- Yazar: Crispigino · Link: https://www.tradingview.com/script/6ve1ax1D-NQ-MNQ-Super-Scalper-BACKTEST/
- Kaynak: 3292 satır Pine
- Zaman dilimi / pazar: 1–5 dk · NQ/MNQ vadeli
- **Karar: ELE**

## strategy() bildirimi
```
9: strategy("NQ/MNQ Super Scalper [BACKTEST]", overlay=true, initial_capital=15000, default_qty_type=strategy.fixed, default_qty_value=1, pyramiding=20, commission_type=strategy.commission.cash_per_contract, commission_value=0.62, slippage=2, process_orders_on_close=false, calc_on_every_tick=false, currency=currency.USD, margin_long=5, margin_short=5)
```

## Ne yapıyor
NQ/MNQ 'Super Scalper': 6 giriş yolu (ORB, FVG, OTE, BOS/MSS, likidite süpürme...), 20 kademeli pyramiding, 20 desenli akıllı çıkış; 3291 satır.

## Koddan kanıt (satır: kod)
```
9: strategy("NQ/MNQ Super Scalper [BACKTEST]", overlay=true, initial_capital=15000, default_qty_type=strategy.fixed, default_qty_value=1, pyramiding=20, 
120: spyClose  = request.security("SPY", timeframe.period, close, lookahead=barmerge.lookahead_off)
123: [esHigh, esLow] = request.security("ES1!", timeframe.period, [high, low], lookahead=barmerge.lookahead_off)
131: qqqClose  = request.security("QQQ", timeframe.period, close, lookahead=barmerge.lookahead_off)
148: [prevDayH, prevDayL, prevDayC, prev2DayH, prev2DayL] = request.security(syminfo.tickerid, "D", [high[1], low[1], close[1], high[2], low[2]], lookahead
360: float csDojiFactor = time(timeframe.period, "0830-0930", "America/Chicago") != 0 ? 0.08 : time(timeframe.period, "1700-0100", "America/Chicago") != 0 
366: bool inRTH     = time(timeframe.period, "0700-1600", "America/Chicago") != 0
367: bool inAsia    = time(timeframe.period, "1600-0100", "America/Chicago") != 0
368: bool inLondon  = time(timeframe.period, "0100-0400", "America/Chicago") != 0
369: bool inPreMkt  = time(timeframe.period, "0400-0830", "America/Chicago") != 0
371: bool isOpen    = time(timeframe.period, "0830-0930", "America/Chicago") != 0
372: bool isLunch   = time(timeframe.period, "1100-1300", "America/Chicago") != 0
373: bool isLast    = time(timeframe.period, "1500-1600", "America/Chicago") != 0
374: bool isMorning = time(timeframe.period, "0930-1100", "America/Chicago") != 0
```

## Repaint / lookahead kontrolü
10 adet `request.security`, 1 tanesi `lookahead_on` (satır bulundu); pivotlar çok.

## Karar ve gerekçe
KESİN ELEME: gerekli veri yok (NQ 1–5 dk geçmişi) ve scalper (<5 dk, pyramiding=20). Aynı zamanda 3291 satır çok bileşenli ICT sistemi.
