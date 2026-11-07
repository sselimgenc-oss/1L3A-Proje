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
9. ~~(2026-11-06) Az enstrüman, derin uzmanlık.~~ (2026-11-07 kullanıcı kararıyla değişti → karar 23)
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
23. (2026-11-07) **Canlıda enstrüman sayısı artacak (kullanıcı kararı); portföy katmanı zorunlu.** (a) Çok enstrümanlı
    portföy motoru: aynı anda birden çok grafik, portföy düzeyinde sert limitler (günlük %3, %20 kill switch, toplam 3x;
    işlem başı %1 risk her pozisyonda korunur). (b) Tek-grafik stratejilerinin birleşik çalıştırılması (risk üst üste
    binmesi, korelasyon). (c) "Tek enstrüman mimarisi" yüzünden elenen tüm stratejiler (rotasyon, kesitsel momentum,
    çift işlemi, KMN vb.) kodlanıp test edilir — strateji kaçırılmaz. ML ve opsiyon gibi başka nedenle elenenler hariç.
24. (2026-11-07) **Portföy stratejileri için eleme ölçütü (kullanıcı onayı):** işlem sayısı yerine OOS ≥ 3 yıl ve
    ≥ 20 yeniden dengeleme; başarı Sharpe ve düşüşle ölçülür (lider eşikleri: OOS net > 0, OOS Sharpe ≥ 0.5,
    OOS max düşüş ≤ %20). (2026-11-07 güncelleme, kullanıcı onayı: "en iyi %5 gün hariç net > 0" kaldırıldı — al-tut dahil
    hiçbir günlük seri geçemiyordu; yoğunlaşma sağlamlık aşamasında ölçülür.) Tek-grafik stratejilerinde karar 13 aynen geçerli.
25. (2026-11-07) **Portföy risk bütçesi (kullanıcı onayı):** tek-grafik stratejilerinde işlem başı %1 aynen kalır.
    Portföy (hedef ağırlık) stratejilerinde pozisyon başına %1 yerine **portföyün toplam stop riski ≤ %5**; günlük %3,
    %20 kill switch ve 3x tavanı her iki türde aynen geçerli. Değer koddadır (SERT_LIMITLER), ajan aşamaz.
26. (2026-11-07) **Yetki devri (kullanıcı):** canlı para dışındaki strateji/araştırma kararlarını lider sorumluluk alarak
    verir ve sonrasında kullanıcıya bildirir. Canlı para (gerçek emir, sermaye, API anahtarı, sert limitlerin gevşetilmesi)
    her zaman kullanıcı onayı ister. Lider kararları "Lider kararları günlüğü" bölümüne yazılır.
18. Önceki projelerden alınanlar: 4S kırılım (algo-sg A + swing-sg S2 birleşik), KGT, S1; yedek B. S3 alınmadı. KMN portföy katmanında test edilecek (karar 23).

## Aşama 2 — devam ediyor (2026-11-07)
- Katman 1 ✅: 192 strateji kodlu (105 kitap + 87 dış), 226 kart ayarı, 110 dış ayar. 1501+ test.
- Katman 2 ✅ (kripto): geniş tarama 3168 + ızgara ~27k koşu (`sonuclar/tarama/`). Swing %66 PF>1; daytrade %8, scalp %3.
  Uyarı: 2020–25 kripto boğa dönemi (BTC 15x) uzun-trend stratejilerini şişiriyor.
- Katman 3 (kripto) ✅: hızlı walk-forward (`motor/arastirma/wf_tarama.py`; swing 730/180 gün, day/scalp 365/90).
  1140 görevden karar 13'ü geçen 32 (swing 31, daytrade 1, scalp 0). Hiçbiri 3 kripto sembolün üçünde birden geçmedi.
