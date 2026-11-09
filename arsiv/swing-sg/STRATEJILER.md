# Swing Trading Sistemi — Doküman Analizi ve Strateji Kuralları

Bu sistem `metinler/` klasöründeki 35 kitabın/dokümanın metinlerinden çıkarılan **ortak paydalar** üzerine kuruldu.
Çerçeve: **haftalık grafikte yön, günlük grafikte işlem.**

## 1. Dokümanlardaki ortak paydalar

Kavramların kaç dokümanda geçtiği (`metinler/` üzerinde metin taraması):

| Kavram | Geçtiği doküman sayısı |
|---|---|
| RSI | 34 |
| Destek/direnç | 32 |
| Geri çekilme (pullback) | 30 |
| Haftalık zaman dilimi | 30 |
| Hacim | 29 |
| Hareketli ortalama | 27 |
| Boşluk (gap) | 25 |
| Risk/ödül oranı | 22 |
| ATR (ortalama gerçek aralık) | 19 |
| Stokastik / MACD / Bollinger | 15 / 14 / 14 |
| Kırılım (breakout) | 14 |

Dokümanların neredeyse hepsinin üzerinde birleştiği beş ilke:

1. **Çoklu zaman dilimi — "haftalığa bak, günlükte işlem yap".** Lee & Tryde (*Swing Traderlar için Zamanlama
   Çözümleri*, böl. 7): *"Haftalık grafikler piyasa yapısını tanımak ve devam eden eğilimi belirlemek için
   kullanılır… Kural, günlük fiyatın bir sonraki daha yüksek zaman diliminin eğilim yönünde, yani haftalık olarak
   işlem yapmaktır."* Kathy Lien, Christopher (*Geçimini Sağlamak için Swing Trading*), Munroe (haftalık Heikin
   Ashi + 100 SMA), Farley ve Elder (Simon Jordan ve Lee & Tryde içinde alıntılanan Üçlü Ekran) aynı yapıyı önerir.
