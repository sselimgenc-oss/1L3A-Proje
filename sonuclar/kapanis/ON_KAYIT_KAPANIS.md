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
