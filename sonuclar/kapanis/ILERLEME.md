# Kapanış turu ilerleme kaydı

Son kontrol: 2026-11-13 11:39 UTC. **Görev bitmedi; gerçek piyasa verisi koşulmadı.** Bu dosya oturum devam noktasıdır.

## Değişmez ön kayıt

- Dal: `codex/kapanis-turu`, taban `origin/main` `d960401`.
- Ön kayıt commit'i: `7a89080`. `ON_KAYIT_KAPANIS.md` ve `aday_listesi.csv` sonraki commit'lerde değişmez.
- 4.773 kapalı kayıt: 4.067 ana kaynak kimliği + 85 ayar izi + 621 iz incelemesi. Ana 4.067 = K1 46 + K2 6 + K3 1.816 + K4 2.199. K2'deki 5 D kaydı K4 karar tablosunda da sayılır; bunlar koşuda tek hipotez olur.
- Kaynak SHA-256'ları ön kayıtta. Hakem metni main'de yoktu; `origin/pr-58` dalındaki `HAKEM_FABLE.md` okundu, bu dala kopyalanmadı.

## Katman durumu ve sayı kontrolü

| Katman | Girdi | Karar tablosu | Son karar | Kod/koşu | Durum |
|---|---:|---:|---:|---|---|
| K1 | 48 = 26 v3 + 18 ek ayar + 4 teknik hata | 48 | 0 | 18 ayar okuyucusu kuruldu; veri/hesap koşu bağı yok | sürüyor |
| K2 | 7 kaynak biçimi (saatlik, T61, T21, S0002, S0005, Ichimoku, Argus); S0083 gibi alt kaynaklar K4'te | ayrı karar tablosu yok | 0 | S0002 ve S0005 yeni sınıfları + sentetik test | sürüyor |
| K3 | 1.816 = 161 E + 35 belirsiz + 1.620 diğer D | 1.816 | 0 | kaynak uygunluğu incelenmedi | başlamadı |
| K4 | 2.204 `benzer_hedef` dolu D (K2'ye ayrılan 5 dahil) | 2.204 | 0 | kaynak ↔ arşiv kodu tek tek karşılaştırılmadı | başlamadı |
| K5 | 706 = 85 ayar izi + 621 iz adayı | 706 | 85 ayarın iz kararı; 520 iz kaydı ana deftere bağlandı, nihai akıbet bekliyor | 18 ayar gerçekten aday havuzuna girmemiş; 67 eski WF aday havuzunda | sürüyor |

Tablolardaki `INCELEME_BEKLIYOR` bir hüküm değildir. `kanit` sütununda eski hesap defterinin başlangıç izi vardır; kaynak-kod eşitliğinin yeni doğrulaması değildir. Satır sayılarını koşudan önce tekrar doğrula. K2/K5 katmanları K1/K3/K4 ile örtüştüğünden rakamlar toplanıp bağımsız strateji sayısı diye sunulmaz.

## K5 koşu izi çapraz denetimi

- Eski dalın 85 `P5_ayar_kosu_izleri.csv` ayarının tümü `G0_ayarlar.csv` kayıtlarına yol/indeks ve ayar kimliğiyle eşlendi: 18 ek JSON ayarı aday havuzunda yok, 67 ayar v1 WF aday havuzunda. 67 için bu iz, tam eşit kaynak kuralının adil kapılardan geçtiği anlamına gelmez; tam koşu/kaynak karşılaştırması K1/K4 kararıyla yapılır. G0 sınıflaması 20 seçilen + 47 aday; Fable 18 + 49 dediği için bu sayım uyuşmazlığı ayrıca kontrol edilecek.
- Eski dalın 621 `P8_iz_eksigi_E_adaylari.csv` satırından 80 `DIS906:Sxxxx`, `ham_satirlar.csv` içindeki `X005:xxxx` üzerinden ana `tekil_id`ye bağlandı: 29 E, 24 H, 16 D, 10 F, 1 belirsiz ön durum. KAYIT ve EXCELKURAL kayıtlarının 440 tanesi daha eski P8 adı ile ana `ham_satirlar.csv` adı birebir ve tekil eşleştiği için yalnız kimlik düzeyinde bağlandı. 23 KAYIT/EXCELKURAL ve 78 KART kaydı hâlâ kimlik bağında açık. Ad eşitliği kural eşitliği kanıtı değildir. Bunlar ayrı aday değildir. Kalan 101 iz satırı ve 520 satırın nihai kural/koşu hükmü bekliyor.

## İlk kaynak denetiminde bulunan ayrımlar

- `S0002` 6h Donchian20 + SMA200 + karşı alt bant çıkışı, **kaynakta 2R hedef yok**; kaynak stopu yok. Yeni sınıf buna göre yazıldı; ATR×3 stop açık uyarlama. 2R hedefli EMA200/H4 kaynak **S0083** (aday listesinde `HAM:X005:83`), ayrı karşılaştırma ister. T02 ailesi diye iki kural eşit sayılmaz.
- `S0005` MACD çizgisi sinyal üstünde **durum** + fiyat EMA100 üstünde; çıkış iki koşul birlikte tersine dönünce. Yeni sınıf ters kesişim olayıyla karıştırmaz; stop ATR×3 uyarlama.
- S0002 ve S0005'in birincil Python dosyaları `jesse-ai/example-strategies` commit `7c91e0a37bf62165790120d730442e4f6eb00364` üzerinden salt okunur açıldı. SHA-256 sırasıyla `fc635b257ad1e12951dc140dae46a63bd37e9abfa5f2d681ef1e754d8ce393fe`, `5c0cae71e63a5a510220d60d6bba48ae39a542aa988154eaa13b91f8dd2209a8`. S0005 dosyasının üst açıklamasında “crosses” yazsa da çalışan `should_long` gövdesi MACD>signal **durumunu** kullanıyor; kod davranışı esas alındı. Üçüncü taraf kodu repoya kopyalanmadı.
- T61'in %20 iz stoplu biçimi **S0879** (`HAM:X005:879`, K4 kapsamı); `S0687` kaynakta X hisse başına örneklem içinde optimize ve çoğunlukla %1 altı. İkisi kaynak değeri bakımından farklı. Ön kayıtta T61 başlığı altındaki S0687 referansı tek başına %20 biçimi temsil etmez; iki kayıt da kapalı kümede mevcut.
- T21/S0395 tek makalede 10 önceden belirtilmiş (S,L,B) kuralı içeriyor. Bunlar tek bir parametre seçimi değildir; deney kimliği/çoklu test sayımı çözülmeden rastgele birini seçme.
- `v3__saatlik-asiri-tepki` mevcut kodunun docstring'i eşik/süre/stop değerlerinin kaynakta bulunmadığını söylüyor; birincil metin doğrulanmadan “birebir kaynak” olarak koşuya bağlanamaz.
- 26 v3 kodunun içinde `pf__v3-funding-1s-devam` (1h portföy altyapısı eksik) ve `v3__ters-fvg-nq-long` (NQ 5m veri/evren dışı) var. K1'de bütün 26'yı körlemesine koşuya sokma.
- V2 tek-grafik yeniden oynatıcısı işlem riski/kill ayarı alıyor; mevcut portföy motoru SERT_LIMITLER ile %1/−%20 kullanıyor. Ön kayıttaki %1,5/−%30 ayrı araştırma hesabı portföy için henüz uygulanmadı. Bu fark çözülmeden koşu yasak.

## Kod ve doğrulama

- `motor/strateji/kapanis/jesse_kaynak.py`: S0002 ve S0005, kaynak satırı/linki, ATR uyarlaması yazılı.
- `motor/arastirma/kapanis/ek_ayarlar.py`: 18 ayarı iki JSON'dan okur, sınıfına kurar; eski araştırma aday kümelerine müdahale etmez.
- `testler/test_kapanis_jesse_kaynak.py` ve `testler/test_kapanis_ek_ayarlar.py`: 6 sentetik test geçti (`PYTHONPATH=/tmp/kapanis-test-deps:. python -m pytest ...`). Gelecek mum değişimi geçmiş sinyali etkilemiyor; her girişte stop var; ek ayarlar eksiksiz ve tekil.
- Tüm suite geçti: `PYTHONPATH=/tmp/kapanis-test-deps:. python -m pytest testler -q -p no:cacheprovider` → **5101 geçti, 17 atlandı** (315 saniye). Eksik Python geliştirme paketleri yalnız `/tmp/kapanis-test-deps` altına kuruldu; repo bağımlılık dosyaları değişmedi. Bu koşu sentetik/birim testleridir; gerçek piyasa strateji koşusu değildir.
- `veri/mumlar` bu ortamda yok; gerçek koşu burada yapılamaz.
- `araclar/kapanis_kosu.py` henüz yazılmadı. Koşu listesi/kapılar/BH/ikinci evren/test sonuçları hazır değil. Veri yokluğu nedeniyle gerçek strateji testi yapılmadı.

## Devam sırası

1. K5 çapraz bağ çalışmasını commit et ve uzak dala gönder. Sonra kalan 101 iz satırını kaynakta tekilleştir; kaynak eşitliğini ayrıca denetle.
2. K1'in 48 satırına kaynak TF, evren, ayar ve çalıştırılabilirlik kararı ver. 18 ayarın okuyucusunu araştırma koşucusuna bağla. 1h portföy ve risk/kill ayrımını çöz.
3. K2 kısa listesinin kaynak metnini/kodunu doğrula; yalnız tam kuralı belli biçimleri kodla, belirsizleri kanıtla dışla.
4. K3/K4/K5'in **her** satırını kanıtla karara bağla; `INCELEME_BEKLIYOR` sıfır olmadan koşu planı dondurulmaz.
5. Tek koşu betiği, kapılar, BH, yeni 40 sembol aşaması ve uçtan uca sentetik test; ardından tüm suite. Bu ortamda gerçek mum koşusu yapılmaz.
6. Hazırlık raporunda kalan soru işaretlerini dürüstçe say. Her katman tamamlanınca ayrı commit; hepsi bitince PR aç, main'e birleştirme.
