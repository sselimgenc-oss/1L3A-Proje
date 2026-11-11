# Birleşik hesap oynatması — ÖN KAYIT (koşudan önce yazıldı ve commit edildi; tek koşu)

Betik: `araclar/canli_birlesik_oynatma.py`  sha256: `9609f6bc367c7c4561030e44f1763177cf7081d52c9772e8c5d3307030d642d6`
Testler: `testler/test_canli_birlesik_oynatma.py` (sentetik). Betikte koşudan sonra değişiklik olursa raporda "SONUÇ SONRASI DEĞİŞİKLİK" başlığı açılır.

## Amaç
CANLI_PLAN "1L3A v2" planında 250 USD adımından önce şart: stratejiler şimdiye dek ayrı kasalarda oynatıldı; toplam hesap düşüşü, -%20 hesap kill'i ve stratejilerin birlikte kaybetmesi ölçülmedi.

## Yöntem (sabit)
- Mevcut yeniden oynatma IMPORT edilir: `canli_boyut_yeniden_oynat.oyna` (CANLI_LIMITLER; işlem başı %1,5 = `canli_olcum_250_15.RISK`; toplam açık stop riski <= %6, brüt <= 1,5x, günlük -%6 yeni giriş yok, strateji -%30 kalıcı kill, asgari emir tutarı altı atlanır). Kopya yok.
- Girdi: `sonuclar/evren/v2/ham/x1|x2` işlem listesi + `mtm/x1|x2` günlük MTM (kum_r): AÇIK POZİSYONLAR DAHİL (günlük MTM). Giriş fiyatı = stop_mesafe / sf. Veri hattı, OLCUM_250_15 ile tek başına 4 strateji için karşılaştırılır (geliştirme kontrolünde kuruş düzeyinde uyum görüldü; senaryo koşusu görülmeden).
- x2 koşusunda boyutlandırmadaki kayma+komisyon da x2 (işlem R'leriyle tutarlı); x1'de x1.
- Her strateji AYRI alt hesap (kasası ayrı). Birleşik seri günlük: K = Σ min(alt hesap özsermayesi, tahsis) (canlı hesap-kill ölçüsü; en çok Σ tahsis); H = Σ özsermaye (kâr hesapta kalır). Net % ve H düşüşü H'den; -%10 büyüme freni değme, -%15 aşma, -%20 hesap kill K'dan (H karşılıkları ayrıca). Gerekçe: K mekanik olarak Σ tahsisi aşamaz, bu yüzden net sonuç K'dan okunamaz.
- Hesap kill: K, Σ tahsisten (ortak zirve) >= %20 düşerse o gün sonu hepsi kapanır, sonrası donuk.
- Senaryolar: S1 ewo 250 + e0v1en 60; S2 = S1 + hma-atr-rider 250 + lube 250; S3 = e0v1en, ewo, hma, lube 4 x 250 USD. Hepsinde işlem başı risk %1,5 (hma %2 sorusu kullanıcıda; burada %1,5).
- Dönem: v2 geliştirme, en geç 2025-11-07 (holdout okunursa RuntimeError). Maliyet x2 ANA, x1 EK.
- Pencereler: tüm dönem 2018-01-01..2025-11-07; yıl başı 12 ay (2018..2024 tam yıllar; 2025 yarım, istatistik dışı ayrı satır); 6 ay ve 12 ay kayan (ayda bir kaydır). Her pencere sıfırdan başlar, pencere öncesi giriş yok, pencere sonunda açık işlem MTM'dir. Ortak başlangıç 2018-01-01 (kripto verisi 2017-08'de başlar; 2017 yarım yıl dışarıda).
- Ölçüler: net %, maks düşüş (H ve K), -%10 değme / -%15 aşma / -%20 kill oranları, strateji kill sayıları, 12 ay yıl başı pencerelerde net sonucun -%10..+%10 bandında / üstünde / altında oranı (6 ve 12 ay kayan için de), alt hesap günlük getiri korelasyonu, en kötü 6 ve 12 ay (kayan pencere net minimumu).
- Eşik tanımı: değme >= %10; aşma > %15; kill >= %20 (dahil).
- Denetim (önceden seçildi): S2 x Y2022 x x2, birleşik seri saf-Python ayrı kodla yeniden hesaplanır.
- Uyarı: stratejiler bu dönemde seçildi; sonuçlar ÜST SINIRDIR.
