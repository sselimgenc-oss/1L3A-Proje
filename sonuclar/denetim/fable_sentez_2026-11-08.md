# Baş denetçi sentezi — 1L3A evren testi ve paper (2026-11-08)

Kaynaklar: 7 boyutun 42 doğrulanmış bulgusu (3'ü tekrar: Telegram token, günlük özet saati, holdout mührü — birleştirildi), `sonuclar/evren/2017_gelistirme/wf_evren.csv` ön sonuçları (735 satır; swing 380 → 44 geçen, daytrade 336 → 5 geçen hepsi 30m, portföy 19 → 1; scalp hâlâ koşuyor), DURUM.md ve ON_KAYIT.md. Yalnız okuma yaptım; arka plan koşusuna dokunmadım.

Kısa yorum: boru hattının omurgası sağlam (OOS sızıntısı yok, maliyet tablosu sabit, holdout tek seferlik, sert limitler kodda ve testli, martingale yapısal olarak imkânsız, repoda anahtar yok). Sorunlar üç kümede toplanıyor: **(A)** sağlamlık/holdout aşaması koşulmadan önce karar gerektiren tanım hataları, **(B)** seanslı (hisse/BIST) veride "zaman = mum sayısı" varsayımının her yerde kırılması, **(C)** paper'ın backtestten sessizce ayrışması ve çökmede sessiz kalması.

---

## 1. Denetim özeti (ciddiyete göre)

### Yüksek

**Y1. K5 DSR kapısı mevcut tanımla geçilemez → iyi/iyiye yakın listeleri kesin boş çıkar**
`motor/arastirma/wf_evren.py:1183-1189, 1070-1078, 729-737`; `saglamlik.py:494-497`
Deneme sayısı N ≈ 223.000 ve V (WF satırlarının OOS Sharpe varyansı) ile "şansla beklenen en yüksek Sharpe" (SR0) yıllık ≈ 3.2 çıkıyor. WF'yi geçen 50 stratejinin en iyisi 1.90. Her satır K5'ten kalır → iki liste de boş → seçim ve holdout koşacak şey bulamaz. Ayrıca N ve V farklı popülasyonlardan (N sembol-çarpanlı eski denemeler + çarpansız yeni, V ise yalnız WF kazananları). ~2 günlük koşunun sonunda "hiçbir şey yok" çıkar ve eşiği o zaman değiştirmek "sonuç görüldükten sonra yöntem değiştirme" olur. **Karar sağlamlık koşulmadan ÖNCE alınmalı.**

**Y2. Seanslı veride "gün sonu mumu" hiç tespit edilmiyor → daytrade/scalp hisse sonuçları tanım dışı bir stratejiyi ölçüyor**
`motor/strateji/daytrade/_ortak.py:23-36`, `onceki/_ortak.py:46-56`
Kural yalnız 7/24 veride çalışıyor; DK_AAPL 1h'de 0 işaret (gerçek veriyle doğrulandı). ~41 strateji dosyası (daytrade/scalp tamamı + gap stratejileri) hisselerde pozisyonu gece/hafta sonu taşıyor; ORB'de 62 işlemin 50'si gece taşındı; gap-devam hisselerde hiç sinyal üretmiyor. Şu an koşan daytrade sonuçlarının hisse ayağı ve scalp'in SPX/XAU/WTI ayağı bu hatayla ölçülmüş. Paper'da (Binance perp 7/24) ise gün sonu UTC gece yarısında tetiklenir → araştırma ≠ paper.

### Orta — araştırma yöntemi

**O1. K2 rastgele giriş tutma süresi seanslı veride ~5 kat şişiyor** — `wf_evren.py:961-1001`, `saglamlik.py:166-172`. Takvim zamanı/medyan aralık = mum sayısı varsayımı; hisse 1h'de 1 gün = 24 mum = ~5 seans. Long stratejiler haksız kalır, short'lar haksız geçer. Sağlamlık henüz koşulmadı → şimdi düzeltmek ön kayıtlı kuralın ("aynı tutma süresi") doğru uygulanmasıdır.

**O2. Kısmi/devam koşuda DSR deneme sayısı bayat kalır** — `wf_evren.py:1199-1203`. Eski satırlar küçük N ile, yeniler büyük N ile hesaplanmış DSR taşıyabilir; kontrol yok, rapor farkı gizler. "Hepsi en sonda birlikte" kararı süreçle önlüyor, kod zorlamıyor.

**O3. Holdout mührü asıl girdileri kapsamıyor** — `wf_evren_holdout.py:29, 60-62, 154-165`. Mühür yalnız 3 CSV + maliyet hash'i; koşulacak ayar (`secimler`) ve dışlanan semboller mühürsüz `wf_evren.parquet`'ten okunuyor; kart/strateji kodu da mühürde yok; wf/portföy/sağlamlık aşamaları holdout başladıysa yazmayı reddetmiyor. Projenin "sonradan değiştirme yok" kuralının tek teknik kilidi bu, ve delik.

**O4. Holdout ve K4'te sembol bazlı hata sessizce yutuluyor** — `wf_evren_holdout.py:105`, `wf_evren.py:1037, 1366`. Sembol düşer, hata sayılmaz; holdout daraltılmış evrende "doğrulanmış" yazabilir. "Sessiz try/except yok" kuralına aykırı.

**O5. BIST: açığa satış serbest, ödünç/finansman maliyeti sıfır, TRY nominal** — `evren_maliyet.py:101-107`. BIST short'ları ve enflasyon kaynaklı TRY trendi genişlik ölçütünde "bist" sınıfını kârlı gösterip stratejiyi geçirebilir; canlı BIST yolu zaten yok.

**O6. Sert limit mantığı 4 ayrı kopyada; seçimi belirleyen `secim.yeniden_oyna` hiçbir motorla eşdeğerlik testine sokulmamış** — `secim.py:336-400`. yeniden_oyna açık pozisyonu nihai R'nin doğrusal yoluyla değerliyor (kazanan işlem hiç zararda görünmez); motorlar gerçek MTM kullanıyor. Kill/günlük limit sıklığı ve max düşüş sistematik farklı olabilir; fark ölçülmeden karar veriliyor.

**Benim ek gözlemim (ön sonuçlardan, güven: orta):** daytrade'de geçen 5 stratejinin **5'inde de** `kill_olayi = 1` (yeniden_oyna'da kill tetiklenince `olu=True`, sonraki tüm girişler reddediliyor; `secim.py:365-383`). Yani bu 5 strateji geliştirme döneminde %20 kill switch'i yemiş, buna rağmen gerçekleşmiş `max_dusus ≤ 0.20` kapısını (0.17–0.20, hepsi sınırda) geçmiş. Paper'da aynı strateji kill switch ile durdurulurdu. Swing'de geçenlerde 0, tüm swing satırlarında %63. ON_KAYIT'ta "kill olayı = 0" diye bir kapı yok; bunu kapı yapmak sonuç-sonrası değişiklik olur → kullanıcı kararı. En azından iyi/yakın listelerinde `kill_olayi` ve `gunluk_limit_olayi` (12–32!) sütunları açıkça gösterilmeli.

### Orta — backtest çekirdeği

**O7. "İşlem başı %1" yalnız fiyat riskini kapsıyor** — `motor/backtest/motor.py:306`. Stop kayması + 2 komisyon eklenince kaldıraç tavanında gerçek kayıp ≈ %1.45; paper/portföy motorunda aynı. Karar 14 metni ile uygulama arasında tanım boşluğu.

### Orta — paper/canlı ve risk

**O8. tur() içinde BinanceHata dışındaki her istisna süreci düşürüyor; systemd 8 denemede servisi kalıcı durduruyor; Telegram uyarısı yok** — `motor/canli/paper.py:412`, `deploy/1l3a-paper.service`. Tek stratejide tek mumda bir istisna 7 stratejiyi birden "dondurur"; açık pozisyonlar stop kontrolsüz kalır; kullanıcı günler sonra fark edebilir.

**O9. Yeniden başlatmada bir sembol TRADING dışına düşerse durum dosyası hiç yüklenemez** — `paper_motor.py:649`. Çökme döngüsü, elle düzeltme gerekir.

**O10. Çok sembollü birimde satır, semboller tamamlanmadan yayımlanıyor; TradFi 300 sn kısıtlayıcı hafta sonundan sonra sembolleri ayırıyor** — `paper_kaynak.py:35`, `paper_canli.py:95-102`. Pazartesi satırında hisse = None → o barın stop kontrolü hiç yapılmaz, hedef emri bir gün gecikir. Hemen her hafta tekrarlanabilir.

**O11. Canlı TradFi yeniden örneklemede Pazar 1d emtia barı üretiliyor, araştırmada yok** — `paper_veri.py:222`, `yeniden_ornekle.py:51`. DK_XAU/DK_WTI ile doğrulandı. pf__kanarya/rotasyon haftada 1 fazla bar işler → backtest ≠ paper.

**O12. `--ayar-guncelle` portföy sütunlarını eski kayıttan alıyor** — `paper.py:251`. Yeni sembol kümesi sessizce yok sayılır.

**O13. Telegram bot token'ı ağ hatasında journal'a sızıyor** — `telegram.py:67` (`%r` ile istisna repr'i URL'yi içeriyor). Repo kuralı karşılanıyor ama sunucu logu düz metin token taşıyor; KURULUM "journalctl çıktısını paylaş" diyor.

**O14. Paper kabul listesi "sert limit ihlali"ni motorun uyguladığı tanımdan farklı (anlık MTM) ölçüyor** — `aylik_rapor.py:158-167`. Kârdaki sabit stoplu pozisyonda stop riski %5'i, kapanış brütü 3.0x'i hiçbir kural kırılmadan aşar → "kaldı" görünür.

**O15. Günlük Telegram özeti 03:10 TSİ'de gidiyor, "Bugün" yalnız 3 saati gösteriyor, her restartta tekrar gidiyor** — `paper.py:387`. Biten günün K/Z'si hiçbir özette yer almıyor.

### Orta — pano

**O16. Backtest payı 0 olan çıkış nedeninde binom p = 0 → tek işlem Koç'ta "beklenti dışı"** — `dersler.py:230`, `koc.py:189-199`. İlk `gunluk_limit` çıkışı (kullanıcı kararıyla ihlal değil) kırmızı bulgu üretir.

**O17. BTC al-tut kıyası sunucuda ~5 günde bayatlar** — `kiyas.py:48`. Paper mumları diske yazmıyor; güncelleyici yalnız DK_SPX için var.

**O18. Kesinti ölçümü bir mum süresi fazla sayıyor** — `aylik_rapor.py:66`. 1d'de tek eksik mum = 48 saat → en erken değerlendirme tarihi haksız kayar (muhafazakâr yönde).

### Düşük (kısa)
- Sharpe yıllıklandırması seanslı veride ~2.2× şişiyor (`metrikler.py:32`) — yalnız tarama/portföy motoru raporlarında; evren kapıları etkilenmiyor.
- Spot vekil döneminde (2017-19) short'lar gerçekçi değil (`wf_evren.py:239`).
- Düşüş/limitler gerçekleşmiş özsermaye + doğrusal yolla iyimser (`secim.py:338`) — ön kayıtlı, ama O6 ve kill gözlemiyle birleşince önemi artıyor.
- K4 komşu testi WF'den farklı evrende (HYPEUSDT dahil) koşuyor (`wf_evren.py:1161`).
- deneme_kaydi "evren" çift kayıt — yalnız bilgi sütunu (`wf_evren.py:934`).
- Walk-forward modülünde pencere bağımsızlığı — modül artık kullanılmıyor.
- Kill switch'te tetikleyen birimin pozisyonu bir bar sonra kapanıyor (`paper_motor.py:526`) — 1d/seanslı için günler; karar 14 metniyle zamanlama çelişkisi.
- TradFi funding paper'da var, backtestte yok (`paper_canli.py:76`); TradFi veri boşluğu hiç olay olmuyor (`tk_acik`, `paper_canli.py:133`); `ws_dogrula` çağrılmıyor; paper emir kopyası sembol bazlı maliyeti desteklemiyor (`paper_motor.py:366`).
- spx_guncelle 404'te mevcut ayı siliyor; panoda sabit "7 strateji" ve %3/%20 metinleri; bir `data-gun` kaçışsız (pratik risk yok).
- Ops: pano-sunucu ilk kurulumda start-limit'e takılır; KURULUM'da l3a ile SSH/mkdir çalışmaz; pano.service çıkış kodu 1'i başarı sayar; paper.service'te anında yükselen hatalarda (418/451/ayar) kalıcı "failed" + alarm yok (10 dk kesinti senaryosu çürütüldü).
- Gerçek veriye bağlı tutarlılık testleri temiz ortamda sessizce atlanıyor.

---

## 2. Öneriler (proje yönü)

**Ö1. Sağlamlık koşulmadan önce DSR kararını al ve ON_KAYIT'a "Güncelleme 6" olarak yaz (WF sonuçlarının görüldüğünü açıkça belirterek).**
Ne: SR0 (yıllık) ve geçenlerin Sharpe dağılımını kullanıcıya göster; üç tutarlı seçenekten birini seçtir: (a) N ve V'yi aynı popülasyondan al (stil×tf grubunun tüm aday-ayar OOS Sharpe'ları; pbo_matrisi zaten üretiyor), önceki denemeler ayrı "bilgi DSR'si"; (b) K5'i yalnız rapor yap, PBO kapı kalsın; (c) kuralı koru ve sonucun boş çıkacağını baştan yaz. Neden: aksi hâlde 2 günlük hesap sonrası boş liste ve zorunlu bir sonuç-sonrası eşik değişikliği. Fayda: holdout'un anlamlı kalması, dürüst kayıt. Maliyet: bir kullanıcı konuşması; **ON_KAYIT Güncelleme 5 (DSR ≥ 0.90 kapı) ile çelişir** — bu yüzden kullanıcı kararı ve açık kayıt şart.

**Ö2. Seanslı veri düzeltmelerini tek pakette yap, sonra daytrade (+ scalp bitince) WF'yi yeniden koş; swing'e dokunma.**
Ne: gün sonu mumu tespitini seans takviminden (`paper_takvim.seans_maskesi`) yap; K2 tutma süresini indeks konumundan hesapla; `pd.Series(idx).diff().median()` kullanan tüm yerleri tara (motor.py:193, htf.py, metrikler.py, _ortak.py); kripto için birebir regresyon testi + hisse için "her seans gününde tam 1 son mum" testi. Neden: daytrade/scalp hisse sonuçları şu an başka bir stratejiyi ölçüyor; paper ile de ayrışıyor. Fayda: daytrade'in gerçek durumu görülür (bugünkü 5 geçen muhtemelen değişir). Maliyet: daytrade/scalp koşusu tekrar (~saatler-1 gün); **"sonuç görüldükten sonra yöntem değiştirilmez" kuralıyla gerilim var** — bu bir hata düzeltmesi (ön kayıt "gün sonu kapanır" der), ama DURUM'a "daytrade/scalp sonuçları görüldükten sonra düzeltildi, eski sonuç arşivde" diye yazılmalı.

**Ö3. Seçim öncesi "limit gerçekliği" bilgi paketi: kill/günlük olayı sütunları, mum tabanlı MTM düşüşü, yeniden_oyna ↔ portföy motoru sapma testi.**
Ne: iyi/yakın listelerine `kill_olayi`, `gunluk_limit_olayi`, `red_*` sütunlarını açıkça koy; işlem bazlı gerçek MTM düşüşünü (MFE/MAE tanımıyla) bilgi sütunu yap; sentetik veride `yeniden_oyna` ile `portfoy_backtest`'in kill/günlük olayı sayısını karşılaştıran test ekle, farkın yönünü ON_KAYIT'a yaz. Neden: 5/5 daytrade geçeni kill yemiş; paper'da bu stratejiler durdurulacak. Fayda: paper'a "zaten ölü" strateji almamak. Maliyet: düşük (seçim kuralına dokunmaz). Not: `kill_olayi = 0`'ı kapı yapmak **ON_KAYIT geçme ölçütleriyle çelişir** → kullanıcıya bilgi olarak sun, kapı kararı onun.

**Ö4. Holdout mührünü genişlet ve yazma kilidi koy — holdout'tan önce.**
Ne: mühre `wf_evren.parquet`, `saglamlik.parquet`, `pbo.csv` sha256'ları + OLCUT JSON hash'i + listedeki stratejilerin kaynak dosya ve kart hash'leri; holdout `secimler`i mühürlü dosyadan okusun; wf/portföy/sağlamlık aşamaları `holdout_baslamis_mi` ise yazmayı reddetsin; holdout/K4/kilit koşularında sembol hatası sayılsın (`n_hata_sembol`, `hata_ornegi`), hata varsa satır "hata" olsun. Ayrıca `saglamlik_asamasi`'na "N değişti → yeniden hesapla / dur" kontrolü. Neden: tek teknik kilit delik; holdout bir kerelik, yanlış koşulursa telafisi yok. Maliyet: düşük-orta. Çalışma dizini git değil; **commit disiplini için git şart** (DURUM commit hash'lerinden söz ediyor, dizinde `.git` yok — netleştirilmeli).

**Ö5. BIST'i seçim kararında "bilgi" sınıfına çek; canlı yolu netleşince ağırlık ver.**
Ne: wf satırına BIST short payı ve BIST netinin toplam içindeki payı; bilgi amaçlı "BIST yalnız long" ve "USD bazlı" koşuları; genişlik ölçütünde "bist" tek başına ikinci sınıf olmasın (ya da ayrıca işaretlensin). Neden: short maliyetsiz, TRY enflasyonu long trendleri şişiriyor, canlı BIST yolu yok. **Karar 27 (BIST evrene eklendi) ve ON_KAYIT Güncelleme 2 (BIST ayrı sınıf, genişlikte sayılır) ile kısmen çelişir** → kullanıcıya sor.

**Ö6. Paper dayanıklılığı: genel istisna yakalama + Telegram "motor hatası" + systemd alarm.**
Ne: `tur()` çevresine `except Exception` (olay yaz, Telegram gönder, aynı hata N kez → kontrollü dur), `finally`'de kalp atışı/kaydet; `durum_yukle`'de bilinmeyen/veri-yok kolu "askıda" taşı; `OnFailure=` birimi ile Telegram; `WatchdogSec` ya da kalp atışı yaşını izleyen timer; `TimeoutStopSec` 120. Neden: tek istisna 7 stratejiyi sessizce dondurur. Fayda: 8 haftalık paper'ın kesintisizlik şartı korunur. Maliyet: düşük. "Sessiz try/except yok" kuralıyla çelişmez (hata yazılır ve bildirilir).

**Ö7. Paper veri yolunu araştırmayla birebir sınayan test ve "satır tamlığı" kuralı.**
Ne: aynı 5m parquet'ten `tf_mumlari` ile `pv.mumlar` çıktısını gün gün karşılaştıran test (hafta sonu, tatil, DST); eksik eşiğini pencere medyanından değil tohumdan türetilen sabit mum sayısından al; birimin satırını tüm semboller gelmeden (ya da zaman aşımı dolmadan) yayımlama, eksikse `veri_bosluk` olayı; `son_kontrol`'ü başarılı fetch'ten SONRA yaz; TradFi funding için karar (kapat / ayrı tut / araştırmaya ekle) ve kaydı. Neden: haftalık, deterministik backtest ≠ paper sapmaları Dersler'de "strateji sapması" gibi okunacak. Maliyet: orta.

**Ö8. Boyutlamaya maliyeti dahil et ya da limiti "fiyat riski" olarak yazıp onaylat.**
Ne: `miktar = nakit·risk / (|giriş−stop| + fiyat·(stop_kayma + 2·taker))` (BIST'te BSMV dahil). Neden: karar 14 "işlem başı %1" diyor, gerçek kayıp %1.45'e çıkıyor; günlük %3 limiti 3 stopla aşılır. Fayda: kural ile uygulama örtüşür. Maliyet: işlem büyüklüğü %10-30 küçülür → sonuçlar değişir; **SERT_LIMITLER'in tanımına dokunduğu için kullanıcı onayı şart (karar 14/26)**. Evren koşusu bittikten ve seçim yapıldıktan sonra uygulanmalı (ortasında değiştirilmez).

**Ö9. Pano/Dersler istatistik düzeltmeleri (kabulü yanlış yöne çevirenler önce).**
Ne: q=0 çıkış nedeninde test yapma, "backtestte gözlenmedi (üst sınır ~3/n)" yaz; Koç'ta kova başına ≥5; kabul "sert limit ihlali"ni motor olayları (kill, dolum anı aşımı) üzerinden tanımla, anlık MTM aşımını ayrı uyarı yap (tolerans kullanıcı kararı); kesinti aralığına mum süresi ekle; BTC kıyasını motorun bellekteki mumlarından al; günlük özeti TSİ 00:10'da "dün tam gün" ile gönder, `son_ozet`'i state'e yaz; token'ı maskele (`type(e).__name__`). Neden: 2026-11-08 kabul kararları bu sayılara dayanıyor. Maliyet: düşük.

**Ö10. Araştırma hijyeni (düşük maliyet, yüksek güven):** `kilit_acilis.jsonl` için dönem+aşama bazında tek açılış kaydı; `deneme_kaydi`'na evren satırı yerine wf parquet hash+toplam; Sharpe yıllıklandırmasını gözlenen mum sayısına bağla (kripto regresyon testiyle); gerçek veri testleri için `PAPER_GERCEK_VERI=1` ile skip→fail; spot vekil dönemi short sayısı/R'si bilgi sütunu; K4'e WF'nin enstrüman listesini geçir.

---

## 3. Önce yapılacak 3 şey

1. **DSR kararı (Ö1) — sağlamlık/pbo/seçim/holdout başlatılmadan.** Kullanıcıya SR0 ≈ 3.2 (yıllık) ve geçenlerin en iyi Sharpe 1.90 gerçeğini göster; (a)/(b)/(c) seçtir; ON_KAYIT Güncelleme 6 olarak, "WF sonuçları görüldü" notuyla kaydet. Bu yapılmadan sağlamlık koşulursa 2 gün boşa gider ya da kural çiğnenir.

2. **Seanslı veri paketi (Ö2 + O1) ve holdout mühür/hata kilidi (Ö4) — scalp koşusu biterken.** Gün sonu mumu + K2 tutma süresi + mühür kapsamı + sessiz except'ler. Sonra daytrade ve scalp WF'yi yeniden koş (swing etkilenmez), eski sonucu arşivle ve DURUM'a "sonuç görüldükten sonra düzeltildi" diye yaz. Sağlamlık bu düzeltmelerin üstünde koşmalı; aksi hâlde K2 kapısı hisselerde yön bağımlı yanlış karar verir.

3. **Paper'ı sağırlıktan kurtar (Ö6) ve kabulü etkileyen sayı hatalarını düzelt (Ö9'un ilk üç maddesi).** Genel istisna + Telegram + OnFailure; `durum_yukle` askıda modu; token maskeleme; Dersler q=0; kabul "sert limit" tanımı. Bunlar küçük değişiklikler ama 8 haftalık paper'ın "kesintisiz çalışma + beklenti aralığı" hedefini doğrudan koruyor. Paper veri yolu testleri (Ö7) hemen arkasından.

Not: Ö8 (boyutlamaya maliyet) ve Ö5 (BIST ağırlığı) kullanıcı kararı gerektiriyor ve mevcut koşunun ortasında uygulanmamalı; evren seçimi bitince gündeme alınmalı.