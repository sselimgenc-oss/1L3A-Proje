# Grover Llorens Activator (`VuYM89Tw`)

- Yazar: alexgrover · Link: https://tr.tradingview.com/script/VuYM89Tw-Grover-Llorens-Activator-Strategy-Analysis/
- Kaynak: 31 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("Grover Llorens Activator")
```

## Ne yapıyor
Grover Llorens Activator (VuYM89Tw): ATR(480)×14 izleyen çizgi, kesişimde yön değiştir.

## Koddan kanıt (satır: kod)
```
19: strategy.entry("Buy", strategy.long)
21: strategy.entry("Sell", strategy.short)
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/grover.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, tüm pazarlar (uzun ATR: günlükte ~2 yıl).
