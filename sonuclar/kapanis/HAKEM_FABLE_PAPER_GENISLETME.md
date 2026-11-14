# Bağımsız hakem (Fable) — paper'a daha fazla strateji eklenmeli mi?

Tarih: 2026-11-14. Kod ve sonuç dosyaları değiştirilmedi. Kaynak: `ileri_sinav/`, `ileri_sinav_ek11/`, `ileri_sinav_ek12/`,
`ileri_sinav_ek12_pf/` (sonuc.csv + JSON'lardaki sembol bazlı R), önceki raporlarım (`HAKEM_FABLE_SONUC_ASAMA1.md`, `..._ASAMA2.md`).
Yeniden oynatma yapmadım; aşağıdaki sayılar bu dosyalardan hesaplandı.

Soru: "İleri dönem sınavında iyi sonuçlar varsa neden yalnız 6 tane ekliyoruz?"

## Kısa yanıt

**En çok 2–3 hesap daha eklemeye değer (730, 259; istenirse 538). 30'unu eklemek zarar vermez ama bilgi de katmaz; elenen 414'ten hiçbiri eklenmesin.**
Neden: "30 strateji sınavı geçti" cümlesi olduğundan iyi görünüyor. Üç sebep:

1. **Sınav çıtası düşüktü.** Geçmek için: zarar etmemek, kill olmamak, (yalnız long ise) −%18,7'lik al-tut'u geçmek yeterli.
   Geliştirmede *elenen* günlük long stratejilerin de %55'i (124'te 68) bu sınavı geçti. Yani "geçti" tek başına "iyi" demek değil.
