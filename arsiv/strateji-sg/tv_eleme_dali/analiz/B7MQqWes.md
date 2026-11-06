# EWO,RSI advanced Signals Strategy - Exhaustion Filter[Pridarasx] (`B7MQqWes`)

- Yazar: Pridarasx · Link: https://tr.tradingview.com/script/B7MQqWes-EWO-RSI-advanced-Signals-Strategy-Exhaustion-Filter/
- Kaynak: 124 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy("EWO,RSI advanced Signals Strategy - Exhaustion Filter[Pridarasx]", overlay=true, initial_capital=10000, currency=currency.USD)
```

## Ne yapıyor
EWO + RSI Signals (B7MQqWes): RSI 40'ı yukarı keser + MFI>30 + EWO yükselir + hacim + (10 bar zirve kırılımı veya yakın zamanda RSI<30) → long; RSI 60'ı aşağı keser + MFI<70 + EWO düşer → short. Ters sinyalde yön değiştirir.

## Koddan kanıt (satır: kod)
```
85: strategy.entry("Long", strategy.long, alert_message="EWO/RSI Strategy: BUY NOW - Long Entry Triggered. Price: " + str.tostring(close) + " | RSI: " + s
88: strategy.entry("Short", strategy.short, alert_message="EWO/RSI Strategy: SELL NOW - Short Entry Triggered. Price: " + str.tostring(close) + " | RSI: "
112: alert("EWO/RSI Strategy: POSITION EXITED/REVERSED. Price: " + str.tostring(close) + " | P&L: " + str.tostring(strategy.closedtrades.profit(strategy.cl
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/ewo_rsi.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik.
