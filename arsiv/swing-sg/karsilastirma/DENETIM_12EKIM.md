# Denetim — 12 Ekim 2026 (panel + 5 hesap + strateji belgeleri)

Üç bağımsız denetim (panel kodu, panel↔bot mutabakatı, strateji/belge tutarlılığı). Bulgular koordinatörce
kaynağından doğrulandı. Durum: **düzeltildi** / **ekibe iletildi** / **Aralık kararı** / **kayıt**.

## A. Panel (düzeltildi, 2211e25 → sonrası)

| # | Bulgu | Durum |
|---|---|---|
| A1 | Koni ilk günlerde yapay dardı (backtest kârı kapanış gününe yazıyor) → Algo'da yanlış alarm | düzeltildi: kısa ufukta bant normal yaklaşımla genişletildi |
| A2 | Koni "sarı" (%5–25 dilimi) sağlıklı hesapta da sık; her seferinde uyarı üretiyordu | düzeltildi: sarı yalnız kartta, uyarı yalnız kırmızıda |
| A3 | GitHub fetch geçici hata verirse hesap 10.000 $ / boş işlem olarak yazılıyordu | düzeltildi: eldeki son referansla devam; "veri yok" alarmı eklendi |
| A4 | 00:00 UTC girişler tarih-only'ye dönüşüyordu (saat kaybı, süre/sıralama hatası) | düzeltildi |
| A5 | 1e-5 altı fiyatlar (PEPE) yuvarlanıp giriş = stop görünüyordu | düzeltildi: 6 anlamlı basamak |
| A6 | Kart "maks. düşüş" (saatlik) ile su altı grafiği (günlük) farklı sayı | düzeltildi: ikisi aynı tanım |
| A7 | Günlük değerler UTC gününe, işlemler İstanbul gününe göre | düzeltildi: hepsi İstanbul günü |
| A8 | Alt hesap tekrarları (KGT 6 defter) açık pozisyonu ve "son 24 saat"i şişiriyordu (19→13, 9→7) | düzeltildi |
| A9 | Eğri başlangıç noktası (10.000) botun ilk satırıyla eziliyordu | düzeltildi |
| A10 | "Son 24 saat" tarih-only kayıtlarda ~48 saate açılıyordu; yalnız dengeleme olan gün "." yazıyordu | düzeltildi |
| A11 | Bot gecikme uyarısı "24 saattir" sabit metin; panel bayatlığı hiç uyarılmıyordu | düzeltildi: gerçek süre + 3 saatten eski panel uyarısı |
| A12 | İşlem listesi 400'de kesiliyor, istatistik sekmesi bunu söylemiyordu | düzeltildi: 1000 + uyarı notu |
| A13 | Kayıp serisi iki ekranda farklı tanım; "en iyi gün" negatifken yeşil; gün sayacı 62'yi aşabiliyordu | düzeltildi |

## B. Botlar (panel↔bot mutabakatı)

| # | Bulgu | Durum |
|---|---|---|
| B1 | Swing: DOT/APT/NEAR emirleri dönem öncesi hayalet pozisyon yüzünden açılmadı | main'de düzeltildi (PR #5); durum dalı botun bir sonraki çalışmasında düzelir — izleniyor |
| B2 | GitHub zamanlayıcısı çalışmaları atlıyor: algo 2,4 günde 9/29, strateji 63 saatte 19/126 çalışma | kayıt: yeniden oynatma veri kaybını önlüyor, panel arada bayat kalıyor; panel artık bunu gösteriyor |
| B3 | Strateji: TP1 kısmi kârları islemler.csv'ye yazılmıyor; kapananlarda yön boş, defter etiketi tutarsız | strateji ekibine iletildi (kayıt düzeltmesi) |
| B4 | Algo: kısmi çıkışlar islemler.csv'de yok (APT K/Z CSV'den doğrulanamıyor) | algo ekibine iletildi |
| B5 | Trend: başlangıç pozisyonları "zaten elde" sayılıyor, ilk alım işlemi ve maliyeti yok | kayıt: etkisi tek seferlik ≈ binde 1–3; test ortasında bot değiştirilmedi |
| B6 | Day trade 0 işlem: bozuk değil — BTC 4s filtresi (EMA20<EMA50) tüm alışları kesiyor | kayıt: tasarım riski, rejim sürerse bot boşta kalır |

## C. Strateji ve belgeler (Aralık kararını doğrudan etkiler)

