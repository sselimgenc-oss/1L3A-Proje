# Aşama 2 triyajı — K3 / K4 / K5 ve COK_KOLLU (bağımsız hakem, sonuç görülmeden)

Tarih: 2026-11-13. Gerçek mum verisi açılmadı, hiçbir koşu yapılmadı, `veri/` okunmadı, aşama 1 koşu çıktılarına (`kosu_asama1/`) bakılmadı. Bu rapor **satır kararı vermez**; popülasyon düzeyinde "hangi alt küme uğraşmaya değer" sorusunu yanıtlar. Alt küme tablosu: `triyaj_asama2.csv` (33 satır; katman toplamları 1.816 / 2.204 / 706 / 87 ile birebir tutuyor). Robotic'in 277 KOSULACAK satırına dokunulmadı (ayrı hakemde).

## 1. Kısa sonuç

| Katman | Toplam | Zaten kapalı / aşama 1'de kapsandı | Kapsam dışı bırak (ek 5 ile) | İncele | Koş |
|---|---:|---:|---:|---:|---:|
| K3 | 1.816 | 1.214 | 541 | 48 (Robotic) | 13 |
| K4 | 2.204 | 561 + 87 (COK_KOLLU, bkz. §5) | 1.150 | 129 (+277 Robotic, ayrı hakemde) | — |
| K5 | 706 | 620 (mekanik devralma) | 72 | 14 | — |
| COK_KOLLU | 87 | — | 86 | 1 | — |

- **Kapalı** = bu satırların kararı zaten verildi ve denetlendi, ya da kullanıcının kendi belgeleri olduğu için aşama 1'de ele alındı. Ek iş yok, hiçbir şey silinmiyor.
- **Kapsam dışı** = henüz satır satır incelenmemiş (ya da incelemesi reddedilmiş) ve incelemeye değmeyecek kümeler: toplam **1.763 satır + 86 çok kollu dosya**.
- **Gerçekten uğraşmaya değer kalan iş:** 13 hipotez (koş) + 143 satırlık hızlı inceleme (K4'te 129, K5'te 14) + Robotic kararı (48 + 277).

## 2. Bu satırlar nereden geliyor

K3 + K4 = 4.020 satır. Kaynak grubuna göre (hesap defteri `kaynaklar.csv`):

