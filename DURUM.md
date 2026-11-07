# 1L3A — Durum ve Kararlar

_Son güncelleme: 2026-11-06 (Aşama 1 ara durum)_

## Takım düzeni
- **Lider (Claude Opus):** planlama, görev/ajan dağıtımı, denetim, kalite.
- **Kod:** Sonnet ajanları. **Düşük eforlu işler** (özetleme, veri ayıklama): Haiku ajanları.
- Kararlar kullanıcıyla birlikte verilir.

## Alınan kararlar
1. Strateji seçimi = kitaplarda yaygın (**farklı yazar sayısı**) + kurala dökülebilir + **backtest'te avantaj**.
2. Price action'a zorlanmaz; kurala dökülemeyen elenir.
3. Min zaman dilimi 5 dk. Stratejiler deterministik kod; LLM ajanları her mumda değil, ≥15 dk aralıkla üst seviyede karar verir (rejim, sermaye dağılımı, işlem sonrası analiz).
4. Öğrenme: lider değişiklik önerir → walk-forward test → kullanıcı onayı. Canlıda kendini değiştiren kod yok.
5. Sert risk limitleri LLM kontrolü dışında. Martingale kesin ret.
6. Binance: kripto + TradFi (ABD hisse, emtia) perpetual'ları. BIST yok.
7. Önce paper trading (Binance testnet değil, canlı veri + kendi simülasyon motoru).
8. DigitalOcean'da çalışır; dashboard + Telegram.
9. (2026-11-06) **Az enstrüman, derin uzmanlık:** ajan yüzlerce enstrümanda işlem kovalamaz; az sayıda enstrümanda iyi işlem yapar.
10. (2026-11-06) Önceki projelerden aday stratejileri lider seçer (enstrüman sayısına bakmadan, işe yarayacağını düşündükleri); hepsi 1L3A'da yeniden test edilir. Delist/hayatta kalma yanlılığı ile uğraşılmaz.

## Aşama 0 — tamamlandı
- 50 PDF → `veri/kartlar_ham/` altında **438 kart** (scalp 94, day trade 126, swing 218).
- Birleştirme → `stratejiler/aileler.json`: **100 aile** (stil başına), **13 çıkış/risk modülü**, **70 elenen** (nedenleriyle).
- Aday listesi: [stratejiler/ADAY_RAPORU.md](stratejiler/ADAY_RAPORU.md) — her stil için 10 önerilen + 5 yedek.
- Görsel ağırlıklı, metni olmayan PDF'ler: Bressert, Morge (0 kart).

