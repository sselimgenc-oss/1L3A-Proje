# Bollinger Squeeze Breakout + Volume (`N1OCoFkf`)

- Yazar: PinegenAI · Link: https://tr.tradingview.com/script/N1OCoFkf-Bollinger-Squeeze-Breakout-Volume/
- Kaynak: 64 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("Bollinger Squeeze Breakout + Volume", overlay=true, default_qty_type=strategy.percent_of_equity, default_qty_value=10)
```

## Ne yapıyor
Bollinger Squeeze Breakout + Volume (N1OCoFkf): BB genişliği 50 bar ortalamasının %80'inin altındaydı + üst/alt banda kırılım + hacim>ort → giriş; ATR×1.5 stop, ATR×3 hedef.

## Koddan kanıt (satır: kod)
```
41: strategy.entry("Long", strategy.long)
42: strategy.exit("Long Exit", "Long", stop=longSL, limit=longTP)
45: strategy.entry("Short", strategy.short)
46: strategy.exit("Short Exit", "Short", stop=shortSL, limit=shortTP)
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/sikisma_bb.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 1 saatlik, tüm pazarlar.
