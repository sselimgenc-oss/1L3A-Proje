# 1L3A kapanış turu — sonuç görülmeden önce ön kayıt

Tarih: 2026-11-13. Bu metin ve aynı commit'teki `aday_listesi.csv` ilk gerçek mum koşusundan **önce** dondurulur. Sonraki commit'lerde ikisi de değiştirilmez. Kaynak hesap defteri: `sonuclar/hesap_defteri/tekil_stratejiler.csv` (main `d960401`); hakem: PR #58, `HAKEM_FABLE.md` (`c50607e`). Önceki hesap defteri dalındaki 85 ayar ve 621 iz adayı ayrıca satır satır denetlenir. Bu tur, kullanıcının açık kapsam genişletme kararıdır; `CANLI_PLAN_V2.md` ve `ON_KAYIT_V2.md` içindeki daha dar araştırma takviminden sapar. Eski sonuçlar ve görülmüş holdout kanıt sayılmaz.

## Kapalı aday ve karar kümesi

`aday_listesi.csv` bu ön kaydın ayrılmaz parçasıdır: `strateji_id`, katman, kaynak, kaynakta yazılı kısa kural ve uyarlama notu içerir. Bu listedeki kimlikler dışında koşu yoktur. Liste, hesap defterindeki bütün C, D, E ve BELIRSIZ satırlarını, v2'de teknik hata ile ölçülemeyen dört kimliği, hakemin kısa listesindeki kaynak kimliklerini ve eski dalın özgül koşu izi bulunmayan 85 ayarını kapsar. D/iz satırları **otomatik koşulacak strateji değildir**; bunlar kapalı inceleme kümesidir. Kaynak kuralı belirli, izinli ve mevcut veriyle uygulanabilir ise aynı kimliğe bağlı tek uygulama koşulur. Kuralı belirsizse, veri/evren yoksa veya yasak tipse neden ve kaynak satırı yazılır; boşluk keyfi bir ayar uydurularak doldurulmaz. Kodlanan bir aile varyantı, aynı mantığı taşıyan listedeki başka kimliklere kanıtla bağlanabilir; aynı işlem yolu iki kez koşulmaz. Bağlar ve dışlananlar koşudan **önce** `k3_karar.csv` / `k4_karar.csv` ile mühürlenir. Sonuç görüldükten sonra aday, parametre, kapı veya evren eklenmez.

Liste sayımı: **4.773 satır** = 4.067 ana kaynak kimliği + 85 ayar izi + 621 iz adayı. Ana katmanlar: K1 42 kodlu koşulmamış + 4 teknik hata; K2'ye ayrı bağlanan 6 kaynak varyantı (`S0002` ana hesap defterinde kod kimliğiyle birleştirildiğinden kaynak kimliği burada ayrıca korunur); K4 2.199 satır (5 kısa liste satırı K2'de); kalan D/E/BELIRSIZ uygunluk incelemesi 1.816. K5 iz kayıtları hipotez değildir; ana kimlikle eşleştirilince aynı strateji iki kez koşulmaz. `aday_listesi.csv` SHA-256: `53ed26a73ac379f0a65de18ca8b81d77775da2fc9e822f198fca85acae373ab4`. Ana hesap defteri SHA-256: `97eafd32e8be310b9c57ae2ab35af59c8d406e8901d1b081ee1fd2e0ddd5d515`. Hakem metni SHA-256: `f5da1b8cbaf8a1ef002151ff6b6c1b345ffbaf7b7a1b172202141a960a8ad3d5`.

K1: 26 v3 kodu, d11j/d12b ek ayarları (kaynakla bağlı 16 + bağlı olmayan 2 = 18) ve dört teknik hata kimliği. K2: hakem kısa listesinin saatlik aşırı tepki, T61, T21, T02/S0002, S0005, Ichimoku 20/60/120, Argus gizli uyumsuzluk biçimleri. K3: E satırları ve dış kaynaklarda `BIZDE_YOK + kullanılabilir` denilen, yukarıdaki kapalı kaynak evrenine düşen satırlar. K4: `benzer_hedef` dolu D satırları ve doğrulanmamış arşiv bağları. K5: önceki dalın 85 ayarı ve 621 iz adayı, aynı aday kimliğine bağlanıp gerçek boşluk yönünden kontrol edilir. Katmanlar birbirini tekrar ederse tek koşu kimliği kullanılır. Her satırın kararı ve eşlemesi kayda geçer.

