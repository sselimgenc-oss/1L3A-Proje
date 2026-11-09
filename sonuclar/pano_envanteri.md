# Eski pano envanteri ve mevcut panoyla karşılaştırma

_Hazırlayan: araştırma ajanı (yalnız okuma). Tarih: 2026-11-08. Kod değiştirilmedi; ağır komut çalıştırılmadı._
_İlke (DURUM.md, Aşama 3): **pano yeni hesap yapmaz**, yalnız motorun yazdığı durum/kayıt dosyalarını biçimler. Bu yüzden her özelliğin "hesap nerede" sütunu: motor (`motor/canli/paper_durum.py` / `backtest_durum.py` yeni JSON alanı yazar) veya pano (yalnız biçim)._
_Gizli anahtar/token: taranan eski pano klasörlerinde (sg-pano, strateji-test-pano, swing-sg/karsilastirma, codex-algo) **anahtar bulunmadı**. Eski panoların bir kısmı claude.ai artifact platformuna (`window.claude.use("db"/"sample")`) bağlı; bunun kendisi bir anahtar değil ama bizim için taşınamaz bir bağımlılık._

---

## 0. Kaynak haritası (önemli: ekran görüntülerinin gerçek kaynağı nerede)

| Kaynak | Ne olduğu | Güvenilirlik |
|---|---|---|
| `arsiv/sg-algo-proje/pano_ekranlar/s01..s17.jpg` | "Kağıt Hesaplar" panosu (5 ekip botu, 13 sekme: Özet, Karne, Grafikler, Takvim, Açık pozisyonlar, İşlem geçmişi, İstatistik, Stratejiler, Koç, Öğrenme, Rapor, Dönemsel getiri, Risk). Kullanıcının kendi ekran görüntüleri (15 Ekim 2026 verisi). | Gerçek (gerçek bot verisi, formüller koduyla doğrulandı) |
| **`arsiv/swing-sg/karsilastirma/panel/index.html`** (+ `panel_veri.py`, `koni.py`, `EKIP.md`) | **Ekran görüntülerinin birebir kaynak kodu.** Karne, koç, gölge öğrenme, rapor, simülatör, risk, korelasyon formülleri burada (görev metni bunu "sg-arge copytrade/canli/pano.py" diye tarif ediyordu; o dosya arşivde yok, `arsiv/sg-arge-/` içinde yalnız .md ve .xlsx liste var). | Gerçek, hesaplayan kod |
| `arsiv/codex-algo/src/codex_algo/dashboard.py` + `docs/DASHBOARD_PARITY.md` | Aynı panonun bağımsız Streamlit karşılığı + 12 yeni fikir. Koç/simülatör/öğrenme **iskelet** (gerçek hesap yok); karne farklı (backtest özetinden). | Yarı iskelet; `DASHBOARD_PARITY.md` iyi bir işlev şartnamesi |
| `arsiv/strateji-test-pano/` (index.html, paper_trading_dashboard.html, data.json, bot_engine.py) | "Sg Test Panel / SPS-03 All-Weather" görünümü. **`bot_engine.py` yalnız saatlik fiyat çekip açık pozisyon K/Z'sini günceller** (stop yoksa varsayılan `entry*0.96`, boyut varsayılan 2000 $); karne puanları, PSR, "luck_prob", Sharpe 2.44, gölge-mod %78 isabet gibi her şey `data.json`'a **elle yazılmış**. | **Doğrulanamaz / uydurma izlenimi**: tasarım fikri olarak okunur, sayılar kanıt değildir |
| `arsiv/sg-pano/` | Hyperliquid **copy-trade** izleme panosu (Özet / Trader'lar / Huni / Ayarlar) + animasyonlu "ofis". Trading stratejisi panosu değil; bizim için fikir kaynağı (huni, aday kapısı, performans körlüğü, kararlarım). GPL-3.0 (ofis kodu Etre Trading Office'ten türemiş). | Gerçek ama alakası kısmi |
| `arsiv/swing-sg/deneyler/{meta_etiket.py, codex2_adaylar.py}`, `arsiv/algo-sg/dis_kaynak/kurallar.py` | Makine öğrenmesi denemeleri (bkz. Bölüm 3). | Gerçek kod ve sonuç |

## 1. Mevcut pano (motor/canli) — kısa durum

- Sekmeler: ÖZET, STRATEJİLER, POZİSYON, İŞLEMLER, RİSK, SAĞLIK (`pano.py` `SEKMELER`). Tek dosya HTML, JS'siz çalışabilir, TSİ saati, yazdır CSS'i var, Telegram metni aynı modülde (`telegram_metni`).
- **Eski panoda olmayan, bizde olan**: sert limit kullanım çubukları (günlük %3, 3x, %20 kill switch, açık stop riski), maliyet dökümü (ücret/kayma/funding), reddedilen/kırpılan sinyal sayacı ve nedenleri, risk olayları günlüğü, beklenti penceresi (4/8 hafta, p05..p95 bandı, alarm eşiği), veri bayatlığı (seans dakikası), strateji ayarı + sonraki yenileme.
- **KRİTİK BULGU (okuyucu hazır, yazıcı yok):** `pano.py` şu alanları okumak/çizmek için **hazır** ama `paper_durum.py` / `backtest_durum.py` bunları **henüz yazmıyor**; yalnız `testler/test_pano.py` sahte veriyle yazıyor. Bu yüzden canlı panoda bu bölümler "motor yazar / veri yok" der (uydurma yok, doğru davranış):
  `ozet.istatistik{}` (SQN, Sharpe, Sortino, çeyrek Kelly, seriler, tutma süresi, en iyi/kötü gün), `ozet.cikis_nedenleri[]`, `ozet.gunluk_kz_ajan[]` (dönemsel getiri), `stratejiler.ajanlar[]`, `stratejiler.enstrumanlar[]`, `stratejiler.strateji_enstruman[]` (matris), `maruziyet.bekleyen_emirler[]`.
- Gerçekte yazılan ek dosyalar: `maruziyet.json`, `maliyet.json`, `reddedilen.json`, `olaylar.jsonl`, `icgoruler.json`, `ozsermaye_gecmisi.json`, `islemler.jsonl`, `saglik.json` (+ `gunluk_kz`, `dusus_serisi`).
- İlgili testler: `testler/test_pano.py`, `test_canli_durum.py`, `test_paper_durum.py`, `test_telegram.py`.

