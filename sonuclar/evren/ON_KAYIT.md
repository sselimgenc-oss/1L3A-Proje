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
