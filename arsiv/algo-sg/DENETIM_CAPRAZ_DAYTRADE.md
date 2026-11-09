# Çapraz denetim — day-trade-sg (S10 Akşam Momentumu · S13 Tuzak Kırılım · S15 Trend Günü Molası)

Denetçi: algo-sg oturumu, 2026-10-12. Talep: ekip lideri (swing-sg). **Salt okunur:** day-trade-sg
deposuna commit/push yapılmadı, kağıt bota dokunulmadı. Kod: day-trade-sg `main` 7ef56d8; veri:
`market-data-uzun` (2023-10 → 2026-10, 25 coin) ve `market-data-2021` (2020-11 → 2023-10, delist edilmiş
coinler dahil 37 coin). Testler day-trade-sg'nin kendi kodu ile (`daytrade/*`, `kagit/motor.portfoy_ayri`,
`secili.py` parametreleri) koşuldu: `scripts/denetim_daytrade.py`, ham sonuçlar
`results/denetim_daytrade_{2023_26,2021_23}.json`.

**Tekrarlanabilirlik:** taban sonuç birebir tuttu: 1752 işlem, kazanma %49,0, PF 1,60, +%56,3,
maks. düşüş −%5,0 (docs/kripto_sonuc2.md ile aynı). Stres seti: 1823 işlem / PF 1,14 / +%12,8
(belgede 1811 / 1,15 / +%13,6; küçük fark tarih sınırı/PUMP kaynaklı).

## Bulgular (14)

