# Test C — Stop / çıkış teşhisi (sade anlatım)

**Soru:** 'İyi trader'lar %40 kazanmayla bile kaybı hemen keser, kârı koşturur; bizim stoplarımız nasıl?'
**Bu bir TEŞHİS:** yalnız mevcut işlemlere bakıldı (geliştirme dönemi, < 2025-11-08, maliyet ×2). Hiçbir ayar/stop değiştirilmedi, 'şöyle olsaydı' simülasyonu yok; canlı planı değiştirmez. Ön kayıt: `sonuclar/teshis/ON_KAYIT_TESHIS.md`.

## Kısa cevap

- 9 stratejiden **6'sı 'kayıp kısa / kâr uzun'** (lube, gauss-stoch-eth, haftalik-macd, uc-ortalama, jt-awesome, voltarget): %22-36 kazanıp kazançları kayıpların 3-5 katı yapıyorlar. İyi trader tarifine uyuyorlar.
- **hma-atr-rider 'karma'** ama payoff 1,93 ile eşiğin hemen altında; davranışı aynı yönde.
- **Canlıdaki iki 15 dakikalık strateji (e0v1en, ewo-ema-ofset) tersi:** 'çok kazan az kazan' (%67 kazanma, payoff 0,58-0,69), kayıpların %65-87'si tam stop. Bunlar iyi trader tarifi değil; avantajı sık küçük kazançtan alıyorlar (bu yüzden maliyete ve kayma/fiyat farkına çok duyarlılar).
- Kaybedenlerin çoğu +1R'ye bile ulaşmamış (e0v1en/ewo/gauss/hma: %0,2-3); yani 'kâr vardı, geri verdik' sorunu yok. Swing'de lube (%20), jt (%15), voltarget (%13) istisna.

## Tablo

| Strateji | TF | İşlem | Kazanma | Payoff | Beklenti (R) | Tip | Kazananların % kaçı önce −0,5R'yi gördü | Kaybedenlerin % kaçı +1R gördü | Kazananlarda geri verilen (medyan R) |
|---|---|---|---|---|---|---|---|---|---|
| e0v1en | 15m | 2461 | %67 | 0.58 | +0.04 | çok kazan az kazan | %15.2 | %2.4 | 0.03 |
| ewo-ema-ofset | 15m | 1287 | %67 | 0.69 | +0.13 | çok kazan az kazan | %15.5 | %2.6 | 0.05 |
| hma-atr-rider | 1d | 2125 | %37 | 1.93 | +0.04 | karma | %1.5 | %0.2 | 0.78 |
| lube | 1d | 175 | %36 | 4.35 | +0.71 | kayıp kısa / kâr uzun | %20.6 | %19.6 | 1.59 |
| gauss-stoch-eth | 1d | 1336 | %30 | 4.13 | +0.15 | kayıp kısa / kâr uzun | %1.0 | %2.8 | 0.94 |
| haftalik-macd-gunluk-ma | 1d | 619 | %31 | 3.42 | +0.15 | kayıp kısa / kâr uzun | %12.2 | %5.6 | 1.11 |
| uc-ortalama-boga-sma60 | 1d | 367 | %28 | 3.45 | +0.08 | kayıp kısa / kâr uzun | %3.0 | %3.8 | 1.08 |
| jt-awesome-osilator | 1d | 1851 | %34 | 3.82 | +0.36 | kayıp kısa / kâr uzun | %12.2 | %14.7 | 1.66 |
| voltarget-trend | 1d | 1421 | %22 | 5.24 | +0.17 | kayıp kısa / kâr uzun | %10.1 | %12.6 | 0.85 |

Sınıflama (ön kayıtlı): 'kayıp kısa / kâr uzun' = payoff ≥ 2 ve kazanma ≤ %45; 'çok kazan az kazan' = kazanma ≥ %60 ve payoff < 1; diğerleri 'karma'. Payoff = ort. kazanç R / |ort. kayıp R|.

## Ayrıntı tablosu

