# 1L3A v2 — Canlı plan (kullanıcı onaylı, 2026-11-11)

Bu dosya `CANLI_PLAN.md`'nin (4 × 250 USD) **yerini alır**. Kaynak: Öneri Formu (ana plan) + Yönetici Sentezi'nden
3 ek + Fable hakem düzeltmeleri + 11 Kasım testleri. Kullanıcıya sunulan PDF: "1L3A v2 — Güçlendirilmiş Proje Planı".
Bu dosyadaki eşikler sonuç görülmeden önce yazılır; sonradan değiştirilmez (değişiklik = yeni kullanıcı kararı).

## 1. Tanım
Bu bir kâr projesi değil, **yürütme ve ölçüm** projesidir. Kanıtlanmış avantaj yok; küçük parayla sınanmaya değer tek
güçlü aday ewo-ema-ofset. Yapının tamamı long (risk kontrollü "büyük kriptolar çökmez" bahsi). Para öğrenme harcamasıdır.

Dayanak testler (11 Kasım): meta-test + sağlamlık (`sonuclar/evren/meta_test*`), yeni sembol sınavı
(`sonuclar/evren/yeni_sembol/`: 4/4 genelleşmiyor), teşhis (`sonuclar/teshis/`: yalnız ewo düzenli), portföy boyutu
(`sonuclar/evren/portfoy_boyutu/`: strateji sayısı ortalama getiriyi artırmıyor).

## 2. Kadro
| Strateji | Rol | Para | Etiket |
|---|---|---|---|
| dis__ewo-ema-ofset (15m) | Çekirdek | 60 USD (duman) → 250 USD | Tek resmi sınavı geçen ve tek düzenli strateji |
| dis__e0v1en (15m) | Kod sınayıcı | 60 USD; 250'ye yalnız ilk 30 işlem maliyet kontrolüyle | KIRILGAN, ilk emeklilik adayı |
| dis__hma-atr-rider, dis__lube (1d) | Paper'da bekler | Gerçek para yok | KIRILGAN; canlıya geçiş §6 |
Kapsam dışı: scalp, yön bağımsız kol, yeni sembol, yeni strateji araması. Yıl sonuna kadar riskteki para en fazla
≈ 370 USD (60 + 60 + 250); kalan sermaye borsaya yatırılmaz. "6–9 strateji" hedefi kaldırıldı.

## 3. Risk
- İşlem başı risk **%1,5 sabit**. Eski %1,5 → %2 → %3 artış takvimi ve "atlanan > %50 ise %2 ile başla" maddesi
  KALDIRILDI. `risk_adim_kontrol` aracı bu planda kullanılmaz. Zarardan sonra boyut büyütülmez.
- CANLI_LIMITLER aynen: toplam açık stop riski ≤ %6, brüt ≤ 1,5x, günlük −%6 yeni giriş yok, strateji −%30 kalıcı,
  hesap toplamı −%20 kalıcı; izole marj.
- **Büyüme freni (yeni):** toplam canlı sermaye (Σ min(özsermaye, tahsis)) zirvesinden −%10 → yeni kademe ve para
  ekleme durur, kullanıcı gözden geçirir. (Fable önerisi; test edilmedi.)
- Piyasa rejim filtresi (ör. BTC 200g ortalama altı giriş yok) EKLENMEZ: ewo kazancının ≈ üçte biri o bölgede
  (Fable kontrolü; sonuca bakılmış fikir olduğu için ancak yeni ön kayıtla denenebilir).

## 4. Sayısal ölçütler
| Konu | Ölçüt |
|---|---|
| "Yatay" | 12 ayda net sonuç, yatırılan canlı sermayenin −%10 … +%10'u (sunucu gideri ayrı satır) |
| Düşüş | Günlük, açık pozisyonlar dahil, toplam canlı sermaye zirvesinden; hedef ≤ %15 |
| ewo beklenti (250 USD) | 12 ayda −7R … +33R (≈ −26 … +125 USD; medyan ≈ +20R); ≤ −15R → emeklilik incelemesi |
| e0v1en emeklilik | Son 60 işlem ΣR ≤ −10R → uyarı; ≤ −15R → emeklilik; ilk 30 işlemde maliyet > modelin 1,5 katı → emeklilik |
| Diğer emeklilik | Kalıcı kill; canlı–paper ayrışması (< %95 eşleşme); maliyetin modeli aşması. Keyfi kapatma yok |
1R = işlem başı riske edilen para (250 USD'de 3,75 USD; 60 USD'de 0,90 USD). Kaynak: Fable, v2 geliştirme işlem listeleri.

