# Test B — Meta-test sağlamlık — ÖN KAYIT (KEŞİF)

Tarih: 2026-11-11. Meta-test (SEÇİM ÇALIŞIYOR, D̄ +7,92, p 0,046; ilk 5 pencerenin 4'ü eksi, son 6 artı) SONRASI, bağımsız gözden geçirenin
önerdiği üç ucuz kontrol. Kilitli canlı planı DEĞİŞTİRMEZ. Hesaplamadan ÖNCE yazıldı; betiğin sha256'sı koşudan önce eklenip commit edilir.
Tek koşu, parametre değişmez. Betik `araclar/meta_test_secim.py` fonksiyonlarını (veri yükleme, kesimler, G1–G3, puan, P_i,k, D_k, işaret çevirme)
IMPORT eder; mantığı kopyalamaz (yalnız dosya/işlem süzgeci ve pencere içi çıkarma eklenir).

## Ortak (meta-testle AYNI)
Ana ölçü D̄ = 11 kesimde D_k = ort P(S_k) − ort P(N1_k) ortalaması (N1'e karşı); işaret çevirme 2^11 = 2048; tek yönlü p_yukarı (p_aşağı da yazılır);
%90 GA (t, sd=10). Kesimler 2020-05-08 … 2025-05-08, 6 aylık pencere, yalnız < 2025-11-08 veri. Kapılar/puan/S_k kuralı (ilk 10, <3 ise N1'den tamamla) aynen.
Kontrol: tam veriyle yeniden hesaplanan D̄ meta-testin D̄'sine eşit olmalı (tolerans 1e-6), değilse DUR.

## Koşular
- **B1 "bilinen büyükler":** yalnız şu enstrümanların işlemleri (geriye bakış + ölçüm; strateji serisi, kapılar ve uygunluk bu enstrümanlarla
  yeniden kurulur): BTCUSDT, ETHUSDT, DK_XAU, DK_XAG, DK_WTI, DK_COPPER, DK_NATGAS, DK_AAPL, DK_MSFT, DK_AMZN, DK_GOOGL, DK_JPM, DK_JNJ, DK_V,
  DK_MA, DK_WMT, DK_XOM. mtm dosya adlarıyla eşleşmeyen varsa raporlanır, liste DEĞİŞTİRİLMEZ.
- **B2 "kazananları çıkar":** her pencere k'da al-tut getirisi en yüksek 5 enstrüman (veri/mumlar günlük kapanışları; başı = T_k'den önceki son
  günlük kapanış, sonu = pencere sonundan önceki son günlük kapanış; o tarihte verisi olmayan enstrüman sıralamaya girmez; evren = mtm dosyası olan
  enstrümanlar, eşitte ad sırası). Bunların işlemleri YALNIZ ölçüm penceresinden çıkarılır (günlük R serisinin [T_k, T_k+6 ay) kısmından); geriye bakış,
  kapılar ve seçim DEĞİŞMEZ.
- **B3 "yalnız short":** yalnız short (yon = −1) işlemler (geriye bakış + ölçüm, kapılar dahil; seri/uygunluk yeniden kurulur).
  Ek tablo: her kesimde S_k'nin (tam veri, meta-test S_k'si) long işlem payı vs N1'in (tam veri) — havuzlanmış işlem sayısıyla; iki görünüm:
  geriye bakış (çıkışı T_k'den önce) ve ölçüm (girişi pencerede).

## Önceden yazılan yorum
Üçünde de D̄ > 0 ise "evren/long şüphesi büyük ölçüde zayıflar". Biri ≤ 0 ise: B1 → sonuç küçük/az bilinen enstrümanlara (evren etkisine) bağlı olabilir;
B2 → üstünlük birkaç büyük kazanana bağlı; B3 → üstünlük long yönünden (yükselen piyasa) geliyor. Eşik/p kararı yok.

## Çıktılar (`sonuclar/evren/meta_test_saglamlik/`)
`sonuc.csv` (kesim başına D_k ve sayılar), `long_payi.csv`, `b2_kazananlar.csv`, `ozet.json`, `rapor.md`.

## Bilinen sınırlar (önceden)
11 pencere = düşük güç; süzülmüş verilerde kapı geçen sayısı az olabilir (S_k çoğunlukla N1'den tamamlanır); sonuç sonrası tasarlanmış keşif.

## Betik sha256
1e0932e317ecb37354968c651e3b4d4f9e2e1df72f532d3048441494fd0d162e  araclar/meta_test_saglamlik.py

Not: ilk koşu `yon_tablosu` adımında (B3 ek long-payı tablosu) KeyError ile çöktü; hiçbir sonuç yazılmadan/görülmeden. Neden: pf__ (portföy) satırlarının
ham dosyasında işlem sütunları yok; `yon_tablosu` havuz kuralını (mtm'siz satırları atla) uygulamıyordu. Yalnız bu süzgeç düzeltildi (parametre/kural
değişmedi); sha256 yukarıda düzeltilmiş betiğindir.
