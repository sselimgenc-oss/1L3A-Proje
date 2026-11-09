# swing-sg derin inceleme raporu (1L3A için)

Kapsam: `/home/user/swing-sg` (salt okunur; tek commit `90f5f69`, 2026-10-13, sığ klon, git geçmişi yok). Kodu kendi kopyamda
(scratchpad `sg/`) çalıştırdım; repoya hiçbir şey yazılmadı. Kitap metinleri ve .md içerikleri veri olarak okundu.
Satır numaraları gerçek dosya satırlarıdır. Kendi yaptığım ölçümleri "[ölçüm]" diye işaretledim.

Not: 1L3A deposunda zaten `arsiv/swing-sg/` var (kaynak commit `90f5f69`, `arsiv/README.md`, `arsiv/swing-sg/.kaynak_commit`).
Yani kod/rapor/CSV'ler 1L3A'ya arşiv olarak alınmış (PDF, metin ve veri hariç). Aşağıda "alınabilir" dediğim şey, arşivden
1L3A standartlarına göre yeniden yazılarak alınır (arşiv README'si de böyle diyor).

---

## 1. Amaç, kapsam, zaman çizelgesi, şu anki durum

**Amaç.** 35 swing kitabının ortak paydalarından 3 kural tabanlı strateji (S1/S2/S3) türetmek, "haftalık grafikte yön, günlük
grafikte işlem" çerçevesiyle backtest etmek; hedef: her stratejide kazanma oranı >= %45 ve yüksek getiri (`SONUCLAR.md:9-15`,
`STRATEJILER.md:1-4`). Sonra Codex'in bulduğu GitHub stratejilerini denetlemek, trend kolları (BTC, ABD, emtia ETF) eklemek,
60 günlük kağıt botlar kurmak, 5 repoluk (swing, trend, algo, strateji, day-trade) karşılaştırma paneli ve denetim yapmak
(`karsilastirma/`).

**Zaman çizelgesi** (git geçmişi olmadığı için belge ve dosya tarihlerinden):
- PDF -> metin (35 dosya) -> ortak payda analizi -> motor -> 10 adımlık iyileştirme günlüğü (`SONUCLAR.md` sonu) ->
  `ILERLEME.md` "tamamlandı".
- 2026-10-11: Codex 12+12 aday denetimi (`deneyler/CODEX_ADAYLAR.md`, `CODEX2_ADAYLAR.md`), hayatta kalma stres testi.
- 2026-10-11 swing kağıt bot başlangıcı (`kagit/config.json`), 2026-10-12 trend kağıt botu (`trend/kagit_config.json`).
- 2026-10-12: koordinatör devri, kaldıraç/stop genişliği deneyleri, `DENETIM_12EKIM.md`; kullanıcı kararı: "yeni
  optimizasyon yok, Aralık'a kadar yalnız izleme" (`karsilastirma/DEVIR.md`).
