# 1L3A paper trading — sunucu kurulumu (DigitalOcean Frankfurt, Ubuntu 24.04)

Bu motor **gerçek emir vermez**, Binance'te **anahtar gerektirmez** (yalnız herkese açık veri). Aşağıdakiler SİZİN yapacağınız
adımlardır; bu depoda sunucuya bağlanan hiçbir şey yoktur.

> Neden Frankfurt: Binance vadeli API'si bazı ülkelerden (ve bu geliştirme makinesinden) engelli (HTTP 451). Frankfurt'ta çalışır;
> yine de kurulumdan sonra aşağıdaki "5. Ağ kontrolü"nü yapın.

## 1. Sunucu ve kullanıcı
```bash
# root olarak, yeni Droplet (Ubuntu 24.04, 1 vCPU / 2 GB yeterli)
apt update && apt install -y python3-venv python3-pip git rsync
adduser --disabled-password --gecos "" l3a
mkdir -p /opt/1l3a && chown l3a:l3a /opt/1l3a
# l3a ile SSH girişi (pano tüneli için, §6): l3a'nın parolası yok; root'a eklediğiniz SSH anahtarını l3a'ya da kopyalayın
install -d -m 700 -o l3a -g l3a /home/l3a/.ssh
install -m 600 -o l3a -g l3a /root/.ssh/authorized_keys /home/l3a/.ssh/authorized_keys
```
Kontrol (kendi bilgisayarınızdan): `ssh l3a@SUNUCU true` hatasız bitmeli. "Permission denied (publickey)" alırsanız yukarıdaki iki
`install` satırını root olarak tekrar çalıştırın (Droplet'ı anahtarla açtıysanız `/root/.ssh/authorized_keys` vardır).

## 2. Kod ve sanal ortam
```bash
sudo -u l3a git clone <DEPO_ADRESI> /opt/1l3a        # ya da: rsync ile kendi bilgisayarınızdan
cd /opt/1l3a
sudo -u l3a python3 -m venv .venv
sudo -u l3a .venv/bin/pip install -r requirements.txt
```

## 3. Tohum veri (geçmiş mumlar) — önemli
(v2 seti için sembol listesi §12-A'dadır; ilk kurulumda doğrudan oradaki listeyi kullanın.)
Stratejilerin gösterge ısınması için uzun geçmiş gerekir; Binance TradFi geçmişi kısadır (2026'dan). Bu yüzden kendi
bilgisayarınızdaki `veri/mumlar` klasöründen YALNIZ gerekli sembolleri kopyalayın (yaklaşık 600 MB'ın küçük bir kısmı):
```bash
# kendi bilgisayarınızdan (root ile: /var/lib root'a aittir, l3a orada dizin AÇAMAZ):
ssh root@SUNUCU "install -d -o l3a -g l3a /var/lib/1l3a-paper /var/lib/1l3a-paper/veri /var/lib/1l3a-paper/veri/mumlar"
rsync -av veri/mumlar/{BTCUSDT,ETHUSDT,SOLUSDT,DK_AAPL,DK_MSFT,DK_GOOGL,DK_AMZN,DK_NVDA,DK_META,DK_TSLA,DK_XAU,DK_WTI,DK_COPPER} \
      root@SUNUCU:/var/lib/1l3a-paper/veri/mumlar/
ssh root@SUNUCU "chown -R l3a:l3a /var/lib/1l3a-paper"          # rsync root ile kopyaladı: sahipliği l3a'ya ver
```
Tohum eksik sembolün geçmişi yalnız REST'ten alınır (kısa); uzun geçmişli stratejiler için bu bir **uyarıdır** (loga yazılır).
S&P 500 (kıyas çizgisi) için `DK_SPX` de kopyalayın (yukarıdaki rsync listesine `DK_SPX` ekleyin); günlük güncellemeyi 4b yapar.
Not: tohum Dukascopy (DK_) verisidir, canlı devamı Binance TradFi perp mumlarıdır (seans süzgeciyle); fiyat farkı küçük ama sıfır değildir.

## 4. Servisler
```bash
cd /opt/1l3a
cp deploy/1l3a-paper.service deploy/1l3a-pano.service deploy/1l3a-pano.timer deploy/1l3a-pano-sunucu.service /etc/systemd/system/
cp deploy/1l3a-paper.env.ornek /etc/1l3a-paper.env && chmod 600 /etc/1l3a-paper.env
nano /etc/1l3a-paper.env          # Telegram token/chat_id (isteğe bağlı; boşsa Telegram kapalı kalır, motor çalışır)
systemctl daemon-reload
systemctl enable --now 1l3a-paper.service                  # önce motor: durum dosyalarını o yazar
sleep 60 && ls /var/lib/1l3a-paper/durum/                 # ozet.json vb. görünmeli (ilk açılış bir-iki dakika sürebilir)
systemctl enable --now 1l3a-pano.timer 1l3a-pano-sunucu.service
```
`1l3a-pano-sunucu` durum dizinini kendisi de oluşturur (systemd `StateDirectory`), yani sıra karışsa da başlar; motor dosyaları
yazana kadar sayfada dosya listesi/404 görürsünüz. Takıldıysa: `systemctl reset-failed 1l3a-pano-sunucu && systemctl restart 1l3a-pano-sunucu`.
İlk açılışta motor: exchangeInfo'yu okur (tick/step/minNotional), TradFi sembol eşlemesini doğrular (bulamadığı sembolü kullanan
stratejiyi "VERİ YOK" işaretler, uydurmaz), tohum + REST ile geçmişi kurar ve her stratejinin son kapanmış mumundan başlar.

## 4b. Günlük S&P 500 (DK_SPX) güncellemesi
Pano kıyası S&P 500 serisini `/var/lib/1l3a-paper/veri/mumlar/DK_SPX/1h.parquet`'ten okur (paper motoru bu dizini `--tohum` ile alır ve kıyasa da aynısını verir);
son mum 5 günden eskiyse çizgi boş kalır. `1l3a-spx.timer` her gün 22:30 UTC'de (ABD kapanışından sonra) Dukascopy'den eksik günleri indirir
(`python -m motor.canli.spx_guncelle`: son mumun ayından 1 ay öncesinden yarına kadar aylık saatlik dosya, eski geçmiş yeniden indirilmez/yazılmaz; hata olursa servis BAŞARISIZ olur).
```bash
cp deploy/1l3a-spx.service deploy/1l3a-spx.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now 1l3a-spx.timer
```
Tek seferlik tohum — iki yol: (a) adım 3'teki rsync ile `DK_SPX` kopyalayın (önerilen; geçmiş tam gelir); (b) kopyalamazsanız ilk çalıştırmayı elle, başlangıç ayıyla yapın
(arşiv yokken `--baslangic` zorunludur, kendiliğinden tüm geçmişi indirmez):
```bash
sudo -u l3a /opt/1l3a/.venv/bin/python -m motor.canli.spx_guncelle --veri /var/lib/1l3a-paper/veri/mumlar --baslangic 2026-01
```
Kontrol: `systemctl list-timers | grep 1l3a-spx`, `journalctl -u 1l3a-spx -n 20 --no-pager` ("DK_SPX: ... -> <bugün>" satırı). Bu araç yalnız sunucu paper/kıyas dizinine yazar; depo içi araştırma `veri/mumlar` dizinini reddeder (kilit kuralı).
Not: kıyasın sunucuda doğru dizini okuması için `motor/canli/paper.py` güncel olmalı (önceden kıyas `/opt/1l3a/veri/mumlar`'a bakıyordu).

## 4c. Hata bildirimi (servis durursa Telegram)
Paper motoru beklenmeyen hatayı loga ve Telegram'a yazar; aynı hata art arda 5 kez olursa kontrollü durur. systemd artan aralıklarla
yeniden başlatır; denemeler tükenirse `1l3a-bildirim@` birimi Telegram'a "Servis durdu" gönderir (token yalnız /etc/1l3a-paper.env'den).
```bash
cp /opt/1l3a/deploy/1l3a-paper.service /opt/1l3a/deploy/1l3a-bildirim@.service /etc/systemd/system/
systemctl daemon-reload
systemctl start 1l3a-bildirim@deneme.service      # Telegram'a deneme mesajı gelmeli
systemctl restart 1l3a-paper
# servis 'failed' kalırsa sorunu düzeltip:
systemctl reset-failed 1l3a-paper && systemctl restart 1l3a-paper
```

## 5. Ağ kontrolü (kurulumdan sonra bir kez)
```bash
curl -s https://fapi.binance.com/fapi/v1/ping        # {} dönmeli (451 dönerse bu sunucu konumu Binance vadeliye kapalı)
journalctl -u 1l3a-paper -n 50 --no-pager
```

## 6. Günlük işler
| İş | Komut |
|---|---|
| Canlı log | `journalctl -u 1l3a-paper -f` |
| Son 200 satır | `journalctl -u 1l3a-paper -n 200 --no-pager` |
| Durum | `systemctl status 1l3a-paper` |
| Yeniden başlat | `systemctl restart 1l3a-paper` (durum diskte; kaçan mumlar REST'ten tamamlanır) |
| Durdur | `systemctl stop 1l3a-paper` |
| Pano | bilgisayarınızda `ssh -L 8080:127.0.0.1:8080 l3a@SUNUCU` (l3a anahtarı §1'de eklendi; eklemediyseniz önce onu yapın), sonra tarayıcıda `http://localhost:8080/pano.html` |
| Pano üretimi durumu | `systemctl status 1l3a-pano` — "failed" (çıkış kodu 1) = durum dosyaları eksik/bozuk (motor yazmıyor olabilir); kod 2 (kritik uyarı) başarı sayılır, uyarı panoda yazılıdır |
| Durum dosyaları | `/var/lib/1l3a-paper/durum/` (ozet.json, stratejiler.json, islemler.jsonl, saglik.json, olaylar.jsonl, ...) |
| Motor hafızası | `/var/lib/1l3a-paper/durum/paper_state.json` (silerseniz paper SIFIRDAN başlar!) |

Pano her 5 dakikada `1l3a-pano.timer` ile yeniden üretilir (`systemctl list-timers | grep 1l3a`).
Pano hesap yapmaz; motorun yazdığı dosyaları gösterir. Dosya `yazildi_zaman`ı 15 dk'dan eskiyse "VERİ BAYAT / motor durmuş olabilir" der.

## 7. Telegram
`/etc/1l3a-paper.env` içine `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` yazın, `systemctl restart 1l3a-paper`. Gelenler: işlem kapanışı,
günlük limit / kill switch, bağlantı olayları, her gün 00:10 TSİ'de dünün (TSİ) tam gün özeti (yeniden başlatmada tekrar gitmez), motor hatası ve servis durması. Anahtar yoksa hiçbir şey gönderilmez ve logda
"Telegram devre dışı" yazar. Anahtarı **asla** depoya koymayın.

## 8. Ayar yenileme (otomatik DEĞİL)
`sonuclar/final/guncel_ayarlar.csv` içindeki `sonraki_yenileme` tarihi gelince motor panoya/Telegram'a "AYAR YENİLEME ZAMANI" uyarısı yazar.
Motor kendi ayarını DEĞİŞTİRMEZ. Yenilemek için (kendi bilgisayarınızda, güncel veriyle):
```bash
python -m motor.arastirma.guncel_ayar        # sonuclar/final/guncel_ayarlar.csv'yi yeniler
```
Sonucu inceleyip onaylarsanız csv'yi sunucuya alın ve `python -m motor.canli.paper --canli --ayar-guncelle` ile BİR KEZ başlatın
(servis dosyasına `--ayar-guncelle` eklemek yerine geçici olarak elle çalıştırmanız önerilir). Onaysız yeni ayar uygulanmaz:
kayıtlı ayarlar csv'den farklıysa motor açık hata verip başlamaz.

## 9. Geçmişi "canlıymış gibi" tekrar etme ve backtest eşleşme testi (kendi bilgisayarınızda, yerel veriyle)
```bash
python -m motor.canli.paper --tekrar 2025-11-01 2025-12-01 --ayar kilit --durum /tmp/tekrar   # durum dosyaları + pano için
python -m motor.canli.paper_esleme --gun 90                                                    # paper ↔ backtest karşılaştırması
python -m pytest testler/test_paper_*.py                                                       # testler (ağ gerektirmez)
PAPER_AG_TESTI=1 python -m pytest testler/test_paper_veri.py -k gercek_ag                      # isteğe bağlı gerçek ağ testi
```

## 10. Sorun giderme
- `451` / "restricted location": sunucu konumu Binance vadeliye kapalı; başka bölge deneyin.
- `418` / `429`: istek sınırı; motor `Retry-After` kadar bekler. 418 (IP yasağı) olursa motor durur ve loga yazar; bekleyin.
- "kayıtlı durumun ayarları ... farklı": 8. bölüme bakın.
- Pano kırmızı "VERİ BAYAT": önce `systemctl status 1l3a-paper`; hisse/emtia hafta sonu ve tatilde bayat sayılmaz (seans takvimi).

## 11. Panoyu telefondan görmek (Cloudflare Workers, 15 dakikada bir)
Sunucu `pano.html`'i her 15 dakikada Cloudflare'e yükler; sayfa `https://1l3a-pano.<hesabınız>.workers.dev` adresinde açılır
(adresi bilen herkes görebilir; içerik yalnız paper sonuçlarıdır, anahtar/gizli bilgi içermez).
```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt install -y nodejs && npm install -g wrangler@4.158.0
cp deploy/1l3a-pano.env.ornek /etc/1l3a-pano.env && chmod 600 /etc/1l3a-pano.env && nano /etc/1l3a-pano.env
cp deploy/1l3a-pano-yayin.service deploy/1l3a-pano-yayin.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now 1l3a-pano-yayin.timer && systemctl start 1l3a-pano-yayin.service
journalctl -u 1l3a-pano-yayin -n 20 --no-pager        # "pano yayımlandı" ve workers.dev adresi görünmeli
```

## 12. v2 paper setine geçiş (eski 7'li deneme sürüşünden 10'lu v2 setine)
Yeni set: 10 strateji, **her biri kendi 10.000 USD sanal kasasında** (`stratejiler/paper_v2_seti.json`). Eski 7'li deneme sürüşünün durumu
**silinmez**, kenara alınır; yeni set temiz başlar. Eski durumu yeni sete yüklemeye çalışırsanız motor açık hata verip başlamaz (güvenlik).
Her adımı sırayla, kopyala-yapıştır yapın.

**A. Kendi bilgisayarınızda — yeni semboller için tohum veriyi sunucuya gönderin** (yaklaşık 520 MB; var olanlar yeniden gönderilmez):
```bash
cd <proje klasörünüz>
rsync -av veri/mumlar/{BTCUSDT,ETHUSDT,BNBUSDT,XRPUSDT,SOLUSDT,TRXUSDT,ZECUSDT,HYPEUSDT,DOGEUSDT,LINKUSDT,ADAUSDT,XLMUSDT,BCHUSDT} \
      root@SUNUCU:/var/lib/1l3a-paper/veri/mumlar/
rsync -av veri/mumlar/{DK_AAPL,DK_NVDA,DK_MSFT,DK_GOOGL,DK_AMZN,DK_META,DK_TSLA,DK_AVGO,DK_LLY,DK_WMT,DK_JPM,DK_V,DK_MU,DK_AMD,DK_XOM,DK_JNJ,DK_MA,DK_XAU,DK_XAG,DK_WTI,DK_COPPER,DK_NATGAS,DK_SPX} \
      root@SUNUCU:/var/lib/1l3a-paper/veri/mumlar/
ssh root@SUNUCU "chown -R l3a:l3a /var/lib/1l3a-paper"
```
**B. Sunucuda (root olarak):**
```bash
systemctl stop 1l3a-paper
cd /var/lib/1l3a-paper
mv durum durum_eski_7li_$(date +%Y%m%d)          # SİLMİYORUZ, yalnız kenara alıyoruz
cd /opt/1l3a
sudo -u l3a git pull
sudo -u l3a .venv/bin/pip install -r requirements.txt
systemctl daemon-reload
systemctl start 1l3a-paper
```
**C. Kontrol** (ilk açılış 3-5 dakika sürebilir: 35 sembolün geçmişini kurar):
```bash
journalctl -u 1l3a-paper -n 60 --no-pager        # hata yok; "Paper başlatıldı" yazmalı
ls /var/lib/1l3a-paper/durum/hesaplar | wc -l    # 10 yazmalı (her strateji için bir klasör)
ls /var/lib/1l3a-paper/durum_eski_7li_*          # eski durum duruyor mu (paper_state.json görünmeli)
```
Beklenen, **normal** uyarılar: `DK_JNJ` ve `DK_MA` için "Binance karşılığı yok": bu iki hisse evrenden düşer, strateji kalan sembollerle çalışır
(panoda ve `saglik.json` uyarılarında görünür). Pano "Backtest bütünlüğü: maliyet_modeli kayıtlı sha256 ile uyuşmuyor" uyarısı verirse bu
beklenir (kayıt eski sete aitti); yenilemek sizin onayınızla `python -m motor.canli.guven --kaydet` ile yapılır, motor kendiliğinden yazmaz.
Pano: her stratejinin yanında **doğrulandı** (resmi holdout kapısını geçti) ya da **iyi göründü** (sonuç sonrası keşif, kanıt değil) etiketi ve
"Kasa" satırı (o stratejinin kendi sanal hesabı) görünür. Üst düzey sayılar 10 kasanın TOPLAMIDIR; sert limitler her kasada ayrı uygulanır.
Her kasanın tam dosyaları `durum/hesaplar/<strateji>/` altındadır.

**Hata mesajları:**
- `bu durum dosyası v2 paper setine ait değil`: eski durum dizini hâlâ yerinde. B adımındaki `mv durum ...` satırını yapın, tekrar `systemctl start 1l3a-paper`.
- `paper v2 seti BAŞLAMAZ: ... çıkış ayarlarını kullanıyor`: bir strateji paper'ın uygulamadığı çıkış ayarı taşıyor (bilerek durur; kodda düzeltilmeden başlamaz).
- `kayıtlı set imzası ... şimdiki ...`: set dosyası (strateji/etiket/s) kayıttan sonra değişmiş. Bilinçli değişiklikse durumu kenara alıp temiz başlayın.

**Geri dönüş (gerekirse):** `systemctl stop 1l3a-paper; cd /var/lib/1l3a-paper; mv durum durum_v2_deneme; mv durum_eski_7li_* durum`, sonra
`/etc/systemd/system/1l3a-paper.service` içindeki `ExecStart` satırının sonuna `--set eski` ekleyip `systemctl daemon-reload && systemctl start 1l3a-paper`.

## 13. Canlı (gerçek emirli) yürütücü — küçük bütçe
> **Uyarı:** Bu bölüm GERÇEK PARA ile ilgilidir. Önce **kuru**, sonra **testnet**, ancak ikisi de günlerce sorunsuz çalıştıktan sonra **canlı**.
> **1L3A v2 planı (2026-11-11, `sonuclar/canli/CANLI_PLAN_V2.md`):** testnet'te YALNIZ e0v1en (testnet tek hesap = tek strateji;
> `/etc/1l3a-canli.json` içinden ewo satırını silin). Gerçek parada önce duman: e0v1en ve ewo, her biri kendi alt hesabında 60 USD,
> `islem_risk` 0.015 sabit; alt hesapta 60 USD'den fazla para tutmayın.
>
> Paper servisi (`1l3a-paper`) aynen çalışmaya devam eder; canlı yürütücü ayrı bir servistir (`1l3a-canli`) ve ayrı durum dizini kullanır.

**Mantık (sade):** canlı servis, paper motoruyla AYNI sinyalleri üretir; sanal dolum yerine Binance'e gerçek emir verir. Her girişten hemen
sonra Binance'in kendi sunucusunda bir **stop emri** durur (sunucumuz kapansa bile korur). Stop kurulamazsa pozisyon hemen kapatılır.
**Bir Binance hesabı = bir strateji.** Alt hesabınız (sub-account) varsa her canlı strateji kendi alt hesabının anahtarını kullanır;
yoksa yalnız bir strateji canlı çalışır. **Canlı risk kuralı (kullanıcı kararı 2026-11-11; yalnız canlı yürütücü için — paper/backtest eski sert limitlerle AYNEN devam eder).**
Tek kaynak: `motor/canli/borsa/canli_limitler.py` (`CANLI_LIMITLER`); kodla zorlanır, strateji ya da ajan aşamaz. "Kasa" = her strateji hesabında
`min(borsadaki özsermaye, o stratejiye ayırdığınız tahsis_usd)`.

| Kural | Değer |
|---|---|
| İşlem başı stopta kayıp (komisyon + stop kayması dahil) | kasanın en fazla %3'ü |
| İşlem başı marj / nominal | kasanın en fazla %50'si / en fazla 1.5 katı |
| Miktar | `min(1.5·kasa/fiyat, 0.03·kasa/(stop mesafesi + birim maliyet))`, borsanın adımına **aşağı** yuvarlanır |
| Borsa minimumunun altında kalırsa | işlem **atlanır** (asla yukarı yuvarlanmaz), Telegram'a `min_tutar_alti` |
| Tüm açık pozisyonların toplam stop riski / brüt nominal | kasanın en fazla %6'sı / 1.5 katı |
| Günlük kayıp | UTC günü içinde gün başı kasadan -%6: ertesi UTC gününe kadar **yeni giriş yok**; açık pozisyonlar KAPATILMAZ (borsa stopu ve stratejinin kendi çıkışı sürer) |
| Strateji kill | kasa zirveden -%30: hepsi kapatılır, strateji KALICI durur (yeniden başlatma kaldırmaz) |
| Hesap kill | TÜM canlı stratejilerin kasa toplamı ortak zirveden -%20: tüm stratejiler kapatılır ve KALICI durur |
| Marj / kaldıraç | izole marj; stop mesafesi <= %15 ise 3x, > %15 ise 2x (girişten önce sembole ayarlanır). 2x'te nominal tavanı fiilen 1.0x kasa (marj %50 sınırı) |
| Stop mesafesi > %25 | işlem atlanır |

Girişten sonra gerçek dolum fiyatıyla kural yeniden kontrol edilir; aşılmışsa pozisyon küçültülür (sığmazsa kapatılır).
Küçük kasada (ör. 165 USD) BTC (min 100 USD) ve ETH (min ~20 USD) gibi sembollerde işlem sık sık `min_tutar_alti` ile atlanabilir: bu beklenen ve güvenlidir.
Şimdilik **yalnız tek-grafik (sinyal) stratejileri** canlıya alınabilir: portföy (`pf__...`) stratejileri ve kısmi çıkışlı stratejiler açık hatayla reddedilir.
Geçmiş verideki "yeniden oynatma" sonucu: `sonuclar/canli/BOYUT_RAPORU.md` (geçmiş; gelecek tahmini DEĞİL).

**A. Binance API anahtarı (her strateji/hesap için ayrı):**
1. Binance → API Yönetimi → yeni anahtar. İzinler: **yalnız "Enable Reading" ve "Enable Futures"**. **"Enable Withdrawals" KAPALI kalmalı**
   (hiçbir koşulda açmayın), "Enable Spot & Margin Trading" da gerekmez, kapalı bırakın.
2. **IP kısıtlaması:** "Restrict access to trusted IPs only" seçin ve yalnız **sunucunun IP adresini** ekleyin.
3. Önce **testnet** için ayrı anahtar alın (https://testnet.binancefuture.com, GitHub ile giriş; sahte para). Gerçek anahtarla karıştırmayın.
4. Anahtarı ve gizli değeri **sohbete, e-postaya, depoya yazmayın**; yalnız aşağıdaki sunucu dosyasına koyun.

**B. Sunucuda dosyalar (root olarak):**
```bash
cd /opt/1l3a && sudo -u l3a git pull
cp deploy/1l3a-canli.service /etc/systemd/system/
cp deploy/1l3a-canli.env.ornek /etc/1l3a-canli.env
chown root:root /etc/1l3a-canli.env && chmod 600 /etc/1l3a-canli.env     # yalnız root okuyabilir
nano /etc/1l3a-canli.env          # BINANCE_API_KEY_S1= ve BINANCE_API_SECRET_S1= satırlarını doldurun. CANLI_ONAY BOŞ kalsın (testnet).
cp stratejiler/canli_ayar.ornek.json /etc/1l3a-canli.json
nano /etc/1l3a-canli.json         # "id": canlıya alınacak stratejinin kimliği (paper_v2_seti.json'daki "strateji"), "tahsis_usd": ayırdığınız tutar
# paper'ın tohum verisini canlıya kopyalayın (iki servis aynı veri dizinine yazmasın)
install -d -o l3a -g l3a /var/lib/1l3a-canli/veri && cp -a /var/lib/1l3a-paper/veri/mumlar /var/lib/1l3a-canli/veri/ && chown -R l3a:l3a /var/lib/1l3a-canli
systemctl daemon-reload
```
**C. Kuru çalıştırma (hiçbir emir gitmez, anahtar gerekmez):** `/etc/1l3a-canli.json` içinde `"mod": "kuru"` yapıp
`systemctl start 1l3a-canli; journalctl -u 1l3a-canli -f` ile "KURU piyasa ..." satırlarına bakın. Beklenen emirler paper işlemleriyle uyumlu olmalı.

**D. Testnet (sahte para, gerçek emir akışı):** `"mod": "testnet"` (varsayılan) yapın, testnet anahtarlarını `/etc/1l3a-canli.env`'e koyun,
`systemctl restart 1l3a-canli`. Telegram'da "canli_emir_doldu" ve "canli_stop_kuruldu" mesajlarını görmelisiniz; Binance testnet arayüzünde
pozisyonun yanında stop emrini kontrol edin. **Koşullu emir uçları (algo) ilk kez testnet'te doğrulanır**; hata alırsanız `"kosullu_modu": "klasik"` deneyin ve bana bildirin.
Servisi bir kez `systemctl restart` edin: mevcut pozisyon/stop'lar çift emir üretmeden devralınmalı.
Adım adım kontrol listesi (kuru, testnet, nadir yollar, kayıt dosyaları, 60 USD duman): [sonuclar/canli/TESTNET_KONTROL.md](../sonuclar/canli/TESTNET_KONTROL.md).

**E. Canlıya geçiş (yalnız testnet temiz çalıştıktan sonra, bilerek):**
```bash
nano /etc/1l3a-canli.env     # GERÇEK anahtarlar + en alta  CANLI_ONAY=evet
nano /etc/1l3a-canli.json    # "mod": "canli"
systemctl restart 1l3a-canli && journalctl -u 1l3a-canli -n 40 --no-pager
```
`CANLI_ONAY=evet` yoksa servis "GERÇEK PARA ile başlatma reddedildi" diyerek **başlamaz** (bu bir güvenlik özelliğidir).

**Kill switch ve acil durdurma:** günlük kasa kaybı -%6 olursa yürütücü ertesi UTC gününe kadar yeni giriş yapmaz (açık pozisyonları kapatmaz; stoplar ve strateji çıkışları sürer).
Strateji kasası zirveden -%30 düşerse (strateji kill) ya da tüm canlı stratejilerin kasa toplamı ortak zirveden -%20 düşerse (hesap kill) tüm pozisyonlar
ÖNCE kapatılır, kapanış borsada doğrulanınca emirler iptal edilir ve yeni giriş yapılmaz. İkisi de KALICIDIR: strateji için
`/var/lib/1l3a-canli/durum/canli/yurutucu_*.json` içindeki `"kill": true`, hesap için `/var/lib/1l3a-canli/durum/canli/hesap_durumu.json` içindeki `"kill": true`
satırını yalnız nedenini anladıktan sonra elle `false` yapın (hesap kill'i kaldırırken stratejilerinkini de kaldırın; hesap zirvesi `"zirve": null` ile yeniden başlar). Elle durdurma: `systemctl stop 1l3a-canli` (borsadaki stop emirleri yerinde kalır, pozisyonlar korunur).
Tanımadığı bir pozisyon görürse yürütücü **dokunmaz**, yalnız Telegram'a "BİLİNMEYEN pozisyon" yazar.

**F. Kayıt dosyaları ve haftalık rapor (salt okunur araç; borsaya bağlanmaz).** Yürütücü işlem mantığına dokunmadan, `/var/lib/1l3a-canli/durum/canli/` altına append-only yazar:
`islemler.jsonl` (kapanan her gerçek işlem: dolum fiyatı, komisyon, funding, net PnL, R, çıkış nedeni, maliyet bps), `ozsermaye_gunluk.jsonl` (servis başı ve her UTC günü
strateji özsermaye/tahsis/kasa + hesap toplamı ve zirve; tahsis değişimi `sermaye_hareketi` satırı olarak ayrı), `olaylar_arsiv.jsonl` (her olay: dolan/atlanan sinyal ve neden).
Kayıt yazılamazsa işlem durmaz; Telegram'a "canli_kayit_hatasi" gelir. Haftalık rapor (sunucuda tek komut; `--yaz-karsilastirma` risk adımı kontrolünün okuduğu `haftalik_karsilastirma.json`'u da üretir):
```bash
cd /opt/1l3a && sudo -u l3a .venv/bin/python -m araclar.canli_haftalik_rapor --canli-durum /var/lib/1l3a-canli/durum --paper-durum /var/lib/1l3a-paper/durum \
  --ayar /etc/1l3a-canli.json --baslangic 2026-12-15 --sunucu-gider-usd-ay 6 --yaz-karsilastirma --cikti /var/lib/1l3a-canli/rapor/haftalik_$(date +%F).md
```
Çıktı: aynı adla `.md` (sade Türkçe) ve `.json`. Risk adımı şartlarına bakmak için: `python -m motor.canli.borsa.risk_adim_kontrol --durum /var/lib/1l3a-canli/durum`.