| # | Önem | Bulgu | Kanıt |
|---|---|---|---|
| 1 | **Yüksek** | **Rejim bağımlılığı:** ana backtest dönemi (2023-10 → 2026-10) tamamen boğa; ayı/yatayda kenar yok. Kağıt botun beklentisi (PF 1,6, `durum.json` "beklenti") iyimser. | 2021-23 (37 coin): PF 1,14, Sharpe 0,69, DD −%11,7. **2022: 410 işlem, PF 0,66, −%8,2**; 2023: PF 0,98. 2023-26 içinde bile 2025: PF 1,10, Sharpe 0,34. |
| 2 | **Yüksek** | **Çoklu test / deflated Sharpe:** 15 strateji (S1–S15) denendi, parametreler eğitimde seçildi. Günlük getiri dağılımı aşırı çarpık → Sharpe kırılgan. | DSR (N=15, çarpıklık/basıklık düzeltmeli): 2023-26 Sharpe 1,66, eşik 1,03 → **DSR 0,95** (sınırda geçer). 2021-23 Sharpe 0,69 < eşik 1,07 → **DSR 0,25** (geçmez). Yalnız OOS (408 işlem, ~10 ay): Sharpe 2,02, eşik 1,92 → DSR 0,56 (kanıt değeri yok). Çarpıklık 10,4, basıklık 186. |
| 3 | **Yüksek** | **Hayatta kalma / zaman içi evren (point-in-time):** evren bugünün ilk 25'i (`daytrade/universe.py:28`, "2026-10-10"). OOS gücünün büyük kısmı 2023'ten sonra yükselen coinlerden. Kendi stres testinin "yanlılık küçük" sonucu yalnız delist edilmiş coinleri ölçüyor, bugünün kazananlarını seçmeyi ölçmüyor. | Yalnız Eki-2023'te de ilk 25'te olan 16 coin: **OOS PF 1,74 → 1,27, Sharpe 2,02 → 1,01, OOS getiri +%17,9 → +%4,3**; IS etkilenmiyor (PF 1,70). |
| 4 | **Yüksek** | **Kâr yoğunlaşması:** iki coin toplam kârın %41'i. | 2023-26: TRX +1.339 $, QNT +998 $ / toplam 5.632 $. Aynı TRX 2021-23'te −189 $. |
| 5 | **Yüksek** | **Kağıt test bir icra testi değil, ileriye dönük backtest:** günde 2 çalıştırma, tarihsel mum açılışından dolum. Kayma, gecikme, spread hiç ölçülmüyor; 60 günlük kağıt başarısı canlı kanıtı sayılmaz. | `.github/workflows/kagit.yml:11` cron "41 0,12"; gerçek çalışmalar 10-11 06:22, 17:47, 10-12 06:28, 21:24 UTC (5–9 sa kayma). İlk 2 günde 0 işlem. Olumlu taraf: yeniden oynatma sayesinde kaçan işlem yok ve sonuç tekrarlanabilir. |
| 6 | **Yüksek** | **Canlı parite, `_session_ok`:** "son 30 dk giriş yok" kuralı günün son mumunu (`since_open.groupby(day).transform("max")`) kullanıyor. Backtestte 24 saatlik kriptoda bu sabit (1425 dk), ancak canlıda o günün en son mumuna eşit olduğu için sinyal o an tanınmıyor, ancak sonraki veriyle ortaya çıkıyor. Yeniden oynatma bu işlemi tarihsel t+1 açılışından dolduruyor, canlıda bu fiyat yakalanamaz. | `daytrade/strategies.py:82-86`. **1 mum gecikme etkisi: 2023-26'da PF 1,60 → 1,46, getiri +%56 → +%41; 2021-23'te PF 1,14 → 1,04, getiri +%12,8 → +%2,7.** Sistem icra gecikmesine çok duyarlı. |
| 7 | Orta | **`last_bar` geleceğe bakıyor (`shift(-1)`):** canlı verinin son mumu "gün sonu" işaretleniyor; ara çalıştırmada açık pozisyonlar sahte "eod" kapanışı gösterebilir ve son mumdaki sinyal "bekleyen" olarak yazılmaz. Sonraki çalıştırma düzeltir, ama ara raporlar yanıltıcı olabilir. | `daytrade/features.py:89`. |
| 8 | Orta | **Maliyet ince:** 15 dakikalık altcoin kırılımında yön başına %0,08 (komisyon + kayma). Binance spot taker %0,10 (BNB ile %0,075) ve üstüne kayma var. Stres rejiminde gerçekçi maliyetle kenar kayboluyor. | `daytrade/universe.py:51`. Maliyet %0,12: PF 1,51 (stres 1,09). %0,16: PF 1,43 (**stres 1,04, getiri +%2,8, DD −%15,6**). |
| 9 | Orta | **BTC 4s filtresi (EMA20>EMA50) giderek daha çok engelliyor; uzun vade boğa iken bile:** filtrenin avantajın kaynağı olduğu da gösterilemiyor. | İzinli gün oranı: 2023 %78 → 2024 %59 → 2025 %49 → 2026 %52. BTC günlük 83.085 > SMA200 71.956 (10-10). Filtre kaldırılınca 2023-26 Sharpe 1,66 → 1,83, ama 2021-23 DD −%11,7 → −%14,6 ve 2022 PF 0,70. |
| 10 | Orta | **Günlük −%3 kuralı fiilen ölü:** iki dönemde de tek işlemi engellemedi. Kural yalnız gerçekleşen kârı sayıyor (açık zarar dahil değil) ve alt hesap bazında çalışıyor. %0,5 risk ve alt hesap başına ≤3 pozisyonla −%3'lük gün pratikte imkânsız. | `kagit/motor.py:168`. Limitli/limitsiz işlem: 1752=1752, 1823=1823. En kötü gün: −%1,54 (2023-26), −%1,39 (2021-23). |
| 11 | Orta | **Strateji çeşitlenmesi zayıf:** üçü de aynı faktör (trend + yalnız alış). Streste üçü birlikte zayıflıyor. | 2021-23 alt hesap: S13 PF 1,08 (DD −%15), S10 PF 1,12, S15 PF 1,18 (en kötü hafta −%5,5, DD −%15,6). |
| 12 | Düşük | **Kuyruk riski ve BTC bağımlılığı düşük** (gün sonu çıkış gece boşluğunu kesiyor), ama yalnız-alış bir çöküşte tüm pozisyonlar birlikte hareket eder. | Portföy en kötü hafta −%1,5 (2023-26) / −%2,8 (2021-23); CVaR95 günlük −%0,61 / −%0,71; BTC korelasyonu günlük 0,17–0,23, haftalık 0,29–0,32. |
| 13 | Düşük | **Evren ilk çalıştırmada donduruluyor;** kağıt dönemi için doğru, ama içinde verisi çok kısa coinler var. | `kagit/motor.py:50-60`; HYPE verisi 2026-09-24'ten (1572 mum), GRAM da kısa. |
| 14 | Düşük | **Isınma 45 gün:** 4s EMA200 tam oturmuyor, kağıt↔backtest arasında gösterge farkı küçük de olsa var. | `kagit/motor.py:32`; başlangıç değerinin kalan ağırlığı ≈ e^(−270·2/201) ≈ %7. |

Zaman dilimi: her şey UTC, kripto günü 00:00 UTC'de başlıyor; tutarlı, bulgu yok.

## Optimizasyon önerileri (3, hepsi "Aralık v2 adayı"; canlı bota dokunulmaz)

Bu denetimde **5 optimizasyon varyantı** denendi: SMA200, SMA100, BTC 4s filtresi kaldırma,
BTC 4s yerine SMA200, PIT evren. Ayrıca 3 duyarlılık testi yapıldı (maliyet ×2, 1 mum gecikme).
Hepsi önceden tanımlıydı, ızgara taraması yok. 2023-26 IS/OOS = ilk %70 / son %30 (sistemin kendi
bölmesi), stres = 2021-01 → 2023-09 (delist edilmiş coinler dahil).