| Kaynak | Ne | K3 | K4 | Durum |
|---|---|---:|---:|---|
| X005 / X008 | **Kullanıcının belgeleri** (906 listesi, ajan2 raporu) | 135 | 479 | Tamamı kararlı; aşama 1 listesi + ön eleme |
| B001 | **Robotic / Freqtrade 909 dosya arşivi** | 176 | 446 | Tamamı kararlı: 325 KOSULACAK (277 K4 + 48 K3), 87 COK_KOLLU, 210 ret |
| V001–V016, V90x | v3 turunun katalogları (GitHub/Reddit/site taramaları, Gemini/ChatGPT derin araştırma) | 722 | 311 | K3: 176 kabul, 227 denetim reddi (p06), 319 kararsız. K4: 311 kararsız |
| H001–H007 | Bizim GitHub taramamız (7 grup × 50 repo) | 440 | 280 | K3 kararlı; K4 kararsız |
| P001–P009 | Eski arşiv Excel/repo listeleri (sg-arge) | 117 | 345 | K3 kararlı; K4 kararsız (234'ü yalnız anahtar kelime eşlemesi) |
| K001–K135 | Kitap kartları | 127 | 275 | K3 kararlı; K4 kararsız |
| A001–A013, A912 | Kullanıcının eski projeleri (algo-sg vb.) | 8 | 45 | K3 kararlı; K4 kararsız |
| D, Q | Eski dış envanter, Kakushadze 151 | 91 | 23 | K3 kararlı; K4 kararsız |

Önemli tespitler:

1. **Kullanıcı belgeleri (614 satır) bitmiş durumda.** 311 satır koşulabilir bulundu; 257'si aşama 1 listesinde, 45'i ön elemede, 9'u kodlanamadı. Aşama 2'de bu kaynaklardan iş kalmadı.
2. **"Freqtrade 909" = B001.** Hesap defterindeki kayıt: `2026-11_freqtrade_robotic/dosya_listesi.csv`, 909 dosya. Kullanıcının "freqtrade 909 stratejisinden bahsetmiyorum" sözü ile görev tanımındaki "öncelik: Robotic B001" birbiriyle çelişiyor olabilir; bkz. §7 soru 1. K3/K4 içinde B001 payı 622 satır.
3. **Kararsız K4'ün tamamı (1.279 satır) kullanıcı önceliği dışındaki kaynaklardan.** Bunlar eski defterde "D: kodlanmadı, nedeni yazılı; benzeri arşivde var" etiketliydi.
4. **Kabul edilmiş K3 partilerinde kullanıcı-dışı kaynakların verimi çok düşük:** 959 satırdan 8 KOSULACAK (%0,8). Kitap kartları 0/127, Excel listeleri 0/117, GitHub taraması 1/440.

## 3. K4'te kalan 1.279 satır: eşleşen arşiv sınıfına ne olmuştu

Her satır bir arşiv sınıfına "benzeri var" diye bağlı. O sınıfın hesap defterindeki akıbetine göre:

| Alt küme | Satır | Öneri | Neden |
|---|---:|---|---|
| Kesitsel / pairs / rotasyon portföyüne bağlı | 135 | ÇIKAR | Kullanıcı kararı (politika 4): evren dışı, ek katman yok |
| Sınıf **aşama 1'de zaten koşuyor** (kullanıcı listesinin ayarıyla, 13 kriptoda) | 375 | ÇIKAR | Aile temsil ediliyor; katalog satırı aynı sınıfa bir parametre noktası ekler |
| Sınıf **performansla elenmiş** (v1 walk-forward 345, v2 kârlılık 260, v2 test 10) | 617 | ÇIKAR | Aile ızgaralı testte elendi; kaynak kalitesi düşük |
| Sınıf v2'de **yalnız yapısal kapıdan** elenmiş, aşama 1'de yok | 75 | İNCELE | Tek gerçek boşluk (aşağıda) |
| Kullanıcının eski projeleri (A serisi) | 38 | İNCELE | Küçük, kuralı tam, kendi malzemesi |
| Sınıf geçmiş (canlı/paper) | 16 | İNCELE (isteğe bağlı) | En olası ama en fazlalık |
| v3 kartına / v3 koduna bağlı | 23 | ÇIKAR | K1 kararı ve K5 kart kümesi kapsıyor |

**75 satırlık boşluk nedir:** v2'de bir strateji, kârlı olsa bile kazancı tek varlık sınıfından (ör. yalnız kripto) geliyorsa "genişlik" kapısından eleniyordu. Kapanış turu yalnız kripto ve bu kapı yok. `dis__ma-cift-cross`, `swing__ma-geri-cekilme`, `swing__bb-sikisma-kirilim`, `dis__tsmom` gibi sınıflar bu şekilde elenmiş ve aşama 1 listesinde yok. Sınıflar hazır olduğu için kodlama gerekmez (mevcut sınıf + kaynak ayarı). Beklentiyi düşük tutmak gerekir: önceki hakem raporuma göre bu türden 73 sınıfın 43'ü 9–10 Kasım'da yeniden koşuldu, yalnız 6'sı anlamlı çıktı ve hepsi paper'da.

**617 satır için dürüstlük notu:** "Bu kurallar zaten test edildi" denemez. Kullanıcı listesinde 479 "benzeri var" satırından yalnız 4'ü arşiv sınıfıyla gerçekten aynı çıkmıştı. Doğru ifade: fikir ailesi test edilip elendi, kaynağın kendi biçimi ayrıca sınanmadı ve sınanmayacak. Bu bir **kapsam kararıdır**, kanıt değil.

## 4. K3 ve K5

**K3 (1.816):** 1.214 satır kapalı. Kalan:
- **13 hipotez KOŞ** (`K3-5a`): çoğu kripto gün içi kuralı (ChatGPT/Gemini derin araştırma satırları V006, V010), bir mevcut sınıf + ayar (H007:48), bir eski proje kuralı (A002:6). Yaklaşık bir kodlama partisi.
- **4 hipotez ÇIKAR** (`K3-5b`): kesitsel beta (politika 4), her 15 dakikada tek 5m mum tutma (maliyet ×2 gidiş-dönüş %0,28–0,40; koşulsuz giriş bunu karşılayamaz), iki hyperopt sayı aralığı.
- **48 Robotic KOSULACAK** (`K3-3`): diğer hakemin 277 satıra uyguladığı ölçütlerin aynısı uygulanmalı; bu 48 satır o kümenin dışında kalmış.
- **537 satır kapsam dışı:** 319 kararsız + 218 denetimi reddedilmiş p06 kararı. Hepsi v3 katalogları. Bu kataloglar v3 turlarında iki kez ön elemeden geçti (2.592 satır + 799 satırın kod açılarak yeniden bakışı); ürünü 154 kart ve 26 v3 koduydu, onlar da K1 ile aşama 1'de. Üçüncü geçişin beklenen verimi 6 hipotezin altında.

**K5 (706):** Ön kayda göre K5 "hipotez değildir", iz kaydıdır.
- 620 satır mekanik: bağlı olduğu ana kimliğin kararını devralır (betikle, elle inceleme yok).
- 78 kodlanmamış v3 kartından **6'sı İNCELE**: kuralı kartta tam, v3 hakem puanı ≥4, kripto/genel, kesitsel değil, hiç koşulmamış. Kalan 72 ÇIKAR.
- 8 arşiv kaydı (`codex-algo/pdf_candidates.csv`): ana defterde karşılığı bulunamamış tek küme; 15 dakikalık bakış.

## 5. COK_KOLLU (87 dosya) — öneri: 86 ÇIKAR, 1 İNCELE

| Aile | Dosya | Kol | Stop | Öneri | İstenirse temsilci |
|---|---:|---|---|---|---|
| NFI / Nostalgia / CryptoFrogNFI / Combined_NFI | 51 | 10–48 | 43/48'de −0,99 | ÇIKAR | B001:724 (NFI V3, 10 kol) |
| BigZ / Bcmbigz / BigPete | 16 | 12–23 | 16/16 −0,99 | ÇIKAR | B001:411 (BigZ03, 12 kol) |
| BB_RPB_TSL türevleri, BBMod1, Alien | 9 | 11–69 | 6/8 ≤ −0,50 | ÇIKAR | B001:407 (11 kol) |
| BinHCluc + MAD | 6 | 10–21 | 5/6 −0,99 | ÇIKAR | B001:461 (V9, 10 kol) |
| NASOS RV6, true_lambo | 3 | 13–16 | −0,15 | ÇIKAR | B001:101 |
| ckNSJT_morning | 1 | 10 | −0,99 | ÇIKAR | — |
| RSI_Futures (1h, iki yön) | 1 | 14 | −0,30 | İNCELE | B001:215 |

85'i 5m, 86'sı yalnız long. Sayılar karar dosyalarından ve scratchpad'deki depo kopyasında metin sayımından (87 dosyanın 79'u bulundu; kod çalıştırılmadı).

