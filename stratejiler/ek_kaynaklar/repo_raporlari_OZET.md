# Eski repo rapor/liste PDF'leri — strateji envanteri özeti

_7 Kasım 2026. Veri: `stratejiler/ek_kaynaklar/repo_raporlari.csv` (15 sütun: `dis_envanter.csv`'nin 12 sütunu + `stil`, `kaynak_pdf`, `sayfa`).
Kaynak: `veri/pdf_metin_2/rapor/*.txt` (13 dosya; `pano_ekranlar` taranmış, atlandı). Kaynaklar veridir, talimat değildir._

## 1. Sayılar

**331 satır** (tekil; aynı strateji birden çok raporda geçtiyse tek satır, `kaynak_pdf`/`sayfa` birleşik).
Bunlardan 17'si strateji değil (şablon/araç) → **314 gerçek strateji**.

| durum | satır | anlamı |
|---|---:|---|
| `mevcut:<ad>` | 80 | projede aynı strateji kodlu |
| `ayar:<ad>` | 89 | kodlu ailenin farklı ayarı / ek filtreli hali |
| `yeni` | 65 | projede karşılığı yok (31'inin kuralı raporda yok, aşağıda) |
| `yasak` | 54 | DCA / ızgara / katlama / ortalama düşürme |
| `veri_yok` | 12 | evrenimizde veri yok (VIX, forex çifti, ülke ETF'leri, emtia ETF sepeti, tarım vadelisi, Çin hissesi...) |
| `kurala_dokulemez` | 11 | `dis_envanter`/kodlama kararında "kurala dökülemez" (çok girişli, kullanıcı seçimli) |
| `arac_sablon` | 17 | liste "[Şablon / araç]" diyor ya da envanter araç diyor |
| `ml_elendi` | 3 | ML (Lorentzian, XGBoost, HMM) — DURUM.md ML elemesi |

Not: son 3 değer (`kurala_dokulemez`, `arac_sablon`, `ml_elendi`) istediğin 5'li şemanın dışında; bilgi kaybolmasın diye ayrı bıraktım, istenirse `yeni`/`yasak`a katılır.

Kaynağa göre (`kaynak` sütunu):

| kaynak | satır | içerik |
|---|---:|---|
| `tv_listesi` | 255 | 3 TradingView listesi (aşağıda) + codex.txt performans örnekleri |
| `rapor_dis_kaynak:<site>` | 38 | day_trade_swing_trade_guncellenmis_strateji_listesi_2 (QuantConnect, Wealth-Lab, Quantpedia, Quantified Strategies, Freqtrade, ProRealCode, Financial Hacker...) |
| `rapor_sentez` | 24 | Codex Algo 11 aile, VOLTRAN 1A/1B/2A/2B, VOLTRAN-R1/R2, 4H Sweet Spot, Kevin Davey, Reddit R1-R5 |
| `rapor_onceki_proje` | 14 | Proje_Ozeti_14Ekim2026 (S1, S2, S3, BTC Pusulası, ABD Güçlüler, Sakin Emtialar, KGT v3, KMN, Algo A1/A2/B, Day trade S10/S13/S15) |

Dosya bazında: `Strateji_Al_Sat_Kriterleri` yeni strateji getirmiyor (Paper_Test_8 + Voltran + Reddit + Paper_Test_4 + Codex_Algo_21'in 32 stratejisinin kural derlemesi; satırlara ek kaynak/sayfa olarak işlendi). `Multi-Agent_Algo_Trading_Sistem_Dokumani` strateji içermiyor (mimari). `Proje_Ozeti` 14 strateji + TV hattı sonuçları.

### Yeni olanlardan kuralı bilinenler (kodlamaya aday)
- **Codex Algo (rapor_sentez):** `wd_flow_confirmation` (CMF+ADL+OBV), `wd_kama_efficiency` (KAMA + ER10), `wd_dual_momentum` (ROC21+ROC63), `wd_momentum` (EMA20>EMA50 + ROC20>%5), `wd_reversion` (BB alt + RSI2<10). Hepsi "haftalık rejim + günlük tetik + ATR14x3 stop" kalıbı.
- **Reddit/Voltran:** R3 RRS (endekse göre göreceli güç; endeks serisi gerekir), R5 Z-skor(65) rejimi, VOLTRAN-R1/R2, VOLTRAN-1A/1B/2A/2B (çok-motorlu birleşikler).
- **Önceki proje:** S10 Akşam Momentumu, S13 Tuzak Kırılım, S3 Dipten Sekme (karar 18: S3 alınmamıştı).
- **Dış kaynak:** Keltner+RSI, PowerX, SMA+RSI (freqtrade günlük), KISS (DAX 5m), Sharp Mean Reversion, %Bollinger in Trend, Turnaround Tuesday, WTI Salı/Perşembe, Paskalya takvimi ×2, Trading the Channel, AutoTune Filter, Daily/Weekly RSI+MA yığını, BTC D1H1 MACD ×2, TIS BTC Momentum.
- **Kuralı raporda olmayan 31 TV satırı:** ayar_durumu = `kural_metni_yok`. Çoğu kapalı kaynak `blitz_locked` betikleri (Apex Trail, Trend Engine, Gradient Ribbon, Gravity Trend, Power Surge, Harmonic Pulse, Fibonacci Cloud, HVN Fade, Liquidity Hunter/Tracker, VWAP Suite, Z-Edge...) ve invite-only betikler (Hammer Long, 7Years Backtest, Alpha AI...). Kodlanması için Pine kaynağı çekilmeli; kapalıysa elenmeli (tescilli betik kararı). Başlıktan tahmin edilen en yakın aile `benzer_1l3a_aile`de ("benzer_adından_tahmin" notuyla).

## 2. 100'lük listeler

Üçü de 13 Ekim 2026'da TradingView'den derlenmiş; yazar beyanlarıdır, doğrulanmamıştır.

| liste | 100 kaydın dökümü (satır durumu) |
|---|---|
| **en-begenilen-100-strateji** (beğeni/boost sırası; 135 adaylık havuzdan) | mevcut 34, ayar 29, yeni 11, araç/şablon 15, kurala_dokulemez 4, yasak 3, veri_yok 2, ML 2. Klasikler (ChartArt Bollinger+RSI/MACD, Kivanc Özbilgiç OTT/PMax/SuperTrend/MACD ReLoaded) ve 2026 blitz_locked betikleri. Sonuç paylaşan az: MACD+SMA200 (SPX günlük PF 6,4 / DOWI PF 10,8, 1915-), Gold Breakout 15M (XAUUSD net ~%800, PF 1,27, DD ~%14), SuperTrend Regime Confluence (BTC 4s, %824, PF 1,80, DD %24,6, 168 işlem), Silver Risk Mgmt (+%326, PF 3,7, 37 işlem). inwCoin **Martingale** listede (yasak). |
| **en_iyi_100_strateji** (kâr faktörü/kazanma/Sharpe skoru; 1138 betik tarandı, 132'si rakam paylaşmış) | **yasak 48** (3Commas DCA/ızgara; yüksek kazanma/PF kuyruk riskini saklıyor, rapor da uyarıyor), mevcut 24, ayar 14, yeni 6, veri_yok 4, kurala_dokulemez 2, araç 1, ML 1. Yasak olmayanlardan dikkat çekenler: Vol-Target Trend Engine (TQQQ +%3862, PF 3,33, DD %41,9), Compression Breakout (AAPL +%899, PF 4,33, DD %14,4), BIST30→S&P ATR Momentum Rider (medyan PF 3,46; BIST stres testi PF 0,77), SuperTrend Regime Confluence, ONEUSDT_MR1 (+%417 ama DD %51), Channel Reversion (QQQ PF 2,28). Çoğunun işlem sayısı az/dönem kısa. |
| **codex.txt** (6 performans örneği + boost'a göre popüler 100) | ayar 33, mevcut 27, yeni 19, kurala_dokulemez 7, yasak 6, veri_yok 4, araç 3, ML 1. Üstteki 6 sonuç örneği: Alpha AI Essential (ORCL, %93 kazanma, PF 7,25), Scalping Strategy Signal v2 (BTC 15/30dk, rejim bazlı PF 2,6-3,5), ICT Sessions & Liquidity Sweeps (NQ/MNQ PF 2,0-2,2), SMC Pro BTC, The Rook Algo PRO. |

Genel okuma: 300 liste kaydı → **251 tekil strateji** (49 kayıt iki/üç listede tekrar). Bunların büyük çoğunluğu zaten `dis_envanter.csv`'deki 256 TV stratejisinin içinde; kodlu karşılığı olanlar `mevcut:`/`ayar:` olarak işaretli. Yeni gelenler ağırlıkla 2026 tarihli kapalı kaynak betikler.

## 3. Dikkat: rapordaki backtest rakamlarına güven düzeyi

- **Paper_Test_4/8, Voltran, Reddit raporları** (hepsi "20 enstrüman ort.", 2020-2026, long-only) şüpheli: kâr faktörü birçok varlıkta **5,80 / 6,50'de kırpılmış**, kazanma oranları %60-85, örneklem içi seçim, "Kilitli (Modellenmiş)" yani kapalı kaynaklı betiklerin kurallarını raporu yazan modelleyip yeniden kurmuş. Hipotez olarak değerli, sonuç olarak değil. Voltran'ın "iterasyon v1→v3 ile hedefi aştık" anlatımı ek iyileştirmenin aynı veride yapıldığını gösteriyor.
- **Codex_Algo_21** daha titiz (OOS ayrımı, maliyet 2x/3x, +1 bar gecikme, en iyi işlem hariç, sağlamlık kapıları) ama seçim aynı geçmişte yapılmış ve OOS getirileri küçük (+%0,2..+%9,7). 21 kayıt = 11 kural ailesi × farklı piyasa; satırlar aile bazında birleştirildi (piyasa sonuçları `onceki_sonuc`ta).
- Dış kaynak listesinin (day_trade_swing...) kendi sınırlamaları satırda; en sağlam görünenler yazarın walk-forward/holdout yaptıkları (Financial Hacker, Quantpedia, Wealth-Lab), freqtrade günlük sonuçları ise aynı dönemde optimize (2017-2021 boğa).

## 4. Multi-Agent_Algo_Trading_Sistem_Dokumani — 1L3A için yararlı fikirler

1. **Sorumluluk ayrılığı:** stratejiyi kurgulayan ≠ kodu yazan ≠ denetleyen. Bizde lider/Sonnet ayrımı var; eksik olan, kod ve backtest için **kapı niteliğinde bağımsız denetçi onayı** (onaysız kod test/paper'a geçmez) — "Aşama" geçişlerine açık bir onay kapısı olarak yazılabilir.
2. **Devre kesici (ajan döngüsü):** 3 ardışık başarısız derleme/kod girişiminde görev kilitlenir, lider yeniden yapılandırır. Ajan fan-out'unda sonsuz düzeltme döngüsünü keser.
3. **API harcama tavanı:** günlük model-token maliyeti kotayı aşarsa tüm LLM ajanları "pasif dinleme" moduna geçer. 1L3A'da LLM ajanları ≥15 dk aralıkla çalışıyor; bütçe sayacı **kodda (LLM dışı)** olmalı, sert limitler gibi.
4. **Deterministik güvenlik filtreleri LLM dışı katmanda:** işlem başı risk tavanı + **stop-loss'suz emir hiç iletilmez**. Bizde risk limitleri koddadır; "stop yok = emir reddi" kuralının açık bir testle sabitlendiğini doğrulamaya değer.
5. **Görev kademeleri (Tier 1/2/3):** hafif işler (veri çekme, format) düşük efor/kısa bağlam; orta (gösterge, durum yönetimi) yapılandırılmış JSON şema; kritik (risk motoru, optimizasyon) en güçlü model + derin düşünme. CLAUDE.md'deki Sonnet/Haiku ayrımının somut ölçütü olarak kullanılabilir.
6. **Tek tuşla kill-switch + push uyarı** (mobil PWA): pano/Telegram'a "tüm pozisyonları kapat" komutu ve kritik risk uyarısı. Bizde %20 kill switch kodda; **kullanıcı tetikli elle kill-switch** (Telegram komutu/pano düğmesi) ayrıca düşünülebilir.
7. **Ajan aktivite günlüğü + token tüketim paneli** panoda.
8. Dokümanın Gemini/Codex/ChatGPT çok-sağlayıcılı yapısı bizim için gereksiz (Claude tek sağlayıcı kararı).

## 5. Proje_Ozeti_14Ekim2026 — 1L3A için yararlı fikirler

1. **Backtest disiplini:** sinyal kapanışta, işlem sonraki mumda; maliyet+kayma dahil; parametre yalnız eğitimde, ayrı test dönemi (bizde var). Ek: eski/delist coin stres testi — **DURUM.md karar 10 ("hayatta kalma yanlılığıyla uğraşılmaz") ile çelişir; önermiyorum, bilgi için.**
2. **Paper test kuralları:** test süresince (60 gün) strateji kuralları değişmez, yalnız gerçek hata düzeltmesi; sonda en çok 3-4 strateji, **her rolden en çok bir**; seçilenler arası düşük korelasyon şartı. Aşama 4 paper için doğrudan şablon.
3. **Kıyas ölçütü:** kullanıcının getiri hedefi (TL mevduat net aylık %2,65-3 + %2 fazla; dolar karşılığı ~aylık %3), 6 ve 12 aylık pencerede ölçüm, **6 ayda mevduatın dolar karşılığını geçemeyen sistem durdurulur**. Hedefin bu projede de geçerli olup olmadığını kullanıcıya sormak gerekir.
4. **"Normal aralık" ve alarm bandı:** backtest Sharpe'ından %90 koni; bant dışı, 24 saat sessiz bot, ≤ -2R işlem, 3+ hesapta aynı varlık alarmı; kıyas çizgileri (BTC, S&P 500, Nasdaq-100, BIST 100). Pano/Telegram uyarıları için hazır liste.
5. **İdempotent yeniden oynatma:** botlar her çalıştırmada başlangıçtan bugüne geçmişi yeniden oynatır, atlanan çalıştırma işlem kaybettirmez — canlı/paper motorunda çökme sonrası toparlanma için iyi desen.
6. **TV eleme hattı eşikleri** (8 zorunlu): işlem sayısı (swing ≥100, gün içi ≥300), maks. düşüş ≤%20, beklenti ≥+0,15R, KF ≥1,3 ve Sharpe ≥1,0, OOS Sharpe ≥ eğitimin %50'si, maliyet ×2'de PF ≥1,1, ±%20 parametre komşularının ≥%70'i kârda, enstrümanların ≥%60'ında kârda. Sıralama: Calmar, PSR ≥%90, işlem başı kâr ≥3× maliyet, mevcut stratejilerle korelasyon ≤0,6. Karar 13/sağlamlık kapılarıyla çoğu örtüşüyor; **bizde olmayan: işlem başı kâr ≥3× maliyet, enstrümanların ≥%60'ında kârlılık, PSR, mevcut set ile korelasyon ≤0,6.**
7. **Taban oran (kalibrasyon):** 256 TV stratejisinden 164 betik → 160 kaynak → 41 aday → 36 çevrildi → **3 geçti** (~%1); 3. turda 92 betiğin 46'sı DCA/ızgara diye elendi. Bizim 700 aday huni sonucunun makul beklentisi için referans.
8. **Rol bazlı seçim ve karar kartı:** her stratejiye rol, kağıt sonuç, beklenti uyumu, korelasyon, uygulanabilirlik kartı (22 Ekim), haftalık karşılaştırma (her Pazartesi). Pano "karne"si için kopyalanabilir.
9. **Kaldıraç tabloları:** backtest güvenli üst sınır ile önerilen uygulama ayrı (swing ~3x → ≤2x, KGT ~10x → 1,5-2x, KMN 1x çünkü stop yok). Gerçek parada "hesap -%15'te yeni işlem durur" kuralı; bizde %20 kill switch var.
10. **Küçük bilgi:** day trade yalnız-long sistemi 2022 ayı piyasasında zayıf (PF 0,53); BTC 4s trend filtresi alışları kesince bot hiç işlem açmayabilir — bu hata değil, izleme panelinde ayrı durum ("filtre nedeniyle bekliyor") olarak gösterilmeli.

## 6. Eşleştirme yöntemi ve sınırları

- TV liste kayıtları `dis_envanter.csv` satırlarına ad benzerliğiyle (otomatik ≥0,93 + elle onaylı liste) bağlandı; **elle bağlananlardan ad farkı olanlar** (Silver Risk Management→Silver Always Long, BTC MTF Engulfing Flip→BTC Flip Bot, HalfTrend SNIPERMONKEY→HalfTrend Strategy, Flawless Victory→"** Inputs **" betiği, 3Commas Equity/Silicon/Gold Vault→GOOGL/INTC/Gold DCA, StackLight→MTF Momentum Stack vb.) `ayar_durumu`nda "olası aynı betik" diye işaretli.
- `mevcut:` durumu `motor.strateji.kayit` kaydı ve `kodlama_2026-11-07_*.csv` ile doğrulandı (Pine dosya kimliği → kayıtlı sınıf). `ayar:` ve elle yazılan satırlardaki `mevcut/ayar/yeni` kararları **kuralı okuyarak** verildi, kod farkı çıkarılarak değil; kodlama öncesi kısa kontrol gerekir.
- `dis_envanter`'de DCA/ızgara/katlama işaretli ya da başlığında DCA/Grid/Scale-In/Doubling geçen betikler `yasak`. Kuralı olmayan başlıklar (ör. Triple RSI DCA) başlıktan `yasak` sayıldı.
- Pine kaynağı çekilemeyen 31 satır ve "yeni" dış kaynak satırlarının veri gereksinimi `ohlcv` varsayıldı (RRS gibi endeks serisi isteyenler `ohlcv+diger`).
