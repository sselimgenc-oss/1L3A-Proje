# ortak/

`backtest_islemleri.csv`: nihai sistemin (algo/final.py) ana evrendeki portföye alınmış ve kapanmış backtest işlemleri, 2020-01 → 2026-10. Kaynak: `results/final_trades_{A,B}.csv`.

Sütunlar:
- `strateji_kod`: A1 / A2 / B.
- `giris_zamani`, `cikis_zamani`: UTC.
- `R`: maliyet ve funding dahil net R.
- `getiri`: işlemin özsermaye getirisi, R × risk olarak hesaplanır. Toplam 5x nominal sınırı nedeniyle küçültülen nadir işlemlerde gerçek getiri biraz daha düşüktür.
- `risk`: işlem başına özsermaye riski. A1/A2 için 0.005, B için 0.0075.

IS (2020–2023) ve OOS (2024+) ayrımı `giris_zamani` sütunundan yapılır.