**Eski panoda değerli ama bizde olmayan ana bloklar** (DURUM.md ile uyumlu): Karne (radar), Koç/dersler + "ne olurdu", Öğrenme kaydı, aylık Rapor sayfası, dönemsel getiri (yazıcı eksik), Risk (korelasyon, kaldıraç düşüş olasılığı, eşikli yoğunlaşma uyarısı), kıyas serileri, işlem açıklaması çekmecesi, araştırma/keşif (huni) ekranı.

---

## 2. Özellik envanteri

Gösterim: **Mevcut** = var / kısmen / yok. **Hesap** = nerede yapılmalı.

### 2A. Kağıt Hesaplar panosu (swing-sg/karsilastirma + ekran görüntüleri)

**F01 — Özet KPI şeridi + hesap kartları** (s01-s02; `panel/index.html kartlar()`)
- Ne yapıyor: Toplam değer, toplam getiri, son gün, açık pozisyon, kapanan·kazanma; her hesap için kart: mini eğri, maks. düşüş, kazanma, PF, kapanan/açık, "düşüş süresi" (en uzun/şimdiki), "şans dışılık (PSR)", son çalışma, beklenti bölgesi etiketi (normal/dikkat/alarm).
- Veri: özsermaye geçmişi, işlemler, koni bölgesi, bot sağlığı.
- Mevcut: **kısmen** (şerit, strateji satırı, mini eğri, beklenti çipi var; düşüş süresi ve PSR yok).
- Hesap: motor (düşüş süresi, PSR).
- Not: PSR `panel_veri.ek_metrikler`: Bailey-López de Prado formülü, ≥10 günde hesaplıyor; 10 günle anlamsız. Motorda zaten `saglamlik.deflated_sharpe` var, onunla tutarlı yazılmalı; ≥60 günden önce "veri birikiyor".

**F02 — Alarm şeritleri** (s01; `panel_veri.alarmlar`)
- Ne yapıyor: Bot gecikmesi (>2,5x beklenen sıklık), beklenti bandı altı, işlem −2R veya daha kötü (stoptan kötü çıkış), aynı varlıkta ≥3 hesap/≥1000 $, panel verisi >3 saat bayat.
- Mevcut: **var** (`uyarilar()`: bayatlık, kill/günlük limit, beklenti alarmı). Eksik: "stoptan kötü çıkış (R ≤ −2)" ve yoğunlaşma alarmı.
- Hesap: motor (alarm listesi), pano biçimler.

**F03 — "Son 24 saat" cümlesi + olay çipleri** (s01; `panel_veri.olaylar`)
- Ne yapıyor: "2 pozisyon açıldı, 3 işlem kapandı (toplam −43 $). En iyisi …, en kötüsü …" + açıldı/kapandı çipleri. Aynı varlığın alt hesap tekrarlarını tek olay sayar.
- Mevcut: **kısmen** (`icgoruler.json` cümleleri; çip listesi yok).
- Hesap: motor.

**F04 — Karne (radar), 6 not + genel puan** (s03-s04; `karneHesap`)
- Ne yapıyor: Her hesap için 0-10 notlar: **Getiri** = canlı getirinin backtest Monte Carlo konisindeki yüzdelik dilimi/10; **Risk** = 10 + maksDD·100/2 (−%20 = 0); **Beklenti** = 5 + ortR·10 (0R=5, +0,5R=10); **Şans dışılık** = PSR·10; **Deneyim** = 5·min(1,kapanan/30) + 5·min(1,gün/60); **Çeşitlendirme** = 10 − (ort|korelasyon| − 0,3)·20. Genel = mevcut notların ortalaması ×10; deneyim <5 ise "veri birikiyor". Kazanma oranı bilinçli olarak yok.
- Veri: koni (backtest), özsermaye, işlem R'leri, hesaplar arası korelasyon.
- Mevcut: **var (öncelik 6, 2026-11-08)**: `karne.json` (6 eksen; eşikler projenin kendi kuralları, eski eşikler kullanılmaz); pano radar çizer, yalnız bilgi.
- Hesap: motor (`karne.json`); pano radar çizer.
- Risk/not: (1) eksik notlar ortalamadan düşüyor → hesaplar arası puanlar karşılaştırılamaz (veri azken puan şişer); (2) ağırlıklar keyfi, tek sayı Goodhart riski; karne **seçim/eleme ölçütü olarak kullanılmamalı** (karar 13/24 kapıları var); (3) bizde "hesap" yerine 7 strateji (evren geçişinde ≤3/ajan); (4) Codex sürümü farklı formül kullanıyor (backtest özetinden), yani "karne" tek bir tanım değil. strateji-test-pano'daki 100/100 puanlar elle yazılmış.

**F05 — Getiri karşılaştırması + kıyas serileri** (s05; `kiyas()`)
- Ne yapıyor: Hesap eğrileri (% getiri) + onay kutularıyla Bitcoin, Nasdaq 100, S&P 500, BIST 100, mevduat (%1,2/ay) çizgileri; ortak başlangıç tarihi.
- Veri: kıyas fiyat serileri (eskiden ayrı Actions işi `kiyas-durum` dalı).
- Mevcut: **yok** (özsermaye eğrisi var, kıyas yok).
- Hesap: motor (`kiyas.json`: aynı başlangıçta normalize % seri; BTC, DK_SPX, altın, "al-tut sepeti" elimizde).
- Not: al-tut kıyası bizde kritik (portföy Sharpe ~1.1 al-tut ≈ Mag7 boğası); kıyassız getiri yorumu yanıltır.