2. **Trend yönünde işlem, karşı trendde değil.** TMP RSI rehberi (*"kısa vadeli trendleri uzun vadeli trendlere
   karşı zayıflat"*), Ladha (*"Asla piyasayla kavga etmeyin"*), Lee & Tryde, Velez, Rivalland.
3. **Genel piyasanın (endeksin) durumu önce kontrol edilir.** Ladha Strateji 2 ve 3: kırılımlar ve dip alımları
   yalnızca endeks (NIFTY vb.) 50 günlük ortalamasının üzerindeyken / teyit edilmiş yükseliş trendindeyken.
4. **Üç tekrarlayan giriş kurulumu:**
   - Yükselen 10/20/50 EMA'ya **geri çekilmede alım** (Ladha S3, Farley, Velez, Ghosh *Bounce*, Leandro, Ochoa);
   - Daralma/konsolidasyon sonrası **10–20 günlük zirve kırılımı** (Ladha S2, Boxer, Bulkowski, Farley NR7,
     Jea Yu, Kathy Lien);
   - Trend içindeki **aşırı satımdan dönüş** — RSI/Stokastik/Bollinger alt bant (Munroe, TMP, Ladha S10,
     Thomsett, Graham, Velez).
5. **Risk yönetimi:** işlem başına sermayenin %0,5–1'i (Ladha, Farley), stop fiyat yapısının/ATR'nin altına,
   **kârın bir kısmını erken alıp kalanı izleyen stopla taşıma** (Ladha: *"girişinizden 2,5–5 işlem günü sonra
   yarısını satıyoruz… kalan 10/20 günlük EMA ile takip edilebilir"*; Farley, Velez ölçekli çıkış), 2–20 günlük
   tutma süresi (Leandro: *"2 ila 10 gün arası hareketler"*; TMP: *"3 haftadan fazla olamaz"*).

Bu ortak paydalardan **üç strateji** türetildi; her biri farklı bir piyasa davranışını (trend devamı, volatilite
genişlemesi, kısa vadeli ortalamaya dönüş) yakaladığı için birbirini tamamlar.

## 2. Ortak çerçeve (tüm stratejiler)

- **Haftalık yön:** Haftalık mumlar (hafta Pazar kapanır). Bir gün için yalnızca *tamamlanmış* son hafta
  kullanılır (ileriye bakma hatası yok).
  - `ha` (Munroe): haftalık Heikin Ashi mumu yeşil **ve** haftalık kapanış 20 haftalık SMA (~100 gün) üzerinde.
  - `ema10_30` (Lee & Tryde / Elder): haftalık EMA10 > EMA30 **ve** kapanış EMA30 üzerinde.
- **Piyasa rejimi (Ladha):** varlık sınıfının referans endeksi de yükselişte olmalı —
  kripto → BTC, Magnificent 7 → Nasdaq-100, BIST → BIST 100 (USD), emtia → filtre yok.
- **Emir zamanlaması:** sinyal günlük kapanışta oluşur, emir **ertesi gün açılışta** (S3'te limit emir).
- **Pozisyon büyüklüğü:** her işlemde özsermayenin **%1'i** riske edilir (giriş–stop mesafesine göre adet),
  tek pozisyon en fazla özsermayenin %20'si, toplam maruziyet ≤ %100 (kaldıraç yok), en fazla 10 açık
  pozisyon, aynı varlıkta aynı anda tek pozisyon.
- **Maliyet (tek yön):** kripto %0,10, Mag7 %0,05, BIST %0,15, emtia %0,05 (komisyon + kayma).
- Yalnızca **uzun (alım)** yönlü işlem; açığa satış testlerde değer katmadı ve BIST'te pratik değil.

## 3. Stratejiler

### S1 — Trend Geri Çekilme (Pullback)
Kaynaklar: Ladha Strateji 3, Farley, Velez, Ghosh (*Bounce*), Leandro, Ochoa, Lee & Tryde.

| Adım | Kural |
|---|---|
| Haftalık yön | `ha`: haftalık Heikin Ashi yeşil + kapanış 20 haftalık SMA üzerinde |
| Piyasa rejimi | Sınıf endeksinin haftalık Heikin Ashi yönü yukarı |
| Günlük trend | Kapanış > EMA50, EMA10 > EMA50, EMA50 5 gün öncesinden yüksek |
| Geri çekilme | Son 3 günde düşük, EMA10'a 0,3 ATR yakınlığa kadar indi **ve** RSI(14) son 3 günde < 65 |
| Tetik | Kapanış, önceki günün en yükseğinin ve EMA10'un üzerinde (dönüş teyidi) |
| Giriş | Ertesi gün açılış |
| Stop | min(son 4 günün dibi, kapanış − 1 ATR) − 0,5 ATR |
| Kâr alma | +1R'de pozisyonun yarısı satılır, stop başabaşa çekilir |
| Çıkış | Kapanış EMA50 altına inerse ertesi açılış; en fazla 30 gün |
| Varlıklar | Kripto, Mag7, altın/petrol |

### S2 — Sıkışma Sonrası Kırılım (Breakout)
Kaynaklar: Ladha Strateji 2, Boxer, Bulkowski, Farley (NR7 / daralma), Jea Yu, Kathy Lien.

| Adım | Kural |
|---|---|
| Haftalık yön | `ema10_30`: haftalık EMA10 > EMA30 + kapanış EMA30 üzerinde |
| Piyasa rejimi | Sınıf endeksinin haftalık EMA10 yönü yukarı |
| Daralma | Son 5 gün içinde ATR(5)/ATR(50) < 0,9 (volatilite sıkışması) |
| Tetik | Kapanış önceki 20 günün en yükseğinin üzerinde, hacim ≥ 20 günlük ortalama, kapanış günlük aralığın üst %40'ında |
| Giriş | Ertesi gün açılış |
| Stop | Kapanış − 2 ATR |
| Kâr alma | +1,5R'de yarısı satılır, stop başabaşa |
| Çıkış | İzleyen stop (en yüksek kapanış − 4 ATR) veya kapanış 20 günlük dibin altına inerse; en fazla 30 gün |
| Varlıklar | Kripto, Mag7, BIST, altın/petrol |

### S3 — Trend İçinde Aşırı Satım Dönüşü (Bounce)
Kaynaklar: Munroe (Heikin Ashi + Stokastik), TMP RSI rehberi, Ladha Strateji 10, Thomsett, Graham, Velez.

| Adım | Kural |
|---|---|
| Haftalık yön | `ha`: haftalık Heikin Ashi yeşil + kapanış 20 haftalık SMA üzerinde |
| Piyasa rejimi | Sınıf endeksinin haftalık EMA10 > EMA30 |
| Uzun trend | Günlük kapanış > SMA200 |
| Tetik | RSI(2) < 10 (kısa vadeli aşırı satım) |
| Giriş | Ertesi gün **limit emir**: kapanış − 0,5 ATR (dolmazsa iptal) |
| Stop | Limit fiyat − 2 ATR |
| Çıkış | Kapanış SMA10 üzerine çıkarsa veya RSI(2) > 70 olursa ertesi açılış; en fazla 10 gün |
| Varlıklar | Kripto, Mag7 |

### Neden BIST yalnızca S2 ile işleniyor?
BIST fiyatları TL bazında yüksek enflasyon nedeniyle sürekli yukarı kayıyor; bu, TL bazlı backtest'i yapay
olarak güzelleştiriyor. Sistem BIST'i **USD'ye çevrilmiş fiyatlarla** değerlendirir. USD bazında S1 ve S3,
BIST'te hem 2015–2022 hem 2023+ döneminde negatif beklenti verdi; S2 her iki dönemde de pozitif kaldı
(ayrıntı: `SONUCLAR.md`). Aynı nedenle emtia S3'ten çıkarıldı (örneklem-içi dönemde negatif).