Kaynak parametre, TF, yön ve çıkış **kaynak metnindeki biçimiyle** alınır; optimizasyon/ızgara yoktur. Kaynak stopu yoksa ATR(14) × 3 felaket stopu eklenir ve `uyarlama` diye işaretlenir. Bu stop kuralı kaynak biçimiyle eşitlik iddiası değildir. Eksik parametreye keyfi varsayılan verilmez; o satır `KURAL_YOK` olur. Sinyal yalnız kapanmış mumdan, dolum bir sonraki açılıştan; göstergeler yalnız geçmiş ve kapanmış veriden hesaplanır. Tekrarlanan kaynaklar bir mantık/ayar olarak birleştirilir; eşitlik için giriş, çıkış, filtre, TF ve yön karşılaştırılır. Anahtar kelime eşlemesi kanıt değildir.

## Veri ve maliyet

Geliştirme dönemi: v2'nin aynı veri başlangıcı → **2025-11-07 23:59:59 UTC**. 2025-11-08 ve sonrası holdout geçmişte görüldüğü için **okunmaz**. Evren, `motor.arastirma.v2.sabit.evren_listesi('kripto')` ile tanımlı 13 Binance USDT perpetual sembolüdür; DK_ yalnız kaynağın vazgeçilmez şartı ise ve aynı geliştirme dönemi verisi mevcutsa kullanılır. Sembol listesi koşudan önce aday karar tablosunda sabitlenir; performansa göre ayıklama yoktur. 5m–1d OHLCV ve funding dışındaki veriler kullanılmaz. Veri yokluğu açık hata/ret nedenidir, sessiz atlama değildir.

Maliyet: `sonuclar/evren/maliyet_tablosu.csv` ve v2 funding varsayımı. Ana karar maliyet **×2** (komisyon/spread/kayma), bilgi satırı **×1**; funding v2'deki gibi çarpılmaz. Her strateji kendi 10.000 USDT sanal hesabında, işlem başı başlangıç stop riski özsermayenin **%1,5**'i, zirveden **−%30** kalıcı kill ile oynatılır. Mevcut canlı/paper limitleri bu araştırma hesabı için değiştirilmez.

## Tek koşunun kapıları

Birinci kapının **hepsi** şarttır; ölçülemeyen değer geçmez:

1. Maliyet ×2'de net getiri > 0 ve PF(R) ≥ 1,2.
2. En az 200 kapanmış, kabul edilmiş işlem.
3. Toplam R'si en yüksek sembol çıkarılınca da, en yüksek takvim yılı çıkarılınca da kalan ΣR > 0. Bu iki çıkarma ayrı hesaplanır.
4. %1,5 işlem riskiyle kendi hesabında −%30 kill hiç tetiklenmez.
5. Long-only kural, aynı dönem ve sembollerin eşit ağırlıklı al-tut Sharpe'ını aşar. Kıyas net, aynı maliyet ×2 ve aynı tarih kapsamıyla hesaplanır.
6. v2'nin takvim çeyreği içinde aynı sembol/yön/çıkış mantığını koruyan rastgele giriş testi: p ≤ 0,05; p=(1+#{sim≥gerçek})/(B+1), B=100.000, sabit tohum 20261113 ve kimlikten crc32. Testin desteklemediği çıkış `HATA`dır, p=1 olarak gizlenmez.
7. Tüm koşu adayları üzerinde Benjamini–Hochberg q=0,10. Kodlanamaz/tekrar adaylar p=1 ile ailede kalır; aile büyüklüğü `aday_listesi.csv` içindeki ana hesap defteri kimlikleri + bağımsız K5 ayar kimlikleridir. Aynı mantığın tekrar kaydı ayrı hipotez yaratmaz; bu birleştirme koşudan önceki karar tablosunda mühürlenir. Eşit p'de kimlik sırası kullanılır.

