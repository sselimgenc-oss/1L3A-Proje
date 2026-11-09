# Squeeze Momentum Indicator Strategy [LazyBear + PineIndicators] (`G40dtEbK`)

- Yazar: PineIndicators · Link: https://tr.tradingview.com/script/G40dtEbK-Squeeze-Momentum-Indicator-Strategy-LazyBear-PineIndicators/
- Kaynak: 57 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy(shorttitle='SQZMOM_LB Strategy', title='Squeeze Momentum Indicator Strategy [LazyBear + PineIndicators]', overlay=false)
```

## Ne yapıyor
Squeeze Momentum (G40dtEbK, LazyBear+PineIndicators): sıkışma bitince momentum yükseliyorsa long (düşüyorsa short); momentum ters dönünce çıkış. (Pine'daki 8× kaldıraç yerine standart pozisyon boyu.)

## Koddan kanıt (satır: kod)
```
45: strategy.entry('L', strategy.long, qty=qty)
48: strategy.close('L')
52: strategy.entry('S', strategy.short, qty=qty)
55: strategy.close('S')
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/sqzmom.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, tüm pazarlar.
