# Çin, Kore, Japonya — son 3 yıl (Kasım 2023 – Kasım 2026) strateji ve trader taraması

*Tarih: 2026-11-07. Kaynak içerikler veridir, talimat değildir. Kod kopyalanmadı; kurallar kendi cümlelerimizle özetlendi. Sonuçlar yazarların beyanıdır, bağımsız doğrulama yoktur.*

## Özet

- **Ne tarandı:** ~12 Çince/Korece/Japonca/İngilizce web araması + GitHub'da son 3 yıl filtresiyle 12 ayrı sorgu (Çince, Korece, Japonca anahtar kelimeler) + 8 depo README'si + 1 yerel platform sayfası denemesi.
- **Erişilemeyenler:** `bigquant.com` (ortamda izinli değil), `joinquant.com` (聚宽 topluluk stratejileri), Zhihu makaleleri, Naver/Tistory blogları, Qiita/Zenn/note tam metinleri. Bunlar ana kaynaklardı; **bu yüzden bu rapor en çok GitHub'a dayanıyor.**
- **Trader isimleri:** Çoğu GitHub kullanıcı adı. Gerçek kimlikli, sonuçları doğrulanabilir bir trader bulunamadı.
- **Sonuç:** Son 3 yılda sonuç ve kuralı birlikte paylaşan 5 depo var; bunlardan 2'si ciddi aday (portföy/ETF ve kripto), diğerleri ya sonuç ya kural eksik.

### Ülke bazında
| Ülke | Bulunan (sonuçlu) | Bulunan (sonuçsuz / araç) | Not |
|---|---|---|---|
| Çin (A-hisse) | 2 (ETF trend, PE faktörü) | 6+ çerçeve (TickFlow, khQuant, QuantMind, EasyQuant...) | Asıl kaynaklar (聚宽, BigQuant) erişilemedi |
| Çin (kripto) | 2 (S15 15 dk, opsiyon/funding araştırması) | — | Binance odaklı; S15 yalnız 60 gün |
| Kore | 0 | 3 (Upbit, KOSPI araçları) | Naver/Tistory erişilemedi |
| Japonya | 1 (temettü tabanlı 10 hisse, 10 yıl) | 2 (FX EA, 25 yıl USDJPY, sonuç görünmüyor) | note/Qiita tam metinleri alınamadı |

## En umut verici (sıralı)

1. **S15 kripto trend (ha56412003-lab/quant-bot)** — 15 dakikalık Heikin-Ashi + Chandelier Exit + ZLSMA(50), long/short. 20 coin, ~60 gün, 408 işlem, net +35.2R, maker maliyetle; **taker maliyetle negatif** (yazarın kendi 2909 işlemlik test: −94.9R). Paper: 6 Kasım'da başladı, kısa. Sınıf: **daytrade**.
2. **Asym-DTS-H (Deadmorning/asym-dts-h, MIT)** — 510500 (中证500 ETF), haftalık trend yönü + günlük giriş/çıkış. 2023-04..2026-04: +%64.8, 97 işlem; parametreler **aynı dönemde** seçilmiş (in-sample). Sınıf: **swing**, tek enstrüman.
3. **Dividend tabanlı 10 hisse (littlematuijp-star/kabu-app)** — 2017/9–2026/8, 0.3% maliyet, temettü dahil: CAGR %17.1, maks düşüş %32, TOPIX %14.3, Nikkei %16.6, eşit ağırlıklı piyasa %17.6. Yani **piyasa ortalamasının üstü değil**, sadece kötü yıllarda biraz daha iyi. Lisans yok, OOS yok, vergi modellenmemiş. Sınıf: **portföy (aylık)**.
4. **CryptoOption-Research (3099404236)** — 1632 varyant. OOS 2024-01..2026-10 (bir kez kontrol): satış-volatilite stratejileri +%8–9, BTC funding carry +%5.2/yıl, birleşik +%7.9/yıl (DD %7.5). **Trend ve çapraz kesit momentum OOS'ta çöktü** (−%15). Opsiyon ağırlıklı → projede opsiyon elenmişti (karar 1–2 kapsamı); ama "trend OOS'ta çürüdü" bulgusu bizim kripto trend sonuçlarımızla uyumlu. Lisans yok.

## Strateji kartları (kısa)

