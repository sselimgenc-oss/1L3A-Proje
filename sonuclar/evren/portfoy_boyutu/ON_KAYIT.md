# Test A — "Kaç strateji ideal?" — ÖN KAYIT (KEŞİF)

Tarih: 2026-11-11. Meta-test (SEÇİM ÇALIŞIYOR, D̄ +7,92, p 0,046) SONRASI tasarlanmış bir keşif testidir; kilitli canlı planı
DEĞİŞTİRMEZ. Hesaplamadan ÖNCE yazıldı; betiğin sha256'sı koşudan önce eklenip commit edilir. Tek koşu, parametre değişmez.
Betik `araclar/meta_test_secim.py` fonksiyonlarını (veri yükleme, kesimler, G1–G3 kapıları, puan) IMPORT eder; mantığı kopyalamaz.

## SPEC
- Kesimler: meta-testle aynı 11 kesim T_k (2020-05-08 … 2025-05-08), 6 aylık ölçüm penceresi [T_k, T_k + 6 ay). Yalnız < 2025-11-08 veri.
- Her T_k'de G1–G3'ü geçenler (yalnız T_k öncesi veri), puana (geriye bakış t-puanı) göre sıralı.
- N ∈ {1, 2, 3, 4, 6, 8, 10}. İki tür:
  (a) "üst-N": puana göre ilk N (eşitte kimlik sırası);
  (b) "rastgele-N": kapı geçenlerden 2000 rastgele N'li çekiliş (iadesiz, çekiliş içinde), tohum 20261111 (kesim sırası, sonra N sırası).
- Kapı geçen sayısı < N ise o kesim o N için atlanır; atlanan sayısı raporlanır.
- Para hesabı: her strateji 250 USD AYRI kasa; günlük getiri oranı = o günün R(×2) toplamı × 0.015 (işlem başı %1,5 risk; kasa üzerinden bileşik);
  strateji kasası kendi zirvesinden −%30'a inerse (≤ 0,70·zirve; zirve başlangıç kasasını içerir) o strateji pencerenin kalanında durur (değeri sabit);
  tüm kasaların toplamı kendi zirvesinden −%20'ye inerse (≤ 0,80·zirve) hepsi durur. Kontroller gün sonunda. Kaldıraç/marj sınırı MODELLENMEZ.
- Ölçüler (N ve tür başına, kesimler üzerinden): ortalama ve medyan pencere getirisi %; getirinin kesimler arası sd'si (ddof=1);
  ortalama ve en kötü (kesimler arası) portföy max düşüşü %; hesap kill olasılığı; en az bir strateji kill olasılığı
  (hesap durduktan sonra olan strateji kill'leri sayılmaz); ortalama strateji-arası günlük korelasyon (pencere günlük R'leri, Pearson, N=1 yok).
  Rastgele-N'de kesim içi çekiliş dağılımının 5./50./95. yüzdelikleri (getiri ve max düşüş) ve kesimler arası ortalamaları; kesim düzeyindeki
  değer = çekilişlerin ortalaması, olasılık = çekiliş payı.
- Önceden yazılan yorum: "doyma noktası" = ortalama max düşüşteki iyileşmenin bir sonraki N adımında < 1 puan kaldığı en küçük N.
  Tek başına karar değildir; karar/eşik/p yoktur.

## Çıktılar (`sonuclar/evren/portfoy_boyutu/`)
`sonuc.csv` (tür × N × kesim), `ozet_tablo.csv`, `kesim_gecen.csv`, `ozet.json` (girdi hash, commit), `rapor.md`.

## Bilinen sınırlar (önceden)
11 pencere = düşük güç; sonuç sonrası tasarlanmış keşif; evren 2026'da seçildi; kaldıraç/marj yok; kesim kümeleri N'ye göre değişebilir.

## Betik sha256
2de0fdf92f291ac150fd6e0504c043c11881073867348759a633228ffe49e43e  araclar/portfoy_boyutu.py
