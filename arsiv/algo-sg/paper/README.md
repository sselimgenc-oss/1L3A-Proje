# Kağıt al-sat botu (A: trend kırılımı + B: kapitülasyon dönüşü)

Gerçek para kullanmadan, canlı piyasa verisiyle **60 gün** boyunca 7/24 al-sat simülasyonu yapar.

## Ne yapar
- **Bütçe:** 10.000 $ sanal bakiye; A'ya 5.000 $, B'ye 5.000 $ (backtest'teki eşit ağırlık).
- **Kurallar:** `algo/final.py` içindeki nihai parametreler, backtest'teki fonksiyonların aynısı.
  - **A:** işlem başına %0.5 risk, en fazla 10 pozisyon.
  - **B:** işlem başına %0.75 risk, en fazla 25 pozisyon.
- **Doğrulama:** 2026-08-01'den başlayan 60 günlük geçmiş dönemde kağıt motoru ile backtest karşılaştırıldı. İkisinde de bulunan işlemler birebir aynı (R farkı 0). Farklar yalnızca dönem başındaki boş portföyden kaynaklanıyor.
- **Masraf ve fonlama:** masraf taraf başına %0.07. Funding OKX USDT swap geçmişinden alınır ve kalan pozisyon kadar uygulanır.
- **Süre:** `paper/config.json` dosyasında `start` + `days` (60). Süre dolunca son değerlendirme raporunu yazar ve durur (`BITTI` dosyası).

## Nasıl çalışır
Her çalıştırmada kağıt döneminin başından bugüne kadar olan tüm **kapanmış** mumlar, backtest koduyla yeniden oynatılır. Kararlar yalnızca kapanmış mumlara dayandığı için sonuç, botun her saat açık olmasıyla aynıdır. GitHub zamanlayıcısı gecikse ya da bir çalıştırmayı atlasa bile hiçbir işlem kaçmaz.

## Veri
- **Fiyatlar:** Binance spot 1h (`data-api.binance.vision`). Binance vadeli API'si GitHub'ın ABD sunucularına 451 hatası veriyor. Spot ile vadeli fiyat farkı yaklaşık %0.01–0.05.
- **Hacim:** 2026-10-01 ile 10-08 arasındaki çakışmadan hesaplanan katsayıyla vadeli ölçeğine çevrilir (`live/volume_scale.json`). Hacim oranı 20 adet 4H mumla hesaplandığı için katsayı yalnızca ilk ~3 günü etkiler.
- **Geçmiş:** `data/1h` (Binance vadeli, 2026-10-08'e kadar) ve canlı mumlar uç uca eklenir.

## Nerede çalışır
- **Zamanlama:** GitHub Actions, `.github/workflows/kagit.yml`, 2 saatte bir (:43).
  - Diğer repodaki bot (`strateji-sg`) saatlik çalışıyor ve aynı hesabın ücretsiz kotasını (ayda 2.000 dakika) paylaşıyorlar. Bu bot ayda yaklaşık 360 dakika kullanır.
- **Durum ve kayıtlar** `kagit-durum` dalında tutulur:
  - `ozet.md`: anlık durum, açık pozisyonlar ve son işlemler
  - `durum.json`: özet metrikler ve backtest beklentisi
  - `pozisyonlar.csv`, `islemler.csv`, `ozsermaye.csv`
  - `live/`: canlı mumlar ve funding
- **Günlük rapor:** "Kağıt al-sat raporu (algo-sg A+B, 10.000 USD)" başlıklı GitHub issue'ya yazılır. GitHub bildirimiyle e-postaya ve telefona gelir.

## Kontrol
- **Hemen çalıştırmak:** Actions → kagit-al-sat → "Run workflow".
- **Durdurmak:** Actions → kagit-al-sat → "…" → "Disable workflow".
- **Sıfırdan başlatmak:** `kagit-durum` dalını silmek yeterli.
- **Yerel deneme (ağ gerekmez):**
  `ALGO_LIVE=/tmp/live PAPER_CFG=<start'ı geçmiş bir tarih olan config> python -m paper.engine --durum /tmp/durum`