Birinci kapıyı geçenler ikinci kapıda `sonuclar/evren/yeni_sembol/` çalışmasındaki seçimde kullanılmamış **40 sabit sembolde** aynı kural ve maliyet ×2 ile sınanır: ortalama işlem R > 0. Bu sembollerin 2025-11-08 sonrası verisi de okunmaz; veri yoksa kapı geçilmez ve hangi sembolün eksik olduğu yazılır. Bu geçmiş sınav, daha önce görülmüş olduğu için bağımsız kanıt değildir.

Geçen strateji yalnız **paper adayı**dır. En az 12 hafta ileri paper gözlemi ve ayrı kullanıcı onayı olmadan canlıya alınmaz. Elenen stratejiye yeni ayar/kapı denemesi yoktur; hesap defterinde B olarak, bu turun sonucu ve tarih etiketiyle **yeni kapanış tablosunda** kaydedilir (mühürlü/eski hesap defteri değiştirilmez). Gerçek koşu yalnız bir kez yapılır. Altyapı hatası nedeniyle sonuçtan sonra düzeltme gerekirse eski hata korunur, yeni rapor açıkça `sonuç sonrası` etiketi taşır; sessiz yeniden koşu yoktur.

## Çalıştırma ve dürüstlük sınırı

Bu ön kayıt, adayların işlem kurallarının henüz doğrulandığı anlamına gelmez. K3/K4/K5 kaynak karşılaştırması, yeni sınıflar, koşu betiği ve sentetik testler sonraki commit'lerde hazırlanır. İlk gerçek veri koşusu, satır sayısı denetimleri ve bütün uygun kodlar hazır olmadan çalıştırılamaz. Geçmiş geliştirme verisinde seçilmiş fikirlerin iyi görünmesi kanıt sayılamaz; tur yalnız açık soruları kapatır.

## Ön kayıt düzeltmesi — sonuç görülmeden

Tarih: 2026-11-13. Bu ek, kullanıcı düzeltmesiyle, ilk gerçek mum koşusundan ve herhangi bir kapanış sonucu görülmeden yazıldı. Yukarıdaki asıl metin korunur. **Benjamini–Hochberg (BH) ailesi için yukarıdaki 7. maddenin aile tanımı yerine bu paragraf geçerlidir:** Aile yalnız kaynak incelemesi tamamlanıp kodlanan ve tek koşu listesine alınan benzersiz strateji/ayar hipotezlerinden oluşur. Kodlanamayan, `KURAL_YOK`, tekrar ve kapsam dışı kayıtlar p=1 verilerek aileye katılmaz; karar tablolarında gerekçeleriyle tutulur. Aynı işlem kuralının tekrar kaynak kayıtları tek hipotez sayılır. Aile büyüklüğü, koşu listesi tüm katman kararlarından sonra ve gerçek sonuç görülmeden dondurulduğunda, listedeki benzersiz koşulacak kimliklerin sayısı olarak sabitlenir; sayı, kimlik listesi ve liste özeti SHA-256 değeri koşu planına ve rapora yazılır. Bu sabitlemeden sonra aday eklenmez veya çıkarılmaz. BH eşik değeri q=0,10 ve diğer kapılar değişmez.

## Ön kayıt düzeltmesi — sonuç görülmeden (2): portföy satırları ve kapıların çarpanı

Tarih: 2026-11-13. Lider kararı; hiçbir kapanış koşusu yapılmadan ve sonuç görülmeden yazıldı. Yukarıdaki metinler korunur; bu ek yalnız ön kaydın açık bıraktığı noktaları tanımlar.

