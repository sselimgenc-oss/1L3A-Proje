# TradingView stratejileri: eleme ve kağıt test (görev tanımı)

Kullanıcı TradingView'de yayımlanmış açık kaynak stratejileri test etmek istiyor. Kullanıcıyla Türkçe, kısa yazışılır.
Gelecekte 1 PDF daha gelecek; aynı hattan geçer.

## Girdi
- `tv/kaynak/linkler.txt`: 164 benzersiz betik linki (iki PDF'den). PDF metinleri aynı klasörde (yazar, beğeni, yazarın iddia ettiği sonuçlar).
- Pine kaynağı: sayfadaki `PUB;<32hex>` kimliği → `https://pine-facade.tradingview.com/pine-facade/get/PUB%3B<id>/last` (JSON, `source` alanı). Ağ izni var.
  Kaynağı gelmeyen (protected / invite-only) betik → "kapali" diye işaretle, atla.

## Aşama 1 — Ön eleme (164 → ~30-40). Ucuz, kod çalıştırmadan.
Her betik için `tv/aday.csv`: id, ad, yazar, link, tur (strategy/indicator), erisim, zaman_dilimi, yon (long/short/ikisi),
pazar (kripto/hisse/emtia/vadeli/forex), karar (al / ele), neden. Pine kodları `tv/pine/<id>.pine` olarak saklanır.
Ele:
- strategy() olmayan (gösterge), eğitim/şablon/altyapı betikleri;
- kaynak kapalı;
- `lookahead=barmerge.lookahead_on` ile geleceği gören `request.security` (offset olmadan), `calc_on_every_tick` bağımlı, repaint eden pivot/zigzag girişleri (sinyal geçmişe yazılıyorsa);
- yalnız tick/emir defteri/opsiyon/sentetik spread verisi gerektirenler, 1 dk altı scalping;
- aynı mantığın kopyası (en iyisini tut).
Kalanları aileye göre grupla (trend, kırılım, ortalamaya dönüş, SMC/ICT, osilatör...) ve en fazla ~40 seç.

## Aşama 2 — Python'a çevirme ve backtest
- Kod: `tv/stratejiler/<kisa_ad>.py`, ortak motor `tv/motor.py` (bar kapanışında sinyal, SONRAKİ barın açılışında giriş; stop/hedef mum içinde, ikisi aynı mumda olursa önce stop).
  Pine'daki `strategy.exit` stop/limit, trailing, pyramiding=0 varsayılanı, `process_orders_on_close` gibi ayarları birebir uygula.
- Varsayılan Pine parametreleri kullanılır; OPTİMİZASYON YOK (yalnız Aşama 3'teki ±%20 sağlamlık testi).
- Pozisyon boyu: işlem başına sabit %1 risk (stop varsa), stop yoksa sabit %10 sermaye. Sonuçları R ile de raporla.
- Masraf (taraf başına): kripto %0,07, ABD hisse %0,02, BIST %0,10, emtia vadeli %0,03; kayma +%0,02.
- Veri:
  - kripto: Binance spot `data-api.binance.vision` (uzun geçmiş, 15dk/1s/4s/1g), 2019→bugün. Mevcut önbellek: `backtest/kripto_veri.py`.
  - hisse/emtia: Yahoo (yfinance). Günlük 2015→; saatlik son ~730 gün; 15dk yalnız 60 gün (15dk hisse stratejisi 1s'e uyarlanır ya da yalnız kriptoda test edilir). Örnek: `araclar/veri_hisse.py`.
- Enstrüman seçimi stratejiye göre (her stratejide hepsi gerekmez, uyanı seç ve neden yaz):
  - BIST (~10): THYAO, ASELS, AKBNK, GARAN, KCHOL, BIMAS, TUPRS, EREGL, FROTO, SISE (.IS)
  - ABD (10): Mag7 (AAPL MSFT GOOGL AMZN META NVDA TSLA) + AVGO, JPM, LLY
  - kripto (12-15): BTC ETH SOL BNB XRP ADA DOGE AVAX LINK DOT LTC TRX + likit 1-3 tane
  - emtia: altın GC=F, gümüş SI=F, petrol CL=F
  Yazarın test ettiği pazar/zaman dilimiyle başla; NQ/ES vadeli stratejisi → QQQ/SPY veya Mag7, forex → atla ya da altın.
- Dönem bölme: eğitim = ilk %70, görmediği dönem (OOS) = son %30. Parametreler değişmez; bu sadece çöküş testi.

## Aşama 3 — Eleme kuralları (kullanıcı onaylı, 13 Eki 2026; değiştirme)
Tüm veride (portföy, seçilen enstrümanlar birlikte) ZORUNLU:
1. İşlem sayısı: swing ≥ 100, day trade ≥ 300
2. Maks. düşüş ≤ %20
3. Beklenti ≥ +0,15R (stop yoksa işlem başı ort. getiri / ort. kayıp ile eşdeğeri)
4. Kâr faktörü ≥ 1,3 ; Sharpe (günlük, yıllık) ≥ 1,0
5. OOS Sharpe ≥ eğitim Sharpe × 0,5 (ve OOS'ta kârda)
6. Maliyet ×2'de kâr faktörü ≥ 1,1
7. Parametre ±%20 (her sayısal parametre ayrı ayrı ve birlikte, ~20 komşu): komşuların ≥ %70'i kârda
8. Enstrümanların ≥ %60'ında kârda
Kazanma oranı tek başına eşik değil (raporda göster).
Sıralama (geçenler arası): Calmar ≥ 1, en uzun düşüş süresi < 6 ay, PSR ≥ %90, işlem başı ort. kâr ≥ 3× maliyet,
mevcut 14 stratejiyle korelasyon ≤ 0,6 (günlük getiriler: `ortak/backtest_gunluk_getiri.csv`).
Çıktı: `tv/sonuclar/ozet.csv` (her strateji × her ölçüt, geçti/kaldı) ve `tv/RAPOR.md` (Türkçe, kısa: kaç aday, kaç çevrildi, kaç geçti, neden kaldılar).

## Aşama 4 — Geçenler hemen kağıt teste (kullanıcı onaylı)
- `tv/kagit.py`: geçen stratejileri canlı veriyle çalıştıran kağıt bot. Mevcut botların mantığı: her çalıştırmada başlangıç tarihinden
  itibaren geçmişi YENİDEN OYNATIR (kaçırılan saat işlem kaybettirmez), `--durum <dizin>` ile durum klasörüne yazar:
  `durum.json`, `islemler.csv` (giris/cikis zamanı, sembol, yön, fiyatlar, R, kâr $, sebep: giriş ve çıkış nedenleri Türkçe tek cümle),
  `ozsermaye.csv` (saatlik toplam ve strateji bazında). Bütçe 10.000 $ sanal, geçen stratejiler arasında eşit.
  Örnek format: `canli/kagit.py` ve swing-sg `karsilastirma/panel_veri.py` (panel bunu okuyor).
- Başlangıç: geçişten sonraki ilk gün 00:00 UTC; süre ~57 gün (diğer testlerle aynı bitiş: 9-10 Aralık 2026).
- Durum dalı: `kagit-tv-durum`. Saatlik tura ve panele bağlamayı koordinatör oturum yapacak; sen `python3 -m tv.kagit --durum X` komutunun tek başına çalıştığını göster.

## Kurallar
- Türkçe, kısa. Gerçek para yok. Mevcut botlara/kurallara/`canli/`'ya DOKUNMA.
- Dal: `tv-eleme`. Sık commit + push. Bitince main'e PR aç (birleştirmeyi koordinatör yapar).
- Her aşama sonunda `tv/DURUM.md`'yi güncelle (ne bitti, ne kaldı) ki oturum düşerse kaldığı yerden devam edilsin.
- Belirsizlikte makul varsayımı seç ve RAPOR'a yaz; kullanıcıya soru sorma.
