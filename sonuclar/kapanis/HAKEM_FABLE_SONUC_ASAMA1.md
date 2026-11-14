# Bağımsız hakem (Fable) — kapanış aşama 1 sonuç denetimi

Tarih: 2026-11-14. Kod değiştirilmedi, sonuç dosyaları değiştirilmedi. 31 aday kendi betiğimle yeniden oynatıldı (yalnız okuma;
betikler oturumun geçici klasöründe `hakem/h1.py … h7.py`, repoya yazılmadı). Kaynak: `sonuc_asama1.csv`, `kosu_asama1/*.json`, `_ikinci/*.json`.

## Kısa hüküm

- **Hata/sızıntı bulunmadı**, ama **31 "paper adayı" 31 ayrı keşif değildir.** Hepsi aynı tek faktörün (kripto, günlük, long trend/momentum)
  türevleri; haftalık getirilerinde ilk ortak bileşen varyansın %50'sini açıklıyor, ortalama ikili korelasyon 0,46.
- Kâr 4 olaya yığılmış: 2020 sonu–2021 başı alt-coin koşusu, Ekim 2023 SOL, Kasım 2024 XRP, Ağustos–Kasım 2025 ZEC. 31 adayın 26'sında
  toplam R'nin yarıdan fazlası, 16'sında %77 ve üzeri bu 4 pencereden. 31 adayın 28'inde en iyi 20 işlem çıkarılınca toplam R ≤ 0
  (artıda kalanlar: 664, 705, 259).
- Yüksek geçişin asıl nedeni kapıların bu aileyi ayırt edememesi: kapı 5 adayların 18'ine hiç uygulanmadı, kapı 6/7 ve ikinci kapı pratikte bağlayıcı değil.
- Bağımsız (görülmemiş veri) kanıtı olan aday: **0**. İzlemeye değer, birbirinden farklı temsilci: **4–5**. Ön tahminim (0–4) ile çelişmiyor.

## 1. Neden bu kadar çok geçti? (kanıtla)

**(a) Dönem + zaman dilimi etkisi — ana neden.** Geçiş neredeyse yalnız 1d'de: 1d 221 hipotezin 151'i net>0 (%68), 39'u kapı 1–5, 29'u aday.
1h: 45'te 0; 5m/15m/30m: 47'de 0; 4h: 46'da 1; 6h: 3'te 1. Yani "günlük mumda long trend" 2019-07 → 2025-11 döneminde neredeyse
ne yazılsa kazandırmış. Aynı dönemde eşit ağırlıklı al-tut +%827 (dengelemesiz) / +%3.392 (günlük dengeli). Bu bir strateji keşfi değil, dönem özelliği.

**(b) Kapıların gevşekliği — ikinci ana neden.**
- *Kapı 5 muafiyeti:* 31 adayın 18'i "iki yönlü" sayıldığı için al-tut kıyasından muaf. Yeniden oynatmada bu 18'in 17'sinde short bacağı
  net zararda, birinde +2R (toplam short R: −32 … +2). Yani fiilen long stratejiler, ama long sınavına girmediler. Aynı kıyas (Sharpe > 0,854)
  bunlara da uygulansa 13'ü kalır: 144, 181, 779, 844, L15#2#v1, L15#2#v4, 727, 792, 76, 809, 400, 525, 725. Geriye 18 aday kalır.
- *Kıyasın kendisi zayıf:* al-tut sepeti dengelemesiz ve yalnız başlangıç gününde verisi olan sembollerden (SOL, BCH, HYPE ve büyük olasılıkla DOGE dışarıda; strateji
  ise bunlarda işlem yapıyor). Günlük dengeli, tüm semboller dahil eşit ağırlıklı sepetin Sharpe'ı 1,11. Bu kıyasla (raporlanan Sharpe)
  yalnız 3 aday kalır: 301 (1,24), 664 (1,53), 705 (1,29). Ön kayıt "eşit ağırlıklı al-tut" diyor, dengelemesiz tanım kural ihlali değil; ama gevşek uç.
