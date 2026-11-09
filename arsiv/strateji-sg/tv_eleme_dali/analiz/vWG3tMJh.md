# Laguerre RSI (`vWG3tMJh`)

- Yazar: mertriver1 · Link: https://tr.tradingview.com/script/vWG3tMJh-Laguerre-RSI-by-KivancOzbilgic-STRATEGY/
- Kaynak: 49 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
6: strategy("Laguerre RSI", shorttitle="LaRSI", overlay=false)
```

## Ne yapıyor
Laguerre RSI (vWG3tMJh): Laguerre filtresi (alpha 0.2) yukarı/aşağı bileşenleri cu, cd: cu>cd kesişiminde long, cu<cd kesişiminde short; hep piyasada.

## Koddan kanıt (satır: kod)
```
48: strategy.entry("Long",   true, when = window1() and crossover(cu, cd))
49: strategy.entry("Short", false, when = window1() and crossunder(cu, cd))
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/laguerre.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük, tüm pazarlar.
