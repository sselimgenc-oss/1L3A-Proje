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

### Kullanıcı kararı bekleyenler
1. Scalp: 1m kaynaklı kartlar 5m'ye taşınsın mı, yoksa havuz ≥5m kartlarla mı sınırlansın?
2. Day trade havuzu: swing ailelerinin 15m–1h versiyonları eklensin mi / aday sayısı azaltılsın mı?
3. Aşama 2 eleme eşikleri (min işlem, OOS profit factor, maliyet sonrası beklenti vb.).
4. Sert limit değerleri (TASLAK: %1 risk, %3 günlük, 3x, %20 kill switch). Günlük limitte açık pozisyon kapatılsın mı?
5. Sunucu bölgesi: Binance ABD'yi engelliyor → öneri Frankfurt/Singapur.
6. TradFi kısa veri: öneri — seçim kriptoda (2020–), TradFi'de yalnızca doğrulama.
7. ~~Önceki projelerin adayları~~ → karar 10 ile çözüldü.
8. arsiv/OZET.md §1'deki test disiplini kuralları (OOS seçimde görülmez, deneme sayısı kaydı vb.) onaylansın mı?
9. Her stratejide ilk stop dışında zorunlu çıkış (hedef / iz süren / zaman) kuralı.

## Yeniden kullanılacak eski kod
Kullanıcının kendi `sselimgenc-oss/sg-arge` reposu (Hyperliquid copy trade, GPLv3):
`canli/hesap.py` (pozisyon/PnL/funding defteri), `canli/yurutucu.py` sanal dolum, `canli/risk.py`,
`canli/telegram.py`, `deploy/*.service` şablonları → Binance'e uyarlanacak.
Düzeltilecek: miktar yuvarlamada `round` yerine aşağı yuvarlama + `Decimal`; Binance rate-limit / WS 24 saat sınırı.
