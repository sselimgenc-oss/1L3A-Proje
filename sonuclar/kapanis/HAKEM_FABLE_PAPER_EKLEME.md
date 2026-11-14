# Hakem (Fable) — paper v2 setine 6 kapanış stratejisi ekleme (10 → 16 hesap)

Tarih: 2026-11-14. Kapsam: commit edilmemiş çalışma ağacı (HEAD `ce66ae1`). Kod değiştirilmedi, commit yapılmadı.

## Sonuç: KOŞULLU ONAY

Kod tarafı doğru ve güvenli; deploy öncesi aşağıdaki 4 koşul kapatılmalı. Koşulların hiçbiri motor mantığı hatası değil:
ikisi deploy talimatı/betiği, biri mühürlü dosya onayı, biri commit düzeni.

## Yapılması gerekenler (deploy öncesi)

1. **Sunucu talimatı çalışmaz / yedeksiz geçiş penceresi (düzeltilmeli).** `KAPANIS_EKLEME_SUNUCU_ADIMLARI.md` "cd /opt/1l3a && bash
   deploy/v2_kapanis_ekle.sh" diyor; ama betik sunucuya ancak `git pull` ile gelir ve `git pull` betiğin İÇİNDE. Yani ilk komut "dosya yok"
   der. Kullanıcı önce elle `git pull` yaparsa: paper hâlâ çalışırken yeni kod diske iner; o arada servis herhangi bir nedenle yeniden
   başlarsa (Restart=on-failure) 10→16 geçişi YEDEK ALINMADAN yapılır. Doğru sıra talimata yazılmalı:
   `systemctl stop 1l3a-paper` → `sudo -u l3a git pull --ff-only` → `bash deploy/v2_kapanis_ekle.sh` (betikteki stop/pull tekrarı zararsız).
2. **Betik hata verirse paper kapalı kalır.** `set -e` + `systemctl stop` sonrası `git pull --ff-only`, `pip install` ya da ön kontrol
   hata verirse betik çıkar, paper DURMUŞ kalır ve kullanıcıya ne yapacağı söylenmez. Eklenmeli: (a) hata tuzağı (`trap ... ERR`):
   "paper DURDU; yedek şurada; eski sürüm şu; şu komutlarla geri başlatın" mesajı; (b) başlatmadan ÖNCE durum dosyası kontrolü:
   `paper_state.json` içindeki `set_imza` == `v2.onceki_set_imzasi(s)` (beklenen `985f914d0bb6b643`) değilse başlatma — yoksa servis
   açık hatayla düşer ve systemd tekrar tekrar dener (durum bozulmaz ama paper kapalı kalır).
3. **`sonuclar/final/butunluk_kayit_v2.json` yeniden yazıldı — kullanıcı onayı açıkça alınmalı.** Ayrıntı aşağıda (bölüm "Bütünlük kaydı").
4. **Commit düzeni.** Çalışma ağacında bu işle ilgisiz iki şey var: `sonuclar/kilit_acilis.jsonl` (+4 satır, ek 12 portföy koşusundan) ve
   `sonuclar/kapanis/ileri_sinav_ek12/`. Ayrı commit edilmeli. Yeni dosyalar (`deploy/v2_kapanis_ekle.sh`,
   `deploy/KAPANIS_EKLEME_SUNUCU_ADIMLARI.md`, `testler/test_paper_v2_kapanis.py`) izlenmiyor; commit'e eklenmezse sunucuya gitmez.

## Kesin kurallar — ihlal var mı?

