# Ultimate Ichimoku Cloud Strategy (`boHD0HzE`)

- Yazar: antondmt · Link: https://tr.tradingview.com/script/boHD0HzE-Ultimate-Ichimoku-Cloud-Strategy/
- Kaynak: 130 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("Ultimate Ichimoku Cloud Strategy", "UIC Strategy", true, default_qty_type = strategy.percent_of_equity, default_qty_value = 100, process_orders_on_close = true)
```

## Ne yapıyor
Ultimate Ichimoku Cloud (boHD0HzE): tenkan/kijun kesişimi + pozitif bulut + fiyat bulut üstünde + chikou + fiyat>tenkan → long (tersi short); kijun/tenkan ters kesişiminde çıkış. process_orders_on_close=true: emir sinyal mumunun kapanışında dolar.

## Koddan kanıt (satır: kod)
```
103: strategy.entry("Long", strategy.long)
105: strategy.close("Long")
107: strategy.exit("TP/SL", "Long", stop = strategy.position_avg_price * (1 - i_SL / 100), limit = strategy.position_avg_price * (1 + i_TP / 100))
111: strategy.entry("Short", strategy.short)
113: strategy.close("Short")
115: strategy.exit("TP/SL", "Short", stop = strategy.position_avg_price * (1 + i_SL / 100), limit = strategy.position_avg_price * (1 - i_TP / 100))
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/ichimoku.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük (Ichimoku klasik).
