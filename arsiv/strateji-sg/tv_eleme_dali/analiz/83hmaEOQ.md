# Tomukas Elite SMC (`83hmaEOQ`)

- Yazar: Tomukasss · Link: https://tr.tradingview.com/script/83hmaEOQ-Tomukas-Elite-SMC/
- Kaynak: 261 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("Tomukas Elite SMC", overlay=true, initial_capital=100000, default_qty_type=strategy.percent_of_equity, default_qty_value=10, max_labels_count=500, max_lines_count=500, max_boxes_count=500)
```

## Ne yapıyor
Tomukas Elite SMC (83hmaEOQ): EMA200 trendi + ADX>20 + seans (08:00–17:00 UTC−4); 5/5 swing dibini süpürüp güçlü kapanış (likidite süpürme), karşı swing tepesinin kapanışla kırılması (MSS) ve oluşan FVG'ye geri çekilme → trend yönünde giriş; stop süpürme ucu, TP1 1R (%50), ardından kalan yarım başa-baş stop + ters süpürme/EMA200 kırılımında çıkış. İki bacak (%50/%50).

## Koddan kanıt (satır: kod)
```
49: float ph = ta.pivothigh(high, swingLen, swingLen)
50: float pl = ta.pivotlow(low, swingLen, swingLen)
170: strategy.entry("Buy", strategy.long)
178: strategy.entry("Sell", strategy.short)
188: strategy.exit("TP1", "Buy", qty_percent=50, limit=tp1Price)
190: strategy.exit("SL/BE", "Buy", stop=slPrice)
194: strategy.close("Buy", comment="Runner Exit")
201: strategy.exit("TP1", "Sell", qty_percent=50, limit=tp1Price)
203: strategy.exit("SL/BE", "Sell", stop=slPrice)
207: strategy.close("Sell", comment="Runner Exit")
```

## Repaint / lookahead kontrolü
Pivot: satır 49: `float ph = ta.pivothigh(high, swingLen, swingLen)` — pivot sağ-bar kadar gecikmeyle onaylanır; çeviride onay sonrasında kullanılıyor, repaint yok.

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/tomukas_smc.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Seans süzgeçli gün içi (5 dk olabilir); saatlik uyarlama.
