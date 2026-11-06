# Fractal Breakout Strategy (by ChartArt) (`EjLwVtgp`)

- Yazar: ChartArt · Link: https://tr.tradingview.com/script/EjLwVtgp-Fractal-Breakout-Strategy-by-ChartArt/
- Kaynak: 69 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Fractal Breakout Strategy (by ChartArt)", shorttitle="CA_-_Fractal_Breakout_Strat", overlay=true)
```

## Ne yapıyor
Fractal Breakout (EjLwVtgp, ChartArt): son 3 fraktal tepe fiyatı ortalaması yükseliyor ve fiyat son fraktalı kırıyor → long; 3 bar içinde trend bozulursa çıkış. Yalnız long.

## Koddan kanıt (satır: kod)
```
66: strategy.entry('Long', strategy.long)
69: strategy.close('Long')
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/fractal_brk.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Zaman dilimi belirtilmemiş; günlük (klasik 2016 betiği), yalnız long.