- *Sharpe birimleri farklı:* stratejinin günlük serisi gerçekleşmiş özsermaye (kâr çıkışta yazılıyor), al-tut serisi günlük piyasa değeri.
  Kendi yaklaşık piyasa-değerli hesabımda (bileşiksiz, R birimi) sonuç iki yöne de oynuyor: 395 0,89→0,68; 718 1,01→0,79 (0,854'ün altına
  düşerler); 481 0,98→1,27; momentum 0,92→1,16. Yaklaşık hesaptır, karar değiştirmek için kullanılmamalı; ama kapı 5 sınıra yakın adaylarda güvenilir değil.
- *Kapı 6:* 365'te 186 geçiyor (%51); teşhis doğru, "kâr var mı"yı değil "rastgele girişten iyi mi"yi ölçüyor. *Kapı 7 (BH):* k*=187 → eşik
  0,051; yani p≤0,05 ile aynı, hiçbir şey elemiyor. *İkinci kapı:* 36'dan 31'i geçti; eşik yalnız ortalama R>0. L15#2#v1 0,002R, 727 0,006R,
  664 0,017R, 792 0,018R ile geçti. Aynı dönem, aynı alt-coin koşusu: bağımsız kanıt değil (ön kayıt da böyle diyor).
- *Kapı 3:* "en iyi yıl" ve "en iyi sembol" ayrı ayrı çıkarılıyor ve yıl, işlemin *giriş* yılı. 2020 sonunda açılıp 2021 baharında kapanan dev
  işlemler "2020"ye yazılıyor. Tek işlem bağımlılığını yakalamıyor: 525'te tek BNB işlemi 134R (toplam 206R), 395'te tek DOGE işlemi 169R (toplam 405R).

**(c) Kopya/aynı faktör — evet.** Bkz. bölüm 2. En yüksek korelasyonlar: 844–525 0,95; 194–37 0,93; 144–L15#2#v4 0,91; 181–779 0,89; 481–momentum 0,87.

**(d) Hata/sızıntı — bulunamadı.**
- Kesme testi: 31 adayın hepsi, 3 sembol (BTC, DOGE, XRP) × 2 kesim tarihi (2022-06-03, 2024-03-11): veri kesilince geçmiş işlemler aynı kalıyor, 0 fark.
- Net getiri 31/31 kayıtta JSON ile aynı çıktı (yeniden oynatma). Kapı 3 ve 5 elle doğrulandı (bölüm 3).
- Sonuç profili gerçek trend takibine benziyor, sızıntıya değil: kazanma oranı %20–38, medyan işlem negatif, kâr birkaç büyük işlemden.
- Dikkat edilecek üç şişirici (hata değil):
  1. **Dönem sonu zorla kapanış.** ZEC işlemleri veri son gününde (2025-11-08) açıkken kapatılmış: 76'da 112R, 481 ve momentumda 81R, 395'te 77R,
     181'de 75R, 779'da 73R. Gerçekte iz süren çıkış bu kârın bir kısmını geri verir. Bildiğim kadarıyla ZEC o günlerde zirveye yakındı; bunu veriyle doğrulamadım (sonraki veri okunmuyor).
  2. **Tek işlemde 100R+.** Stop mesafesi sakin dönemde küçük, fiyat 10–100 kat gidince R çok büyüyor. Hesap doğru, ama tekrarlanması beklenemez.
  3. **Veri kökeni.** Seriler 2017–2019'dan başlıyor, Binance USDT vadelileri ise daha geç açıldı (ör. DOGE verisi 2019-07-06). Erken dönem büyük olasılıkla
     spot kaynaklı; o dönemin fonlama/maliyet varsayımını denetlemedim. Bilmiyorum.
- 792 "sonuç sonrası düzeltme" kaydıdır (altyapı hatası sonrası yeniden koşu); raporda ayrı etiketlenmeli.

