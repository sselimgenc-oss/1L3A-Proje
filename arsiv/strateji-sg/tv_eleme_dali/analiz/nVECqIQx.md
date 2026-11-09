# TASC 2026.03 One Percent A Week (`nVECqIQx`)

- Yazar: PineCodersTASC · Link: https://tr.tradingview.com/script/nVECqIQx-TASC-2026-03-One-Percent-A-Week/
- Kaynak: 111 satır Pine
- Zaman dilimi / pazar: 1d (çeviri) · endeks,abd
- **Karar: AL**

## strategy() bildirimi
```
10: strategy( "TASC 2026.03 One Percent A Week", "1%/W", overlay = true, initial_capital = 1000, default_qty_type = strategy.percent_of_equity, default_qty_value = 10 )
```

## Ne yapıyor
TASC 2026.03 One Percent A Week (nVECqIQx): pazartesi açılışının %1 altına limit alış (hafta içi geçerli); dolunca +%1 hedef; cuma kapanışında çık. (Başa-baş çıkışı modellenmedi.)

## Koddan kanıt (satır: kod)
```
22: bool newSession = dayofweek == dayofweek.monday and session.isfirstbar_regular
24: if newSession
33: if newSession
34: strategy.entry("Buy", strategy.long, limit = down1)
51: strategy.exit(
64: strategy.exit(
86: newSession or not na(pt) ? na : wOpen,
92: newSession or not na(pt) ? na : down1,
```

## Repaint / lookahead kontrolü
Haftalık seans; yalnız geçmiş. Repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «eğitim (TASC makale örneği)». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/one_pct_week.py` olarak çevrilip test edildi. TASC makalesi örnek kod ama gerçek bir alım-satım kuralı (haftalık -%1 limit alış, +%1 hedef) içeriyor.