2. **30 geçen 30 ayrı başarı değil, aynı bahsin tekrarları.** 41 adayın sınav yılındaki toplam kazancı sembollere bölününce:
   ZEC +90R, ETH +54R, BTC +49R; 13 sembolün 5'inde toplam eksi. Yani bir-iki coin'in iyi yılı 30 satıra dağılmış.
   Örnek: 705 (paper'da) ZEC çıkarılınca eksi (5,4R'nin 9,9R'si ZEC); 37 ve 538 de öyle.
3. **Paper'ın işi "kim kazandı"yı bulmak değil, uygulamayı ve farklı fikirleri izlemek.** Aynı fikrin 10 kopyası aynı gün kazanır, aynı gün kaybeder.

## 1. Daha fazla eklemenin faydası / zararı

| | |
|---|---|
| Fayda | Hesap neredeyse bedava (ayrı sanal kasa, gerçek para yok). Farklı bir fikir eklenirse yeni bilgi gelir. |
| Zarar 1 — bilgi yok | Aynı faktörün kopyası (haftalık korelasyon 0,6–0,95) yeni bir şey söylemez; pano kalabalıklaşır, izlemek zorlaşır. |
| Zarar 2 — seçim yanlılığı | Sınav sonucunu gördükten sonra "iyi çıkanı" seçersek, o iyi sonucun bir kısmı şanstır ve 12 haftada geri gider. Kaç tane çok hesap açarsak, 12 hafta sonunda içlerinden birinin sırf şansla "çok iyi" görünme olasılığı o kadar artar. |
| Zarar 3 — "kazanan" iddiası zayıflar | 16 hesaptan en iyisi ile 46 hesaptan en iyisi aynı şey değildir. Hesap sayısı arttıkça "en iyi olan gerçekten iyi" demek için gereken kanıt da artar. |

Gruplar arası dürüst karşılaştırma (günlük mum, sınav yılı, maliyet ×2):

| Grup | Sayı | Geçen | Medyan net | Net > %10 |
|---|---|---|---|---|
| Paper adayları (1d) | 32 | 24 (%75) | +%5,3 | 10 |
| Elenenler (1d) | 191 | 86 (%45) | −%1,0 | 17 |

Adaylar grup olarak elenenlerden daha iyi çıktı (rastlantı olasılığı kabaca binde 1–2; ama adaylar birbirinin kopyası olduğu için gerçek kanıt
bundan zayıf — 32 bağımsız deneme değil, yaklaşık 5 alt biçim). Bu, geliştirme kapılarının *bir miktar* işe yaradığını gösterir; tek tek stratejiler için kanıt değildir.

## 2. 41 adaydan hangileri eklenmeye değer?

Ölçüt (üçü birden): (a) ileri dönemi geçti, (b) önceki raporumda "şüpheli" değil, (c) mevcut 6'nın (664, 705, 301, 138, 670, 574) kopyası değil / farklı bilgi katıyor.

**Eklenmeye değer:**

| Kimlik | Neden | Çekince |
|---|---|---|
| **HAM:X005:730#v2** (OBV momentum, 1d, iki yönlü) | Aşama 1 raporumda E kümesinin temsilcisi olarak sonuç görülmeden adı geçmişti; bu küme paper'da hiç yok. Sınavın en iyisi: net +%21,6, düşüş %5,1, 115 işlem. Kazanç ZEC'e bağlı değil (ETH, XRP, BNB, SOL, BTC). | Geliştirmede short bacağı zarardaydı (−12R). Sınav yılında short'un para kazanıp kazanmadığını **bilmiyorum** (dosyada yön ayrımı yok). Paper tam bunu gösterir. |
| **HAM:X005:259#v1** (Bollinger 1σ + RSI, 1d, long) | Aşama 1'de "en iyi 20 işlem çıkınca hâlâ artıda" kalan 3 adaydan biri (diğer ikisi 664 ve 705, zaten paper'da). Sınavda +%10,4, düşüş %6,1; kazanç 13 sembole en dengeli dağılan aday, ZEC katkısı sıfıra yakın. | Aşama 1 notum "zayıf"tı (2022–25 yalnız +13R). C kümesinde (664/705 ile aynı aile); dengeli dağılım gözlemi sonuç sonrası. |

**İsteğe bağlı (üçüncü):** **HAM:B001:538#v1** (Keltner kırılım, 6h). Paper'da 6h ve kırılım tipi yok; 664/705 ile korelasyon orta (0,5).
Ama sınav kazancı (+%5,8) ZEC çıkınca sıfıra iniyor. Aşama 2'de "eklenmesin" demiştim; hesap bedava olduğu için "izlenebilir"e yumuşatıyorum, şart değil.

**Eklenmesin (geçtiği hâlde):**

| Kimlikler | Neden |
|---|---|
| L15#2#v4, 144, 844, 395#1, 809, A002:6 | Önceki raporlarda **şüpheli** (tek işlem/tek yıl/tek coin bağımlılığı, kıyastan muaf geçiş). Sınavda iyi çıkmaları bu notu silmez; A002:6 ve L15#2#v4'ün sınav kazancı da ağırlıkla tek-iki coin. |
| 194, 37, 421, 718, H007:48, V014:255 | 664/705'in kopyası (C kümesi, korelasyon 0,6–0,93). 37'yi MACD temsilcisi olarak önceden anmıştım, ama sınav profili 705 ile aynı (ZEC + HYPE; ZEC çıkınca eksi): yeni bilgi yok. 194'ü "37'den iyi çıktı" diye seçmek tam sonuç sonrası seçim olur. |
| 79, 346 | 730 ile aynı küme (E); 730 temsil ediyor. |
| 725 | 301 ile aynı küme (D); kıyastan muaf geçmişti. |
| momentum-sıfır, 181, 779 | B kümesi (kırılım). Kümenin önceden seçilmiş temsilcisi 481 sınavı **geçemedi**, 76 −%25 yaptı; 181 ve 779 ortalama işlemde eksi (yalnız kıl payı artı). Küme bütün olarak çalışmadı; içinden iyi çıkanı almak şans seçmektir. |
| 792 | "Sonuç sonrası düzeltme" kaydı. |
| B001:105 | Dip ailesi 670/574 ile temsil ediliyor; sınavda yalnız 12 işlem. |

Etiket: mevcut 6 `kapanis_aday` olarak kalsın. Yeni eklenenler ayrı etiket alsın: **`kapanis_aday_ek`** ("sonuç sonrası seçim").
(Kodda etiket listesi sabit; yeni etiket küçük bir kod değişikliği ister — lider/kod ajanı işi.)

## 3. Ek 12 (elenen 414) — iyi görünenler eklensin mi?

**Hayır, hiçbiri.** Ek 12'nin kendi metni de böyle diyor ("keşif — kanıt değil; paper'a ancak yeni ön kayıtla").

Şans beklentisi (günlük mumlu 189 elenen kayıt; kenarı sıfır olan bir stratejinin yıllık sonucu yaklaşık ±%11 oynuyor):

| Eşik | Sırf şansla beklenen | Gözlenen |
|---|---|---|
| Net > 0 (kabaca "geçti") | 80–95 | 86 |
| Net > %10 | 25–33 | 17 |
| Net > %20 | 4–6 | 3 |

Yani elenenlerdeki "iyi görünenler"in **tamamı şansla açıklanıyor**; şansın üstünde bir fazlalık yok (hatta biraz altında).
414'ün toplamında 112 geçen var; kısa zaman dilimlerinde (5m–1h, 159 kayıt) geçen yalnız 10, çoğu maliyetten battı.
En üsttekiler (X005:8 +%61, X005:85 +%58, X005:2 +%39, X005:690 +%33) çarpıcı ama: (i) 414 denemenin en iyisi her zaman çarpıcıdır,
(ii) dördünde de en büyük kalem ZEC (15–35R), (iii) `swing__ma-kesisim` sınıfından 7 ayrı ayar geçti — aynı kuralın tekrarları.

"Keşif" etiketiyle paper'a almak da önerilmez: pano 16'dan 25–30'a çıkar, 12 hafta sonunda içlerinden biri neredeyse kesin "çok iyi" görünür ve
bu görüntü karar vermeyi zorlaştırır. İleride istenirse doğru yol: yeni ön kayıt, seçimi sonuca göre değil önceden yazılı kurala göre yapmak (ör. "1d-long-trend dışı, ≥50 işlem, sınıf başına 1"), en çok 3 hesap.

## 4. Net öneri

- **Hesap sayısı: 16 → 18** (isteğe bağlı 19). Ekle: `HAM:X005:730#v2`, `HAM:X005:259#v1`; isteğe bağlı `HAM:B001:538#v1`.
- **Etiket:** `kapanis_aday_ek` (sonuç sonrası seçim). Ek 12'den ekleme yok. Portföy kayıtlarından (ek 12 pf: 6'da 1 geçti) ekleme yok.
- Risk ayarları mevcut hesaplarla aynı (risk %0,5, kaldıraç 3, sermaye 10.000, limitler değişmez).

