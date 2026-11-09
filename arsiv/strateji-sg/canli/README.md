# Kağıt al-sat botu (KGT v3 + KMN)

Gerçek para kullanmadan, canlı piyasa verisiyle 2 ay boyunca 7/24 al-sat simülasyonu yapar.

## Ne yapar
- **Bütçe:** 10.000 $ sanal bakiye.
  - **KGT v3:** %50, 6 alt portföy (gün başlangıçları 00/04/…/20 UTC, her biri 833 $).
  - **KMN:** %50, 2 defter (A ve B, her biri 2.500 $, 7 gün arayla 14 günde bir dengelenir).
- **Kurallar:** backtest ile aynı fonksiyonlar (`backtest/strateji.py`, `kripto_final.py`, `momentum_sinyal.py`).
  - Motor, backtest motoruyla birebir doğrulandı: 2024'te 221/221 işlem aynı.
  - 2 aylık uçtan uca oynatmada (2025-03 → 2025-05) KGT işlemlerinin 90/90'ı aynı, toplam sonuç farkı %0,3.
- **Masraf ve fonlama:**
  - Masraf taraf başına %0,07.
  - Fonlama 00/08/16 UTC damgalarında uygulanır. Oran OKX vadeli piyasasından alınır, çünkü Binance vadeli API'si GitHub sunucularından erişilemiyor.
- **Mum içi belirsizlik:** aynı saatte 1R kısmi kâr ve başabaş stopu oluşursa 1 dakikalık veriyle çözülür.
- **Süre:** 2 ay (61 gün) sonra kendiliğinden durur ve son raporu yazar.

## Veri
- **Fiyatlar:** Binance spot (`data-api.binance.vision`). Binance'in ana API'si ABD sunucularından 451 hatası veriyor.
  - Yalnız vadelide işlem gören coinler (spot karşılığı olmayanlar) atlanır.
  - `1000PEPEUSDT` gibi semboller spot karşılığıyla (`PEPEUSDT`) eşlenir.
- **Coin evreni:** her ay Binance vadeli arşivinden (S3) bir önceki ayın hacmine göre ilk 40 coin. Backtest ile aynı mantık.

## Nerede çalışır
- **Zamanlama:** GitHub Actions, `.github/workflows/kagit.yml`, her saat :07 ve :37'de (GitHub tetiklemeleri düşürebildiği için iki zaman).
- **Gecikme telafisi:** GitHub zamanlayıcısı bazen gecikir ya da atlar. Bot son işlediği saatten itibaren tüm kapanmış mumları sırayla işler, en fazla 7 gün geriye.
- **Durum ve kayıtlar:** `kagit-durum` dalında; main dalı kirlenmez.
  - `durum.json`: pozisyonlar ve bakiyeler.
  - `islemler.csv`: kapanan KGT işlemleri (R, kâr/zarar, sebep).
  - `ozsermaye.csv`: saatlik değer (KGT, KMN, toplam).
  - `kmn_dengeleme.csv`: KMN dengelemeleri ve hedef ağırlıklar.
  - `ozet.md`: son durum ve açık pozisyonlar.
- **Günlük rapor:** her UTC günü bitince "Kağıt al-sat raporu (KGT + KMN, 10.000 USD)" başlıklı GitHub issue'ya yazılır. GitHub bildirimi olarak e-postaya ve telefona gelir.

## Kontrol
- **Hemen çalıştırmak:** Actions → kagit-al-sat → "Run workflow".
- **Durdurmak:** Actions → kagit-al-sat → "…" → "Disable workflow".
- **Sıfırdan başlatmak:** `kagit-durum` dalını silmek yeterli.
- **Yerel test (ağ gerektirmez, backtest verisiyle):**
  `python3 -m canli.kagit --durum /tmp/d --yerel "2025-03-03 10:00" --saat 240 --adim 6`

## Maliyet
- **GitHub Actions:** özel repo, ücretsiz plan, ayda 2.000 dakika. Bot ayda yaklaşık 720–1.440 dakika kullanır.