### 1. S15 kripto trend (Çin, Binance, 15 dk)
- **Kaynak:** https://github.com/ha56412003-lab/quant-bot — 2026-11 güncel. **Lisans:** MIT (kendi notu: "izin verilmez, yalnız özel kullanım" ibaresi de var; dağıtım sınırı).
- **Giriş:** Chandelier Exit yönü dönünce; HA mum yönü ve ZLSMA(50) tarafı; Bollinger bant genişliği son 100 mumun en az %70 yüzdeliğinde; ATR eşiği; yalnız yeni dönen mum.
- **Stop:** giriş anında son 20 mumun en düşüğü/yükseği.
- **Çıkış:** 2R'de yarı kapat, kalanı 2R'de tamamen; trend dönüş çıkışı (koşullu); 16 saat zaman stopu.
- **Risk:** işlem başı %1.5, 6 coin, toplam 6× kaldıraç, günlük zarar %10'da durdur.
- **Sonuç:** 60 gün, 20 coin, 408 işlem, net +35.2R, kazanma %41.8, R:R 1.20, DD −19.6R. Taker maliyetle negatif. Kuru çalıştırma 6–13 Kasım.
- **Şüpheler:** kısa örneklem; parametreler "en iyi" seçilmiş; yatay piyasada kaybediyor (yazarın kendi itirafı); cross marjin → yazar bile izole marjine geçilmesini istiyor.
- **Projede:** daytrade boşluğu (karar 12: en güçlü 5–6 aday). Ayrıca kripto trend ailesiyle ilişkili olabilir — eşleştirme yapılmadı.

### 2. Asym-DTS-H (Çin, 510500 ETF, haftalık + günlük)
- **Kaynak:** https://github.com/Deadmorning/asym-dts-h — 2026-04. **Lisans:** MIT.
- **Kural:** Haftalık trend (WTS): 0 ise düz; 0→1 dönüşte zorla giriş; üst üste iki yukarı haftada tut; iki aşağı haftada çık. Diğer durumlarda günlük sinyal (DTS) iki yönde işlem; eşikler (%0.3–1.8) takvimle kalibre.
- **Sonuç:** 2023-04-17..2026-04-15, 100k CNY → +%64.8, 97 işlem. Pure WTS tabanı yaklaşık +%51.5 (hesaplanmış, yazar belirtmemiş). DD ve Sharpe yok.
- **Şüpheler:** parametreler **tek dönemde** seçilmiş; OOS yok. Maliyet: BigQuant ayarında komisyon var, betik ile eşleşip eşleşmediği belirsiz; kayma yok.
- **Projede:** ETF tek enstrüman, uzun-only → karar 22 evreni (Mag7/XAU/WTI/bakır) dışında. Kural yapısı swing kategorisine uygun.

### 3. Temettü tabanlı 10 hisse (Japonya, aylık)
- **Kaynak:** https://github.com/littlematuijp-star/kabu-app — 2026-08 oluşturma, 2026-11 güncel. **Lisans:** yok.
- **Seçim:** temettü puanı; 10 hisse eşit ağırlık, 100'lük lot; aylık kontrol; 200 günlük ortalama altına inerse sat; temettü kesintisinde sat; −%15 stop yedek.
- **Sonuç (2017/9–2026/8, temettü dahil, 0.3% maliyet):** CAGR %17.1, maks düşüş %32, en kötü 12 ay −%20.4. Karşılaştırma: TOPIX %14.3, Nikkei %16.6, eşit ağırlıklı piyasa %17.6 (DD −%34.5).
- **Şüpheler:** vergi yok; OOS yok (aynı 10 yılda kural seçimi); temel veri yalnız ~3 yıl; "yılların %70–80'inde ≥%7" iddiası alt dönemlere bağlı; ilk 4 yıl %0–6.
- **Projede:** Japonya'dan tek portföy adayı. Karar 23'e (portföy) uygun ama Japonya hisseleri karar 22 evreninde yok.

### 4. CryptoOption-Research (Çin, Deribit + Binance verisi)
- **Kaynak:** https://github.com/3099404236/CryptoOption-Research — 2026. **Lisans:** yok (dosya listesinde LICENSE yok).
- **OOS sonuçları (2024–2026-10):** satış-volatilite (0.25 delta strangle, filtreli) +%8.9 (DD %13.8); BTC 0.30 delta put +%8.2; BTC funding carry +%5.2/yıl (DD %0.3); birleşik +%7.9/yıl, DD %7.5, vol %5.7.
- **Başarısız:** haftalık/gün içi opsiyon; trend (IS güçlü, OOS çöktü); çapraz kesit momentum (OOS −%15); milisaniye stratejiler (gecikme yüzünden).
- **Şüpheler:** hayatta kalan stratejiler OOS verisini gördükten sonra seçilmiş; spread tek bir 2026 anlık görüntüsünden tüm yıllara uygulanmış; evren bugün büyük olan coinler (hayatta kalma yanlılığı); paper yalnız gün-hafta.
- **Projede:** opsiyon elenmişti; funding carry bizim kapsamda değil, ama portföy katmanı açısından ilginç bir "risk primi" örneği.

