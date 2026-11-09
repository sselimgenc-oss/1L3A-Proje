# Rejim filtresi araştırması (yalnız backtest) — 2026-10-11

Talep: ekip lideri (swing-sg). Kağıt bota ve `kagit/ayarlar.json`'a eklenmedi.
**Filtre:** BTC'nin dünkü günlük kapanışı SMA(n) altındaysa hiçbir stratejide yeni alış açılmaz
(Kathy Lien "büyük resim / önce uzun vadeli trend" ilkesi). Günlük BTC serisi 2020-11 → 2026-10
kesintisiz (iki veri setinin birleşimi); SMA henüz hesaplanamayan ilk günler (2021-01 → 2021-05,
BTC o dönemde SMA200'ün çok üstünde) "izin var" sayıldı.
Diğer her şey seçili sistemle aynı (S10+S13+S15, yalnız alış, BTC 4s filtresi, ayrı alt hesap,
%0,5 risk, **spot maliyet %0,08/yön**). Izgara taraması yapılmadı; ölçüt önceden belirlendi:
iki dönemde de PF ve maks. düşüş iyileşmeli, kazanma ≥ %45 kalmalı.

## Sonuçlar

| Varyant | Dönem | İşlem | Kazanma | PF | Getiri | Maks. düşüş | Sharpe |
|---|---|---|---|---|---|---|---|
| Filtre yok (kağıt bottaki) | 2021-01→2023-09 (+çöken coinler) | 1811 | %44,4 | 1,15 | +%13,6 | −%11,3 | 0,72 |
| | 2023-10→2026-10 | 1752 | %49,0 | 1,60 | +%56,3 | −%5,0 | 1,68 |
| **BTC < SMA200 → işlem yok** | 2021-01→2023-09 | 1219 | %45,0 | **1,24** | +%15,8 | **−%7,6** | 0,96 |
| | 2023-10→2026-10 | 1416 | %49,5 | **1,66** | +%50,3 | −%5,0 | 1,58 |
| BTC < SMA100 → işlem yok (komşu) | 2021-01→2023-09 | 1355 | %45,9 | 1,24 | +%17,6 | −%8,7 | 1,00 |
| | 2023-10→2026-10 | 1485 | %49,4 | 1,62 | +%49,7 | −%5,0 | 1,56 |
| Yalnız S13'e SMA200 | 2021-01→2023-09 | 1722 | %45,2 | 1,20 | +%17,5 | −%8,6 | 0,93 |
| | 2023-10→2026-10 | 1693 | %49,2 | 1,63 | +%57,0 | −%5,0 | 1,70 |

Yıllık (SMA200, tüm stratejiler): 2021 PF 1,37 · **2022: işlem yok** (BTC tüm yıl SMA200 altında;
filtresiz: 405 işlem, PF 0,66, −794 $) · 2023 PF 0,90 (BTC Ağustos'ta SMA200 altına indi) ·
2024 PF 1,87 · 2025 PF 1,13 · 2026 PF 2,66 (171 işlem; filtresiz 390 — BTC 2026'da kısmen SMA200 altında).

## Değerlendirme (ölçüte göre)
- **PF:** dört varyantın hepsinde iki dönemde de iyileşiyor (en çok SMA200: 1,15→1,24 ve 1,60→1,66).
- **Maks. düşüş:** 2021-23'te belirgin iyileşme (−%11,3 → −%7,6 / −%8,7 / −%8,6); **2023-26'da değişmiyor
  (−%5,0)** — bu dönemdeki en büyük düşüş BTC SMA200 üstündeyken oluşmuş. Ölçütün "her iki dönemde
  düşüş iyileşmeli" şartı katı okunursa **karşılanmıyor**; "kötüleşmemeli" okunursa karşılanıyor.
- **Kazanma:** tüm varyantlarda ≥ %45.
- **Bedeli:** 2023-26 getirisi +%56 → +%50 (SMA200); işlem sayısı ~%20 azalıyor.
- SMA100 komşu kontrolü aynı yönde → sonuç tek bir uzunluğa bağlı değil (sağlam).
- **Öneri:** SMA200 rejim filtresi (tüm stratejiler) en iyi risk düzeltmesi; ayı piyasasında sistemi
  kapatıyor. Kağıt bota ekleme kararı ekip lideri + kullanıcıda; eklenirse `kagit/ayarlar.json`'a
  ileriye dönük yeni sürüm olarak (geçmiş işlemler değişmez) ve kağıt motoruna BTC günlük SMA200 hesabı
  eklenerek.
