# Kullanıcıya özet

- 2535 dosya envanterde; 479 dosyadan 9080 ham kayıt, 8197 temkinli kayıt profili çıkarıldı. Bunlar bağımsız strateji sayısı değildir.
- 906 son liste sayıldı; eski 417/547/707 turları ikinci kez eklenmedi. Robotic 909 dosya korundu ; 540 kümeye körlemesine birleştirilmedi.
- Profil akıbetleri: A18, B582, C53, D1121, E=0, F4, G127, H71, BELIRSIZ6221.
- 521 gerçek kod tanımında: A=5, B=484, C=26, BELIRSIZ=6. C grubundaki 53 profil kaydı, 53 ayrı koşulmamış kod demek değildir.
- A grubundaki 18 profilin 13’ü eski TV arşividir; güncel A grubundaki beş kodun ikisi holdout SET kapısı, üçü sağlamlık geçişidir. Canlı üstünlüğü çıkarılamaz.
- v2’de 222 satırın 73’ü E1/E3’ü geçip yapısal kapılardan elenmiş; 6 hata performans elemesi sayılmadı.
- Kesin E=0; ayrıca 621 iz eksikliği adayı görünür tutuldu. E=0, unutulmuş strateji yok demek değildir.
- 421 yazılı ayarın 85’inde özgül koşu kimliği bulunamadı; aile testi bu ayarların testini kanıtlamaz.
- “Benzeri test edildi” hükümleri doğrulanmış eşitlik sayılmadı; altı somut kural/kod farkı ayrıca yazıldı.
- “460+19” tarihsel sayısı Gitten doğrulandı; 438 kayıtlı kitap dizini 810 kartın tamamını kapsamıyor.
- Öz denetim: ilk taslakta 12/40 (%30) etki → toplu düzeltme; son nüfustan tekrar 40 kayıtta 2/40 (%5) → düzeltme; aynı 40 kayıtta kalan 0.
- Ajan2’nin 26 tekil kaydı ve Robotic asıl kodları depoda yok; bilinmeyenler uydurulmadı. Strateji testi veya kod değişikliği yapılmadı.

## Sayımın anlamı ve kapsam