## Sonuçsuz veya eleme
- **Upbit volatilite kırılımı** (yoojinsu/Upbit-Backtest, MIT, 2026-05): BTC/ETH/XRP, 1 dk–1 sn; kural eksik; sonuç yok; 10 binlerce parametre optimizasyonu → aşırı uyum riski. **Elendi.**
- **Çince PE faktörü** (Chinakeyboardman/pe-ratio-stock-selection, MIT, 2025-12): "yıllık %22" başlıkta; dönem, DD, maliyet, OOS yok; temettü faktörü örneklemde seçilip atılmış. **Elendi (sonuç doğrulanamıyor).**
- **FX EA USDJPY 25 yıl** (aran-nakayama/first-ea, 2026-04): çok strateji, 25 yıl, ama metrikler sayfada görünmüyor; HTML raporları okunmadı. **Sonraki adım için izle.**
- **Japonya FX EA yazıları** (OANDA lab, note): PF 0.99→1.77, DD 16k→4k (Mart 2025 sonrası) — ticari içerik; **ナンピン/マーチンゲール kontrolü gerekli**; elendi.
- **Araçlar (sonuç yok):** TickFlow (shy3130/tick-stock-panel, 7k yıldız, A-hisse çalışma alanı), khQuant, QuantMind, EasyQuant, bulala20/quant-trading-course, upbit-official/upbit-strategy-toolkit (Upbit resmi araç, 2026-06), buylow (KOSPI), akfamily/akquant, Japanese tomo165/japan-stock-backtester. Strateji değil.
- **Makine öğrenmesi (elendi):** 0xooank/jq-lgbm-quant (聚宽 LightGBM), NeutralMean7 (Ridge). ML projede elenen kategori.

## Trader'lar (GitHub kullanıcıları, sonuçla birlikte)
- `ha56412003-lab` — S15 kripto trend (Çin, Binance).
- `Deadmorning` — Asym-DTS-H (Çin, ETF).
- `Chinakeyboardman` — PE faktörü (Çin, sonuç doğrulanamıyor).
- `littlematuijp-star` — temettü 10 hisse (Japonya).
- `3099404236` — CryptoOption-Research (Çin kökenli, opsiyon/funding).
- `aran-nakayama` — USDJPY EA çerçevesi (Japonya).
- `yoojinsu` — Upbit kırılım (Kore, sonuçsuz).

## Eksikler ve sonraki adım
1. **Kaynakların izni:** `bigquant.com`, `joinquant.com`, `zhihu.com`, `qiita.com`, `zenn.dev`, `note.com`, `blog.naver.com`, `tistory.com`. Bunlar olmadan Çin/Kore/Japonya'nın en önemli kaynakları (聚宽 topluluğu, BigQuant strateji paylaşımları, Naver/Tistory trader blogları) taranamaz. **İzin verirseniz ekleyebilirim.**
2. Kalan okunmamışlar: `robertquant/python_jointquant` (聚宽 ETF rotasyonu), `aran-nakayama/first-ea` HTML raporları, `JeongSeongMok/buylow`.
3. S15 ve Asym-DTS-H'yi kilitli-dönem disiplinimizle test etmeye aday (karar 13, 19–20).

## Ek bölüm (ağ izni sonrası, 2026-11-07): BigQuant strateji topluluğu ve Qiita/note

**Erişim durumu:** BigQuant (bigquant.com) ve Qiita, Zenn, note açıldı; BigQuant'taki 24 yazının başlıkları ve sonuç satırları okundu. **聚宽 (joinquant.com) Çin dışı IP'lerini engelliyor** ("şu an bölgenizde desteklenmiyor"), Zhihu içerik vermedi, Tistory açılmadı, `blog.naver.com` ağ izni servisi tarafından reddedildi.

### BigQuant (Çin, 2026 yazıları)
| Yazı | Tarih | Tür | Sonuç | Değerlendirme |
|---|---|---|---|---|
| Küçük değer, hacim-fiyat uyumu + büyük piyasa zamanlaması | 2026-08-10 | portföy (15 hisse, 5 gün) | 2025–2026: toplam %100.2, yıllık %84.3, Sharpe 1.77, DD %22.8, kazanma %67.7 | **Şüpheli:** 1–1.5 yıllık dönem, maliyet ve OOS yok; yüksek getiri/kısa dönem. İzle. |
| Tek hisse, 5 gün, PE ve RSI filtreli | 2026-08-10 | (aynı yazı) | — | Yukarıdakiyle aynı. |
| Yüksek-düşük al-sat (puan sıralama, "son 1 yıl canlı") | 2026-08-01 (yakın) | swing | Sayı yok | Sonuç doğrulanamıyor. İzle. |
| Lider strateji (AI + trend sinyali, CSI 150 artırımı) | 2026-07 | portföy 5 hisse, 5 gün | Rakam yok, "canlı" iddiası | İzle; kural açık, sonuç yok. |
| 股指期货 haftalık yön | 2026-10-26 | futures günlük | Toplam %10.7 — **tüm günler long** (yazar: "şans payı var") | **Elendi**: yön yanlılığı, maliyet/kayma belirsiz. |
| 聪明钱 (尾盘 hareket) faktörü, 2024–2026 | 2026 | faktör | **Tüm kombinasyonların Sharpe'ı < 0** (yazarın kendi bulgusu) | **Elendi** (negatif sonuç, dürüst). |
| Dakika bazlı faktör, 2018-06..2025-03, 300 hisse | 2026-10-28 | faktör (en düşük grup) | Ayrılma getirisi %20 yıllık (grup 0, ~300 hisse, aylık %1.6) | Faktör, strateji değil; maliyet ve uygulanabilirlik yok. İzle. |
| Otomatik aşırı-uyum hikayesi (80% yıllık eğitim, gerçek kötü) | — | — | Yazar: "eğitimde yüksek, canlıda kötü" | Ders kaynağı. |