Tümden çıkarma gerekçeleri:

1. **"Birebir uyarlama" bu çerçevede anlamını yitiriyor.** 79 dosyanın 71'inde stop −%50 ya da daha geniş (çoğu −%99, yani fiilen stopsuz). Mevcut politika bunlara ATR×3 stop koyup işlemi %1,5 riske göre boyutlandırıyor. Bu sistemler "zarardaki pozisyonu tut, küçük kârı sık al" üzerine kurulu; stop eklenince ölçülen şey kaynak strateji olmaz. Sonuç ne çıkarsa çıksın "NFI çalışıyor/çalışmıyor" denemez.
2. **Aşırı uyum riski listenin en yükseği.** NFI ailesinde dosya başına medyan 285 hyperopt parametresi, 51 dosyada toplam yaklaşık 116.000 satır. Bunlar tek bir sistemin sürüm serisi; 51 ayrı fikir değil.
3. **Aileler zaten temsil ediliyor.** Her ailenin 10'dan az kollu ata sürümleri Robotic'in 277 satırlık kümesinde var: NostalgiaForInfinity V1/V2, CombinedBinHAndCluc (13 dosya), CombinedBinHClucAndMAD V3/V5/V6, BB_RPB_TSL_RNG (4), NASOS v4/v5 ve modları, Elliot serisi. Ayrıca projenin canlı stratejisi `dis__ewo-ema-ofset` bu ailenin çekirdeğinin sadeleştirilmiş hali.
4. **Maliyet.** BigZ/BinHCluc ROI tablosu 40 dakika sonra %0,5 hedefe iniyor; maliyet ×2 gidiş-dönüş %0,28–0,40. Dürüst sınır: "5m hiç geçemez" diyemem, çünkü canlıdaki iki strateji 5m/15m ailesinden geldi; bu madde tek başına gerekçe değil.
5. **Sonuç zaten aday üretemez.** Lider politikası bu kümeyi ana BH ailesinin dışında, ayrı raporlanan bir aşama olarak tanımladı. Yani en iyi durumda bilgi notu çıkar.
6. **İş yükü orantısız.** Dosya medyanı 1.300 satır, toplam yaklaşık 150.000 satır; her biri için uyarlama + sentetik test + kod denetimi + kapı 6 simülatörünün kâra bağlı çok dallı çıkışları desteklemesi gerekir.

