# Kripto day trade — strateji geliştirme sonucu (2026-10-10)

**Veri:** Binance, ilk 25 kripto (CoinGecko, stablecoin hariç), 15dk/1s/4s, 2023-10 → 2026-10
(3 yıl; `market-data-uzun` dalı). **Eğitim:** her sembolün verisinin ilk %70'i (≈2023-10 → 2025-12),
**test:** son %30 (≈2025-12 → 2026-10). Parametreler yalnızca eğitim dönemine göre seçildi.
**Maliyet (tek yön, komisyon+kayma):** vadeli %0,05, spot %0,08. **Portföy:** 10.000 $, işlem başına
%0,5 risk, en fazla 8 pozisyon, tek pozisyon ≤ %30, toplam ≤ %100 (kaldıraç yok), aynı coinde tek
pozisyon, günlük −%3 zarar limiti, aynı anda gelen sinyallerde en güçlü coin önce.

## Seçilen strateji: S10 — Geç seans gün içi momentum (yalnızca alış)

| Kural | Değer | Kitap dayanağı |
|---|---|---|
| Yön (4s + 1s) | 4s EMA20 > EMA50 **ve** 1s EMA20 > EMA50, kapanış > 1s EMA50 | Lien (çoklu zaman dilimi), Wallace, Velez |
| Giriş penceresi | 16:00–20:00 UTC (İstanbul 19:00–23:00), 15dk mum | Lien (seanslar), Velez (NY seansı) |
| Tetik | Fiyat gün açılışından (00:00 UTC) ≥ 1,0 × günlük ATR yukarıda | Lien momentum ("ivme sizin tarafınızdayken"), Tranquil Trader (trend günü) |
| Giriş | Sinyal mumunun kapanışından sonraki mumun açılışı; günde coin başına 1 işlem | — |
| Stop | Giriş − 1,0 × günlük ATR | Backus/Lien (yapısal stop, ATR) |
| Çıkış | Gün sonu (UTC 24:00) veya stop | Bernstein (gün sonu çıkışı) |

### Sonuçlar (portföy, 3 yıl, 1073 işlem)

| | İşlem | Kazanma | PF | Kâr |
|---|---|---|---|---|
| Eğitim (vadeli) | 786 | %50,6 | 1,59 | +6.413 $ |
| Test (vadeli) | 287 | %55,1 | 2,16 | +4.995 $ |
| **Toplam (vadeli)** | **1073** | **%51,8** | **1,72** | **10.000 → 21.408 $ (+%114), maks. düşüş −%8,0** |
| Toplam (spot) | 1073 | %50,5 | ~1,63 | 10.000 → 20.017 $ (+%100), maks. düşüş −%8,1 |

Yıllık (vadeli): 2023 son çeyrek PF 1,46 · 2024 PF 1,71 · 2025 PF 1,40 · 2026 PF 2,22 — **her yıl kârlı**.
Çeyrek: 13'ün 10'u kârlı (zararlılar: 2024Ç3 −55 $, 2025Ç1 −269 $, 2026Ç4 kısmi). Ay: 37'nin 26'sı kârlı.

### Sağlamlık kontrolleri
- **Parametre platosu:** 16/17/18 UTC, hareket 0,8–1,2 ATR, stop 0,75–1,0 ATR komşu ayarların hemen
  hepsi eğitimde PF 1,3–1,6, testte 1,3–2,4. Tek bir şanslı hücre değil.
- **Momentum şartının katkısı (eğitim, yalnız alış):** şartsız PF 1,44 → ≥0 ATR 1,45 → ≥0,5 ATR 1,57
  → ≥1,0 ATR 1,54; testte 1,40 → 1,55 → 1,92 → 2,34.
- **Dürüst not — avantajın kaynağı:** yükseliş trendinde (4s/1s) günün herhangi bir saatinde alıp gün
  sonunda satmak da 3 yılda çoğunlukla kârlı (eğitim PF 1,0–1,7). Yani temel kaynak **trend takibi**
  (kriptoda bilinen zaman serisi momentumu); geç seans momentum şartı bunu iyileştiriyor. Kripto uzun
  bir düşüş/yatay döneme girerse işlem sayısı azalır ve sonuç zayıflar (2025Ç1 gibi).
- **Kısa (satış) işlemler elendi:** eğitimde PF 0,99 (başa baş). Spot piyasada açığa satış da yok.
- **Elenen dönem bağımlı sonuç:** Avrupa (7 UTC) ve ABD (14 UTC) açılışı varyantları son 11 ayda
  parlak görünüyordu (PF 1,6–2,8) ama 2023-2025 verisinde PF 0,9 — elendi.

## İsteğe bağlı ikinci strateji: S12 — Güçlü kapanış devamı (yalnızca alış) — SINIRDA
Dün gün aralığının üst %30'unda kapanış + 4s/1s yükseliş → 00:00–00:30 UTC'de al, gün sonunda sat,
stop 1 günlük ATR (Bernstein, Lien). 3 yıl: 1947 işlem, kazanma %45,8, PF 1,33, +%152, maks. düşüş
−%16,4; test kazanması %44,4 (hedefin hemen altında). S10 ile birlikte çalıştırınca gün boyu pozisyon
tuttuğu için S10'un yerini kapıyor (toplam PF 1,34–1,39, düşüş −%16). **Önerim: yalnız S10.**

## Elenen stratejiler (kripto, maliyet sonrası zararda veya tutarsız)
S1 trend geri çekilme, S2 momentum 20-100, S3 açılış aralığı, S4 Bollinger dönüşü, S5 önceki gün
kırılması, S6 sahte kırılma/Fader, S7 VWAP geri alma, S8 Camarilla, S9 seans aralığı kırılması
(Londra/NY), S10 Avrupa/ABD açılış varyantları. Ortak sorun: brüt beklenti ≈ 0R; 15dk'lık kısa
işlemlerde maliyet riskin %10–40'ı.
