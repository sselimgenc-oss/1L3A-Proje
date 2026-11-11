# Testnet ve duman kontrol listesi (Faz 1 + Faz 2)

Kaynak: `CANLI_PLAN_V2.md` §7 (Faz 1 ve Faz 2), `deploy/KURULUM.md` §13, `motor/canli/borsa/` kodu.
Bu dosya bir **kontrol listesidir**: her maddeyi yapın, sonucu gördüyseniz kutuyu işaretleyin (☐ → ☒). Görmediyseniz **geçmedi** sayılır.
Yazılan her komut, dosya yolu ve olay adı koddan/KURULUM'dan alınmıştır. Koddan kesin çıkarılamayan noktalar **⚠ doğrulanmadı** ile işaretlidir:
bunları denerken sonucu bana bildirin, listeyi birlikte güncelleriz.

**Genel kurallar**
- Komutların hepsi DigitalOcean web konsolunda **root** olarak çalıştırılır. Her komut ayrı kutudadır: kutuyu kopyalayın, konsola yapıştırın, Enter.
- `nano` dosyasını kaydetmek: `Ctrl+O`, Enter; çıkmak: `Ctrl+X`. Bu dosyada nano yerine mümkün olduğunca tek komutla dosya yazan bloklar kullanıldı.
- **Anahtar (API key/secret) yalnız `/etc/1l3a-canli.env` dosyasına yazılır.** Sohbete, e-postaya, ekran görüntüsüne, depoya asla.
- Paper servisi (`1l3a-paper`) hiçbir adımda durdurulmaz ya da değiştirilmez.
- Servis adı: `1l3a-canli`. Kod: `/opt/1l3a`. Durum dizini: `/var/lib/1l3a-canli/durum`. Kayıt dosyaları: `/var/lib/1l3a-canli/durum/canli/`.
- Bir adımda beklenmeyen bir şey görürseniz **durun**, ekrandaki satırı (anahtarsız) bana yapıştırın; sonraki adıma geçmeyin.

**Telegram'da göreceğiniz mesajın biçimi** (kodda tek biçim): `🔴 1L3A CANLI (testnet) · dis__e0v1en` ve altında kalın olay adı + açıklama.
Paper'ın kendi mesajları bu serviste susturulur; yalnız bu 🔴 mesajlar gelir. Parantez içi `(kuru)`, `(testnet)` ya da `(canli)` modu gösterir.