## 2. Kümeler (haftalık piyasa-değerli R korelasyonu, ortalama bağlantı ≥ 0,6)

| Küme | Üyeler | Ortak özellik | Temsilci |
|---|---|---|---|
| A. Yavaş trend, 2020 BNB/BTC tek işlem | 144, 844, 525, L15#2#v4 | Korelasyon 0,85–0,95; kâr 2020 sonu girişlerinde | Yok (hepsi şüpheli) |
| B. Kırılım/bant/momentum | 181, 779, 76, 481, momentum-sıfır | Donchian, Bollinger, SMA27, ROC20; ZEC 2025 açık işlemine bağlı | 481 |
| C. MACD/EMA kısa-orta trend, long | 194, 37, 421, 705, 718, 362, 664, 259, 626 | En kalabalık; 194≈37≈421 aynı MACD | 664, 705 (ve MACD için 37) |
| D. 4h/SuperTrend/ADX | 301, 725, 809 | 301 tek 4h aday | 301 |
| E. SuperTrend/OBV/Heikin-Ashi | 79, L15#2#v1, 730, 727, 346 | İki yönlü yazılmış, short zararda | 730 |
| Tekil | 395, 793, 792, 138, 400 | 138 ve 792 dört olaya en az bağlı olanlar (%17, %10) | 138 |

Gerçekten bağımsız fikir sayısı: **1 faktör, 5 alt biçim.** Tekil görünenler de aynı yönde (long, trend) çalışıyor. 31'inin toplamı tek portföy
gibi oynatılınca yaklaşık Sharpe 1,16; günlük dengeli al-tut 1,11. Fark 2022–2025'te açılıyor (1,20'ye karşı 0,69): asıl katkı "ayı piyasasında
dışarıda kalmak". Bu bilinen bir etkidir (kripto zaman serisi momentumu), yeni keşif değildir ve bu dönemde zaten göründüğü biliniyordu.

## 3. Elle doğrulama (JSON'dan)

Kapı 3 (ΣR − en iyi yıl; ΣR − en iyi sembol; ikisi de > 0 olmalı):

| Aday | ΣR | En iyi yıl | Kalan | En iyi sembol | Kalan | JSON k3 | İkisi birlikte çıkarılınca |
|---|---|---|---|---|---|---|---|
| 144#v1 | 166 | 2020: 132 | 34 | BNB: 102 | 64 | True ✓ | 18 |
| 525#v1 | 206 | 2020: 157 | 49 | BNB: 139 | 67 | True ✓ | 41 |
| L15#2#v4 | 96 | 2020: 83 | 13 | BNB: 63 | 33 | True ✓ | **−8** |
| 727#v2 | 89 | 2021: 65 | 24 | SOL: 30 | 59 | True ✓ | 20 |
| 400#v1 | 52 | 2024: 35 | 17 | XRP: 25 | 27 | True ✓ | 3 |
| 664#v1 | 135 | 2020: 48 | 87 | XRP: 31 | 104 | True ✓ | 68 |

