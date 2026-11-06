# Shinobi HA Stratégia v3 (`CtFpKECD`)

- Yazar: Takumi_algo · Link: https://tr.tradingview.com/script/CtFpKECD-Shinobi/
- Kaynak: 238 satır Pine
- Zaman dilimi / pazar: 1h (çeviri) · kripto,abd,emtia
- **Karar: AL**

## strategy() bildirimi
```
2: strategy("Shinobi HA Stratégia v3", overlay=true, pyramiding=0, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, process_orders_on_close=true)
```

## Ne yapıyor
Shinobi HA v3 (CtFpKECD): Heikin Ashi desenı — iki tam gövdeli (fitilsiz) HA mumu ardından, ondan büyük doji mum + SuperTrend(3.44) yönü + ADX≥22 + yapı filtresi (swing dipleri yükseliyor) + hacim ≥ EMA20 + 17:00–20:00 (Budapeşte) seansı; stop HA dibi/tepesi, hedef 1R. (Seans UTC 15–18 alınır.)

## Koddan kanıt (satır: kod)
```
150: swing_bull_ok = na(last_sl2) or last_sl > last_sl2
154: struct_bull = switch filter_type
158: "Swing HL"         => swing_bull_ok
202: sell_setup = s_bull2 and s_lowwick2 and s_bull1 and s_lowwick1 and s_doji and s_size
210: buy_setup  = b_bear2 and b_upwick2 and b_bear1 and b_upwick1 and b_doji and b_size
213: long_signal  = buy_setup  and ha_bull and adx_ok and struct_bull and inSession and vol_ok
214: short_signal = sell_setup and ha_bear and adx_ok and struct_bear and inSession and vol_ok
220: strategy.entry("Long", strategy.long)
221: strategy.exit("Long Exit", "Long", stop=sl, limit=tp)
226: strategy.entry("Short", strategy.short)
227: strategy.exit("Short Exit", "Short", stop=sl, limit=tp)
```

## Repaint / lookahead kontrolü
`ta.pivothigh(ha_high, 5, 5)` 5 mum gecikmeli; repaint yok.

## Karar ve gerekçe
Önceki tur gerekçesi: «Heikin Ashi + pivot; temsilci seçilmedi». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/shinobi_ha.py` olarak çevrilip test edildi.
