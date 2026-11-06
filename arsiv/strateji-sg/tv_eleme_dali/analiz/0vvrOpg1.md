# HalfTrend Strategy (`0vvrOpg1`)

- Yazar: YashikaSatya · Link: https://tr.tradingview.com/script/0vvrOpg1-HalfTrend-SNIPERMONKEY/
- Kaynak: 144 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy('HalfTrend Strategy', overlay = true, default_qty_type = strategy.percent_of_equity, default_qty_value = 100)
```

## Ne yapıyor
HalfTrend Strategy (0vvrOpg1): amplitude 2, sapma 2; HalfTrend yön değiştirince long/short. Hint seans penceresi (09:20-15:20) ve gün sonu çıkışı uygulanmadı (NSE'ye özgü).

## Koddan kanıt (satır: kod)
```
109: strategy.close('Short', comment = 'Short → Long flip')
110: strategy.entry('Long', strategy.long, comment = carryBuy ? 'HT Buy (carried)' : 'HT Buy')
114: strategy.close('Long', comment = 'Long → Short flip')
115: strategy.entry('Short', strategy.short, comment = carrySell ? 'HT Sell (carried)' : 'HT Sell')
119: strategy.close_all(comment = 'EOD Exit 3:20 PM')
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/halftrend.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Yazar Hint gün içi (NSE) için yazmış; seans/gün sonu kuralı atılıp 1 saatlik, tüm pazarlarda test.