Kapı 5 (yalnız long-only'de: Sharpe×2 > al-tut Sharpe×2): al-tut 0,8540 (kendi hesabım: 0,8540, aynı). 194: 0,961 ✓; 37: 1,018 ✓; 395: 0,886 ✓
(marj 0,03); 138: 0,893 ✓ (marj 0,04); 664: 1,525 ✓. İki yönlü sayılanlarda `bh_sharpe_x2` boş, k5 otomatik True: 144 (0,69), 76 (0,70), 525 (0,52),
400 (0,46), 809 (0,50) kıyasa girseydi kalırdı. Kapı bayrakları koda ve ön kayda uygun; sorun hesapta değil, kuralın kapsamında.

## 4. Aday aday değerlendirme

"Güçlü" yok: hiçbir adayın görülmemiş veride kanıtı yok. "Orta" = kıyası gerçekten aşıyor ve kâr birkaç işleme bağlı değil; yine de yalnız geçmiş veri.
Kısaltmalar: T10 = en iyi 10 işlem çıkarılınca kalan R; 22–25 = 2022 ve sonrası girişlerin R'si; 4O = dört olayın payı.

| Aday | Not | Gerekçe |
|---|---|---|
| 664#v1 wavetrend | orta | En dağınık kâr (T10 +65, 4O %51), Sharpe 1,53; ama 40 sembolde ortalama yalnız 0,017R |
| 705 üçlü MA 3/9/21 | orta | T10 +53, Sharpe 1,29, sembol dağılımı en dengeli (en iyi sembol %16) |
| 301#v1 RSI+EMA50/200 (4h) | orta | Tek 4h aday, Sharpe 1,24, T10 +111; short bacağı −6R (fiilen long), 2022–25 zayıflamış |
| 37#v1 MACD tolerans | orta | Kapı 5'i gerçekten geçti (1,02), 22–25 +65R; 194 ve 421 ile aynı fikir |
| 194 MACD sinyal | orta (kopya) | 37 ile korelasyon 0,93; ayrı aday sayılmamalı |
| 481 SMA27 üstü | orta− | 22–25 +100R ama 81R'si dönem sonunda zorla kapatılan tek ZEC işlemi |
| 730#v2 OBV momentum | orta− | Sharpe 0,94, T10 +22; short −12R, kapı 5'ten muaf geçti |
| 138#v3 SMA 10/50, 5 gün tutma | orta− | Dört olaya en az bağlı (%17), her yıl 2020'den beri artı; ama kenar küçük (ΣR 33, 40 sembolde 0,028R) |
| momentum-sıfır-kesişim | zayıf | 481'in kopyası (0,87); ZEC 81R; T10 +12 |
| 362#v2 EMA9 stop-emir | zayıf | 2020 payı %63, T10 +17 |
| 421#v4 MACD+EMA100 | zayıf | MACD kopyası; kârın %97'si dört olayda |
| 718#v1 korelasyon trend | zayıf | Yaklaşık piyasa-değerli Sharpe 0,79 (al-tut altı); 2025 negatif |
| 626#v1 VM-HMA | zayıf | PF 1,40, 1.406 işlemde ΣR 83; kenar ince |
| 259#v1 BB 1σ + RSI | zayıf | İşlem yığılması yok ama 22–25 yalnız +13R |
| 79#v1 ikili SuperTrend (6h) | zayıf | SOL payı %42, 2025 negatif, yaklaşık piyasa-değerli Sharpe 0,73 |
| 346#v2 bant kırılım | zayıf | 76'nın kopyası (0,81); T10 −1 |
| 76 Donchian 20/10 | zayıf | Sharpe 0,70 < al-tut (muaf geçti); ZEC 112R açık işlem |
| 181#v1 BB kırılım | zayıf | Sharpe 0,76 < al-tut (muaf); ZEC 75R |
| 779#v1 dinamik kırılım | zayıf | 181 kopyası (0,89); Sharpe 0,71 < al-tut (muaf) |
| 725#v1 SuperTrend 2/3 | zayıf | Sharpe 0,847 < al-tut (muaf); T10 −8 |
| 793#v1 MACD oran | zayıf | 2020–21 dışında toplam +7R; 2025 negatif |
| 792 EMA kesişim, 12 mum | zayıf | "Sonuç sonrası düzeltme" kaydı; PF 1,39, Sharpe 0,82 < al-tut (muaf) |
| 727#v2 Heikin-Ashi EMA | şüpheli | Kârın %73'ü 2021; 2020–21 dışı +9R; 40 sembolde 0,006R |
| L15#2#v1 SAR/EMA | şüpheli | PF 1,24, 40 sembolde 0,002R (fiilen sıfır); en iyi 5 işlem çıkınca +1R |
| L15#2#v4 SuperTrend | şüpheli | 2020 %87, BNB %66; yıl ve sembol birlikte çıkınca −8R |
| 144#v1 EWMA kütle merkezi | şüpheli | 2020 %79, BNB %62; T10 −17; Sharpe 0,69 (muaf) |
| 844 ROC60 iki yön | şüpheli | T10 −30; yaklaşık piyasa-değerli Sharpe 0,47 |
| 525#v1 KAMA−SMA | şüpheli | Tek BNB işlemi 134R / toplam 206R; 201 işlem (eşik 200); Sharpe 0,52 |
| 395#1 VMA bant | şüpheli | Tek DOGE işlemi 169R / 405R; PF 5,71 bunun ürünü; yaklaşık piyasa-değerli Sharpe 0,68 |
| 809#v1 ADX/DI | şüpheli | Sharpe 0,50; short −24R; en iyi 5 işlem çıkınca +1R |
| 400#v1 MACD min-maks | şüpheli | Sharpe 0,46; XRP %48, 2024 %67; yıl ve sembol birlikte çıkınca +3R |

## 5. Önerilen sonraki adım (karar kullanıcıda)

1. **31'i "31 strateji buldum" diye okumayın.** Doğru cümle: "2019–2025 kripto verisinde günlük long trend takibi işe yaramış; elimizde bunun
   5 biçimi var." Bu, canlıya geçiş gerekçesi değildir.
2. **Paper'a en çok 4–5 temsilci:** 664, 705, 301, 138 ve istenirse 481 (ya da MACD için 37). Aynı kümeden ikinciyi eklemek bilgi katmaz, yalnız
   aynı riski büyütür. Şüpheli 9 aday paper'a alınmasın.
3. **12 haftalık paper'dan fazla şey beklemeyin.** Bu stratejiler 6 yılda 4 olaydan kazandı; 12 hafta büyük olasılıkla küçük eksi ya da sıfır
   gösterir ve bu ne lehte ne aleyhte kanıt olur. Paper'ın işi uygulamayı (dolum, maliyet, sinyal uyumu) doğrulamaktır, kenarı kanıtlamak değil.
   Kenarı sınayacak ölçüt şimdiden yazılmalı: "ayı/yatay dönemde zarar sınırlı mı, bir sonraki büyük trendde içeride mi".
4. **Temiz holdout yok.** 2025-11-08 sonrası veri önceki turlarda görüldü, ön kayıt okunmasını yasaklıyor. Bu 31 kural o veride hiç koşulmadı;
   tek seferlik, önceden yazılmış ölçütle bir sınav bilgi verir ama "görülmüş veri" kusurunu taşır ve ön kayıttan sapmadır. Yapılacaksa ayrı
   kullanıcı kararı, önceden yazılı ölçüt (ör. temsilcilerin her biri için net > 0 ve dengeli al-tut'tan düşük düşüş) ve tek koşu şart.
5. **Sonraki turlar için kural önerileri (bu turun sonucunu değiştirmez):** kapı 5 herkese uygulansın ve kıyas günlük dengeli sepet olsun; kapı 3'e
   "en iyi 5 işlem çıkarılınca ΣR > 0" eklensin; dönem sonunda açık kalan işlemler ayrı raporlansın; aday sayısı küme başına bir ile sınırlansın.

## Bilmediklerim

- Bu ailenin gelecekte çalışıp çalışmayacağını. Elimdeki tek dönem güçlü bir boğa dönemi; 2022 ayısında adayların çoğu küçük eksi yazdı, kâr etmedi.
- Piyasa-değerli Sharpe'ların kesin değerini (benim hesabım yaklaşık: bileşiksiz, giriş fiyatı bir önceki kapanış sayıldı).
- 2019 öncesi/erken dönem verinin vadeli mi spot mu olduğunu ve o dönemin fonlama varsayımının doğruluğunu.
- 31 sınıfın kaynak metne birebir uyduğunu (bu denetimde bakılmadı; önceki kod hakemi yalnız 32 sınıflık örneklem denetledi).
- ZEC'in 2025-11-08 sonrasındaki seyrini veriyle (okunmadı).
