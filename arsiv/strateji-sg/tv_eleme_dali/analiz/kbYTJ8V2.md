# Aurora KAMA Trend (`kbYTJ8V2`)

- Yazar: blitz_locked · Link: https://tr.tradingview.com/script/kbYTJ8V2-Aurora-KAMA-KAMA-Adaptive-Trend-Strategy/
- Kaynak: 179 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy( "Aurora KAMA Trend", shorttitle          = "Aurora-KAMA", overlay              = true, initial_capital      = 10000, default_qty_type     = strategy.percent_of_equity, default_qty_value    = 25, commission_type      = strategy.commission.percent, commission_value     = 0.05, slippage              = 1, pyramiding            = 1, calc_on_order_fills   = false, max_labels_count      = 500 )
```

## Ne yapıyor
Aurora KAMA Trend (kbYTJ8V2): KAMA(10) 3 bar yükselirse + fiyat>SMA200 → long (düşüşte short); sabit %4 stop, %6 izleyen (5 bar gecikmeli).

## Koddan kanıt (satır: kod)
```
97: strategy.close("Short")
98: strategy.entry("Long", strategy.long)
103: strategy.close("Long")
104: strategy.entry("Short", strategy.short)
117: strategy.exit(
125: strategy.exit(
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/kama_trend.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik. Girişler arası min. 5 bar kuralı uygulanmadı (motor yeniden girişi zaten stop sonrası bir sonraki sinyalde yapar).