**F06 — Sermaye + beklenti konisi (Monte Carlo)** (s05; `koni.py`)
- Ne yapıyor: Her hesabın backtest günlük getirilerinden (2023+) **5 günlük blok bootstrap, 3000 yol**, gün 0..62 için %5/%25/%50/%75/%95 birikimli getiri bandı; canlı eğri bandın içinde mi? Bölge: ≥%25 normal, %5-25 dikkat, <%5 alarm (veya DD ≤ beklenen DD). Kısa ufuk için bant, normal yaklaşım (µg ± zσ√g) ile ad hoc genişletiliyor (backtest kârı çıkış gününe yazdığı için yapay dar çıkıyor).
- Mevcut: **kısmen**: `beklenti_araliklari.csv` (4/8 hafta p05..p95, alarm eşiği) ve strateji/set başına `bant` çipi var; **gün gün koni grafiği yok**.
- Hesap: motor (`motor/arastirma/beklenti.py blok_bootstrap` zaten var; gün bazlı yüzdelik serisi `beklenti_koni.json` olarak yazılır).
- Risk/not: Bootstrap iid-blok varsayımı, 2020-25 boğa ağırlıklı geçmiş → bant iyimser; DURUM'daki "kilit testinde seçim yönteminin öngörü gücü zayıf" uyarısıyla birlikte gösterilmeli. Ad hoc genişletme bizde kullanılmamalı; dürüst yöntem: günlük MTM seri + blok bootstrap.

**F07 — Zirveden düşüş (su altı) grafiği** (s05; `ek_metrikler.su_alti`)
- Mevcut: **var** (`dusus_serisi`, zirveden düşüş grafiği). Eksik: "en uzun düşüş süresi (gün)".
- Hesap: motor.

**F08 — Takvim** (s06-s07; `takvim()`, `poz_gunsonu`)
- Ne yapıyor: Aylık ısı haritası (günlük $ değişim = kapanan işlem + açık pozisyon değerlemesi), hafta toplamları, ay özeti (en iyi/kötü gün, yeşil gün). Güne tıklayınca: kapanan işlemler + **gün sonunda açık pozisyonların günlük değişimi** (her çalışmada günün anlık görüntüsü saklanıyor, ardışık iki günün farkı alınıyor).
- Mevcut: **var** (günlük K/Z ısı haritası, gün seç → kapanan işlemler). Eksik: hafta toplamı (bilinçli: pano toplamaz → motor yazmalı), gün sonu açık pozisyon değişimi, İstanbul günü kesimi (bizde UTC günü).
- Hesap: motor (`gunluk_kz` zaten motor; haftalık toplam + `acik_pozisyon_gun_sonu` ekle).

**F09 — Açık pozisyonlar** (s08-s10)
- Ne yapıyor: Para nerede (hesaba göre / varlık sınıfına göre halka), pozisyon başına anlık K/Z çubukları, tam tablo (giriş, süre, stop, tutar, K/Z, R, stopa uzaklık), **bekleyen emirler** (sinyal, limit, stop, stop mesafesi).
- Mevcut: **var/kısmen** (pozisyon tablosu, K/Z çubukları, sembol başına para dağılımı, maruziyet kartları, bekleyen emirler için yer ayrılmış ama motor yazmıyor).
- Hesap: motor (`bekleyen_emirler[]`; "stopa uzaklık %" `maruziyet.pozisyonlar` içinde yazılabilir).

**F10 — İşlem geçmişi** (s11): hesap/sonuç filtresi, arama, kısmi satırların ana işleme birleştirilmesi (`kismi_birlestir`), çıkış nedeni. Mevcut: **var** (filtre, sıralama, "daha fazla"). Not: kısmi çıkış birleştirme bizde stratejiye bağlı; `islemler.jsonl` sözleşmesinde "kısmi" alanı yok (kısmi kâr alan çıkış modülleri açıldıkça gerekecek).

**F11 — İstatistik** (s12): net K/Z, işlem, kazanma, PF, ort. kazanç/kayıp, kazanç/kayıp oranı, işlem başı beklenti, **SQN** (√min(n,100)·ortR/sdR; <1,6 zayıf, <2 ort., <3 iyi), **Kelly** (w − (1−w)/payoff), en uzun seri, tutma süresi, yeşil gün, en iyi/kötü gün, Sharpe (günlük·√365, ≥10 gün), Sortino; strateji bazlı birikimli K/Z eğrisi, varlık bazlı K/Z çubukları.
- Mevcut: **kısmen** (görüntüleyici var, motor yazmıyor — Bölüm 1).
- Hesap: motor.
- Risk/not: **Kelly pozisyon büyütme önerisine dönüşmemeli** (sert limitler kodda; bizde "çeyrek Kelly" yalnız bilgi). Küçük örneklemde (n<30) SQN/Kelly/PF gizlenmeli ("veri birikiyor"); Codex sürümü zaten böyle yapıyor. Sharpe için ≥10 gün çok az; ≥60 gün.

**F12 — Dağılım/kırılım tabloları** (s12-s13): R histogramı (10 kova), tutma süresi–R saçılımı, alış/satış kırılımı, gün (Pzt..Paz) ve saat (TSİ) performansı, R dağılımı ve en uzun kayıp serisi hesap bazında.
- Mevcut: **yok**.
- Hesap: motor (`dagilim.json`) — histogram kovaları ve gün/saat tabloları ham işlem listesinden toplamdır, pano toplarsa "hesap" sayılır.
- Not: gün/saat tablosu post-hoc alt grup; çoklu test yanılsaması (7×24 hücre). Yalnız bilgi.

**F13 — Strateji kırılımı + çıkış nedenleri** (s13): hesap/strateji başına kapanan, kazanma, ort. R, K/Z, açık; "veri birikiyor (n/8)" etiketi; çıkış nedeni başına işlem/pay/K/Z (stop, iz stop, başabaş stop, hedef, süre, sinyal, gün sonu).
- Mevcut: **kısmen** (strateji tablosu var; `cikis_nedenleri` ve `ajanlar` yazıcı eksik).
- Hesap: motor.

**F14 — Koç: öncelikli bulgular** (s13-s14; `kocBulgular()`)
- Ne yapıyor: Sabit kontroller + iki-oran z-testi, dolar etkisine göre sıralı, "düşük/orta/yüksek istatistiksel güven" etiketli: kayıpların stoplardan gelmesi; stoptan kötü çıkış (R < −1,25: kayma/boşluk); tek varlıkta kayıp yoğunlaşması (≥%30 pay); zayıf 4 saatlik açılış bloğu (z-test); alış/satış yönü farkı; kaybedenler kazananlardan >1,5x uzun tutuluyor; beklenti konisi altı; bot gecikmesi; iki hesabın korelasyonu >0,7; en güçlü strateji. Her olumsuz bulgu: "test süresince kural değişmez, değerlendirilir."
- Mevcut: **var (öncelik 6, 2026-11-08)**: `koc.json` (kurallı tespitler, Bonferroni, risk büyütme önermez). `icgoruler.json` basit cümleler ayrıca var.
- Hesap: motor (`koc.json`), pano kart basar.
- Risk/not: Çok sayıda kontrol × strateji × saat bloğu → **çoklu test**; "en kötü saat bloğu" max-z ile seçiliyor (seçim yanlılığı); güven etiketi Bonferroni'siz. Bulgular **bilgi**, karar değil (karar 4: değişiklik → walk-forward → kullanıcı onayı). Eşikler (1,25R, %30, 1,5x) elle seçilmiş.

