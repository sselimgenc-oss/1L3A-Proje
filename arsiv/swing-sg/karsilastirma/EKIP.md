# Trading ekibi — görev dağılımı ve denetim

**Koordinatör:** swing-sg oturumu (session_011BRVoXb6shVtKMUVB7Sb5H). Her üye kendi işini yapar; koordinatör
botları her gün denetler, sorun görürse sorumlu oturuma kanıtla birlikte görev gönderir ve düzeltildiğini doğrular.

| Üye (oturum) | Repo | Kağıt hesap | Bot iş akışı | Durum dalı | Kendi haftalık rutini |
|---|---|---|---|---|---|
| Borsa stratejileri (session_01MFgJCiBxPPTFKWmuAWrNtp) | strateji-sg | KGT v3 + KMN, 10.000 $, 09.10 → 09.12 | kagit.yml (saatlik) | kagit-durum | Pzt 08:52 (trig_01XhPohEUR2wmDmNPEeXdAWv) |
| Algoritmik trading (session_01NbbBKnzZPiZMrQMFfihzqF) | algo-sg | A trend kırılımı + B kapitülasyon, 10.000 $, 10.10 → 09.12 | kagit.yml (2 saatte bir) | kagit-durum | kapalı (kullanıcı kararı); izleme koordinatörde |
| Day trading (session_01FYtv9WC1N8AV8qUDBeA4TT) | day-trade-sg | S10 + S13 + S15 kripto, 10.000 $, 11.10 → 10.12 | kagit.yml (günde 2) | kagit-durum | Pzt 08:44 (trig_01C6uRueNnaJBkgw1jcKuK3M) |
| Swing (koordinatör) | swing-sg | S1 + S2 + S3, 10.000 $, 11.10 → 09.12 | kagit.yml (günde 2) | kagit-durum | Pzt 08:47 (tüm hesaplar karşılaştırması dahil) |
| Swing (koordinatör) | swing-sg | Trend kolları, 10.000 $, 12.10 → 10.12 | kagit-trend.yml (günde 1) | kagit-trend-durum | aynı rutin |
| Scalp | scalp-sg | — (oturum artık yok, bot kurulmadı) | — | — | — |

## İletişim kuralı (kullanıcı talimatı, 2026-10-11)
- Üye oturumlar kullanıcıya **doğrudan soru sormaz, onay istemez.** Karar/onay gereken her konu kanıt ve öneriyle
  koordinatöre (session_011BRVoXb6shVtKMUVB7Sb5H) `send_message` ile gönderilir.
- Koordinatör cevaplar; yalnız kendi yetkisini aşan durumlarda (gerçek para, stratejiyi test ortasında değiştirmek,
  botu durdurmak, maliyetli/geri alınamaz adımlar) kullanıcıya sorar.
- Bot hatası düzeltmeleri: üye PR açar → koordinatör inceler ve birleştirir.
- Üyeler geri alınabilir, görev kapsamındaki adımlarda cevap beklemeden ilerler.

## Denetim kuralları
1. **Günlük denetim** (Pzt hariç her gün 09:13 İstanbul): 5 botun son çalıştırması başarılı mı, ozsermaye 30 saatten
   eski mi (`python -m karsilastirma.tum_hesaplar`), açık issue'lara rapor düşüyor mu.
2. **Sorun varsa:** kanıt (çalıştırma kimliği + hata satırı) ve önerilen asgari düzeltmeyle sorumlu oturuma
   `send_message`; ertesi denetimde düzeltildiği doğrulanır. Sorumlu oturum 24 saat içinde düzeltmezse kullanıcıya
   bildirilir. Koordinatör başka repoların koduna kendisi dokunmaz (kullanıcı açıkça istemedikçe).
3. **Strateji kuralları** test süresince değiştirilmez; yalnız bot hataları düzeltilir.
4. **Kaynak tasarrufu:** Claude kullanım limiti ortak. Gereksiz rutinler kapatılır; sorun yoksa denetim tek satırla biter.
5. **Haftalık (Pzt 08:47):** tüm hesapların karşılaştırması swing-sg'de "Tüm kağıt hesaplar — haftalık karşılaştırma"
   issue'suna yazılır.
6. **Aralık başı:** tüm hesapların son değerlendirmesi ve gerçek paraya hangi yapıyla geçileceğine dair öneri.