## 5. Sermaye basamakları
| Basamak | Para | Geçiş şartı (hepsi) |
|---|---|---|
| 0. Duman | 2 × 60 USD | Testnet geçildi |
| 1. Ölçüm | ewo 250 USD (+ e0v1en 60) | Duman ölçütleri + 2026-12-08 sadakat + birleşik hesap oynatması |
| 2. Doğrulama | ~5.000 USD | ≥ 6 ay hatasız; canlı–paper ≥ %95; maliyet ≤ 1,5x; kalıcı kill yok; toplam sermaye başlangıcın −%10'undan aşağıda değil |
| 3. İşletme | 20.000 USD+ | ≥ 12 ay; sonuç önceden yazılan beklenti aralığında |
Basamak geçişi her zaman ayrı kullanıcı kararıdır.

## 6. Trend kolunun canlıya geçişi (hepsi; en erken 2027 2. çeyrek, ayrı kullanıcı kararı)
2026-12-08 sadakati + ≥ 6 ay paper; birleşik oynatmada trend dahil hesap düşüşü ≤ %15; R > 3 işlemlerin atlanan payı
≤ %25 (SWING_SECIM: lube %24, hma %54); paper toplamı −10R'nin altında değil. Paper kârı tek başına kanıt sayılmaz.
Kilitli swing seçim kuralı (`CANLI_PLAN.md`) aday sırası olarak geçerli kalır.

## 7. Takvim
| Faz | Tarih | Yapılacak | Bitiş ölçütü |
|---|---|---|---|
| 0. Hazırlık | 25 Kasım'a kadar | Alt hesaplar, kısıtlı API anahtarı, pano kilidi (B18), haftalık rapor aracı | Hepsi hazır |
| 1. Kuru + testnet | 25 Kas – 5 Ara | Önce emirsiz, sonra testnet'te e0v1en | Giriş, stop kurma/yükseltme, kapatma, yeniden başlatma görüldü; stop reddi ve başarısız kapatma zorla denendi |
| 2. Duman | Aralık 1. hafta | ewo + e0v1en, 60'ar USD gerçek para | ≥ 10 giriş, ≥ 1 borsa stopu, 1 yeniden başlatma, stopsuz pozisyon 0, mutabakat farkı 0 |
| 3. Sadakat + birleşik oynatma | 8–20 Aralık | Paper ↔ backtest kontrolü (14 bayat dolum hariç); birleşik hesap oynatması | Geçemeyen büyümez; hesap düşüşü raporu yazılı |
| 4. ewo 250 USD | Tahminen Ocak | ewo büyür; e0v1en 60'ta | 4 hafta rapor; maliyet ≤ 1,5x |
| 5. Değerlendirme | Şubat sonu | e0v1en 30 işlem kontrolü; trend paper raporu | Değerlendirme raporu |

## 8. Araştırma disiplini ve rapor
- Kota doldurulmaz; elenen strateji başka adla geri getirilmez; görülmüş test dönemi yeniden kanıt sayılmaz.
- Her yeni test: kural, maliyet, ret ölçütü önce yazılır, tek koşu. Yılda en fazla 2–3 ön kayıtlı tur.
- Canlı sürerken stratejiye yeni filtre eklenmez.
- Haftalık rapor (`araclar/canli_haftalik_rapor.py`): masraf sonrası net, kaçan sinyaller, maliyet (model vs gerçek),
  canlı–paper eşleşmesi, stratejilerin ortak kaybı, sunucu gideri, §3–§4 eşik uyarıları.

## 9. Yapılmayacaklar
Testnet ve 2026-12-08 atlanmaz · risk %1,5'ten oynatılmaz, martingale/DCA yok · yeni sembol eklenmez, yeni sembol
sınavına bakıp sembol ayıklanmaz · durdurulan strateji ayarı değiştirilip yeniden açılmaz · geçmiş getiri gelir bütçesi
yapılmaz · gizli anahtar asla sohbete ya da repoya girmez.

## 10. En zayıf nokta (Fable)
Plan, sonradan seçilmiş 13 büyük coinde çalışan tek bir long stratejiye (ewo) dayanıyor; avantajı görülmemiş coinlere
taşınmadı. Bu yüzden para küçük tutulur, kanıt canlıdan beklenir.
