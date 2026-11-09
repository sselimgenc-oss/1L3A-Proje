## FAZ 12 — HGT: haftalık yön / günlük işlem (20 Str. #5 uyarlaması) — TAMAMLANDI, BAŞARISIZ (2026-10-10). Rapor: RAPOR_HGT.md
Kullanıcı (2026-10-10, her şeye onay): "1 hafta yön 1 gün işlem" ayrı strateji. backtest/hgt.py, 52 varyant (sonuclar/hgt/izgara*.csv).
Sonuç: IS 2020-23 en iyi Sh 1.39 (kâr 2020-21 boğasından), OOS 2024-26 tüm varyantlarda Sh <= 0.25 (çoğu negatif), rastgele girişle aynı. Kağıt bota eklenmedi.
Not: haftalık rutin yeni oturumda repo erişimi olmadığı için hata verdi -> silindi, bu oturuma bağlı yenisi kuruldu (trig_01XhPohEUR2wmDmNPEeXdAWv).

## FAZ 11 — Hisse/emtia testi (Mag7, BIST, altın, Brent) — DURDURULDU (kullanıcı kararı, 2026-10-09). Rapor: RAPOR_HISSE.md
Sonuç: KGT Mag7'de umut verici (%1 risk: CAGR 20, DD 16, Sh 1.43; 3 yıl, kısa örneklem), BIST zayıf, emtia düşük getirili;
KMN hisse/emtiada çalışmıyor (küçük evren). Kullanıcıyla anlaşma: kripto kağıt botuna odaklan, 2 ay sonra gerekirse Mag7 KGT eklenebilir.