**F15 — Dersler: canlı sonuç ↔ backtest beklentisi** (s14; `panel_veri.dersler`)
- Ne yapıyor: Strateji başına (≥8 işlem) canlı kazanma oranını backtest oranıyla **binom testi** (p<0,05) ve ort. R'yi t-testiyle (z<−2) karşılaştırır; kayıp serisi nadirliği (qⁿ·n<0,05); stop oranı >%60; 4 saatlik saat kümelenmesi (binom). Beklentiler `STRATEJI_BEKLENTI` sözlüğünde **elle**.
- Mevcut: **yok** (yalnız bant çipi).
- Hesap: motor. Beklenti verisi bizde otomatik: `sonuclar/final/beklenti_araliklari.csv` (kazanma oranı, işlem sayısı, net, DD; strateji başına). Elle sözlük gerekmez.
- Not: **En değerli "koç" parçası**: paper'ın asıl amacı (beklenti aralığıyla karşılaştırma) ile birebir örtüşür. Tek taraflı testlerin çokluğu için düzeltme eklenmeli.

**F16 — "Ne olurdu?" strateji çıkarma simülatörü** (s14; `simulator()`)
- Ne yapıyor: Kapanmış işlemleri strateji başına gruplar; onay kutusu kapatılan stratejilerin K/Z'sini toplam birikimli eğriden çıkarır ("tümü −328 $ / seçili −15 $"). Basit çıkarma; açık pozisyon dahil değil.
- Mevcut: **yok**.
- Hesap: **motor**, ve interaktif toplama yerine **statik tablo**: "strateji X olmasaydı: net, maks. DD, işlem sayısı" (ilkeye uygun; JS toplaması "pano hesabı" sayılır).
- Risk/not: (1) Bizde stratejiler ortak limitleri paylaşıyor (günlük %3, 3x, portföy %5 bütçe, kill switch) → bir stratejiyi çıkarınca diğerlerinin dolumları/reddedilenleri değişir; basit çıkarma yaklaşık, **tam karşı-olgu için motorun yeniden oynatması** gerekir. (2) Geriye dönük "kaybedeni at" = klasik aşırı uyum; seçim aracı olarak **kullanılmamalı**, yalnız anlama aracı. (3) Eleme kararı karar 13/24 ve walk-forward üzerinden verilir.

**F17 — Öğrenme (gölge mod)** (s15; `ogrenme()`)
- Ne yapıyor: Her kapanan işlem için aynı strateji+yöndeki **önceki kapanan** işlemlerin R toplamından büzülmeli tahmin: `tahmin = ΣR / (n + 5)`; n ≥ 5 ve tahmin < −0,2R ise gölge filtre "atla". Gerçek sonuç ↔ gölge filtreli sonuç, atlanan işlem sayısı, "atlamalarda isabet" (atlanan işlem gerçekten R<0 muydu). Bot kararlarını **değiştirmez**.
- Mevcut: **yok**.
- Hesap: motor (ileriye dönük kayıt olarak: tahmin giriş anında yazılır).
- Risk/not: **ML değil**, kayan ortalama. Lookahead riski var: sıralama **kapanış zamanına** göre; "önceki işlemler" arasında bu işlemin girişinden sonra kapanmış olanlar da giriş filtresi simülasyonunda kullanılabiliyor (giriş zamanı < kapanış sırası). Giriş anı filtresi için yalnız `cikis_zamani <= bu işlemin giris_zamani` olan işlemler kullanılmalı. Eşik (−0,2R), büzülme (K=5), min n (5) elle, OOS'suz. Ekran görüntüsünde isabet **%43** (yazı-tura altı) ve atlanan 7 işlem: kanıt yok. Ayrıca ekranda gösterilen "+74 $ tasarruf" aynı örneklemde ölçülmüş. Karar 4 ile uyumlu kullanım: yalnız gölge günlük; canlıya bağlanmaz, Aşama 5'te walk-forward + kullanıcı onayı ister.

