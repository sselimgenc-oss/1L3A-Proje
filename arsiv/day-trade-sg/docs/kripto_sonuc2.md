# Kripto — 2. tur: kitaplardan yeni stratejiler (2026-10-10)

Aynı test düzeni: Binance ilk 25 kripto, 15dk giriş / 1s-4s yön, 2023-10 → 2026-10 (3 yıl),
eğitim = ilk %70 (≈2023-10 → 2025-12), test = son %30. Parametreler yalnızca eğitime göre seçildi.
Portföy: 10.000 $, işlem başına %0,5 risk, en fazla 8 pozisyon, kaldıraç yok, yalnızca alış.

## S13 — Lien "Yanlış kırılmaları filtreleme" (gün içi uyarlama)
Kural (Kathy Lien, Böl. 9): fiyat 80×15dk (20 saat) yeni tepe yapar → 12 mumluk dibe geri çekilir
(zayıf oyuncular silkelenir) → 12 mum içinde yeniden o tepenin üstünde kapanırsa AL.
Filtre: 1 saatlikte **mükemmel düzen** SMA10>20>50>100>200 + 4s EMA20>EMA50 + 1s ADX>25 (Lien:
"ADX 20'den büyük"). Stop: 1 günlük ATR. Çıkış: gün sonu (UTC 24:00).

## S15 — Trend gününde EMA20 geri çekilmesinden alış
Kural (Lien momentum + Backus 20 EMA + Christensen VWAP mantığı): 14:00 UTC sonrası, gün içi tepe gün
açılışının ≥ 1,0 günlük ATR üstünde (momentum günü) ve 4s/1s yükselişte; fiyat 15dk EMA20'ye
(0,2 ATR yakınına) çekilir, EMA20 üstünde ve önceki mumun tepesinin üstünde kapanınca AL. Fiyat gün
açılışının üstünde olmalı. Stop: 0,75 günlük ATR. Çıkış: gün sonu.

## Sonuçlar (portföy, 3 yıl)

| Portföy | Maliyet | İşlem | Kazanma eğt/test | PF eğt/test | 10.000 $ → | Maks. düşüş |
|---|---|---|---|---|---|---|
| S13 tek | vadeli | 348 | %48,6 / %48,4 | 1,74 / 1,83 | 13.605 $ (+%36) | −%5,2 |
| S15 tek | vadeli | 1293 | %48,4 / %48,6 | 1,53 / 1,68 | 23.903 $ (+%139) | −%10,9 |
| **S13 + S15** | vadeli | 1478 | %48,2 / %47,1 | 1,50 / 1,68 | 26.029 $ (+%160) | −%12,2 |
| S13 + S15 | spot | 1475 | %46,3 / %46,2 | 1,42 / 1,59 | 23.272 $ (+%133) | −%12,9 |
| S10 + S13 + S15 | vadeli | 1746 | %47,7 / %48,3 | 1,42 / 1,74 | 27.219 $ (+%172) | −%10,6 |
| S10 + S13 + S15 | spot | 1744 | %46,5 / %47,7 | 1,35 / 1,65 | 24.044 $ (+%140) | −%11,9 |

Yıllık (S13+S15, spot): 2023 son çeyrek PF 1,32 · 2024 1,54 · 2025 1,23 · 2026 1,67 — her yıl kârlı.
S10+S13+S15 (vadeli): 13 çeyreğin 12'si kârlı.

## Notlar
- Avantajın ana kaynağı trend takibi (4s/1s yükseliş, yalnız alış); yeni stratejilerin girişleri
  (silkelenme sonrası kırılım, trend gününde geri çekilme) bunu iyileştiriyor. Uzun düşüş
  dönemlerinde işlem sayısı azalır.
- Portföy içinde S13'ün kazanma oranı %43,5–44,6'ya iniyor (tek başına %48,6) — geliştirme sürüyor.
- Elenen: S14 Bernstein MAC (kazanma ~%40, PF ~1,1).

## Son hal (geliştirmeler sonrası)
- **Ayrı alt hesap:** her strateji sermayenin eşit payıyla ve kendi pozisyon hakkıyla çalışır
  (stratejiler aynı coinde birbirinin yerini kapmaz). S13 portföy içi kazanma %44,6 → %47–48.
- **BTC 4s trend filtresi** (Manny Backus: hisseyi ancak S&P 500 olumluyken al): eğitimde her iki
  stratejide kazanma ve PF hafif arttı → eklendi.
- **5dk giriş:** son 180 günde 15dk ile aynı tablo, ek fayda yok → 15dk kaldı.
- **1R kısmi kâr (S13):** kazanma +0,8 puan, PF düştü → eklenmedi.

| Portföy (ayrı alt hesap + BTC filtresi, 3 yıl) | Maliyet | İşlem | Kazanma eğt/test | PF eğt/test | 10.000 $ → | Maks. düşüş |
|---|---|---|---|---|---|---|
| S13 + S15 | vadeli | 1227 | %48,8 / %47,7 | 1,61 / 1,72 | 16.544 $ (+%65) | −%5,8 |
| S13 + S15 | spot | 1224 | %47,3 / %47,5 | 1,54 / 1,64 | 15.685 $ (+%57) | −%6,4 |
| **S10 + S13 + S15** | vadeli | 1753 | %49,9 / %50,1 | 1,63 / 1,85 | 16.350 $ (+%64) | −%4,3 |
| **S10 + S13 + S15** | spot | 1752 | %48,8 / %49,5 | 1,56 / 1,76 | 15.634 $ (+%56) | −%5,0 |

Strateji bazında (üçlü, spot): S10 %52,8 / PF 1,72 · S13 %46,0 / PF 1,66 · S15 %47,0 / PF 1,50.
Yıllık PF (üçlü, spot): 2023 son çeyrek 1,38 · 2024 1,89 · 2025 1,10 · 2026 1,82 — her yıl kârlı.
İşlem başına risk %0,5 (alt hesap bazında); düşük düşüş nedeniyle risk %1'e çıkarılırsa getiri ve
düşüş yaklaşık iki katına çıkar.
