# 1L3A — Durum ve Kararlar

_Son güncelleme: 2026-11-06_

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

## Sıradaki — Aşama 1
1. Binance'te TradFi perpetual'larının geçmiş veri uzunluğunu kontrol et (yeni listelendikleri için kısa olabilir → gerekirse dayanak varlık verisiyle backtest, seans farkına dikkat).
2. Geçmiş mum verisi indirme ve saklama (`veri/mumlar/`, parquet; repoya girmez).
3. Strateji arayüzü (tek tip: sinyal üret → giriş/stop/hedef) + çıkış/risk modülleri.
4. Backtest motoru: komisyon, kayma, funding, `Decimal` + borsa filtreleri, walk-forward.
5. Aday aileleri koda dök (Sonnet), denetle (lider).

## Yeniden kullanılacak eski kod
Kullanıcının kendi `sselimgenc-oss/sg-arge` reposu (Hyperliquid copy trade, GPLv3):
`canli/hesap.py` (pozisyon/PnL/funding defteri), `canli/yurutucu.py` sanal dolum, `canli/risk.py`,
`canli/telegram.py`, `deploy/*.service` şablonları → Binance'e uyarlanacak.
Düzeltilecek: miktar yuvarlamada `round` yerine aşağı yuvarlama + `Decimal`; Binance rate-limit / WS 24 saat sınırı.
