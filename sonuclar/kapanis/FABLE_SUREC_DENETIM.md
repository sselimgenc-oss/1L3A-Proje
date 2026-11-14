# Fable süreç denetimi (kapanış koşusu)

## 2026-11-13 23:20 UTC
- İlerleme A1: 318/365 json. Uzun TF 317/318 (kalan tek kayıt: KOD:v3__donchian-ansambl-vol-hedef, pf 1d, ~50 dk'dır tek işçide; pf rastgele testi yavaş, izlenmeli). Kısa TF: 5m 1/29, 15m 0/15, 30m 0/3 (bekliyor).
- İlerleme A2: 27/96. 4h 13/13, 1d 6/6, 6h 2/2, 1h 6/56 (son 35 dk'da 8 kayıt, 3 işçi), 5m 0/18, 30m 0/1. Ortalama süre: 1d ~20 sn, 4h ~95 sn, 1h A1 ~400 sn (en çok 1852 sn), tek 5m 919 sn.
- HATA A1: 7 (A2: 0). (a) 4 kayıt (HAM:X005:757/184/792/493, 1d): `'dict' object has no attribute 'atr_iz_suren_k'` = parametrelerdeki `cikis_ayarlari` sözlüğü CikisAyarlari nesnesine çevrilmiyor: ALTYAPI HATASI, strateji ölçülmedi. (b) 3 funding pf kaydı: `funding_orani eksik` (BTC/ETH/SOL): veri yükleme eksiği, altyapı/veri. V001:225 henüz koşulmadı.
- HATA kayıtlarında p=1, k1–5 boş: BH paydasında kalır, kapı geçemez (temkinli yön). Ön kayıt gereği sessiz yeniden koşu yok; düzeltilirse `sonuç sonrası` etiketi gerekir. Karar kullanıcıya sorulmalı.
- Kapı bayrakları: tek-grafik TAMAM kayıtlarının tümünde k1/k2/k4/k5 metriklerden yeniden hesaplandı: A1 0 uyumsuz, A2 0 uyumsuz.
- Kapı 6: A1 309 testte p<=0,05 182 (%59), T<0&p<=0,05 34: TESHIS_KAPI6 ile birebir aynı sayılar. A2 19/27 (%70), T<0 4. T>0 iken p>0,5 örnekleri de var (yön tutarlı). B=100000, gecersiz_oran 0. k1–5 VE p<=0,05: A1 33 (çoğu 1d, p tabanda 1e-5), A2 5. Şüpheli yeni örüntü yok; tek başına k6 anlamlı sayılmamalı (teşhisle aynı).
- Ek 8/9: iki süreç de `--tf-haric 5m,15m,30m` ile çalışıyor; kısa TF koşulmuyor (uyumlu). Tek istisna HAM:X005:15#v1 (5m) ek 8'den önce bitmiş, k6 koşulsuz almış: ek 9 son maddesine uygun. ATLANDI_K1_5 henüz hiç kayıtta yok (kod yolu `kapanis_kosu.py:311`, bayrak `--k6-on-eleme-tf`); kısa TF başlatılırken bu bayrağın verildiği doğrulanmalı.
- Sonuç: DURDUR gerektiren bulgu yok. Açık iş: 7 HATA'nın (özellikle 4 `cikis_ayarlari` kaydı) akıbeti ve kısa TF koşusunun bayrağı.

## 2026-11-14 00:15 UTC
- İlerleme A1: 318/365 (uzun TF 317/318; 7 düzeltme yeniden koşuldu). A2: 48/96 (uzun TF 48/77; son 30 dk 17 kayıt, 3 işçi; 1h ort. ~490 sn). Tahmin: A2 uzun TF ~80 dk (≈01:35), ardından kısa TF (A1 47 + A2 19 kayıt, k6 ön elemeli) kabaca 1–3 saat.
- HATA: A1 0, A2 0 (tüm JSON'lar TAMAM). `_hata_v1/` 7 eski kayıt yerinde.
- Düzeltilmiş 7 kayıt: hepsinde `sonuc_sonrasi_duzeltme` var, B=100000, metrik dolu. k1/k2/k4 metriklerden yeniden hesaplandı: 7/7 uyumlu. k1–5 geçen tek kayıt HAM:X005:792 (net +0,64, PF 1,39, 566 işlem, p=0,00074); 184 PF 1,17 ile k1'de kalıyor; 3 funding pf'si negatif net, kill 1, p 0,30–0,48. Raporda "sonuç sonrası" etiketiyle ayrı gösterilmeli.
- Kapı bayrakları: A1 318 + A2 48 kaydın tümünde k1/k2/k4, k3=k3a∧k3b yeniden hesaplandı: 0 uyumsuz.
- Kapı 6: A1 tek-grafik 313 testte p<=0,05 184 (%59), T<0&p<=0,05 34 (değişmedi). A2 48 testte p<=0,05 40 (%83), T<0&p<=0,05 18; 1h'de 24/27. A2'de (1h Robotic) kapı 6 neredeyse ayırt etmiyor: teşhisle (rastgele giriş maliyet sürüklenmesi) aynı yön, sıklık arttıkça güçleniyor. k1–5 VE p<=0,05: A1 34, A2 6. Karar yine k1–5 + BH + ikinci kapıya dayanmalı; raporda açıkça yazılmalı.
- KOD:v3__donchian-ansambl-vol-hedef TAKILMAMIŞ: `_kismi/.../a2/sharpe.npy` 45 sn'de 7125 → 7150 (hedef 10000, ~2000/saat) → ~85 dk kaldı (≈01:40). a1 (B=500) p<=0,02 çıktığı için ikinci aşamada; yavaşlık pf simülasyonunun doğası.
- UYARI (DURDUR değil): zincir betiği A1 bitince `--asama 2 --isci 4`'ü yeniden başlatacak; A2 zaten ayrı süreçte (3 işçi) koşuyor ve koşucuda kilit yok (yalnız "JSON var mı" bakıyor). İkisi çakışırsa süren kayıtlar çift koşulur, aynı `_kismi` dizinine yazılır, CPU 7 süreç/4 çekirdek olur. Sonuç tohumlu olduğundan değişmemeli ama kısmi dosya bozulma riski var: A1 bitmeden zincirin 2. adımı çıkarılmalı ya da A2 bitene kadar bekletilmeli. Kısa TF adımlarında `--k6-on-eleme-tf 5m,15m,30m` bayrağı zincirde mevcut (doğrulandı).
- Sonuç: DURDUR gerektiren bulgu yok.

## 2026-11-14 01:12 UTC
- İlerleme A1: 318/365 (uzun TF'de kalan tek kayıt donchian pf). A2: 67/96 (uzun TF 67/77; son ~60 dk 20 kayıt, 3 işçi) → kalan 10 kayıt ~30–40 dk.
- Donchian TAKILMAMIŞ: `a2/sharpe.npy` 7150 → 9100/10000 (57 dk'da ~1950, hız sabit), dosya taze → ~25–30 dk kaldı (≈01:40).
- HATA: A1 0, A2 0 (yeni 20 kaydın tümü TAMAM; kosu2.log'da hata satırı yok; kosu.log'daki 7 eski, düzeltilmiş).
- Çift koşu YOK: A1 için tek süreç (pid 8645, `--tf-haric 5m,15m,30m`), A2 için tek ana süreç (13942) + 3 işçi; zincir betiği süreç listesinde yok. Toplam 4 yoğun süreç / 4 çekirdek.
- Kapı bayrakları (yeni 20 A2 kaydı, k1/k2/k3a/k3b/k3/k4/k5 yeniden hesaplandı, B=100000, gecersiz_oran 0): 1 görünür fark, HAM:B001:817#v1 k1=True iken JSON'da pf_x2=null (3 işlem, kayıp yok → PF sonsuz, JSON'a null yazılmış). Koddaki karar doğru olabilir, sonuç değişmez (k2 3<200 ile kalıyor); raporda PF "sonsuz/tanımsız" diye gösterilmeli. Diğer 19 kayıt uyumlu.
- Kapı 6 (yeni 20): p<=0,05 17, bunların 11'i T<0; k1–5 VE p<=0,05: 0. Önceki teşhisle aynı yön (1h'de kapı 6 ayırt etmiyor). Sonuç: DURDUR gerektiren bulgu yok.

## 02:12 UTC
- Ek 9 uygulaması DOĞRU (A1, 01:56'dan beri koşulan 26 kısa TF kaydı): hepsi k1–5'ten en az birini kaçırmış, hepsi `ATLANDI_K1_5`, p=1; uzun TF'de ATLANDI_K1_5 yok. k1–5'in hepsini geçen kısa TF kaydı henüz HİÇ yok → "geçen kapı 6 alır" yolu canlıda henüz sınanmadı (ilk geçen kayıtta bakılmalı).
- Tutarsızlık (ciddi değil): HAM:X005:15#v1 (5m, A1) ek 9 öncesinden (13 Kas 15:57) kalma; k1–5'i geçmediği hâlde kapı 6 almış, p=1e-5. Sonuç değişmez (zaten eleniyor) ama tabloda diğer kısa TF'lerle aynı görünmesi için ya p=1/ATLANDI'ya çevrilmeli ya dipnot düşülmeli. Ayrıca `kosu_asama1/_kismi/` içinde 19:27–19:36'dan kalma bayat X005:16, X005:18 klasörleri var.
- YENİ HATA 1 (A2): HAM:V001:225#v1 (1h) "desteklenmeyen çıkış (rastgele giriş testi yok): stop_sonrasi_bekleme_mum" → durum HATA, p=1. Çökme değil, kontrollü; raporda "test edilemedi" diye ayrı sayılmalı, "başarısız" diye değil. A1'de yeni hata 0 (kosu.log'daki 7 eski).
- İlerleme: A1 347/365, kalan 18'in hepsi 5m; hız ~26 kayıt/14 dk → ~10 dk (kapı 6 alan çıkarsa uzar). A2 76/96; kalan 18×5m + 1×30m + 1×1h. A2 kısa TF koşusu henüz BAŞLAMADI (A2 süreci hâlâ `--tf-haric`) → A1 bitince ayrıca başlatılmalı, ~15 dk daha.
- İzlenecek: A2'nin son uzun TF kaydı HAM:B001:842 (1h) 01:43'ten beri sürüyor, `_kismi`'de tek dosya (ADAUSDT, 01:52), 19 dk'dır yenisi yok; işçi %99 CPU'da, yani çalışıyor ama yavaş. 02:30'a kadar ilerlemezse takılma say.
- Çift koşu YOK: A1 (pid 15650, `--k6-on-eleme-tf`, 3 işçi) ve A2 (pid 13942, `--tf-haric`, 3 işçi, yalnız 1'i aktif) ayrı listeler; yük ort. 4,2 / 4 çekirdek. DURDUR gerektiren bulgu yok.

## 03:12 UTC
- A1 TAMAMLANDI: 365/365 JSON, 365 tekil kimlik, bozuk dosya yok, durum 365 TAMAM / 0 HATA (7 eski hata `_hata_v1/`'de, düzeltilmişleri koşulmuş). k3=k3a∧k3b 0 uyumsuz.
- Ek 9 (A1 kısa TF 47 kaydın tamamı): 45'i k1–5'ten kalıp `ATLANDI_K1_5`, p=1; k1–5'i geçen tek kayıt HAM:X005:576#v1 (5m) kapı 6 almış (p=1e-5) → "geçen kapı 6 alır" yolu artık canlıda doğrulandı. Tek istisna yine HAM:X005:15#v1 (ek 9 öncesi, kalmış ama kapı 6 almış; sonucu değiştirmez, dipnot gerek). Uzun TF'de ATLANDI yok. `kosu_asama1/_kismi/`'de 13 Kas'tan bayat X005:16, X005:18 klasörleri duruyor (zararsız).
- A2: 84/96, 83 TAMAM + 1 HATA (HAM:V001:225#v1, bilinen "desteklenmeyen çıkış"; yeni hata yok). Kısa TF 8 kayıt: 5 ATLANDI_K1_5 (p=1), 3'ü (B001:205/558/561, 5m) k1–5'i geçip kapı 6 almış, p=1e-5: bayrak/durum tutarlı. Kalan 11 kısa TF + 842.
- Çift koşu YOK: iki A2 süreci ayrık kümelerde (pid 16937 `--tf-haric 1h,4h,6h,1d` 2 işçi → yalnız kısa TF; pid 17183 `--tf-haric 5m,15m,30m` 1 işçi → yalnız 842); kosu2.log'da yinelenen kimlik yok; A1 süreci kalmadı. 3 yoğun süreç / 4 çekirdek.
- UYARI (DURDUR değil): HAM:B001:842 çok yavaş: `_kismi`'de 13 semboldan 2'si bitti (ADA 01:52, BCH 02:21 → ~29 dk/sembol; kısa TF 673'te sembol 15–60 sn). 02:46'daki yeniden başlatmadan beri 25 dk'dır yeni dosya yok. Bu hızla ~5 saat daha (≈08:00). Bekleme/erteleme kararı kullanıcıya sorulmalı; A2 birleştirmesi bu kayıt olmadan eksik kalır.
- Zincir: kısa TF A2 bitince `--birlestir` (varsayılan `--asama 1`) başlayacak; A1 tam olduğu için sorun yok, 842 ile aynı anda koşacak (CPU yeter). Sonuç: DURDUR gerektiren bulgu yok.

## 2026-11-14 04:11 UTC
- A2: 89/96 (88 TAMAM + 1 bilinen HATA V001:225; yeni hata yok, günlükte tek HATA satırı o). Son denetimden beri 5 yeni kayıt (B001:673/564/570/574/590, hepsi 5m): k1–5 true, `k6_durum=TAMAM`, B=100000, p=1e-5, `desteklenmeyen=[]`, geçersiz oran 0, kill 0 → bayrak/durum tutarlı; ek 9 doğru (k1–5 geçen kapı 6 almış, yeni ATLANDI yok). Kalan: 6 kısa TF (670 11/13 sembol, 573 4/13) + 842.
- Çift koşu YOK: aynı iki ayrık süreç (pid 16937 kısa TF 2 işçi; pid 17183 yalnız 842), yük 3.1/4 çekirdek, günlükte yinelenen kimlik yok.
- UYARI (DURDUR değil): 842 daha da yavaşladı: 4/13 sembol (BNB 03:21 → BTC 04:02 ≈ 41 dk/sembol); kalan 9 sembol ≈ 6 saat (≈10:00 UTC), önceki 08:00 tahmini tutmuyor. Bekle/ertele kararı kullanıcıya sorulmalı.
- Not (doğrulanmadı): `r_enstruman` 673'te 13 sembol (HYPE dahil), 564/570/574/590'da 12 (HYPE yok). Muhtemelen işlemsiz sembol yazılmıyor; raporda "13 enstrüman" denmeden önce kodda teyit edilmeli. Sonuç: DURDUR gerektiren bulgu yok.