| Strateji | Ort. kazanç R | Ort. kayıp R | Kazananların MAE medyan / %75 / %90 | Kazanan %MAE≥0,5R / ≥0,8R | Kaybeden %MFE≥0,5R / ≥1R / ≥2R | Süre medyan gün (kazanan / kaybeden) | Kayıpların % tam stop / küçük |
|---|---|---|---|---|---|---|---|
| e0v1en | +0.44 | -0.75 | 0.14 / 0.37 / 0.58 | %15.2 / %2.6 | %12.0 / %2.4 / %0.4 | 0.05 / 0.07 | %65.2 / %34.8 |
| ewo-ema-ofset | +0.65 | -0.94 | 0.10 / 0.37 / 0.62 | %15.5 / %3.8 | %19.5 / %2.6 / %0.0 | 0.11 / 0.05 | %86.9 / %13.1 |
| hma-atr-rider | +0.79 | -0.41 | 0.09 / 0.22 / 0.35 | %1.5 / %0.0 | %21.4 / %0.2 / %0.0 | 18.00 / 8.00 | %2.0 / %98.0 |
| lube | +3.32 | -0.76 | 0.15 / 0.46 / 0.68 | %20.6 / %3.2 | %40.2 / %19.6 / %8.0 | 84.00 / 13.00 | %47.3 / %52.7 |
| gauss-stoch-eth | +1.18 | -0.29 | 0.06 / 0.17 / 0.27 | %1.0 / %0.0 | %17.5 / %2.8 / %0.4 | 37.00 / 6.00 | %1.8 / %98.2 |
| haftalik-macd-gunluk-ma | +1.50 | -0.44 | 0.11 / 0.32 / 0.53 | %12.2 / %1.6 | %27.9 / %5.6 / %0.5 | 30.00 / 8.00 | %11.2 / %88.8 |
| uc-ortalama-boga-sma60 | +1.18 | -0.34 | 0.03 / 0.16 / 0.28 | %3.0 / %0.0 | %19.5 / %3.8 / %0.4 | 26.00 / 4.00 | %6.4 / %93.6 |
| jt-awesome-osilator | +2.21 | -0.58 | 0.18 / 0.37 / 0.53 | %12.2 / %0.6 | %35.3 / %14.7 / %2.5 | 56.00 / 13.00 | %26.3 / %73.7 |
| voltarget-trend | +2.28 | -0.43 | 0.07 / 0.24 / 0.50 | %10.1 / %2.2 | %25.5 / %12.6 / %3.7 | 40.00 / 5.00 | %12.9 / %87.1 |

MAE = işlem sırasında lehe dönmeden önce gördüğü en kötü ters hareket (stop mesafesi = 1R). MFE = en iyi lehte hareket. 'Tam stop' = kayıp r ≤ −0,85R (ön kayıtlı).

## Her strateji için 1-2 cümle

- **e0v1en:** Çok sık kazanıyor ama kazanç küçük (ort. +0,44R), kayıp büyük (−0,75R); kayıpların %65'i tam stop. Trade'ler ~1-2 saat sürüyor. 'Kârı koşturan' değil, 'küçük kâr toplayan' tip.
- **ewo-ema-ofset:** e0v1en ile aynı yapı: %67 kazanma, payoff 0,69; kayıpların %87'si tam stop (kayıp neredeyse hep −1R). Kazançlar ~+0,65R'de kesiliyor.
- **hma-atr-rider:** Kazanma %37, payoff 1,93: eşiğin (2) hemen altında, 'karma'. Kayıpların %98'i stop'a varmadan küçük (−0,41R) çıkıyor (sinyal çıkışı); kazananlar 18 gün, kaybedenler 8 gün tutuluyor. Fiilen 'kaybı kes, kârı koştur' davranışına yakın.
- **lube:** Tam 'kayıp kısa / kâr uzun': %36 kazanma, payoff 4,35, kazananlar 84 gün tutuluyor. Ama kayıpların %47'si tam stop ve kaybedenlerin %20'si +1R görüp geri verdi. Yalnız 175 işlem (az).
- **gauss-stoch-eth:** Klasik trend takipçisi: %30 kazanma, payoff 4,13. Kayıpların %98'i stop'a varmadan küçük (−0,29R) kesiliyor; kazananlar 37 gün, kaybedenler 6 gün. Kazananlar tepeden medyan 0,94R geri veriyor (trend dönüşünü beklemek).
- **haftalik-macd-gunluk-ma:** %31 / payoff 3,42: 'kayıp kısa / kâr uzun'. Kayıpların %89'u küçük çıkış; kazananların %12'si önce −0,5R'ye inip toparlanmış.
- **uc-ortalama-boga-sma60:** %28 / payoff 3,45. Kazananlar neredeyse hiç geri çekilmiyor (medyan MAE 0,03R) ve kayıplar küçük (−0,34R).
- **jt-awesome-osilator:** %34 / payoff 3,82. Kaybedenlerin %35'i +0,5R, %15'i +1R görüp geri vermiş; kayıpların %26'sı tam stop.
- **voltarget-trend:** En uç trend profili: %22 kazanma, payoff 5,24; kayıplar küçük (−0,43R). Kaybedenlerin %13'ü +1R, %3,7'si +2R görüp kaybetmiş.

## Nasıl ölçüldü ve sınırlar (önemli)

