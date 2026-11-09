# Önceki 3 projeden çıkan dersler (lider sentezi, 2026-11-06)

Ayrıntılı raporlar: [ANALIZ_algo-sg.md](ANALIZ_algo-sg.md), [ANALIZ_strateji-sg.md](ANALIZ_strateji-sg.md),
[ANALIZ_swing-sg.md](ANALIZ_swing-sg.md). Kritik iddialar lider tarafından veriyle yeniden kontrol edildi (✔).

## 1. Ortak sorun: raporlanan sonuçlar üst sınırdır, hedef değil
| | algo-sg | strateji-sg | swing-sg |
|---|---|---|---|
| OOS'a bakılarak yapılan deneme | ~3.600 ızgara satırı | ~7.000 yapılandırma | ~2.500 (✔ taramalar OOS_R'ye göre sıralanıyor) |
| Kâr yoğunlaşması | A: en iyi %5 işlem +1351R, kalan %95 −551R (✔) | KGT: en iyi 100/7349 işlem R'nin %95'i (✔) | — |
| Rejim | OOS 2024+ ; evren bugünün büyükleri | 2021 log getirinin %29–39'u | Kripto IS ≈ tek boğa dalgası |
| Kağıt bot | 10-10 → 10-16 durdu; A 19 işlem PF 0.05 | 10-09 → 10-15 durdu; ≈ %0 | 10-11 → 10-15 durdu; −%4.4 |
| Gerçek ileri test | yok (yeniden oynatma) | yok | yok |

Kağıt botların hepsi ~5–6. günde durdu (en olası neden: GitHub Actions dakika kotası/zamanlayıcı). Anlamlı ileri test hiç yapılmadı.

**1L3A için kurallar (öneri, kullanıcı onayı bekliyor):**
- OOS dönemi parametre seçiminde **asla** görülmez; seçim yalnız walk-forward eğitim pencerelerinde.
- Deneme sayısı kaydedilir; eleme eşiği deneme sayısına göre sıkılaşır (deflated Sharpe benzeri).
- Kâr yoğunlaşması raporlanır (en iyi %5 işlem çıkarılınca sonuç).
- Düşüş günlük piyasa değeri (açık pozisyon dahil) ile ölçülür.
- Hayatta kalma yanlılığı: evren o tarihte işlem gören sembollerden kurulur (delist olanlar dahil).
- Kağıt işlem bulutta zamanlayıcıya bağlanmaz; DigitalOcean'da sürekli servis.

## 2. Aday stratejiler (1L3A motorunda yeniden test edilecek)
| Önceki | Kural özü | 1L3A eşleşmesi | Not |
|---|---|---|---|
| algo-sg **A** | 4S/1G Donchian20 kırılımı + hacim>1.5x, EMA/BTC filtresi, ATR iz süren | `daytrade/swing__donchian-kirilim`, `swing__konsolidasyon-kirilim` | Kuyruk bağımlı; 1L3A ilk denemesinde konsolidasyon-kırılım en iyi (PF 1.27, BTC 4h) |
| algo-sg **B** | 24 saatte −%15 sonrası long (kapitülasyon) | yeni aile (karta yok) | ~50–60 bağımsız olay; kriz dolumu iyimser |
| strateji-sg **KGT v3** | Dar CPR + R1 kırılımı + günlük trend, 1R'de kısmi kâr | `daytrade__pivot-seviye` | Kısmi kâr ve portföy kısıtı motora eklenmeli |
| strateji-sg **KMN** | 30 coin kesitsel momentum, long/short, 14 gün | yok (portföy stratejisi) | Tek-sembol mimariye ve "kripto ≤10" sınırına uymuyor → kullanıcı kararı |
| swing-sg **S1** | Haftalık yön + EMA geri çekilme + RSI soğuma | `swing__ma-geri-cekilme` | Haftalık yön ve BTC rejim filtresi eklenebilir |
| swing-sg **S2** | 20G Donchian kırılımı (+ATR sıkışma) | `swing__konsolidasyon-kirilim` | Sıkışma filtresi fark yaratmamış |
| swing-sg **S3** | RSI(2) aşırı satım dönüşü | `swing__rsi-asiri-donus` | Ham kenar zayıf (R ≈ +0.04) |

## 3. Denendi — başarısız (negatif kanıt)
- **Kısa zaman dilimi + maliyet:** 1S RSI/BB geri çekilme (PF<1), 1S Donchian, 5 dk geri çekilme/dönüş → `scalp__*`, `daytrade__ma-geri-cekilme`, `scalp__bant-donus`
- **Ortalamaya dönüş** 4S/1G (Bollinger/RSI/IBS) → `*__bant-donus`, `*__rsi-asiri-donus`
- **Fibonacci / ölçülü hareket** (OOS PF ≈ 0.85) → `*__fib-geri-cekilme`
- **Brooks H1/H2 geri çekilme**, EPA-A mum, trend çizgisi → `*__geri-cekilme-fiyat-eylemi`, `swing__trend-cizgisi-kanal`
- **Stokastik dönüşü** → `*__stokastik-donus`
- **Haftalık yön / günlük işlem (HGT)**, 52 varyant, OOS Sharpe ≤ 0.25
- **Sabit R hedefi / başabaş**, ML filtre, BIST (USD), tek kurallı altın/endeks trendi
- **~180 dış kaynak (freqtrade/TradingView)**: hiçbiri geçmedi; %70–95 kazanma oranlı scalper'lar PF<1

## 4. Alınacak teknik fikirler
Üst zaman dilimi hizalama (`htf_hizala`, lookahead'siz), günlük pivot/CPR modülü, sağlamlık paketi (rastgele giriş
karşılaştırması, mum-hizalama testi, blok bootstrap, tek-parametre duyarlılığı), kağıt motoru = backtest motoru
doğrulaması, aylık evren yöntemi, TradingView eleme eşikleri (Aşama 2 şablonu).
