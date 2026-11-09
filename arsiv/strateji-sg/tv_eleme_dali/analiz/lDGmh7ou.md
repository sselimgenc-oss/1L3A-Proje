# UT Bot v2 — ATR Trailing Stop (`lDGmh7ou`)

- Yazar: QuantNomad · Link: https://tr.tradingview.com/script/lDGmh7ou-UT-Bot-v2-ATR-Trailing-Stop/
- Kaynak: 99 satır Pine
- Zaman dilimi / pazar: 4h (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy(title = 'UT Bot v2 — ATR Trailing Stop', shorttitle = "UT Bot v2", overlay = true)
```

## Ne yapıyor
UT Bot v2 (lDGmh7ou): ATR(10)×1 izleyen stop; fiyat çizgiyi keserse yön değiştir.

## Koddan kanıt (satır: kod)
```
94: strategy.entry("Long", strategy.long)
97: strategy.entry('Short', strategy.short)
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/utbot.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. UT Bot genelde saatlik/4 saatlikte kullanılır; 4 saatlik.