**F18 — Aylık performans raporu** (s16; `rapor()`)
- Ne yapıyor: Ay seçici; KPI (toplam değer, getiri, ay kapanan, kazanma, en kötü hesap düşüşü); hesap tablosu: ay getirisi, toplam, maks DD, kapanan, karne, ve **kabul kontrol listesi** (30+ işlem, 60+ gün, DD<%10, koni içinde, PSR>%95); kümülatif getiri eğrisi + BTC/S&P/mevduat; koçun ilk 5 bulgusu; Yazdır/PDF.
- Mevcut: **kısmen** (Yazdır düğmesi + yazdırma CSS'i; aylık sayfa ve kontrol listesi yok).
- Hesap: motor (`aylik_rapor.json`, ay başına); pano biçimler.
- Not: Aşama 4 kabul ölçütü ("kesintisiz çalışma + sonuçların beklenti aralığında olması", ≥8 hafta, en erken 2027-01-02) için hazır "paper kabul kontrol listesi" olarak çok değerli. Eşikler bizim kapılara göre yeniden tanımlanmalı (DD ≤ %20 karar 24, beklenti bandı, sağlık). PSR>%95 yerine DSR/benzeri (deneme sayısı yüksek).

**F19 — Dönemsel getiri matrisi** (s17): günlük/haftalık/aylık × hesap, yeşil-kırmızı ısı hücreleri.
- Mevcut: **kısmen** (günlük gün×stil matrisi için pano kodu hazır; `gunluk_kz_ajan` motor yazmıyor; haftalık/aylık yok).
- Hesap: motor (üç ayrı seri yazılmalı). Not: DURUM Aşama 4 notu (d): hafta sonu paydası tutarsızlığı çözülmeden portföy kolu günlük getirisi yanıltabilir.

**F20 — Risk: aynı varlıkta yoğunlaşma** (s17; `maruziyet`)
- Ne yapıyor: Tüm hesapların açık pozisyon + bekleyen emirleri varlık bazında toplar; ≥3 hesap veya >1.000 $ → "yoğunlaşma". Net (yön işaretli) ve brüt tutar.
- Mevcut: **kısmen** (`_yogunlasma`: sembol başına stratejiler, brüt/net, kasaya oran; eşikli uyarı yok).
- Hesap: motor (`yogunlasma_durumu` alanı; eşik değeri kodda, pano yalnız etiketler). Eşik bizde kasa oranına göre (örn. brüt ≥ %X) ve "kaç strateji" olmalı; $1000 sabiti 10k hesaba göreydi.

**F21 — Risk: kaldıraçla düşüş olasılığı** (s17; `koni.py ruin`)
- Ne yapıyor: Blok bootstrap ile 60 gün ve 1 yılda hesabın zirveden −%10/−%20/−%30 görme olasılığı, 1x/2x/3x kaldıraç için.
- Mevcut: **yok**.
- Hesap: motor (`risk_olasilik.json`).
- Not: Bizde kaldıraç 3x tavan ve %20 kill switch sabit → anlamlı çıktı: "8 hafta/1 yılda kill switch (%20) ve günlük %3 limitine değme olasılığı" (sert limitlerin işlem sonrası simülasyonu). Bootstrap iyimserlik uyarısıyla (boğa geçmişi) gösterilmeli.

**F22 — Risk: hesaplar birlikte mi hareket ediyor (korelasyon)** (s17; `korelasyon`)
- Ne yapıyor: Hesapların günlük getiri korelasyon matrisi; ≥10 ortak gün şartı; >0,7 koç uyarısı, ≥0,6 kırmızı hücre; karnedeki çeşitlendirme notuna giriyor.
- Mevcut: **yok** (DURUM: portföy düzeyinde korelasyon izlemesi şart demişti: "bant dönüşü/konsolidasyon kırılımı/stokastik üç stilde birden").
- Hesap: motor (`korelasyon.json`). 
- Not: 10 gün çok gürültülü → ≥30 gün ve güven aralığı; Codex önerisi: ortak zarar ve ortak düşüş korelasyonu (aynı anda zarar etme), korelasyon kümeleri.

**F23 — İşlem açıklaması çekmecesi** (`aciklama()`, `STR`, `CIK`)
- Ne yapıyor: İşlem satırına tıklayınca "Neden açtı? Neden kapattı? Değerlendirme": her strateji için sabit kural metni, çıkış nedeni sözlüğü, R'ye göre yorum ("planlanan zarar, tek başına hata değil"). Kodda itiraf: "botlar işlem anındaki gösterge değerlerini kaydetmediği için kuralın genel hâli anlatılıyor."
- Mevcut: **var (öncelik 6, 2026-11-08)**: İŞLEMLER satırına tıklayınca çekmece (giriş gerekçesi, ayar sürümü, giriş/çıkış, R, çıkış nedeni, MFE/MAE).
- Hesap: motor kaydı (giriş anında sinyal değerleri/gerekçe + çıkış gerekçesi `islemler.jsonl`'a eklenir); kural metni kart/aileler.json'dan. Pano yalnız biçim.
- Not: Gösterge değerlerini girişte kaydetmek, ileride "paper ↔ backtest işlem eşlemesi"ni de kolaylaştırır.

**F24 — "Claude'a sor" kutusu / Claude Danışman** (`sor()`, strateji-test-pano `askAI`)
- Ne yapıyor: Panel verisinden JSON bağlamı kurup claude.ai artifact `sample` API'siyle Türkçe kısa cevap (günlük 10 soru sınırı). strateji-test-pano'daki sürümde cevaplar `setTimeout` ile **hazır metin** (gerçek analiz değil).
- Mevcut: **yok**.
- Hesap: LLM, pano değil. Karar 3: LLM ≥15 dk aralıkla üst seviyede (Aşama 5) → pano değil `yorum.json` (lider ajan yazar). Canlı LLM çağrısı panoda **önerilmez** (platform bağımlılığı + sert limit dışında bir kanal).

**F25 — Bot sağlığı** (s01 kartlarda "son çalışma", alarm): Mevcut **var** (SAĞLIK sekmesi, bayatlık, servis, uyarılar) ve daha ayrıntılı.

**F26 — TRY karşılığı + kur** (strateji-test-pano, `usdtry()`): toplam değer ₺. Mevcut yok; değer düşük. Hesap: motor (kur bilgisi veri katmanından), düşük öncelik.

### 2B. strateji-test-pano'ya özgü

**F27 — Strateji kataloğu / detay modalı (27 lider strateji)**: PDF kaynağı, MTF, gösterge formülleri, yön filtresi, giriş/çıkış/stop-ratchet metni, "argon notu". Mevcut: **kısmen** (strateji satırında ayar + beklenti; kural metni yok). Hesap: yok (kart/ayar metadatasından biçim). Not: strateji metinlerindeki "PF 3.60+", "p<0.006" gibi iddialar kanıtsız.

**F28 — Manuel "Yeni paper trade ekle" + JSON dışa/içe aktarım + PC/mobil senkron** (`handleNewTrade`, `exportJSON`): Mevcut yok. **Önerilmez**: pano yazmaz (motorla pano farklı sayı göstermesin); elle işlem paper bütünlüğünü bozar.

**F29 — `bot_engine.py` saatlik MTM güncelleyici**: yalnız crypto fiyatı çekip K/Z yazar; stop/boyut varsayılanları uydurma. Mevcut paper motoru bunu çok aşıyor. **Yeniden kullanım yok.**

**F30 — "SMC + Lorentzian ML" stratejisi (V1B / L08)**: bkz. Bölüm 3; ML değil, el yapımı skor. Pano özelliği değil, strateji. Karar: tescilli/ML elendi (DURUM, Aşama 0 listesi); kuralı kodlanabilir bir gösterge skoruysa kitap/GitHub kuyruğu ayrı değerlendirir.

### 2C. sg-pano (copy trade) — bizim için fikir değeri

**F31 — Huni + Keşif/aday kartları**: havuz → aday → oda sayıları; son tarama (evren, işlenen, kapsam, "eksik koşu" uyarısı); aday kartlarında **8 adımlı kapı** (her adım: Geçti/Yetersiz/Elendi + neden), katman (kopyalanabilir/izleme adayı), "genç aday" etiketi, piyasa payı süzgeçleri.
- Mevcut: **yok**. Bizde karşılığı: araştırma hunisi (~700 aday → geniş tarama → walk-forward karar 13 → sağlamlık/PBO/DSR → holdout → final/paper) ve strateji başına "hangi kapıda elendi ve neden" kartı; "yeni strateji araştırma/keşif ekranı" bu.
- Veri: `sonuclar/{tarama,wf,saglamlik,secim,evren}/…csv`, `stratejiler/aileler.json`, `sonuclar/deneme_kaydi.jsonl`.
- Hesap: motor/araştırma tarafı (`huni.json` yazıcı); pano yalnız tablo.
- Not: Deneme sayısı (DSR) ve "Bonferroni'yi hiçbiri geçmiyor" uyarısı ekranda görünmeli; ekran **seçim için OOS gösterip çoklu test yanılgısına** yol açmamalı; holdout/kilit verisi hiç görünmemeli (karar 20). Ağır evren testi (sunucuda koşuyor) bitmeden anlamlı veri yok.

**F32 — "Kararlarım değer kattı mı?" (Açtım/Atladım, atlama nedenleri, sanal sonuç)**: Telegram düğmeleriyle kullanıcı kararı kaydı; açtıklarım ↔ tümü karşılaştırması; oda değişimlerinin "değişim alfası".
- Mevcut: **yok**, bizde otonom paper var. Karşılığı: **lider değişiklik önerisi günlüğü** (karar 4/26): öneri, walk-forward sonucu, kullanıcı kararı (onay/ret), sonrası paper etkisi. Aşama 5 işi; düşük öncelik. Hesap: lider ajan/motor kaydı.

**F33 — Performans körlüğü (ön kayıt), veri tazeliği satırları, "?" sözlük ipuçları, tutar hesaplayıcı**:
- Körlük: ofiste kâr/zarar "kilitli (hafta x/12)" gösterilmiyordu → erken yorum (peeking) engellenirdi. Bizde pano sonuç gösteriyor; öneri: n/gün yetersizken "veri birikiyor" etiketi (eski Kağıt Hesaplar'da vardı). Mevcut: **kısmen** (beklenti penceresi dolana kadar alarm yok).
- Veri tazeliği: **var** (bayat bant, TSİ).
- Sözlük: **var** (SAĞLIK → Sözlük). Satır içi "?" ipuçları yok (kullanıcı trading'de orta: değer var, düşük efor).
- Tutar hesaplayıcı (bütçe → işlem başına $): **yok**; Aşama 6 (küçük bütçe) için "X $ olsaydı" ölçekleme; hesap motor (`olcek`), düşük öncelik.

**F34 — Animasyonlu izometrik ofis**: Dekoratif. **Önerilmez** (büyük efor, GPL-3.0 kökenli kod/varlık: kopyalanırsa lisans yükü; yalnız tasarım fikri alınabilir). Ürettiği tek değerli fikir: olay → görsel eşlemesi ve oda başına bayatlık (sis).

**F35 — Mutabakat sağlığı / trader ışıkları / kırmızı bayrak**: Yetim pozisyon, kaçırılmış dolum, pozisyon farkı, hesap değeri sıçraması → yalnız uyarı. Bizde Aşama 6 (gerçek emir) mutabakatı için gerekecek; şimdilik paper'da gerek yok.

### 2D. Codex `DASHBOARD_PARITY.md` ek fikirleri (hiçbiri uygulanmamış)

| # | Fikir | Mevcut | Hesap | Not |
|---|---|---|---|---|
| F36 | Veri güveni kartı (kapsam başlangıcı, son bar, eksik bar, kaynak, SHA-256, gecikme) | kısmen (SAĞLIK: son mum, bayatlık; sha256/kapsam yok) | motor/veri katmanı (sha256 zaten indirme aşamasında) | düşük efor |
| F37 | Backtest bütünlük kartı (sonraki bar uygulama, maliyet, OOS oranı, maliyet stresi, lookahead testleri geçti/kaldı) | yok | motor (statik JSON, test sonuçlarından) | düşük efor, güven değeri yüksek |
| F38 | Piyasa × strateji uygunluk matrisi | kısmen (strateji × enstrüman katkı matrisi için pano hazır, motor yok) | motor | evren testi sonrası |
| F39 | Beklenti sapması (getiri dışında işlem sıklığı, ort. R, maliyet, DD ayrı ayrı) | kısmen (net/DD bandı var) | motor | F15 ile birleşir |
| F40 | Sürüm ve denetim izi (her işlemde strateji sürümü + parametre özeti + veri zamanı) | yok | motor (`islemler.jsonl` alanı) | ayar yenilemeleri (180/90 gün) için önemli: eski/yeni ayar sonuçları karışmasın |
| F41 | Marjinal risk katkısı + korelasyon kümeleri | yok | motor | portföy kolu + tek-grafik ortak risk; orta efor |
| F42 | Rejim haritası (trend/yatay, vol, risk-on/off) | yok | motor | rejim etiketi **önceden tanımlı** olmalı (işlem sonrası optimize etme) |
| F43 | Champion-challenger gölge testi | yok | motor/Aşama 5 | karar 4 ile uyumlu (aday paper'a dokunmaz); önceden yazılı terfi eşiği |
| F44 | Maliyet kırılma noktası (maliyet kaç kat olunca avantaj sıfır) | kısmen (maliyet dökümü + sağlamlıkta ×2 stres) | motor | backtest tarafında zaten ×2 var |
| F45 | Alarm gelen kutusu (ilk/son görülme, çözüldü, tekrar yok) | yok | motor/telegram | Telegram spam'ine karşı faydalı |

---

## 3. Makine öğrenmesi kısımları (derinlemesine)

Pano kodlarında **canlı ML yok**; ML şu yerlerde geçiyor:

**3.1 "Lorentzian ML / SMC ML olasılık kapısı" (strateji-test-pano V1B, L08)** — `index.html`/`data.json`, "Öğrenme (Gölge Mod & Lorentzian k-NN)" ekranı
- Ne tahmin ediyor: Aslında **hiçbir şey öğrenmiyor/tahmin etmiyor**. "4 boyutlu k-NN özellik skoru" = elle yazılmış toplam: `(RSI14−45)/20 + (Close>EMA34 ? 0,9 : −0,9) + (+DI>−DI ? 0,6 : −0,6) + (EMA13>EMA34 ? 0,5 : −0,5)`; giriş eşiği ≥1,10 (+ RSI≥46), çıkış ≤ −0,7 (veya ≤ −1,1). Eğitim, komşu arama, hedef değişken yok.
- Özellikler: RSI(14), EMA34'e göre konum, ±DI, EMA13/EMA34.
- Eğitim: yok. Parametreler (1,1, −0,7, 46, ±0,9/0,6/0,5) elle; "Lorentzian aşırı uyumu önler" iddiası kanıtsız.
- Lookahead: göstergeler kapanmış muma göre; ayrıca "Bullish FVG = Low > High[2]·0,99" geçmişe bakıyor. Doğrudan lookahead görünmüyor; ama "PF 3,60+ NVDA/AAPL/META" sonuçları elle girilmiş veri, doğrulanamaz (Mag7 boğası, tek yönlü).
- Sonuç: ML etiketi yanıltıcı; kuralı (gösterge skoru eşiği) bir strateji olarak aileler.json'da başka kartlar gibi test edilebilir. Aşırı uyum riski: 6+ elle seçilmiş eşik, OOS kaydı yok.

**3.2 Gölge öğrenme filtresi (swing-sg panel `ogrenme()`, Codex "gölge mod")**
- Tahmin: bir sonraki işlemin R'sinin ortalaması (aynı strateji+yön), büzülmeli ortalama `ΣR/(n+5)`; karar kuralı: <−0,2R → "atla". İstatistiksel öğrenme (shrinkage), ML değil. Özellik yok (yalnız strateji+yön geçmişi).
- Lookahead: bkz. F17 (kapanış sırası ↔ giriş anı). Ekran görüntüsündeki isabet %43.
- Hedef: sinyali filtrelemek için pano değil motor kararı; karar 4 gereği canlıya otomatik bağlanmaz.

**3.3 LightGBM meta-etiketleme (swing-sg `deneyler/meta_etiket.py`)** — sonucu `karsilastirma/EKIP.md`'de
- Ne tahmin ediyor: Swing sinyalinin (S1/S2/S3) **kazanıp kazanmayacağını** (ikili hedef R>0), sinyal gününde (girişten önceki kapanış) bilinenlerle.
- Özellikler (14+3): atr_pct, rsi14, rsi2, d_ema20/d_ema50/d_sma200, mom20/mom60, hacim/SMA20, vol_oran (ATR5/ATR50), endeks mom20 ve SMA50 uzaklığı, hafta mom5, haftanın günü, strateji kodu, sınıf kodu, stop mesafesi.
- Eğitim: IS 2015-2022; IS içi yürüyen doğrulama (her yıl 2018-2022, öncesiyle eğit, 35 gün arınma); eşik IS yürüyen tahminlerinden (alt %30); final model tüm IS; OOS 2023+ seçimde görülmedi. Hafif model (7 yaprak, min 60 örnek, L2=5, 150 tur).
- Lookahead: özellikler girişten **önceki** kapanışa göre (temiz). Küçük sızıntı: son model "tüm IS"e eğitiliyor; giriş 2022'de olup çıkış 2023+'ya taşan işlemlerin etiketi OOS dönemine bakmış olabilir (30 gün maks. tutma, etkisi küçük).
- **Sonuç: işe yaramadı**: IS puan–kazanç Spearman +0,03; OOS'ta filtre Sharpe 1,45 → 1,26, puana göre boyutlama 1,29. Eklenmedi.

**3.4 QQQ-ML (LightGBM, 11 fiyat özelliği, 5 gün sonrası yön) — `deneyler/codex2_adaylar.py` D1**
- Tahmin: `Close[t+5] > Close[t]` ikili; özellikler: ATR%, SMA10/20/50 uzaklık, 20/55 gün tepe-dip uzaklığı, mom5/mom20, vol10/vol20, sınıf kodu. Yıllık yürüyen eğitim (8 gün arınma), eşik 2019-2022'de seçildi (hedef: en iyi ortalama 5 gün getiri).
- Sonuç: OOS 182 işlem, kazanma %41, PF 0,99, Sharpe 1,45 → 1,19, DD −%22,6; "kazanım yalnızca 2019-22'den geliyor" → RED. Klasik **dönem içi şişkinlik**.

**3.5 backtesting.py kNN ML örneği (BP05 / P7-P8; algo-sg `dis_kaynak/kurallar.py`)**: 1h, ±%0,4, 48 mum ufku, kNN(7), 400 mum, 20 mumda yeniden eğitim. Orijinal örnekte son 48 mumun **gelecek etiketi eğitime giriyordu (lookahead sızıntısı)**; "dürüst sürüm" etiketi bilinmeyen son 48 mumu atıyor. Sonuç elendi (zarar). freqtrade `wtc.py` ve `lookahead_bias/` örnekleri bilerek sızıntılı (sklearn), alınmadı.

**3.6 Diğerleri**: `ai_quant_trade` (A8, A10-A13 faktör ML/RL, A15-A16 NLP/LLM) ve Jansen "ML" kitabı → elendi. Codex "öğrenme" sekmesi ML değil (iskelet).

**ML sonuç özeti / tavsiye**: Dört bağımsız deneme (meta-etiket, QQQ-ML, kNN, gölge filtre) bizim veride kanıt üretmedi; en az iki tanesi OOS'ta kötüleşti. Karar 3/4/5 ve DURUM'daki "ML elendi" ile tutarlı: **pano'ya ML eklenmemeli**, F17 yalnız "ileriye dönük gölge günlük" olarak (lookahead'siz) ve iddiasız. Bir ML denemesi istenirse: (a) ön kayıt (özellik listesi, hedef, eşik kuralı), (b) purge/embargo ile zaman sıralı CV, (c) deneme sayısı DSR'ye eklensin, (d) kilit/holdout bir kez, (e) maliyet ×2. Aşırı uyum riski yüksek: özellik/eşik/ufuk serbestliği çok, örneklem (≈7 stratejinin işlemleri) küçük.

---

## 4. Yasak mantık kontrolü (martingale / DCA / grid)

- Tarama: pano kodlarında (sg-pano, strateji-test-pano, swing-sg panel, codex-algo dashboard) martingale, DCA, grid, ortalama düşürme, katlama mantığı **bulunmadı**.
- Dolaylı riskler:
  - **Kelly** kutusu (F11): pozisyon büyütme önerisine dönüşmemeli (sert limitler koddadır; çeyrek Kelly yalnız bilgi).
  - **Simülatör "stratejiyi ekle/çıkar"** (F16) ve **gölge filtre** (F17): geriye dönük seçim → aşırı uyum; karar aracı olmaz.
  - **Kaldıraç düşüş olasılığı 2x/3x** (F21): 3x tavan zaten kodda; 2x/3x senaryoları bilgi, "kaldıracı artır" önerisi yok.
  - "Güçlü–Zayıf Sepeti" (KMN), "Dipten Sekme" gibi stratejiler strateji tarafında ayrıca denetlenir; pano özelliği değil.
- `STRATEJI_BEKLENTI` el yapımı sözlük, bizde beklenti CSV'sinden otomatik gelmeli (elle tutulan beklenti = sapma/uydurma riski).

## 5. Önerilen öncelik sırası (değer/efor)

**Hemen (yüksek değer, düşük-orta efor, pano kodu zaten hazır):**
1. **Motor yazıcı paketi**: `paper_durum.py` ve `backtest_durum.py` 7 hazır alanı yazsın: `istatistik{}` (F11; n<30'da SQN/Kelly null+neden), `cikis_nedenleri[]` (F13), `gunluk_kz_ajan[]` + haftalık/aylık (F19), `ajanlar[]`, `enstrumanlar[]`, `strateji_enstruman[]` (F13/F38), `bekleyen_emirler[]` (F09). Test: `test_pano.py` "motor yazarsa birebir gösterilir" zaten var. Önce Aşama 4 notları (c)(d) kapatılsın (hafta sonu paydası).
2. **Beklenti/Dersler (F15+F39)** strateji başına: canlı kazanma/R ↔ `beklenti_araliklari.csv` (binom/t, ≥8 işlem, çoklu test düzeltmeli). Paper'ın asıl hedefi bu.
3. **Aylık rapor + paper kabul kontrol listesi (F18)**: 8 hafta değerlendirmesinden (2027-01-02) önce hazır olsun; eşikler bizim kapılar (DD ≤ %20, beklenti bandı, sağlık, kesintisiz çalışma).
4. **Veri güveni + backtest bütünlük + sürüm izi (F36, F37, F40)**: statik/ucuz, güven artırır; `islemler.jsonl`'e ayar sürümü ve giriş gerekçesi alanı (F23 temeli) — ayar yenilemeleri başlamadan eklenmeli.

**Sonra (orta değer/efor):**
5. **Beklenti konisi grafiği + kıyas serileri (F06, F05)**: mevcut `blok_bootstrap` yeniden kullanılır; al-tut/BTC/DK_SPX/altın kıyası.
6. **Risk: korelasyon (≥30 gün) + eşikli yoğunlaşma uyarısı + kill switch/limit olasılığı (F22, F20, F21)**; ortak zarar korelasyonu (F41).
7. **Koç kuralları (F14)** bilgi amaçlı, çoklu test düzeltmeli, "karar değil" ibaresiyle; dağılım/gün-saat tabloları (F12) en sonda.
8. **İşlem açıklaması çekmecesi (F23)**, takvimde gün sonu açık pozisyon değişimi (F08), karne (F04; yeniden tanımlı, eksik not = "veri yok", seçim için kullanılmaz).
9. **Araştırma/keşif hunisi ekranı (F31)**: sunucudaki ağır evren testi (ham → wf → portföy → sağlamlık → pbo → seçim → holdout) bitip çıktılar oturunca; deneme sayısı/DSR uyarısıyla, holdout gizli.

**Aşama 5 ve sonrası / düşük öncelik:**
10. "Ne olurdu" statik tablo (F16), gölge öğrenme günlüğü (F17, lookahead'siz ileriye dönük), lider öneri günlüğü (F32), champion-challenger (F43), rejim haritası (F42), alarm gelen kutusu (F45), TRY/ölçekleme (F26, F33).

**Yapılmamalı:** animasyonlu ofis (F34; GPL, efor), manuel işlem ekleme/JSON senk (F28), canlı "Claude'a sor" kutusu (F24; LLM Aşama 5'te `yorum.json` olarak), `bot_engine.py` (F29), Lorentzian "ML" iddialarını ve elle yazılmış karne/PSR sayılarını (strateji-test-pano) kanıt saymak, ML sinyal filtresi (Bölüm 3).

## 6. Açık sorular / notlar (lider/kullanıcı için)

- Karne (F04) ve "ne olurdu" (F16) için formül/eşik onayı: eski eşikler (30 işlem, 60 gün, DD<%10, PSR>%95) bizim karar 13/24 ile uyuşmuyor; hangi tanım kullanılacak? (Öneri: kabul listesi = paper bitiş ölçütü, karne = yalnız bilgi.)
- PSR/DSR: pano değeri motorda `saglamlik.deflated_sharpe` ile tutarlı üretilmeli; deneme sayısı (787 Haiku + evren testi) DSR'ye eklenmeli (DURUM notu).
- Gün kesimi: eski panoda İstanbul günü, bizde UTC günü (takvim "UTC günü" etiketi var). Telegram/kullanıcı için TSİ günü gerekirse motor yazmalı, pano toplamamalı.
- `arsiv/sg-arge-/` içinde `copytrade/canli/pano.py` yok (yalnız strateji listeleri); DURUM'daki sg-arge pano referansı için o dosya gerekirse kullanıcının eski repo kopyasından alınmalı. Ekran görüntülerinin kodu (swing-sg panel) eksiği büyük ölçüde kapatıyor.
- GPL: sg-pano ve sg-arge GPL-3.0; oradan kod kopyalamak yerine formül/tasarım fikri alınmalı (swing-sg'nin lisansı bu çalışmada incelenmedi).