| Kural | Durum |
|---|---|
| SERT_LIMITLER / risk / kill / günlük limit değer ve mantığı | **Değişmedi.** `motor/risk`, `motor/portfoy`, `motor/backtest` diff'i boş. Kayıttaki `sert_limitler` sha256 eskiyle aynı. Yeni hesaplar: risk %0,5, limit_modu "uygula", kaldıraç 3, sermaye 10.000 (mevcutlarla aynı). |
| CANLI_LIMITLER / canlı (gerçek emir) yolu | **Kod değişmedi** (`motor/canli/borsa/*` diff'i boş). Dolaylı etki: aşağıda "Canlı notu". |
| Mevcut 10 stratejinin davranışı + durum dosyası uyumu | **Bozulmadı** (aşağıda 2 ve 3). |
| `sonuclar/final/` mühürlü | **İhlal (onaya bağlı):** `butunluk_kayit_v2.json` yeniden yazıldı. |

## Denetim maddeleri

**(1) azalan_roi / geri_cekilme semantiği — backtest ile birebir.** `PaperMotor._karar_sinyal` (paper_motor.py:270) ile
`motor/backtest/motor.py:506-522` satır satır karşılaştırıldı: aynı `cks.kar_yuzde / azalan_roi_doldu / geri_cekilme_doldu` çağrıları;
kâr kapanıştan, zirve `p.ekstrem`'den (çekirdek `super()` içinde aynı mumun yüksek/düşüğüyle güncellendikten sonra), `p.tutulan` artırıldıktan
sonra; çıkış `cikis_emri` olarak sonraki açılışta dolar. Öncelik: kill > günlük limit > sinyal > zaman > roi > geri çekilme (çekirdek bir çıkış
emri koyduysa ek kod dokunmuyor). Alanlar boşken ilk `if` ile hemen dönüyor. Backtest'te bu ikisinden SONRA gelen dallar (kar_rsi, yasa_zarar,
kapanis_chandelier, kanca) ile önce gelen koşullar (min_tutma_mum, yalniz_karda_cikis) paper'da yok; bunlar fail-closed listesinde kalmaya
devam ediyor ve yeni eklenen "pozisyon_cikisi (kanca)" kontrolü de doğru. 6 stratejinin gerçek ayarları: 4 tanesi varsayılan çıkış ayarı;
B001:670 ve B001:574 yalnız azalan_roi + geri_cekilme kullanıyor, kanca yok.

**(2) `_karar_sinyal` override'ı mevcut 10'u etkiler mi — hayır.** Mevcut 10'un hiçbiri bu iki alanı taşımıyor (daha önce fail-closed'dan
geçiyorlardı, yani alanlar boştu); override `super()` sonrası hemen dönüyor. Portföy hesabı (`pf__sabit_sepet`) `_karar_agirlik` yolunda,
bu fonksiyona hiç girmiyor. `set_imzasi` havuz kayıtları için aynı girdiyi üretiyor: HEAD'deki 10'lu setten bağımsız hesapladığım imza
`985f914d0bb6b643` = `onceki_set_imzasi`. `hesap_dizin_adi` mevcut 10 ad için adı AYNEN döndürüyor (klasörler değişmez).

**(3) İmza geçişi — güvenli.** Yalnız "kayıtlı imza == kapanış kayıtları çıkarılmış setin imzası" ise kabul; kayıtta olmayan hesap bir
kapanış kaydı değilse açık hata; başka her fark eski açık hata. Mevcut hesaplar `sozlukten_yukle` ile aynen, yeniler `baslat` ile sıfırdan
(dolum yok, yalnız son kapanmış barın kararı). Geçişten hemen sonra `kaydet()` → dosya yeni imzayı (`4c22e27149b65a14`) taşır; kaydetmeden
çökerse geçiş aynen tekrarlanır (zararsız). Geri dönüş (yedek + eski commit) tutarlı: eski kod 16'lı kaydı yüklemez, yedekteki 10'lu kaydı
yükler. Notlar: (a) geri dönüşte 10 hesap yedek anına döner (arada geçen işlemler `durum_16lik_deneme` içinde kalır, eski koda taşınamaz);
(b) `git checkout <sürüm>` kopuk HEAD bırakır, sonraki `git pull --ff-only` çalışmaz — talimata `git checkout <dal>` notu eklenebilir;
(c) üst düzey (toplam) geçmiş eğrisi geriye dönük +60.000 gösterir (`_birlestir_gunluk` yeni hesapları geçmiş günlerde 10.000 sayar):
sahte sıçrama/düşüş üretmez ama eski günlerin toplam rakamı öncekinden farklı görünür.

**(4) Deploy betiği / adımlar dosyası.** `rm` yok, durum silme yok, limit değişikliği yok, gizli anahtar/ortam değişkeni yok; yedek
`cp -a` ile kopya, pano sunucusunun yayınladığı `durum/` dizininin DIŞINDA. Tehlikeli komut yok. Sorunlar koşul 1 ve 2'de.

