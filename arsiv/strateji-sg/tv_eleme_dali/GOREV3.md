# 3. tur + 1-2. tur denetimi (kullanıcı 13 Eki: "hepsini detaylıca analiz et, yüzeysel geçiştirme")

Temel kurallar `tv/GOREV.md` ile aynı (8 zorunlu eşik, optimizasyon yok, maliyetler, veri kaynakları). Ek olarak:

## A. 3. tur
- Girdi: `tv/kaynak/linkler3.txt` (92 yeni betik), metin `tv/kaynak/pdf3_en_iyi_100.txt`.
- Aşama 1-3'ü bu betiklere uygula; `aday.csv`'ye `tur` sütunu (1-2 / 3).
- Ek kesin eleme nedeni: DCA / grid / martingale / ortalama düşürme (ör. 3Commas DCA) — kuyruk riski gizli.

## B. Kalite çıtası (tüm turlar)
1. HER betik için `tv/analiz/<id>.md`: ne yapıyor (giriş/çıkış/stop/hedef kuralları Pine'dan okunarak), zaman dilimi, pazar, repaint/lookahead kontrolü (hangi satır), karar ve gerekçe. Tek kelimelik gerekçe yok; kodla gösterilir.
2. Şüphede ELEME, çevir ve test et. Kesin eleme nedenleri yalnız: kaynak kapalı, strategy() yok, gerçek repaint/lookahead (satır), DCA/grid/martingale, gerekli veri yok (tick/emir defteri/opsiyon).
3. Çeviri doğrulaması: yazarın sonuç verdiği her stratejide aynı sembol/zaman dilimi/dönemde (verimiz varsa) bizim sonuç ile yazarın iddiası yan yana (işlem sayısı, kazanma oranı, KF). Büyük farkta önce çeviriyi kontrol et (Pine varsayılanları: initial_capital, default_qty_type, commission, pyramiding, process_orders_on_close, calc_on_order_fills), nedeni yaz. `tv/sonuclar/dogrulama.csv` + RAPOR.
4. Kalanlar: her zorunlu kural için değer ve eşiğe fark (ör. Sharpe 0,94 → 1,0) RAPOR'da tablo.

## C. 1-2. tur denetimi
- 123 elenenin ve çevrilemeyen 5'in gerekçelerini B çıtasıyla yeniden incele; haksız elenen varsa çevir/test et.
- Geçen 3 stratejinin (hybrid_brk, sqzmom, macd_reloaded) çevirisini B3 ile doğrula. Çeviri hatası bulunursa düzelt ve yeniden değerlendir; sonuç değişirse RAPOR'da açıkça yaz.

## D. Kağıt test
- Yeni geçenler `gecenler.json`'a eklenir; mevcut 3'ün sermayesi (3.333,33 $) ve başlangıcı (2026-10-14) DEĞİŞMEZ. Her stratejiye sabit 3.333,33 $, strateji bazında başlangıç (yeniler: geçişten sonraki ilk gün 00:00 UTC). Başlamamış strateji 3.333,33 $ sabit sayılır; toplam = strateji özsermayeleri toplamı.
- Çıktı biçimi korunur (islemler.csv, pozisyonlar.csv, ozsermaye.csv: zaman + strateji adları + toplam; durum.json) — panel bunu okuyor.
- Mevcut 3'ten biri denetimde çeviri hatası nedeniyle eşiği kaybederse çıkarma; RAPOR'a yaz, karar koordinatör/kullanıcıda.

## E. Süreç
- Dal `tv-eleme`. Acele etme, eksiksiz yap. `tv/DURUM.md`'yi sık güncelle, sık commit + push.
- Bitince main'e PR, Türkçe kısa açıklama. Kullanıcıya soru sorma; belirsizlikte makul varsayım + RAPOR'a not.

## F. İzleme listesi (kullanıcı onayı 14 Eki 2026: "denemekte fayda var")
- Denetim ve 3. tur bittikten sonra, 8 zorunlu kuraldan YALNIZ BİRİNİ kılpayı kaçıranlar "izleme" hesabına girer. Kılpayı = eşiğe %15 içinde:
  Sharpe ≥ 0,85 · maks. düşüş ≤ %23 · beklenti ≥ +0,13R · KF ≥ 1,2 · OOS/eğitim Sharpe ≥ 0,42 · maliyet×2 KF ≥ 1,0 · komşu kârlı ≥ %60 · enstrüman kârlı ≥ %50 · işlem sayısı ≥ 85 (swing) / 255 (gün içi).
  Diğer 7 kural tam geçilmiş olmalı. Eşikler ve geçen 3'ün statüsü DEĞİŞMEZ; izleme ayrı bir deney.
- En fazla 8 strateji (çoksa Sharpe sırasıyla). Her biri 3.333,33 $, başlangıç: listenin kesinleştiği günden sonraki ilk gün 00:00 UTC.
- Ayrı liste `tv/izleme.json`, aynı kağıt bot: `python3 -m tv.kagit --liste izleme --durum X` (varsayılan liste gecenler). Çıktı biçimi aynı.
- RAPOR'a "İzleme listesi" bölümü: her biri hangi kuraldan ne kadar farkla kaldı.
