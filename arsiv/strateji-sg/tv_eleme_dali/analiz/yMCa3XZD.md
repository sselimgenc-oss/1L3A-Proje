# MACD + SMA 200 Strategy (by ChartArt) (`yMCa3XZD`)

- Yazar: ChartArt · Link: https://tr.tradingview.com/script/yMCa3XZD-MACD-SMA-200-Strategy-by-ChartArt/
- Kaynak: 75 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("MACD + SMA 200 Strategy (by ChartArt)", shorttitle="CA_-_MACD_SMA_strategy", overlay=true)
```

## Ne yapıyor
MACD + SMA 200 (yMCa3XZD, ChartArt): SMA tabanlı MACD histogramı 0'ı keserse + MACD>0 + hızlı>yavaş + 26 bar önce kapanış>SMA200 → long (tersi short). Stop-emir girişi bir sonraki açılışta dolar.

## Koddan kanıt (satır: kod)
```
64: strategy.entry("MACDLE", strategy.long, stop=buyprice, comment="Bullish")
70: strategy.entry("MACDSE", strategy.short, stop=sellprice, comment="Bearish")
```

## Repaint / lookahead kontrolü
request.security ve pivot yok; yalnız kapanmış mum verisi → repaint/lookahead yok. Giriş sinyal mumunun sonraki açılışında (strategy.entry varsayılanı).

## Karar ve gerekçe
Kod okundu; kesin-eleme listesinde (kapalı kaynak, strategy() yok, repaint/lookahead, DCA/grid/martingale, veri yok) değil → `tv/stratejiler/macd_sma200.py` olarak çevrildi ve test edildi. Sonuç ve eşik tablosu RAPOR.md'de. Yazar SPX/DOWI günlük test etmiş; günlük, tüm pazarlar.
