# Bağımsız hakem (Fable) — kapanış aşama 2 sonuç denetimi

Tarih: 2026-11-14. Kod ve sonuç dosyaları değiştirilmedi. 10 paper adayı kendi betiğimle yeniden oynatıldı (salt okuma; betikler oturumun
geçici klasöründe `hakem2/r1.py, a1–a3.py, kes.py, g1.py`, repoya yazılmadı). Kaynak: `sonuc_asama2.csv`, `kosu_asama2/*.json`, `_ikinci/*.json`.
Ölçütler aşama 1 raporuyla (`HAKEM_FABLE_SONUC_ASAMA1.md`) aynıdır.

## Kısa hüküm

- **Hata/sızıntı bulunmadı.** 10/10 kayıtta net getiri JSON ile aynı çıktı. Kesme testi 10/10 temiz. Maliyet ×2 doğru uygulanmış.
- **10 aday 10 keşif değil, 2 fikir:** (a) 6 kayıt aynı "çöküş mumundan sonra dip alımı" ailesi (5m: 558, 561, 573, 574, 670; 1h: 105),
  (b) 4 kayıt aşama 1'deki günlük/6h long trend faktörünün yeni biçimleri (A002:6, H007:48, V014:255, 538).
- **Yeni olan tek şey dip alımı ailesi.** Aşama 1 temsilcileriyle haftalık korelasyonu 0,0–0,3: gerçekten farklı bir getiri kaynağı.
  Ama kârın %56–83'ü 2021'den, kâr dağılımı ters çarpık (çok sayıda küçük kazanç, seyrek −%15…−%35 stop) ve 2022 sonrası kanıt ince.
- Ön tahminim ("5m'de umut yok, EWO zayıf umut") kısmen yanlış çıktı: 5m ailesi kapıları geçti ve geçişi bir hataya bağlayamadım.
  "Zayıf umut, aynı veride bulunmuş fikir" kısmı duruyor. **"Güçlü" aday yok**; görülmemiş veride kanıtı olan aday yine 0.

## 1. Özel şüphe: 5m kayıtlar maliyet ×2'de nasıl kârlı?

Kısa yanıt: bunlar sık işlem yapan scalper değil. 12 sembolde 6,3 yılda 690–1.354 işlem (sembol başına yılda 9–18). Her işlem, 5 dakikada
ortalama −%1,9…−%3,5 düşen bir mumdan sonra alıp %1,5–2,5'lik tepkiyi hedefliyor. Maliyet (gidiş-dönüş ~%0,33) bu hedefin yanında küçük.

| Kayıt | İşlem | Net ort. %/işlem (×2) | Medyan | Kazanma | En kötü | Medyan süre | Net−brüt (medyan) | ×2−×1 farkı |
|---|---|---|---|---|---|---|---|---|
| 558 | 690 | +1,18 | +2,49 | %84 | −%19,1 | 85 dk | −%0,335 | %0,169 |
| 561 | 1.354 | +0,57 | +1,04 | %69 | −%30,7 | 35 dk | — | %0,164 |
| 573 | 1.067 | +0,73 | +1,43 | %81 | −%15,8 | 50 dk | −%0,329 | %0,167 |
| 574 | 816 | +1,39 | +2,52 | %87 | −%30,9 | 60 dk | −%0,334 | %0,165 |
| 670 | 1.301 | +1,01 | +1,47 | %75 | −%35,4 | 40 dk | −%0,327 | %0,163 |

- **Maliyet doğru:** açılıştan açılışa brüt getiri ile net getiri farkı işlem başına medyan %0,33; ×1 ile ×2 koşusu farkı %0,16–0,17 (yani ×1 ≈ %0,16, ×2 ≈ %0,33).
- **Kancalar kapanış bazlı, gelecek bilgisi yok:** motor (`motor/backtest/motor.py`, adım 6) ROI, geri çekilme ve `pozisyon_cikisi` kancasını mumun
  kapanışında değerlendiriyor, çıkış sonraki mumun açılışında. Kancalar (`_iz_ihlali`, `_iz_stop`, `_pf_cik`) yalnız giriş mumundan bir önceki
  kapanışa kadar olan diziyi (`kv[bas:i]`) okuyor. Kaynak Freqtrade'de ROI/iz stop mum içi (yüksek/düşük) sınanır; buradaki uyarlama daha **tutucu**.
  ROI "0" basamağı brüt kâr ≥ 0'da çıkıyor (maliyet sonrası hafif eksi olabilir): bu da sonucu şişirmez, kısar.