- **Ana çarpan:** Kapı 1, 3, 4, 5'in tamamı maliyet ×2 oynatmasıyla ölçülür (ana karar ×2). ×1 yalnız bilgi satırıdır. Tek grafik ve portföy için aynıdır.
- **Araştırma hesabının diğer sınırları:** tek grafik hesabıyla aynı: günlük −%3 yeni giriş yok, toplam kaldıraç 3x, toplam açık stop riski tavanı tek grafikte %5 (mevcut `secim.OynatmaAyari` varsayılanı). Kill −%30 kalıcıdır (`limit_modu='uygula'`).
- **Portföy (`pf__*`) stratejileri:** işlem başı risk yerine karar 25'teki toplam stop riski bütçesi aynı oranla ölçeklenir: %5 × (1,5 / 1,0) = **%7,5** toplam stop riski; kill −%30, günlük −%3, 3x. Uygulama: `motor/arastirma/kapanis/portfoy.py` (SERT_LIMITLER değişmez, koşu süresince ayrı araştırma limiti).
- **Portföy kapıları** (v2 portföy satırlarının karşılıkları, `ON_KAYIT_V2.md` E1–E5 portföy paragrafı): (1) net×2 > 0 ve günlük Sharpe×2 ≥ 0,5; (2) dönem ≥ 1.095 gün ve ≥ 20 yeniden dengeleme; (3) en iyi takvim yılı çıkarılınca net×2 > 0 (sembol çıkarma portföyde tanımsız, uygulanmaz); (4) ×2 hesabında kill hiç tetiklenmez; (5) long-only ise aynı evren/dönemde eşit ağırlıklı al-tut Sharpe'ını (aynı maliyet ×2) aşar; (6) rastgele kıyas v2'deki `RastgeleAgirlik` yöntemiyle aynı yeniden dengeleme takviminde, B=100.000 yerine v2 test ayarı korunarak p ≤ 0,05 (yöntem ve B koşu betiğinde v2 kodundan aynen alınır, kayda yazılır); (7) BH ailesine tek grafiklerle birlikte girer.
- **Veri:** sabit evrendeki bir sembolün geliştirme döneminde hiç verisi yoksa o koşu `HATA` sayılır (kapı geçilmez, sembol yazılır). Dönem içinde geç başlayan sembol, v2'deki gibi başlangıç öncesinde dışarıda kalır.

## Ön kayıt düzeltmesi — sonuç görülmeden (3): 906 listesi için standart ayar katmanı (K6)

Tarih: 2026-11-13. Kullanıcı kararıyla ("hiçbir kod atlanmayacak"; seçenek: "Standart ayarla koş"). Hiçbir kapanış koşusu yapılmadan ve sonuç görülmeden yazıldı. Yukarıdaki metinler korunur.

- **Kapsam:** Yalnız `HAM:X005:*` (trend/ortalamaya dönüş 906 listesi) satırlarından, kaynak (metin ve varsa kod) okunduktan sonra yalnız **sayısal parametre, MA tipi ya da zaman dilimi eksikliği** yüzünden `KURAL_YOK` kalanlar. Öznel/takdire bağlı kural ("yatay piyasa", el ile çizgi), tanımsız özel gösterge formülü, kapalı kod ve tutarsız kural `KURAL_YOK` kalır; K6'ya girmez.
- **Standart değerler (değişmez tablo):** RSI 14; ATR 14; ADX/DMI 14; Stokastik 14/3/3; MACD 12/26/9; Bollinger 20/2σ (kapanış); MA tipi yazılmamışsa SMA; CCI 20; Williams %R 14; MFI 14; ROC/momentum 10; Donchian 20; Keltner EMA20 ± 2×ATR10; Ichimoku 9/26/52; Parabolic SAR 0,02/0,02/0,2; SuperTrend ATR10×3; hacim ortalaması 20; z-skoru penceresi 20. Kaynak kendi varsayılanını yazmışsa o kullanılır.
- **Aralık verilmişse** (ör. "EMA 7–10"): kaynağın belirttiği varsayılan; yoksa aralığın orta noktası (tamsayı parametrede aşağı yuvarlanır). Izgara yoktur, tek değer.
- **Zaman dilimi yazılmamışsa:** 4h ve 1d iki ayrı hipotez olarak koşulur. Kaynak yalnız "gün içi" diyorsa 1h.
- **Kaynakta stop yoksa** ATR(14)×3 uyarlaması (ana kuraldaki gibi).
- **Etiket ve kapılar:** Bu satırlar `K6_STANDART` katmanı olarak ayrı raporlanır; kapılar ve ikinci kapı aynıdır. BH ailesine **dahildir** (aile büyüklüğü artar, eşik sıkılaşır). Geçen olursa raporda "standart ayar uyarlaması" notuyla yalnız paper adayıdır.
- Her K6 satırının hangi parametreye hangi standart değerin verildiği koşu listesinde satır satır yazılır ve koşudan önce dondurulur.

