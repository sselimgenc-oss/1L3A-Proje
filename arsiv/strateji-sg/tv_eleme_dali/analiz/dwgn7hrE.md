# RSI Range Compression (Momentum Coil Breakout) (`dwgn7hrE`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/dwgn7hrE-Coil-Breaker-RSI-Range-Compression/
- Kaynak: 104 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("RSI Range Compression (Momentum Coil Breakout)", overlay=false, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, commission_type=strategy.commission.percent, commission_value=0.04, slippage=1)
```

## Ne yapıyor
RSI Range Compression (dwgn7hrE): RSI aralığı son 100 barın alt %20 yüzdeliğine sıkışıp (5 bar bellek) RSI aralığın tepesini/dibini kırarsa EMA50 eğimi yönünde giriş; ATR×2 stop. (Pine'daki long hedefi hatalı: close + stopFiyatı×2 — birebir uygulandı, long'da hedef fiilen ~3×fiyat.)

## Koddan kanıt (satır: kod)
```
68: strategy.entry("Long",strategy.long,qty=qty)
69: strategy.exit("Long Exit", "Long", stop=stopPrice, limit=targetPrice)
74: strategy.entry("Short", strategy.short, qty=qty)
75: strategy.exit("Short Exit", "Short", stop=stopPrice, limit=targetPrice)
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/rsi_coil.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 1 saatlik.
