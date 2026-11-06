# Gap Filling Strategy (`ghocsiv7`)

- Yazar: alexgrover · Link: https://tr.tradingview.com/script/ghocsiv7-Gap-Filling-Strategy/
- Kaynak: 33 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · abd,bist
- **Karar: AL**

## strategy() bildirimi
```
5: strategy("Gap Filling Strategy",overlay=true)
```

## Ne yapıyor
Gap Filling (ghocsiv7): yeni seansın ilk saatlik mumunda yukarı boşluk → short, aşağı boşluk → long (boşluğu kapanışa doğru fade); hedef = önceki mumun gövde kenarı (boşluk dolum seviyesi); stop yok; sonraki seansın başında kapat.

## Koddan kanıt (satır: kod)
```
12: upgap = o > high[1] and min(c,o) > max(c[1],o[1])
13: dngap = o < low[1] and min(c[1],o[1]) > max(c,o)
15: val = upgap ? max(c[1],o[1]) : min(c[1],o[1])
16: lim = valuewhen(ses and (upgap or dngap),val,0)
18: strategy.close_all(clw == "New Session" ? ses :
19: clw == "New Gap" ? ses and (upgap or dngap) : false)
21: strategy.entry("Buy", strategy.long, when=ses and upgap)
22: strategy.entry("Sell", strategy.short, when=ses and dngap)
24: strategy.entry("Buy", strategy.long, when=ses and dngap)
25: strategy.entry("Sell", strategy.short, when=ses and upgap)
27: strategy.exit("ExitBuy","Buy",stop=lim)
28: strategy.exit("ExitSell","Sell",stop=lim)
30: strategy.exit("ExitBuy","Buy",limit=lim)
31: strategy.exit("ExitSell","Sell",limit=lim)
```

## Repaint / lookahead kontrolü
Yalnız önceki mum ve seans başı; `change(time("D"))`. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/gap_fill.py` olarak çevrilip test edildi. Gün içi mantık: saatlik hisse verisiyle.
