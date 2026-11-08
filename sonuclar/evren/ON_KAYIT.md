# Evren stratejileri seçimi — ön kayıt (karar 27)

Tarih: 2026-11-07. Kullanıcı: "ben seçtiğim evrenden stratejiye göre seçim yapıp işleme giren stratejiler arıyorum,
sadece SOL'de sadece NVDA'da ne diye işlem kovalayacam". Önceki final set (tek sembol–strateji ikilileri) paper'dan kaldırılır.
Bu dosya koşulardan ÖNCE yazıldı; ölçütler sonuç görüldükten sonra değiştirilmez (değişirse kullanıcıya bildirilir).

## GÜNCELLEME 1 (2026-11-07, kullanıcı, ham koşular bitmeden — sonuç görülmeden)
Evren aşağıdaki gibi değişti; "Evren U (13)" tanımının yerine geçer:
- **Daytrade ve swing evreni:**
  - Emtia: altın (DK_XAU), gümüş (DK_XAG), petrol (DK_WTI), bakır (DK_COPPER), doğalgaz (DK_NATGAS).
  - ABD hisse: S&P 500 üyesi ve piyasa değeri > 500 milyar USD (her gün kontrol). 2026-11-07 listesi: AAPL, NVDA, MSFT,
    GOOGL, AMZN, META, TSLA, AVGO, LLY, WMT, JPM, V, MU, AMD, XOM, JNJ, MA, ABBV.
  - Kripto: stabil coinler hariç piyasa değeri > 5 milyar USD (her gün kontrol). 2026-11-07 listesi: BTC, ETH, BNB, XRP, SOL,
    TRX, ZEC, HYPE, XMR, DOGE, LEO, LINK, ADA, XLM, BCH. Binance USDⓈ-M'de perp'i olmayanlar (ör. XMR, LEO) işlem yapılamayacağı
    için dışarıda kalır ve raporlanır.
- **Scalp evreni (yalnız 4):** S&P 500 endeksi (DK_SPX), XAUUSD (DK_XAU), petrol (DK_WTI), BTCUSDT.
- Backtest'te üyelik bugünkü listeyle sabit alınır (geçmiş piyasa değeri verisi yok; karar 10: hayatta kalma yanlılığıyla
  uğraşılmaz — raporda yanlılık olarak belirtilir). Canlı/paper'da üyelik her gün kurala göre güncellenir (Aşama 4 işi).
- Bir enstrümanın verisi o TF'de yoksa (ör. kısa geçmiş) dışarıda kalır ve raporlanır; analiz başlangıcı evrenin ≥ %75'inin
  verisi olduğu tarih. Genişlik ölçütündeki üç sınıf (kripto/hisse/emtia) scalp için de geçerlidir (SPX hisse sınıfı sayılır).

