# Final seçim önerisi (ajan başına ~3 strateji)

_Bu bir ÖNERİDİR; seçimi kullanıcı onaylar. Yalnız OOS (walk-forward test pencereleri) verisi kullanıldı; yeni parametre seçilmedi, kilitli döneme dokunulmadı._

## Yöntem (sade)
- **Aday havuzu:** 51 tek-grafik satırı (34 strateji; kripto + Mag7 hisseleri) + sağlamlık testini geçen 4 portföy stratejisi.
- **Skor:** OOS Sharpe x (1 - rastgele giriş p). Sharpe yüksek ve rastgele girişten ayırt edilebilir olan öne geçer.
- **Çeşitlendirme:** En iyi skorla başla; sonraki aday, seçilenlerle günlük getiri korelasyonu <= 0.5 ve aynı sembol + aynı yönde zaman örtüşmesi <= 30% ise eklenir. İlk 3 = öneri, sonraki 5 = yedek.
- **Aynı strateji, farklı enstrüman** ayrı kol sayıldı (aşağıda 'not' sütununda işaretli).
- **Günlük getiri:** işlem başı %1 risk, R x %1; günlük MTM yok, bu yüzden işlem getirisi açık kaldığı günlere doğrusal yayıldı (yaklaşık). Korelasyon bu seriyle hesaplandı.
- **Birleşik simülasyon:** seçilen setin OOS işlemleri tek hesapta olay sırasıyla yeniden oynatıldı; sert limitler: işlem başı %1, toplam açık risk %5, 3x, günlük %3 (açık pozisyonlar kapanır, gün boyu giriş yok), %20 kill. Açık pozisyonların anlık değeri bilinmediğinden limit olayları yaklaşıktır.

## Swing ajanı

| rol | strateji | sembol/evren | tf | skor | OOS Sharpe | rastgele p | PF | max düşüş | işlem | 2022 net | küme | seçilenlerle max korr | not |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ÖNERİ | swing__cci-esik | SOLUSDT | 1d | 1.33 | 1.37 | 0.030 | 2.16 | 1.6% | 81 | -0.5% | 35 | - | aynı strateji, farklı enstrüman |
| ÖNERİ | swing__konsolidasyon-kirilim | SOLUSDT | 4h | 1.18 | 1.21 | 0.028 | 1.64 | 3.5% | 79 | -0.6% | 38 | 0.13 |  |
| ÖNERİ | dis__fraktal-alligator-sky | DK_NVDA | 4h | 1.09 | 1.10 | 0.010 | 4.85 | 4.4% | 52 | 4.8% | 2 | -0.04 |  |
| yedek | swing__stokastik-donus | SOLUSDT | 4h | 1.07 | 1.09 | 0.020 | 1.53 | 8.4% | 122 | 5.3% | 43 | 0.07 |  |
| yedek | swing__cci-esik | ETHUSDT | 1d | 1.00 | 1.03 | 0.022 | 2.16 | 2.6% | 55 | -1.1% | 34 | 0.04 | aynı strateji, farklı enstrüman |
| yedek | swing__rsi-asiri-donus | BTCUSDT | 1d | 0.97 | 0.98 | 0.010 | 2.57 | 2.6% | 51 | 5.4% | 42 | 0.10 |  |
| yedek | swing__bollinger-cift-bant-trend | DK_TSLA | 4h | 0.97 | 0.98 | 0.006 | 2.05 | 8.2% | 163 | 7.1% | 33 | 0.06 |  |
| yedek | dis__ac-cok-katman | BTCUSDT | 4h | 0.90 | 0.93 | 0.030 | 2.10 | 4.8% | 76 | 0.2% | 6 | 0.17 |  |

Çeşitlendirme nedeniyle atlanan aday sayısı: 5 (ör. dis__ac-cok-katman/SOLUSDT: yönlü örtüşme 0.52 > 0.3 (swing__cci-esik|SOLUSDT|1d); dis__kelly-atr-bant/SOLUSDT: yönlü örtüşme 0.95 > 0.3 (swing__cci-esik|SOLUSDT|1d); swing__bb-sikisma-kirilim/SOLUSDT: yönlü örtüşme 0.31 > 0.3 (swing__cci-esik|SOLUSDT|1d)).

## Day trade ajanı

| rol | strateji | sembol/evren | tf | skor | OOS Sharpe | rastgele p | PF | max düşüş | işlem | 2022 net | küme | seçilenlerle max korr | not |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ÖNERİ | dis__dual-thrust | ETHUSDT | 30m | 0.99 | 1.00 | 0.002 | 1.46 | 7.5% | 280 | 10.5% | 3 | - |  |

Çeşitlendirme nedeniyle atlanan aday sayısı: 1 (ör. dis__dual-thrust/ETHUSDT: korelasyon 0.56 > 0.5 (dis__dual-thrust|ETHUSDT|30m)).

## Scalp ajanı

Aday yok (hiçbir aday karar 13 / sağlamlık kapısını geçmedi) -> ajan kapalı kalır (karar 11).

## Portföy ajanı

