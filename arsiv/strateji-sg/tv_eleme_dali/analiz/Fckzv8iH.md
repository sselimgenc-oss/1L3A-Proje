# Squeeze Momentum on Reversal Strategy (`Fckzv8iH`)

- Yazar: DeepEntropy · Link: https://tr.tradingview.com/script/Fckzv8iH-Squeeze-Momentum-on-Reversal-Strategy/
- Kaynak: 51 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · kripto,abd,bist,emtia
- **Karar: AL**

## strategy() bildirimi
```
5: strategy(shorttitle = "Squeeze MOM", title="Squeeze Momentum on Reversal Strategy", overlay=false)
```

## Ne yapıyor
Squeeze Momentum on Reversal (Fckzv8iH): LazyBear momentumu (BB sapması KC çarpanıyla) sıfırın altındayken yukarı dönerse (|val|>0.0018) long, sıfırın üstündeyken aşağı dönerse short; hep piyasada.

## Koddan kanıt (satır: kod)
```
37: valin = linreg(source  -  avg(avg(highest, lowest), lastsma), lengthKC,0)
44: shortcondition = valin > strength and valin < nz(valin[1]) // line become green
45: longcondition = valin < (strength*-1) and valin > nz(valin[1]) // line become maroon
47: if(longcondition)
48: strategy.entry("BUY", strategy.long)
49: if(shortcondition)
50: strategy.entry("SELL", strategy.short)
```

## Repaint / lookahead kontrolü
Yalnız geçmiş mumlar; security/pivot yok. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/sq_reversal.py` olarak çevrilip test edildi.