## Ön kayıt düzeltmesi — sonuç görülmeden (4): aşamalı koşu ve BH aileleri

Tarih: 2026-11-13. Kullanıcı önceliği (önce kendi belgeleri) ve süre nedeniyle; hiçbir kapanış koşusu yapılmadan yazıldı. Yukarıdaki metinler korunur.

- Koşu iki aşamadır. **Aşama 1:** kullanıcı belgeleri (HAM:X005 906 listesi + HAM:X008 ajan2) + K1 + K2 katmanları. **Aşama 2:** Robotic (HAM:B001), COK_KOLLU, K3/K4/K5'in kalan katmanları.
- Benjamini–Hochberg (q=0,10) her aşamada **ayrı aile** olarak uygulanır; aile = o aşamanın dondurulmuş koşu listesindeki benzersiz hipotez kimlikleri (varyant ve TF ayrı kimlik). Aşama 1 listesi koşudan önce dondurulur (kimlik listesi + SHA-256); aşama 2 sonuçları aşama 1 ailesini değiştirmez. Raporda her iki aileyi birleştiren ek (bilgi amaçlı) BH tablosu da verilir.
- Sonuç görülmeden yapılan koşu listesi elemesi (`eleme/eleme.csv`, kullanıcı yönlendirmesiyle) aşama 1 listesinin parçasıdır; ÇIKAR kayıtlar koşulmaz ve aileye girmez.
- Diğer kapılar, çarpanlar ve ikinci kapı değişmez.

## Ön kayıt düzeltmesi — sonuç görülmeden (5): aşama 2 Robotic elemesi

Tarih: 2026-11-13. Kullanıcı yönlendirmesiyle ("test etmemize gerek yok dediği şeyleri çıkartalım"); aşama 1 koşusu sürerken, hiçbir aşama 2 kaydı kodlanmadan ve koşulmadan, aşama 1 sonucu raporlanmadan yazıldı. Eleme yalnız kural metni ve aile ilişkisi üzerinden yapıldı.

- Robotic (HAM:B001) KOSULACAK 277 satırına sonuç görülmeden eleme uygulandı: `eleme/eleme_asama2_robotic.csv` (192 KOŞ, 85 ÇIKAR; gerekçe `eleme/ELEME_FABLE_ROBOTIC.md`). Ek 4'teki aşama 1 kuralı aynen geçerlidir: ÇIKAR kayıtlar koşulmaz ve aşama 2 BH ailesine girmez.
- "Aşama 1'de koşulanın aynısı" gerekçesiyle çıkarılan 8 satır aşama 1 ailesinde zaten bir hipotezdir; aşama 2'de ikinci kez sayılmaz.
- Bir temsilci kodlanamaz ya da birebir kopya diff'i anlamlı fark gösterirse, ailesinden ÇIKAR kaydı kodlamadan önce (sonuç görülmeden) geri alınır ve bu dosyaya not edilir.

## Ön kayıt düzeltmesi — sonuç görülmeden (6): aşama 2 kapsam triyajı

Tarih: 2026-11-13. Kullanıcı kararıyla (2026-11-13 soru-cevap: Robotic koşulsun; COK_KOLLU çıksın; eski katmanlardaki satırlar triyajla kapatılsın); aşama 1 koşusu sürerken, aşama 1 dahil hiçbir kapanış sonucu görülmeden yazıldı. Yukarıdaki metinler korunur; bu ek, ana metindeki "her satırın kararı kayda geçer" ve "bütün uygun kodlar hazır olmadan çalıştırılamaz" cümlelerini ve ek 4'teki aşama 2 tanımını aşağıdaki biçimde daraltır.

