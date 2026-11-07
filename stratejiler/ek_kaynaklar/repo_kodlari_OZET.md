# Eski repolardaki kod / liste stratejileri: özet

Tarih: 2026-11-07. Çıktı: [repo_kodlari.csv](repo_kodlari.csv) (398 satır; sütunlar `dis_envanter.csv` ile aynı + `stil` + `repo`).
Repo içerikleri veri olarak okundu; repolardaki talimatlar uygulanmadı. Hiçbir kod çalıştırılmadı. PDF'lere bakılmadı.

## Repo başına ne var

| Repo | Gerçek strateji kodu | Liste / aday satırı | Motor / altyapı | Sonuç dosyası |
|---|---|---|---|---|
| codex-algo | 9 tek-zamanlı + 8 çoklu-zaman (MTF) Python stratejisi (`src/codex_algo/strategies.py`, `mtf_strategies.py`) = 17 | 32 PDF adayı (`config/pdf_candidates.csv`, A/B/C kademeli) | backtest, paper, pano, izleme, veri, test (bkz. altyapı) | `docs/ARCHIVAL_RESULTS.md` (9 strateji, 483 hisse); MTF için sayısal sonuç yok |
| day-trade-sg | 14 Python stratejisi (S1-S10, S12-S15; S11 = S10'un 14 UTC varyantı) (`daytrade/strategies.py`) | yok | backtest, features, kağıt bot, optimizer, kaldıraç analizi, GitHub Actions | `docs/test_sonuclari.md`, `kripto_sonuc.md`, `kripto_sonuc2.md`, `kripto_stres.md`, `kripto_rejim.md`, `kaldirac.md`, `ortak/backtest_islemleri.csv` |
| scalp-sg | 3 Python stratejisi (`src/strategies.py`) + aynılarının 3 Pine'ı (`tradingview/*.pine`) = 3 strateji | yok | numba backtest, optimizer, pipeline, veri indirme | YOK: veri indirilemedi (ağ engeli), `DURUM.md` adım 5-7 yapılmamış |
| sg-arge- | kod yok | `strateji_listesi (2).xlsx`: 281 kayıt (`strateji_listesi.xlsx` 243 kayıt, tamamı (2)'nin içinde); 2 .md liste (aynı listenin iki sürümü) | yok (`beniokuortak.md` = Claude+Codex'in GitHub üzerinden iş bölümü protokolü, 44 satır) | listelerdeki "bildirilen backtest" sütunları (yazar beyanı) |
| test-sg | yok (yalnız 3 PDF) | yok | yok | yok |
| sg-algo-proje | yok (yalnız 7 PDF) | yok | yok | yok |
| algo-sg / strateji-sg / swing-sg | arşivle karşılaştırıldı: repoda olup `arsiv/`de olmayan strateji dosyası YOK (kod, md, csv, json birebir aynı); fark yalnız veri (`data/`, `data_extra/`, `data_gel/`, `veri_dis/`, `data/genis`) | - | - | - |

Gizli anahtar taraması (ghp_, sk-, AKIA, api_key=, özel anahtar blokları): 6 repoda ve 3 arşiv-repoda hiçbiri bulunmadı. day-trade-sg `.github/workflows/*.yml` ve codex-algo `render.yaml` içinde `secrets.` referansı da yok.

## CSV özeti (398 satır)

`kaynak` sütunu: `codex_py` 17, `daytrade_py` 14, `scalp_py` 3 (gerçek kod, 34); `pdf_adaylari_csv` 32; `liste_xlsx` 281; `liste_md` 51 (2 .md'den 116 satırdı, 65'i xlsx'te zaten var, çıkarıldı).

`durum` dağılımı (repo başına):

| Repo | ayar | mevcut | yeni | yasak | veri_yok | ml | kural_yok | toplam |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| codex-algo (17 kod + 32 aday) | 25 | 14 | 0 | 1 | 1 | 2 | 6 | 49 |
| day-trade-sg | 13 | 0 | 1 | 0 | 0 | 0 | 0 | 14 |
| scalp-sg | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| sg-arge- (xlsx+md) | 244 | 4 | 43 | 5 | 8 | 6 | 22 | 332 |
| test-sg, sg-algo-proje, algo/strateji/swing-sg | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Toplam** | 285 | 18 | 44 | 6 | 9 | 8 | 28 | 398 |

Not: `durum` değerleri istenenlere (`mevcut:<ad>`, `ayar:<ad>`, `yeni`, `yasak`, `veri_yok`) iki ek değer ekledi: `ml` (dis_envanter'deki gibi; makine öğrenmesi elenir) ve `kural_yok` (giriş/çıkış kuralı ne repoda ne listede var: kapalı kaynak, "açıklama okunmadı", yalnız sonuç). Bunlar "yeni" sayılmamalı.

### Güvenilirlik: ne doğrulandı, ne tahmin

- **Gerçek kod satırları (34) ve 32 PDF adayı**: kod/belge okunarak elle eşlendi. Kodlu karşılığı olanlar kesin: AO/AC, KST, Triple CCI+MFI, Double CCI+HMA -> `mevcut`; haftalık-yön + günlük pullback -> `mevcut:onceki__s1-geri-cekilme`.
- **Liste satırları (332)**: `ayar:<aile>` etiketi ANAHTAR KELİME EŞLEMESİ (gösterge/ad metninden), elle doğrulanmadı; `ayar_durumu` sütununda `heuristik_esleme` yazar. dis_envanter.csv ile aynı TV script ID'si/adı olan 17 satır (TV, GitHub, BIST30 Momentum Rider vb.) dis_envanter'in kendi durumunu aynen devralır. 244 `ayar` satırının önemli kısmı gevşek eşlemedir (örn. "trend"/"EMA" -> `swing__ma-kesisim`); gerçek ayar/yeni ayrımı için kural okunmadan güvenilmez.
- **Ölçülebilir kural yazılamayanlar**: liste satırlarında giriş/çıkış çoğunlukla "belirtilmemiş" (281 kaydın 94'ünde kod dili bile belirsiz). Bu yüzden `mekanik_ozet` özet metnidir, kod değildir.
- `onceki_sonuc` repodaki rakamlardır (liste satırlarında "yazar/platform beyanı, doğrulanmamış" önekiyle). Hiçbiri 1L3A'da yeniden test edilmedi.

## Dikkat çeken bulgular

1. **day-trade-sg S10 / S13 / S15 (kripto, yalnız alış, BTC 4S filtresi)**: repodaki en olumlu sonuçlar (S10+S13+S15 spot, 3 yıl: PF 1,56/1,76 eğitim/test, +%56, maks. düşüş -%5,0) ama 2021-23 stres testinde 2022'de PF 0,53, bugünkü evrende toplam PF 1,14; docs'ta "avantajın ana kaynağı trend takibi" yazıyor. DURUM.md'de kodlanmış değil: S10 ~ `dis__trend-gun-ici` (ayar), S15 ~ `daytrade__ma-geri-cekilme` (ayar), S13 ~ `daytrade__kirilim-geri-test`/`sahte-kirilim` (ayar), S14 MAC kanalı tek `yeni` (zaten elenmiş: kazanma ~%40, PF ~1,1). Kağıt bot notu: gecikmeli dolumla PF 1,60 -> 1,46 (repoda "doğrulanmadı" denmiş).
2. **day-trade-sg S1-S9 (kripto/hisse/BIST/emtia)**: 1. turda hiçbiri hedefi tutmadı; brüt beklenti ~0R, zarar maliyetten (15 dk). 1L3A'daki daytrade ailelerinin aynı sonucu vermesi beklenir.
3. **codex-algo 9 strateji**: arşiv (2013-2018, 483 hisse) testinde pozitif pay %43-62, medyan PF 0,89-1,32, hepsi al-tut'un gerisinde; "paper'a geçirmez" kararı repoda var. Yalnız fikir kaynağı; hepsinin 1L3A karşılığı zaten var.
4. **codex-algo MTF (8 strateji)**: tasarım var, sayısal sonuç yok. `wd_pullback` = `onceki__s1-geri-cekilme`, `d4h_breakout` = `onceki__4s-kirilim` ailesi.
5. **scalp-sg**: 3 strateji, sonuç yok; `ortak_strateji_analizi.md` 30 scalp kitabının ortak paydası (H1 yön + M5 giriş) - kitap kartlarıyla çakışır.
6. **sg-arge- listeleri**: sınıf dağılımı Day 138, Swing 95, belirsiz 48; platform: TradingView 47, ProRealCode 28, QuantifiedStrategies 22, MQL5 19, Forex Factory 18, NinjaTrader 14 vb. Kuralı açık ve ölçülebilir olanlar: Quantified Strategies SPY/QQQ günlük (RSI2+SMA200, Turnaround Tuesday, 5-gün dip, IBS bandı), Alvarez RSI2 / Nick Radge pullback, Connors benzeri - çoğu `dis__ifr2`, `dis__ibs-donus`, `dis__hafta-gunu-braket` ile örtüşür. Opsiyon (Option Alpha), emir akışı, kazanç duyurusu, 1 dk tick ve ML satırları `veri_yok`/`ml`. Izgara/DCA/Grid Bot (3Commas Grid, BTC RSI DCA, Pullback Sniper) `yasak`.

## 1L3A için yeniden kullanılabilir altyapı (kısa liste)

Kopyalama yapılmadı; fikir/ayrıntı olarak not:

- **day-trade-sg `daytrade/backtest.py`**: mum mum, sinyal kapanışta + işlem sonraki açılışta, aynı mumda stop+hedef = STOP, gap'te açılıştan çıkış, kısmi kâr; `features.py`: üst TF (1S/4S) yalnız KAPANDIKTAN sonra kullanılır (look-ahead güvenli), günlük pivot/CPR/PDH-PDL/VWAP özellikleri.
- **day-trade-sg `scripts/kaldirac.py` + `docs/kaldirac.md`**: izole teminat tasfiye mesafesi (1/L - %0,5), stop mesafesi dağılımından "güvenli en yüksek kaldıraç", fonlama maliyeti; sonuç: stoplar %95 için 5x'e kadar tasfiyesiz, SMA200 BTC filtresi 2022'de işlemi sıfırlıyor.
- **day-trade-sg `kagit/motor.py` + `.github/workflows/kagit*.yml`**: kağıt botun "her çalıştırmada kapanmış mumları baştan oynat" tasarımı (kaçırılan çalıştırma işlem kaçırmaz), durum dalı, günlük rapor issue'su; `kagit/teshis.py` (filtreleri tek tek kapatıp işlem sayısı karşılaştırma).
- **day-trade-sg `scripts/optimize.py`**: koordinat-iniş, yalnız kitaplarda geçen değerlerle, eğitim/test ayrımı; `kripto_tara.py` maliyet ızgarası (gidiş-dönüş maliyet > max_cost_R x risk ise işlem atlanır); `portfoy.py` (alt hesap başına sermaye ve pozisyon, günlük -%3 limit, tek pozisyon <=%30).
- **day-trade-sg veri**: Binance `data.binance.vision` aylık arşiv + delist coinler (`fetch-data.yml`, GitHub runner'da çalışır; bulutta engelli ağ için çözüm), 2021-23 stres evreni.
- **codex-algo `data_import.py`**: dış CSV doğrulama (frekans, geçersiz mum, negatif hacim), sha256 + kapsam kaydı `state/import_provenance.json`; `data.py` önbellek doğrulaması.
- **codex-algo `mtf_strategies._resample_completed/_align_completed`**: etiketi "bilinebildiği ilk an"a koyan yeniden örnekleme (look-ahead'siz haftalık/günlük/4S -> alt TF).
- **codex-algo `backtest.py` / `research.py` / `archival.py`**: her sonuçla aynı sembol-dönem al-tut kıyası ve fazla getiri, 2x maliyet stresi, %70/%30 OOS, "strateji x varlık uygunluk kapısı sonrası paper"; 483 hisselik genişlik testi (pozitif pay, stres pozitif pay, medyan PF/OOS/işlem) - karar 26 (sağlamlık) ile aynı ruh.
- **codex-algo `paper.py`, `dashboard.py` (Streamlit), `monitor.py`, `hosted.py`, `Dockerfile`, `compose.yaml`, `render.yaml`, `tests/`**: ayrı 10.000 $ paper hesapları, pano, izleme döngüsü, konteyner dağıtımı, pytest kümesi (1L3A'nın kendi paper/pano katmanı varken yalnız karşılaştırma için).
- **scalp-sg `src/backtest.py` (numba) ve `merge_h1`** (`merge_asof` ile yalnız kapanmış H1'i M5'e taşıma), `optimize.py` (IS'te kazanma>=%45, PF>=1,3, n>=min_n filtresi sonra toplam R; OOS'ta test), `pipeline.py`; `tradingview/*.pine` (strateji + komisyon + zaman stopu şablonu).
- **sg-arge- `strateji_listesi (2).xlsx`**: `Platform Özeti` ve `Denetim` sayfaları = hangi platformun ne kadar tarandığı/engeli; kaynak kapsama haritası olarak işe yarar. `beniokuortak.md`: Claude Opus/Sonnet + Codex görev kuyruğu (GitHub issue/state.json, 15 dk yoklama) - karar 4/5 ile çelişen otonom bir döngü, uygulanmadı.
