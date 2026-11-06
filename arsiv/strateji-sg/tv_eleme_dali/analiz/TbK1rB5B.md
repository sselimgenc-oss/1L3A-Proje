# Supertrend + Volatility Regime Switch (`TbK1rB5B`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/TbK1rB5B-TrendShift-Supertrend-ADX-Regime-Adaptive-Strategy/
- Kaynak: 150 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Supertrend + Volatility Regime Switch", overlay=true, initial_capital=100000, default_qty_type=strategy.fixed, default_qty_value=1, commission_type=strategy.commission.percent, commission_value=0.05, slippage=1, calc_on_every_tick=false)
```

## Ne yapıyor
Supertrend + Volatility Regime Switch (TbK1rB5B): ADX>25 'trend' (çarpan 1.75), ADX<20 'yatay' (çarpan 4.5, yeni giriş kapalı); dönüşte yön değiştir.

## Koddan kanıt (satır: kod)
```
88: strategy.entry("Long", strategy.long, qty=qty, comment="LONG")
91: strategy.entry("Short", strategy.short, qty=qty, comment="SHORT")
98: strategy.exit("Long Exit", from_entry="Long", stop=stLine, limit=useTP ? longTP : na)
101: strategy.exit("Short Exit", from_entry="Short", stop=stLine, limit=useTP ? shortTP : na)
105: strategy.close_all(comment="Close (Choppy)")
111: strategy.close_all(comment="Max Bars Exit")
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/st_rejim.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 1 saatlik. Trailing/TP varsayılanı kapalı (yalnız dönüşle çıkış).