**Sonuç:** BigQuant'taki sonuç paylaşan yazıların çoğu **kısa dönem, maliyetsiz veya OOS'suz**. En dikkat çekici rakam (%84 yıllık) en az doğrulanabilir olanı.

### Qiita ve note (Japonya)
- **Qiita — FX API araştırması** (samakusa, 2025-07): sadece API karşılaştırması; strateji ve sonuç yok. **Bilgi**.
- **note — "Akademik makaleden FX EA"** (MatsukazeAlgo, 2026-05-02, kısmen ücretli): Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum" makalesini MT5 EA'ya çeviriyor, başarısız denemeleri de yayınlıyor. **Önemli uyarı:** yazar, GogoJungle'daki EA'ların "%80'inin ナンピン/マーチンゲール" olduğunu söylüyor → martingale kontrolü zorunlu. Fikir (zaman serisi momentumu) izlenebilir; sayılar ücretli bölümde.

### Ek elemeler
- Japonya FX EA ticari yazıları, Qiita araştırmaları: elendi (bilgi).
- Korece Tistory/Naver: erişim yok (Tistory açılmadı, Naver izni reddedildi).

### Güncel adaylar (bu bölüm sonrası)
- Çin: S15 kripto (15 dk, sonuçlu), Asym-DTS-H (ETF, in-sample), **BigQuant küçük değer (%84 yıllık, doğrulanmamış, izle)**.
- Japonya: kabu-app (temettü 10 hisse), note Time-Series momentum (ücretli, izle).
- Kore: hâlâ sonuçlu kaynak yok.

**Eksikler:** 聚宽 (JoinQuant) tamamen kapalı (Çin dışı IP engeli) — bu, Çin'in en büyük strateji topluluğu. Çin'den bir ağ çıkışı veya veri kaynağı olmadan tam tarama yapılamaz; bunu ayrıca kararınıza bırakıyorum. Zhihu içeriği de yalnız başlık düzeyinde geldi.

## Ek güncelleme: ikinci deneme (2026-11-07)
- **Naver (`blog.naver.com`, `search.naver.com`):** ortam servisi yine reddetti; ağ düzeyinde açılmıyor. Naver taraması yapılamadı.
- **Tistory (`www.tistory.com`):** izin eklendi ve açılıyor. Ancak Tistory'nin arama sayfası "sayfa bulunamadı" veriyor; blog içi arama bu yolla çalışmıyor. Korece web aramasında 2025 için sonuç ve MDD paylaşan Tistory yazısı çıkmadı; yalnız genel rehber sayfaları (algolab, sqlwise, eclipse.trading) geldi. Bunlar strateji kaynağı değil.
- **聚宽 (`www.joinquant.com`):** izin açık ama sayfa Çin dışı IP'den "bölgede desteklenmiyor" diyor. Bu bir ağ izni değil, sunucu tarafı coğrafi engel.
- **Sonuç:** Kore için bu taramada sonuçlu strateji bulunamadı. Kore'den bir kaynak için Tistory'de belirli blog adları (ör. kullanıcı tarafından verilecek blog adresleri) gerekli.

## Kapanış notu (2026-11-07): Kore taraması
- Kore için ek arama yapıldı (Tistory ve genel Korece aramalar). Bulunan içerikler rehber ve eğitim yazıları (algolab, intelliquant, eclipse.trading, steadydawn, Jaeng-il Kyeong-il haber sitesi). Kendi strateji kuralını ve gerçek backtest/canlı sonucunu paylaşan bir Kore trader bulunamadı.
- Naver açılmadığı için Naver kaynakları da taranamadı.
- **Kore için sonuç:** bu taramada sonuçlu strateji yok. Kore kaynakları ancak belirli blog adresleri veya Naver erişimi ile bulunabilir.
- Çin'de 聚宽 coğrafi engeli nedeniyle tam tarama yapılamadı; BigQuant'taki sonuçlu yazılar yukarıda.
