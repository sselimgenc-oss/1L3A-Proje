# Swing kağıt al-sat botu (10.000 $, 60 gün)

Gerçek para kullanmadan, canlı piyasa verisiyle **60 gün** boyunca 7/24 swing sistemini işletir.

- **Kurallar:** `swing/ayarlar.py` içindeki seçili parametreler. Backtest'teki fonksiyonların aynısı
  (`swing/stratejiler.py`, `swing/motor.py`). Portföy kuralları da aynı: işlem başına %1 risk, en fazla 10 pozisyon,
  tek pozisyon ≤ %20, toplam ≤ %100 (kaldıraç yok), aynı varlıkta tek pozisyon.
- **Süre:** `kagit/config.json` (`baslangic` + `gun`). Süre dolunca son değerlendirme raporunu yazar ve durur (`BITTI`).

## Nasıl çalışır
Her çalıştırmada veriler yeniden indirilir ve kağıt döneminin başından bugüne kadar olan tüm **kapanmış** günlük
mumlar backtest koduyla yeniden oynatılır. Kararlar yalnızca kapanmış mumlara dayandığı için bir çalıştırma
kaçsa ya da gecikse bile hiçbir işlem kaçmaz; sonuç bot sürekli açıkmış gibidir.

## Nerede çalışır
- **Zamanlama:** GitHub Actions, `.github/workflows/kagit.yml`, günde 2 kez (UTC 00:23 ve yedek 12:23;
  00:23 itibarıyla kripto, BIST ve ABD günlük mumları kapanmıştır). Ayda ~120 dakika; ücretsiz kota
  (2.000 dk) strateji-sg ve algo-sg botlarıyla ortaktır.
- **Durum dalı `kagit-durum`:** `ozet.md` (anlık durum, açık pozisyonlar, bekleyen emirler, son işlemler),
  `durum.json`, `islemler.csv`, `pozisyonlar.csv`, `ozsermaye.csv`.
- **Günlük rapor:** "Kağıt al-sat raporu (swing-sg S1+S2+S3, 10.000 USD)" başlıklı GitHub issue'ya yazılır.

## Kontrol
- **Hemen çalıştırmak:** Actions → kagit-al-sat → "Run workflow".
- **Durdurmak:** Actions → kagit-al-sat → "…" → "Disable workflow".
- **Sıfırdan başlatmak:** `kagit-durum` dalını silmek yeterli.
- **Yerel deneme:** `KAGIT_BASLANGIC=2026-08-01 python -m kagit.motor --durum /tmp/durum`