**(5) PENCERE ve uzun bellekli göstergeler — ölçtüm, sapma yok.** 6 stratejinin her biri için BTC/SOL/DOGE'de (kilitli dönem okunmadan)
tam geçmişle üretilen sinyali, canlıdaki gibi yalnız son N barla (5m 4000, 4h 3000, 1g 1500) üretilen sinyalle karşılaştırdım:
18 strateji×sembol, toplam ~1.240 uç nokta (çoğu sinyalli bar): yön, çıkış ve stop farkı = 0. EMA200/EWO 4000 barlık pencerede tam yakınsıyor.
Kalan risk: yeni listelenmiş/eksik geçmişli sembolde pencere dolmadan sinyal (13 kripto için geçerli değil).

**(6) Testler.** `python -m pytest testler/test_paper_v2*.py testler/test_paper_motor*.py testler/test_gun_sonu_paper.py -q` →
**77 geçti** (3 dk 40 sn). Kapsam iyi: roi/geri çekilme paper=backtest (işlem bazında, 1e-9), gerçek 6 sınıf sentetik mumda paper=backtest,
boş ayarda etkisizlik, geçiş (korunan hesap = kesintisiz koşuyla aynı işlemler/özsermaye), yanlış imza/eksik havuz hesabı hatası, sahte
Binance ile `canli_calistir` geçişi, bütünlük kaydı + sert limit eşitliği. Eksikler (engel değil): çok sembollü tek kasada roi eşdeğerliği
yalnız tek sembolle sınanmış; deploy betiğinin kendisi sınanmıyor; "roi"/"geri_cekilme" çıkış nedenlerinin Telegram/pano Türkçe karşılığı
yok (ham ad görünür, hata vermez).

## Bütünlük kaydı (`sonuclar/final/butunluk_kayit_v2.json`)

- **Zorunlu mu?** Paper'ın çalışması için HAYIR. Yalnız panodaki "Bütünlük" bandının "eşleşti" göstermesi için gerekli; yazılmasaydı iki kalem
  (set dosyası, maliyet modeli) dürüstçe "uyuşmuyor" görünürdü.
- **Eski alanlar aynı mı?** Evet. Eski 1.171 yaprak alandan hiçbiri silinmedi; yalnız 4'ü değişti: `kaydedildi`, `kod_commit`,
  `set_dosyasi.sha256` (set dosyası değişti), `maliyet_modeli.sha256` (toplam özet). `havuz`, `maliyet_tablosu`, `sert_limitler` özetleri ve
  mevcut 10 hesabın `ayrinti` değerleri birebir aynı; 378 alan eklendi (6 yeni hesap).
- **Kusur:** `kod_commit` = `266fda4` (HEAD `ce66ae1` bile değil; bu değişikliğin commit'i hiç değil). Alan yalnız bilgi amaçlı,
  karşılaştırmada kullanılmıyor.
- **Daha güvenli alternatif:** eski dosyayı bayt bayt bırakıp yeni kaydı ayrı dosyaya yazmak (ör. `butunluk_kayit_v2_16.json`) ve
  `guven.KAYIT_YOLU_V2`'yi ona çevirmek: 10'lu setin mühürlü kanıtı yerinde kalır. Dosyanın kendi notu "Güncellemek kullanıcı kararıdır"
  dediği ve eski sürüm git geçmişinde durduğu için yerinde güncelleme de savunulabilir — ama karar kullanıcının; onay DURUM.md'ye yazılmalı.

## Canlı notu (kod ihlali değil, karar gerektirir)

`motor/canli/borsa/calistir.py:onkontrol` canlı strateji kimliğini "paper_v2 setinde var mı" diye kontrol ediyor, etikete bakmıyor.
Set 16'ya çıkınca 6 kapanış adayı da canlı ayarına yazılabilir hale geldi (bugün yazılı değil; deploy `/etc/1l3a-canli.json`'a dokunmuyor).
"12 hafta paper + kullanıcı onayı" şartı şu an yalnız sözle korunuyor. Öneri (ayrı kullanıcı kararı, canlı yolunu değiştirdiği için bu
değişikliğe katılmamalı): `onkontrol`'e `kapanis_aday` etiketini reddeden satır.

## Bilgi: paper ile kapanış backtest'i aynı ölçü değil

Kapanış koşuları (ve ileri dönem sınavı) her sembolü AYRI backtest etti; paper'da 13 sembol TEK 10.000 USD kasada (toplam risk tavanı %5 →
aynı anda en çok 10 pozisyon; kaldıraç tavanı 3). Sinyaller aynı, ama eşzamanlı sinyallerde bazı girişler reddedilebilir; paper sonucu
kapanış tablolarıyla birebir karşılaştırılmamalı. Mevcut 10 hesapla aynı kural, yeni bir sapma değil.
