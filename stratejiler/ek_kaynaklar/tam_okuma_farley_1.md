# Tam okuma: Alan Farley, "Swing Trader" (Master Swing Trader Toolkit) — sayfa 1-153 (parça farley_1)

Sayfa numaraları metin dosyasındaki `=== SAYFA n ===` numaralarıdır (kitap sayfası = n - 6). Aralıktaki 153 sayfanın tamamı sırayla okundu.

## Okuma kanıtı (blok başına konu)
- 1-12: İçindekiler, önsözler, teşekkür; kitabın amacı (bant okuma, savunmacı strateji, 5-3-3 Stokastik tercihi).
- 13-32 (Böl. 1): modern piyasa ve program ticareti, "şeytani piyasa" (tuzak/kırbaçlama), 5 hayatta kalma tekniği, ticaret avantajı, desen döngüleri, devam boşluğu ve %38 sıçrama (s.29-30).
- 33-58 (Böl. 2): ECN/ondalık/program algoritmaları, endeks vadeli işlemler, 15 dk 50/200 EMA + 5-3-3 grafiği, program satışında "iki adım aşağı bir adım yukarı" (s.45-46), 1-2-3 etki-tepki-çözüm döngüsü (s.48-50), piyasalar arası ilişkiler, gerçek dünya örneği (gece satışı).
- 59-83 (Böl. 3): trend göreliliği, elektronik işlem günü, takvim etkileri, FOMC, opsiyon vade haftası/manyetik vuruş fiyatı, kazanç sezonu, agresif/savunma döngüleri, şok sarmalları, VIX 15/60 dk grafiği.
- 84-103 (Böl. 4): göreceli güç; Fiyat-200 MA sıralaması ve 52 hafta filtreleri (s.88-89); 17-17-1 Stokastik / yumuşak RSI (s.89-91); 60 dk 5-3-3 alım-satım salınımı (s.92-93); dönüş belirlemenin 10 yolu (s.94-95); ideal fiyat/zaman örnekleri (s.96-98); gerçek dünya: çeyrek sonu/vade örneği (s.99-103).
- 104-120 (Böl. 5): kazanmanın doğası, beklenti formülü, 4 yapı taşı (tahmin, zamanlama, oynaklık, risk), hayatta kalma planı, yo-yo tüccar, düşüşte kâr koruma (5S), hesap birleştirme. Kart yok (kavram/psikoloji).
- 121-131 (Böl. 6 başı): hayatta kalma stratejileri, rotasyon, salınım analizi (engel sayımı, kâr/başarısızlık hedefi, Celestica örneği), yakınsama-ıraksama (CD) kavramı.
- 132-138: savunmacı açığa satış (4 giriş stratejisi, filtreler, yap/yapma listesi).
- 138-144: 50 günlük EMA stratejileri (kartlı), hacim (3x/60 gün kuralı), OBV.
- 145-148: Fibonacci oyunları (kartlı), Gartley/Kelebek notu.
- 148-153: karşı piyasa oyunları (üç tür, 200/50 EMA, düşen bıçak, menzil oyunu), ilk saat aralığı kırılımı başlangıcı (kartlı; devamı s.154'te, aralık dışı).

## Yeni kartlar (12)
Dosyalar: `veri/kartlar_ham/swing/Swing_Trader_-_Alan_S_Farley_306_sayfa__tam_farley_1.json` (11) ve `veri/kartlar_ham/daytrade/...__tam_farley_1.json` (1).
Swing:
1. `swing__60dk-stokastik-533-geri-cekilme-alimi__farley` (s.91-93, puan 1)
2. `swing__stokastik-17-17-1-uzun-vade-donus__farley` (s.89-91, puan 1; esasen zamanlama filtresi)
3. `swing__2b-basarisiz-kirilim-donusu__farley` (s.94-95, 133, puan 1)
4. `swing__dar-aralik-sikisma-short__farley` (s.134, 141, puan 2)
5. `swing__basarisizligin-basarisizligi-ikinci-sinyal__farley` (s.49, 135-136, 141, 147, puan 2)
6. `swing__geri-cekilme-short-direnc__farley` (s.133, puan 1)
7. `swing__hacim-3x-genis-bar-kirilim__farley` (s.143-144, puan 2)
8. `swing__aralik-destek-direnc-karsi-trend__farley` (s.150-153, puan 2)
9. `swing__taban-sonrasi-geri-cekilme-kademeli-limit__farley` (s.150-152, puan 1)
10. `swing__devam-boslugu-geri-cekilme-fib38__farley` (s.29-31, puan 1)
11. `swing__kirilim-1-2-3-ikinci-sans-girisi__farley` (s.48-50, 70, puan 1)
Daytrade:
12. `daytrade__program-satisi-iki-asagi-bir-yukari-alim__farley` (s.45-46, puan 1)

Not: 5, 10 ve 11 mevcut kartlarla kısmen örtüşür (Fibonacci kamçı, 50 EMA, geri test mantığı); birleştirmede aynı aileye alınabilir. Kitabın kendi tercihi tüm kurulumlarda "çapraz doğrulama" (seviye + EMA + trend çizgisi + Stokastik) ve bant okumadır; bu yüzden puanlar düşük kalmıştır.

## guncelleme_onerileri
- `swing__50ema-geri-cekilme__farley` (s.138-142):
  - Stop yeri açıklaması: doğal destek (kırılma seviyesi) altına stop konunca stoplar toplanıyor, alıcılar 50 EMA'da çıkıyor; yani stop kırılma seviyesinin değil 50 EMA'nın altına (s.140). Sayısal tampon yine yok.
  - Short ayna senaryosu: güçlü hacimli çöküşten sonra destekte toparlanma 50 EMA'ya kadar, burada çubuklar daralınca dar barlar içinde short, stop 50 EMA üstü (s.141). Bu ayrıca `swing__dar-aralik-sikisma-short__farley` olarak kartlandı.
  - Aynı mantık gün içi 15 dk ve 60 dk grafiklerde 50 dönemlik EMA ile çalışır ama çok daha gürültülü; en güvenilir sinyal fiyat uzaktan 50 EMA'ya inince/çıkınca (s.142).
  - Çapraz teyit: Stokastik/RSI'nin aşırı alım-satımdan dönüşü ve günlük 50 EMA bölgesinde 60 dk dönüş modeli (3 boyutlu grafik) (s.141-142).
  - Yazar piyasa koşulu: "güçlü kırılım" sonrası "çoğu çıkış 50 günlük EMA'ya dönüyor" iddiası kanıtsız.
- `swing__fibonacci-62-78-kamci__farley` (s.145-148):
  - Fibonacci seviyesi tek başına işlem sebebi olmaz; 50 günlük EMA, altı aylık trend çizgisi gibi çapraz doğrulama aranır (s.140-141, 146).
  - Kural: derin geri çekilme seviyesine yaklaşınca kenara çekil, seviye aşılıp fiyat geri dönünce ilk geçişi giriş sinyali say (s.147).
  - MasterCard short örneğinde: %62 altına dönüş ilk short; %50'de duraklamada ekleme, stop %62'nin hemen üstü; hedef önceki yükselişin başlangıcı (162) (s.148).
  - Ek: Gartley (%78,6) ve Kelebek (%127 uzantı) desenlerinin adı geçer, kural verilmez (s.148). Dikey bar (geniş çubuk) geri çekilmenin son %20-25'inde tükenme işaretidir; %62,8/%78,6 son bariyer, ardından %100 geri dönüş (s.123-124).
- `daytrade__ilk-saat-araligi-kirilim-ve-basarisizlik__farley` (s.153): enstrüman likit olmalı (günde >5 milyon hisse; mümkünse ETF); aynı yönde hareket etmeyen izleme listesi; tam pozisyon hemen alınır (ölçeklenmez); işlem hızla kâra geçmezse kırbaçlanma olasılığı artar; zihinsel stop önerilmez. Örnek: aralık 22-24 → yukarı kırılımda stop 23,60-23,70 (zirvenin altı), aşağı kırılışta stop 22,30-22,40 (dibin üstü). İlk 30 dk gözlem sonrası aralığın "5 dk salınımlarla" belirlenmesi.

## Kart çıkmayan bölümler ve nedeni
- s.1-12, 13-32 (genel): giriş, öykü, hayatta kalma ilkeleri; kural yok.
- s.33-58 program ticareti: gözlem listesi (öğle saati zirve/dip, 80:20 yukarı/aşağı hacim trend günü, gün sonu program kapanışı) yön veya sayısal tetik vermiyor; açılış öncesi emirler (s.35, 47, 56-57) hisse/ECN'ye özgü, 24/7 kriptoya uygulanamaz.
- s.59-83: takvim (Ocak/çeyrek sonu, FOMC 14:15, vade haftası "manyetik vuruş fiyatı", kazanç sezonu) opsiyon açık faizi, haber ve temel veri gerektirir (karar: elenir). Kazanç sonrası 60 dk taban + 3 gün satış baskısı (s.78) kazanç verisi ister. VIX 15/60 dk 50/200 EMA kuralı (s.81-83): VIX bizim enstrüman evreninde yok.
- s.84-103: Fiyat-200 MA % sıralaması ve 52 hafta yüksek/düşük %25 filtreleri (s.88-89) hisse tarama aracı (evren seçimi), işlem kartı değil; "dönüş belirlemenin 10 yolu" (s.94-95; Taylor 3 gün döngüsü, Bollinger %75 sivri uç, Salı dönüşü, 2B, volatilite durması, hacim tükenişi, mum, üçlü, boşluk) tek tek tetik/stop/hedef değil, tanımlar ve filtre fikirleri; ölçülebilir olanlar (Bollinger bar %75 dışı, 2B) kartlara/belirsizliklere işlendi.
- s.104-120: tüm bölüm risk/psikoloji/beklenti; "al ve çık" (günlük kâr eşiği ≥ 2x zarar eşiği, yo-yo için) risk modülü fikri olabilir ama sayısal eşik yok.
- s.121-131: salınım analizi ve CD (yakınsama-ıraksama) kavram; engel sayımı ile ödül:risk hesabı (giriş ile son zirve arası az engel, giriş ile salınım başlangıcı arası çok engel) bir işlem filtresi olarak not edilebilir ama kart değil.
- Savunmacı short "momentum girişi" (s.134): yüzde bazlı stop dışında kural yok; kart yapılmadı. "Yap/yapma" listesi (s.137-138) genel tavsiye.
- s.142-144 hacim ve OBV: hacmin güvenilmezliği genel uyarı; 3x/60 gün kuralı kartlandı, geri kalan kart değil.
- s.148-149: Gartley/Kelebek: oran verilmeden ad olarak geçer.
- s.150-151 düşen bıçak (Fuqi örneği, s.152): iki giriş tekniği 9. kartta; hisse özgü örnek.