- Katman 3b (kripto) ✅: sağlamlık (`motor/arastirma/saglamlik.py`; kapılar: maliyet×2 PF≥1.05, rastgele giriş p≤0.05,
  bootstrap PF alt sınırı >1, komşu parametrelerin ≥%60'ında PF>1). 32 adaydan 13'ü geçti (öneri). Uyarılar: Bonferroni'yi
  hiçbiri geçmiyor; aynı strateji komşu sembol/TF'de çoğunlukla zayıf; DSR ≈ 0.
- Portföy katmanı (karar 23) ✅ motor + 15 strateji sınıfı (71 adaydan 54 bağlandı) + portföy walk-forward.
  Kripto: 0/15 karar 13; 8'i Sharpe'ta al-tutu geçiyor; 2022'de al-tut −%75, çoğu strateji −%14..+%5.
- Veri ⏳: Dukascopy (karar 22). DK_AAPL 5m tamam (2017–); dakikalık indirme yavaş (9–30 saat). Hızlı yol: aylık
  saatlik dosyalar → swing/daytrade 1h+ testleri önce; 15m/30m dakikalık veri tamamlanınca.

## Lider kararları günlüğü (karar 26)
- 2026-11-07: Portföy sağlamlık paketi eklenir (rastgele ağırlık/sepet kıyası, blok bootstrap Sharpe alt sınırı,
  maliyet ×2, parametre komşuluğu); karar 24'ten kaldırılan yoğunlaşma ölçütünün yerini alır.
- 2026-11-07: Veri kaynağı sabitlendi: DK_ sembollerinde tf ≥ 1h için her zaman 1h dosyası (dakikalık indirme sürerken
  kaynak kayıyordu; 5m'de eksik günler var). k3_dk ve DK içeren portföy koşuları yeni etiketle (v2) yeniden koşulur.
- 2026-11-07: Portföy sonuçları: kripto 5/15 karar 24, sağlamlıkta yalnız pf__kesit_ls (sınırda, p=0.03); hepsi evreni
  1/15 (ibs_donus), sağlamlıkta rastgele kıyastan kaldı. Karar: "hepsi" evreninde OOS 2009'dan başlıyor (yalnız altın
  varken) → portföy koşularında başlangıç, evrendeki sembollerin çoğunun (≥ %75) verisi olduğu tarihe çekilir; v3 ile tekrar.
  v3 sonucu (OOS 2019-01 → 2025-06; emtia 2014 →): sağlam = hepsi: pf__rotasyon (Sharpe 1.12), pf__btc_hedge (0.92);
  hisse_emtia: pf__kanarya (1.60, maliyet×2'de 1.55). Al-tut Sharpe ~1.1 (Mag7 boğası); yalnız kanarya belirgin üstün.

- 2026-11-07: TradFi tek-grafik (sabit veri, k3_dk_v2): WF 198/2877 geçti, sağlamlık 36. Kripto 15. Final tek-grafik
  aday havuzu 51 satır / 34 strateji (`sonuclar/final_aday_havuzu_tek_grafik.csv`); hepsi swing, tek daytrade
  (dis__dual-thrust ETH 1h/30m), scalp 0 (TradFi dakikalık veri bekleniyor). Çok sembolde sağlam: fraktal-alligator (5 hisse),
  rsi-gauss-velocity (3 hisse). Emtiada sağlam tek-grafik yok.
- 2026-11-07: Hisse kısa TF (15m/30m scalp + 30m/1h daytrade, k3_hisse_kisa): WF 27/1358 geçti, sağlamlık 0.
  Karar (karar 11 + 26): **scalp ajanı kapatıldı** (kripto 0, hisse 0 sağlam); emtia dakikalık veri tamamlanınca
  bir kez daha denenir, sağlam çıkarsa yeniden açılır. Daytrade'de tek aday dis__dual-thrust ETH 30m.
- 2026-11-07: **Katman 4 kilitli dönem testi** (ön kayıt `sonuclar/kilit/ON_KAYIT.md`, kilit bir kez açıldı, günlük
  `sonuclar/kilit_acilis.jsonl`; ayarlar kilit açılmadan seçildi). Set ölçütü GEÇTİ: tek-grafik kolu +%17.8 / Sharpe 1.21 /
  düşüş %8.0; portföy kolu −%2.8; 50/50 harman +%7.2 / Sharpe 0.85 / düşüş %4.2. A'da 7'nin 3'ü geçti (cci-esik SOL,
  dual-thrust ETH, kesit_ls). Ayırt edicilik tek-grafikte YOK (C medyan R −0.107 < D −0.054; WF PF ile kilitli PF
  Spearman −0.09). Kilitli dönem artık kullanılmış sayılır. Karar (ön kayıt gereği): set değiştirilmeden Aşama 3 (Pano)
  ve Aşama 4 (paper trading) başlar; seçim yönteminin öngörü gücü zayıf olduğu için paper trading asıl bağımsız sınavdır,
  canlıya geçiş paper sonucu + kullanıcı onayı olmadan konuşulmaz.
- 2026-11-07: Kullanıcı: kilitli yılda geçen 14'lük ayrı izleme listesi istenmedi, final 7 ile devam. Lider kararları:
  (1) paper'da ağırlıklar kilit testindeki set oynatmasıyla aynı (tek-grafik %1/işlem, portföy %5 bütçe, kollar 50/50),
  pf__rotasyon dahil — sert limitler (günlük %3, kill %20) paper'da da durdurucu; (2) paper ayarları WF kuralının
  ileriye devamı: son eğitim penceresi verinin sonuna kadar, yenileme swing/portföy 180 gün, daytrade 90 gün;
  (3) Aşama 2 kapanışı (final_set.json, beklenti aralıkları) ve Aşama 3 Pano v1 başlatıldı.
- 2026-11-07: **Aşama 2 kapandı, Aşama 3 Pano v1 hazır.** `stratejiler/final_set.json` (7), `sonuclar/final/`
  (guncel_ayarlar, beklenti_araliklari, OZET.md, pano_ornek.html), `motor/canli/` (durum sözleşmesi, backtest_durum, pano).
  Güncel ayar (veri sonuna kadar eğitim) 7'nin 4'ünde kilit testindekinden farklı (dual-thrust, fraktal-alligator,
  rotasyon, kesit_ls). Set 8 hafta beklenti: net %5/%50/%95 = −2.6/+2.0/+10.4, düşüş %95 = 3.9 → alarm eşiği.
  Kilit günlüğünde ajanın veri kontrolü sırasında yazdığı 6 "deneme" satırı var (silinmedi: günlük ekle-yalnız).
  **Aşama 4 için zorunlu notlar:** (a) portföy kolu kilit testinde limit_modu="olc" ile koştu — paper'da limitler
  uygulanır olmalı; (b) iki kolun ortak hesap limit kontrolü yazılmalı; (c) bayatlık eşiğine seans takvimi
  (hisse hafta sonu); (d) portföy kolu ortalamasında hafta sonu paydası tutarsızlığı (set.csv mean vs beklenti 0/3) tekleştirilmeli.

- 2026-11-07: Son 1 ay açık kaynak araştırması (Haiku oturumu, kullanıcı onaylı 4 aday) test edildi: hiçbiri final havuza
  girmedi. dis__son1ay-donchian-adx BTC 4h WF+karar 13+sağlamlık geçti (PF 1.93) ama kilitli dönemde (bilgi) PF 0.94;
  kanal 20/10 işlem sayısı yetersiz; TrendRider (OOS 15 gün kısa, al-tut altı) ve E014 makro (düşüş %29.9) karar 24'ten kaldı.
  Yeni veri: DK_SPX, DK_UST (1h). Donchian-ADX BTC 4h yedek gözlem listesinde, sette değil.

- 2026-11-07: **Aşama 4 paper motoru kodu hazır** (`motor/canli/paper*.py`, `deploy/KURULUM.md`). Tekrar modu ↔ backtest
  kilitli dönemde 7/7 stratejide işlem/fiyat/miktar/PnL birebir (NVDA'da 5 çıkışın yalnız zaman etiketi farklı: backtest
  seanslı 4h'ta medyan aralık kullanıyor). Limitler UYGULANIR (tek hesap, iki kol ortak). Açık: fapi.binance.com bu
  konteynerden 451 (konum kısıtı) → canlı WS/exchangeInfo ilk kez sunucuda doğrulanacak; TradFi perp 7/24 vs seanslı
  araştırma verisi (seans süzgeci varsayımı); TradFi funding backtestte yoktu.

- 2026-11-07: GTAA 10 aylık SMA (SPY/EFA/IEF/VNQ/DBC, Haiku araştırma önerisi) paper'a ALINMADI: varlıklar Binance TradFi'de
  yok, SPY'a üstünlük bootstrap'ta kanıtsız, boru hattımızdan geçmedi. Yeniden değerlendirme şartı: Binance vekilleriyle
  karar 24 + sağlamlık, sonra ≥6 ay paper (DD ≤ %15, beklenti aralığında).
- 2026-11-07: Paper sunucusu açıldı (DigitalOcean Frankfurt, Ubuntu 24.04, 2 GB); fapi.binance.com erişimi var ({}),
  repo salt-okur deploy key ile çekildi, veri indiriliyor.

- 2026-11-07 16:12 UTC: **Aşama 4 paper trading BAŞLADI** (DigitalOcean FRA1, servis 1l3a-paper, sanal 10.000 USD, 7 strateji,
  güncel ayarlar). Binance TradFi sözleşmeleri exchangeInfo'da "TRADIFI_PERPETUAL" türünde → kod düzeltildi (cab5d2e), durum sıfırlanıp
  yeniden başlatıldı. Sağlık: tüm semboller bayat değil. Süre ≥ 8 hafta (en erken değerlendirme 2027-01-02). Telegram henüz kapalı;
  pano yalnız sunucuda (telefona yayın yolu açık iş).

- 2026-11-07: Haiku Ar-Ge alt projesi (elenen 120 strateji × XU30/SPX/XAUUSD/UKOIL/BTCUSDT) kapandı: WF'de 3 geçen
  (altın 1d swing, XU30 1h daytrade ×2), hepsi sağlamlıktan kaldı; ön kayıtlı 12 geliştirme varyantı da kaldı → kazanan yok.
  Kayıt: dal claude/haiku-arge-5-enstruman, sonuclar/haiku_arge/KAPANIS.md. Deneme sayısı 787 — DSR hesabında toplam
  deneme sayısına eklenmeli.

## Kullanıcıyı bekleyen kararlar
- ~~Final seçim ve kilitli dönemin bir kez açılması (karar 20)~~ — kullanıcı "aç" dedi (2026-11-07), yapıldı: `sonuclar/kilit/RAPOR.md`.
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
