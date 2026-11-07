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