## Ortak standart (tüm sistemler için asgari doğrulama)
| # | Kural | Strateji | Algo | Day trade | Swing | Trend |
|---|---|---|---|---|---|---|
| 1 | İleriye bakma yok: sinyal kapanışta, işlem sonraki mumda | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 | Gerçekçi maliyet (komisyon + kayma, vadelide fonlama) | ✅ | ✅ | ✅ (spot) | ✅ | ✅ |
| 3 | Parametre seçimi yalnız eğitim döneminde, ayrı test dönemi | ✅ | ✅ | ✅ (70/30) | ✅ | ✅ |
| 4 | Ayı piyasası (2022) dahil uzun dönem | ✅ 2020-26 | ✅ 2020-26 | ⚠️ test edildi: 2022 PF 0,53 (zayıf) → rejim filtresi araştırması | ✅ 2015-26 | ✅ 2015-26 |
| 5 | Hayatta kalma yanlılığı kontrolü | ✅ aylık hacim evreni | ✅ 20 eski coin stres | ✅ 12 çöken coin: etki küçük | ✅ 22 eski coin stres (KO %57, PF 2,5) | ✅ Mag7 hariç test |
| 6 | Kağıt bot: yeniden oynatma, günlük issue raporu | ✅ | ✅ düzeltildi | ✅ | ✅ | ✅ |
| 7 | Haftalık değerlendirme rutini açık | ✅ | ❌ kapalı → **görev** | ✅ | ✅ | ✅ |
| 8 | Durum/ilerleme belgesi güncel | ✅ | ⚠️ PROGRESS eski | ⚠️ PROGRESS eski | ✅ | ✅ |

## Açık görevler
| Tarih | Sorumlu | Görev | Durum |
|---|---|---|---|
| 2026-10-11 | Algo | engine.py:162 tz hatası + PROGRESS.md | tamam: PR #4 birleşti, run 38155359070 başarılı, ozsermaye kesintisiz (koordinatör doğruladı). Haftalık rutin açılmayacak (izleme koordinatörde) |
| 2026-10-11 | Day trade | 2021-01→2023-09 (2022 ayı) ve çöken coinlerle stres testi | tamam: 2021 PF 1,45, **2022 PF 0,53 (−%8)**, 2023 PF 1,06; çöken coin etkisi küçük (docs/kripto_stres.md) |
| 2026-10-11 | Day trade | Rejim filtresi (BTC günlük < SMA200 → yeni alış yok) backtest araştırması | tamam: 2021-23 PF 1,15→1,24, DD −%11,3→−%7,6; 2023-26 PF 1,60→1,66, DD aynı (docs/kripto_rejim.md). **Test sonunda (Aralık) kullanıcıya yeni sürüm olarak önerilecek; bot şimdilik değişmez** |
| 2026-10-11 | Swing (koordinatör) | Swing kripto kısmının çöken/listeden çıkan coinlerle stres testi | tamam: geçti (deneyler/HAYATTA_KALMA.md) |
| 2026-10-11 | Koordinatör | Strateji-sg'deki kopya haftalık rutin kapatıldı (trig_01EP8WD1HQ48TZmUR98qB4a4) | tamam |

Kural: Test süresince kağıt botların parametreleri değiştirilmez. Stres testi kötü çıkarsa bulgu koordinatöre
bildirilir, karar kullanıcıyla birlikte verilir.

- (swing-sg) S4 adayı "gizli boğa uyumsuzluğu" (deneyler/CODEX2_ADAYLAR.md): Aralık sonu değerlendirmesinde S1+S2+S3+S4 olarak sunulacak; test süresince bota eklenmez.