İnceleme tabanı `a07d18d` (PR #56), dal `codex/hesap-defteri`. Envanterdeki 2.535 dosya; kaynaklar, kararlar, kod ve sonuç kanıtlarını kapsar. 328 asıl katalog/kart dosyasından 8.559 kaynak satırı ve 151 kod modülünden 521 kayıtlı sınıf ayrı ham kayıt olarak alınmıştır: toplam 479 kaynak dosyası, 9.080 ham satır. Her ham satır tek bir `tekil_id`ye bağlanır. Kaynak ve uygulama, mantık eşitliği ispatlanmadığında ayrı kalır. Bu yüzden 8.197 sayısı kanıtlı bağımsız algoritma sayısı değildir.

| Kayıt birimi | Profil |
|---|---|
| kaynak_strateji_kaydi | 7407 |
| cikis_risk_modulu | 35 |
| arac_veya_yazi | 225 |
| toplu_katalog_kaydi | 8 |
| toplu_beyan | 1 |
| operasyonel_kod | 521 |

35 çıkış/risk kartı, 225 araç/yazı ve 8 toplu katalog kaydı toplamda görünür; bağımsız giriş sistemi diye yorumlanmaz. Bir toplu kayıt, eksik 26 kayıtlı Ajan2 listesinin beyanıdır. Bazı kataloglar tek satırda birkaç alt modu anlatır; ham `veri_json` bütün alt kuralları korur. Kaynakta açıkça adı verilen grup üyeleri `ara/P8_grup_uyeleri.csv` içindedir; eksik üyelerin kuralları adından türetilmedi. `diğer` aile etiketi, ailesi kesinleşmeyen kayıtları da içerir.

328 ana dosyanın, 675 ara dosya/listenin ve 57 sonuç tablosunun kaynak–çıktı sayımı yapıldı; fark 0. Ara P4/P5/P6/P7 tabloları karar/ayar/eşleştirme tekrarlarını da içerir; bu tabloların toplamı ham strateji sayısı değildir. Dış araştırmanın destek tabloları yeni kaynak strateji diye tekrar sayılmadı. 77lik belgenin ayrıntılı Mantık bölümleri aynı 77 ham kayda bağlandı. Kataloglara eklenmemiş tur5 araştırma belgesinin 5 maddesi ve 2 toplu ret paragrafı da korundu.

`kaynaklar.csv` dosya SHA256larını ve ilk Git ekleme tarihlerini içerir. Git tarihi kullanıcının kaynağı ilk getirdiği tarih olarak sunulmaz; bulunamayan tarih BELIRSIZ kalır. 409 belgedeki otomatik atıf indeksi semantik doğrulama yerine geçmez; 45 anlatım/şema belgesinin kapsam kararı `ara/P5_P7_belge_kapsam_kararlari.csv` içindedir. Kaynakta yer almayan üçüncü taraf programları yeniden indirilmedi.

## Tekilleştirme ve kanıt standardı

883 ek kopya kayıt birleştirildi. Aynı kart kimliği; aynı fiziksel kaynak/dosya ve aynı mekanik, gösterge, TF, veri ihtiyacı; yahut bütün alanları birebir aynı katalog/Excel kaydı kullanıldı. Ada/fuzzy benzerliğe göre birleştirme yapılmadı. Mekaniği eksik katalog kaydının birebir kopyasını birleştirmek, görünmeyen programların mantıksal eşitliğini ispatlamaz. Robotic 540 kümesinin üyelik toplamı 909 doğrulandı; alttaki 909 kod dosyası olmadığı için kopya/ML/DCA/lookahead bayrakları bağımsız doğrulanmış sonuçlara çevrilmedi.

906 kayıtlı listede eski üç turun kimlik ve link sürekliliği kontrol edildi; 707 + 199 = 906, kesişim yok. 18 kural/parametre alanı sürüm farkı saklandı. Kararların sonraki turlardaki etiketleri kaydedildi; aynı kopya kayıtlar aynı turda çelişiyorsa dosya sırasına göre hüküm seçilmedi. 54 v3 ad/URL dışı satır atfı kaynak satırına geri izlendi; provenans bağlantısı kural eşitliği sayılmadı. `gorev2` önceki etiket/kapsam atıfları ayrı belirsizlik notuyla tutuldu.

## Akıbetler ve aşamalar

| Durum | Bütün profiller | Gerçek kod tanımları |
|---|---|---|
| A_TEST_EDILDI_GECTI | 18 | 5 |
| B_TEST_EDILDI_ELENDI | 582 | 484 |
| C_KODLANDI_KOSULMADI | 53 | 26 |
| D_KODLANMADI_NEDENLI | 1121 | 0 |
| E_KODLANMADI_NEDENSIZ | 0 | 0 |
| F_YASAK_TIP | 4 | 0 |
| G_ML | 127 | 0 |
| H_BIZIM_EVRENDE_UYGULANAMAZ | 71 | 0 |
| BELIRSIZ | 6221 | 6 |

A grubundaki 18 kaydın 13’ü, aynı Pine kaynak kimliğiyle bulunan eski TV arşiv geçişidir. Güncel koda A/B transfer edilmedi. 135 arşiv JSON’unda 99 kaynak Pine kimliği var; bazıları iki arşiv aşamasında yinelenir. Güncel A grubundaki beş kod: `dis__gauss-stoch-eth` ve `dis__ewo-ema-ofset` resmi holdout SET kapısı; `dis__ama-egri-donus-filtresi`, `dis__aroon-stochrsi-ema-dip`, `dis__gauss-stoch-btc` v2 sağlamlık geçişi, son sete seçilmemiştir. A etiketi yalnız yazılan aşamayı ifade eder.

B grubundaki 582 kaydın içinde 484 gerçek kod, 86 eski arşiv kaynak profili, 9 v3 uyarlama kaynağı ve 3 farklı mantıklı temsilci kaydı vardır. Kaynak profilinin B/Csi test edilen uyarlamaya ait olduğunda `asama`, `adil_test=zayif temsilci`, uygulama idsi ve fark notu açık yazılır; özgün kaynağın aynı kurallarla test edildiği iddia edilmez. `islem_kaniti` seçilen aşamanın TF/evren/işlem/kapı değerlerini; `ayar_kapsami` ayar etiketlerini gösterir. Tam tarihçe `ara/P8_kod_tarihce.csv`dedir; örtüşen dönemler toplanmaz.

Paper üyeliği eski eleme kararını silmez. 10 paper uyum JSONu mevcut geçmiş tekrar karşılaştırmasıdır; ileri paper başarısı veya canlı sonucu değildir (`ara/P3_paper_tekrar_uyum.csv`). Atıf yapılan `sonuc_freqtrade*.csv` dosyaları bu checkoutta bulunmadığı için metindeki PF/Sharpe iddialarından test hükmü üretilmedi.

## C — kodlu, koşu kanıtı bulunamayanlar

35 v3 kodunun 9’unda eleme sonucu, 26’sında araştırma koşusu kanıtı yok. Neden koşulmadığını açıklayan kesin kayıt bulunamadı; uydurulmadı. Birim test varlığı araştırma koşusu sayılmadı. Tam C grubundaki 53 profil listesi `ara/AKIBET_C.csv`; aşağıdaki 26 farklı operasyonel tanımın kaynak/prototip atıfları C sayısını artırır.

| Kod kimliği | Kod dosyası:sınıf |
|---|---|
| pf__v3-funding-1s-devam | motor/portfoy/stratejiler/v3.py:109:Funding1sDevam |
| pf__v3-funding-kesit-decil-carry | motor/portfoy/stratejiler/v3.py:128:FundingKesitCarry |
| pf__v3-funding-z90-3gun | motor/portfoy/stratejiler/v3.py:154:FundingZ90UcGun |
| v3__adaptivetrend-6s-momentum | motor/strateji/dis/v3_adaylar.py:125:AdaptiveTrend6s |
| v3__aralik-kirilim-bekleyen-emir | motor/strateji/dis/v3_adaylar_2.py:36:AralikKirilimBekleyenEmir |
| v3__asya-kutu-kirilim-ma50 | motor/strateji/dis/v3_adaylar.py:32:AsyaKutuKirilimMa50 |
| v3__donchian-ansambl-vol-hedef | motor/strateji/dis/v3_adaylar.py:150:DonchianAnsambl |
| v3__ema-9-21-50-rsi-hacim | motor/strateji/dis/v3_adaylar_3.py:37:EmaRsiHacimKesisim |
| v3__haftalik-sma-trix-kirilim | motor/strateji/dis/v3_adaylar.py:174:HaftalikSmaTrixKirilim |
| v3__kirmizi-mum-2x-hacim | motor/strateji/dis/v3_adaylar.py:203:KirmiziMumHacim |
| v3__l-sekli-ma-kirilim-long | motor/strateji/dis/v3_adaylar_2.py:75:LSekliMaKirilimLong |
| v3__londra-volatilite-kirilim | motor/strateji/dis/v3_adaylar_3.py:68:LondraVolatiliteKirilim |
| v3__momentum-sifir-kesisim | motor/strateji/dis/v3_adaylar_3.py:164:MomentumSifirKesisim |
| v3__orb-4s-hacim-atr | motor/strateji/dis/v3_adaylar_2.py:108:Orb4sHacimAtr |
| v3__pazartesi-dip-endeks | motor/strateji/dis/v3_adaylar_3.py:179:PazartesiDip |
| v3__rsi14-ema200-izleyen-stop | motor/strateji/dis/v3_adaylar_3.py:195:Rsi14Ema200Iz |
| v3__rsi2-sma200-hacim | motor/strateji/dis/v3_adaylar_3.py:212:Rsi2Sma200Hacim |
| v3__rsi30-hacim-ema200 | motor/strateji/dis/v3_adaylar_3.py:230:Rsi30HacimEma200 |
| v3__rsi32-yon-hedef4 | motor/strateji/dis/v3_adaylar_3.py:100:Rsi32Yon |
| v3__saat-21-23-utc | motor/strateji/dis/v3_adaylar.py:77:Saat2123Utc |
| v3__saatlik-asiri-tepki | motor/strateji/dis/v3_adaylar.py:103:SaatlikAsiriTepki |
| v3__sma-trend-rsi-atr | motor/strateji/dis/v3_adaylar_3.py:119:SmaTrendRsiAtr |
| v3__ters-fvg-nq-long | motor/strateji/dis/v3_adaylar_2.py:159:TersFvgNqLong |
| v3__volatilite-kirilim-k05 | motor/strateji/dis/v3_adaylar.py:223:VolatiliteKirilimK05 |
| v3__yarim-fitil | motor/strateji/dis/v3_adaylar_3.py:144:YarimFitil |
| v3__z-skor-karsit | motor/strateji/dis/v3_adaylar_3.py:249:ZSkorKarsit |

421 ayar kaydının 336’sında özgül `kart:`/`dis:` kimlikli koşu var: 226 kitap ayarı + 110 dış ayar.67 dış ayar ve 18 d11j/d12b ayarı için özgül kimlikli sonuç bulunamadı. Bunlar 85 ayrı sınıf demek değildir; ailelerin varsayılan koşuları bu modların çalıştığını göstermez. İzler ve varsayımlar `ara/P5_ayar_kosu_izleri.csv`de korunur.

## E — açıklamasız kodlanmayanlar ve iz eksikleri

Kesin E listesi boştur (`ara/AKIBET_E.csv`). Bu, her kaynağın hesabının geçmişte doğru verildiğini göstermez. 621 kaynak profili açık uygulama/karar izinden yoksun veya BIZDE_YOK beyanı taşıyan adaydır: `ara/P8_iz_eksigi_E_adaylari.csv`. Tam özgün kural yokken başka isim altında aynı uygulamanın bulunmadığı ispatlanamaz; kullanıcı kuralına uygun biçimde BELIRSIZ bırakıldı. Geri kalan BELIRSIZlerde benzerlik iddiası, eksik asıl kod, çelişkili karar veya kapısız ayar taraması gibi başka nedenler vardır. Bu 621 kayıt bütün belirsizliklerin tamamı değildir.

## Elemenin adaleti ve somut temsil farkları

v2’de 222 satırdan 18’i ilk elemeyi geçer. 73 satır E1 kârlılık ve E3 yoğunlaşmayı geçip E2/E4/E5ten kalır; kaynak kapı/değerleri `ara/P3_v2_yapisal_kapi.csv`de, gerçek kod satırları `yapisal_kapi=evet` işaretlidir. Bu tespit kuralların yanlış olduğunu veya aynı veri üzerinde eşik gevşetmek gerektiğini kanıtlamaz. v2nin varsayılan ayarı, eski WFdeki grid taramasını yok sayacak şekilde anlatılmadı.

Altı v2 hata kaydı ayrı tutuldu: dört sınıfta üst TF=alt TF, iki portföyde evren uygunluğu. Güncel operasyonel BELIRSIZ olan 6 listesi:

| Kod | Hata/kanıt |
|---|---|
| dis__norn-weave-thurisaz | 35 sembolde koşu hatası: ValueError: 1d üst TF olarak kullanılamaz (alt TF 1 days 00:00:00) |
| dis__shm-wma | 35 sembolde koşu hatası: ValueError: 1d üst TF olarak kullanılamaz (alt TF 1 days 00:00:00) |
| onceki__4s-kirilim | 35 sembolde koşu hatası: ValueError: 1d üst TF olarak kullanılamaz (alt TF 1 days 00:00:00) |
| onceki__kgt | 35 sembolde koşu hatası: ValueError: 1d üst TF olarak kullanılamaz (alt TF 1 days 00:00:00) |
| pf__gumus_makro | portföy koşusu hata: RuntimeError: varsayılan ayar bu evrende uygun değil (yeterli sembol/çift yok) |
| pf__son1ay_e014 | portföy koşusu hata: RuntimeError: varsayılan ayar bu evrende uygun değil (yeterli sembol/çift yok) |

Bağımsız kural/kod açılarak incelenen altı temsil sorunu:

| Kaynak | Bulgu |
|---|---|
| S0002 | Dış kural 6 saat, yalnız long, SMA200, alt kanal çıkışı ve kaynaksız stop. Sınıfın varsayılanı 20/10 kanal, SMA filtresi kapalı, short açık ve 2 ATR stop; ızgara SMA200/short/stop_modu seçeneklerini taramıyor. Kaynak kuralla aynı ayarın 6 saatte koşulduğu kanıtı yok. |
| S0005 | Dış kural MACD>signal DURUMU ile EMA100 fiyat filtresini birlikte arıyor, çıkışta iki şartın birlikte bozulmasını istiyor. Kod kesişim OLAYI kullanıyor; EMA100 fiyat filtresi ve o birleşik çıkış yok. ATR stop ekli. |
| S0141 | Dış kural ay sonu 10 AYLIK kapanışın ortalamasını ve beş ETF/T-bill sepetini kullanıyor. Kod 300 GÜNLÜK takvim ızgarasında tüm günlük kapanışların ortalamasını, farklı evreni ve zorunlu ATR stopunu kullanıyor. 300 günlük günlük ortalama matematiksel olarak 10 ay-sonu kapanış ortalamasına eşit değildir. |
| S0153 | Dış kural aylık evren seçimi, geçmiş Sharpe süzgeci, L/eşik yeniden seçimi ve ATR iz süren stop içeriyor. Kod L=20/eşik=0/ATR=3 sabit, evren seçim katmanı yok; momentum tersine dönünce çıkıyor. Sınıfta ATR iz süren çıkış ayarı tanımlanmamış; taban varsayılanı kapalı. |
| S0244 | Dış kural Upbit gününü 09:00 KST ile kesiyor ve sonraki gün açılışında çıkıyor; kaynakta stop yok. Kod üç kapanışlık trend filtresi ekliyor, 2 ATR stop ve kapanışla doğrulanan ilk tetik kullanıyor. |
| ROBOTIC:K001 | Katalog çekirdeği EMA28/48 ile StochRSI şartını veriyor. Bizde tipik fiyatın 30/6/4 LWMA dizilimi, çizgi eğimleri, Gator histogram açılması ve ATR eşiği var; StochRSI şartı yok. |

Örneğin 6 saatlik Donchian filtresiz kısa/uzun ve ATRstoplu uygulamayla; 10 ay-sonu kapanış ortalaması 300 günlük kapanış ortalamasıyla; EMA100 filtreli MACD durum kuralı MACD kesişim olayıyla eşit kabul edilmedi. AdaptiveTrend sınıfında ATR iz-stop ayarı bulunmadı. Kore 9KST ile 00UTC zaman eşitliği fark diye yazılmadı. Karşılaştırmaların kaynak/kod konumları ve sınırlamaları `ara/P8_manuel_mantik_denetimi.csv` içindedir. Tüm B kayıtlarının adil olmadığı iddia edilmez; tam temsil kanıtı eksik olanlar dürüstçe belirtilir.

## Belgelerdeki sayılar

| Konu | Dosyadan ölçüm | Hüküm |
|---|---|---|
| 460 tek grafik +19 portföy | c10e79d: 460 + 19; güncel:492 +29=521 | Tarihsel sayı doğru; bugünkü tüm kaynak veya test adedi değil |
| ~120 ek ayar/mod | 177 dis_ayarlari +11 d11j +7 d12b=195 yazılı ayar; kitap226 ile421. 336 ayar için özgül kaynak kimlikli koşu kaydı,85 için yok. | Yaklaşık sayının birimi açık değil;195 yazılı kayıtla birebir eşit değil. Kod ailesinin testi her ayarın testi değil. |
| Kart dizini | 810 güncel kitap kartı; v3 kartları154 ayrı | Dizin kitap kartlarının tamamını kapsamıyor |
| v3 kod ve koşu | 35=9 sonuç+26 koşu kanıtsız | Doğrulandı; C gerçek kod listesi26, kaynak profilleriyle53 görünmesi53 ayrı kod değil |
| v2 yapısal eleme | 222,73; ayrıca6 hata | Doğrulandı; hata performans elemesi değil |
| GitHub g1..g7 | 1198 | Satır sayısı; bağımsız strateji/test sayısı değil |
| Kakushadze 151 | CSV173 | Kitap başlığı ile envanter alt strateji satırı farklı birim |
| Repo raporları | Güncel CSV331 | Farklı sürüm;314 bugünkü kapsam sayısı değil |
| Dış liste turları | 906 son liste;707+199=906 | Üst kümeler; eski turlar ham sayımda yok.18 kural/parametre sürüm farkı korundu |
| Robotic909/540 | 909 dosya,540 üyelik kümesi; toplamsal üyelik909 | Üyelik doğrulandı;540 mantıksal tekil strateji olduğu ispatlanmadı |
| ChatGPT26 | Tekil CSV yok;1 eksik-liste toplu kaydı | 26 adı/kuralı uydurulmadı; satır kapsamı doğrulanamaz |

## Öz denetim ve doğrulama sınırı

Tohum `random.Random(20261113)`, sıralama `tekil_id` artan. İlk taslaktaki 40 kayıtta 12 kayıt etkilendi (%30): 7 Robotic ad alanı, doğrulanmamış 3 ML hükmü, 1 aşırı geniş yasak-tür eşleşmesi, 1 eksik arşiv sonuç zinciri. İlgili parçalar bütünüyle düzeltildi; ilk hatalı anın eksiksiz değişmez snapshotı bulunmadığı açık yazıldı (`ara/P9_ilk_taslak_hata_gunlugu.csv`).

Son 8.197 kayıt nüfusundan 40 yeniden seçildi; orijinal CSV/JSON/Excel/AST kaynakları ara veri_json yerine yeniden açıldı. İki eksik tür sınıflaması bulundu: LLM sistemi ve opsiyon straddle,2/40=%5. Aynı açık tür kanıtına sahip bütün kayıtlar düzeltildi. Aynı 40 üzerindeki son kontrolde kalan hata 0; bu bağımsız üçüncü örneklem veya tüm tablonun hatasızlık garantisi değildir. Her kaydın ayrı gerekçesi `ara/P9_oz_denetim_orneklemi.csv`, orijinal kaynak kanıtı `ara/P9_asli_kaynak_kanitlari.json`, düzeltme öncesi ikinci örneklem de `ara/`dadır.

Nihai tablo SHA256: `06cb8b36d3307e03f4f749968be027f0b00c63219e94649c0cfe25359a66da52`. Ham kimlik/bağlantı eksikliği 0, yinelenen ham_id 0, sayım farkı 0; 2.535 kaynak dosyada SHA256 değişimi 0. Bunlar muhasebe bütünlüğünü doğrular; eksik üçüncü taraf kodun mantığını doğrulamaz. Strateji testi/backtest, paket kurulumu veya strateji kodu değişikliği yapılmadı.

## Sonraki karar için somut iş listesi

1. 621 iz eksikliği adayında önce özgün kuralları ve yazılı kodlama kararını tamamlayın; isim benzerliğiyle eleme yapmayın.
2. 26 kod tanımı ve 85 özgül ayarın koşu kapsamını ayrı yönetin; bunları test edilmiş havuz sayısına eklemeyin.
3. Yapısal 73 kayıt için ekonomik sonuç ile uyumluluk gerekçesini ayrı değerlendirin; kanıt olmadan başarı etiketi vermeyin.
4. Kaynak kuralı → uygulama → ayar → koşu → kapı zincirini kalıcı kimlikle tutun; kart dizinini bu zincirden üretin.
5. Bu denetim tamamlanan yerel belge muhasebesidir. Ajan2 eksik 26 listesi ve 909 dış kodun bağımsız doğrulaması için gerekli dosyalar mevcut değil; bu sınır BELIRSIZ olarak bırakıldı.

## Dosyaları kullanma

`ham_satirlar.csv`den herhangi bir kaydın kaynağına ve `tekil_id`sine gidilebilir. `tekil_stratejiler.csv` her profile tek durum, aşama, kanıt, temsil/adalet notu ve bağlı kod idlerini verir. `ara/AKIBET_*.csv` durum filtreleridir. Kaynak/ham/profil birimleri ve sayım dayanakları bu raporda; yeniden üretme sırası `betikler/yeniden_uret.py` ve `ILERLEME.md`dedir.