- **Giriş-çıkış aynı mumda:** 10 kayıtta 0 işlem. En kısa tutma 1 mum.
- **−0,99 → ATR×3 uyarlaması bu 5m adayları etkilemiyor:** beşinde de kaynak stop −%15…−%35 ve aynen korunmuş (558 −%17,9; 561 −%30,2;
  573 −%15; 574 −%30; 670 −%35; 105 −%31,1; 538 −%25,4). ATR×3 yalnız H007:48 ve V014:255'te var.
- **Kesme testi:** 558, 573, 574, 670 (DOGE, BTC; 558'de XRP de) × 2 kesim (2022-06-03, 2024-03-11): 404–619 işlem karşılaştırıldı, 0 fark.
  105, 538, A002:6, H007:48, V014:255 için 3 sembol × 2 kesim: 0 fark. 561 kesme testine sokulmadı (558 ile aynı `_OfsetEwo` sınıfı, yalnız parametreleri farklı; ayrıca sınanmadı).
- **Bir mum geç giriş (kendi yaklaşık hesabım, brüt):** 670 %1,09 → %0,98; 558 ve 574 değişmiyor; **573 %1,31 → %0,77** (kenarın ~%40'ı ilk mumda).
  Yani kâr yalnız "çöküş mumunun hemen ardındaki açılış fiyatını yakalamaya" bağlı değil; 573 hariç.
- **Ek maliyet duyarlılığı (işlem başına ek kayıp):** +%0,5'te hepsi artıda kalır (561 hariç: 2022+ eksiye döner). +%1,0'da 558, 573, 670 sıfıra iner,
  574 (+%0,39) ve 105 (+%0,90) kalır. Çöküş mumunda gerçek kayma 2–4 baz puandan büyük olabilir; ne kadar olduğunu **bilmiyorum**, paper'ın ölçeceği şey budur.

**Asıl zayıflıklar (hata değil):**
1. **2021 yığılması.** İşlemlerin %47–55'i ve R'nin %56–83'ü 2021'de (558 %65, 561 %83, 573 %59, 574 %56, 670 %58). 2021 hariç Sharpe 0,80–1,29 (670: 2,54).
2. **2022 sonrası ince:** 558 176 işlem +8,7R; 561 303 işlem **0,0R**; 573 283 işlem +18,4R; 574 229 işlem +11,8R; 670 376 işlem +8,5R; 105 52 işlem +3,4R.
3. **Ters çarpıklık.** En iyi 20 işlem çıkarılınca hepsi artıda kalıyor (558 +33, 573 +26, 574 +30, 670 +28) ama bu ölçüt bu aile için anlamsız: kazançlar
   zaten tavanlı. Doğru soru "kaç fazladan tam stop kârı siler": 2022+ kârı 558 ve 670'te ~9, 574'te ~12 fazladan stopla sıfırlanır. Gözlenen büyük kayıp
   (< −%10) sayısı: 558 53, 573 93, 574 28, 670 9, 561 14. Kuyruk oranı az örnekten tahmin ediliyor.
4. **Aynı gün çoklu giriş.** Çöküş günlerinde semboller birlikte sinyal veriyor: en kötü gün 573 −4,8R, 558 −4,1R (2021-05-19), 105 −3,9R.
5. **40 sembolde kenar neredeyse sıfır:** ikinci kapı ortalaması 561 0,005R, 574 0,007R, 670 0,011R (558 0,047R, 573 0,072R). Aynı aileden birinci kapıyı
   geçen 5 kayıt daha (564, 570, 590, 205, 673) ikinci kapıda **eksi** ortalamayla kaldı. Aile 12 sembol dışına iyi taşınmıyor.
6. **Kaynak parametreleri.** Bildiğim kadarıyla bu Freqtrade stratejileri (ElliotV, NASOS, SMAOffset) topluluk tarafından 2021 verisinde hyperopt ile
   ayarlandı (0,978; 4,471 gibi değerler bunun izi). Doğruysa 2021 kaynak için de örneklem içidir, 2022+ ise kaynak açısından örneklem dışıdır. Yayın tarihlerini doğrulamadım.

## 2. Aşama 1 ölçütleri

**Kapı 5 ve dengeli al-tut (Sharpe 1,11):** 558 1,61; 561 1,17; 573 1,31; 574 2,00; 670 1,92; 105 1,12; 538 1,25 geçer.
H007:48 0,94 ve V014:255 0,86 (0,854'ü 0,008 farkla geçti) dengeli kıyasta **kalır**. A002:6 iki yönlü sayıldığı için kapı 5'ten muaf; Sharpe 0,74 (0,854'ün de altı),
short bacağı 180 işlemde −12,2R (fiilen long). Not: dip ailesinin Sharpe'ı çoğu günü sıfır olan gerçekleşmiş seriden; al-tut ile birebir kıyas değil.

**En iyi 5/10/20 işlem çıkarılınca kalan R, yığılma, dönem sonu açık işlem:**

| Aday | ΣR | T5 | T10 | T20 | En iyi yıl | En iyi sembol | 2022+ R | Dönem sonu açık |
|---|---|---|---|---|---|---|---|---|
| A002:6 (1d) | 165 | 44 | 13 | **−23** | 2025 %45 | ZEC %42 | 109 | **72R (ZEC)**; tek işlem 70R |
| H007:48 (1d) | 90 | 38 | 10 | **−28** | 2020 %57 | BNB %20 | 30 | 2R |
| V014:255 (1d) | 107 | 39 | 17 | **−11** | 2024 %42 | XRP %33 | 49 | 2R |
| 538 (6h) | 84 | 43 | 25 | +5,5 | 2021 %38 | XLM %18 | 44 | 1R |
| 105 (1h) | 16 | 12 | 9 | 6 | 2021 %54 | ZEC %24 | 3,4 | 0 |

538'de tek ay (Kasım 2024) 24,8R; en iyi 10 gün 65R/84R. 105 yalnız 72 ayrı günde işlem yaptı, 2023'te hiç işlem yok.

**Kümeleme (haftalık piyasa-değerli R korelasyonu; aşama 1 temsilcileri 664, 705, 301, 138, 481 ile):**
- H007:48: 0,58–0,73 (138 ile 0,38). V014:255: 0,58–0,71. → aşama 1 kümesi C/D'nin kopyaları.
- A002:6: 481 ile 0,67, 301 ile 0,48. → küme B (ZEC 2025 açık işlemine bağlı kırılım).
- 538: 664 ile 0,53, 705 ile 0,51. → aynı faktör, orta bağlı.
- Dip ailesi: aşama 1 temsilcileriyle −0,13…+0,31. Aile içi: **561–670 0,92; 558–574 0,75**; 558–573 0,48; 670–574 0,12; 105 diğerleriyle 0,13–0,41.
  Aylık ölçekte aile içi 0,45–0,95 ve trend adaylarıyla 0,1–0,6 (2021 hepsini birlikte taşıyor).

## 3. Aday aday

| Aday | Not | Gerekçe |
|---|---|---|
| 670 NASOS-SMA ofset (5m) | orta | Ailenin en temizi: 7 yılın 7'si ≥ 0, yalnız 9 büyük kayıp, 2022+ 376 işlem +%0,79/işlem; ama 2021 %58, 40 sembolde 0,011R |
| 574 NASOS v5 mod1 (5m) | orta− | 2022+ +11,8R, +%1 ek maliyete dayanıyor; −%30 stop kuyruğu, 40 sembolde 0,007R |
| 558 ElliotV2 (5m) | orta− | 574 ile 0,75 korelasyon (ayrı aday sayılmamalı); 2021 %65, 2022+ Sharpe ~0,5–0,7 |
| 573 NASOS v5 (5m) | orta− | 2022+ en yüksek (+18,4R) ve 40 sembolde 0,072R; ama bir mum geç girişte kenarın ~%40'ı gidiyor, en derin düşüş %15, 2025 eksi |
| 538 Keltner kırılım (6h) | orta− | T20 +5,5, 2022+ 44R, Sharpe 1,25; ama trend faktörünün bir biçimi, Kasım 2024 tek ay 25R, 40 sembolde 0,010R |
| 105 Overwatch (1h) | zayıf | Aynı dip fikri; 72 işlem günü, 2022+ 52 işlem, ikinci kapı n=434; örneklem çok küçük |
| 561 ElliotV5HO (5m) | zayıf | 670'in kopyası (0,92); 2022+ ΣR 0,0; +%0,2 ek maliyette 2022+ eksi |
| H007:48 RSRS eğim (1d) | zayıf | Aşama 1 kopyası (0,73); T20 −28; dengeli al-tut altında (0,94) |
| V014:255 RSI5 (1d) | zayıf | Aşama 1 kopyası (0,71); T20 −11; kapı 5 marjı 0,008; XRP %33 |
| A002:6 Elder impulse (1d) | şüpheli | ΣR'nin 72R'si dönem sonunda zorla kapatılan ZEC işlemi; T20 −23; kapı 5'ten muaf geçti (Sharpe 0,74), short −12R |

## 4. İki aşama birlikte: paper için önerilen temsilci listesi (karar kullanıcıda)

**En çok 6:** 664, 705, 301, 138 (aşama 1, trend faktörü) + **670 ve 574** (aşama 2, dip alımı; birbirleriyle haftalık korelasyon 0,12, ailenin iki alt kolu).
- 481 listeden çıkarılabilir (A002:6 ile aynı ZEC bağımlılığı; yer dip ailesine verilsin). 5 isteniyorsa 574 de çıkar, 670 kalır.
- 558, 561, 573, 105 eklenmesin: 670/574'ün kopyası ya da daha zayıfı. H007:48, V014:255, A002:6, 538 eklenmesin: aşama 1 faktörünü tekrar ediyor.
- Dip ailesi için paper gerçekten bilgi verir: sınanacak şey kenar değil **dolum kalitesi** (çöküş mumundan sonraki açılışta gerçek kayma). Ölçüt önceden yazılsın:
  "işlem başına gerçekleşen kayma, backtest varsayımından en çok %0,5 kötü". 12 haftada beklenen işlem sayısı düşük (670 ~20–30, 574 ~15); az işlemle hüküm verilmemeli.
- Dip ailesinde risk kuralı gözden geçirilmeli: aynı gün çok sembolde giriş −4…−5R'lik gün üretebiliyor (mevcut günlük limit bunu kesiyor mu, denetlemedim).

## Bilmediklerim

- Çöküş mumlarında gerçek dolum kaymasını ve emir defteri derinliğini (backtest 2–4 baz puan varsayıyor).
- Kaynak stratejilerin yayın/optimizasyon tarihlerini (2021 hyperopt bilgisi hafızamdan; repodan doğrulamadım).
- 5m verinin erken dönemde (2019–2020) vadeli mi spot mu olduğunu ve o dönemdeki fitil/kalite sorunlarını.
- 10 sınıfın kaynak koda birebir uyduğunu (yalnız 558/561/573/574/670/538 sınıf metinlerini ve ortak kancaları okudum; kaynak dosyalarla karşılaştırmadım).
- Kapı 6 (rastgele giriş) simülasyonunun dip ailesinde ne kadar ayırt edici olduğunu (yeniden koşmadım; hepsinde p=1e-5).
- Piyasa-değerli Sharpe ve korelasyonların kesin değerini (hesabım yaklaşık: bileşiksiz, R birimi, günlük kapanışla).
- Ailenin gelecekte çalışıp çalışmayacağını; 2022–2025 kanıtı artı ama küçük ve seçim aynı veride yapıldı.