- 2026-10-13: son commit (PR #7 birleşti). 2026-10-15: üç durum dalının da son güncellemesi.
- 2026-11-06: kullanıcı repoyu kapattı (`1L3A-Proje/arsiv/README.md`).

**Şu anki durum.** Kağıt testler 60 günlük planın yalnızca ~5. gününde durmuş (bkz. 5). Hiçbir bölümde canlı/gerçek para
yok; "hiçbir repoda borsaya emir gönderen kod yok" (`DENETIM_12EKIM.md` C10). Gerçek ileri test fiilen yapılmadı.

---

## 2. Veri

- **Kaynak.** Kripto: Binance spot günlük (USDT paritesi), `data-api.binance.vision`, yedek api.binance.com/.us, o da olmazsa
  Yahoo (`scripts/fetch_data.py:20-60`). Hisse/emtia/endeks/kur: Yahoo `yfinance`, `auto_adjust=True` (temettü/bölünme
  düzeltmeli) (`fetch_data.py:63-77`). Veri GitHub Actions ile çekilip repoya commit ediliyor (`.github/workflows/fetch-data.yml`);
  sebep: oturum proxy'si Yahoo/Binance'i engelliyor (`ILERLEME.md`).
- **Evren** (`scripts/varliklar.py`): 25 kripto (bugünün piyasa değeri ilk 25'i, stablecoin hariç: BTC, ETH, XRP, BNB, SOL, DOGE, TRX, ADA,
  LINK, AVAX, XLM, SUI, BCH, HBAR, LTC, TON, DOT, SHIB, UNI, NEAR, APT, AAVE, ICP, ETC, PEPE); Mag7; BIST30'un en büyük 10'u
  (ASELS, GARAN, KCHOL, THYAO, BIMAS, AKBNK, ISCTR, TUPRS, FROTO, YKBNK); emtia = GC=F (altın) ve CL=F (petrol) sürekli vadeli
  serisi. Yardımcı: NDX, SPX, XU100, USDTRY. Trend kolları için ayrıca `data/genis` (BIST30, 50 ABD hissesi, 22 emtia vadeli,
  18 emtia ETF) ve `data/stres` (22 coin).
- **Günlük/haftalık.** Tüm işlem günlük mumla. Haftalık mum günlükten türetilir (`W-SUN`, `swing/veri.py:66-69`); haftalık değer
  ancak Pazartesi'den itibaren kullanılır (`veri.py:72-78`, `haftalik_gunluge`), yani ileriye bakma yok.
- **IS/OOS.** IS = 2015-2022, OOS = 2023-2026 (`swing/calistir.py:8`, `OOS_BASLANGIC = 2023-01-01`).
- **BIST USD.** `usd_cevir` (`veri.py:31-37`): O/H/L/C aynı günün USDTRY kapanışına bölünür. TL'de S1/S3 BIST'te kârlı görünürken USD'de
  ~0'a düşüyor (`SONUCLAR.md:67-68`). Küçük kusur: kur kapanışı (21:00 UTC) BIST kapanışından (15:00 UTC) geç; gün içi kur
  hareketi lookahead sayılır ama etkisi ihmal edilebilir.
- **Veri kapsamı gerçeği [ölçüm].** Dosya başlangıçları: BTC/ETH 2017-08, BNB 2017-11, LTC 2017-12, ADA 2018-04, XRP 2018-05,
  çoğu alt 2019-2020, SHIB/ICP 2021, APT 2022-10, PEPE/SUI 2023-05, TON 2024-08 (TON verisi 2026-06-30'da bitiyor, muhtemelen
  delist/veri kesintisi). Aktif kripto sayısı: 2017: 4, 2018: 9, 2019: 13, 2020: 19, 2021: 21, 2022: 22, 2023: 24, 2024-26: 25.
  Yani "IS 2015-2022" kripto için fiilen 2019-2021 (2018'de 3, 2022'de 5 işlem: BTC rejim filtresi kapatıyor).
  Hisse/BIST 2015'ten başlıyor. Bu, kripto IS sonuçlarını (PF 2,94) tek bir boğa dalgasına bağlıyor.

---

## 3. Backtest motoru (`swing/motor.py`)

**Maliyet/kayma.** Sabit tek yön oran: kripto %0,10, Mag7 %0,05, BIST %0,15, emtia %0,05 (komisyon+kayma birlikte,
`veri.py:21`); işlem sonunda `net = brüt - 2*maliyet` (`motor.py:123`). Stop çıkışları ek kayma görmez (stop fiyatından
dolum, gap'te açılıştan). Kripto için %0,10 zaten Binance spot taker komisyonunun (%0,1) kendisi; kayma payı sıfıra yakın.
**Binance'te funding yok** (spot) ve **short yok** (`short=False` her yerde). 1L3A perpetual + funding kullandığı için bu fark
önemli (bkz. 7e).

**Giriş zamanlaması.** Sinyal t kapanışında, giriş t+1 açılışında (`motor.py:60`). S3 için "limit emir": limit = kapanış - 0,5 ATR;
açılış limitin altındaysa açılıştan, gün içi düşük limite değerse limit fiyatından dolum, yoksa iptal (`motor.py:61-69`).
Dolum kuralı "dokunma = dolum" (kuyruk/derinlik yok); `DENETIM_12EKIM.md` C10 bunu kendisi de iyimser buluyor.

**Mum içi çözüm.** Gün içi stop kontrolü her zaman hedeften/kısmi kârdan önce (muhafazakâr), `motor.py:84-89`. Açılış stopun ötesindeyse
açılıştan çıkış (`motor.py:84-86`). Kısmi kâr (+R'de %50) gün içi high ile tetiklenir, stop başabaşa çekilir (`motor.py:90-94`);
aynı gün başabaş stopun test edilmemesi küçük iyimserlik. Kapanış bazlı izleyen stop/çıkış sinyali ertesi açılışta uygulanır
(`motor.py:101-115`). Giriş gününde açılış stoptan aşağıdaysa işlem hiç açılmaz (`motor.py:72`), bu gerçek hayatta da
makul (açılışı görüp girmezsiniz).

**Lookahead taraması [kod okuma + test].** Haftalık yön, piyasa rejimi, Donchian (`h.rolling(n).max().shift()`), göstergeler:
ileriye bakma bulamadım. Rejim endeks serisi `reindex(..., ffill)` ile gününe hizalı (`stratejiler.py:38-48`). Kapanmamış kripto
günü atılıyor (`veri.py:53-54`). Sorun yok; asıl sorunlar aşağıdaki seçim/uygulama iyimserlikleri.

**Portföy (`motor.py:152-200`).** Sermaye 100.000; her işlemde ağırlık = %1 risk / stop mesafesi, tek pozisyon <= %20, toplam <= %100,
<= 10 açık pozisyon, aynı varlıkta tek pozisyon, ağırlık < %2 ise atla. Kaldıraç yok (toplam <= %100). Ayrı kaldıraç deneyi:
`deneyler/kaldirac.py` (fonlama günlük %0,03 kripto, yalnız borçlanılan kısım üzerinden; izole tasfiye modeli).

**Kodda kendi bulduğum hatalar ve iyimser varsayımlar**
1. **Max düşüş gerçekleşmiş eğriden hesaplanıyor** (`motor.py:185-190`: eğri yalnız kapanan işlem günlerinde güncelleniyor).
   Açık pozisyonların gün içi/gün sonu zararı yok. [ölçüm] Günlük piyasa değeriyle (`kagit/motor.py:69-86`) maks. düşüş tüm dönem
   -%17,4 (OOS -%17,4, IS -%11,5), raporlanan -%12,6. Sharpe aylık gerçekleşmiş eğriden 1,40; günlük MTM IS 1,76 / OOS 1,32.
   `DENETIM_12EKIM.md` C3 de aynı şeyi yazıyor. Raporlanan düşüşü ~4-5 puan düşük kabul etmek gerek.
2. **Raporlanan istatistikler 2198 sinyalin, portföyün gerçekte aldığı 1185 işlemin değil.** `SONUCLAR.md` KO %56,1 / 2197 işlem.
   Portföy 10 pozisyon/%100 tavanı nedeniyle sinyallerin %54'ünü alıyor. [ölçüm] Alınanlarda KO %56,7, ort. R +0,315 (hepsi:
   56,3% / +0,324); fark yok, ama sıralama kuralı `(giris_tarih, varlik adı)` yani alfabetik (`motor.py:160`): aynı gün
   10'dan fazla sinyalde "AAPL, AAVE..." öncelikli. Kalite sıralaması yok; önyargı küçük ama keyfi.
3. **Sharpe risksiz faiz çıkarılmadan** (aylık ortalama/std; trend/ tarafında günlük ort/std, rf=0). 2023-26'da %4-5 faizle
   şişkin.
4. **Monte Carlo yanlış sıralı:** işlem R'leri sıralı birleştirilip %1 risk bileşiklenmiş (`deneyler/saglamlik.py:39-50`),
   eşzamanlılık ve korelasyon yok. Kağıt hesapta ilk 2 günde 9 S1 pozisyonu, 6'sı kripto (bkz. 5): işlemler bağımsız değil.
5. **Aynı yanlılık:** `ayarlar.py:12-13` yorumu "BIST S1/S3'te hem IS hem OOS negatif" der. [ölçüm] S1 BIST IS +0,11 R (PF 1,27,
   n=226), OOS -0,10; S3 BIST IS -0,24, OOS -0,16. Yani S1 BIST dışlaması OOS'a bakılarak yapılmış, yorum IS için yanlış.
6. **Duyarlılık [ölçüm].** Limit dolumunu "limit altına %0,5 daha inmeli" yapınca S3 KO %70,4 -> %67,2, CAGR %29,2 -> %28,2;
   hem %0,5 limit penetrasyonu hem %0,5 stop kayması: CAGR %25,3, DD -%16,3, ort. R 0,324 -> 0,284. Sistem yürütme
   iyimserliğine kırılgan değil ama düşüş genişliyor.
7. `swing/optimize.py:45` `__main__` bloğu boş (kalıntı); `ILERLEME.md:18` olmayan `gunluk-sinyal.yml`'e, `:16` olmayan `data/GUNCELLE`
   dosyasına atıf yapıyor (belge-kod çelişkisi, bkz. 8).

---

## 4. Stratejiler

### 4.1 Ortak çerçeve (`STRATEJILER.md:36-60`, `swing/ayarlar.py`)
Long-only. Haftalık yön modları (`stratejiler.py:15-35`): `ha` = haftalık Heikin Ashi yeşil ve kapanış 20 haftalık SMA üstünde;
`ema10_30` = haftalık EMA10 > EMA30 ve kapanış > EMA30. Piyasa rejimi (`stratejiler.py:38-48`): kripto -> BTC, Mag7 -> NDX, BIST
-> XU100 (USD), emtia -> filtre yok. Çıkışlar kısmi kâr + izleyen stop + zaman stopu.

### 4.2 S1 Trend geri çekilme (`stratejiler.py:77-112`, parametreler `ayarlar.py:3-4`)
| Adım | Kural / değer |
|---|---|
| Haftalık yön | `ha` |
| Rejim | sınıf endeksi haftalık `ha` yukarı (emtia: yok) |
| Günlük trend | kapanış > EMA50, EMA10 > EMA50, EMA50 > EMA50(5 gün önce) |
| Geri çekilme | son 3 günde low <= EMA10 + 0,3 ATR, ve RSI14'ün son 3 günlük min'i < 65 |
| Tetik | kapanış > önceki gün high ve kapanış > EMA10 |
| Giriş | ertesi açılış |
| Stop | min(son 4 günün low'u, kapanış - 1 ATR) - 0,5 ATR (kripto medyan mesafe %13,3 [ölçüm]) |
| Çıkış | +1R'de %50 sat, stop başabaşa; kapanış < EMA50 -> ertesi açılış; en fazla 30 gün; izleyen stop yok (`iz_atr=None`) |
| Sınıflar | kripto, Mag7, emtia (BIST dışlandı) |

Sonuçlar (`SONUCLAR.md:19-22`): tüm n=1186, KO %52,4, PF_R 1,82, ort. R +0,32, yıllık %19,8, DD -%16,0 (tek başına).
IS 591 işlem KO %54,5 R +0,39; OOS 595 işlem KO %50,4 R +0,25.
[ölçüm] Sınıf x dönem: kripto IS 253 işlem R +0,68 / OOS 429 R +0,19 (KO %58,5 -> %48,0); Mag7 IS +0,21 / OOS +0,34; emtia IS +0,11 /
OOS +0,69 (n=28). Çıkış nedenleri: stop 613, süre 301, sinyal 264.

### 4.3 S2 Sıkışma kırılımı (`stratejiler.py:121-147`)
| Adım | Kural / değer |
|---|---|
| Haftalık yön | `ema10_30`; rejim: endeks haftalık EMA10 yukarı |
| Daralma | son 5 günde ATR(5)/ATR(50) < 0,9 |
| Tetik | kapanış > önceki 20 günün high'ı; hacim > 20 günlük ort.; kapanış günlük aralığın üst %40'ında |
| Stop | kapanış - 2 ATR |
| Çıkış | +1,5R'de %50 sat + başabaş; izleyen stop (en yüksek kapanış - 4 ATR); kapanış < 20 gün dip; en fazla 30 gün |
| Sınıflar | kripto, Mag7, BIST, emtia |

Sonuçlar: n=501, KO %50,5, PF_R 1,85, R +0,43; IS 305 KO %52,5 / OOS 196 KO %47,4 R +0,41; yıllık tek başına %12,3 (OOS %4,9).
[ölçüm] kripto IS +0,80 / OOS +0,58; Mag7 +0,55 / +0,32; BIST +0,08 / +0,31 (n=77/42); emtia +0,05 / +0,11 (n=23/18 ~ gürültü).

### 4.4 S3 Aşırı satım dönüşü (`stratejiler.py:156-200`)
| Adım | Kural / değer |
|---|---|
| Yön / rejim | haftalık `ha`; endeks haftalık EMA10/30 |
| Trend | günlük kapanış > SMA200 |
| Tetik | RSI(2) < 10 |
| Giriş | ertesi gün limit: kapanış - 0,5 ATR (dolmazsa iptal) |
| Stop | limit - 2 ATR |
| Çıkış | kapanış > SMA10 veya RSI(2) > 70 -> ertesi açılış; en fazla 10 gün |
| Sınıflar | kripto, Mag7 (emtia ve BIST dışlandı) |

Sonuçlar: n=510, KO %70,2, PF_R 1,96, R +0,22; IS %70,0 / OOS %70,4; yıllık %9,5, DD -%9,8. Ort. kazanç +%6,8 ~ ort. kayıp -%7,1:
yüksek KO, kayıplar kazançlarla aynı büyüklükte (uzun kuyruk değil, simetri). [ölçüm] kripto R +0,19 / +0,17, Mag7 +0,28 / +0,24.
Çıkış: sinyal 379, stop 93, süre 25.

### 4.5 Birleşik ve varlık sınıfı ayrımı
Birleşik (`SONUCLAR.md:27-30`): n=2197 KO %56,1, yıllık %29,1, DD -%12,6, Sharpe 1,40 (IS %30 / OOS %25,4). Sınıf bazı
(`SONUCLAR.md:44-50`): kripto IS PF 2,94 -> OOS 1,61; Mag7 IS 1,79 -> OOS 1,88; BIST IS 1,14 -> OOS 1,62 (n=77/42); emtia 1,21 -> 2,14 (n=105/46).
[ölçüm] kâr katkısı (R toplamı, alınan işlemler): kripto 1,47, Mag7 1,35, BIST 0,35, emtia 0,07. Yıllık: 2020 +82%, 2021 +108% (MTM);
2015-2019 CAGR ~%12; 2025 en zayıf ve 2025 kripto ort. R -0,03.

### 4.6 Parametre seçimi ve OOS'a kaç kez bakıldı
- Belge iddiası: "Parametreler yalnızca IS'te seçildi, OOS seçimde kullanılmadı" (`SONUCLAR.md:5-6`).
- Kod gerçeği: `swing/optimize.py:9-39` her ızgara satırında IS **ve OOS** sütunlarını hesaplayıp yazıyor; seçim skoru IS'ten
  (`IS_R * sqrt(IS_n)`, KO >= %45 şartı `optimize.py:39`) ama tarama betikleri OOS'a göre sıralıyor/filtreliyor:
  `s1_tarama3.py:10` (`OOS_WR >= .45`, `sort_values("OOS_R")`), `ince_ayar.py:8,12` (OOS_R / IS_DD), `s3_tarama2.py:9` (`OOS_CAGR`).
  Ayrıca rejim filtresi, BIST/emtia dışlama, S1 RSI<65, S2 kısmi 1,5R adımları OOS sayılarıyla gerekçelendirildi (`SONUCLAR.md`
  günlük 8-10). `DENETIM_12EKIM.md` C2: "swing iyileştirmeleri OOS R'ye göre sıralandı". Yani OOS bağımsız değil.
- Deneme sayısı [ölçüm, CSV satırları]: S1 1.158 (432+384+288+54), S2 648 (576+72), S3 704 (512+192) ızgara noktası + 39 duyarlılık +
  rejim 5x3 + elle 10 adım + stop genişliği 7 varyant; yaklaşık 2.500+ deneme, hepsinde OOS görüldü. `DENETIM_12EKIM.md`: swing çoklu
  deneme düzeltmeli Sharpe (DSR) 0,77-0,89.
- **KO hedefi beklentiyi aşındırıyor** [ölçüm `s1_tarama2.csv`]: kısmi kâr almak KO'yu artırıyor (IS %45,3 -> %47,3-51,2) ama ortalama
  beklentiyi düşürüyor (IS ort. R 0,289 -> 0,206-0,232; OOS 0,131 -> 0,067-0,089). Yani %45 hedefi (`optimize.py:39`) kısmi kâr
  seçimini yönlendirmiş; pratikte "KO için beklenti feda edildi".
- İlk S1 ızgarası (`s1_tarama.csv`, n küçük) IS ort. R +0,48, OOS -0,02: ham S1 kuralı OOS'ta çöküyordu; sonradan eklenen `ha` yönü,
  rejim filtresi ve RSI eşiği gevşetme (40 -> 65) OOS'u kurtarmış görünüyor ama bu adımlar OOS görülerek seçildi.
- Varyasyon testi (`saglamlik.py`, `SONUCLAR.md:62-64`): 39 tek parametreli oynatmada hep beklenti pozitif; ama tek bir komşu seçim,
  birlikte kayma değil.
- S2: daralma filtresi (ATR oranı < 0,9) [ölçüm `s2_tarama.csv`]: filtre kapalı (99) IS R 0,642, 0,9: 0,643 (aynı); OOS 0,40 vs 0,52.
  Yani getirinin asıl kaynağı 20/55 günlük kırılım + trend yönü; "sıkışma" katkısı IS'te yok.
- S3: ham ızgarada ortalama R ~ +0,04 (IS 0,045 / OOS 0,059); stokastik varyantı negatif (IS -0,074 / OOS -0,085); Bollinger ~ RSI(2);
  limit 0,5 ATR ortalamada fark yaratmıyor (IS -0,001 vs 0,027); "ardışık 2 düşüş" zararlı (`s3_tarama.csv`). Nihai S3 R 0,22,
  rejim + `ha` + limit/çıkış adımlarıyla geldi (OOS bakılarak).

### 4.7 Sağlamlık / rejim / hayatta kalma testleri (`deneyler/`)
- `saglamlik.py`: tek parametre oynatma; 2x maliyet (KO %55,8, yıllık %26,8, DD -%14,1); sıralı bootstrap Monte Carlo (medyan DD -%13,1).
- `rejim_testi.py/.csv`: sınıf endeks rejimi (None, ema10_30, ha, ema10, sma200) etkisi.
- `hayatta_kalma.py` + `HAYATTA_KALMA.md`: "çöken coin" stres testi. **Zayıf**: 25 coinlik listenin yalnızca 22'si indirilebilmiş (`data/stres`);
  LUNA, MATIC ve COMP yok. Yani en kritik çöken (LUNA) testte yok. Kalan coinler (XMR, ATOM, FIL, MKR, ZEC, DASH, ALGO...) hâlâ yaşayan
  ve Yahoo'da verisi olanlar; gerçekten delist/sıfırlanan coin Yahoo'da bulunmaz. Sonuç beklenti dışı şekilde stres evreni ana evrenden
  daha iyi çıkıyor (PF 2,47 vs 2,05; S2 stres PF 3,82). Bu "stres" değil, eşdeğer bir ikinci yaşayan evren; hayatta kalma yanlılığını
  ölçmüyor. Ayrıca ana evrenin içindeki yeni listeli 6 coin (PEPE, SUI, APT, TON, ICP, HBAR) [ölçüm] ort. R +0,16 vs diğerleri +0,39.
- `bist_usd.py`: TL vs USD (BIST yalnız S2).
- `stop_genisligi.py` (+`karsilastirma/EKIP.md` 117-121): daha dar stop kârı artırmıyor; "stop %15'ten uzaksa girme" Sharpe 1,40 -> 1,67
  (7 varyant arası seçim, aşırı uyum riski, "swing v2" adayı).
- `kaldirac.py`: 2x %54 / DD -%30, 3x %79 / -%44 (güvenli üst ~3x, tavsiye <= 2x; stop medyanı %13 olduğu için 5x'te işlemlerin %12'si
  stoptan önce tasfiye).
- `meta_etiket.py`: LightGBM sinyal filtresi swing'de işe yaramadı (Spearman +0,03; OOS Sharpe 1,45 -> 1,26).
- `portfoy_dagilim.py`, `karsilastirma/koni.py`: 5 hesabın portföy dağılımı ve beklenti konisi/bootstrap batma olasılığı.

### 4.8 Codex aday listeleri
`CODEX_ADAYLAR.md`: 11 repo kod denetimi (3'ünde geleceği görme/P&L hatası, 4'ünde eksik kod/veri); 4 aday bizim çerçevede test:
C1 vol. momentum (OOS PF 1,46, tek başına yıllık %14,7), C2 KA-MATS geri çekilme (OOS PF 1,17, DD -%23), C3 sıkışma kırılımı
(OOS 52 işlem, PF 0,55), C4 Ichimoku trend (OOS PF 2,52 ama KO %41). Hiçbiri birleşik Sharpe'ı artırmadı. `CODEX2_ADAYLAR.md`:
D1 ML RED, D2 bileşik 10 gösterge skoru RED (KO %29), D3 **gizli boğa uyumsuzluğu** (3 mum teyitli dip, RSI14 uyumsuzluğu, kapanış > SMA200,
stop 2 ATR, hedef 1,5R, 10 gün) tek başına zayıf (+0,09 R) ama çeşitlendirici -> "S4 adayı" (panelde "Gizli Güç").

### 4.9 Trend kolları (`trend/`)
Kaynak: brainbrick-trades `strategies_long_only.py` (kullanıcının paylaştığı), düzeltmelerle (`trend/OZET.md`): 007'de 52 gün -> 252/365 gün,
ertesi açılış işlem, BIST/XU USD, negatif petrol fiyatı atma (`trend/veri.py:41`), vol hedefi yalnız IS.
- **BTC trend (T1)**: haftalık EMA10>EMA30 ve kapanış>EMA30 **ve** günlük kapanış>SMA50 -> %100 BTC, değilse nakit
  (`trend/stratejiler.py:40-41,62-65`). IS Sharpe 1,30 / OOS 1,12 (al-tut 1,04 / 1,15); DD -%51 / -%24 (al-tut -%83 / -%53).
  SMA 40-100 duyarlılığı Sharpe IS 1,21-1,37 / OOS 0,78-1,18 (`GELISTIRME.md`). OOS'ta Sharpe al-tut'u geçmiyor, yalnız DD azalıyor.
  Tek varlık; BTC tarihsel olarak yapısal yükselen seri; IS 2014'ten (Yahoo BTC-USD) başlıyor. KO ~%33.
- **Kripto portföy genişletmesi (25 coin)**: IS Sharpe 1,46 -> OOS 0,67 (DD -%54), reddedildi. ETH, XU100, XU030, S&P, NDX, altın tek-kural
  al-tut'u geçmedi. BIST portföyleri OOS'ta dağıldı.
- **ABD trend portföyü**: ay sonu 12 aylık getirisi pozitif tüm hisseler eşit ağırlık; S&P haftalık EMA10/30 aşağıysa nakit
  (`trend/kagit.py:44-46`, `stratejiler.py:91,108`). IS Sharpe 1,10 / OOS 1,53, DD -%13 / -%8. Evren: bugünün 50 büyük hissesi;
  "Mag7 hariç" testi (`gelistir.py:71`) kalan 43'ün de bugünün kazananları olduğunu görmezden geliyor. OOS'ta kendi al-tut'undan düşük
  (Sharpe 1,53 vs 1,70; `DENETIM_12EKIM.md` C5). Kağıt hesapta fiilen 32 hisse tutuyor.
- **Emtia ETF düşük vol.**: ay sonu 252 gün oynaklığı en düşük %20 ETF (>=3) eşit ağırlık; IS 0,94 / OOS 1,23, DD -%17 / -%9. Karar sırası:
  önce vadeli seriler (IS 1,13 / OOS 1,2), sonra "vade geçişi fiyatta" gerekçesiyle ETF'ye geçildi; ETF'nin kendi eşit ağırlık al-tutu
  IS 0,29 / OOS 0,79. Seçim kuralı "hem IS hem OOS Sharpe >= 0,9" (`birlesim.py:2-5`) yani OOS seçimde kullanıldı. Kağıtta 4 ETF
  (DBA, CORN, SOYB, DBB).
- **Birleşim** (`BIRLESIM.md`): swing tek başına MTM IS Sharpe 1,75 / OOS 1,32; trend kolları 1,62 / 1,79; %50/%50 2,00 / 1,70;
  haftalık korelasyon swing-BTC 0,37, swing-ABD 0,42, swing-emtia 0,17. Günlük yeniden dengeleme varsayımı.

### 4.10 Elenenler ve nedenleri (özet)
BIST S1/S3 (USD'de ~0/negatif); emtia S3 (IS negatif); stokastik osilatör S3 (negatif); sabit R hedefi, başabaş, dar izleyen stop (ham S1
ızgarasında fayda yok); momentum/hacim filtreleri (anlamlı fark yok); açığa satış ("değer katmadı" iddiası, ama dosya yok -> doğrulanamaz);
Codex RED'leri (geleceği görme, opsiyon verisi, elle işaret, 6,5x kaldıraç); ML meta-etiket; vol hedefleme; kripto trend portföyü; BIST/ETH/endeks
trend; vadeli emtia (roll).

---

## 5. Kağıt botlar

**Mimari** (`kagit/motor.py`, `kagit/README.md`, `.github/workflows/kagit.yml`): Her çalıştırmada veri yeniden indirilir ve kağıt dönemi
başından bugüne kapanmış tüm günlük mumlar backtest koduyla baştan oynatılır (`kagit/motor.py:34-63,89`); durum `kagit-durum` dalına
(`ozet.md, durum.json, islemler.csv, pozisyonlar.csv, ozsermaye.csv`) ve bir GitHub issue'ya yazılır. Zamanlama: günde 2 kez (`23 0,12 * * *`).
Dönem öncesi sinyaller yok sayılır (`kagit/motor.py:45-49`; "hayalet pozisyon" hatası PR #5'te düzeltildi, `DENETIM_12EKIM.md` B1).
Trend botu: `trend/kagit.py`, günde 1 kez (`53 1 * * *`), 3 kol 1/3 sermaye. Ayrı `kiyas-veri.yml` BTC/SPX/NDX/XU100 kapanışlarını
`kiyas-durum` dalına yazar (`scripts/kiyas_veri.py`; yalnız 2026-09-01'den, 2026-10-09'a kadar veri).

**Başlangıç / son güncelleme.** Swing: 2026-10-11 (`config.json`), son durum commit'i 2026-10-15 17:10 UTC. Trend: 2026-10-12, son commit
2026-10-15 06:32 UTC. Kıyas: son 2026-10-15 06:27 UTC. Bugün (2026-11-06) üçü de ~3 hafta bayat; 60 günlük dönem (bitiş ~12-10) hiç tamamlanmadı.

**Neden durmuş olabilir** (kanıt sınırlı, hipotezler):
- GitHub zamanlayıcısı çalışmaları atlıyor: algo 2,4 günde 9/29, strateji 63 saatte 19/126 (`DENETIM_12EKIM.md` B2). ozsermaye.csv'de swing için
  2026-10-13/14 günleri yok (5 satır), yani çalışmalar zaten aksıyordu.
- Zamanlanmış iş akışları yalnız varsayılan dalda çalışır (`ILERLEME.md:18-19`); kod dev dalındaydı, PR #7 ile main'e 10-13'te alındı.
- Ücretsiz Actions kotası 5 bot arasında ortak (`kagit.yml` yorumu; ~120+90+kıyas dk/ay).
- Kullanıcının kararı/kapatması ve token tasarrufu (`DEVIR.md`). GitHub MCP ile workflow run listesi boş döndü (yetki veya silinmiş
  olabilir), nedeni kesin söyleyemiyorum.
- Dikkat: `DEVIR.md` "9-10 Ekim -> 9-10 Aralık" yazıyor, config 10-11/10-12; belge tutarsız.

**Gerçekleşen vs beklenti.** Swing (2026-10-15): değer 9.563 $ (-%4,37), DD -%5,0; kapanan 1 işlem (NVDA S3 stop, -1,02R), açık 9 S1
pozisyonu (ADA, APT, DOT, NEAR, AVAX, BTC %19 ağırlık, ICP, MSFT %20, PEPE). Beklenti (60 gün) +%3-4, aralık -%8..+%15. İlk 2 günde 9
pozisyonun 7'si kripto ve aynı anda açılmış: yoğunlaşma/korelasyon (BTC rejimi ortak) gerçekleşti. Trend (2026-10-15): -%1,32 (BTC trend -%3,4,
ABD +%0,22, emtia -%0,78); BTC kolu çıkış sinyali verdi, ABD 32 hisse. 4-5 gün örneklem istatistiksel olarak anlamsız (denetim: yıllık Sharpe
standart hatası ±3,6, `DENETIM_12EKIM.md` C6). Bot, "geçmişi oynat" modelinde olduğu için gerçek canlı yürütme (dolum/kayma) hakkında hiçbir
şey söylemiyor.

---

## 6. Pano / raporlama / sinyal taraması

- `swing/tarama.py`: son kapanışa göre ertesi gün emirleri (AL, limit/piyasa, stop, kısmi kâr, ağırlık), açık pozisyonlar ve haftalık yön
  tablosu -> `sinyaller/GUNCEL.md` (örnek: 2026-10-09 verisi; S1 DOT stop %22,1, APT %19,5: kripto stopları geniş).
- `kagit/motor.py` `ozet_md` ve `trend/kagit.py` `ozet_md`: günlük rapor (issue). `swing_karsilastirma`: 50/50 sanal birleşim.
- `karsilastirma/`: `panel_veri.py` (777 satır; beş botun durum dallarından hesap/işlem/meta JSON'u, ArtifactData'ya yazılan özel panel),
  `tum_hesaplar.py` (5 hesap tek tablo, bayatlık uyarısı `yas <= 30` saat), `koni.py/koni.json` (blok bootstrap konisi, 1x/2x/3x batma
  olasılığı), `portfoy_dagilim.py`. Panel 3 saatte bir rutinle güncelleniyordu (`DEVIR.md`). 12 Ekim denetimi panelde 13 hata düzeltti (`DENETIM_12EKIM.md` A1-A13).
- 1L3A için: bayatlık/sağlık kartı, koni (beklenti bandı + batma olasılığı), "iyimser + stres" iki beklenti ilkesi doğrudan işe yarar fikirler.

---

## 7. 1L3A'ya aktarım

### (a) Alınabilecek kod modülleri (arşiv `arsiv/swing-sg/` kaynak; 1L3A'da Decimal/borsa filtresi/lookahead testiyle yeniden yazılarak)
| Modül | Değer | Not |
|---|---|---|
| `swing/stratejiler.py` `haftalik_yon` + `haftalik_gunluge` (`veri.py:66-78`) | Yüksek | Çoklu zaman dilimi filtresi için lookahead'siz şablon; 1L3A'da `motor/veri/yeniden_ornekle.py` ile birleştirilebilir. HA yönü (haftalık Heikin Ashi + 20h SMA) ve EMA10/30 yönü. |
| Sınıf endeksi rejim filtresi (`stratejiler.py:38-48`) | Yüksek | 1L3A'da BTC rejimi: kripto için. Not: `DENETIM_12EKIM.md` C4: BTC rejimi 4 hesabı yönlendiriyor (gizli korelasyon). |
| Kısmi kâr + başabaş + ATR izleyen stop (`motor.py:90-115`) | Orta | 1L3A `cikislar.py` zaten `iz_suren_stop`, `basabasa_cek` içeriyor; "kısmi çıkış" yok. KO artırır ama beklentiyi azaltabilir (bkz. 4.6). |
| `deneyler/saglamlik.py` tek-parametre oynatma, `meta_etiket.py` ve `kaldirac.py` fikri | Orta | Aşama 2 eleme eşikleri için hazır desen; kaldıraç tasfiye-mesafe modeli 1L3A perp'lerine uyar. |
| `kagit/motor.py` `gunluk_egri` (günlük MTM) | Orta | Maks. düşüşü MTM ile ölçme zorunluluğu (bkz. 3). |
| `karsilastirma/koni.py` (blok bootstrap konisi, batma olasılığı) | Orta | Lider ajan/dashboard için. |
| `trend/motor.py` `getiri()` (gece boşluğu/gün içi ayrımı) | Düşük | 24/7 perp için gerekmez. |
| Alınmamalı | - | `optimize.py` (OOS görerek sıralama), `portfoy` gerçekleşmiş eğri DD'si, alfabetik öncelik, "dokunma=dolum" limit varsayımı (1L3A'da `limit_modu="olc"` zaten daha dikkatli). |

### (b) S1/S2/S3 <-> 1L3A swing aileleri (`motor/strateji/swing/*.py`)
1L3A'da kodlanmış 10 swing ailesi: ma-kesisim (`motor/strateji/ma_kesisim.py`), macd-sinyal, ma-geri-cekilme, cift-dip-tepe,
konsolidasyon-kirilim, dar-aralik-kirilim, fib-geri-cekilme, bant-donus, aralik-ticareti, mum-yutan-donus. **`swing__rsi-asiri-donus`
henüz kodlanmamış (yedek 1)**.

**S1 <-> `swing__ma-geri-cekilme`** (`ma_geri_cekilme.py`): aynı çekirdek (trend + MA'ya geri çekilme + dönüş mumu). Farklar:
| | swing-sg S1 | 1L3A ma-geri-cekilme |
|---|---|---|
| MA | EMA10 temas (<= +0,3 ATR), EMA50 trend | EMA20 (grid 10/20/50), temas 0 ATR, trend SMA200 ve MA > SMA200 |
| Geri çekilme penceresi | 3 gün | 5 mum (`geri_n`) |
| Soğuma | RSI14 3 gün min < 65 | yok (ADX isteğe bağlı) |
| Tetik | kapanış > önceki high ve > EMA10 | yeşil mum (kapanış>açılış), kapanış > MA ve > önceki high |
| Stop | min(4g dip, kapanış-1 ATR) - 0,5 ATR | geri çekilme dibi - 0,5 ATR |
| Çıkış | +1R %50 + başabaş, kapanış<EMA50, 30 gün | MA'nın karşısına kesişim kapanışı; hedef_r opsiyonel (yarım çıkış yok) |
| Üst TF/rejim | haftalık HA + endeks rejimi | yok |
| Short | hayır | evet (varsayılan) |
Fark yaratanlar: haftalık HA yönü + endeks rejimi + yarım kâr + EMA50 çıkışı. 4.6'ya göre ham S1 OOS'ta çöküyordu; 1L3A'da bu filtreler (üst TF + BTC rejimi)
önce ablation ile test edilmeli. Short: swing-sg'de test dosyası yok, kanıt yok.

**S2 <-> `swing__konsolidasyon-kirilim` (esas) / `swing__dar-aralik-kirilim` (daralma kısmı)**:
- S2 = 20 günlük Donchian kırılımı + ATR(5)/ATR(50) < 0,9 daralma + hacim > 20g ort. + kapanış üst %40 + haftalık trend.
- 1L3A konsolidasyon-kirilim: önceki L mum kutusu **dar** (genişlik <= 5 ATR), kapanış kutu üstü + 0,1 ATR, hacim > 1,5x kutu ort.; stop kutu karşı ucu;
  hedef kutu yüksekliği. Short var.
- 1L3A dar-aralik-kirilim: NR7 / iç bar sonrası setup mumunun ucunun kapanışla kırılması; stop dar mumun karşı ucu. S2'nin "daralma"sı NR7 değil ATR oranı
  (doküman "Farley NR7" diyor ama kod ATR(5)/ATR(50), `stratejiler.py:121-136`; belge-kod farkı).
- S2 stopu kapanış-2 ATR (kutu ucu değil), çıkışı izleyen 4 ATR + 20g dip (1L3A'da hedef ölçülü hareket). Bulgu: S2'nin IS kalitesi daralma filtresinden değil
  Donchian + trend yönünden geliyor (4.6), bu yüzden 1L3A'da konsolidasyon-kirilim'e "trend_ema" + haftalık yön eklemek daha doğru deney.

**S3 <-> (kodlanmamış) `swing__rsi-asiri-donus`; kısmen `swing__bant-donus`**:
- S3 = trend içinde RSI(2) < 10 + SMA200 + haftalık HA/endeks rejimi + 0,5 ATR limit alış + SMA10/RSI2>70 çıkış. Bu Connors tarzı; kaynaklar TMP RSI, Ladha S10,
  Thomsett (TMP ve Thomsett 1L3A'nın kaynaklarında yok). 1L3A `swing__rsi-asiri-donus` taslağı RSI(14)<30 yukarı kesim veya RSI(2)<10 diyor, yazar: Schroder, Jordan,
  Johnson; **Schroder s.224: RSI(2) 90/10 sisteminde Sharpe zayıf, düşüş büyük** (negatif kanıt, `aileler.json`). swing-sg S3'ün ham ızgarası da zayıf (R +0,04); iyileşme rejim/HA/limit adımlarından.
- `swing__bant-donus` (BB dışından geri dönüş + ADX<25, hedef orta bant) farklı tetik (bant dışına çıkış sonrası geri giriş, trend yok); swing-sg `osc="bb"` varyantı (kapanış < alt bant)
  RSI(2) ile aynı performansta (4.6) -> S3 testi bant-donus için de ipucu: ortalamaya dönüş yalnız trend + rejim filtresiyle çalıştı (ADX<25 yatay filtre swing-sg'de test edilmedi; S3 tam tersine
  SMA200 üstü trend şartı koyuyor).

### (c) "Denendi-başarısız" negatif bilgi (aile_id eşleme)
| aile_id | swing-sg bulgusu | Kaynak |
|---|---|---|
| `swing__stokastik-donus` | S3 osilatörü stokastik (K<20 yukarı kesişim) ortalama R IS -0,074 / OOS -0,085 (RSI2 ve BB +0,05) | `s3_tarama.csv` |
| `swing__rsi-asiri-donus` | "Ardışık 2 düşük kapanış" şartı faydasız (IS -0,007); RSI2 tek başına ham R +0,04 | `s3_tarama.csv` |
| `swing__ma-geri-cekilme` | ham S1 (EMA10/50, RSI<40-50) OOS ort. R -0,02; yön modu `macd` ≈ `ema10`; sabit hedef (2R/3R), başabaş, dar izleyen stop fayda sağlamadı | `s1_tarama.csv` |
| `swing__macd-sinyal` | yalnız haftalık yön filtresi olarak denendi (`yon_mod=macd`), diğerlerinden iyi değil | `s1_tarama.csv` |
| `swing__ma-kesisim` | doğrudan test yok; BTC trend kuralı (EMA10/30 + SMA50) BTC'de al-tut Sharpe'ını geçmedi, ETH/XU100/S&P/NDX/altında al-tut'u geçemedi | `trend/OZET.md`, `SONUCLAR_TREND.md` |
| `swing__konsolidasyon-kirilim` | Codex C3 "sıkışma kırılımı (bizim)" OOS PF 0,55 (52 işlem), D2 bileşik skor RED; S2'nin sıkışma filtresi IS'te fark yok | `CODEX_ADAYLAR.md`, `s2_tarama.csv` |
| `swing__rsi-diverjans` | D3 "gizli boğa uyumsuzluğu" tek başına +0,09R, PF 1,04, ama düşük korelasyonlu ekleme (9 komşu ayarda pozitif): küçük/pozitif | `CODEX2_ADAYLAR.md` |
| `swing__heikin-ashi-donus` | haftalık HA yön filtresi olarak S1/S3'te en iyi yön modu (OOS R 0,179 vs 0,135-0,138) | `s1_tarama3.csv` |
| BIST (tüm aileler) | USD bazında S1/S3 negatif, trend BIST portföyleri OOS'ta dağılıyor, XU100 trend al-tut'u geçmiyor. 1L3A'da BIST zaten yok | `SONUCLAR.md`, `trend/OZET.md` |
| emtia (tek kural) | altın tek kural trend negatif; vadeli emtia S2 zayıf (+0,05..0,11 R); S3 emtia IS negatif | `SONUCLAR_TREND.md`, ölçüm |
| ML meta-etiket, vol. hedefleme, kripto trend portföyü | fayda yok / OOS çöküş | `EKIP.md:136-138`, `OZET.md`, `GELISTIRME.md` |
Test edilmemiş (negatif bilgi DEĞİL): cift-dip-tepe, fib-geri-cekilme, mum-yutan-donus, aralik-ticareti, short bacağı.

### (d) Metinler ve PDF'ler (1L3A `veri/kart_dizini.csv` `kaynak_dosya` ile örtüşme)
swing-sg kökünde 35 PDF + `metinler/` altında 35 .md (118 MB PDF, 8,2 MB metin; telif. 1L3A kuralı: kitaplar repoya girmez). Örtüşme (yazar eşlemesiyle,
13 kitap ortak): Ladha (140s), Sharpe, Heikin Ashi Trader 4S, Christopher (Geçimini Sağlamak), Boxer, Scheier, Simon Jordan, Mark Make, Velez, Jea Yu, Hogan,
Bulkowski, Graham. Morge (Metal piyasaları) iki depoda da var ama 1L3A'da 0 kart (görsel ağırlıklı).
**swing-sg'de olup 1L3A kart dizininde olmayan 21 kitap** (aday: yeni kart çıkarımı): Ochoa (5 Adımlı Plan), Ghosh (Bounce), Kathy Lien, Abraham (Forex Swing),
Danq Brown (Forex Swing Rehberi), Barry Rudd (Formasyonlar), Munroe (Heiken Ashi + Stokastik), TMP (RSI Swing, 13s; S3 kaynağı), David Smith (Short Swing), Swing Failure
Pattern (11s), Farley (Swing Trader, 306s), Lee & Tryde (Zamanlama Çözümleri; haftalık/günlük çoklu TF), Anderson, Rivalland, Jan Arps, Leandro Yöntemi, Mermigas,
Thomsett (Swing Tradinge Giriş), "Swing yüksek/düşükleri" (40s), Walters, Ivanov. Özellikle çoklu TF (Lee&Tryde, Munroe), Connors/RSI(2) (TMP) ve Leandro/Ochoa/Ghosh pullback
kitapları S1/S3 eşdeğerlerini besler. Tersi: 1L3A'da olup swing-sg'de olmayan swing kaynakları: Landry, Crane, McArthur, Penn, Adekunle, Aaron Lee Johnson, Kratter, Edward Day.
Dikkat: swing-sg `STRATEJILER.md` kavram sayıları (RSI 34 doküman vs.) basit metin taraması; yazar bağımsızlığı denetimi yok (1L3A'nın `yazar_denetimi.csv` daha titiz).

### (e) S1-S3 kripto günlük sonuçlarının 4 saatlik / perpetual (funding) koşullarına taşınabilirliği
- Günlük kripto sonuçları (IS 2019-21, OOS 2023-26): S1 R +0,68 -> +0,19; S2 +0,80 -> +0,58; S3 +0,19 / +0,17 (4.5 ve [ölçüm] sınıf tablosu).
- **4 saatlik**: Kurallar gün cinsinden (EMA10/50, RSI14, ATR14, 20 gün kanal, SMA200, 30 gün). 4S'de aynı sayıların kopyalanması çok farklı davranış doğurur
  (RSI(2)<10 çok sık, gürültü ve maliyet payı artar; 6x işlem). swing-sg'de 4S testi yok, taşınma kanıtsız. En makul eşleme "günlük/haftalık yön (zaten
  var) + 4S tetik" ya da kuralların bar sayısını x6 ölçeklemek; ikisi de yeniden doğrulama ister. Maliyet: S3 ort. net +%2,7/işlem, 4S'de brüt kazanç küçülürken
  %0,10 çift yön maliyet aynı kalır; S3 en kırılgan.
- **Perpetual/funding**: swing-sg kripto spot, funding yok. Ortalama tutma 16 gün (S1) x ~%0,01/8s funding (boğada daha yüksek) ~ %0,5/işlem notional'a,
  stop mesafesi %13'e bölününce ~0,04R (S1), S3 (5 gün) ihmal edilebilir; 2021 boğasında funding çok daha yüksek olabilir. `kaldirac.py` funding'i yalnız
  borçlanılan kısma uyguluyor (perp'te nominalin tamamına gerekir), düşük tahmin. Kripto stop medyanı %13: 1L3A %1 risk + 3x sınırı altında bu, pozisyon boyutunu ~%7'ye
  düşürüyor, kaldıraç tavanı bağlayıcı olmaz; ama yüksek kaldıraçta tasfiye (5x'te işlemlerin %12'si stoptan önce).
- Perp'te short mümkün; swing-sg short test etmedi (kanıt yok).
- TradFi perp (hisse/emtia): kısa tarihçe (1L3A DURUM.md: 1-10 ay). swing-sg'nin Mag7/emtia sonuçları (Yahoo, 2015+) bu perp'lere doğrulama için kullanılabilir ama perp
  fiyatı/fonlaması farklı; Mag7 sonuçları seçim yanlılığı taşıyor (bugünün kazananları).
- Sonuç: S1 ve S2 kripto günlükte ham olarak 1L3A günlük/swing ailelerine taşınabilir; 4S ve S3 için ayrı doğrulama gerekli.

---

## 8. Kırmızı bayraklar

1. **Aşırı uyum ve OOS kirliliği.** ~2.500+ ızgara noktası, her birinde OOS görüldü; `SONUCLAR.md:5-6` "OOS seçimde kullanılmadı" ifadesi
   kodla (`s1_tarama3.py:10`, `ince_ayar.py`, `s3_tarama2.py:9`) ve kendi denetimleriyle (`DENETIM_12EKIM.md` C2) çelişiyor. Gerçek ileri test yok.
2. **Sınıf dışlaması OOS'a bakılarak**, `ayarlar.py:12` yorumu S1 BIST için IS'te yanlış ([ölçüm] IS +0,11 R).
3. **KO hedefi beklentiyi bozuyor**: kısmi kâr KO'yu yükseltirken ortalama R'yi düşürüyor (4.6).
4. **Kripto IS = tek boğa dalgası.** IS kripto fiilen 2019-2021, 2018/2022'de 3 ve 5 işlem; PF 2,94 -> 1,61; 2025 kripto ~sıfır R. Yıllık getirinin büyük kısmı 2020-21
   (+82%, +108%). 2015-2019 CAGR ~%12.
5. **Hayatta kalma yanlılığı**: 25 coin bugünün listesi; yeni listeli 6 coin ayrı ve düşük (+0,16 R). "Stres" testi 22 coin, LUNA/MATIC/COMP yok, hepsi yaşayan, sonuçlar
   ana evrenden iyi (stres olmuyor). Mag7 bugünün kazananları; ABD trend sepeti bugünün 50 büyüğü.
6. **Düşüş ölçümü iyimser**: raporlanan -%12,6 gerçekleşmiş eğri; MTM -%17,4. Sharpe rf=0.
7. **Rakamlar sinyal bazlı (2198), portföy 1185 aldı**; alfabetik öncelik.
8. **Yürütme iyimserliği**: limit dokunma=dolum, sabit %0,10 kripto maliyet = Binance spot komisyonunun kendisi, küçük coinlerde kayma düşük tahmin; trend botu
   ve kağıt bot geçmişi yeniden oynatıyor (gerçek ileri test değil).
9. **Gizli yoğunlaşma**: BTC rejimi, aynı gün 7 kripto S1 girişi (kağıt hesapta -%4,4 ilk günlerde); ortak 17 coin üç bot arasında.
10. **Belge-kod çelişkileri**: (a) `ILERLEME.md:18` `gunluk-sinyal.yml` yok (`.github/workflows` altında 6 dosya); (b) `ILERLEME.md:16` `data/GUNCELLE` yok;
    `fetch-data.yml` onu tetikleyici sayıyor; (c) `STRATEJILER.md` S2 "Farley NR7" ama kod ATR(5)/ATR(50); (d) `SONUCLAR.md`/README "35 kitaptan türetildi" ama S3'ün RSI(2)<10 +
    SMA200 + HA yönü ızgara sonucu, kitaplarda tek tek bu parametreler yok; (e) `STRATEJILER.md:58` "açığa satış testlerde değer katmadı" ama sonuç dosyası yok;
    (f) `trend/OZET.md` emtia satırı vadeli sürümün (1,09/1,35) rakamlarını verirken kağıtta ETF %20 (0,94/1,23) var; trend metni "50 hisse/18 ETF", fiilen 32/4;
    (g) `DEVIR.md` tarihleri vs config; (h) `SONUCLAR.md` 2197 işlem, yeniden çalıştırmada [ölçüm] 2198 (veri güncellemesi nedeniyle küçük kayma).
11. **Test süresince kural dondurma** iyi niyetli ama kağıt bot 5 günde durdu; hiçbir ileri kanıt üretmedi.
12. `DENETIM_12EKIM.md` C10: hiçbir repoda borsaya emir gönderen kod yok; canlı katman yok.

---

## Lider için özet
1. swing-sg = günlük/haftalık, long-only, kripto+Mag7+BIST+emtia swing sistemi (S1 pullback, S2 kırılım, S3 RSI(2) dönüşü) + trend kolları; rapor: KO %56, yıllık %29, DD -%12,6; bu rakamlar iyimser.
2. Gerçek durum: OOS bağımsız değil (~2.500 deneme, OOS görülerek seçim), DD gerçekleşmiş eğriden (MTM -%17,4), kripto IS 2019-21 tek boğa dalgası, stres testi eksik (LUNA yok).
3. Kağıt botlar 2026-10-15'te durmuş (~5. gün, swing -%4,4, trend -%1,3); gerçek ileri kanıt yok.
4. Alınacak: haftalık HA/EMA yön + endeks (BTC) rejim filtresi şablonu (lookahead'siz), MTM drawdown ölçümü, koni/bayatlık panosu fikri, tek-parametre sağlamlık testi.
5. Eşleme: S1 ~ swing__ma-geri-cekilme (+haftalık yön, RSI soğuma, yarım kâr, EMA50 çıkışı), S2 ~ konsolidasyon-kirilim (Donchian20; sıkışma filtresi IS'te fark yok), S3 ~ rsi-asiri-donus (kodlanmamış; ham edge zayıf).
6. Negatif bilgi: stokastik dönüşü, ardışık-düşüş şartı, sabit R hedefi/başabaş, BIST, tek-kural altın/endeks trend, ML filtre, kripto trend portföyü.
7. Kitap örtüşmesi 13/35; 21 swing-sg kitabı (TMP RSI, Munroe, Lee&Tryde, Farley, Leandro, Ochoa...) 1L3A kartlarında yok.
8. 4S/perp taşınabilirliği kanıtsız: swing-sg spot, funding ve short yok; S1/S2 günlük kripto OK (OOS R +0,19/+0,58), S3 en kırılgan.
9. Bu rakamları hedef değil üst sınır sayın; 1L3A'da aynı filtreleri ablation + walk-forward + MTM DD ile yeniden test edin.
10. Rapor: /tmp/claude-0/-home-user-1L3A-Proje/d9801314-f689-5b3c-ae41-5973e32ea499/scratchpad/rapor_swing-sg.md