### Denetim notları
- Listeler **aday**dır; final 10 Aşama 2'de backtest sonucuyla seçilecek (15 aday/stil test edilir).
- **ORB** (day trade #1): Bulkowski'nin 555 hisse testinde mekanik çıkışlarla komisyon sonrası zararlı → testte doğrulanırsa elenir.
- Day trade havuzu zayıf (çoğu tek yazarlı); swing havuzu güçlü (MA kesişimi 12, MACD 7 yazar).
- Bant dönüşü / konsolidasyon kırılımı / stokastik üç stilde birden var → liderin portföy seviyesinde korelasyon/risk izlemesi şart.
- Elenenler: opsiyon, temel/olay verisi, tescilli göstergeler (LuxAlgo, VSA, ML), Level-2/TICK, martingale.
- Kitaplardaki kazanma oranı iddiaları çoğunlukla kanıtsız (raporda "şüpheli" işaretli).

## Aşama 1 — devam ediyor
Yapılanlar:
- **Veri:** Binance API bu bulut makinesinden konum nedeniyle engelli; geçmiş veri `data.binance.vision` arşivinden
  (`motor/veri/`: indirme + sha256 + parquet + 5m→üst TF). Arşivde 2026-10-28 günü tüm sembollerde eksik.
  Funding aralığı sembole göre değişir (BTC 8s, XAU 4s).
- **Sembol envanteri:** `veri/sembol_envanteri.csv` — 1080 sembol. TradFi geçmişi kısa: en eski XAU 2025-12,
  hisseler 2026-01..10 (≈1–10 ay). Sınıflandırma tahmini; kesin liste exchangeInfo ile (API erişimli sunucudan).
- **Backtest çekirdeği:** strateji arayüzü, göstergeler, Decimal motor (komisyon/kayma/funding, step aşağı yuvarlama),
  sert limitler (TASLAK), walk-forward, metrikler. İlk deneme (BTC 5m, EMA 9/21, 2 ay): −%17, komisyon sermayenin ~%9'u
  → 5m'de %1 risk kaldıraç tavanına dayanıyor, maliyet baskın.
- **Sürüyor:** swing ailelerinin kodu (9 aile), stop kayması ayrı + limit "ölç" modu, yazar sayısı denetimi,
  BTC/ETH 2020– 5m veri indirme.

### Aşama 0 denetim bulguları (lider)
- Kartların piyasası: hisse 185, genel 154, vadeli 64, forex 32, **kripto 2**, emtia 1 → kitap iddiaları bizim enstrümanlarda denenmemiş.
- 51 kart 1m kaynaklı (çoğu scalp) → 5m'ye taşınınca "esinlenen" stratejiye dönüşür.
- Day trade önerilenlerin 6/10'u ≤2 yazar; bb-sıkışma ve stokastik tek kart.
- Çok stilli 33 ailenin kanonik kuralı stiller arasında birebir kopya (ör. daytrade__stokastik-donus'un tek kartı Williams %R).
  → Koda dökerken kaynak kartlar esas alınır.
- Yazar sayısı yakın-ama-farklı kurallarla şişmiş olabilir (denetim sürüyor: `stratejiler/yazar_denetimi.csv`).
- 166 kartta stop, 192 kartta kâr al yok → çıkış modülü seçimi sonucu belirleyecek.
- Çoklu test riski (45 aday × ızgara × sembol) → Aşama 2'de eleme eşikleri gerekli.

### Önceki projeler (kapatıldı, arşivlendi)
`algo-sg`, `strateji-sg`, `swing-sg` kapatıldı; kod, stratejiler, sonuçlar, kağıt bot durumları `arsiv/` altında
(kitap/PDF alınmadı — kullanıcı kararı). Dersler ve aday/elenen listesi: [arsiv/OZET.md](arsiv/OZET.md).
Ana ders: önceki sonuçlar OOS'a bakılarak seçilmiş ve kâr birkaç işlemde yoğun → üst sınır kabul edilir.

### Kararlar (2026-11-06, kullanıcı onaylı)
11. **Scalp:** yalnız ≥15m, en güçlü 4–5 aday; hiçbiri geçmezse scalp ajanı kapanır.
12. **Day trade:** 10'a tamamlanmaz; en güçlü 5–6 aday (KGT dahil).
13. **Eleme ölçütü:** maliyet+funding sonrası kârlı, OOS PF ≥ 1.2, ≥ 50 işlem, en iyi %5 işlem çıkarılınca çökmez,
    OOS parametre seçiminde asla görülmez (seçim yalnız walk-forward eğitim pencerelerinde).
14. **Sert limitler kesin:** işlem başı %1, günlük %3 (dolunca açık pozisyon da kapanır), 3x, %20 kill switch.
15. **Sunucu:** DigitalOcean Frankfurt.
16. ~~Veri/seçim: BTC+ETH 2020–; TradFi yalnız doğrulama.~~ (2026-11-06 kullanıcı kararıyla değişti → karar 22)
17. ~~Enstrüman: başlangıçta 3–5 (BTC, ETH, XAU + 1–2).~~ (2026-11-06 → karar 22). README'deki ~25 enstrüman planı iptal.
19. (2026-11-06) **Hepsi test edilir, erken eleme yok:** ~700 aday (438 kart + 160 TradingView + 68 freqtrade + ~30 dış kural).
    Huni: (1) hepsi kodlanır → (2) geniş tarama, yalnız apaçık umutsuzlar elenir → (3) walk-forward (karar 13) →
    (4) kilitli dönem → ajan başına ~3.
20. (2026-11-06) **Kilitli dönem:** 2025-11-01 00:00 UTC sonrası veri kasada. Tarama/walk-forward/seçimde kullanılmaz;
    final seçimde yalnız BİR kez açılır (açılış kayda geçer).
21. (2026-11-06) KGT iki aday: `onceki__kgt` (swing, orijinal, günlerce tutar) + `onceki__kgt-gun` (day trade, gün sonu kapanır).
22. (2026-11-06) **Test evreni (kullanıcı kararı):** yalnız kripto değil. Kripto: BTC, ETH, SOL (Binance verisi).
    TradFi: Magnificent 7 (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA) + altın (XAU) + petrol (WTI) + bakır.
    TradFi geçmişi Binance'ta kısa olduğundan veri **Dukascopy**'den çekilir (`DK_` önekli semboller); canlı işlem
    Binance TradFi perp'lerinde. Maliyet modeli Binance'ınki; Dukascopy verisinde funding yok. Kilit tarihi aynı.
    Canlıda yine az enstrüman (karar 9): enstrüman seçimi testlerin sonucuna göre yapılır.
18. Önceki projelerden alınanlar: 4S kırılım (algo-sg A + swing-sg S2 birleşik), KGT, S1; yedek B. KMN ve S3 alınmadı.

## Aşama 2 — devam ediyor (2026-11-07)
- Katman 1 ✅: 192 strateji kodlu (105 kitap + 87 dış), 226 kart ayarı, 110 dış ayar. 1501+ test.
- Katman 2 ✅ (kripto): geniş tarama 3168 + ızgara ~27k koşu (`sonuclar/tarama/`). Swing %66 PF>1; daytrade %8, scalp %3.
  Uyarı: 2020–25 kripto boğa dönemi (BTC 15x) uzun-trend stratejilerini şişiriyor.
- Katman 3 (kripto) ✅: hızlı walk-forward (`motor/arastirma/wf_tarama.py`; swing 730/180 gün, day/scalp 365/90).
  1140 görevden karar 13'ü geçen 32 (swing 31, daytrade 1, scalp 0). Hiçbiri 3 kripto sembolün üçünde birden geçmedi.
- Katman 3b ⏳: sağlamlık paketi (maliyet ×2, rastgele giriş, deflated Sharpe, bootstrap, parametre komşuluğu, rejim).
- Veri ⏳: Dukascopy'den Mag7 + XAU + WTI + bakır (karar 22), sonra aynı Katman 2–3.

## Kullanıcıyı bekleyen kararlar
- Scalp: kriptoda walk-forward'ı geçen 0. Karar 11'e göre geçen yoksa scalp ajanı kapanır — TradFi sonuçlarından sonra karar.
- Final seçim (ajan başına ~3) ve kilitli dönemin açılması (karar 20) — kullanıcı onayıyla.
- Karar 13 eşikleri çoklu test düzeltmesi içermiyor; sağlamlık paketi öneri kapısı ekliyor (son karar kullanıcıda).

## Yol haritası (2026-11-06)
**Aşama 1 — Altyapı ve adaylar**
- 1A Motor: zorunlu çıkış kuralı; günlük limitte açık pozisyon kapatma; kısmi kâr alma; üst zaman dilimi hizalama
  (haftalık/günlük filtre, lookahead'siz); deneme sayısı kaydı; kâr yoğunlaşması ve günlük MTM düşüş metrikleri.
- 1B Veri: XAU + 1–2 aday enstrüman indirme; enstrüman listesinin kesinleşmesi (3–5).
- 1C Adaylar: swing 10 (✅ 9 + MA kesişim) + önceki projelerden 4S kırılım, KGT, S1 (+ yedek B);
  day trade 5–6; scalp (≥15m) 4–5.
- Bitiş: tüm adaylar kodlu, lookahead testli, 1A özellikleri testli.

**Aşama 2 — Test ve seçim**
- Karar 22 evreni (kripto + Mag7 + XAU/WTI/bakır): her aday için walk-forward (OOS seçimde görülmez), karar 13 ölçütleri.
- Geçenler: rejim analizi (boğa/ayı/yatay), parametre duyarlılığı, rastgele giriş karşılaştırması, maliyet ×2 stresi.
- Hedef: canlıda **ajan başına ortalama ~3 strateji** (10 aday bilerek fazla tutuldu, eleme beklenir). Aralarında korelasyon kontrolü.
- TradFi: Dukascopy uzun geçmişiyle tam test (karar 22); Binance TradFi verisi (2025-12+) kilitli dönemde fiyat tutarlılığı kontrolü.
- Bitiş: her stil için onaylı final listesi + beklenti aralıkları (paper'da karşılaştırmak için).

**Aşama 3 — Pano**
- sg-arge `copytrade/canli/pano.py` örnek alınır. İlke: **pano yeni hesap yapmaz**, yalnız motorun yazdığı durum/kayıt
  dosyalarını biçimler (motor ile pano asla farklı sayı göstermez).
- İçerik: ajan/strateji bazında özsermaye, açık pozisyonlar, kapanan işlemler, risk limitleri durumu, backtest
  beklenti aralığına göre konum, sağlık (veri bayatlığı, servis çalışıyor mu). Telefondan okunur; Telegram özetiyle uyumlu.
- Önce Aşama 2 backtest sonuçlarıyla çalışır, sonra paper verisine bağlanır.
- Bitiş: pano paper'ın ilk gününden hazır.

**Aşama 4 — Paper trading**
- DigitalOcean Frankfurt; Binance WS canlı veri; sanal dolum + hesap/risk/Telegram (sg-arge'den uyarlanır, Decimal), pano bağlı.
- Kağıt motoru = backtest motoru doğrulaması (aynı dönem aynı işlemler); dashboard.
- Süre ≥ 8 hafta; sonuç backtest beklenti aralığıyla karşılaştırılır.
- Bitiş: kesintisiz çalışma + sonuçların beklenti aralığında olması.

**Aşama 5 — Lider ajan ve öğrenme** (Aşama 4 sırasında başlar)
- ≥15 dk aralıkla: rejim tespiti, stiller arası sermaye dağılımı, işlem sonrası analiz, haftalık rapor.
- Değişiklik önerisi → walk-forward test → kullanıcı onayı. Canlıda kendini değiştiren kod yok.

**Aşama 6 — Küçük bütçeyle canlı**
- Gerçek emir yürütücü, borsa filtreleri (exchangeInfo), mutabakat; küçük bütçe; sert limitler aynı.

## Yeniden kullanılacak eski kod
Kullanıcının kendi `sselimgenc-oss/sg-arge` reposu (Hyperliquid copy trade, GPLv3):
`canli/hesap.py` (pozisyon/PnL/funding defteri), `canli/yurutucu.py` sanal dolum, `canli/risk.py`,
`canli/telegram.py`, `deploy/*.service` şablonları → Binance'e uyarlanacak.
Düzeltilecek: miktar yuvarlamada `round` yerine aşağı yuvarlama + `Decimal`; Binance rate-limit / WS 24 saat sınırı.