**Kodda geçen gerçek olay adları (Telegram'da kalın yazılan)**

| Olay | Anlamı |
|---|---|
| `canli_emir_doldu` | Giriş piyasa emri doldu |
| `canli_stop_kuruldu` | Borsada STOP_MARKET (reduceOnly) kuruldu (yükseltmede de aynı ad) |
| `canli_kapandi` | Yürütücü pozisyonu piyasa emriyle kapattı; sonunda parantez içinde neden yazar |
| `canli_giris_atlandi` | Sinyal var ama girilmedi (neden yazar) |
| `min_tutar_alti` | Hesaplanan miktar borsa minimumunun altında: atlandı (60 USD kasada sık görülür, normal) |
| `canli_uyusmazlik` | Mutabakat: borsa ile kayıt farklı (bazıları normal, aşağıda ayrıldı) |
| `canli_stop_basarisiz` | Stop kurulamadı → pozisyon hemen kapatılır |
| `canli_stop_hatasi` | Stop yükseltilemedi, eski stop yerinde |
| `canli_kapatma_hatasi`, `canli_iptal_hatasi` | Kapatma/iptal emri başarısız (tekrar denenir) |
| `canli_giris_hatasi`, `canli_giris_belirsiz`, `canli_giris_blok` | Giriş reddi / sonucu belirsiz / art arda 3 hatada girişin bloklanması |
| `canli_risk_asimi` | Gerçek dolumla sert limit aşıldı, pozisyon küçültüldü/kapatıldı |
| `canli_hedef_hatasi` | Hedef (TAKE_PROFIT) emri kurulamadı; stop var, pozisyon korunur |
| `canli_kill_switch` | Günlük −%6 limiti, strateji kill ya da hesap kill |
| `canli_kill_hatasi` | Kill sırasında pozisyon kapatılamadı |
| `canli_yurutucu_hatasi` | Yürütücü turunda beklenmeyen hata |
| `canli_kayit_hatasi` | Kayıt dosyası yazılamadı (işlem sürer) |

---

## A. Ön şartlar

- ☐ **A1. Sunucuda kod güncel** ve paper servisi çalışıyor.
```bash
cd /opt/1l3a && sudo -u l3a git pull && systemctl is-active 1l3a-paper
```
Görülmeli: `active`. (Bu dal henüz ana dala girmediyse `git pull` yeni dosyaları getirmez: önce bana sorun.)

- ☐ **A2. Testnet API anahtarı alındı.** https://testnet.binancefuture.com → GitHub ile giriş → sayfanın altındaki "API Key" sekmesi → anahtar oluştur.
  Bu **sahte para** hesabıdır, gerçek Binance hesabınızdan ayrıdır. Gerçek anahtarla karıştırmayın.
  ⚠ doğrulanmadı: testnet sitesinin ekran düzeni zamanla değişiyor; menü adları farklı olabilir. Testnet hesabında varsayılan sahte USDT bakiyesi (genelde büyük bir sayı) vardır;
  bizim kasa `tahsis_usd` ile 60 USD'ye sınırlanır, yani bakiyenin büyüklüğü botu etkilemez.

- ☐ **A3. Anahtarlar yalnız `/etc/1l3a-canli.env` içinde.** Dosyayı açın ve şu satırları doldurun (başka hiçbir yere yazmayın):
```bash
nano /etc/1l3a-canli.env
```
  Doldurulacaklar: `BINANCE_API_KEY_S1=` ve `BINANCE_API_SECRET_S1=` (testnet anahtarı), ayrıca Telegram için `TELEGRAM_BOT_TOKEN=` ve `TELEGRAM_CHAT_ID=`
  (paper'daki ile aynı bot olabilir; değerleri `/etc/1l3a-paper.env`'den kopyalayın, sohbete yazmayın). **`CANLI_ONAY=` BOŞ kalmalı.**
  Dosya yoksa önce KURULUM §13 B adımlarını yapın. İzin kontrolü:
```bash
ls -l /etc/1l3a-canli.env
```
  Görülmeli: `-rw-------  1 root root` (yalnız root okur). Farklıysa: `chown root:root /etc/1l3a-canli.env && chmod 600 /etc/1l3a-canli.env`.
  Değerleri ekrana yazdırmadan dolu olup olmadığını görmek için:
```bash
grep -c '=.' /etc/1l3a-canli.env
```
  Görülmeli: 5 ya da daha büyük bir sayı (KEY, SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID dolu; `CANLI_ONAY` boş olduğu için sayılmaz; yorum satırları `#` ile başlayıp `=` içerdiği için sayıyı büyütebilir, bu yüzden bu sayı yalnız kaba kontroldür).

- ☐ **A4. `/etc/1l3a-canli.json` yalnız `dis__e0v1en` içerir** (ewo satırı yok; testnet tek hesap = tek strateji). Tüm dosyayı tek komutla yazın (önce kuru modda başlıyoruz):
```bash
cat > /etc/1l3a-canli.json <<'EOF'
{
  "surum": 1,
  "mod": "kuru",
  "working_type": "MARK_PRICE",
  "kosullu_modu": "algo",
  "giris_gecikme_max_sn": 900,
  "hedef_emri": true,
  "stratejiler": [
    {
      "id": "dis__e0v1en",
      "api_key_env": "BINANCE_API_KEY_S1",
      "api_secret_env": "BINANCE_API_SECRET_S1",
      "tahsis_usd": 60,
      "islem_risk": 0.015
    }
  ]
}
EOF
```
  Kontrol: aşağıdaki komut `"mod": "kuru"` ve `"id": "dis__e0v1en"` göstermeli, `ewo` kelimesi OLMAMALI.
```bash
grep -E '"mod"|"id"|ewo' /etc/1l3a-canli.json
```

- ☐ **A5. Mod değerleri** (anlamı; kodda `MODLAR = kuru | testnet | canli`):
  `kuru` = hiçbir emir gitmez, anahtar gerekmez; `testnet` = sahte para, gerçek emir akışı (varsayılan); `canli` = GERÇEK PARA, `CANLI_ONAY=evet` olmadan servis **başlamaz**.
  Mod değiştirmek için (örnek: kuru → testnet) yalnız şu komutu kullanın, sonra kontrol edin:
```bash
sed -i 's/"mod": *"[a-z]*"/"mod": "testnet"/' /etc/1l3a-canli.json && grep '"mod"' /etc/1l3a-canli.json
```
  Başka yazım biçimi kullanmayın; `canli` yazmak yalnız Faz 2'de (bölüm F) yapılır.

- ☐ **A6. Tohum veri dizini var** (KURULUM §13 B'nin son satırı yapıldı mı):
```bash
ls /var/lib/1l3a-canli/veri/mumlar | head -3
```
  Görülmeli: sembol klasörleri (ör. `BTCUSDT`). Boşsa KURULUM §13 B'deki `install -d ... cp -a ...` satırını çalıştırın.

---

## B. Kuru çalıştırma (2–3 gün; hiçbir emir gitmez)

Amaç: servis hatasız dönüyor, sinyaller emre çevriliyor, paper ile aynı şeyi görüyor. **Bu aşamada yeniden başlatma denemeyin** (kuru borsa bellekte yaşar; yeniden başlatınca "borsada pozisyon yok, kayıt temizlendi" görürsünüz, bu kuruya özgüdür ve zararsızdır).

- ☐ **B1. Servisi başlat.**
```bash
systemctl daemon-reload && systemctl start 1l3a-canli
```
```bash
journalctl -u 1l3a-canli -n 60 --no-pager
```
  Görülmeli: `dis__e0v1en: kuru hesabı hazır, özsermaye 60, tahsis 60` ve hata (ERROR/Traceback) yok.
  Görülmemeli: `canlı yürütücü BAŞLAMADI` ya da `borsa bağlantısı kurulamadı`.
```bash
systemctl is-active 1l3a-canli
```
  Görülmeli: `active`.

- ☐ **B2. Servis dönüyor.** Birkaç dakika bekleyip tekrar bakın; servis `active` kalmalı, durum dizini oluşmalı:
```bash
ls /var/lib/1l3a-canli/durum /var/lib/1l3a-canli/durum/canli
```
  Görülmeli: `paper_state.json`, `canli/` altında `yurutucu_<12 harf>.json` ve `ozsermaye_gunluk.jsonl` (servis başı satırı).

- ☐ **B3. Sinyal gelince beklenen log satırları** (15 dakikalık mum kapanışında; sinyal sık olmayabilir, saatlerce hiçbir şey görmemek normaldir). Canlı izlemek için (çıkmak: `Ctrl+C`):
```bash
journalctl -u 1l3a-canli -f
```
  Ya da geçmişe bakmak için:
```bash
journalctl -u 1l3a-canli --since "24 hours ago" --no-pager | grep -E "KURU|canlı olay"
```
  Giriş olduğunda sırayla görülmeli:
  1. `KURU hazırla <SEMBOL> ISOLATED one-way x3` (ya da `x2`)
  2. `KURU piyasa <SEMBOL> BUY <miktar> reduceOnly=False`
  3. `canlı olay canli_emir_doldu [dis__e0v1en]: ... LONG <miktar> @ <fiyat> (stopta kayıp %... kasa, ...)`
  4. `KURU STOP_MARKET <SEMBOL> SELL <miktar> @ <stop> reduceOnly`
  5. `canlı olay canli_stop_kuruldu [dis__e0v1en]: ... STOP_MARKET reduceOnly ...`
  Telegram'da aynı olaylar `(kuru)` etiketiyle gelir: `canli_emir_doldu`, `canli_stop_kuruldu`.
  Küçük kasada BTC/ETH girişlerinin `min_tutar_alti` ile atlanması beklenir.

- ☐ **B4. Çıkış satırları.** Strateji çıkışında: `KURU piyasa <SEMBOL> SELL <miktar> reduceOnly=True` ve `canli_kapandi ... piyasa emriyle kapatıldı (<neden>)`.
  **Kuruya özgü, normal sayılan satır:** kuru borsa fiyatı izleyip stopu kendisi tetiklemez. Paper motoru stopa takılıp pozisyonu kapatırsa canlı servis şunu yazar:
  `canli_uyusmazlik ... paper motoru pozisyonu kapattı ama borsada açık; borsada da kapatılıyor` ardından `canli_kapandi ... (motor_kapali)`. Bu bir hata değildir.

- ☐ **B5. Paper ile eşleşme nasıl kontrol edilir.** Canlı servisin içindeki paper motoru her sinyali "niyet" olarak üretir; yürütücü bunları ya doldurur (`canli_emir_doldu`) ya da bir sebeple atlar. Sayım:
```bash
grep -c '"tur": "canli_emir_doldu"' /var/lib/1l3a-canli/durum/canli/olaylar_arsiv.jsonl
```
```bash
grep -E '"tur": "(canli_giris_atlandi|min_tutar_alti|canli_giris_hatasi|canli_giris_blok)"' /var/lib/1l3a-canli/durum/canli/olaylar_arsiv.jsonl | cut -c1-300
```
  Görülmeli: her atlama satırının nedeni açık (`min_tutar_alti`, `günlük kayıp`, `sinyal barı ... önce kapandı` vb.); nedensiz kaybolan sinyal olmamalı.
  Bağımsız paper servisiyle karşılaştırma (aynı strateji, aynı sinyal zamanı ve sembol): canlı servisin kendi paper işlemleri ve bağımsız paper:
```bash
tail -n 5 /var/lib/1l3a-canli/durum/islemler.jsonl | cut -c1-300
```
```bash
grep e0v1en /var/lib/1l3a-paper/durum/islemler.jsonl | tail -n 5 | cut -c1-300
```
  Görülmeli: aynı sembolde, aynı `giris_zamani` ile aynı işlemler (iki servisin başlangıç tarihi farklı olduğu için yalnız ikisinin de çalıştığı dönem kıyaslanır).
  ⚠ doğrulanmadı: bağımsız paper `islemler.jsonl` içinde strateji kimliğinin `kimlik` alanında hangi biçimde (`dis__e0v1en` ya da kısa ad) yazıldığı; `grep e0v1en` boş dönerse `tail -n 3 /var/lib/1l3a-paper/durum/islemler.jsonl` ile biçime bakıp bana bildirin.
  Hazır özet (haftalık rapordaki "4. Canlı–paper eşleşmesi" bölümü, hedef ≥ %95) bölüm E'de çalıştırılır; kuruda `min_tutar_alti` yüzünden yüzde düşük çıkabilir, nedenleri okuyun.

- ☐ **B6. Kayıt hatası yok.**
```bash
grep -c canli_kayit_hatasi /var/lib/1l3a-canli/durum/canli/olaylar_arsiv.jsonl
```
  Görülmeli: `0`.

- ☐ **B7. En az 2 tam gün, tercihen 3 gün sorunsuz** (servis `active`, `canli_yurutucu_hatasi` yok, restart döngüsü yok):
```bash
journalctl -u 1l3a-canli --since "48 hours ago" --no-pager | grep -E "canli_yurutucu_hatasi|Traceback|ERROR" | head
```
  Görülmeli: çıktı boş. En az bir giriş (B3) görülmediyse kuru süresini uzatın.

**B geçti mi?** ☐ B1–B7 hepsi → testnet'e geçilir. Geçmediyse: bölüm başındaki kayıt satırlarını bana yapıştırın.

---

## C. Testnet temel akış (sahte para, gerçek emirler)

- ☐ **C1. Testnet'e geç.** Servisi durdurun, modu değiştirin, **önce kuru durum kaydını yedekleyin** (kuru pozisyonları testnet'e karışmasın):
```bash
systemctl stop 1l3a-canli
```
```bash
mv /var/lib/1l3a-canli/durum /var/lib/1l3a-canli/durum_kuru_$(date +%Y%m%d)
```
```bash
sed -i 's/"mod": *"[a-z]*"/"mod": "testnet"/' /etc/1l3a-canli.json && grep '"mod"' /etc/1l3a-canli.json
```
```bash
systemctl start 1l3a-canli && sleep 20 && journalctl -u 1l3a-canli -n 40 --no-pager
```
  Görülmeli: `dis__e0v1en: testnet hesabı hazır, özsermaye <testnet bakiyesi>, tahsis 60`. Bu satır anahtarın ve izinlerin doğru olduğunu da kanıtlar.
  Görülmemeli: `API anahtarı/gizli tanımlı değil`, `borsa bağlantısı kurulamadı` (varsa anahtar ya da IP/izin sorunu; anahtarı sohbete yazmadan hata satırını gösterin).
  Not: `durum` dizinini taşımak paper motorunu da sıfırlar (yeni, temiz başlar). Kuru kayıtları `durum_kuru_...` altında durur, silinmez.

- ☐ **C2. Giriş emri doldu.** Sinyali bekleyin (B3'teki gibi `journalctl ... -f`). Görülmeli:
  - Log: `canlı olay canli_emir_doldu [dis__e0v1en]: ... LONG <miktar> @ <fiyat> ...` (`KURU` öneki YOK).
  - Telegram: `🔴 1L3A CANLI (testnet) · dis__e0v1en` + `canli_emir_doldu`.
  - Binance testnet arayüzü → Futures → **Positions**: aynı sembolde pozisyon, **Isolated** marj, kaldıraç 3x (stop mesafesi ≤ %15) ya da 2x.
  Sinyal atlanırsa (`min_tutar_alti`, `canli_giris_atlandi`): normal; sembol testnet'te listelenmiyorsa ya da testnet fiyatı kayma yarattıysa da görülebilir. ⚠ doğrulanmadı: testnet sembol listesi ve fiyatları gerçek piyasadan farklı/eksik olabilir; çok sayıda "sembol bulunamadı" tipi atlama görürseniz bana bildirin.

- ☐ **C3. Borsada stop görünüyor** (algo / koşullu emir). Girişten hemen sonra:
  - Log + Telegram: `canli_stop_kuruldu ... STOP_MARKET reduceOnly <miktar> @ <stop> (MARK_PRICE)`.
  - Binance testnet arayüzü: pozisyon satırı yanında ya da altta **"Open Orders"** sekmesinde, **"Conditional" / "Stop" / algo emirleri** bölümünde `STOP MARKET`, `Reduce Only`, doğru miktar ve tetik fiyatı.
  ⚠ doğrulanmadı: `kosullu_modu: "algo"` uçları (`/fapi/v1/algoOrder`, `openAlgoOrders`, yanıt alanları `algoId`/`algoStatus`) **ilk kez testnet'te sınanıyor** (`binance_futures.py` başlığı). Testnet arayüzünde algo emirlerinin hangi sekmede göründüğü de belirsizdir; hiçbir sekmede göremiyorsanız stop yok sayılmaz, log'daki `canli_stop_kuruldu` ve C3'ün altındaki `canli_stop_basarisiz` olmaması esas alınır, ama bana bildirin.
  **Algo uçları hata verirse** (log'da `reddedildi: HTTP 4xx` ve hemen ardından `canli_stop_basarisiz`, pozisyon kapanır): servisi durdurun, `sed -i 's/"kosullu_modu": *"[a-z]*"/"kosullu_modu": "klasik"/' /etc/1l3a-canli.json`, başlatın, tekrar deneyin ve bana bildirin (KURULUM §13 D).
  Kontrol: `grep kosullu /etc/1l3a-canli.json`.

- ☐ **C4. Stop yükseltme.** Strateji stopu yukarı çekerse (zaman alabilir; her pozisyonda olmayabilir): önce yeni stop kurulur, sonra eskisi iptal edilir.
  Görülmeli: yeni bir `canli_stop_kuruldu ... @ <daha yüksek stop>` ve borsada **tek** aktif stop (eskisi gitmiş). Telegram'da yine `canli_stop_kuruldu`.
  Görülmemeli: `canli_stop_hatasi` ("stop yükseltilemedi"). Çıkarsa eski stop yerinde kalır (güvenli) ama bana bildirin.
  Yükseltme hiç oluşmazsa bu madde **geçmedi** kalır; testnet süresini uzatmak mı yoksa "gözlenmedi, kodla kanıtlı (`test_stop_yukselir_once_yeni_sonra_eski_iptal_gevsetme_yok`)" diye kabul etmek mi sizin kararınızdır (bölüm F).

- ☐ **C5. Strateji çıkışı.** Strateji pozisyonu kapatırsa:
  - Log: `canli_kapandi ... <sembol> <miktar> piyasa emriyle kapatıldı (<neden>)`; hemen ardından borsadaki stop emri iptal edilir.
  - Binance: pozisyon yok, Open Orders'ta o sembolde açık emir yok.
  - Telegram: `canli_kapandi`.

- ☐ **C6. Borsa stopu çalışırsa** (fiyat stopa değerse): Telegram'da yürütücü kapatmadığı için `canli_kapandi` gelmez; bir sonraki turda (≤ ~1 dk) şu görülür:
  `canli_uyusmazlik ... borsada pozisyon yok (stop/hedef çalışmış ya da elle kapatılmış olabilir); kayıt temizlendi, kalan emirler iptal`. **Bu stop kapanışının normal mesajıdır, hata değildir.** `islemler.jsonl` satırında `cikis_nedeni: stop` olmalı (bölüm E).

- ☐ **C7. Kapanış sonrası temizlik.** Pozisyon kapanınca borsada o sembolde **hiç açık emir kalmamalı** (stop/hedef dahil, yetim emir yok); `yurutucu_*.json` içinde `"pozlar": {}`:
```bash
grep -o '"pozlar": {[^}]*}' /var/lib/1l3a-canli/durum/canli/yurutucu_*.json | head -c 300
```
  (Dosya biçimi farklıysa `cat` ile bakın; pozisyon yokken `pozlar` boş görünmeli.)

---

## D. Zorla denenecek nadir yollar

Hepsi **testnet**'te, küçük pozisyonla. Elle denenemeyenler açıkça işaretlidir; onların kanıtı kod testidir:
```bash
cd /opt/1l3a && sudo -u l3a .venv/bin/python -m pytest testler/test_canli_borsa.py -q
```
Görülmeli: `66 passed` (sayı ileride artabilir, `failed` olmamalı). ☐ **D0** test paketi geçti.

- ☐ **D1. Servis yeniden başlatma (çift emir yok; pozisyon ve stop devralınır).** Önce açık bir testnet pozisyonu ve stopu olmalı (C2–C3). Borsada o sembolün açık emir sayısını not edin (1 stop; hedef varsa 2). Sonra:
```bash
systemctl restart 1l3a-canli
```
```bash
sleep 45 && journalctl -u 1l3a-canli -n 60 --no-pager
```
  Görülmeli: servis yeniden `... testnet hesabı hazır ...` yazar; **yeni `canli_emir_doldu` YOK**, **yeni `canli_stop_kuruldu` YOK**, `canli_uyusmazlik ... STOPSUZ` YOK. Borsada pozisyon ve stop aynı, açık emir sayısı değişmemiş.
  Paper tarafı kesintiyi kaydeder: `grep yeniden_baslatma /var/lib/1l3a-canli/durum/olaylar.jsonl | tail -n 2`.
  Opsiyonel sert deneme (çökme taklidi): `systemctl kill -s SIGKILL 1l3a-canli` — systemd 30 sn sonra kendiliğinden yeniden başlatır (`Restart=on-failure`); sonuç aynı olmalı.
  Geçti: ☐ (çift emir yok) ☐ (stop devralındı) ☐ (kayıt dosyası bozulmadı: `ozsermaye_gunluk.jsonl` yeni `servis_basi` satırı ekledi).

- ☐ **D2. Stop reddi** (stop kurulamazsa pozisyon hemen kapanır; olay `canli_stop_basarisiz`). Kod testi: `test_stop_basarisiz_pozisyon_hemen_kapanir`.
  **Zorlama yolu (⚠ doğrulanmadı, sonucu önceden bilmiyoruz):** Binance koşullu emirleri yalnız algo ucundan kabul ediyorsa, eski uç (`klasik`) reddeder. Dolayısıyla:
  1. Servisi durdurun: `systemctl stop 1l3a-canli`
  2. `sed -i 's/"kosullu_modu": *"[a-z]*"/"kosullu_modu": "klasik"/' /etc/1l3a-canli.json && grep kosullu /etc/1l3a-canli.json`
  3. `systemctl start 1l3a-canli` ve yeni bir sinyal gelene kadar bekleyin.
  Görülmeli (red gelirse): `canli_emir_doldu`, hemen ardından `canli_stop_basarisiz ... stop kurulamadı; pozisyon HEMEN kapatılıyor`, sonra `canli_kapandi ... (stop_basarisiz)`; borsada pozisyon **kalmamış**.
  Görülürse ☐ geçti. Görülmezse (testnet klasik ucu hâlâ kabul ediyor, stop normal kuruldu): bu yolla zorlanamadı demektir; "elle denenemez, kod testiyle kanıtlı" diye işaretleyin. **Denemeden sonra** `kosullu_modu` değerini mutlaka eski haline getirin (`"algo"`, ya da C3'te klasik gerekmişse klasik) ve servisi yeniden başlatın.

- ☐ **D3. Başarısız kapatma** (stop kurulamadı VE kapatma da başarısız → `canli_stop_basarisiz ... KAPATMA DA BAŞARISIZ ... ELLE KONTROL EDİN`, her turda yeniden denenir). **Elle denenemez, kod testiyle kanıtlı:** `test_stop_ve_kapatma_ikisi_de_basarisiz_alarm_ve_tekrar`, `test_r3_kill_kapatma_basarisizken_stopsuz_pozisyona_stop_kurulur`. İki şeyin aynı anda reddedilmesini testnet'te güvenle üretemeyiz. Gerçekte görürseniz: bölüm G (acil durdurma).

- ☐ **D4. Belirsiz giriş** (ağ kesilir, emir sonucu bilinmez: `canli_giris_belirsiz`; yürütücü kimlikle sorar, çift emir vermez). **Elle denenemez, kod testiyle kanıtlı:** `test_r1_belirsiz_giris_emir_dolduysa_tekrar_gonderilmez`, `test_r1_..._bir_kez_yeniden_gonderilir`, `test_r4_r5_belirsiz_giris_sonra_pozisyon_gorunce_hemen_stop_ve_acik`.

- ☐ **D5. Stopsuz pozisyonun kendiliğinden onarılması (elle denenebilir).** Açık pozisyon varken Binance testnet arayüzünde **stop emrini elle iptal edin** (Open Orders → Conditional → Cancel). En geç ~1 dakika içinde:
  Log/Telegram: `canli_uyusmazlik ... pozisyon STOPSUZ; kayıtlı stop <fiyat> kuruluyor`, ardından `canli_stop_kuruldu`. Borsada stop geri gelmiş olmalı. ☐ geçti.
  (Kod testi: `test_mutabakat_stopsuz_pozisyona_stop_kurar`.)

- ☐ **D6. Bilinmeyen pozisyon** (yürütücü dokunmamalı, yalnız uyarmalı). Binance testnet arayüzünden (Futures, Market) **elle çok küçük bir pozisyon açın** (mümkünse yürütücünün işlem yapmadığı bir sembol; en küçük miktar). En geç ~1 dakika içinde:
  Telegram/log: `canli_uyusmazlik ... BİLİNMEYEN pozisyon: <SEMBOL> <miktar>; stratejinin beklemediği bir pozisyon. Otomatik işlem YAPILMADI, elle bakın`.
  Görülmeli: pozisyon **olduğu gibi duruyor** (yürütücü kapatmadı, stop eklemedi), uyarı **tek sefer** gelir (her turda tekrarlanmaz). Sonra pozisyonu elle kapatın. ☐ geçti.
  (Kod testi: `test_mutabakat_bilinmeyen_pozisyon_yalniz_uyari`.)

- ☐ **D7. Günlük −%6 davranışı** (yalnız o gün **yeni giriş yok**; açık pozisyon kapatılmaz; ertesi UTC günü açılır). Testnet'te gerçek kayıp üretmek zor; kasayı `tahsis_usd` düşürerek sanal olarak "düşürebiliriz" (kasa = min(özsermaye, tahsis)).
  **Yöntem (⚠ doğrulanmadı; koddan çıkarım, testnet'te hiç denenmedi):** servisi durdurun, `tahsis_usd`'u 60'tan 55'e indirin (−%8,3), başlatın:
```bash
systemctl stop 1l3a-canli
```
```bash
sed -i 's/"tahsis_usd": *60/"tahsis_usd": 55/' /etc/1l3a-canli.json && grep tahsis /etc/1l3a-canli.json
```
```bash
systemctl start 1l3a-canli && sleep 30 && journalctl -u 1l3a-canli -n 30 --no-pager
```
  Görülmeli: `canli_kill_switch ... GÜNLÜK LİMİT: gün başı 60.00 -> 55.00 (>= %6 kayıp); bugün yeni giriş yok (açık pozisyonlar kapatılmaz)`. Açık pozisyon varsa **kapanmamalı**, stopu yerinde. Yeni sinyal gelirse `canli_giris_atlandi ... günlük kayıp limiti ... bugün yeni giriş yok`.
  Bu gün blok'u kendiliğinden **ertesi UTC günü** kalkar (00:00 UTC = 03:00 Türkiye). Testten sonra `tahsis_usd`'u 60'a geri alın (`sed -i 's/"tahsis_usd": *55/"tahsis_usd": 60/' ...`) ve yeniden başlatın; ayrıca `ozsermaye_gunluk.jsonl`'a `sermaye_hareketi` satırı düşer (bu kâr/zarar sayılmaz, beklenen).
  Gerçek kayıpla gözlenemez; kod testi: `test_gunluk_limit_yeni_giris_yok_kapatmaz_ertesi_gun_acilir`, `test_r6_kill_ve_gunluk_tahsis_tabanli`.

- ☐ **D8. Kill davranışı** (strateji zirveden −%30 / hesap toplamı −%20: tüm pozisyonlar ÖNCE kapatılır, emirler sonra iptal, KALICI durur). **Bu deneme kalıcı kilit bırakır; D listesinin SON denemesi olsun.** Yöntem D7 ile aynı (⚠ doğrulanmadı): açık testnet pozisyonu varken `tahsis_usd` 60 → 40 (−%33) yapıp yeniden başlatın. Tek hesapta hesap kill'i (−%20) önce tetiklenebilir; ikisi de beklenen sonuç verir.
  Görülmeli: `canli_kill_switch ... STRATEJİ KILL` (ya da `HESAP KILL`), ardından `canli_kapandi ... (kill_switch)` (ya da `hesap_kill`); borsada pozisyon yok ve emir yok. Servis çalışır görünür ama bir daha giriş yapmaz.
  **Temizlik (zorunlu):** bu testnet durumu kalıcıdır; testten sonra durum dizinini yedekleyip temiz başlayın, `tahsis_usd`'u 60'a geri alın:
```bash
systemctl stop 1l3a-canli
```
```bash
mv /var/lib/1l3a-canli/durum /var/lib/1l3a-canli/durum_killtest_$(date +%Y%m%d_%H%M)
```
```bash
sed -i 's/"tahsis_usd": *[0-9]*/"tahsis_usd": 60/' /etc/1l3a-canli.json && grep tahsis /etc/1l3a-canli.json
```
```bash
systemctl start 1l3a-canli
```
  Gerçek düşüşle gözlenemez; kod testi: `test_kill_switch_toplam_dusus_hepsini_kapatir_ve_bloklar`, `test_r3_kill_once_kapat_sonra_iptal_kapatma_basarisizsa_stop_kalir`.
  Not: Faz 1 kayıtları (E bölümü) için D8'den ÖNCE E kontrollerini bitirin; çünkü D8 durum dizinini yedeğe taşır.

- ☐ **D9. `CANLI_ONAY` olmadan canlı mod reddedilir.** Gerçek servise dokunmadan, geçici bir ayar dosyasıyla denenir (ağ isteği yapılmadan, başlamadan reddedilir; gerçek hiçbir şey çalışmaz):
```bash
sed 's/"mod": *"[a-z]*"/"mod": "canli"/' /etc/1l3a-canli.json > /tmp/canli_onay_deneme.json && grep '"mod"' /tmp/canli_onay_deneme.json
```
```bash
cd /opt/1l3a && env -u CANLI_ONAY sudo -u l3a .venv/bin/python -m motor.canli.borsa.calistir --ayar /tmp/canli_onay_deneme.json --durum /tmp/onay_deneme_durum; echo "cikis_kodu=$?"
```
  Görülmeli: `canlı yürütücü BAŞLAMADI: mod=canli için ortamda CANLI_ONAY=evet gerekir; yok: GERÇEK PARA ile başlatma reddedildi` ve `cikis_kodu=2`.
  Not: komut `/etc/1l3a-canli.env` dosyasını yüklemez (yalnız systemd yükler), bu yüzden `CANLI_ONAY` ortamda yoktur. Sonra geçici dosyayı silin: `rm /tmp/canli_onay_deneme.json`. Kod testi: `test_canli_mod_onay_olmadan_baslamaz`.
  (Servis dosyası `RestartPreventExitStatus=2 3` içerir: çıkış kodu 2 ve 3'te systemd tekrar denemez; `Restart=on-failure` döngüsüne girmez.)

---

## E. YENİ kayıt dosyalarının doğrulanması

Üç dosya `/var/lib/1l3a-canli/durum/canli/` altında, append-only, satır başına bir JSON. **Bu bölümü en az bir tam kapanmış testnet işlemi olduktan sonra, D8'den önce yapın.** Bir satırı okunaklı görmek için:
```bash
tail -n 1 /var/lib/1l3a-canli/durum/canli/islemler.jsonl | python3 -m json.tool
```

- ☐ **E1. `islemler.jsonl` satırı var** (her kapanan gerçek işlem için bir satır). Kontrol edilecek alanlar:
  - `veri_kaynagi` = `"userTrades"` (kuruda `"yok"` olurdu; testnet'te `userTrades` olmalı).
  - `giris_fiyati`, `cikis_fiyati`, `miktar` dolu; `miktar` Binance Positions ekranındaki miktarla aynı.
  - `komisyon_usd` **dolu** (null değil), `komisyon_neden` = `null`. Komisyon USDT cinsinden olmalı; BNB gibi bir varlıkla ödenmişse satır `komisyon USD cinsinden değil (...)` yazar ve komisyon null kalır.
  - `funding_usd` sayı (testnet'te kısa işlemde `"0"` olabilir; null ise `funding_neden` nedenini söyler).
  - `brut_pnl_usd`, `net_pnl_usd` (= brüt − komisyon + funding) dolu; `net_funding_dahil` = `true`.
  - `r` bir sayı (null değil). Elle kontrol: `r` ≈ `net_pnl_usd` ÷ `planlanan_risk_usd` (60 USD kasada 1R ≈ 0,90 USD).
  - `cikis_nedeni`: stop ile kapandıysa `stop`, yürütücü kapattıysa `strateji`/`sistem`/`kill`; `bilinmiyor` yalnız elle kapatmada çıkar.
  - `model_maliyet_bps` ve `gercek_maliyet_bps` dolu.
  - `notlar` boş ya da anlamlı (ör. "r hesaplanamadı" varsa nedeni yazılıdır).
  ⚠ doğrulanmadı: `userTrades` / `income` uçlarının **gerçek testnet yanıt biçimi** (alan adları `orderId`, `commission`, `commissionAsset`, `realizedPnl`) koda sahte yanıtla yazıldı. Alanlar boş/beklenmedikse bana satırı (anahtarsız) gösterin.
  ☐ komisyon dolu ☐ r hesaplandı ☐ `orderId` eşlemesi: giriş dolumu `giris_fiyati`'nı veriyor ve `miktar` pozisyonla aynı (eşleşme tutmazsa `notlar`'da "pozisyon dolum geçmişinde tam sıfırlanmamış görünüyor" ya da `islemler` satırı hiç yazılmaz).

- ☐ **E2. Binance ekranıyla çapraz kontrol.** Binance testnet → Futures → **Trade History** (ya da Transaction History): ilgili işlemin fiyatları, miktarı ve ücreti `islemler.jsonl` satırıyla (küçük yuvarlama dışında) aynı olmalı. Fark varsa not edin; "mutabakat farkı 0" ölçütü (F) buna dayanır.

- ☐ **E3. Stopla kapanan işlem satırı.** Stop çalışmışsa `cikis_nedeni` = `stop`, `cikis_kayma_bps` dolu. (Stop hiç çalışmadıysa bu madde bekler; Faz 2 duman bunu da kapsayabilir.)

- ☐ **E4. `ozsermaye_gunluk.jsonl`.**
```bash
head -n 3 /var/lib/1l3a-canli/durum/canli/ozsermaye_gunluk.jsonl | cut -c1-400
```
  Görülmeli: servis her başladığında `"tur": "strateji"`, `"neden": "servis_basi"` satırı (`ozsermaye`, `tahsis_usd` = 60, `kasa` = min(özsermaye, 60), `acik_pozisyon`) ve aynı anda `"tur": "hesap"` satırı (`toplam`, `zirve`). Gün değişince (UTC) `"neden": "gun"` satırları eklenir. Tahsis değiştirdiyseniz `"tur": "sermaye_hareketi"` satırı (kâr/zarar değil).
  ☐ servis başı satırı var ☐ ertesi UTC günü `gun` satırı geldi (1 gün sonra).

- ☐ **E5. `olaylar_arsiv.jsonl`.**
```bash
tail -n 5 /var/lib/1l3a-canli/durum/canli/olaylar_arsiv.jsonl | cut -c1-300
```
  Görülmeli: her olay bir satır (`zaman`, `strateji`, `tur`, `mesaj`); Telegram'a giden olayların tümü burada da var; `canli_kayit_hatasi` yok (`grep -c canli_kayit_hatasi ...` = 0).

- ☐ **E6. Haftalık rapor testnet durum dizinine karşı çalışıyor.** Rapor salt okunurdur (borsaya bağlanmaz). `--baslangic` olarak testnet'e başladığınız günü yazın (örnek biçim `2026-11-25`):
```bash
mkdir -p /var/lib/1l3a-canli/rapor && chown l3a:l3a /var/lib/1l3a-canli/rapor
```
```bash
cd /opt/1l3a && sudo -u l3a .venv/bin/python -m araclar.canli_haftalik_rapor --canli-durum /var/lib/1l3a-canli/durum --paper-durum /var/lib/1l3a-paper/durum --ayar /etc/1l3a-canli.json --baslangic 2026-11-25 --sunucu-gider-usd-ay 12 --yaz-karsilastirma --cikti /var/lib/1l3a-canli/rapor/testnet_$(date +%F).md
```
  Görülmeli: `yazıldı: ...testnet_<tarih>.md ve ...json` (hata/Traceback yok).
```bash
cat /var/lib/1l3a-canli/rapor/testnet_$(date +%F).md
```
  Raporda bakılacaklar: "Özet uyarılar"; "1. Dönem ve toplam" (sunucu gideri 12 USD/ay ayrı satırda); "3. Maliyet" (canlı/model bps dolu); "4. Canlı–paper eşleşmesi" (dolan/atlanan sayıları E5'teki olaylarla tutuyor); "7. Sistem sağlığı" (**Stopsuz pozisyon (toplam): 0**, kill `False`); en altta "Yürütücünün yazmadığı / eksik alanlar" (uydurma yok, eksik alan açıkça yazılır). `--yaz-karsilastirma` ayrıca `canli/haftalik_karsilastirma.json` dosyasını yazar:
```bash
cat /var/lib/1l3a-canli/durum/canli/haftalik_karsilastirma.json
```
  Not: testnet'te "ewo beklenti bandı" ve "e0v1en emeklilik (son 60 işlem)" bölümleri çok az veriyle anlamsızdır; Faz 1'de yalnız **hatasız çalışması** aranır.
  ☐ rapor üretildi ☐ sayılar E1/E5 ile uyumlu

- ☐ **E7. Risk adımı kontrolü** (planda kullanılmaz, yalnız aracın çalıştığını görmek için isteğe bağlı): `python -m motor.canli.borsa.risk_adim_kontrol --durum /var/lib/1l3a-canli/durum`. CANLI_PLAN_V2 §3 bu aracı kullanmadığını söyler; çalıştırmak zorunlu değildir.

---

## F. Bitiş ölçütleri: kim, neye göre karar verir

**Kararı her zaman siz (kullanıcı) verirsiniz.** Ben kanıtı (log satırı, Telegram mesajı, rapor) tablo hâlinde sunarım; kutuları işaretlenmemiş ölçüt "geçti" sayılmaz.

### Faz 1 bitiş ölçütü (CANLI_PLAN_V2 §7, 25 Kasım – 5 Aralık)
> Giriş, stop kurma/yükseltme, kapatma, yeniden başlatma görüldü; stop reddi ve başarısız kapatma zorla denendi.

| Ölçüt | Kanıt maddesi | Not |
|---|---|---|
| Giriş görüldü | C2 | |
| Stop kurma görüldü | C3 | algo/klasik uç karar verildi |
| Stop yükseltme görüldü | C4 | oluşmazsa: gözlenmedi, kodla kanıtlı kabul etmek sizin kararınız |
| Kapatma görüldü | C5 / C6 | |
| Yeniden başlatma görüldü | D1 | |
| Stop reddi zorla denendi | D2 | zorlanamazsa "elle denenemez" diye işaretli + kod testi |
| Başarısız kapatma zorla denendi | D3 | **elle denenemez**; kod testiyle kanıtlı (planın bu cümlesi böyle karşılanır) |
| Kayıt dosyaları ve rapor çalışıyor | E1–E6 | |
| Kuru süresi ve test paketi | B7, D0 | |

☐ Faz 1 geçti (siz onaylayın, tarih: ____ ) — Faz 2 yalnız bundan sonra başlar.

**Faz 1 geçmezse ne olur:** Faz 2 (gerçek para) **başlamaz**; plan §9: "Testnet atlanmaz". Sorun kod hatasıysa düzeltme yapılır (Sonnet ajanı + benim denetimim), ilgili madde yeniden denenir; takvim kayar, para riske girmez. Uç/parametre sorunu (algo) için `kosullu_modu: "klasik"` yolu denenir. İkisi de çözmezse yeni plan kararı gerekir.

### Faz 2: Duman (60 USD × 2 gerçek para, Aralık 1. hafta)
Ön koşul: Faz 1 geçti. **Gerçek paraya geçiş KURULUM §13 E'deki adımlarla, bilerek yapılır.** Özet adımlar (bu listede yalnız hatırlatma; ayrıntı ve komutlar KURULUM §13 A, E):
- ☐ **F1. İki ayrı alt hesap, iki ayrı gerçek anahtar** (`BINANCE_API_KEY_S1/S2`, yalnız Reading + Futures, **Withdrawals KAPALI**, sunucu IP kısıtlı). Anahtarlar yalnız `/etc/1l3a-canli.env`'e.
- ☐ **F2. Testnet durumunu ayırın** (testnet kayıtları gerçek para kayıtlarına karışmasın; ⚠ doğrulanmadı: yeni boş durum dizininde paper motoru sıfırdan başlar, tohum veri dizini aynı kalır):
```bash
systemctl stop 1l3a-canli
```
```bash
mv /var/lib/1l3a-canli/durum /var/lib/1l3a-canli/durum_testnet_$(date +%Y%m%d)
```
- ☐ **F3. `/etc/1l3a-canli.json`: iki strateji, 60'ar USD, mod `canli`.** `CANLI_PLAN_V2`'deki örnek ayar `stratejiler/canli_ayar.ornek.json` (2 × 60 USD) dosyasındadır (plan dalında). Yazılacak içerik (mod hâlâ `testnet` ile başlayıp en son `canli` yapılır):
```bash
cat > /etc/1l3a-canli.json <<'EOF'
{
  "surum": 1,
  "mod": "testnet",
  "working_type": "MARK_PRICE",
  "kosullu_modu": "algo",
  "giris_gecikme_max_sn": 900,
  "hedef_emri": true,
  "stratejiler": [
    {"id": "dis__e0v1en", "api_key_env": "BINANCE_API_KEY_S1", "api_secret_env": "BINANCE_API_SECRET_S1", "tahsis_usd": 60, "islem_risk": 0.015},
    {"id": "dis__ewo-ema-ofset", "api_key_env": "BINANCE_API_KEY_S2", "api_secret_env": "BINANCE_API_SECRET_S2", "tahsis_usd": 60, "islem_risk": 0.015}
  ]
}
EOF
```
  `kosullu_modu` değerini Faz 1'de karar verdiğiniz değerle (`algo` ya da `klasik`) aynı bırakın.
- ☐ **F4. Gerçek anahtarları ve `CANLI_ONAY=evet`'i** `/etc/1l3a-canli.env`'e yazın (`nano /etc/1l3a-canli.env`), sonra:
```bash
sed -i 's/"mod": *"[a-z]*"/"mod": "canli"/' /etc/1l3a-canli.json && grep '"mod"' /etc/1l3a-canli.json
```
```bash
systemctl restart 1l3a-canli && sleep 30 && journalctl -u 1l3a-canli -n 40 --no-pager
```
  Görülmeli: iki satır `... canli hesabı hazır, özsermaye <gerçek bakiye>, tahsis 60`. Her hesaba **en az 60 USD** USDT-M Futures cüzdanına aktarılmış olmalı.
  Küçük kasada BTC/ETH sık `min_tutar_alti` ile atlanır: normaldir.
- ☐ **F5. Duman süresince** her giriş için C2–C3 gibi doğrulayın, **ilk gerçek girişte Binance ekranında stopu gözle görün**, haftalık raporu (E6 komutu, `--cikti` adını `duman_` yapın, `--baslangic` Faz 2 başlangıç tarihi) çalıştırın.

### Faz 2 duman ölçütleri (CANLI_PLAN_V2 §7: tümü sağlanmalı)

| Ölçüt | Nasıl sayılır | Kutu |
|---|---|---|
| **≥ 10 giriş** | Toplam `canli_emir_doldu` (iki strateji birlikte; planda "≥ 10 giriş" tek toplam olarak yazılı) | ☐ |
| **≥ 1 borsa stopu** | En az bir pozisyon **borsadaki stop emriyle kapanmış** olmalı (`islemler.jsonl` satırında `cikis_nedeni: stop`; Binance geçmişinde stop emri "Triggered/Filled"). Yalnız stopun kurulması yetmez (kurulma her girişte zaten C3'te kontrol edilir). Lider kararı 2026-11-11: plan metnindeki "borsa stopu" = tetiklenen stop. | ☐ |
| **1 yeniden başlatma** | D1 gerçek paradaki pozisyonla da yapıldı: çift emir yok, stop devralındı | ☐ |
| **Stopsuz pozisyon 0** | Rapor "7. Sistem sağlığı": `Stopsuz pozisyon (toplam): 0`; hiç `canli_stop_basarisiz`, `STOPSUZ` olayı yok; Binance'te her pozisyonun stopu var | ☐ |
| **Mutabakat farkı 0** | Lider kararı 2026-11-11 (üç şart birlikte): (a) Binance'teki açık pozisyon ve emirler = durum dosyası; beklenmedik `canli_uyusmazlik` yok (normal stop kapanış mesajı hariç); (b) Binance Transaction History'de (Realized PnL + Commission + Funding Fee) toplamı ile `islemler.jsonl` `net_pnl_usd` toplamı arasındaki fark ≤ 0,01 USD; (c) `ozsermaye_gunluk.jsonl` kasası Binance bakiyesiyle (≤ 0,01 USD) uyumlu. | ☐ |

Sonuç kuralı ve kararı: ☐ Faz 2 geçti (siz onaylayın, tarih: ____ ). Plan §5: bu, **basamak 1** (ewo 250 USD) için gereken şartlardan **yalnız biridir**; 8 Aralık sadakat kontrolü ve birleşik hesap oynatması da gerekir. Basamak geçişi ayrı kullanıcı kararıdır.

**Faz 2 geçmezse ne olur:** gerçek para büyütülmez (basamak 1 başlamaz). Önce bölüm G ile durdurup pozisyonları kapatın, kök nedeni raporlayın; düzeltme sonrası duman **yeniden** (60 USD ile) yapılır. Kalıcı kill, stopsuz pozisyon ya da açıklanamayan mutabakat farkı varsa o strateji için emeklilik/yeniden değerlendirme kararı da sizindir (plan §4). Zararı telafi etmek için boyut büyütülmez.

---

## G. Acil durdurma

**1) Tek komut (yürütücüyü durdurur; borsadaki stop emirleri YERİNDE kalır, pozisyonlar korunur):**
```bash
systemctl stop 1l3a-canli
```
Kontrol:
```bash
systemctl is-active 1l3a-canli
```
Görülmeli: `inactive`. Yeniden otomatik açılmasını da engellemek için (örn. tatilde, emin değilken):
```bash
systemctl disable 1l3a-canli
```
Paper servisi (`1l3a-paper`) bundan etkilenmez.

**2) Borsada açık pozisyonu elle kapatma** (servisi **önce** durdurun ki yürütücü araya girmesin):
1. Binance (gerçek hesap: binance.com; testnet: testnet.binancefuture.com) → **Futures** → **Positions** sekmesi.
2. Pozisyon satırında **Market** (ya da "Close All Positions"/"Close Position") → onaylayın.
3. **Open Orders** sekmesinde o sembolün kalan emirlerini (STOP MARKET, TAKE PROFIT MARKET; algo/koşullu olanlar ayrı bir bölümde olabilir) **Cancel All** ile iptal edin.
4. Positions listesinin boş ve Open Orders'ın boş olduğunu görün. Birden fazla alt hesap varsa her hesap için ayrı ayrı yapın.
⚠ doğrulanmadı: Binance arayüzündeki düğme adları ve algo emirlerinin görüldüğü sekme zamanla değişebilir; yukarıdaki adlar kabaca yoldur. Yapamazsanız en güçlü yol: Binance → API Yönetimi → ilgili anahtarı **silmek** (bot hiçbir emir veremez; pozisyonu yine elle kapatmanız gerekir).

**3) Sonrası.** Yürütücüyü durdurup pozisyonu elle kapattıysanız, servisi yeniden açmadan önce bana yazın: kayıtlı durum (`yurutucu_*.json`) ile borsa farklı olabilir. Elle kapatılmış pozisyon, servis açıkken olsaydı yalnız `canli_uyusmazlik ... borsada pozisyon yok ... elle kapatılmış olabilir` olarak temizlenirdi (zararsız); `islemler.jsonl` satırında `cikis_nedeni` `bilinmiyor` görünür.

**Kalıcı kill kilidini kaldırmak** (yalnız nedenini anladıktan sonra, bana sorarak): KURULUM §13 "Kill switch ve acil durdurma" paragrafı.