## Kullanıcı paneli (2026-10-12)
- Panel: https://claude.ai/artifact/XCVNapDZJFWbVKq59dGysU (özel, yalnız kullanıcı). Sayfa: `karsilastirma/panel/index.html`.
- Veri: `python -m karsilastirma.panel_veri --cikis <dizin>` beş durum dalını okur → panel veritabanına (hesaplar/, islemler/, meta/ozet) ArtifactData batch ile yazılır.
- Güncelleme: SAATLİK (trig_01QxwwmpqYNBzCG8Fd965fww, her saat :31) yardımcı oturumda: session_012zeiJo3K4ANnisxVVBWBqp (Sonnet, 4 depo bağlı). Eski günde-2 rutini (trig_01FezT5MXSF2eqMa7aisCu7v) kapalı. Yeni alarm (bant dışı, 24 saat sessiz bot, ≤ −2R işlem, 3+ hesapta aynı varlık) → telefon bildirimi + koordinatöre mesaj.
- Panelde: son 24 saat özeti, alarm bandı, normal aralık (beklentinin %90 bandı, Sharpe'tan), varlık yoğunlaşması, korelasyon (10 gün sonra otomatik).
- Bekleyen: ~22 Ekim "Aralık karar kartı" (her hesap için beklentiyle uyum, düşüş, kazanma, istikrar ölçütleri). Ekiplerin dosya biçimi (ozsermaye/islemler/pozisyonlar) değişirse koordinatöre haber verilir.

## Kullanıcıya gösterilen strateji adları (2026-10-12)
Kullanıcıya giden her rapor, panel ve sunumda bu adlar kullanılır; kod adı gerekirse parantez içinde. Botların kodları değişmez.

| Hesap | Kod | Ad |
|---|---|---|
| Swing | S1 / S2 / S3 (aday S4) | Trend Molası / Sıkışma Patlaması / Dipten Sekme (Gizli Güç) |
| Trend kolları | btc_trend / abd_trend / emtia_dusukvol | BTC Pusulası / ABD Güçlüler Sepeti / Sakin Emtialar |
| Strateji | KGT / KMN | Seviye Kırılımı / Güçlü–Zayıf Sepeti |
| Algo | A (A1, A2) / B | Trend Avcısı (4 saatlik, günlük) / Panik Dönüşü |
| Day trade | S10 / S13 / S15 | Akşam Momentumu / Tuzak Kırılım / Trend Günü Molası |

## Koordinatör kararları — gerçek para planı v1 (2026-10-12, kullanıcı kararı koordinatöre devretti)
1. **Sermaye:** gerçek para en fazla 5.000 $; beş hesaba bölünmez. Aralık değerlendirmesinde en iyi 1–2 sisteme verilir.
2. **Kaldıraç:** ilk ay 1x (canlı kayma/dolum kağıtla karşılaştırılır). Canlı sonuç kağıtla uyumluysa 2x. 3x yalnız
   kaldıraç testinde "güvenli en yüksek kaldıraç" ≥ 5 çıkan (dar stoplu) sistemlerde. 5x ve üstü kullanılmaz.
   Swing ve trend kolları en fazla 2x (kripto stop medyanı %13; 5x'te işlemlerin %12'si stoptan önce tasfiye).
3. **Kaldıraç kuralı:** önce işlem başına risk sabitlenir (en fazla %1,5–2), kaldıraç ona göre ayarlanır; izole teminat;
   tasfiye mesafesi stop mesafesinin en az 1,5 katı.
4. **Durdurma kuralı (canlı):** hesap −%15 düşüşe (2x'te −%25) ulaşırsa yeni işlem açılmaz, koordinatör kullanıcıyla değerlendirir.
5. **Short:** Güçlü–Zayıf Sepeti short bacağıyla kalır (kâr iki bacağın farkından). Trend Avcısı için "yalnız ayı
   piyasasında short" (BTC < EMA200) sürümü algo ekibince test ediliyor; iyi çıkarsa Aralık'ta v2 olarak önerilir.
6. **Test sürerken botlar değişmez.** Kaldıraç ve v2 sonuçları Aralık değerlendirmesine girer.

## Açık görevler (2026-10-12)
| Sorumlu | Görev | Çıktı |
|---|---|---|
| Algo | Trend Avcısı v2 (rejime bağlı short) + kaldıraç testi (A, B, A+B) | tamam (algo-sg 37de482): v2 mevcut A'dan kötü → short kuralı aynen kalır. Güvenli L: A 7,2x, B 1,9x. A+B büyütme 2x %31/−29, 3x %38/−40 |
| Strateji | Kaldıraç testi (KGT, KMN, birleşik) | tamam (strateji-sg ffe26bb): güvenli L KGT ~10x; KMN stopsuz → kaldıraçsız kalmalı (1,5x'te bile bozuluyor). En iyisi yalnız KGT 1,5–2x: portföy 1,5x %55/−20,5, 2x %63/−25 |
| Day trade | Kaldıraç testi (S10/S13/S15, SMA200 aday sürüm dahil) | tamam (day-trade-sg e1c9802): güvenli L 5x; büyütme 2x %38/−9, 3x %62/−13 (2023-26); 2022'de 3x −%24 düşüş, SMA200 filtresiyle 0 |
| Koordinatör | Swing kaldıraç testi | tamam: deneyler/kaldirac.py |

## Aralık eleme çerçevesi (2026-10-12, kullanıcıyla anlaşma)
Hedef: 14 stratejiden en fazla 3–4'ü (5.000 $ için ideal 3). Her rolden en fazla bir strateji:
| Rol | Adaylar |
|---|---|
| Kripto trend/kırılım | Trend Molası, Sıkışma Patlaması, Seviye Kırılımı, Trend Avcısı, BTC Pusulası |
| Düşüşten dönüş alımı | Dipten Sekme, Panik Dönüşü, Tuzak Kırılım |
| Piyasa nötr | Güçlü–Zayıf Sepeti |
| Gün içi | Akşam Momentumu, Trend Günü Molası |
| Hisse/emtia (ilk aşamada yok) | ABD Güçlüler Sepeti, Sakin Emtialar, Mag7/BIST swing |
Ölçütler: (1) kağıt sonuç backtest normal aralığında, (2) rol içinde riske göre en iyi, (3) seçilenler birbiriyle düşük korelasyonlu,
(4) 5.000 $ + en fazla 2x ile uygulanabilir. Strateji bazında karar kartı panele 22 Ekim'de eklenecek (trig_01LPr5gnFsecetpL4zodEdtB).

## Kullanıcının karşılaştırma ölçütü (2026-10-12)
- Kullanıcı: TL mevduat/para piyasası net aylık %2,65–3; hedef bunun +%2 fazlası (aylık %4,5–5, TL).
- Dolar karşılığı (USDTRY son 12–24 ay aylık değer kaybı ~%1,4–1,7): mevduat ≈ aylık %1,0–1,4 $; hedef ≈ aylık %3 $ (yıllık ~%40–50 $).
- Ölçüm: aylık değil, 6 ve 12 aylık pencerede (sistemlerde ayların ~1/3'ü zararlı). Alt sınır: 6 ayda mevduatın $ karşılığını geçmeyen sistem durdurulur.
- Swing backtest: 1x aylık ort. %2,4 $ (12 aylık pencerelerin %18'i hedefi geçer); 2x %4,7 $ ortalama, medyan %1,85 (pencerelerin %54'ü hedefi, %75'i mevduatı geçer).

## Swing stop genişliği (2026-10-12, deneyler/stop_genisligi.py)
Trend Molası kripto stop medyanı %13 (ATR tabanlı). Daraltmak kârı artırmıyor (tampon yok: sistem 2023+ Sharpe 1,45→1,20, düşüş −%17).
"Stop %15'ten uzaksa işlem açma" sistemi daha istikrarlı yapıyor (Sharpe 1,40→1,67, 2023+ 1,55; yıllık %29→%26) ve kaldıraca uygun —
7 varyant arasından seçildiği için aşırı uyum riski var; Aralık'ta "swing v2" adayı, test süresince bot değişmez.
Kaldıraç kararı: 60 günlük kağıt sonuçlarına göre Aralık'ta verilecek (kullanıcıyla anlaşma).

## Kaldıraç özeti (2026-10-12, üç ekip + swing) — karar Aralık'ta kağıt sonuçlarıyla
| Strateji | Güvenli en yüksek L | Not |
|---|---|---|
| Swing (Trend Molası, Sıkışma Patlaması, Dipten Sekme) | ~3x | 2x %54/−30, 3x %79/−44; ≤2x |
| Seviye Kırılımı (KGT) | ~10x | yalnız KGT 1,5–2x, KMN 1x: %55–63/−20…−25 |
| Güçlü–Zayıf Sepeti (KMN) | 1x | stop yok; kaldıraç sonucu bozuyor |
| Trend Avcısı (A) | ~7x | |
| Panik Dönüşü (B) | ~1,9x | stoplar çok geniş; ≤2x; A+B 2x %31/−29 |
| Day trade (S10/S13/S15) | ~5x | 2023-26 2x %38/−9, 3x %62/−13; 2022 3x −%24 (SMA200 filtresiyle 0) |

## Öğrenme katmanı (2026-10-12)
- Panel "Dersler": canlı işlemler strateji başına (≥8 işlem) backtest beklentisiyle binom/t testleriyle karşılaştırılır; kayıp serisi,
  saat kümelenmesi, stop oranı bulguları. Öneridir; kabul edilenler Aralık'ta yeni sürüme girer (öğren → öner → onay → uygula).
- Makine öğrenmesi sinyal filtresi (meta-etiketleme, deneyler/meta_etiket.py, LightGBM, IS 2015-22 / OOS 2023+): swing'de
  işe yaramadı — IS'te puan–kazanç ilişkisi yok (Spearman +0,03); OOS'ta filtre Sharpe 1,45→1,26, boyutlama 1,29. Eklenmedi.

## Panel yol haritası — beyin fırtınası (2026-10-12; TradesViz + 3 ekip araştırması)
A. Hemen (mevcut veriyle): bot sağlık kartı (son mum/çalışma/gecikme/doluluk), çıkış nedeni dağılımı + filtre, su altı (düşüş süresi)
   grafiği + aylık ısı haritası, olasılıklı Sharpe (PSR), TL karşılığı + isteğe bağlı sabah 3 satırlık Türkçe özet.
B. Ekip verisiyle (~19 Ekim): her ekip `ortak/backtest_islemleri.csv` → strateji başına Monte Carlo beklenti konisi ve "rota" trafik ışığı
   → TAMAM (12 Ekim, erken): `karsilastirma/koni.py` → `koni.json` (blok bootstrap, 3000 yol, 63 gün; 1x/2x/3x batma olasılığı). Kaynaklar: swing motoru; trend `trend.birlesim`; algo `algo-sg@claude/optimistic-franklin-9w0pdk:ortak/backtest_islemleri.csv` (×0,5×0,211/0,489 ölçek); day trade `day-trade-sg@claude/confident-ramanujan-j7tq1t` (S10/S13/S15 ÷3); strateji `strateji-sg@claude/dreamy-cannon-lsimjy:ortak/backtest_gunluk_getiri.csv` (günlük bileşik KGT_KMN_50_50 serisi; işlem toplamı KMN oynaklığını düşük gösteriyordu: 2x −%10 olasılığı %1 değil %41). Panelde koni grafiği, rota ışığı (≥p25 yeşil, ≥p5 sarı, altı kırmızı) ve Risk sekmesinde kaldıraç tablosu. Ekip CSV'si güncellenirse `python3 -m karsilastirma.koni` yeniden çalıştırılır.
   (normal aralığın yerine), risk of ruin (1x/2x/3x). Strateji hesabının kaldıraç satırı: ekibin "KGT2x_KMN1x" günlük serisi (backtest_gunluk_getiri.csv; KMN kaldıraçta tasfiye riski taşıdığı için doğrusal 2x/3x kullanılmaz).
C. 22 Ekim karar kartı: yatırılabilirlik karnesi (deneyim/risk istikrarı/beklentiyle uyum) + risk of ruin + koni.
D. Canlı/Aralık sonrası: MFE/MAE + çıkış verimi, maliyet ayrıştırması (komisyon/fonlama/kayma), piyasa koşulu etiketleri,
   çok koşullu "ne olurdu", pivot tablo. Ertelenen: Türkçe soru kutusu (limit), gölge oynatma, grafik üstünde işlem tekrarı.


## Denetim 12 Ekim

Ayrıntı: `karsilastirma/DENETIM_12EKIM.md`. Panel hataları düzeltildi; Aralık kararı için: iki beklenti (iyimser + stres), MTM ölçüleri, BTC rejim maruziyet sınırı, gerçek para planı v2 (durdurma eşiği ve kaldıraç tablosu 1,5× tasfiye kuralıyla yeniden).

## Token tasarrufu (12 Ekim)

Panel 3 saatte bir (trig_01Qxww…); yardımcı yalnız [alarm] seviyesinde bildirir. Kapatılan rutinler (yeniden açılabilir): günlük denetim trig_01DZQ9…, strateji haftalık trig_01XhPo…, day trade haftalık trig_01C6uR…. Kalan: koordinatör haftalık (Pzt 08:47, tüm hesaplar) ve 22 Ekim karar kartı.

## Ekip oturumları kapatıldı (12 Ekim gece, kullanıcı isteği)

strateji-sg, algo-sg, day-trade-sg oturumları arşivlendi (gerekirse yeniden açılabilir). Bot hata düzeltmeleri artık koordinatörde: ilgili reponun ekip dalında düzelt → kagit-deneme testi → PR → birleştir. Ekip dalları: strateji claude/dreamy-cannon-lsimjy, algo claude/optimistic-franklin-9w0pdk, day trade claude/confident-ramanujan-j7tq1t. Açık kalan oturumlar: koordinatör + panel güncelleyici (session_012zeiJo3K4ANnisxVVBWBqp). Rutinler: panel 3 saatlik, Pzt 08:47 haftalık, 22 Ekim karar kartı (+ kullanıcının LinkedIn rutini).
