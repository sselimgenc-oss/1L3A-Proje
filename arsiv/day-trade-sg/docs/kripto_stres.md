# Kripto sistemi stres testi — 2021-01 → 2023-09 (2022 ayı piyasası + hayatta kalma yanlılığı)

Talep: ekip lideri (swing-sg oturumu), 2026-10-11. Kağıt bota ve `kagit/ayarlar.json`'a dokunulmadı;
parametreler `daytrade/secili.py` ile birebir aynı (S10 + S13 + S15, yalnız alış, BTC 4s filtresi,
ayrı alt hesaplar, işlem başına %0,5 risk, spot maliyet %0,08/yön, gün sonu çıkış).

**Veri:** data.binance.vision aylık arşivleri (delist edilmiş coinler dahil), 15dk/1s/4s, 2020-11 →
2023-10 (`market-data-2021` dalı). İşlemler 2021-01-01 ile 2023-09-30 arasında açılanlar.
LUNA serisi 2022-05-13'te kesildi (çöküş sonrası aynı sembol LUNA 2.0'a geçti).

## 1. Bugünkü evren (hayatta kalanlar; o dönemde verisi olan 19 coin)

| Dönem | İşlem | Kazanma | PF | Kâr |
|---|---|---|---|---|
| 2021 (boğa) | 715 | %50 | 1,45 | +1.624 $ |
| **2022 (ayı)** | **295** | **%38** | **0,53** | **−798 $** |
| 2023 (Oca–Eyl) | 327 | %41 | 1,06 | +103 $ |
| **Toplam** | **1337** | **%45,4** | **1,14** | **+%9,3 (10.929 $)** |

Maks. düşüş −%11,3 · Sharpe 0,59 · yıllık getiri %3,3 · 11 çeyreğin 5'i kârlı (2022'nin 4 çeyreği de zararda).
Strateji bazında: S10 PF 1,10 · S13 PF 0,91 · S15 PF 1,24.

## 2. Hayatta kalma stresi (+ LUNA, FTT, SRM, ALGO, MATIC, EOS, AXS, FIL, THETA, ATOM, ICP, VET)

| Dönem | İşlem | Kazanma | PF | Kâr |
|---|---|---|---|---|
| 2021 | 1005 | %48 | 1,40 | +2.170 $ |
| **2022** | **405** | **%40** | **0,66** | **−794 $** |
| 2023 (Oca–Eyl) | 401 | %40 | 1,00 | −14 $ |
| **Toplam** | **1811** | **%44,4** | **1,15** | **+%13,6 (11.363 $)** |

Maks. düşüş −%11,3 · Sharpe 0,72 · yıllık getiri %4,8.

## Değerlendirme
- **2022 ayı piyasasında sistem zarar ediyor:** PF 0,53–0,66, kazanma %38–40, yılda ≈ −%8.
  Trend filtresi (4s/1s + BTC 4s) düşüş piyasasında işlem sayısını azaltıyor (2021: 715 → 2022: 295)
  ama kısa süreli yükseliş dalgalarındaki alışlar tutmuyor. Ekip liderinin eşiği (2022'de PF < 1)
  aşıldı → bildirildi; kağıt test durdurulmadı, kurallar değiştirilmedi.
- **Hayatta kalma yanlılığı küçük:** çöken coinler eklenince sonuç değişmiyor (PF 1,14 → 1,15).
  Yalnız alış + trend filtresi çöken coinlerden büyük ölçüde uzak tutuyor.
- **Uzun vadeli tablo (2021-01 → 2026-10, iki test birleşik):** boğa dönemlerinde PF 1,4–1,9,
  ayı/yatay dönemlerde PF 0,5–1,1. Ana backtestin (2023-10 → 2026-10, PF 1,60) gelecekteki bir ayı
  piyasası için iyimser olduğu açık; beklenti buna göre düşürülmeli.
- **Olası iyileştirme yönleri (karar ekip liderinde, bu raporda uygulanmadı):** günlük/haftalık
  rejim filtresi (ör. BTC günlük SMA200 altında işlem yok — Lien'in "büyük resim" ilkesi), 2022'de
  zararda olan S13'ün ayı rejiminde kapatılması.