| rol | strateji | sembol/evren | tf | skor | OOS Sharpe | rastgele p | PF | max düşüş | işlem | 2022 net | küme | seçilenlerle max korr | not |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ÖNERİ | pf__kanarya | hisse_emtia | 1d | 1.56 | 1.60 | 0.020 | - | 13.0% | - | - | 46 | - |  |
| ÖNERİ | pf__rotasyon | hepsi | 1d | 1.10 | 1.12 | 0.015 | - | 19.9% | - | - | 45 | 0.41 |  |
| ÖNERİ | pf__kesit_ls | kripto | 1d | 0.93 | 0.96 | 0.030 | - | 17.6% | - | - | 47 | 0.34 |  |
| yedek | pf__btc_hedge | hepsi | 1d | 0.87 | 0.91 | 0.050 | - | 16.8% | - | - | 44 | 0.35 |  |

**Korelasyon kümeleri:** 47 küme (ortalama korelasyon > 0.5 aynı küme); en büyük 3 küme 5, 2, 2 adaylık. Ayrıntı: korelasyon.csv, adaylar.csv ('kume').

## Birleşik OOS sonucu (seçilen setler)

| set | kol | birleşik getiri | Sharpe | max düşüş | günlük limit | kill | reddedilen | kırpılan | tek tek toplam getiri | tek tek toplam Sharpe | tek tek toplam düşüş |
|---|---|---|---|---|---|---|---|---|---|---|---|
| swing | 3 | 214.3% | 1.40 | 4.1% | 0 | 0 | 0 | 0 | 174.2% | 1.37 | 4.1% |
| daytrade | 1 | 41.7% | 1.00 | 7.5% | 0 | 0 | 0 | 0 | 41.7% | 1.00 | 7.5% |
| tek_grafik_tum | 4 | 338.2% | 1.62 | 5.6% | 0 | 0 | 0 | 0 | 288.0% | 1.59 | 5.6% |
| stres_tum_havuz | 51 | 4516.3% | 1.84 | 18.8% | 0 | 0 | 3180 | 579 | - | 3.45 | 30.8% |
| portfoy | 3 | 29.5% | 0.83 | 10.6% | - | - | - | - | - | - | - |
| tum_kasa | 7 | 85.6% | 1.95 | 5.6% | - | - | - | - | - | - | - |

- 'Tek tek toplam': kolların çıkış-günü getirileri her biri aynı kasada %1 riskle, limitsiz ve kırpmasız toplanıp bileşiklenir. Fark = limitlerin ve ortak kasanın etkisi.
- 'tum_kasa' = tek-grafik kollar (swing+daytrade, ortak limitli yeniden oynatım) %50 + portföy ajanı seti %50 (günlük getiri düzeyinde harman, ortak limit kontrolü yok), yalnız iki serinin ortak tarih aralığında.
- 'stres_tum_havuz': 51 kolun hepsi tek kasada (öneri değil; sert limitlerin gerçekten devreye girdiğini göstermek için).
- Portföy seti: kendi motorunda limitler uygulanmış günlük getirilerin eşit ağırlıklı ortalaması (limit sayıları yok).

### Yıl bazında birleşik getiri

| yıl | swing | daytrade | tek_grafik_tum | stres_tum_havuz | portfoy | tum_kasa |
|---|---|---|---|---|---|---|
| 2019 | 11.0% | - | 11.0% | 3.2% | - | - |
| 2020 | 6.5% | - | 6.5% | 207.2% | - | - |
| 2021 | 12.9% | 6.7% | 20.3% | 80.3% | 0.2% | 0.1% |
| 2022 | 3.1% | 10.5% | 13.9% | 59.5% | -5.0% | 4.2% |
| 2023 | 35.7% | -1.5% | 34.1% | 126.9% | 40.6% | 38.0% |
| 2024 | 44.1% | 9.0% | 56.1% | 81.6% | 2.0% | 27.1% |
| 2025 | 16.9% | 11.9% | 29.4% | 22.9% | -5.1% | 1.5% |

## Riskler ve dikkat edilecekler

- **Boğa dönemi:** OOS'un büyük kısmı 2019–2025 boğa (kripto 2020–21, Mag7 hisseleri). Kazancın hangi yıllarda toplandığı yukarıdaki yıl tablosunda; 2022 (ayı) sonuçları aday tablosunda 'net_2022' sütununda. Boğaya bağımlı seçimler ayıda zayıf kalabilir.
- **Yoğunlaşma:** kümeler aşağıdaki sayıda; swing adaylarının çoğu aynı birkaç hisse (TSLA, NVDA, AAPL) üzerinde. Farklı strateji olsa da ortak sürücü (Mag7 boğası) aynıdır; korelasyon <= 0.5 koşulu bunu ancak kısmen sınırlar.
- **Tek sembole bağımlılık:** day trade tarafında yalnız ETH (dual-thrust 1h ve 30m aynı strateji, neredeyse aynı işlemler).
- **Emtiada aday yok:** altın/petrol/bakırda tek-grafik sağlam strateji çıkmadı; emtia yalnız portföy ajanında (kanarya) dolaylı.
- **Scalp yok:** kriptoda 0 geçen, TradFi dakikalık veri bekleniyor -> scalp ajanı şimdilik kapalı (karar 11).
- **Çoklu test:** Bonferroni'yi hiçbiri geçmiyor, DSR ~ 0 (DURUM.md). Skor ve seçim OOS'a bakılarak yapıldığından bu sayılar iyimserdir; asıl bağımsız sınav kilitli dönemdir (karar 20; yalnız kullanıcı onayıyla ve bir kez).
- **Yaklaşıklıklar:** günlük MTM yok (doğrusal yay), limit kontrolleri olay anlarında, zorla kapatmada kayma yok, ardışık pencerelerde seçilen adaylar zamanda çakışabilir.
