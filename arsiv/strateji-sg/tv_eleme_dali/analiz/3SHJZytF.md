# Strategy: HMA 50 + Supertrend Sniper (`3SHJZytF`)

- Yazar: Gustav_Rex · Link: https://tr.tradingview.com/script/3SHJZytF/
- Kaynak: 84 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Strategy: HMA 50 + Supertrend Sniper", overlay=true, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100)
```

## Ne yapıyor
HMA 50 + Supertrend Sniper (3SHJZytF): HMA yükselirken + supertrend yükselişte long; düşerken + düşüşte short; çelişki (choppy) → çıkış.

## Koddan kanıt (satır: kod)
```
46: strategy.entry("Long", strategy.long, comment="LONG")
50: strategy.entry("Short", strategy.short, comment="SHORT")
54: strategy.close_all(comment="Close (Choppy)")
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/hma_st.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; 4 saatlik (Yahoo 1s 2 yıl, kripto 2019+).
