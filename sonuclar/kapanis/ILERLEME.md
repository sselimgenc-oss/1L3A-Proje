# Kapanış turu ilerleme kaydı

Son kontrol: 2026-11-13 11:39 UTC. **Görev bitmedi; gerçek piyasa verisi koşulmadı.** Bu dosya oturum devam noktasıdır.

## Değişmez ön kayıt

- Dal: `codex/kapanis-turu`, taban `origin/main` `d960401`.
- Ön kayıt commit'i: `7a89080`. `aday_listesi.csv` değişmez. `ON_KAYIT_KAPANIS.md` asıl metni korunarak, kullanıcının 2026-11-13 tarihli BH aile düzeltmesi sonuç görülmeden ek başlıkta kaydedildi (`02e0424`).
- 4.773 kapalı kayıt: 4.067 ana kaynak kimliği + 85 ayar izi + 621 iz incelemesi. Ana 4.067 = K1 46 + K2 6 + K3 1.816 + K4 2.199. K2'deki 5 D kaydı K4 karar tablosunda da sayılır; bunlar koşuda tek hipotez olur.
- Kaynak SHA-256'ları ön kayıtta. Hakem metni main'de yoktu; `origin/pr-58` dalındaki `HAKEM_FABLE.md` okundu, bu dala kopyalanmadı.

## Katman durumu ve sayı kontrolü