## FAZ 10 — Kağıt al-sat botu (2 ay, 7/24, 10.000$) (DEVAM EDİYOR) — kullanıcı onaylı, BEKLEME YAPMA
Kararlar (kullanıcı 2026-10-09): GitHub Actions + Binance spot verisi (data-api.binance.vision; Binance fapi ABD'den 451),
PR açılacak kullanıcı main'e birleştirecek, bildirim: günlük GitHub issue özeti + haftalık Claude değerlendirmesi (benim seçimim).
Bütçe: 10.000$ = KGT 5.000$ (6 alt portföy) + KMN 5.000$ (2 alt portföy, 7 gün arayla). Süre 2 ay, sonra kendiliğinden durur.
- [x] K1. canli/ paketi: veri (spot 1S mum önbelleği, 1000X eşleme, S3 aylık evren, OKX fonlama), artımlı KGT motoru (backtest motoru ile aynı kurallar, 1 dk ile mum içi çözüm), KMN defterleri
- [x] K2. Geçmiş veride yeniden oynatma doğrulaması: kağıt motoru = backtest motoru (aynı dönem işlemleri)
- [x] K3. .github/workflows/kagit.yml (saatlik, kaçırılan saatleri telafi eder, durum ayrı dalda: kagit-durum), günlük issue özeti
- [x] K4. Dalda canlı veriyle deneme (GitHub, başarılı), doğrulama: motor 221/221, 2 aylık oynatma KGT 90/90, toplam fark %0.3. PR açıldı -> kullanıcı birleştirecek
- [x] K5. PR https://github.com/sselimgenc-oss/strateji-sg/pull/1 açıldı (kullanıcı birleştirecek; PR takipte). Haftalık Claude rutini kuruldu (trig_01NYzWBMPH4uVrSGGHq9mJQd, Pazartesi 08:52 İstanbul). Birleştirince: ilk çalıştırmayı (kagit-durum dalı + issue) kontrol et.

## FAZ 9 — Derin denetim: bug / mükerrerlik / çelişki + PDF uygunluğu + optimizasyon — TAMAMLANDI (2026-10-09). Rapor: DENETIM.md
Kapsam: KGT v3 (strateji.py, kripto_strateji.py, kripto_motor.py, kripto_final.py, kripto_sinyal.py, kripto_evren.py, kripto_veri.py) ve KMN (momentum.py, momentum_sinyal.py).
- [x] D1. Denetim ajanları: KGT kod, KMN kod, PDF uygunluğu; kendi kontrollerim (evren point-in-time, motor muhasebesi)
- [x] D2. Bulguları doğrula (sentetik testler), düzelt
- [x] D3. Sonuçları yeniden üret (KGT topluluk, KMN, birleşim), optimizasyon
- [x] D4. DENETIM.md raporu, SONUC/RAPOR güncelle, push, kısa özet

## FAZ 8 — Strateji 2: KGT'yi tamamlayan ikinci strateji — TAMAMLANDI (2026-10-09). Rapor: RAPOR_S2.md
Kullanıcı (2026-10-09): KGT v3 kesin ("cebe at"). İkinci strateji: ortalamaya dönüş + piyasa nötr kesitsel momentum paralel test, KGT'yi en iyi tamamlayan seçilir.
Seçim ölçütü: WR >= %50 tercihen (min %40), OOS PF >= 1.3, KGT ile korelasyon < 0.3, KGT+S2 birleşiminde düşüş azalırken getiri korunmalı. Long + short.
- [x] M1. Dokümanlardan kurallar (151S ortalamaya dönüş/momentum, 51S RSI/Bollinger, Brooks TR aralık kuralları) — ajan
- [x] M2. backtest/momentum.py: haftalık kesitsel momentum (piyasa nötr / long-only), günlük getiri, masraf+fonlama
- [x] M3. backtest/ortdon.py: ortalamaya dönüş (rejim filtresi + RSI/Bollinger + ortalamaya çıkış + zaman stopu), 4S/1S
- [x] M4. Izgara + sağlamlık + KGT ile korelasyon/birleşim
- [x] M5. Rapor RAPOR_S2.md, SONUC.md, push, kısa özet
SONUÇ: ortalamaya dönüş (4S/1G/IBS/kesitsel dönüş) BAŞARISIZ. KMN (piyasa nötr, risk skoru, N30 L14 K5 H14 1/σ, >=90 gün): CAGR 43.5 DD 16.3 Sh 1.69,
  OOS Sh 1.88, kor 0.20, rastgele %100, maliyet x3 Sh 1.44; WF Sh 0.60 (iyimserlik uyarısı). KGT %50 + KMN %50: CAGR 39.7 DD 15.0 Sh 1.90.
  Canlı betik momentum_sinyal.py 25/25 eşleşti.

## FAZ 7 — Kullanıcının EMA 8/21/55 + hacim + mum + S/D + trend çizgisi + pullback/breakout stratejisi — TAMAMLANDI (2026-10-09). Rapor: RAPOR_EPA.md
KGT v3 kenarda ("heybede"). Analiz: ANALIZ_EMA_STRATEJI.md (kitap alıntıları + eksikler + test edilebilir "EPA" kural önerisi).
- [x] A1. 7 kitapta EMA/hacim, mum formasyonları, S/D-trend çizgisi-pullback/breakout taraması
Kullanıcı (2026-10-09): "Tamam o zaman her şeye onayım var" -> EPA'yı kodla ve test et. BEKLEME YAPMA.
- [x] A2. backtest/epa.py: 4S mumlar (4 hizalama: 0/1/2/3 saat kaydırma, ortalama), hacim (quote_volume), bağlam (1G EMA 8/21/55 + yatay filtre),
      Kurulum A pullback (4S EMA 8>21>55, 8-21 bölgesine geri çekilme, mum kalitesi: yok/hammer|engulfing/Brooks, konum: yok/EMA21/destek/trend çizgisi),
      Kurulum B breakout (sıkışma, kırılım mumu, hacim çarpanı). Çıkış: 4S EMA21 altında 2 kapanış / EMA8<21 / 4S EMA21-50; kısmi kâr 1R.
- [x] A3. Izgara (her bileşen aç/kapa) -> sonuclar/epa/izgara_A.pkl, izgara_B.pkl
- [x] A4. Sağlamlık (komşu, maliyet x2, rastgele, WF) + KGT ile korelasyon/birleşim
- [x] A5. RAPOR_EPA.md, SONUC.md güncelle, push, kullanıcıya kısa özet
SONUÇ: EPA-B (1G EMA8/21/55 + 4S 18 mum < 7 ATR sıkışma kırılımı + hacim>=2x, EMA8<21 çıkış, 1R %15): WR 48.9 PF 2.03 CAGR 17.3 DD 17.7 Sh 1.31
  (%0.5 risk), OOS Sh 0.96, 4/4 hizalama kârlı, maliyet x3 Sh 1.17, rastgele %100. EPA-A (pullback+mum) başarısız. KGT ile kor 0.77; %30 EPA-B birleşim Sh 1.32.

## FAZ 6 — Düşüşü azaltma + PA metinlerini ayrıntılı okuma — TAMAMLANDI (2026-10-09). Sonuç: SONUC.md, RAPOR_KRIPTO.md v3
Kullanıcı: "%0.25 risk ve max 3 pozisyonu test et, karar sende; sonuç tatmin etmedi, PA evraklarını detaylı oku, kaçırdığın hususlar var".
- [x] D1. Risk ölçekleme doğrusal (Sharpe ~1.26 sabit): %0.25->CAGR 22 DD 22; %0.35->30/29; %0.5->40/38. 3 poz daha kötü (Calmar 0.87). 5 poz kalıyor.
- [x] D2. Brooks: salınım dibi iz süren stop (TR b29), ikinci girişler (Trends b10), doruk sonrası girme (b18), kârdaki pozisyona ekleme (TR b31), 20 boşluk çubuğu MA girişi (TR b13-14)
- [x] D3a. d3 (iz stop k2/k3, doruk filtresi, günde 2 giriş): hiçbiri iyileştirmedi. d4 piramit (slot 2/3, 1R/2R): Calmar düşüyor -> yok.
      d5 bağlam filtreleri (N gün zirvesi, NR4/NR7, iç gün, haftalık trend): kötü/kararsız. TEK İYİLEŞME: günlük kapanış > EMA20
      (WR 45.6 PF 2.01 DD 35.8 Cal 1.08 OOS Sh 1.34; EMA10-30 komşuları tutarlı, maliyet x2 ve evren 20'de de tabandan iyi) -> v3'e alındı.
      d6 kırılım geri çekilmesi: 4 varyant tabandan kötü (tek başına Sh 0.76-0.82, tabana ek 1.23) -> durduruldu, yok.
- [x] Kod: strateji.gunluk_kirilim htf_ust, kripto_final GIRIS htf_ust=1, KGT risk %0.4, topluluk çıktıları *_v3*; kripto_sinyal güncellendi.
- [x] D3. v3 topluluk (%0.4): WR 45.4 PF 2.00 CAGR 32.9 DD 30.6 Sh 1.26 Cal 1.08; OOS CAGR 28.5 DD 18.9 Sh 1.31. Rastgele %97/%97/%85. MC 1y zarar %16.
- [x] D4. Rapor (RAPOR_KRIPTO v3, SONUC), sinyal betiği doğrulandı (20/20 + 20/20), push

## FAZ 5 — Al Brooks kitaplarıyla güçlendirme — TAMAMLANDI (2026-10-09). Sonuç: SONUC.md, RAPOR_KRIPTO.md v2
Hedef (kullanıcı 2026-10-09): kazanma oranı >= %40 şartıyla kârlılığı maksimize et. Yeni PDF'ler (main'den merge): Al Brooks
Price Action Trends (439 s.), Trading Ranges (572 s.), En Başarılı 10 PA Modeli (24 s.) -> metinler/.
Mevcut en sağlam aday: KGT (WF Sharpe 0.99). SKA hizalamaya duyarlı -> bırakıldı.
Sağlamlık şartları (tümü): IS/OOS, mum hizalama / gün başı kaydırma ortalaması, komşu parametre, maliyet x2, rastgele giriş, walk-forward.
- [x] B1. Brooks kurallarını çıkar (10 model özeti + Trends: always-in, H1/H2, 20 EMA geri çekilme, kırılım geri çekilmesi, wedge, başarısız kırılım, ölçülü hareket, stop/hedef)
- [x] B2. H1/H2 dedektörü (pa.py, test edildi), brooks.py (trend gücü, brooks2 çıkışı), KGT+brooks2 çıkış testi
- [x] B3a. Brooks H1/H2 4S (4 hizalama): BAŞARISIZ (OOS PF ~0.5). KGT ev=15 tp1R/0.25 (6 gün başı ort.): WR %46.5 PF 1.86 CAGR %44.6 DD %56 Sh 1.16, OOS CAGR %32.7 DD %28 Sh 1.07 = EN İYİ ADAY.
- [x] B3b. kgt2.py: Brooks çıkışı/kırılım mumu filtresi İYİLEŞTİRMEDİ. En iyi: ev15 tp1R %15 (WR 44.7 PF 1.99 CAGR 48.7 DD 58 Sh 1.19; %0.5 risk: CAGR 39.7 DD 38 Sh 1.27). WF(WR>=40 adaylar) CAGR 28.9. Kazançların %74'ü <0.3R (kısmi kâr). Maliyet x2 WR 38.
      eski: (KGT + brooks2 çıkış, kırılım mumu kalitesi, ev 15/20, max_poz) -> sonuclar/brooks/kgt2.pkl
      Önceki not: brooks ızgarası 4h(4 hizalama)+1h -> sonuclar/brooks/izgara_*.pkl ; KGT+brooks çıkış -> sonuclar/brooks/kgt_brooks.pkl
- [x] B3. Izgara + sağlamlık
- [x] B4. KGT v2 topluluk (6 gün başı, ev15, tp1R %15, %0.5 risk): WR 44.4 PF 1.95 CAGR 39.7 DD 38 Sh 1.27; OOS CAGR 32.4 DD 22. Nihai seçim (WR>=40, max kâr), rapor RAPOR_BROOKS.md, sinyal betiği, commit/push

## FAZ 4 — SKA'yı güçlendirme — TAMAMLANDI (2026-10-09)
Parametre avı YOK; zayıf noktalara çalışılıyor:
- [x] G1. Çoklu zaman dilimi + HİZALAMA TESTİ: SKA yalnız 4S+00:00 hizalamasında güçlü; +1/+2 saat kaydırınca bozuluyor (şans payı büyük).
      Gerçekçi SKA (4 hizalama ort.) CAGR %12.9 DD %21. KGT gün-başı kaydırmaya dayanıklı (6/6 kârlı), ort. CAGR %28 DD %48.
      %50/%50 birleşim CAGR %21.3 DD %34 Sharpe 1.01. Veriler: sonuclar/pa/hizalama_getiri.pkl. RAPOR_PA.md Bölüm 8.
- [x] G2. SKA + KGT birleşimi (korelasyon 0.55) -> yukarıda
- [x] G3. Koşullu short / BTC rejim filtresi: 2022'yi iyileştiriyor ama OOS'u bozuyor, Sharpe her kaydırmada düşüyor -> long-only kalıyor.
- [x] G4. Walk-forward 2021-2026/09: KGT CAGR %38.4 DD %64 Sharpe 0.99 (seçim tutarlı: tp yok, evren 15); SKA CAGR %4.2 Sharpe 0.36 (kararsız) -> SKA bırakıldı.
- [x] G5. RAPOR_PA.md Bölüm 8-9 eklendi.
Kullanıcıdan istenen (opsiyonel): Galen Woods Cilt 1-2 (piyasa eğilimi / trend çizgisi tanımı). Gelirse eğilim filtresi yazarın tanımıyla değiştirilecek.

## FAZ 3 — Price action stratejisi — TAMAMLANDI (2026-10-09), rapor: RAPOR_PA.md
İstek (2026-10-09): KGT kenarda; dokümanlardan (öncelik Galen Woods PA kitabı + 51 Str. Bölüm 7) price action tabanlı yeni strateji.
Çerçeve: kripto (Binance USDT-M, ilk 10-20 coin, 2020-2026/09), 1G+4S bağlam, 1S tetik; long/short ikisi de test; aynı sağlamlık ölçütleri
(OOS 2024+ PF>=1.3, WR>=%45 tercihen, komşu parametre, maliyet x2, rastgele giriş kıyası).
- SONUÇ: SKA (Galen CBF, 4S, ilk 20 coin, long). Tüm WR %54 PF 3.18 CAGR %25 DD %22; OOS WR %55 PF 3.44 DD %18.
  Rastgele girişlerin %97-100'ünden iyi; 19 komşu varyantın hepsi kârlı; kâr az sayıda büyük trende bağlı (XRP 11/2024).
### Adımlar
- [x] P1. Galen Woods kurulum kurallarını çıkar (metinler/), 51 Str. Bölüm 7
- [x] P2. Price action mum/yapı fonksiyonları (backtest/pa.py): swing, trend çubuğu, pin bar, sıkışıklık, geri çekilme bacakları
- [x] P3. Kurulum sinyalleri + portföy backtest, ızgara (ÇALIŞIYOR: sonuclar/pa/izgara_4h.pkl, izgara_1h.pkl)
      Not: 1S kurulumları masraf yüzünden zayıf (TBF/WPB PF 0.7-0.99); 4S kurulum + 1G eğilim de test ediliyor.
- [x] P4. Sağlamlık + rapor (RAPOR_PA.md), sinyal betiği

# DURUM (otomatik ilerleme kaydı)

## FAZ 2 — Kripto trend stratejisi — TAMAMLANDI (2026-10-09), rapor: RAPOR_KRIPTO.md
Kullanıcı onayları (2026-10-08): ana ölçüt PF + OOS istikrarı (%45 WR kısmi kâr al ile ayrıca bakılır),
Binance USDT-M vadeli, kaldıraçsız risk bazlı boyut, hacme göre ilk 30-50 coin (point-in-time evren), long/short.
Yapı: 1G + 4S yön, 1S giriş, trendi sür (gün sonu kapanış yok). Fonlama + komisyon + kayma dahil.

Sağlamlık ölçütleri: tek parametre seti tüm coinlerde; OOS portföy PF >= 1.3; coinlerin >= %60'ında kârlı;
2022 ayı piyasasında felaket yok; komşu parametrelerin çoğu kârlı; long-only vs long/short ve BTC al-tut kıyası.

Veri: data.binance.vision engelli; aynı içerik S3 origin'den (s3-ap-northeast-1.amazonaws.com/data.binance.vision) çekiliyor.

### Notlar (2026-10-09)
- 311 coin (evrene giren tüm semboller, delist dahil, hisse/ETF/emtia tokenleri hariç), 1s mum + fonlama, 2020-01 -> 2026-09.
- İndirme: S3 origin, curl xargs -P8 (python requests yavaştı). Önbellek: data/kripto/ham.
- Motor sentetik testlerle doğrulandı; özsermaye = 1 + Σ işlem PnL kimliği tutuyor.
- İlk koşu: kırılım/geri çekilme PF(R) ~1.1, WR ~%30, ama portföy DD %70-89 (altcoin korelasyonu). OOS (2024+) zayıf.
- K5 ızgarası çalışıyor: sonuclar/kripto/izgara.pkl (BTC rejim filtresi eklendi).

- K5 SONUÇ (2026-10-09): Saf 1S trend girişleri (geri çekilme/kırılım) OOS'ta sağlam değil (576+1120 kombinasyon).
  ADAY: GPK girişi (dar CPR + R1 kırılımı + günlük EMA10/20 trend, 1S) + 4S EMA21/50 trend dönüşünde çıkış, ilk 10 coin,
  long-only, max 5 poz, %1 risk. Saf: IS PF 2.03 / OOS 1.58, WR %23, OOS CAGR %30, DD %31.
  Kısmi (1R'de 1/3 + BE): IS PF 1.60 / OOS 1.49, WR %46/%47, OOS CAGR %18.8, DD %29.
  Komşu parametreler OOS PF 1.34-1.58; maliyet x2 PF 1.47; günlük filtre şart; short zarar ettiriyor.
  UYARI: OOS birden çok kez incelendi (seçim yanlılığı) -> ileri test gerekli.
  >> KULLANICI: 'her şeye onay' -> B varyantı (1R'de 1/3 + BE), long-only seçildi. BEKLEME YAPMA.
  Sıradaki: K6a nihai modül (kripto_final.py), K6b rastgele giriş kıyası, K6c Monte Carlo, K6d sinyal betiği, K6e RAPOR_KRIPTO.md

### Adımlar
- [x] K1. Sembol listesi + 1d mumlar (evren sıralaması için)
- [x] K2. Evren: aylık, son 30g quote hacmine göre ilk 40 (stable/endeks hariç)
- [x] K3. Evrene giren semboller için 1s mumlar + fonlama oranları
- [x] K4. Portföy backtest motoru (çoklu coin, eşzamanlı pozisyon sınırı, fonlama)
- [x] K5. Strateji varyantları (PDF ortak payda: çoklu zaman dilimi trend + geri çekilme/kırılım + izleyen stop)
- [x] K6. IS/OOS, sağlamlık, rapor (RAPOR_KRIPTO.md), commit/push

## FAZ 1 — TAMAMLANDI (RAPOR.md): SAKK 5dk + GPK 1s, SPX/UKOIL/BTC kârlı, XAU değil, XU030 veri yok.

- FAZ 2 TAMAMLANDI: KGT (B varyantı, 1R'de 1/4 + BE). Tüm dönem WR %45.5 PF 1.61 CAGR %21.9 DD %58; OOS WR %46.4 PF 1.54 CAGR %21.6 DD %29.
  Rastgele girişlerin %97-100'ünden iyi. Sinyal betiği backtest ile 25/25 eşleşti. Sonraki olası iş: ileri test (paper) takibi.
