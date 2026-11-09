# Momentum Sequence Strategy [Herman] (`mmrInMTp`)

- Yazar: helmans13 · Link: https://tr.tradingview.com/script/mmrInMTp-Momentum-Sequence-Strategy-Herman/
- Kaynak: 536 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
9: strategy( "Momentum Sequence Strategy [Herman]", overlay = true, pyramiding = 0, initial_capital = 50000, currency = currency.USD, default_qty_type = strategy.fixed, default_qty_value = 1, commission_type = strategy.commission.cash_per_contract, commission_value = 2.50, slippage = 1, margin_long = 5, margin_short = 5 )
```

## Ne yapıyor
Momentum Sequence [Herman] (mmrInMTp): kırmızı 'ana' mumun ardından 5 ardışık yeşil mum (her biri öncekinden yüksek kapanış, düşükleri ana mumun dibinin üstünde) → long; stop = ana mum dibi, hedef = 1.5R. Yalnız long (short varsayılan kapalı).

## Koddan kanıt (satır: kod)
```
149: bool validBullishSequence = true
155: validBullishSequence := false
160: validBullishSequence := false
166: validBullishSequence := false
172: bool validBearishSequence = true
178: validBearishSequence := false
183: validBearishSequence := false
189: validBearishSequence := false
195: longSetup =
197: validBullishSequence
201: validBearishSequence
207: if enableLongTrades and longSetup and strategy.position_size == 0
216: strategy.entry(
234: strategy.entry(
```

## Repaint / lookahead kontrolü
Yalnız geçmiş mum dizisi. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/mom_seq.py` olarak çevrilip test edildi.
