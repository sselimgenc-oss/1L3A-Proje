# Vix FIX / StochRSI Strategy (`TDxSLJRA`)

- Yazar: timj · Link: https://tr.tradingview.com/script/TDxSLJRA-Vix-FIX-StochRSI-Strategy/
- Kaynak: 85 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Vix FIX / StochRSI Strategy", pyramiding=9, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=3, overlay=false)
```

## Ne yapıyor
Vix FIX / StochRSI (TDxSLJRA, timj): Williams VIX Fix filtreli dip dönüşü → long; stokastik aşırı alım kesişiminde çıkış. Yalnız long. (Pine'daki pyramiding=9 tek pozisyona indirildi.)

## Koddan kanıt (satır: kod)
```
79: strategy.entry("Long", strategy.long)
82: strategy.close("Long")
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/vixfix.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, yalnız long (dip alma).
