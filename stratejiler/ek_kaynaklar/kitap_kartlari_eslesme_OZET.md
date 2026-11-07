# Yeni kitap kartları: mevcut stratejilerle eşleştirme (özet)

Tarih: 2026-11-07. Yalnız eşleştirme yapıldı; kod yazılmadı, strateji eklenmedi, commit edilmedi.
Dosyalar: [kitap_kartlari_eslesme.csv](kitap_kartlari_eslesme.csv) (307 kart + 65 tam okuma kartı = 372 satır; tam okuma bölümü 6'da), [kodlama_kuyrugu_2026-11-07.csv](kodlama_kuyrugu_2026-11-07.csv) (133 yeni aile).
Kapsam: `6abf0cf`, `f817816`, `7ede931` ile eklenen 77 kart dosyası = 307 kart (görevde "~308" denmişti; 307 çıktı). Aşama 0 kartlarına dokunulmadı.

## 1. Durum başına kart sayısı

| Durum | Kart | Anlamı |
|---|---:|---|
| `mevcut:<ad>` | 62 | Çekirdek giriş/çıkış mantığı kodlu, parametre ızgarası kapsıyor (ek filtreler gerekçede belirtildi) |
| `ayar:<ad>` | 83 | Mantık kodlu; kartın parametresi ızgara dışı ya da çıkış/stop farklı, `kart_ayarlari`'na eklenebilir |
| `yeni` | 120 | Kodda karşılığı yok (71 yeni aileye bağlandı; repo satırlarıyla birlikte kuyrukta 133 aile) |
| `kural_yok` | 23 | Kodlanabilirlik 0 ya da öznel / özel gösterge tanımsız / filtre |
| `veri_yok` | 18 | Tik verisi, emir defteri (DOM/Level 2), opsiyon, haber takvimi, TICK/TRIN, float/pre-market, faiz farkı |
| `yasak` | 1 | Düşüşte kademeli alım ekleme (ortalama düşürme) |

Stil kırılımı (kart sayısı, durum): daytrade yeni 55 / ayar 38 / mevcut 31 / kural_yok 13 / veri_yok 7 / yasak 1; swing yeni 39 / ayar 25 / mevcut 24 / kural_yok 3 / veri_yok 2; scalp yeni 26 / ayar 20 / mevcut 7 / kural_yok 7 / veri_yok 9.

`ayar` en çok şu hedeflere gitti: `scalp__ma-kesisim` 9 (MA 3/18, 5/10, 5/12, 9/30 gibi izgara dışı çiftler), `daytrade__orb` 7 (aralık 5/15 dk), `scalp__bant-donus` 7 (Bollinger 50 / RSI 3-7), `daytrade__donchian-kirilim` 5, `swing__ma-kesisim` 5 (10/20, 10/50, 50/200, 50/250).

## 2. Kodlama kuyruğu

133 yeni aile = 71 kitap kartı ailesi + 62 yalnız-repo ailesi. Stil dağılımı (ailenin baskın stili):

| Kaynak | daytrade | swing | scalp | belirsiz | Toplam |
|---|---:|---:|---:|---:|---:|
| Kitap kartı ailesi | 31 | 27 | 13 | 0 | 71 |
| Yalnız repo (`repo_kodlari`/`repo_raporlari`) | 15 | 38 | 3 | 6 | 62 |

Öncelik dağılımı: **A 57, B 40, C 36**.
- Kitap ailelerinde: kodlanabilirlik ≥2 → A (57), 1 → B (14), C yok.
- Repo satırlarında kodlanabilirlik puanı yok (boş bırakıldı, uydurulmadı). Kural: mekanik özet açık (giriş/çıkış okunuyor) → B (26); kural gizli / yalnız sonuç / kural metni yok → C (36).
- Repo `yeni` satırları: `repo_kodlari` 44 + `repo_raporlari` 65 = 109 satır, kuyrukta 62 aileye indi (8 aile kitap kartlarıyla birleşti: ortalamaya-donus-gerilme, bant-kirilim-trend, ma-mukemmel-siralama, hafta-ici-takvim, pmax-giris, hacim-patlama-kirilimi, ma-kanali-momentum, ardisik-bar-devam).
- `yeni__kapali-kaynak-sistemler` tek satırda 30 kaynak toplar (Collective2 kapalı sistemler, "kuralı paylaşılmamış", yalnız sonuç tablosu): kodlanamaz, C.

## 3. Kuralı olmayan satırlar ve Pine araması

`repo_raporlari` içinde `kural_metni_yok` etiketli 31 satır var (TradingView listeleri). Hepsinin adı `arsiv/strateji-sg/tv/pine/` (160 dosya) ve `tv/ham/meta.json` (164 kayıt) içinde arandı:
- Birebir adı eşleşen Pine yok. `meta.json`'da yalnız 4 ad geçiyor (Alpha AI Essential, Scalping Strategy Signal v2, ICT Sessions & Liquidity Sweeps, The Rook Algo PRO) ve dördünün de Pine'ı arşivde yok (kapalı kaynak).
- 2 satıra Pine yolu yazıldı: `JeRCEqWU.pine` (CleanTradeQuantum, kuralı açık, B; `dis_kodlanacak.csv` D1'de görünüyor ama sınıfı yok) ve `f9xLZqpF.pine` (Adaptive Dual-Engine'in forecast eklenmiş TÜREVİ, orijinal değil; çekirdek `dis__ema-macd-ikili` olarak zaten kodlu, C).
- Kalan 29 satır oncelik=C. Adı benzeyen başka betikler arşivde var (ör. "Trendline Break Pro", "Simple Harmonic Pattern"), ama bunlar farklı yazarların farklı betikleri; eşleşme sayılmadı.

## 4. Dikkat notları

1. **Eşleştirme derinliği.** 289 stratejinin sınıf docstring'i + `varsayilan_parametreler` + `parametre_izgarasi` okundu; her sınıfın `sinyaller()` gövdesi satır satır okunmadı (ORB, pairs, RSI-MA, Ema21Sapma gibi tereddütlü olanlar hariç). Çıkarım: "mevcut" etiketi çekirdek kuralın eşleştiği anlamına gelir.
2. **Gevşek eşleşmeler.** 36 `mevcut` kartın kodlanabilirliği 1 (Brooks / Ochoa / Halsey benzeri öznel desenler). Bunlar "yakın kural" eşleşmesidir, birebir değil. Birebirlik şüpheli olup önce kontrol edilmesi gerekenler: seans süpürmesi kartları (Lien Londra açılışı, Algo-konsepti Asya aralığı likidite avı) → `dis__orb-sweep-donus` (seans saatleri parametre ama FX saatleri); Algo-konsepti FVG/order block ve likidite süpürme kartları → `dis__smc-ob-fvg-sweep`; Kılınçarslan SMA+ATR bant → `dis__kelly-atr-bant` (SMA yerine EMA kodlu); Davey MA gerilmesi → `dis__ema21-sapma` (aynı fark); EmperorBTC SFP → `dis__likidite-supurme-gun`; Aldridge saatlik çift spread → `pf__pairs` (yalnız günlük pencere).
3. **Ek filtreler kodlu değil.** Birçok `mevcut/ayar` kartta kitabın ek onayları (MACD/RSI/stokastik teyidi, VWAP yönü, dar aralıklı gün vb.) çekirdek sınıfta yok; gerekçe sütununda "kodlu değil" diye yazıldı. Bu kartlar `kart_ayarlari`'na girse bile onay filtresi eksik kalır.
4. **Tik-bar kartları.** Ultimate Scalper (208, 209, 211, 212, 213) 987-tik barla yazılmış; zaman barına (5m) uyarlanır varsayıldı, `veri_yok` sayılmadı. Leshik-Cralle (tik) kartları `veri_yok`.
5. **FX / seans kartları.** Pip tabanlı stop-hedef ve Londra/Asya seans kartları (Lien, Wallace, Carter) karar 27 evreninde (SPX, XAU, petrol, BTC, XU030; ayrıca hisse/kripto/emtia) pip yerine ATR'ye çevrilmeli. Kriptoda "açılış" yapay (UTC 00:00).
6. **Çok kartlı aileler gevşek birleşti.** `yeni__brooks-h2` (9 kart, çubuk sayımı H1/H2/L2 + kama/ölçülü hareket hedefleri), `yeni__ortalamaya-donus-gerilme` (Davey + Pruitt + 2 repo), `yeni__carter-onayli-trend` (7 çok-göstergeli 5dk sistemi) tek sınıf + `kart_ayarlari` ile kodlanabilir ama içlerinde farklı onay setleri var.
7. **Repo satırları çekirdekte mevcutla örtüşüyor olabilir** (repo etiketi `yeni` ama yakın aile var): `repo_kodlari`: "3 Days Down Overnight" (→ `swing__ardisik-bar-tukenme`), "Pairs Trading with Country ETFs" (→ `pf__pairs` mesafe yöntemi), "Trading Signals Function / OsMA" (→ `scalp__macd-sinyal` hist_donus), "Short-Term Reversal in Stocks" (→ `pf__kesit_ls` skor=donus); `repo_raporlari`: "Trading the Channel" (→ `swing__trend-cizgisi-kanal` regresyon modu), "Codex wd: Günlük Dönüş" (→ `swing__bant-donus` + `dis__ifr2`), "S3 Dipten Sekme" (karar 18 ile alınmamıştı). Kuyrukta `not` sütununda işaretli.
8. **Yasaklar.** Tek `yasak` kart: `daytrade__uclu-kademeli-giris-cikis__duarte` (düşüşte ekleme). Kazanan pozisyona ekleme (piramit, Brooks 117 / Munroe 255) yasak sayılmadı; DCA / ortalama düşürme sayılmaz, ama motorun risk limitleri altında kodlanmalı.
9. **Veri bağımlılıkları.** Endeks serisi gerektirenler (RRS göreceli güç, Rudd "genel piyasa güçlü"), hacim isteyenler (hacim patlaması, VWAP, CMF) enstrüman evreninde hacmi olan varlıklarla sınırlı; XAU/emtia spot'ta hacim güvenilir değil.

## 5. kart_id tekrarı düzeltmesi

Üç tekrar eden `kart_id` hepsi Aşama 0'dan (7b61a10) geliyordu: aynı kitapların iki PDF kopyası. İçerikler birebir aynı değildi (farklı sayfa numaraları ve bazı alanlar), bu yüzden silinmedi, ikincisine kitap soneki eklendi:

| Eski id | Dosya | Yeni id |
|---|---|---|
| `scalp__ha-renk-donusu__heikinashi` | `scalp/Scalping_Eğlencelidir_-_Heikin_Ashi_Trader_22_sayfa.json` | `scalp__ha-renk-donusu__heikinashi__eglencelidir` |
| `scalp__superscalp-vsa__holmes` | `scalp/Gavin_Holmes_Scalp_Stratejisi_24_sayfa.json` | `scalp__superscalp-vsa__holmes__scalp-stratejisi` |
| `scalp__ultra-hacim-seviye__holmes` | `scalp/Gavin_Holmes_Scalp_Stratejisi_24_sayfa.json` | `scalp__ultra-hacim-seviye__holmes__scalp-stratejisi` |

Tutarlılık: `stratejiler/aileler.json` (`scalp__heikin-ashi-donus` ailesinin `kaynak_kartlar`'ına yeni id eklendi) ve `stratejiler/elenenler.json` (iki Holmes kartı için "ikinci kopya" kayıtları eklendi) güncellendi. `kart_ayarlari` bu üç id'ye bağlı değildi. Sonuç: 745 kart, 745 tekil `kart_id`; `python araclar/kart_dogrula.py` eksik zorunlu alan yok.

## 6. Tam okuma kartları (65 kart, `*__tam_*.json`) — 2026-11-07 ikinci tur

Dosyalar: eşleşme satırları [kitap_kartlari_eslesme.csv](kitap_kartlari_eslesme.csv) sonuna eklendi (307 satırdan sonrası); yeni aileler [kodlama_kuyrugu_tam_okuma.csv](kodlama_kuyrugu_tam_okuma.csv) (ana kuyruğa EKLENMEDİ); güncelleme önerileri [tam_okuma_guncelleme_ozet.csv](tam_okuma_guncelleme_ozet.csv) (171 satır).
Kaynak: Brooks Ranges 1/2/3 (19 kart), Brooks Trends 1/2 (19), Farley 1/2 (23, daytrade+swing dizinlerinde), Norden (4). Eşleştirme sırasında kayıtta 449 strateji vardı (d10 kitap + d11f-i github dosyaları dahil); kod okunarak karar verildi.

| Durum | Kart |
|---|---:|
| mevcut | 19 |
| ayar | 10 |
| yeni | 19 (8 aileye bağlandı) |
| cikis_modulu | 5 |
| kural_yok | 4 |
| yasak | 4 |
| veri_yok | 4 |

- **Mevcutla örtüşenler:** Brooks H1/H2 kartları `dis__brooks-h2` (sayi=1/2), kama kartları `dis__brooks-kama`, trend çizgisi kartları `dis__trend-cizgisi-kirilim-retest` ve `trend-cizgisi-kanal`, sahte kırılım / 2B / durulama kartları `sahte-kirilim`, Farley kırılım ikinci şans `kirilim-geri-test`. `dis__brooks-ma-bosluk` yeni kartlara bağlanmadı ama güncelleme önerilerinde hedef (ilk MA boşluğu).
- **Yeni aileler (8, kuyruk dosyasında):** `brooks-limit-fade`, `brooks-limit-geri-cekilme`, `brooks-olculu-hareket-limit` (hepsi A, limit emir ile giriş: `dis__brooks-h2` giriş sinyal mumu kapanışında kodlu, limit mantığı yok), `brooks-dikenli-tel`, `brooks-trend-gunu-isaretleri`, `farley-basarisizligin-basarisizligi` (A), `farley-bosluk-turleri` (4 kart), `brooks-doruk-tukenme` (3 kart) (B).
- **cikis_modulu (5):** `islem-yonetimi-kismi-kar-izleyen-stop`, `trend-yonunde-ekleme-ayri-islem`, `trend-gunu-yonetim-2r-yari-swing-iz`, `stop-sonrasi-yeniden-giris`, `uc-asamali-iz-suren-stop-cikis`. Giriş kuralı yok, strateji değil; çıkış / yönetim modülü olarak `stratejiler/cikis_risk_modulleri.json` ile birlikte düşünülmeli.
- **yasak (4):** `zayif-kanalda-karsi-trend-olcekli-fade` (kaybedene ekleme, koordinatör kuralı) ve Farley'in düşüşte kademeli alım kartları (`taban-sonrasi-geri-cekilme-kademeli-limit`, `fibonacci-kademeli-alim` (38/50/62'de artan boyut), `haftalik-uzaktan-kademeli-giris`). Son üçü kendi kararımdır: ortak stop var ve kitaptaki tek-limit alternatifi (destek kenarına tek emir) yasak değil. KARAR GEREKİR: ya yasak kalır ya "tek limit giriş" varyantı kodlanır.
- **veri_yok (4):** Norden kuyruk pozisyonu, sıçrama sonrası teklif, dolum kontrol listesi, teklif vurma (emir defteri / tik).
- **kural_yok (4):** mıknatısta ikinci ters dönüş, ilk geri çekilme sırası, dik kanalda ilk trend çizgisi kırılımını alma, satış programı.
- **Güncelleme özeti:** 171 satır; `kodlamaya_etkisi` dağılımı: cikis_degisikligi 64, bilgi 54, filtre 36, yeni_parametre 17. Bu sınıflama ANAHTAR KELİME sezgiseliyle yapıldı (elle doğrulanmadı), yalnız ilk filtre olarak kullanın. `hedef_strateji` bir kart_id → strateji haritasından geldi: `dis__brooks-*` ailesi 57 satırla en çok, `kural_yok/veri_yok` hedefli satırlar kodsuz kartlara gelen önerilerdir. Sayfa sütunu rapordan regex ile çıkarıldı, bazı satırlarda boş.
- **Dikkat:** Sınıflar raporlardaki alan adlarını (stop/hedef/filtre) olduğu gibi taşır; Brooks'un E-mini tik/puan değerleri ATR'ye çevrilmeli. Brooks "dar aralıkta stop girişi kaybettirir" çelişkisi (`dar-aralik-kirilim-modu` güncelleme önerisi 4) mevcut `swing__dar-aralik-kirilim` ve `daytrade__konsolidasyon-kirilim` mantığını zayıflatır.

### Ana kuyruğun güncel durumu (133 aile)
Eşleştirmeden sonra `dis__d10*/d11*` ile 133 ailenin 88'i (kitap ailelerinin 69/71'i) kodlandı (aile adı `yeni__x` ↔ strateji `dis__x` eşlemesi). Kodlanmayan kitap aileleri: `yeni__halsey-olculu-hareket` (A), `yeni__bladerunner-ters` (B). Kuyrukta kalan 45 satır büyük oranda C (kapalı kaynak / kural metni yok).

