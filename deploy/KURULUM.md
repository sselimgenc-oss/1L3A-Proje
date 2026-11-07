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
```

## 2. Kod ve sanal ortam
```bash
sudo -u l3a git clone <DEPO_ADRESI> /opt/1l3a        # ya da: rsync ile kendi bilgisayarınızdan
cd /opt/1l3a
sudo -u l3a python3 -m venv .venv
sudo -u l3a .venv/bin/pip install -r requirements.txt
```

## 3. Tohum veri (geçmiş mumlar) — önemli
Stratejilerin gösterge ısınması için uzun geçmiş gerekir; Binance TradFi geçmişi kısadır (2026'dan). Bu yüzden kendi
bilgisayarınızdaki `veri/mumlar` klasöründen YALNIZ gerekli sembolleri kopyalayın (yaklaşık 600 MB'ın küçük bir kısmı):
```bash
# kendi bilgisayarınızdan:
ssh l3a@SUNUCU "mkdir -p /var/lib/1l3a-paper/veri/mumlar"        # servis ilk açılışta oluşturur; elle de açılabilir
rsync -av veri/mumlar/{BTCUSDT,ETHUSDT,SOLUSDT,DK_AAPL,DK_MSFT,DK_GOOGL,DK_AMZN,DK_NVDA,DK_META,DK_TSLA,DK_XAU,DK_WTI,DK_COPPER} \
      root@SUNUCU:/var/lib/1l3a-paper/veri/mumlar/
ssh root@SUNUCU "chown -R l3a:l3a /var/lib/1l3a-paper"
```
Tohum eksik sembolün geçmişi yalnız REST'ten alınır (kısa); uzun geçmişli stratejiler için bu bir **uyarıdır** (loga yazılır).
Not: tohum Dukascopy (DK_) verisidir, canlı devamı Binance TradFi perp mumlarıdır (seans süzgeciyle); fiyat farkı küçük ama sıfır değildir.

## 4. Servisler
```bash
cd /opt/1l3a
cp deploy/1l3a-paper.service deploy/1l3a-pano.service deploy/1l3a-pano.timer deploy/1l3a-pano-sunucu.service /etc/systemd/system/
cp deploy/1l3a-paper.env.ornek /etc/1l3a-paper.env && chmod 600 /etc/1l3a-paper.env
nano /etc/1l3a-paper.env          # Telegram token/chat_id (isteğe bağlı; boşsa Telegram kapalı kalır, motor çalışır)
systemctl daemon-reload
systemctl enable --now 1l3a-paper.service 1l3a-pano.timer 1l3a-pano-sunucu.service
```
İlk açılışta motor: exchangeInfo'yu okur (tick/step/minNotional), TradFi sembol eşlemesini doğrular (bulamadığı sembolü kullanan
stratejiyi "VERİ YOK" işaretler, uydurmaz), tohum + REST ile geçmişi kurar ve her stratejinin son kapanmış mumundan başlar.

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
| Pano | bilgisayarınızda `ssh -L 8080:127.0.0.1:8080 l3a@SUNUCU`, sonra tarayıcıda `http://localhost:8080/pano.html` |
| Durum dosyaları | `/var/lib/1l3a-paper/durum/` (ozet.json, stratejiler.json, islemler.jsonl, saglik.json, olaylar.jsonl, ...) |
| Motor hafızası | `/var/lib/1l3a-paper/durum/paper_state.json` (silerseniz paper SIFIRDAN başlar!) |

Pano her 5 dakikada `1l3a-pano.timer` ile yeniden üretilir (`systemctl list-timers | grep 1l3a`).
Pano hesap yapmaz; motorun yazdığı dosyaları gösterir. Dosya `yazildi_zaman`ı 15 dk'dan eskiyse "VERİ BAYAT / motor durmuş olabilir" der.

## 7. Telegram
`/etc/1l3a-paper.env` içine `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` yazın, `systemctl restart 1l3a-paper`. Gelenler: işlem kapanışı,
günlük limit / kill switch, bağlantı olayları, her gün 00:10 UTC özeti. Anahtar yoksa hiçbir şey gönderilmez ve logda
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