- **Dayanak:** `eleme/TRIYAJ_FABLE_ASAMA2.md` ve `eleme/triyaj_asama2.csv` (SHA-256 bu commit'te). Triyaj yalnız kaynak türü, önceki karar tabloları ve hesap defterindeki arşiv akıbetinden yapıldı; mum verisi ve koşu sonucu kullanılmadı.
- **Aşamalı koşu kaydı:** Aşama 1, K3/K4/K5 incelemesi tamamlanmadan başlatıldı. Ek 4'ün aşama tanımı bunu kapsar; ana metnin "bütün uygun kodlar hazır olmadan çalıştırılamaz" cümlesi aşama bazında uygulanır.
- **Kapsam dışı bırakılanlar:** `triyaj_asama2.csv` içindeki K3-6, K3-7, K4-5, K4-8, K4-9, K4-10, K5-5b alt kümeleri (1.759 satır) ve COK_KOLLU kümesinin CK-1…CK-6 satırları (86 dosya) satır satır incelenmez ve koşulmaz. Karar tablolarında `KAPSAM_DISI_TRIYAJ` kodu ve alt küme adıyla kaydedilir (K4-5 için ayrıca mevcut kullanıcı kararı: kesitsel/pairs/rotasyon evren dışı). Bu kod "kural yok" ya da "test edildi, elendi" anlamına gelmez. K3-5b'deki 4 kimlik, aşama 1 ön elemesiyle aynı ölçütlerle (`eleme/ELEME_FABLE.md`) koşu listesine alınmaz.
- **Kapalı sayılanlar:** Daha önce karar verilmiş satırlar mevcut kararlarıyla kalır. K5 iz satırları bağlı oldukları ana kimliğin kararını betikle devralır.
- **Aşama 2'nin yeni tanımı:** (a) Robotic KOSULACAK satırlarının ayrı hakem elemesinden geçenleri (ek 5; 192 satır); (b) `triyaj_asama2.csv` içinde KOŞ olan kimlikler; (c) İNCELE alt kümelerinden, incelemede kuralı tam bulunanlar. (c) için inceleme kararları aşama 2 koşusundan önce mühürlenir.
- **BH:** Aşama 2 ailesi yine dondurulmuş aşama 2 koşu listesidir (ek 4). Kapsam dışı satırlar aileye girmez.
- **Rapor yükümlülüğü:** Nihai rapor, kapsam dışı bırakılan satır sayısını alt küme bazında ve "incelenmedi" ifadesiyle verir. Bu satırlar bu turda sonradan kapsama alınmaz.
- Kapılar, çarpanlar, evren ve ikinci kapı değişmez.

## Ön kayıt düzeltmesi — sonuç görülmeden (7): aşama 2 daraltması

Tarih: 2026-11-13. Kullanıcı kararıyla ("Fable'ın önerisiyle devam et"). Aşama 2'nin hiçbir kaydı koşulmadan ve aşama 2 listesi dondurulmadan yazıldı.
Not (açıklık için): bu sırada aşama 1 koşusu sürüyordu ve 9 aşama 1 kaydı bitmişti. Daraltma ölçütünü öneren hakem bu sonuçlara bakmadı; ölçüt yalnız zaman dilimi, maliyet aritmetiği ve geçmiş turların taban oranlarına dayanır (`eleme/` altında Fable umut değerlendirmesi, ILERLEME.md). Lider, koşu günlüğünün son satırında tek bir aşama 1 p değeri gördü; aşama 1 listesi ve ailesi değişmez.

- **Aşama 1 değişmez:** dondurulmuş 365 kayıt sonuna kadar koşulur; BH paydası 365 kalır.
- **Aşama 2 Robotic:** ek 5 ve K3-3 elemesinden geçen 230 kayıttan yalnız zaman dilimi 1h ve üstü olanlar ile EWO-ofset (A/B/C) ve E0V1E aileleri (her TF) kalır: **87 kayıt** (`eleme/daraltma_asama2.csv`). 5m/15m/30m Freqtrade kayıtları bırakılır (maliyet ×2 gidiş-dönüş %0,28–0,40; geçmiş scalp turu 0/204).
- **Aşama 2 küçük kümeler:** K3-5a'nın 13 hipotezi kalır. K4-11 (75 satır) incelemesi ve `ara/asama2_incele.csv`'nin 15 KOSULACAK kaydı (eski proje/kart; aynı veride önceden seçilmiş, "yeniden keşif") bırakılır.
- Bırakılan kayıtlar koşulmaz ve aşama 2 BH ailesine girmez; raporda "ek 7 ile bırakıldı, koşulmadı" diye sayılır.

## Ön kayıt düzeltmesi (8): kısa zaman dilimli kayıtlar koşulmaz — sapma

Tarih: 2026-11-13. Kullanıcı kararıyla. **Sapma kaydıdır:** aşama 1 koşusu başlamıştı ve 9 kayıt bitmişti; karar o sonuçlara bakılarak değil, ölçülen süreye göre verildi (kapı 6 rastgele giriş testi 5m/15m kayıtta sembol başına ~20 dk, kayıt başına ~4 saat; 1. aşamada 47 kayıt ≈ 2 gün; bağımsız hakemin önceden "pratikte umut yok" değerlendirmesi).

- Aşama 1 ve aşama 2'de TF'si **5m, 15m, 30m** olan kayıtlar koşulmaz. Birleştirmede `KOSULMADI`, **p=1** yazılır.
- BH paydası değişmez: aşama 1 = 365, aşama 2 = 96 (dondurulmuş listeler). Koşulmayanlar ailede p=1 ile kalır; bu, sonuçları yalnız daha temkinli yapar.
- Aşama 1'de kısa TF olup daha önce biten kayıtlar (koşu sırası gereği bitenler) sonuçlarıyla aileye girer; bu kayıtlar dışarıda bırakılmaz (seçici çıkarma yapılmaz).
- Raporda koşulmayan kayıt sayısı TF'ye göre "ek 8 ile koşulmadı" diye verilir.

## Ön kayıt düzeltmesi (9): kısa TF kayıtları için ucuz yol — ek 8'i değiştirir

Tarih: 2026-11-13. Kullanıcının "koşmadıklarımız arasında iyiler varsa?" sorusu üzerine; kısa TF kayıtlarının hiçbir sonucu görülmeden yazıldı.

- Ek 8'deki "koşulmaz" yerine: 5m/15m/30m kayıtları (aşama 1 ve 2) uzun TF'ler bittikten sonra **kapı 1–5 ile koşulur**. Kapı 6 (rastgele giriş testi, asıl süre maliyeti) yalnız kapı 1–5'in **hepsini** geçen kayıtlara uygulanır; geçmeyenler `ATLANDI_K1_5`, **p=1**.
- Gerekçe: kapı 1–5'i geçmeyen bir kayıt hangi p ile olursa olsun birinci kapıyı geçemez; p=1 yazmak BH'yi yalnız daha temkinli yapar (diğer kayıtların eşiğini gevşetmez). v2'deki uygulamayla aynı.
- Uzun TF kayıtları (ve ek 8'den önce biten kısa TF kayıtları) kapı 6'yı ön kayıttaki gibi koşulsuz alır. BH paydaları değişmez (365 / 96).

## Ön kayıt eki (10): tek seferlik ileri dönem sınavı — kullanıcı kararı, SAPMA

Tarih: 2026-11-14. Kullanıcı kararıyla ("tek seferlik sınav", paper listesi onaylandı). Kapanış turu sonuçları görüldükten SONRA yazıldı; bu sınav ön kayıtlı kanıt değildir, ayrı bir sapma kaydıdır. Ölçütler sınav verisi açılmadan yazılmıştır.
Not: 2025-11-08 sonrası dönem v2 turunda başka stratejiler için açıldı (temiz holdout değil); bu 6 kayıt o dönemde hiç koşulmadı.

- **Kapsam (6 kayıt, kullanıcının paper listesi):** HAM:X005:664#v1, HAM:X005:705, HAM:X005:301#v1, HAM:X005:138#v3 (aşama 1); HAM:B001:670#v1, HAM:B001:574#v1 (aşama 2). Aynı sınıf, aynı parametre, aynı TF, kripto13 evreni, aynı motor ve maliyet tablosu.
- **Dönem:** 2025-11-08 00:00 UTC → mevcut en son kapanmış mum. Isınma için gösterge geçmişi bu tarihten önceki veriden okunabilir; işlem ve ölçüm yalnız dönem içinde.
- **Tek koşu.** Sonuç ne olursa olsun yeniden koşu, ayar ya da evren değişikliği yok.
- **Geçme ölçütü (her kayıt ayrı):** (a) maliyet ×2'de net getiri > 0, (b) %1,5 işlem riskiyle −%30 kill tetiklenmez, (c) long-only davranan kayıtlarda (işlemlerin tamamı long) aynı dönem, aynı 13 sembol, günlük dengeli eşit ağırlıklı al-tut net getirisinden (maliyet ×2) düşük olmamak. İşlem sayısı ve ortalama R raporlanır; az işlem (<20) "yetersiz örnek" etiketi alır ama (a)–(c) yine uygulanır.
- **Sonuca bağlı karar (önceden):** (a) ya da (b)'yi geçemeyen kayıt paper listesinden çıkarılır. (c)'yi geçemeyen trend kaydı paper'da kalır ama "al-tutu geçemedi" etiketi alır. Geçen kayıt için bu sınav "gerekli, yeterli değil" sayılır; canlı şartı (12 hafta paper + kullanıcı onayı) değişmez.

## Ön kayıt eki (11): ileri dönem sınavının kalan 35 paper adayına genişletilmesi — kullanıcı kararı, SAPMA

Tarih: 2026-11-14. Kullanıcı, ek 10'un kapsamını kendisi belirlemek istemişti; lider soruyu yanlış anlayıp yalnız 6 kaydı koştu (lider hatası, kayda geçer). Kullanıcı kararıyla aynı sınav, ek 10 ile birebir aynı dönem, ölçüt ve sonuca bağlı kuralla, aşama 1 ve 2'nin kalan 35 paper adayına (`sonuc_asama1.csv` / `sonuc_asama2.csv` `paper_adayi=True`, ek 10'daki 6 kayıt hariç) uygulanır. Bu 35 kaydın sınav dönemindeki sonucu bu ek yazılırken görülmemiştir; ek 10'un 6 sonucu görülmüştür ve değişmez.
- Tek koşu, ayrı çıktı dizini `ileri_sinav_ek11/`, kilit gerekçesi "kapanış ek 11 ...". Sonuç ne olursa olsun yeniden koşu yok.
- Geçen kayıtlar otomatik olarak paper'a girmez; paper listesine ekleme ayrı kullanıcı kararıdır (Fable kopya/şüpheli notları dikkate alınarak).

## Ön kayıt eki (12): kalan tüm kayıtların ileri dönemde bilgi amaçlı koşusu — kullanıcı kararı, SAPMA

Tarih: 2026-11-14. Kullanıcı: "Koş, eksik bir şeyimiz kalmasın." Bu kayıtların sınav dönemi sonuçları görülmeden yazıldı.
- Kapsam: iki aşamanın dondurulmuş listelerindeki kalan 414 tek grafik kaydı (41 paper adayı hariç). 6 portföy kaydı bu betiğin kapsamı dışında; ayrıca belirtilir.
- Aynı dönem, motor, maliyet ve (a)–(c) ölçütleri; tek koşu; çıktı `ileri_sinav_ek12/`.
- **Bilgi amaçlıdır:** bu kayıtlar geliştirme döneminde ön kayıtlı kapıları geçemedi. İleri dönemde iyi görünen olursa "keşif — kanıt değil" etiketi alır (414 kayıtta şansla iyi görünen beklenir); paper'a girmesi ancak yeni bir ön kayıt ve ileri (paper) veriyle olabilir. Paper adaylarının değerlendirmesini değiştirmez.