RSI_Futures için emin değilim (ailelerin dışında, 1h, stopu gerçek); 30 dakikalık kaynak okumasıyla karar verilsin.

Kullanıcı yine de "bir bakalım" derse: aile başına yukarıdaki 5 temsilci, bilgi amaçlı, aday üretmeyen ayrı bir not olarak. Tavsiyem bu da yapılmasın; aynı soruyu 277 içindeki ata sürümler daha temiz yanıtlıyor.

## 6. Ön kayıt taahhütleri ve uyumlu çıkış

Ön kayıtta bu satırlar için açık taahhütler var:

- Ana metin: `aday_listesi.csv` (4.773 satır) kapalı kümedir; "D/iz satırları otomatik koşulacak strateji değildir; bunlar kapalı inceleme kümesidir"; "**Her satırın kararı ve eşlemesi kayda geçer**"; "Bağlar ve dışlananlar koşudan önce `k3_karar.csv` / `k4_karar.csv` ile mühürlenir."
- Ana metin, son bölüm: "İlk gerçek veri koşusu, satır sayısı denetimleri ve bütün uygun kodlar hazır olmadan çalıştırılamaz." Ek 4 aşamalı koşuyu getirdi ama bu cümleyi açıkça kaldırmadı; aşama 1 şu an K3/K4 bitmeden koşuyor. Bu, ek 5'te açıkça kayda geçirilmeli.
- Ek 4: "Aşama 2: Robotic (HAM:B001), COK_KOLLU, K3/K4/K5'in kalan katmanları."
- Ek 1: Koşulmayan kayıtlar BH ailesine girmez. Yani kapsam dışı bırakmak aşama 2 ailesini küçültür, kimseyi cezalandırmaz.

Kapsam daraltmak ön kayıtla uyumludur, şu şartlarla:

1. **Zamanlama:** Ek 5 ve bu triyaj dosyaları, aşama 1 sonuçları açılmadan önce commit edilmeli (SHA-256 ile). Aşama 1 şu an koşuyor; sonuç görüldükten sonra yazılan bir daraltma "sonuç sonrası" etiketi taşımak zorunda kalır.
2. **Her satır yine bir karar alır**, ama dürüst etiketle: yeni karar kodu `KAPSAM_DISI_TRIYAJ`. Bu satırlar `KURAL_YOK` diye yazılmaz, çünkü incelenmediler.
3. **Raporda açık cümle:** "X satır tek tek incelenmedi; popülasyon triyajıyla kapsam dışı bırakıldı." "Her satır incelendi" iddiası yapılamaz.
4. **Geri dönüş yok:** Kapsam dışı bırakılan satır bu turda sonradan geri alınmaz.

### Önerilen ek metni (ön kayda aynen eklenebilir)

> ## Ön kayıt düzeltmesi — sonuç görülmeden (5): aşama 2 kapsam triyajı
>
> Tarih: 2026-11-13. Kullanıcı yönlendirmesiyle ("test etmemize gerek olmayanları çıkaralım"); aşama 1 koşusu sürerken, aşama 1 dahil hiçbir kapanış sonucu görülmeden yazıldı. Yukarıdaki metinler korunur; bu ek, ana metindeki "her satırın kararı kayda geçer" ve "bütün uygun kodlar hazır olmadan çalıştırılamaz" cümlelerini ve ek 4'teki aşama 2 tanımını aşağıdaki biçimde daraltır.
>
> - **Dayanak:** `eleme/TRIYAJ_FABLE_ASAMA2.md` ve `eleme/triyaj_asama2.csv` (SHA-256 bu commit'te). Triyaj yalnız kaynak türü, önceki karar tabloları ve hesap defterindeki arşiv akıbetinden yapıldı; mum verisi ve koşu sonucu kullanılmadı.
> - **Aşamalı koşu kaydı:** Aşama 1, K3/K4/K5 incelemesi tamamlanmadan başlatıldı. Ek 4'ün aşama tanımı bunu kapsar; ana metnin "bütün uygun kodlar hazır olmadan çalıştırılamaz" cümlesi aşama bazında uygulanır.
> - **Kapsam dışı bırakılanlar:** `triyaj_asama2.csv` içindeki K3-6, K3-7, K4-5, K4-8, K4-9, K4-10, K5-5b alt kümeleri (1.759 satır) ve COK_KOLLU kümesinin CK-1…CK-6 satırları (86 dosya) satır satır incelenmez ve koşulmaz. Karar tablolarında `KAPSAM_DISI_TRIYAJ` kodu ve alt küme adıyla kaydedilir (K4-5 için ayrıca mevcut kullanıcı kararı: kesitsel/pairs/rotasyon evren dışı). Bu kod "kural yok" ya da "test edildi, elendi" anlamına gelmez. K3-5b'deki 4 kimlik, aşama 1 ön elemesiyle aynı ölçütlerle (`eleme/ELEME_FABLE.md`) koşu listesine alınmaz.
> - **Kapalı sayılanlar:** Daha önce karar verilmiş satırlar mevcut kararlarıyla kalır. K5 iz satırları bağlı oldukları ana kimliğin kararını betikle devralır.
> - **Aşama 2'nin yeni tanımı:** (a) Robotic KOSULACAK satırlarının ayrı hakem elemesinden geçenleri; (b) `triyaj_asama2.csv` içinde KOŞ olan kimlikler; (c) İNCELE alt kümelerinden, incelemede kuralı tam bulunanlar. (c) için inceleme kararları aşama 2 koşusundan önce mühürlenir.
> - **BH:** Aşama 2 ailesi yine dondurulmuş aşama 2 koşu listesidir (ek 4). Kapsam dışı satırlar aileye girmez.
> - **Rapor yükümlülüğü:** Nihai rapor, kapsam dışı bırakılan satır sayısını alt küme bazında ve "incelenmedi" ifadesiyle verir. Bu satırlar bu turda sonradan kapsama alınmaz.
> - Kapılar, çarpanlar, evren ve ikinci kapı değişmez.

## 7. Kullanıcıya sorulması gereken kararlar

1. **Robotic (B001) aşama 2'de kalıyor mu?** "Freqtrade 909 stratejisinden bahsetmiyorum" sözü B001'i kastediyorsa 277 + 48 KOSULACAK ve 87 COK_KOLLU'nun tamamı düşer; aşama 2'nin en büyük kodlama işi (yaklaşık 325 yeni sınıf, 165'i 5m) ortadan kalkar. Tek başına en çok zaman kazandıran karar bu.
2. **COK_KOLLU tümden çıksın mı?** Önerim evet (bilgi amaçlı 5 temsilci dahil yapılmasın).
3. **Kapsam daraltma (ek 5) onayı:** 1.763 satırın incelenmeden kapatılması. Bedeli: raporda "her satıra bakıldı" denemeyecek.
4. **İsteğe bağlı küçük kümeler:** K4-7 (geçmiş sınıfların 16 varyantı) ve K5'teki 6 v3 kartı. İkisi de atlanabilir; atlanırsa kalan inceleme 121 satıra iner.

## 8. İş yükü (kaba tahmin)

Dayanak: şimdiye kadarki tempo (parti başına 221–227 satır; kullanıcı listesinde 317 yeni sınıf 8 kodlama partisi; koşu kayıt başına 2–10 CPU dakikası, 4 çekirdek). Bunlar ölçüm değil tahmindir.

| İş | Tam yol | Triyaj sonrası |
|---|---|---|
| K4 kararsız 1.279 satır | 6 inceleme partisi + 1–2 kodlama partisi + denetim + koşu ≈ 10–15 saat | 129 satır ≈ 1–1,5 saat; çoğu mevcut sınıf, koşu < 1 saat |
| K3 kararsız 319 + p06 yeniden | ≈ 2,5 parti + küçük kodlama ≈ 4–5 saat | 13 hipotez ≈ 1,5–2 saat kodlama + ≈ 15 dk koşu |
| K5 621 iz | elle bağlama ≈ 3–4 saat | betik ≈ 30 dk + 14 satır ≈ 1 saat |
| COK_KOLLU 87 dosya | ≈ 150.000 satır uyarlama: günler | 0 (RSI_Futures 30 dk) |

Toplam kazanç: Robotic hariç yaklaşık **15–20 saat** boru hattı süresi, artı COK_KOLLU'nun günler süren uyarlaması. Kalan iş: yaklaşık 4–6 saat.

## 9. Bu raporun sınırları

- Satır kararı verilmedi; alt küme sayıları karar dosyalarının birleştirilmesiyle üretildi. Birleştirme önceliği lider kuralına göre uygulandı (`duzeltme_fable2` > `derin_erisim` > değişen `_v2` > `derin_*`/`k6` > `kul_*` > `k3_p*`); resmi birleştirme betiğiyle birkaç satır farklı çıkabilir.
- "Sınıf aşama 1'de koşuyor" eşlemesi sınıf adı düzeyinde yapıldı; aynı sınıfın hangi ayarla koştuğu satır satır karşılaştırılmadı.
- Verim tahminleri (≤%2 vb.) kabul edilmiş partilerdeki oranlardan türetildi; kapsam dışı bırakılan 1.763 satırın içinde koşulabilir birkaç kural bulunması olasıdır. Öneri, bunların aranmasının maliyetine değmediği yönündedir, "hiç yok" iddiası değildir.
- COK_KOLLU stop ve satır sayıları scratchpad'deki depo kopyasından; bu kopyanın karar dosyalarındaki commit ile aynı olduğu doğrulanmadı.
