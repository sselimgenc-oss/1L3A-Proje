# Beklenti aralıkları (paper trading ile karşılaştırma için)

Bu dosya, final setin (7 strateji) geçmiş **örneklem-dışı** sonuçlarından 'normal bir 4 ve 8 haftada ne görürüz?' aralığını çıkarır. Paper trading sonucu bu aralıkta kalıyorsa sistem beklendiği gibi çalışıyor demektir; aralığın dışına çıkması alarm nedenidir. Sayılar tahmindir, söz değildir.

## Set (tüm 7 strateji, kollar 50/50) — 4 ve 8 haftalık pencere

| ölçü | %5 | %25 | %50 | %75 | %95 |
|---|---|---|---|---|---|
| 4 hafta net getiri | -2.1% | -0.6% | 0.7% | 2.7% | 7.1% |
| 4 hafta max düşüş | 0.5% | 0.9% | 1.3% | 1.9% | 2.8% |
| 4 hafta işlem sayısı | 8 | 11 | 14 | 17 | 22 |
| 4 hafta kazanma oranı | 21.1% | 33.3% | 43.8% | 53.8% | 69.2% |
| 8 hafta net getiri | -2.6% | -0.1% | 2.0% | 5.0% | 10.4% |
| 8 hafta max düşüş | 0.9% | 1.4% | 1.9% | 2.6% | 3.9% |
| 8 hafta işlem sayısı | 19 | 25 | 29 | 33 | 40 |
| 8 hafta kazanma oranı | 28.0% | 36.8% | 43.8% | 50.0% | 60.9% |

**Alarm eşiği (set, 8 hafta):** net getiri -2.6% altında VEYA düşüş 3.9% üstünde ise uyarı.

## Strateji bazında (8 hafta, net getiri ve düşüş)

| strateji | net %5 | net %50 | net %95 | düşüş %50 | düşüş %95 (alarm: bunun üstü) | alarm: net bunun altı |
|---|---|---|---|---|---|---|
| dis__dual-thrust / ETHUSDT / 30m | -3.1% | 0.8% | 7.5% | 1.5% | 3.9% | -3.1% |
| pf__kanarya / hisse_emtia / 1d | -4.6% | 2.0% | 11.6% | 2.9% | 7.0% | -4.6% |
| pf__rotasyon / hepsi / 1d | -8.7% | 1.5% | 17.0% | 5.6% | 11.4% | -8.7% |
| pf__kesit_ls / kripto / 1d | -5.3% | 0.4% | 12.6% | 3.2% | 7.5% | -5.3% |
| swing__cci-esik / SOLUSDT / 1d | -1.2% | 0.5% | 5.0% | 0.5% | 1.5% | -1.2% |
| swing__konsolidasyon-kirilim / SOLUSDT / 4h | -2.0% | 0.5% | 3.3% | 1.0% | 2.4% | -2.0% |
| dis__fraktal-alligator-sky / DK_NVDA / 4h | -2.1% | 0.0% | 11.0% | 0.4% | 2.1% | -2.1% |
| **kol: tek_grafik** | -4.0% | 2.9% | 17.8% | 2.4% | 5.5% | -4.0% |
| **kol: portfoy** | -4.4% | 0.4% | 8.9% | 3.0% | 6.0% | -4.4% |

Tüm sayılar (4 ve 8 hafta; net, işlem sayısı, max düşüş, kazanma oranı; %5/%25/%50/%75/%95): `beklenti_araliklari.csv`.

## Nasıl hesaplandı

- **Veri (yalnız örneklem-dışı):** tek-grafik stratejilerde walk-forward test pencerelerinin işlemleri + kilitli dönem (2025-11-01 sonrası) işlemleri; portföy stratejilerinde walk-forward OOS günlük getirileri + kilitli dönem günlükleri. Yeni backtest koşulmadı, mevcut dosyalar okundu: `sonuclar/wf`, `sonuclar/wf_portfoy`, `sonuclar/kilit`.
- **Set / kol hesabı:** yalnız 7 stratejinin de OOS'ta olduğu günlerde (1364 gün, 2022-09-15 → 2026-10-30; walk-forward'ın son tam penceresi ile kilit başlangıcı arasında boşluk var). Tek-grafik kolu tek hesapta, kilit testindeki limitlerle (işlem başı %1, toplam stop riski %5, 3x, günlük %3, kill %20) yeniden oynatıldı; portföy kolu 3 stratejinin eşit ortalaması; kollar 50/50.
- **Yöntem:** blok bootstrap — geçmiş günler 14 günlük bloklar halinde yeniden karıştırılıp 28/56 günlük sahte pencereler üretildi (10000 adet, tohum 42); bloklar, ardışık günlerin birbirine bağlı olmasını korur.
- **Blok uzunluğu duyarlılığı (set, 8 hafta net %5 / %50 / %95):** blok 7: -2.6% / 2.1% / 10.1%; blok 14: -2.6% / 2.0% / 10.4%; blok 28: -2.3% / 2.0% / 10.4%.
- **Tutarlılık kontrolü:** kilitli yıldaki 8 haftalık kayan 307 pencerenin 28 tanesi net alarm eşiğinin altında, 6 tanesi düşüş eşiğinin üstünde (bağımsız değil, kayan pencereler çakışır).

## Dürüst uyarılar

- Set, walk-forward OOS sonuçlarına bakılarak seçildi; bu yüzden aralıklar **iyimser** olabilir. Kilit testinde seçim yönteminin öngörü gücü zayıf çıktı (`sonuclar/kilit/RAPOR.md`).
- Geçmişin yeniden karıştırılması 'gelecek de buna benzer' varsayar. Piyasa rejimi değişirse aralık yanıltır; set için geçmiş yalnız birkaç yıl (çoğu kripto boğa/ayı karışımı).
- Kazanma oranı yalnız işlem kapanan pencerelerde hesaplanır (`oran_hesaplanabilir` sütunu). Portföy kolunun 'işlem'i pozisyon bacağıdır.
- Paper'da ilk 4 hafta çok kısa bir sınavdır; tek başına karar için kullanılmaz.