- **Giriş fiyatı ham dosyada yok.** Motor girişi, işlem zaman diliminin giriş mumunun açılışında doldurur; giriş fiyatı = o mumun açılışı (en ince fiyat serisinden: kripto 5 dk, hisse/emtia 1 saat). Kayma payı (birkaç baz puan) hariç.
- **Alt sınır:** MAE/MFE yalnız giriş mumundan sonraki ve çıkıştan önceki mumlara bakar; giriş ve çıkış mumunun kendi içindeki hareketler dışarıda. Gerçek MAE/MFE bunlardan **büyük veya eşittir**. Boş pencere (çok kısa işlem) = 0 sayıldı: oran (%) bu işlemlerde aşağı yanlı. Boş pencere payı: e0v1en %12,6, ewo %13,8, gauss %24,3, haftalik-macd %18,1, hma %6,2, jt %7,3, lube %4,0, uc-ortalama %30,8, voltarget %34,3 (günlük stratejilerde işlem 2-3 gün sürerse pencere boş kalır).
- 'Önce −0,5R'yi gördü' = çıkıştan önce bir anda ulaştı; sıra (önce mi sonra mı) ölçülmedi.
- Veri: maliyet ×2 ham sonuçları (v2 ham/x2), her sembol birlikte (kripto + hisse + emtia). 'Tam stop' kayıplar −0,85R'den kötü olanlar; boşluk (gap) kayıpları da buna girer.
- Veri sonunda zorunlu kapanan işlemler dahil (e0v1en 1, hma 2, lube 7, gauss 8, haftalik-macd 1, jt 13, voltarget 17).
- pf__sabit_sepet portföy olduğu için bu testte yok.

## SONUÇ SONRASI DEĞİŞİKLİK

İlk koşu sonuçları görüldükten sonra denetimde bir hata buldum ve **pencere kuralını düzelttim** (ayrıntı: ON_KAYIT_TESHIS.md 'Ek-2'). Motor, mum-içi stop/hedef ve veri sonu çıkışlarını mumun BİTİŞ anıyla damgalıyor; ilk pencerem stop'un vurduğu çıkış mumunu da içeriyordu. Belirti: e0v1en/ewo kaybedenlerinin %26-29'unda MAE ≥ 1,2R görünüyordu (r ≈ −1,06R iken), yani stop'tan sonraki fitil MAE'ye giriyordu. Düzeltilmiş pencere: giriş mumundan sonra → (çıkış damgası − 1 mum). Düzeltme sonrası bu tutarsızlık sıfır (kaybedenlerde MAE ≥ 1,2R: %0,0-0,1). Düzeltme yalnız Test C'yi etkiledi; ilk koşunun çıktıları `sonuc_ilk_kosu.csv` / `ozet_ilk_kosu.json` olarak duruyor. Karşılaştırma (ilk → düzeltilmiş) kazananlarda %MAE≥0,5R: e0v1en 15.3→15.2, ewo-ema-ofset 15.7→15.5, hma-atr-rider 2.4→1.5, lube 20.6→20.6, gauss-stoch-eth 1.0→1.0, haftalik-macd-gunluk-ma 12.2→12.2, uc-ortalama-boga-sma60 5.0→3.0, jt-awesome-osilator 12.2→12.2, voltarget-trend 10.1→10.1; tip sınıflaması (kazanma, payoff) hiçbir stratejide değişmedi (bu ölçüler MAE/MFE'ye bağlı değil). Ayrıca, ilk denemede tarih doğrulaması 'çıkış = 2025-11-08 00:00' damgasında (veri sonu zorunlu kapanış) durmuştu; kural Ek-1'de genişletildi (fiyat verisi < 2025-11-08 sert kalır).

## Denetim (elle kontrol)

Düzeltilmiş pencere kuralıyla, iki stratejiden (lube, ewo-ema-ofset) 3'er rastgele işlem için giriş fiyatı, pencere ve MAE/MFE mum dosyasından (veri/mumlar) betikten bağımsız pandas kodu ile yeniden hesaplandı; hepsi betikle 4 haneye kadar aynı:

| İşlem | Giriş fiyatı | Pencerede en düşük / en yüksek | MAE / MFE (elle) | MAE / MFE (betik) |
|---|---|---|---|---|
| lube DK_AAPL 2021-07-06→2021-08-12 long | 140,046 | 140,666 / 149,987 | 0 / 1,5509 | 0 / 1,5509 |
| lube ETHUSDT 2022-06-11→2022-08-13 short | 1661,95 | 878,04 / 1943,0 | 0,7386 / 2,0602 | 0,7386 / 2,0602 |
| lube DK_AAPL 2019-10-11→2020-03-06 long | 58,222 | 58,379 / 81,954 | 0 / 5,9331 | 0 / 5,9331 |
| ewo ADAUSDT 2019-07-15 00:30→03:15 long | 0,05509 | 0,05561 / 0,0590 | 0 / 1,4481 | 0 / 1,4481 |
| ewo SOLUSDT 2021-09-14 21:30→23:00 long | 142,982 | 145,25 / 151,0 | 0 / 0,7159 | 0 / 0,7159 |
| ewo TRXUSDT 2021-11-26 08:30→13:45 long | 0,09251 | 0,09015 / 0,09305 | 0,6962 / 0,1593 | 0,6962 / 0,1593 |

Not: Bu elle kontrol hesabı aynı mantığı bağımsız kodla tekrarlar; giriş fiyatının motorun gerçek dolum fiyatıyla (kayma dahil) birebir aynı olduğunu kanıtlamaz. İlk koşudaki denetim (3 işlem) ayrıca yukarıdaki çıkış-damgası hatasını ortaya çıkardı.

Ham işlem düzeyi MAE/MFE tablosu `islem_mae_mfe.parquet` (yerelde, repoya eklenmedi).