**Ölçüm planı — 12 hafta sonunda bakılacaklar (şimdi yazılı, sonra değişmez):**

1. **Uygulama uyumu (asıl amaç):** aynı 12 hafta backtest motoruyla yeniden oynatılır; paper işlemleri ile backtest işlemleri eşleşiyor mu
   (işlemlerin en az %90'ı aynı gün/yön), net fark küçük mü. Uymuyorsa strateji değil uygulama sorunudur.
2. **Zarar sınırı:** kill yok ve düşüş, sınav yılındaki en büyük düşüşün 2 katını aşmıyor (730: %10, 259: %12, 538: %11). Aşarsa hesap çıkar.
3. **Kopya testi:** haftalık getiri korelasyonu 664 ve 705 ile ölçülür. 0,8 ve üzeriyse "kopya" sayılır, çıkarılır (bilgi katmıyor).
4. **730 için ayrıca:** long ve short bacağın neti ayrı raporlanır. Short yine zarardaysa "fiilen long" notu kalıcı olur.
5. **Kazanan ilanı yok:** `kapanis_aday_ek` hesabı 12 hafta sonunda ne kadar iyi görünürse görünsün canlı adayı olmaz; en fazla `kapanis_aday`
   düzeyine yükselir ve ikinci bir 12 hafta ister. Ana karşılaştırma ilk 6 üzerinden yapılır; ek hesaplar ayrı tabloda raporlanır.
6. **Beklenti:** 12 haftada işlem sayısı az olacak (730 ~25, 259 ~15, 538 ~50). Net küçük artı/eksi çıkması ne lehte ne aleyhte kanıttır.

## Bilmediklerim

- Sınav yılında adayların haftalık korelasyonlarını (JSON'larda işlem listesi yok, yeniden oynatmadım; küme bilgisi geliştirme dönemine ait, sembol profili ile destekledim).
- İki yönlü adayların (730, 79, L15#2#v4, 809…) sınav kazancının long'dan mı short'tan mı geldiğini.
- Şans tablosundaki ±%11'i elenenlerin kendi dağılımından aldım; kaba bir tahmindir, kesin bir istatistik testi değil.
- Sınav dönemi verisi önceki turlarda görülmüştü (ek 10–12 "sapma" kaydı); bu sınav temiz bir kanıt değil, yalnız "gerekli, yeterli değil" süzgecidir.
- 730, 259 ve 538'in paper motorunda çalışıp çalışmadığını (çıkış kancaları vb. fail-closed kontrolü) denetlemedim; ekleme öncesi kod tarafında bakılmalı.

## Ek: 20. hesap

Kullanıcı kararı: paper 20 hesap = 16 + 730, 259, 538 + 1 "niş" aday (41 adaylık havuzdan; ek 12'den değil).

**Seçim: `HAM:X005:793#v1`** (MACD sinyal oranı, 1d, iki yönlü). Etiket: `kapanis_aday_ek`.

- **Neden niş:** aşama 1 kümelemesinde **tekil** çıkan (hiçbir kümeyle haftalık korelasyonu 0,6'ya ulaşmayan) beş adaydan biri; diğer dördü ya paper'da (138),
  ya şüpheli (395, 400), ya "sonuç sonrası düzeltme" kaydı (792). Sınav yılı profili de diğerlerinden ayrı: çoğu adayın kazancı ZEC/ETH/BTC'den gelirken
  793'ün kazancı ADA, BNB, DOGE, LINK, BCH, XRP'den; ZEC'te **eksi** (−2,4R). Net +%8,6, düşüş %6,4, 61 işlem.
- **Düzeltme:** yukarıdaki "eklenmesin" tablosunda 793'ü yanlışlıkla "664/705 kopyası" satırına yazmıştım; aşama 1 raporumda tekildir. Satır düzeltildi.
- **Çekince:** aşama 1 notum "zayıf" (2020–21 dışında toplam yalnız +7R, 2025 eksi). Adı MACD ama 194/37/421 MACD ailesiyle aynı kümeye düşmemişti; sınav
  yılındaki korelasyonunu ölçmedim. İki yönlü; short bacağının katkısını bilmiyorum. Gerçek anlamda "ortalamaya dönüş" ya da "short ağırlıklı" bir aday
  havuzda şüphesiz/kopyasız yok; 793 "farklı fikir" değil, "aynı faktörün en az benzeyen biçimi"dir.
- **Düşünülüp alınmayanlar:** 79 (6h iki yönlü; ama 730 ile aynı küme), B001:105 (1h; ama 670/574 ile aynı dip fikri, sınavda 12 işlem), 792 (tekil ama sonuç sonrası düzeltme kaydı).

**12 hafta ölçüm satırı (önceden yazılı):** bölüm 4'teki 1–3 ve 5. maddeler aynen geçerli; zarar sınırı düşüş ≤ %13 (sınav düşüşünün 2 katı); beklenen işlem ~15.
Ek olarak nişlik sınaması: 664, 705 ve 730 ile haftalık getiri korelasyonu **0,6'nın altında** kalmalı — 0,6 ve üzeriyse "niş değil" sayılır ve çıkarılır
(diğer ek hesaplarda eşik 0,8; burada hesabın var olma gerekçesi farklılık olduğu için daha sıkı). Long/short neti ayrı raporlanır.
