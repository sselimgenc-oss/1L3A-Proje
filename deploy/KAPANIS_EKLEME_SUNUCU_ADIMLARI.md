# Paper'a 6 kapanış stratejisi ekleme — sunucu adımları (10 → 16 hesap)

**Ne oluyor?** Çalışan paper'a (10 strateji) kapanış turunun 6 stratejisi eklenir: HAM:X005:664#v1, HAM:X005:705, HAM:X005:301#v1,
HAM:X005:138#v3 (1g/4h) ve HAM:B001:670#v1, HAM:B001:574#v1 (5m). Hepsi kripto13 evreninde, **her biri kendi 10.000 USD sanal kasasında**,
risk ölçeği mevcut setle aynı (işlem başı %0,5). Panoda etiketleri **kapanış adayı**: ileri dönem sınavı gerekli, yeterli değil; canlı şartı
(12 hafta paper + sizin onayınız) aynen geçerli. Gerçek emir YOK, gizli anahtar YOK.

**Mevcut 10 hesaba ne olur?** Hiçbir şey: durumları (açık pozisyon, işlem geçmişi, kasa) olduğu gibi yüklenir. Yeni 6 hesap sıfırdan açılır.
Motor, durum dosyası 10'lu setin imzasını taşıyorsa bunu tek izinli "ekleme geçişi" sayar; başka bir uyuşmazlık varsa **açık hatayla başlamaz**
(durum bozulmaz). Eski durumu kenara almak (v2_gecis.sh'teki gibi) bu sefer GEREKMEZ; betik yalnız **kopya yedek** alır.

**Önce bilmeniz gerekenler**
- Mevcut paper'ın kasa/pano sayıları toplamda 10 hesaptan 16 hesaba çıkar (üst düzey rakamlar 16 kasanın TOPLAMIDIR; başlangıç 160.000 USD görünür).
- 5m stratejiler çok sık mum işler; ilk açılış eskisinden birkaç dakika uzun sürebilir (13 sembolün 5m geçmişi Binance'ten çekilir).
- Pano "Bütünlük" bandı: 16'lı setin kaydı yeni dosyada (`stratejiler/butunluk_kayit_v2_16.json`); eski mühürlü kayıt (`sonuclar/final/butunluk_kayit_v2.json`) değişmeden durur. `git pull` sonrası "eşleşti" görünmeli.
- Kapanış adayları canlı yürütücüye ALINAMAZ (kodda reddedilir): 12 hafta paper + sizin onayınız şartı korunur.

## Adımlar (sunucuda; her kutuyu sırayla kopyala-yapıştır, bir sonrakine geçmeden çıktıyı kontrol edin)

**Neden bu sıra?** Önce paper durdurulur; böylece yeni kod inerken servis kendiliğinden yeniden başlayıp yedeksiz geçiş yapamaz.

**1. Paper'ı durdurun**
```bash
sudo systemctl stop 1l3a-paper
systemctl is-active 1l3a-paper        # "inactive" yazmalı
```
**2. Mevcut durumu yedekleyin** (kopya; asıl dizin yerinde kalır) ve şu anki kod sürümünü not edin
```bash
sudo cp -a /var/lib/1l3a-paper/durum /var/lib/1l3a-paper/yedek_16_oncesi_$(date +%Y%m%d_%H%M)
cd /opt/1l3a
sudo -u l3a git rev-parse HEAD        # çıkan uzun kodu bir yere NOT EDİN (geri dönüş için)
sudo -u l3a git branch --show-current # dal adını da not edin
```
**3. Yeni kodu çekin**
```bash
sudo -u l3a git pull --ff-only
```
**4. Betiği çalıştırın** (durum imzasını kontrol eder, ön kontrol yapar, paper'ı başlatır, 3 dk sonra kontrol çıktısı yazar)
```bash
cd /opt/1l3a
sudo bash deploy/v2_kapanis_ekle.sh
```
Betik hata verirse ekrana "paper DURDU" ve ne yapacağınızı yazar; çıktının tamamını bana yapıştırın.
**Çıktının tamamını bana yapıştırın.**

## Doğrulama (3-5 dakika sonra)
```bash
systemctl is-active 1l3a-paper                                   # active
journalctl -u 1l3a-paper -n 80 --no-pager | grep -i -E "yeni hesap|yeni_hesap|hata|error|BAŞLAMAZ"
ls /var/lib/1l3a-paper/durum/hesaplar | wc -l                    # 16
ls /var/lib/1l3a-paper/durum/hesaplar | grep HAM                 # 6 klasör: HAM_X005_664_v1, HAM_X005_705, HAM_X005_301_v1, HAM_X005_138_v3, HAM_B001_670_v1, HAM_B001_574_v1
python3 -c "import json;d=json.load(open('/var/lib/1l3a-paper/durum/paper_state.json'));print(len(d['hesaplar']),d['set_imza'])"   # 16 4c22e27149b65a14
```
Beklenen: `yeni_hesap` olayı (6 satır, "kasa SIFIRDAN açıldı"); mevcut 10 hesapta pozisyon/işlem sayısı güncelleme öncesiyle aynı (önce/sonra karşılaştırmak için
yedekteki `paper_state.json` ile bakabilirsiniz). Panoda 6 yeni strateji **kapanış adayı** etiketiyle, her biri 10.000 USD kasayla görünür.
Normal uyarılar: mevcut `DK_JNJ`/`DK_MA` notları (kripto stratejilerini etkilemez).

## Hata durumunda
- `kayıtlı set imzası ... != şimdiki ...`: durum dosyası beklenen 10'lu sete ait değil. **Dokunmayın**, çıktıyı bana yapıştırın (yedek zaten alındı).
- `paper v2 seti BAŞLAMAZ: ... çıkış ayarlarını kullanıyor`: bir strateji paper'ın uygulamadığı çıkış ayarı taşıyor; bilerek durur. Çıktıyı yapıştırın.
- `dondurulmuş liste doğrulanamadı`: `sonuclar/kapanis/kosu_listesi_asama*.csv` eksik/değişmiş (git pull tamamlanmamış olabilir). `git status` çıktısını yapıştırın.

## Geri dönüş (gerekirse)
```bash
systemctl stop 1l3a-paper
cd /var/lib/1l3a-paper && mv durum durum_16lik_deneme && cp -a yedek_16_oncesi_<tarih> durum     # yedeği geri koy
cd /opt/1l3a && sudo -u l3a git checkout <2. adımda not ettiğiniz sürüm>
systemctl start 1l3a-paper
# sonra ileride tekrar güncellemek için dala dönün: sudo -u l3a git checkout <2. adımdaki dal adı>
```
(Eski kod 10'lu imzayı beklediği için yedek durumuyla sorunsuz açılır; 16'lı kayıt eski koda yüklenmez.)