| Varyant | 2023-26 PF (IS / OOS) | 2023-26 Sharpe · getiri · DD | 2021-23 PF · Sharpe · DD | 2022 |
|---|---|---|---|---|
| Taban (kağıttaki) | 1,57 / 1,74 | 1,66 · +%56,3 · −%5,0 | 1,14 · 0,69 · −%11,7 | 410 işlem, PF 0,66, −%8,2 |
| **Ö1: + BTC günlük SMA200** | 1,54 / 2,66 (171 işlem) | 1,56 · +%50,3 · −%5,0 | **1,24 · 0,94 · −%7,7** | işlem yok |
| Ö1 komşu: SMA100 | 1,55 / 2,01 | 1,54 · +%49,7 · −%5,0 | 1,24 · 0,98 · −%8,8 | 94 işlem, PF 0,48 |
| **Ö2: BTC 4s yerine SMA200** | 1,52 / 2,61 (195 işlem) | 1,62 · +%53,2 · −%4,8 | **1,23 · 0,97 · −%10,0** | işlem yok |
| (red) BTC 4s filtresi tamamen kalksın | 1,55 / 1,69 | 1,83 · +%66,4 · −%4,8 | 1,13 · 0,69 · **−%14,6** | 589 işlem, PF 0,70 |
| **Ö3: PIT evren (ölçüm)** | 1,70 / **1,27** | 1,43 · +%42,0 · −%4,4 | (bugünün evreni) 1,14 · 0,63 · −%11,2 | 295 işlem, PF 0,53 |

1. **Ö1: BTC günlük SMA200 rejim filtresi** (dünkü kapanış SMA200 altındaysa yeni alış yok;
   mevcut filtrelerin üstüne). Stres döneminde PF 1,14 → 1,24, Sharpe 0,69 → 0,94, DD −%11,7 → −%7,7,
   2022 zararını tamamen önlüyor. Bedeli: 2023-26 getirisi −6 puan, işlem sayısı −%19, IS PF
   1,57 → 1,54. SMA100 komşusu aynı yönde, yani sonuç tek uzunluğa bağlı değil. day-trade-sg'nin
   kendi `docs/kripto_rejim.md` çalışmasını bağımsız olarak doğruluyor. DSR (stres) 0,25 → 0,39:
   iyileşiyor ama hâlâ eşiğin altında.
2. **Ö2: BTC 4s EMA filtresini SMA200 ile değiştirmek** (filtreyi gevşetir). "4s filtresi uzun vade
   boğa iken tüm alışları kesiyor" sorununu çözer: şu an BTC SMA200'ün %15 üstünde. 2023-26: PF 1,64,
   Sharpe 1,62, DD −%4,8. Stres: PF 1,23, Sharpe 0,97, 2022'de işlem yok. Ö1'e göre daha çok işlem
   (1582'ye karşı 1416), ama stres DD'si daha kötü (−%10,0'a karşı −%7,7). 4s filtresinin tamamen
   kaldırılması reddedildi (stres DD −%14,6).
3. **Ö3: zaman içi (PIT) evren + canlı parite düzeltmesi.** Getiri artırmayan bir ölçüm önerisi:
   - Aylık yeniden seçilen PIT ilk-25 evreni.
   - `_session_ok` için sabit seans sonu (kripto: 1440 − son giriş dakikası).
   - `last_bar`'ın yalnız saatten hesaplanması.
   - Kağıt motorunun 15 dk'da bir (en az saatte bir) çalışıp karar anını ve kullanılabilir fiyatı
     kaydetmesi.

   Kanıt: PIT alt kümesinde OOS PF 1,27, 1 mum gecikmede PF −0,14 (stres −0,10). **Beklentinin
   PF 1,6'dan ~1,2–1,3'e çekilmesi** gerekir. Kağıt dönemi bu düzeltme olmadan değerlendirilirse
   iyimser kalır.

## Özet hüküm

Kod temiz ve tekrarlanabilir. Göstergelerde ileriye bakma yok (HTF birleştirme `merge_asof` ile
kapanış anına hizalı, günlük ATR kaydırılmış). Ancak manşet sonuç (PF 1,6, Sharpe 1,7) tek bir boğa
dönemine, bugünün kazanan coinlerine (TRX + QNT kârın %41'i) ve gecikmesiz icraya dayanıyor. Bu üç
düzeltme birlikte uygulanınca gerçekçi beklenti PF ≈ 1,1–1,3, yıllık getiri ≈ %3–8 (risk %0,5'te).
2022 tipi ayı piyasasında koruma ancak SMA200 rejim filtresiyle geliyor.