| Katman | Girdi | Karar tablosu | Son karar | Kod/koşu | Durum |
|---|---:|---:|---:|---|---|
| K1 | 48 = 26 v3 + 18 ek ayar + 4 teknik hata | 48 | 2 kaynak/evren ret; 46 açık | 18 ayar okuyucusu kuruldu; 26 v3 kartı ve 18 ayar kaynağı satıra bağlandı; dört teknik hata için TF seçildi ve sentetik sinyal testi geçti; koşu bağı yok | sürüyor |
| K2 | 7 kaynak biçimi (saatlik, T61, T21, S0002, S0005, Ichimoku, Argus); S0083 gibi alt kaynaklar K4'te | ayrı karar tablosu yok | 0 | S0002 ve S0005 yeni sınıfları + sentetik test | sürüyor |
| K3 | 1.816 = 161 E + 35 belirsiz + 1.620 diğer D | 1.816 | 0 | kaynak uygunluğu incelenmedi | başlamadı |
| K4 | 2.204 `benzer_hedef` dolu D (K2'ye ayrılan 5 dahil) | 2.204 | 0 | kaynak ↔ arşiv kodu tek tek karşılaştırılmadı | başlamadı |
| K5 | 706 = 85 ayar izi + 621 iz adayı | 706 | 85 ayarın iz kararı; 535 iz kaydı ana deftere, 78 kart ve 8 arşiv kaydı özgün kaynağa bağlandı; nihai akıbet bekliyor | 18 ayar gerçekten aday havuzuna girmemiş; 67 eski WF aday havuzunda | sürüyor |

Tablolardaki `INCELEME_BEKLIYOR` bir hüküm değildir. `kanit` sütununda eski hesap defterinin başlangıç izi vardır; kaynak-kod eşitliğinin yeni doğrulaması değildir. Satır sayılarını koşudan önce tekrar doğrula. K2/K5 katmanları K1/K3/K4 ile örtüştüğünden rakamlar toplanıp bağımsız strateji sayısı diye sunulmaz.

## K5 koşu izi çapraz denetimi

- Eski dalın 85 `P5_ayar_kosu_izleri.csv` ayarının tümü `G0_ayarlar.csv` kayıtlarına yol/indeks ve ayar kimliğiyle eşlendi: 18 ek JSON ayarı aday havuzunda yok, 67 ayar v1 WF aday havuzunda. 67 için bu iz, tam eşit kaynak kuralının adil kapılardan geçtiği anlamına gelmez; tam koşu/kaynak karşılaştırması K1/K4 kararıyla yapılır. G0 sınıflaması 20 seçilen + 47 aday; Fable 18 + 49 dediği için bu sayım uyuşmazlığı ayrıca kontrol edilecek.
- Eski dalın 621 `P8_iz_eksigi_E_adaylari.csv` satırından 80 `DIS906:Sxxxx`, `ham_satirlar.csv` içindeki `X005:xxxx` üzerinden ana `tekil_id`ye bağlandı: 29 E, 24 H, 16 D, 10 F, 1 belirsiz ön durum. KAYIT ve EXCELKURAL kayıtlarının 440 tanesi daha eski P8 adı ile ana `ham_satirlar.csv` adı birebir ve tekil eşleştiği için yalnız kimlik düzeyinde bağlandı. 23 KAYIT/EXCELKURAL satırının 15’i xlsx satırıyla ana deftere bağlandı; 8’i ayrı arşiv kaydında. 78 KART kaydının özgün kart dosyası `stratejiler/v3_adaylar/kartlar/` altında ayrı ayrı bulundu; ana defter kapsamı ve kuralın koşulabilirliği açık. Ad eşitliği kural eşitliği kanıtı değildir. Bunlar ayrı aday değildir. Kalan 23 kaydın 15’i xlsx sayfa/satır ve adla ana deftere bağlandı; 8’i `arsiv/codex-algo/config/pdf_candidates.csv` içinde bulundu. Böylece 621 iz kimliğinin kaynağı belli; 621’inin de nihai kural/koşu hükmü bekliyor.

## K1 kaynak izi ve ilk hükümler

- `k1_karar.csv` içindeki 48 satırın kaynak TF/piyasa/kart izi yazıldı: 26 v3 kartı, 18 ek ayar JSON kaydı ve dört teknik hata kod izi. Kart metni birincil kaynak kuralının doğrulanması yerine geçmez.
- `AYAR:dis__funding-carry:d11j:funding-pozitif-short:esik0_short` **KURAL_YOK**: `github_g3_cerceve.csv:24` pozitif funding’de short açma API örneği; kaynak çıkışı yok. JSON’daki 16 saat çıkışı kaynakta yazmıyor.
- `KOD:v3__ters-fvg-nq-long` **EVREN_DISI**: NQ 5m/15m ve NQ puan tamponu gerekir; ön kayıt evreninde NQ yok.
- V2 teknik hatalı dört kod için eski 1d üst-TF hatasını önleyen TF kaydı: Norn 4h, SHM 4h, önceki 4s kırılım 4h, KGT 1h; hepsi v2 kripto 13 sembol. Dört sınıf 1.100 sentetik mumla sinyal üretti, hiçbir giriş stopsuz değil (`testler/test_kapanis_k1_teknik.py`, 4 geçti). Kaynak/çıkış uyumu ve hesap koşu bağı hâlâ açık.
- Kalan 46 satırın kaynak biçimi/uyarlama ve araştırma hesabı koşu bağı henüz kesinleşmedi. Özellikle eski tek grafik Donchian ansamblı, kaynak biçiminden farklı olduğu için doğrudan koşuya alınmaz; yeni portföy biçimiyle sonuç/kimlik bağı denetlenir.

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
- `testler/test_kapanis_jesse_kaynak.py`, `testler/test_kapanis_ek_ayarlar.py` ve `testler/test_kapanis_k1_teknik.py`: 10 sentetik test geçti (`PYTHONPATH=/tmp/kapanis-test-deps:. python -m pytest ...`). Gelecek mum değişimi geçmiş sinyali etkilemiyor; her girişte stop var; ek ayarlar eksiksiz ve tekil.
- Tüm suite geçti: `PYTHONPATH=/tmp/kapanis-test-deps:. python -m pytest testler -q -p no:cacheprovider` → **5101 geçti, 17 atlandı** (315 saniye). Eksik Python geliştirme paketleri yalnız `/tmp/kapanis-test-deps` altına kuruldu; repo bağımlılık dosyaları değişmedi. Bu koşu sentetik/birim testleridir; gerçek piyasa strateji koşusu değildir.
- `veri/mumlar` bu ortamda yok; gerçek koşu burada yapılamaz.
- `araclar/kapanis_kosu.py` henüz yazılmadı. Koşu listesi/kapılar/BH/ikinci evren/test sonuçları hazır değil. Veri yokluğu nedeniyle gerçek strateji testi yapılmadı.

## Devam sırası

1. K1'in kalan 46 satırına kaynak TF, evren, ayar ve çalıştırılabilirlik kararı ver. 18 ayarın okuyucusunu koşuya bağla; 1h portföy ve araştırma risk/kill hesabını canlı limitlere dokunmadan çöz. K5'in 621 iz akıbetini ana K1/K3/K4 kararına bağla.
2. K2 kısa listesinin kaynak metnini/kodunu doğrula; yalnız tam kuralı belli biçimleri kodla, belirsizleri kanıtla dışla.
3. K3'ün 1.816 satırını kanıtla karara bağla.
4. K4'ün 2.204 satırında arşiv kodunu açıp anlamlı farkı denetle; K5 bağlarının nihai akıbetini de kapat. Bütün katmanlarda girdi = karar satırı kontrolü yap.
5. Yalnız gerçekten koşulacak benzersiz strateji/ayarları listeye al; listeyi ve BH aile büyüklüğünü sonuç görülmeden dondur. Tek koşu betiği, kapılar ve yeni 40 sembol aşamasını hazırla. Bu ortamda gerçek mum koşusu yapılmaz.
6. Uçtan uca sentetik test, sonra tüm pytest. Hazırlık raporunu nihai sayılarla yaz. Her katman bitince ara commit; hepsi bitince PR aç, main'e birleştirme.
