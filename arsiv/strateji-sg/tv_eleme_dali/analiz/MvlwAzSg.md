# 3Commas Bot (`MvlwAzSg`)

- Yazar: Bjorgum · Link: https://tr.tradingview.com/script/MvlwAzSg-3Commas-Bot/
- Kaynak: 335 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
8: strategy("3Commas Bot", "Bj Bot", true, precision=3, default_qty_type=strategy.cash, commission_value= 0.05, commission_type=strategy.commission.percent, slippage=1, currency=currency.USD, default_qty_value= 10000, initial_capital= 10000)
```

## Ne yapıyor
3Commas Bot (MvlwAzSg, Bjorgum): EMA21 EMA50'yi yukarı keserse long (aşağı keserse short); stop = 5 mumluk dip/tepe ∓ 1 ATR, hedef 1R (RnR=1); iz süren stop ve ters işlem varsayılanda kapalı; yalnız pozisyon yokken giriş.

## Koddan kanıt (satır: kod)
```
324: strategy.entry  ("Long", strategy.long, when=validLongEntry, comment="Long", alert_message=enterLong)
326: strategy.exit   ("Long Exit", from_entry="Long", stop=trailStop ? trailingStop : tradeStopPrice, limit=tradeTargetPrice, comment="L Exit",   alert_mes
330: strategy.entry  ("Short", strategy.short, when=validShortEntry, comment="Short",   alert_message=enterShort)
332: strategy.exit   ("Short Exit", from_entry="Short", stop=trailStop ? trailingStop : tradeStopPrice, limit=tradeTargetPrice, comment="S Exit",   alert_m
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/bj_bot.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik.
