# Hakem raporu — iki "hesap defteri" denetiminin karşılaştırması

_Fable (bağımsız metodoloji ve risk hakemi), 2026-11-13. Yalnız okuma: repoda dosya değişmedi, test koşulmadı, commit yok.
Her sayı kaynak dosyadan kendi betiğimle yeniden hesaplandı; iki denetçinin özetlerine güvenilmedi._

## Kullanıcıya özet

1. **Kodlanmış 521 stratejide iki denetçi birbirinden bağımsız olarak aynı sonuca vardı** (hangi aşamada, hangi kapıdan elendiği birebir aynı). Bu kısım güvenilir.
2. **Gerçekten "resmi sınavı geçen" strateji 2 tanedir** (ewo-ema-ofset, gauss-stoch-eth). Claude'un "10 geçti"sinin 8'i resmi kapıdan kalıp sonradan "keşif" yoluyla paper'a alınanlardır; Codex'in "18 geçti"sinin 13'ü eski bir projenin arşiv kaydıdır, 1L3A sonucu değildir.
3. **26 strateji kodlandı ama hiç koşulmadı: doğru.** Fakat "unutuldu" değil: v3 ön kaydında yazılı bir karar (yalnız 9 aile temsilcisi koşulur). İçlerinde gerçekten bekleyen tek aday `saatlik-asiri-tepki`.
4. **18 ek ayar (d11j/d12b dosyaları) hiçbir araştırma koşusuna girmedi: doğru.** Bu bir tesisat boşluğu; ama çoğu portföy/short modu, bugünkü canlı yapının dışında.
5. **"73 strateji kârlıydı ama yapısal kapıdan düştü": sayı doğru, yorum eksik.** Bu 73'ün 43'ü zaten 9–10 Kasım'da holdout döneminde ikinci kez koşuldu; yalnız 6'sı anlamlı çıktı ve altısı da paper'a alındı. Geliştirme döneminin en parlakları (kelly-atr-bant, gauss-kanal, ma-cift-cross, rotasyon) holdout'ta sıradan ya da zararlı.
6. **"485 elenenin 215'i adil test edilmedi" hükmü abartılı.** Bu 215'in 199'u daha önce v1 testinde ayar ızgarasıyla (183'ü iki zaman diliminde) da koşulmuş, 169'u orada da elenmişti. Gerçek adalet sorunu olan küme çok daha küçük.
7. **Asıl boşluk kodlanmamış kaynaklarda.** Yaklaşık 900 kaynak "mevcut bir stratejinin benzeri/ayarı" denerek bırakıldı; bu eşleme çoğunda anahtar kelimeyle yapıldı, ayar hiç yazılmadı, fark hiç test edilmedi. Yaklaşık 160 kaynağın da akıbeti hiçbir dosyada yazmıyor.
8. **Hangi tabloya güvenmeli:** kod düzeyinde ikisine de. Kaynak düzeyinde Claude tablosu kullanışlı ve örneklemimde olgusal hata vermedi; Codex tablosu dürüst ama satırların %76'sını "belirsiz" bıraktığı için sorunuza cevap vermiyor.
9. **"Eksik yapıldı" duygunuz yarı yarıya haklı:** kayıt tutma ve "benzeri var" kararları özensizdi; ama kodlanıp test edilenlerde saklanmış bir kazanan görünmüyor.
10. **Önerim:** yeni bir tarama turu açmayın. En erken Şubat sonu değerlendirmesinden sonra, en fazla 3–5 adaylı, önceden yazılmış tek bir tur; sınav yalnız ileri (görülmemiş) veride.
11. **Yapılmaması gereken:** 73'ü ya da herhangi bir elenmişi kapı gevşeterek geri getirmek; aynı geçmiş veride yeni koşu yapıp sonucu "kanıt" saymak.

---

## 1. Yöntem karşılaştırması

| Konu | Claude (ikinci hesap, main) | Codex (`codex/hesap-defteri`) |
|---|---|---|
| Birim | 8.941 ham satır → 6.223 "tekil strateji" | 9.080 ham kayıt → 8.197 "temkinli profil" (kendi ifadesiyle bağımsız strateji sayısı değil) |
| Tekilleştirme | Açık kanıt + kaynak ↔ kod bağlama (KOD / AYAR / ESDEGER / BENZER / TEKRAR). 837 katalog alt kümesi, Excel ↔ repo_kodlari bağlandı | Yalnız birebir kopya (883). Kaynak ile kod, mantık eşitliği ispatlanmadıkça ayrı satır |
| Kanıt standardı | Envanter dosyasındaki `durum` sütunu, ön eleme dosyaları, kodlama günlükleri "yazılı neden" sayıldı | Envanterin kendi `durum` sütunu "beyan" sayıldı, hüküm üretilmedi; yalnız v3 ön eleme ve elenenler dosyaları neden kabul edildi |
| Verdiği kararlar | D 3.824, E 161, F 304, G 526, H 836, BELIRSIZ 35 | D 1.121, E 0, F 4, G 127, H 71, BELIRSIZ 6.221 |
| Kaçındığı | Pek az şeyden; "benzer" hedeflerinin 909'unu doğrulamadığını açıkça yazdı | Kaynak → kod bağından, envanter beyanından, dış depo bayraklarından |
| Adil test sütunu | Kod başına türetilmiş etiket (son aşamaya göre) | Kodlarda kısmen; kaynak profillerinin 7.413'ü BELIRSIZ |
| Öz denetim | 40 satır, 3 hata (%7,5), hepsi "benzer" eşlemelerinde | İlk taslak 12/40 (%30), düzeltme sonrası 2/40 (%5), aynı 40'ta 0 |

**Hangisi daha doğru / dürüst?** Codex daha temkinli ve hiçbir şey uydurmadı; ama temkini tutarsız ve görevin tanımının üstünde.
Görev "D = kodlanmadı, nedeni bir dosyada yazılı" diyordu. Codex, envanterde açıkça `kural_yok`, `veri_yok`, `yasak_dca`, `ml`
yazan yüzlerce satırı (BELIRSIZ içinde: kural_yok 286, veri_yok 253, yasak* ≈130, ml 60) ve dış araştırma raporunun
"FreqAI + pozisyon büyütme + lookahead" dediği Robotic dosyalarını bile BELIRSIZ bıraktı; buna karşılık `on_eleme.csv`'deki aynı
türden gerekçeleri D saydı. Sonuç: 8.197 satırın 6.221'i (%76) için tablo "bilmiyorum" diyor.

**Hangisi daha kullanışlı?** Açık farkla Claude. Sorunuz "her stratejiye ne oldu" idi; Claude tablosu bunu satır satır,
gerekçe ve dosya yoluyla cevaplıyor ve zayıf halkasını (doğrulanmamış "benzer" eşlemeleri) kendisi işaretliyor.
Codex'in E = 0 sonucu "unutulan yok" demek değil (raporu da bunu söylüyor); Claude'un E = 161 sonucu ise alt sınır.

**Codex'in iki somut kaçırması:**
- "İz eksikliği adayı" dediği 621 kaydın 354'ü iki Excel listesinden (`arsiv/sg-arge-/strateji_listesi*.xlsx`). Bunlar
  `stratejiler/ek_kaynaklar/repo_kodlari.csv`'ye `liste_id` ile aktarılmış kayıtlardır; iz vardır (Codex bağı kurmadı).
- 26 koşulmamış v3 kodu için "neden koşulmadığını açıklayan kesin kayıt bulunamadı" diyor. Kayıt var:
  `sonuclar/v3/ON_KAYIT_V3.md` §0.4 ve `stratejiler/v3_adaylar/aileler_v3.csv` (her kart için gerekçe).

**Claude'un iki somut zaafı:**
- "A = geçti" tanımı gevşek (aşağıda §3).
- "215 adil test edilmedi" başlığı kendi tanımının ürünü; kullanıcıyı gereğinden fazla alarma geçiriyor (§4-d).

## 2. Bağımsız doğrulama (tohum 20261114)

Her tablodan 25 satır, katmanlı (A, C, E/BELIRSIZ, B ağırlıklı); her satır kanıt dosyasına kadar izlendi.
Ayrıntı: `ornek_denetim.csv` (aynı klasörde).

| | Claude (25) | Codex (25) |
|---|---|---|
| Olgusal olarak doğru ve yararlı | 19 | 10 |
| Doğru ama tanım uyarısı / zayıf neden | 3 (2 "A" keşif yolu; 1 "ayar denmiş, yazılmamış") | 1 (C doğru, neden "yok" denmiş) |
| Tartışmalı sınıf | 3 (E verilmiş, kaynakta `kural_metni_yok` yazıyor → kendi ölçüsüyle D olmalı) | 2 (Robotic "kullanılabilir" → BELIRSIZ savunulabilir) |
| Aşırı temkin (neden yazılıyken BELIRSIZ) | 0 | 6 |
| Yanıltıcı | 0 | 3 (eski proje arşivi "geçti" → A; ikisinde envanter aynı dosya için "kaldı" diyor) |
| Kısmen (iç çelişki / çift sayım) | 0 | 3 (C kart profilleri: koda bağlı ama metin "uygulama bulunamadı") |
| **Olgusal hata** | **0/25** | **0/25** (yanlış olgu yok) |
| **Sorunuza doğru cevap vermeyen satır** | **3/25 (%12)** | **12/25 (%48)** |

Ek kontrol (Claude'un kendi beyan ettiği zayıf nokta): doğrulanmamış "benzer" eşlemelerinden 8 satır daha (tohum 20261115).
Durum (D) sekizinde de savunulabilir; hedef sınıf 6'sında makul, 2'sinde şüpheli (MOTT → bant-dönüş; Six-Month Cycle MACD → ay
mevsimselliği). Yani "benzeri var" kararlarının kabaca dörtte biri yanlış hedefe işaret ediyor olabilir; Claude'un kendi
bulgusuyla (kodla açılan 174 eşlemenin 118'inde fark) aynı yönde.

Küçük not: Claude'un `B001:n`, `P002:n` kimlikleri dosya satırı değil kayıt sırasıdır (satır = n + 1).

## 3. Anlaşmazlıklar — kim haklı

**Kod düzeyi (521 strateji) çapraz tablo:** B/B 476, C/C 26, yapısal kapı 73/73, aşamalar birebir aynı. Fark yalnız etikette:

| Çelişki | Claude | Codex | Hüküm |
|---|---|---|---|
| A sayısı | 10 = 2 resmi set + 8 paper ("keşif yolu") | 5 kod = 2 resmi set + 3 sağlam keşif (sete alınmayan); + 13 eski TV arşivi = 18 | **İkisi de eksik.** Ön kayıtlı bütün kapıları (holdout dahil) geçen: **2**. Claude'un 8'i resmen elenmiş/izlemede olup 2026-11-09'da "sonuç sonrası keşif — kanıt değil" kararıyla alındı (DURUM.md). Codex'in 3'ü gerçekten her testi geçip küme kuralıyla sete alınmadı (Claude bunlara "elendi" demiş: sert). Codex'in 13 arşiv A'sı 1L3A akıbeti değil; çoğu 1L3A'da kodlanıp elendi (ör. Laguerre RSI → v2 E4) |
| e0v1en | A (canlı kadro) | B (sağlamlık S2'den kaldı) | İkisi de doğru şeyi söylüyor: resmen kaldı, yine de canlı kadroda. Kullanıcı için önemli olan bu çifte gerçek |
| C sayısı | 42 = 26 kod + 16 ek ayar (+2 kaynaksız) | 26 kod (53 profil) + "85 ayarın özgül koşusu yok" | **26 kod: ikisi de doğru. Ayarda Claude haklı.** Codex'in "koşu izi yok" dediği 67 dış ayarın 18'i v1 WF pencerelerinde *seçilmiş* olarak görünüyor (`wf_evren.csv` `secimler`); kalan 49'u aday havuzundaydı ama hiç seçilmedi. Gerçekten hiç koşulmayan ayar: 18 |
| 6 v2 "hata" satırı | B (hata) | BELIRSIZ | Codex haklı: bunlar performansla elenmedi, v2'de hiç ölçülmedi |
| E | 161 | 0 (621 "aday") | Claude daha doğru; ama sayısı alt sınır. Örneklemimdeki 6 E'nin 3'ü kendi ölçüsüyle D. Codex'in 621'inin 354'ü kaçırılmış bağ |
| "Benzeri var" | 2.174 D (909'u doğrulanmamış, açıkça işaretli) | Benzerlikten hüküm çıkarmadı (BELIRSIZ); 6 örnekte kural/kod farkını tek tek yazdı | Codex'in 6 örneği sağlam ve değerli (S0002 Donchian, S0005 MACD+EMA100, S0141 Faber, S0153 AdaptiveTrend, S0244 Kore kırılımı, K001). Claude'un sayımı kullanışlı. İkisi birlikte: "benzeri var" kararları güvenilmezdi |

## 4. Önemli iddiaların doğrulaması

**(a) 26 v3 stratejisi kodlandı, koşulmadı — DOĞRU.** `kodlama_v3.csv` 35 kodlu sınıf; `sonuclar/v3/eleme.csv` 9 satır (0 geçen).
Neden yazılı: ON_KAYIT_V3 §0.4 ("aile = 9 temsilci; diğer kodlu varyantlar bu turda koşulmaz; yalnız temsilci kanıt alırsa") ve
DURUM.md 2026-11-11 ("çoklu test bütçesi"). Önemli ayrıntı: 26'nın yaklaşık yarısı, temsilcisi hiç koşulmayan ailelerde
(ORB/seans kırılımı 5, RSI-trend geri çekilme 3, zaman serisi momentumu 2 …); gerekçeleri "v2 havuzunda zaten test edilip elenen
ailenin varyantı". Yani karar bilinçli ve ön kayıtlı; 9 temsilcinin hepsi elendiği için kural gereği kardeşlere bakılmadı.
Gerçekten askıda kalan tek satır: `v3__saatlik-asiri-tepki` (aile temsilcisi, hakem puanı 6; birincil metin okunamadığı için bekletildi).

**(b) `ayarlar_d11j_ek.json` (11) ve `ayarlar_d12b_ek.json` (7) araştırma koşucularınca okunmuyor — DOĞRU.**
`git grep`: yalnız `testler/test_d11j_modlar.py` ve `testler/test_d12b_151.py`. `tarama._ayar_listesi` ve
`wf_portfoy.aday_listesi` yalnız kart_ayarlari + dis_ayarlari + BAGLAMA + ızgara okur. 18 ayarın 17'si portföy modu
(kesitsel L/S, rotasyon skorları, HRP/min-var/MVO, rejim filtreleri, pairs), 1'i funding short. Etki: gerçek bir boşluk, ama
hiçbiri bugünkü yapıya (yalnız long, tek-grafik, büyük kripto) aday değil.

**(c) v2'de 73 strateji E1+E3'ü geçip E2/E4/E5'ten düştü — DOĞRU** (`eleme.csv`: E4 17, E4+E5 16, E5 15, E2 11, E2+E4 9,
E2+E4+E5 3, E2+E5 2). Kapıların bugünkü yapıya uygunluğu:

| Kapı | Ne ölçüyor | Bugünkü yapıya (strateji başına küçük hesap, yalnız büyük kripto, long) uygun mu |
|---|---|---|
| E4 genişlik (üç sınıftan en az ikisi kârın ≥ %15'i) | Kâr kripto + hisse + emtia arasında yayılıyor mu | **Uymuyor.** Canlı evren zaten yalnız kripto; ön kayıt da "evren = kripto ise kapı yok" diyor. E4'ten düşen 45 satırın 33'ünde kârın ≥ %85'i kriptodan. Ama kapının amacı da tam buydu: 2017–2025 kripto boğasında her long trend kuralı kârlı görünür |
| E5 hayatta kalma (tek kasada −%20 kill hiç yok) | Düşüş | **Büyük ölçüde uyuyor.** Testte işlem riski %1, kill −%20; canlıda risk %1,5, kill −%30: oran aynı. Fark: test 35 enstrümanlı tek kasada |
| E2 örnek (≥ 200 işlem, ≥ 10 enstrüman) | İstatistik gücü | **Uyuyor**; hesap yapısından bağımsız. Yavaş (günlük) stratejileri yapısal olarak zorluyor |

Belirleyici olgu (iki denetçinin raporunda öne çıkmıyor; Codex hiç anmıyor): **bu 73'ün tek kapıdan düşen 43'ü, 2026-11-09
kullanıcı kararıyla holdout döneminde (2025-11 → 2026-11) keşif amaçlı zaten koşuldu** (`sonuclar/evren/v2/holdout_kesif/`).
Sonuç: 28'i artıda, yalnız 6'sı net > 0 ve p ≤ 0,05 (jt-awesome, uc-ortalama, sabit_sepet, lube, hma-atr-rider, voltarget) ve
altısı da paper'a alındı. Geliştirme döneminin yıldızları holdout'ta: kelly-atr-bant +%9,6 (p 0,32), gauss-kanal +%1,1 (PF 0,88),
ma-cift-cross PF 0,93, pf__rotasyon −%7,6. Yani "haksız elenen 73" hikâyesinin 43'lük kısmı zaten telafi edildi ve içinden
çıkanlar alındı. Kalan 30 (çok kapıdan düşenler) holdout'ta koşulmadı; 21'i E5'ten (kill) de düşüyor.

**(d) "485 elenenin 215'i adil test edilmedi" — ZAYIF, bu haliyle kullanılmamalı.** Claude'un tanımı "strateji *son* girdiği testte
tek TF / tek ayar / yapısal kapı / kısa veri ile mi elendi". Ama:
- 215'in 188'i v2 elemesinde. v2'de tek sabit ayar ve tek TF bir kusur değil, **ön kaydın bilinçli tasarımı** (ON_KAYIT_V2 §1.1:
  ayar seçimiyle aşırı uyumu önlemek için).
- 215'in 199'u daha önce v1 evren WF'de 12–27 ayar adayıyla koşulmuştu (183'ü iki TF'de); 169'u orada da elendi, 30'u
  geçmişti (kendi sayımım, `wf_evren.csv`). v1'de hiç satırı olmayan yalnız 16 (9'u v3).
- Gerçek adalet sorunu taşıyan alt küme: 6 teknik hata satırı (ölçülmedi), E4'ün evren uyumsuzluğu (yukarıda; büyük kısmı
  holdout keşfiyle telafi edildi), ve "zayıf temsilci" vakaları (kaynak kuralı ile koşulan kod farklı; Codex'in 6 örneği,
  tur 4 değerlendirmesinin 4 grubu).
Dürüst ifade: "485 elenenin çoğu iki ayrı tasarımla test edildi; adalet tartışması olan küme onlarla ölçülür, yüzlerle değil."

## 5. Metodolojik risk: bu listeden yeniden test

**Taban oran.** 521 kod, 939 (strateji × TF) satır; ön kayıtlı bütün kapıları geçen 2. Canlı adayı 4 stratejinin 4'ü de yeni 40
sembolde genelleşmedi (`sonuclar/evren/yeni_sembol/rapor.md`: ortalama R'nin güven aralığı tamamen sıfırın altında). Bu, eldeki
"en iyilerin" bile seçildikleri 11–13 coine özgü olabileceğini gösteriyor. Bu taban oranla listeden 100 strateji daha koşmak,
gerçek avantajdan çok şans eseri "geçen" üretir.

**Riskler.**
- *Çoklu test:* v2'nin BH düzeltmesi m = 939 ile yapıldı. Aynı veride yeni koşular bu aileyi büyütür; yeni "geçen"lerin
  p-değeri eski eşikle kıyaslanamaz.
- *Sonuç sonrası kapı değiştirme:* 73'lük listeyi gören herkes hangi stratejinin hangi kapıdan, ne kadar kârla düştüğünü
  biliyor. "E4'ü kaldırıp yeniden bakalım" tam olarak yasak olan şeydir; E4'ten düşenlerin kârının kriptodan geldiğini de artık
  biliyoruz.
- *Tükenmiş holdout:* 2025-11 → 2026-11 dönemi resmi holdout + 55 keşif koşusu + yeni sembol sınavı ile kullanıldı. Kanıt değeri yok.
- *Seçim yanlılığı:* Kısa listeyi net getiriye bakarak kurmak (hesap defterindeki "en yüksek net ilk 15" tablosu) doğrudan veri
  madenciliğidir.

**v2 disiplinine göre (yılda 2–3 tur, ön kayıtlı tek koşu, kota yok, elenmiş diriltilmez, canlıda yeni filtre yok):**

| Yeniden test | Meşru mu |
|---|---|
| Hiç koşulmamış, kuralı kaynakta açık ve önceden yazılmış aday (ör. saatlik-aşırı-tepki; kaynak biçimi hiç koşulmamış "zayıf temsilci" kuralları) → yeni ön kayıt, tek koşu, geçmiş veri yalnız *eleme*, kanıt yalnız ileri veri | **Evet** |
| Teknik hatayla ölçülemeyen 4 strateji, hata düzeltilip **eski kapılarla aynen** | **Evet, ama düşük değer** (v1'de ölçülüp elenmişlerdi) |
| 18 ek ayar | Yalnız yön-bağımsız / portföy kolu yeniden açılırsa; bugün kapsam dışı |
| E4/E5/E2'den düşen 73'ün kapı gevşetilerek ya da "kripto evreni" diye yeniden koşulması | **Hayır** (sonuç görülmüş; 43'ü zaten ikinci şansını aldı) |
| Elenmiş bir stratejiye filtre/ayar ekleyip başka adla denemek | **Hayır** (ON_KAYIT_V2 §0.3, CANLI_PLAN_V2 §8) |
| "Benzeri var" denmiş ≈ 900 kaynağın topluca kodlanıp taranması | **Hayır** (kota doldurma; taban oran çok düşük) |
| Yeni sembol sınavına bakıp sembol ya da strateji ayıklamak | **Hayır** (CANLI_PLAN_V2 §9) |

**Yeni sembol sınavının bu listeye etkisi.** İki sonuç: (1) listedeki herhangi bir adayın geçmiş veride iyi görünmesi artık
daha da az şey ifade ediyor; (2) bundan sonraki her ön kayda "seçimde kullanılmamış semboller" kapısı baştan yazılmalı.
Bu sınav 4 strateji ve tek dönemle yapıldı; bütün listeyi hükümsüz kılmaz ama beklentiyi aşağı çeker.

## 6. Hüküm

### (a) Hangi tabloya ne ölçüde güvenilir

| Kısım | Güven | Not |
|---|---|---|
| Kodlu 521 stratejinin aşaması, kapısı, 26 koşulmayan, 73 yapısal | **Yüksek** | İki bağımsız denetim birebir aynı; kaynak dosyalardan da doğruladım |
| Claude: kodlanmamışların F / G / H ve "nedenli D" ayrımı | Orta-yüksek | Örneklemde olgusal hata yok; H ↔ D sınırı kendi içinde tek tip değil |
| Claude: "benzer_var" 2.174 satır | **Düşük-orta** | Durum (kodlanmadı) doğru; "benzeri test edildi" çıkarımı güvenilmez. 909'u hiç doğrulanmadı |
| Claude: E = 161 | Orta | Alt sınır; bir kısmı aslında "kural metni yok" |
| Claude: "215 adil değil" | **Düşük** | Tanım kaynaklı şişkinlik (§4-d) |
| Claude: A = 10 | Yanıltıcı başlık | Resmi geçen 2 |
| Codex: kod satırları ve 6 temsil farkı incelemesi | **Yüksek** | Dikkatli ve doğru |
| Codex: kaynak profilleri (7.400+) | Kullanışsız | Yanlış değil, ama %76 BELIRSIZ; A'daki 13 arşiv satırı yanıltıcı |

Pratik öneri: çalışma tablosu olarak **Claude tablosunu** kullanın; "A" sütununu 2 olarak okuyun; "adil test" sütununa değil
§4'teki dar kümeye bakın; Codex'in `P8_manuel_mantik_denetimi.csv` dosyasını (6 temsil farkı) ek olarak saklayın.

### (b) Gerçekten "haksız elenmiş / hiç denenmemiş" kısa liste

Seçim ölçütüm net getiri değil; "kural açık + bizim evrende yapılabilir + kendi biçimiyle hiç koşulmamış ya da performans dışı
nedenle düşmüş". Sıra öncelik değildir.

| # | Aday | Neden listede | Çekince |
|---|---|---|---|
| 1 | `v3__saatlik-asiri-tepki` (De Nicola) | Aile temsilcisi, kodlu, hakemli kaynak; yalnız "birincil metin okunamadı" diye bekletildi. Hiç koşulmadı | Saatlik ters dönüş: maliyete çok duyarlı (noise-area aynı nedenle çöktü) |
| 2 | Günlük geniş eşikli yüzde filtre / %20 iz stoplu long trend (T61, Alexander–Radge) | Bizde yalnız 1h/30m ve %1–3 eşikle koşuldu; kaynak biçimi (günlük, geniş eşik) hiç koşulmadı | Long trend + kripto boğası yanlılığı; al-tut kıyası şart |
| 3 | BLL tipi bantlı MA (T21) | Kaynak kuralı (kısa/uzun MA + %1 bant) koşulmadı; yakın temsilci 121 işlemle E2'den düştü | Aynı |
| 4 | EMA200 filtreli + 2R hedefli Donchian (T02 / S0002) | Kaynak kuralı (yalnız long, SMA/EMA200 filtresi, kaynaksız stop) ne varsayılanda ne ızgarada var: Codex ve tur 4 raporu ayrı ayrı aynı farkı buldu | Donchian ailesi iki kez elendi; bu üçüncü biçim |
| 5 | MACD durum + EMA100 fiyat filtresi, birleşik çıkış (S0005) | Kod kesişim *olayı* kullanıyor, filtre ve çıkış farklı (Codex incelemesi) | MACD ailesi E4+E5'ten düştü; fark küçük olabilir |
| 6 | Eski projede iyi çıkıp aynı biçimi denenmeyenler: Ichimoku 20/60/120 (bizde ızgara 26/52), Argus gizli uyumsuzluk | Karar 10 "önceki proje adayları 1L3A'da yeniden test edilir" diyordu; aynı parametre biçimi koşulmadı | Eski sonuçlar örnek içi; denetçi notundan alındı, kodu ben satır satır açmadım |
| 7 | Teknik hatayla v2'de ölçülemeyen 4 strateji (`dis__norn-weave-thurisaz`, `dis__shm-wma`, `onceki__4s-kirilim`, `onceki__kgt`) | "1d üst TF, alt TF 1d" yapılandırma hatası; performansla elenmediler | v1'de ölçüldüler ve "en iyi %5 işlem hariç PF" kapısından düştüler: kâr birkaç işleme bağlı |
| 8 | 906 listesinde "bizde yok", kuralı açık, hiç karar yazılmamış 29 fikir (DV2, Larry Williams 9.1/9.2, PFR, Vortex, Stiffness, Correlation Trend, Elegant Oscillator …) | Gerçek E: ne kod ne karar var | Tur 4 değerlendirmesi, arşivde olmayan 16 yeni fikrin 13'ünde hiç dış kanıt bulmadı; çoğu gösterge varyantı |
| 9 | Robotic deposunda "bizde yok + kullanılabilir" 26 küme (GKD ailesi, FeraRelativeVolume, GnF) | Hiç karar yazılmadı | Kod okunmadan tahmin; çoğu 5 dk, hiperopt edilmiş |
| 10 | "Ayar: X" denip ayarı hiç yazılmayan kaynaklar (repo_kodlari'da 234 anahtar-kelime eşlemesi; 93 kitap kartı) | En büyük gerçek boşluk: kâğıt üstünde "ele alındı", fiilen denenmedi | Tek tek aday değil, **havuz**. İçinden seçim ancak önceden yazılmış nesnel ölçütle yapılabilir |

Listeye **almadıklarım** ve nedeni: 73 yapısal eleme (43'ü ikinci şansını aldı, kalanı çok kapıdan düşüyor); 22 "aile
temsilcisi değil" v3 varyantı (ön kayıtlı, bilinçli); 18 ek ayar (kapsam dışı kol).

### (c) Önerilen sonraki adım

1. **Şimdi (araştırma değil, kayıt):** Claude tablosunu "resmi hesap defteri" olarak kabul edin; üç düzeltmeyle: A = 2 + ayrı
   "keşif yoluyla paper" sütunu; "adil test" başlığı yerine §4-d'deki dar tanım; 73 satırına holdout keşif sonucunu ekleyin.
   Bundan sonra her yeni kaynak için tek satır: kaynak → karar → (varsa) kod → koşu. Koşu yok.
2. **Canlı takvime dokunmayın.** Testnet, duman, 2026-12-08 sadakat, ewo 250 USD planı aynen. Bu denetimden canlı kadroya
   giren ya da çıkan hiçbir şey yok.
3. **Tek ön kayıtlı tur, en erken Şubat sonu değerlendirmesinden sonra** (2027'nin 2–3 turluk bütçesinin ilki):
   - **Aday sayısı: en fazla 3–5**, hepsi koşudan önce adıyla ve tam kuralıyla yazılır. Önerim: #1, #2, #4 (+ isterseniz #3, #6'dan
     Ichimoku). Seçim gerekçesi "kaynak biçimi hiç koşulmadı" olmalı, geçmiş getirisi değil.
   - **Kapılar (önceden yazılır, sonra değişmez):** yalnız kripto evreni; maliyet ×2'de net > 0 ve PF ≥ 1,2; en iyi sembol ve
     en iyi yıl çıkarılınca hâlâ artıda; ≥ 200 işlem; kill yok (canlı ölçeğine çevrilmiş); long ise al-tut'u Sharpe'ta
     geçmeli (v3 P6); rastgele giriş testi; **seçimde kullanılmamış sembollerde ortalama R > 0** (yeni sembol sınavının dersi).
   - **Statü:** geçmiş veri koşusu yalnız *eleme*dir (v3 §0.1 ile aynı). Geçen aday "işe yarıyor" sayılmaz; ≥ 12 hafta paper'a
     girer; canlı kararı ayrı.
   - Hiçbiri geçmezse sonuç sıfırdır; yedek liste açılmaz.
4. **Yapılmayacaklar:** 73'ü ya da herhangi bir elenmişi kapı değiştirerek geri getirmek · "en yüksek net" tablosundan aday
   seçmek · 900 "benzeri var" satırını topluca kodlayıp taramak · holdout dönemini (2025-11 → 2026-11) yeniden kanıt saymak ·
   bu tur için canlıdaki stratejilere filtre eklemek · turu Şubat'tan öne çekmek.

### "Eksik yapıldı" duygusu ne kadar haklı

**Haklı olduğunuz yer (süreç ve kayıt):**
- Getirdiğiniz kaynakların çoğu test edilmedi: ≈ 6.200 tekil kaydın yalnız 521'i koda döküldü. Kalanların kabaca üçte biri
  meşru nedenle dışarıda (yasak tip, ML, bizde olmayan veri/piyasa), ama **≈ 2.200'ü "benzeri var" denerek** bırakıldı ve bu
  kararların ≈ 900'ü anahtar kelime eşlemesiydi; "ayar olarak denenecek" denenlerin ayarı çoğunlukla hiç yazılmadı.
- ≈ 160 kaynağın akıbeti hiçbir yerde yazmıyor. 18 ek ayar tesisata hiç bağlanmamış. Belgelerdeki bazı sayılar
  (ör. "~120 ek ayar"; dosyalarda 195) tutmuyor.
- Kaynak kuralı ile koşulan kod arasında gerçek farklar var (zayıf temsilci); "X test edildi, elendi" cümlesi bazen kaynağın
  kendisi için doğru değil.
- Elemelerin önemli bir kısmı kârsızlıktan değil, tek-kasa / çok-sınıf varsayımına dayalı kapılardan; bu varsayım bugünkü
  yapıyla örtüşmüyor (E4).

**Abartılı olduğu yer (sonuç):**
- Kodlanıp test edilenlerde "saklanmış kazanan" izi yok. Kârlı görünüp kapıdan düşenlerin tek kapılı 43'ü ikinci kez koşuldu;
  işe yarar görünen 6'sı zaten paper'da. Diğerleri görülmemiş dönemde sıradan.
- 26 koşulmayan strateji unutulmadı; çoklu test bütçesi için yazılı, önceden alınmış bir karar.
- "215 adil test edilmedi" rakamı gerçeği büyütüyor; çoğu iki ayrı tasarımla test edildi.
- En önemlisi: sorun "yeterince strateji denenmedi" değil. 521 strateji denendi, 2'si resmi sınavı geçti ve en iyi 4'ü yeni
  coinlere taşınmadı. Daha çok strateji denemek bu tabloyu düzeltmez; yanlış pozitif sayısını artırır.

Tek cümleyle: **muhasebe eksikti, hüküm büyük ölçüde değişmiyor.**

## 7. Emin olmadıklarım

- Kısa listenin #6 maddesi (eski proje adayları) Claude denetçisinin G10 notundan; ilgili kodu ve eski sonuç dosyalarını kendim açmadım.
- "Benzeri var" hedeflerinde yalnız 8 + 2 satır baktım; "dörtte biri şüpheli" tahmini kaba (küçük örnek).
- E5'in bugünkü yapıya uygunluğu oran benzerliğine (%1 / −%20 ↔ %1,5 / −%30) dayanıyor; kripto-yalnız tek hesapta kill sayısı farklı çıkabilir, ölçmedim (ölçmek de yeni bir koşu olurdu).
- 49 dış ayarın "aday havuzunda koşuldu" hükmü dolaylı kanıta dayanıyor (aday sayısı eşleşmesi; WF'de hiç seçilmedikleri için kendi satırları yok).
- Örneklem tablo başına 25 satır: hata oranlarının belirsizliği geniş (Claude %12 için kabaca %3–%30 aralığı).
- Codex dalını yalnız çıkarılmış dosyalardan okudum; yeniden üretim betiklerini çalıştırmadım.
- Eski TV arşivindeki "geçti" JSON'ları ile envanterdeki "kaldı" beyanı çelişiyor; hangisinin son durum olduğunu çözmedim (1L3A akıbetini etkilemiyor).
