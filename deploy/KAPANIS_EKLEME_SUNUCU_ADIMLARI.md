# Paper'a kapanış stratejileri ekleme — sunucu adımları (→ 20 hesap)

**Ne oluyor?** Çalışan paper'ın hesap sayısı **20**'ye çıkar. Sunucunuz şu an ya 10 hesaplıdır (kapanış eklemesi henüz uygulanmadı) ya da 16 hesaplıdır
(önceki 6'lık ekleme uygulandı). **Aynı betik ikisini de 20'ye taşır**; hangisinde olduğunuzu bilmeniz gerekmez.

- **6 `kapanış adayı`** (10'dan geliyorsanız eklenir): HAM:X005:664#v1, HAM:X005:705, HAM:X005:301#v1, HAM:X005:138#v3 (1g/4h) ve HAM:B001:670#v1, HAM:B001:574#v1 (5m).
- **4 `kapanış adayı (ek)`** (her iki durumda eklenir): HAM:X005:730#v2, HAM:X005:259#v1, HAM:X005:793#v1 (1g) ve HAM:B001:538#v1 (6h).
  Bunlar ileri dönem sınavının sonucu görüldükten **sonra** seçildi (sonuç sonrası seçim): kanıt değil; 12 haftada canlı adayı olamaz, en fazla "kapanış adayı"na yükselir.

Hepsi kripto13 evreninde, **her biri kendi 10.000 USD sanal kasasında**, risk ölçeği mevcut setle aynı (işlem başı %0,5). Gerçek emir YOK, gizli anahtar YOK.
İkisi de canlı yürütücüye ALINAMAZ (kodda reddedilir); canlı şartı (12 hafta paper + sizin onayınız) aynen geçerli.

**Mevcut hesaplara ne olur?** Hiçbir şey: durumları (açık pozisyon, işlem geçmişi, kasa) olduğu gibi yüklenir. Yalnız eksik hesaplar sıfırdan açılır
(10'dan geliyorsanız 10, 16'dan geliyorsanız 4 hesap). Motor, durum dosyası 10'lu ya da 16'lı setin imzasını taşıyorsa bunu tek seferlik izinli geçiş sayar;
başka bir uyuşmazlık varsa **açık hatayla başlamaz** (durum bozulmaz). Eski durumu kenara almak GEREKMEZ; betik yalnız **kopya yedek** alır.
Durum zaten 20 hesaplıysa betik hiçbir şey yapmaz.

**Önce bilmeniz gerekenler**
- Pano/kasa sayıları 20 kasanın TOPLAMIDIR (başlangıç 200.000 USD görünür).
- 5m stratejiler çok sık mum işler; 6h için de yeni geçmiş çekilir: ilk açılış birkaç dakika uzun sürebilir.
- Pano "Bütünlük" bandı: 20'li setin kaydı yeni dosyada (`stratejiler/butunluk_kayit_v2_20.json`); 16'lık kayıt ve mühürlü `sonuclar/final/` kayıtları değişmeden durur. `git pull` sonrası "eşleşti" görünmeli.

## Adımlar (sunucuda; her kutuyu sırayla kopyala-yapıştır, bir sonrakine geçmeden çıktıyı kontrol edin)

**Neden bu sıra?** Önce paper durdurulur; böylece yeni kod inerken servis kendiliğinden yeniden başlayıp yedeksiz geçiş yapamaz.

**1. Paper'ı durdurun**
```bash
sudo systemctl stop 1l3a-paper
systemctl is-active 1l3a-paper        # "inactive" yazmalı
```
**2. Mevcut durumu yedekleyin** (kopya; asıl dizin yerinde kalır) ve şu anki kod sürümünü not edin
```bash
sudo cp -a /var/lib/1l3a-paper/durum /var/lib/1l3a-paper/yedek_20_oncesi_$(date +%Y%m%d_%H%M)
cd /opt/1l3a
sudo -u l3a git rev-parse HEAD        # çıkan uzun kodu bir yere NOT EDİN (geri dönüş için)
sudo -u l3a git branch --show-current # dal adını da not edin
```
**3. Yeni kodu çekin**
```bash
git pull --ff-only                    # root ile (GitHub anahtarı root'ta)
chown -R l3a:l3a /opt/1l3a            # dosyaların sahibi yine l3a olsun (paper yazabilsin)
```
**4. Betiği çalıştırın** (durum imzasını kontrol eder, ön kontrol yapar, paper'ı başlatır, 3 dk sonra kontrol çıktısı yazar)
```bash
cd /opt/1l3a
sudo bash deploy/v2_kapanis_ekle.sh
```
Betik hata verirse ekrana "HATA ... durdu" ve ne yapacağınızı yazar; çıktının tamamını bana yapıştırın.
**Çıktının tamamını bana yapıştırın.**

## Doğrulama (3-5 dakika sonra)
```bash
systemctl is-active 1l3a-paper                                   # active
journalctl -u 1l3a-paper -n 80 --no-pager | grep -i -E "yeni hesap|yeni_hesap|hata|error|BAŞLAMAZ"
ls /var/lib/1l3a-paper/durum/hesaplar | wc -l                    # 20
ls /var/lib/1l3a-paper/durum/hesaplar | grep HAM                 # 10 klasör (aşağıya bakın)
python3 -c "import json;d=json.load(open('/var/lib/1l3a-paper/durum/paper_state.json'));print(len(d['hesaplar']),d['set_imza'])"   # 20 be84a61831ca9bbc
```
`grep HAM` çıktısında şu 10 klasör olmalı: HAM_X005_664_v1, HAM_X005_705, HAM_X005_301_v1, HAM_X005_138_v3, HAM_B001_670_v1, HAM_B001_574_v1 (kapanış adayı) ve
HAM_X005_730_v2, HAM_X005_259_v1, HAM_X005_793_v1, HAM_B001_538_v1 (kapanış adayı (ek)).

Beklenen: `yeni_hesap` olayı ("kasa SIFIRDAN açıldı"; 10'dan geliyorsanız 10 satır, 16'dan geliyorsanız 4 satır); mevcut hesaplarda pozisyon/işlem sayısı güncelleme öncesiyle aynı
(önce/sonra karşılaştırmak için yedekteki `paper_state.json` ile bakabilirsiniz). Panoda yeni 4 strateji **kapanış adayı (ek)** etiketiyle, her biri 10.000 USD kasayla görünür.
Normal uyarılar: mevcut `DK_JNJ`/`DK_MA` notları (kripto stratejilerini etkilemez).

## Hata durumunda
- `kayıtlı set imzası ... != şimdiki ...` ya da betikte "imzası ne 10'lu ne 16'lı": durum dosyası beklenen sete ait değil. **Dokunmayın**, çıktıyı bana yapıştırın (yedek zaten alındı).
- `paper v2 seti BAŞLAMAZ: ... çıkış ayarlarını kullanıyor`: bir strateji paper'ın uygulamadığı çıkış ayarı taşıyor; bilerek durur. Çıktıyı yapıştırın.
- `dondurulmuş liste doğrulanamadı`: `sonuclar/kapanis/kosu_listesi_asama*.csv` eksik/değişmiş (git pull tamamlanmamış olabilir). `git status` çıktısını yapıştırın.

## Geri dönüş (gerekirse)
```bash
systemctl stop 1l3a-paper
cd /var/lib/1l3a-paper && mv durum durum_20lik_deneme && cp -a yedek_20_oncesi_<tarih> durum     # yedeği geri koy
cd /opt/1l3a && sudo -u l3a git checkout <2. adımda not ettiğiniz sürüm>
systemctl start 1l3a-paper
# sonra ileride tekrar güncellemek için dala dönün: sudo -u l3a git checkout <2. adımdaki dal adı>
```
(Eski kod, yedek durumun imzasını — 10'lu ya da 16'lı — sorunsuz yükler; 20'li kayıt eski koda yüklenmez.)