## GÜNCELLEME 2 (2026-11-07, kullanıcı, sonuç görülmeden)
- **BIST eklendi** (karar 6'daki "BIST yok" kullanıcı kararıyla kalktı).
- Daytrade ve swing evrenine BIST hisseleri: AKBNK, ASELS, ASTOR, BIMAS, EKGYO, EREGL, FROTO, KCHOL, SISE, TCELL, THYAO,
  TRALT, TUPRS (13). Varlık sınıfı olarak "BIST" ayrı sınıf sayılır (genişlik ölçütünde sınıflar: kripto / ABD hisse /
  emtia / BIST — en az ikisinde net > 0).
- Scalp evrenine XU030 (BIST 30 endeksi) eklendi → scalp evreni 5: SPX, XAUUSD, petrol, BTCUSDT, XU030.
- Veri: BIST için ücretsiz kaynakların intraday geçmişi kısadır (ör. 1h ~2 yıl, 5m ~60 gün). Bir sembolün o TF'de WF için
  yeterli geçmişi yoksa (en az bir eğitim + bir test penceresi) o TF'de dışarıda kalır ve raporlanır; uydurma/uzatma yok.
- İşlem yeri: BIST Binance'te yok; paper için veri kaynağı, canlı için ayrı aracı kurum gerekir (canlı kararı kullanıcıda).

## GÜNCELLEME 3 (2026-11-07, kullanıcı, sonuç görülmeden)
- Test dönemi: **2020-01-01 → bugün** (verinin sonu). Kilitli dönem ayrımı bu testte uygulanmaz (kilit Katman 4'te zaten
  kullanıldı); walk-forward örneklem-dışı mantığı aynen sürer, son bağımsız sınav paper trading'dir. Gerekirse 2020 öncesi
  ayrıca indirilir (kullanıcı kararı).
- Tüm kodlu stratejiler (yeni kodlananlar dahil; kodlama bitince) test edilir: scalp → scalp evreni (5); daytrade ve swing
  → BIST + ABD hisse + kripto + emtia evreni. Stratejiler artık tek tek "kendi enstrümanlarında" seçilmez.
- Kilit açılışı: veri okumaları kilit_ac=True, gerekce="karar 27 evren testi 2020→bugün (kullanıcı kararı)" ile günlüğe yazılır.

## GÜNCELLEME 4 (2026-11-07, kullanıcı)
- Amaç strateji odaklıdır: strateji evrenin tamamında tek ayarla değerlendirilir; enstrüman bazında seçim/sıralama YAPILMAZ
  (enstrüman dağılımı yalnız genişlik kontrolü ve bilgi olarak raporlanır).
- "İyi" = tüm ölçütleri geçen; "iyiye yakın" = en çok bir ölçütü kıl payı kaçıran (PF ≥ 1.1, Sharpe ≥ 0.4, düşüş ≤ %25,
  sağlamlıkta en çok bir kontrol kalan). İkisi de stil bazında sıralı listelenir; iyiye yakınlar geliştirme adayıdır.

## GÜNCELLEME 5 (2026-11-08, kullanıcı: "1 2 3 4'ü ekleyelim, 5'i de indir" — koşulardan ve sonuç görülmeden önce)
1. **Son 12 ay ayrılır (holdout):** 2025-11-08 → verinin sonu hiçbir seçimde, ayar seçiminde ve eşik kontrolünde KULLANILMAZ.
   Geliştirme dönemi: başlangıç → 2025-11-07. Tüm WF, sağlamlık, iyi/iyiye yakın listeleri geliştirme döneminden çıkar.
   Listeler dondurulduktan sonra (dosya + commit) her listede kalan strateji, WF'nin geliştirme sonundaki son seçilen
   ayarıyla holdout'ta BİR KEZ koşulur. Holdout kapısı: evren net > 0 ve PF ≥ 1.1. Geçenler "doğrulanmış", geçmeyenler
   "holdout'ta kaldı" diye raporlanır; holdout sonucuna göre ayar/eşik değiştirilmez, ikinci holdout denemesi yapılmaz.
2. **Çoklu test düzeltmesi (kapı oldu, yalnız rapor değil):**
   - DSR (Deflated Sharpe): toplam deneme sayısı = tüm (strateji × tf × ayar) koşuları + önceki denemeler. "İyi" için
     DSR olasılığı ≥ 0.90; "iyiye yakın" için ≥ 0.50.
   - PBO (CSCV, 16 blok): stil × tf başına tüm aday ayarlar üzerinden hesaplanır ve raporlanır; PBO > 0.5 olan stil×tf
     grubundan çıkan "iyi" strateji "iyiye yakın"a düşer.
3. **Rastgele girişle kıyas (K2) kapıdır:** aynı enstrüman/zaman/yön/tutma süresi ve AYNI çıkış kurallarıyla rastgele giriş
   (500 tekrar); p ≤ 0.05 şart (iyiye yakın için p ≤ 0.10).
4. **Gerçekçi maliyet + stres:** enstrüman bazlı maliyet tablosu (komisyon, spread/kayma, kriptoda funding, BIST'te BSMV dahil)
   koşulardan önce sonuclar/evren/maliyet_tablosu.csv olarak yazılır ve sabitlenir. K1 genişler: maliyet ×2 PF ≥ 1.05,
   maliyet ×3 PF ≥ 1.0 ve sinyal 1 mum gecikmeli PF ≥ 1.0 — üçü de şart.
5. **2020 öncesi veri:** mümkün olan en eski tarihten (hedef 2017-01-01) indirilir. Kripto perp'ler Binance'te 2019-09'da
   başladığı için 2017-01 → perp başlangıcı arası SPOT verisiyle (funding yok, maliyet perp ile aynı varsayım) doldurulur ve
   raporda "spot vekil" diye işaretlenir. Dönem: başlangıç (enstrüman bazında en eski) → 2025-11-07 geliştirme; analiz
   başlangıcı kuralı (evrenin ≥ %75'i) aynen geçerli.
Bu güncelleme önceki "kilit ayrımı uygulanmaz" (Güncelleme 3) hükmünün yerine geçer: holdout yeni kilittir.

## GÜNCELLEME 6 (2026-11-08, kullanıcı kararı; WF sonuçları GÖRÜLDÜKTEN sonra, sağlamlık koşulmadan önce)
Açık kayıt: bu karar WF sonuçları (swing 44, daytrade 5 geçen; scalp 4 enstrümanda 0/204) ve bağımsız denetim
(sonuclar/denetim/fable_sentez_2026-11-08.md, Y1) görüldükten SONRA, sağlamlık/PBO/DSR sonuçları hiç görülmeden alındı.
Geçme eşikleri DEĞİŞMEDİ.
1. **DSR (K5) N ve V aynı popülasyondan.** Gerekçe: eski tanımda N ≈ 223.000 (bu testin aday sayısı + önceki deneme
   kaydının sembol çarpanlı/çarpansız karışık toplamı + 787) ve V (WF'yi geçen/koşan satırların OOS Sharpe varyansı) farklı
   popülasyonlardan geliyordu; şansla beklenen en yüksek Sharpe SR0 ≈ 3.2 (yıllık) çıkıyordu, WF'yi geçenlerin en iyisi 1.90
   → kapı tanım gereği geçilemezdi. Yeni tanım: her stil × zaman dilimi grubunun TÜM aday ayar (strateji × ayar) sütunlarının
   OOS-dönem günlük getirileri (PBO ile aynı matris) → her sütunun günlük Sharpe'ı; **N = Sharpe'ı tanımlı sütun sayısı,
   V = bu Sharpe'ların varyansı**. Eşik aynı: "iyi" DSR ≥ 0.90, "iyiye yakın" ≥ 0.50. Önceki/eski denemeler (deneme kaydı
   toplamı + 787) aynı V ile ayrı bir **bilgi DSR'si** (`dsr_bilgi`; eski sembol çarpanlı sayım `dsr_sembol`) olarak raporlanır,
   kapı değildir. Sıra: WF → PBO → sağlamlık → seçim → holdout. Her satıra hesaplandığı N ve V yazılır; N/V değişirse DSR
   yeniden hesaplanır.
2. **Kill switch / günlük limit olayları kapı değil, bilgi.** `kill_olayi`, `gunluk_limit_olayi` ve reddedilen giriş
   sayıları (`red_*`) iyi/iyiye yakın listelerinde ve özette ayrı sütun olarak gösterilir.
3. **BIST yalnız bilgi.** BIST evrende kalır ve koşulur (tek kasada işlem yapar), fakat genişlik kapılarında sayılmaz:
   kârlı enstrüman oranı, tek enstrüman payı ve "en az iki sınıfta net > 0" yalnız kripto/hisse/emtia üzerinden hesaplanır.
   BIST sonuçları bilgi sütunlarında: `net_bist`, `bist_islem`, `bist_short_payi`. Gerekçe: BIST'te açığa satış/ödünç
   maliyeti modellenmiyor, fiyatlar TRY nominal (enflasyon trendi), canlı BIST yolu yok. Mevcut WF satırlarının geçme kararı
   saklanan enstrüman netlerinden yeniden değerlendirilir (eski karar `gecti_g5` sütununda kalır); net/PF/Sharpe/düşüş
   değişmez.
4. Ertelendi: işlem başı %1 riske maliyetin katılması (evren seçimi bittikten sonra ayrıca karar).
Denetim düzeltmeleri (yöntem değişikliği değil, ön kayıtlı kuralın doğru uygulanması): K2 tutma süresi mum sayısı olarak
sembolün mum indeksindeki konum farkından (seanslı veride takvim süresi değil); K4 komşu ayarlar WF'nin kullandığı
enstrümanlarla; holdout/K4 sembol hataları sayılır ve satır "hata" olur; holdout mührü WF/sağlamlık/PBO dosyalarını,
ölçütleri, strateji kodunu ve kartlarını kapsar, holdout ayarı mühürlü kayıttan okunur.

## Tanım
**Evren stratejisi** = bir strateji + bir zaman dilimi + TEK ortak parametre seti, evrenin TÜM enstrümanlarında aynı anda
çalışır; sinyal hangi enstrümanda çıkarsa orada işleme girer. Evren U (karar 22): BTCUSDT, ETHUSDT, SOLUSDT, DK_AAPL, DK_MSFT,
DK_GOOGL, DK_AMZN, DK_NVDA, DK_META, DK_TSLA, DK_XAU, DK_WTI, DK_COPPER (13). Enstrüman seçmek (cherry-pick) yok.

## Yöntem (sabit)
- Aday: tüm kodlu tek-grafik stratejiler (stil: scalp/daytrade/swing) × stilin zaman dilimleri (scalp 5m/15m, daytrade 30m/1h,
  swing 4h/1d) × parametre ızgarası. Veri kuralları, maliyet, motor wf_tarama ile aynı. Yalnız kilit ÖNCESİ veri (< 2025-11-01).
  Bir enstrümanın verisi yoksa (ör. emtia 5m) o TF'de o enstrüman dışarıda kalır ve raporlanır.
- Her (strateji, tf, ayar) evrenin her enstrümanında bir kez koşulur; işlemler tek kasada birleştirilir: işlem başı %1 risk,
  toplam açık stop riski ≤ %5, brüt ≤ 3x (sert limitler; aynı anda çok sinyal varsa sıra/ret kuralı motorla aynı).
- Walk-forward: pencereler wf_tarama ile aynı (swing 730/180 gün, daytrade/scalp 365/90). Her eğitim penceresinde ayar,
  evren TOPLAMI PF(R) ile seçilir (min eğitim işlemi evren toplamında: swing 30, diğer 60). OOS birleştirilir.
- Analiz başlangıcı: evrenin ≥ %75'inin verisi olduğu tarih (wf_portfoy min_kapsama ile aynı).

## Geçme ölçütleri (evren OOS)
1. net > 0, PF ≥ 1.2, ≥ 100 işlem, en iyi %5 işlem hariç PF ≥ 0.9, günlük Sharpe ≥ 0.5, max düşüş ≤ %20.
2. Genişlik: işlem yapan enstrümanların ≥ %50'sinde net > 0; tek bir enstrüman OOS kârının ≤ %40'ı;
   üç varlık sınıfından (kripto / hisse / emtia) en az ikisinde net > 0 (sınıfta işlem varsa).
3. Sağlamlık: K1 maliyet ×2 PF ≥ 1.05; K2 aynı enstrüman/zaman/yön/tutma süresiyle rastgele giriş (500) p ≤ 0.05;
   K3 bootstrap PF alt sınırı > 1; K4 komşu ayarların ≥ %60'ında evren PF > 1. DSR toplam deneme sayısıyla raporlanır
   (Haiku Ar-Ge'nin 787 denemesi dahil).

## Seçim
Stil (ajan) başına en çok 3 strateji; skor = OOS Sharpe × (1 − K2 p); seçilenler arası günlük getiri korelasyonu ≤ 0.5.
Geçen yoksa o ajan boş kalır (zorlama yok). Kilitli yıl yalnız BİLGİ amaçlı raporlanır, seçimde kullanılmaz.
Sonuç kullanıcıya sunulur; paper'a geçiş kullanıcı onayıyla.


## GÜNCELLEME 7 (2026-11-08, kullanıcı kararı; WF sonuçları GÖRÜLDÜKTEN sonra, sağlamlık koşulmadan önce)
BIST (13 hisse) evrenden tamamen çıkarıldı. Evren 35 (13 kripto + 17 ABD hissesi + 5 emtia); swing, daytrade ve scalp bu evrende koşar.
Gerekçe: projenin canlı işlem yolu (Binance) BIST içermez; BIST açığa satış kısıtı/ödünç maliyeti ve TRY nominal fiyatlardaki enflasyon trendi
modellenmediği için BIST sonuçları yanıltıcıydı (Güncelleme 6 (C) ile zaten kapı dışıydı). Güncelleme 6 (C) kuralları BIST olmadan etkisizdir.
Tüm WF aşamaları 35 evrenle yeniden hesaplanır; eski (BIST'li) sonuçlar arşivlenir. deneme_kaydi yeni evren imzasıyla ayrı deneme sayar.