1. **Beklentiler iyimser pencereden** (doğrulandı). Algo yıllık getirisi 2025 +%10, 2026 (9 ay) +%2; %21 beklentiyi 2021 (+%57) ve 2024 (+%35) taşıyor. Day trade 2021–23 stres testi Sharpe 0,59, yıllık %3–5, 2022'de zarar. Trend kollarında örneklem içi düşüş −%19 (beklenti −%7). Panel bu iyimser sayılarla kıyaslıyor. → **Aralık:** her hesap için "iyimser" ve "stres" olmak üzere iki beklenti; karar kartında ikisi de gösterilecek.
2. **"Örneklem dışı" tam örneklem dışı değil.** Trend kolları 2023–26'ya da bakılarak seçildi (birlesim.py), swing iyileştirmeleri OOS R'ye göre sıralandı, strateji EMA20 filtresi OOS'a bakılarak eklendi. Gerçek ileri test yalnız bu 60 gün.
3. **Ölçü yöntemi karışık.** Swing beklentisi gerçekleşmiş özsermayeden (−%13 / 1,45), oysa günlük piyasa değeriyle −%17 / 1,32. Algo bot yapısıyla (5.000 + 5.000) 1,25 / −%17,8. → Aralık kartında MTM sayıları kullanılacak.
4. **Gizli yoğunlaşma.** Üç kripto listesinde ortak 17 coin. BTC rejimi 4 hesabı yönlendiriyor; A-long girişlerinin %66'sı BTC Pusulası açıkken. NEAR 3–4 hesapta, toplam ≥ 816 $. → Aralık seçiminde "farklı rol" yetmez; BTC rejim faktörüne toplam maruziyet sınırı gerekir.
5. **Evren yanlılığı.** ABD sepeti bugünün 50 büyük şirketinden; kural, kendi sepetinin al-tutundan zayıf (Sharpe 1,53'e karşı 1,70). Day trade listesi 10 Ekim'in CoinGecko ilk 25'i.
6. **60 gün istatistik için kısa.** Yıllık Sharpe'ın standart hatası ±3,6. Kağıt test "bot doğru çalışıyor mu"yu kanıtlar, "strateji kazandırır mı"yı kanıtlamaz.
7. **Gerçek para planı v1 kendi testleriyle çelişiyor** (doğrulandı). "−%15'te dur" kuralı, 2x'teki normal düşüşlerin (−%25…−%30) içinde kalıyor. "Tasfiye mesafesi ≥ 1,5 × stop" kuralıyla güvenli kaldıraç A ≈ 4,8x, B ≈ 1,3x (tabloda 7,2x / 1,9x). Algo backtest'i kolu zamanın %22'sinde 1x üstünde tutuyor (maks 2,3x). → **Plan v2 Aralık'ta**: durdurma eşiği hesap başına stres düşüşünün 1,2 katı; kaldıraç tablosu 1,5 kat kuralıyla yeniden.
8. **Kâğıt hesaplar yeniden oynatma.** 4 botta her çalışmada geçmiş baştan simüle ediliyor; bir hata düzeltmesi (swing PR #5) geçmiş işlem listesini değiştirdi. → Planlandı: haftalık raporla birlikte işlem listelerinin anlık kopyası (değişmez kayıt).
9. **Risk limitleri eksik.** Hesap düzeyinde durdurma yalnız day trade'de var. KMN short bacağı stopsuz. Hesaplar arası tek varlık üst sınırı yok. → Gerçek para öncesi zorunlu.
10. **Maliyet ve yürütme.** Hiçbir repoda borsaya emir gönderen kod yok. Kayma sabit (%0,07–0,10), düşük likit coinlerde iyimser. Swing limit emri "dokunma = dolum". Canlı katman Aralık sonrası ayrı iş.
11. **Test süresince kural değişikliği yok** (4 repo; tek sinyal etkileyen commit swing PR #5, hata düzeltmesi).
12. **Belge uyumsuzlukları.** Trend enstrüman metni "50 hisse / 18 ETF", fiilen 32 / 4 → panelde düzeltildi. EKIP standart tablosu bayat. koni.py yalnız dev dalında.

## D. Codex denetim raporu (12 Ekim, 29 bulgu) — değerlendirme

**Kapsam farkı:** Codex, kullanıcının yerel klasörünü (`borsa çalışmam`: algotrading, price, day trade/trade_system, swing/scripts) denetledi. Bu dosyaların hiçbiri canlı botlarımızın depolarında yok (algo-sg/algo, day-trade-sg/daytrade, swing-sg/swing+trend, strateji-sg). Bulgular doğrudan bize ait değil; her hata **türü** bizim kodumuzda ayrıca arandı:

| Codex | Hata türü | Bizim kodda | Sonuç |
|---|---|---|---|
| B-02 | object dtype + `~` → olay filtresi bozulur | day-trade `fillna(False).astype(bool)` sonra `~`; algo/swing'de desen yok | temiz |
| B-04 | stop çıkışı sonrası aynı mumun açılışından yeniden giriş | algo `i = exit_i` → giriş `o[exit_i+1]`; swing/strateji/day-trade da sonraki mum | temiz |
| B-08 | açılış boşluğu stopu aşınca stop fiyatından çıkış | algo `min(stop,o[j])`, swing `o[j]`, day-trade `gap_stop`, strateji ilk mum kontrolü | temiz |
| B-24 | RSI sıfır kayıpta NaN | swing/algo/day-trade RSI `fillna(100)` | temiz |
| B-12 | kapanmamış günlük kripto mumu | swing atıyor (veri.py:54, fetch_data.py:44); **trend BTC-USD (yfinance) atmıyor** | kayıt: bot her çalışmada geçmişi yeniden oynattığı için karar ertesi çalışmada kapanmış mumla düzelir; son gün değerlemesi anlık fiyatla zaten doğru. Test ortasında değiştirilmedi |
| B-14 | negatif petrol fiyatı silinir | swing veri.py:27 `Close > 0` → CL=F 20–21 Nisan 2020 backtest dışı | kayıt: yüzde getiri motoru negatif fiyatı modelleyemez; 2026 canlı etkisi yok |
| B-23 | düşüş başlangıç sermayesini atlar | day-trade başa 0 ekliyor; panel `clip(lower=sermaye)`; swing/algo backtest ilk bar etkisi önemsiz | temiz / önemsiz |
| B-01, B-09, B-11, B-15, B-16, B-17, B-27, B-28 | defter, ortak limit, baz para, OOS, evren, test/sürüm | bizim karşılıkları zaten C bölümünde (C2, C4, C5, C9, C10, C12) | yeni bilgi yok |
| B-03, B-05, B-06, B-07, B-10, B-18–B-22, B-25, B-26, B-29 | yerel projelere özgü kod | bizde karşılığı yok | uygulanmaz |

**Sonuç:** Codex'in bulduğu kusurların hiçbiri canlı botlarımızda yeniden üretilemedi; yalnız B-12'nin trend BTC karşılığı var ve etkisi geçici. Raporun genel ilkeleri (tek defter, dondurulmuş sürüm + ileri test, ortak risk limitleri, ikinci göz kontrolü) Aralık gerçek para planı v2'nin kontrol listesine eklendi.

## E. Kurumsal çapraz denetim (12 Ekim gece) — nihai özet

Her ekip başka bir ekibin stratejisini salt okunur denetledi: strateji→algo (`algo-sg` DENETIM_CAPRAZ_ALGO.md, e30fa0e), algo→day trade (`algo-sg` DENETIM_CAPRAZ_DAYTRADE.md, e19d072), day trade→strateji (`day-trade-sg` DENETIM_CAPRAZ_STRATEJI.md, 2044105). Swing/trend ölçümleri koordinatörce (bağımsız denetçi limitte kaldı; C bölümü bu hesapları zaten kapsıyor).

| Hesap | Çoklu deneme düzeltmeli Sharpe (DSR) | Kuyruk | Rejim / evren | Aralık v2 adayı |
|---|---|---|---|---|
| Strateji | KGT 0,65–0,83 (geçmez); KMN 0,97, 50/50 0,99 (sağlam) | KMN short stopsuz; tek coin %16; en kötü hafta −%13,2 | KMN 2021'e bağımlı; KGT 2022 −%19,8; canlı spot/vadeli ve OKX fonlama farkı | KGT %40 / KMN %60; KMN tek coin ≤ %10 |
| Algo | 0,47–0,82 (≈3.600 deneme) | A en kötü gün −%17,6; B, BTC'nin en kötü 10 gününün 10'unda zararda | son 21 ay Sharpe 0,75; bugünkü 25 coin; B parametreye duyarlı | kollara ters oynaklık ağırlığı (Sharpe 1,25→1,52, DD −17,8→−10,2); B'de 24 saatte ≤3 giriş |
| Day trade | 2023-26 0,95 (sınırda); 2021-23 0,25 | günlük −%3 kuralı hiç devreye girmiyor | 2022 −%8,2; zaman içi evrenle OOS %17,9→%4,3; TRX+QNT kârın %41'i; kağıt bot sinyali geç görüp geçmişten dolduruyor (PF 1,60→1,46) | BTC 4s filtresi yerine SMA200; gerçekçi beklenti PF 1,2–1,3 |
| Swing | 0,77–0,89 | en kötü hafta −%6,4 (gerçekleşme bazlı, eksik tahmin) | OOS seçimde kullanıldı; kripto evreni bugünkü | stop ≤ %15 (önceden test edildi) |
| Trend | 0,88–0,95 | en kötü hafta −%4,4 | kollar 2023-26'ya bakılarak seçildi; ABD sepeti bugünkü mega-cap'ler | yok |

**Kurumsal sonuç:**
1. Çoklu deneme düzeltmesinden sağlam çıkanlar KMN (strateji) ve trend kolları; sınırda olanlar swing ve day trade (yalnız boğa dönemi); geçmeyenler KGT ve algo. Hiçbiri tek başına "kanıtlanmış" sayılmaz; 60 günlük kağıt test bunu değiştiremez.
2. Portföy düzeyinde eşit ağırlık en sağlam dağılım; day trade eleme adaylarının başında (algo ile 0,51 korelasyon, ayı piyasasında zarar, kağıt bot iyimser).
3. Aralık v2 önerileri değişiklik değil adaydır: her biri dondurulmuş kodla yeni bir ileri dönemde test edilmeden gerçek paraya girmez (Codex B-16 ilkesi).
4. Bu turdan sonra panel ve stratejilerde yeni optimizasyon yapılmayacak (kullanıcı kararı, 12 Ekim).
