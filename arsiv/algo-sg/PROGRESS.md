# İlerleme Kaydı (otomatik devam için)

DURUM: TAMAMLANDI

## Bağlam
- Hedef: Kripto (Binance USDT-M perpetual, 25 coin), 1D/4H yön + 1H işlem, 2-3 strateji,
  her biri >= %45 kazanma oranı + yüksek kârlılık (PF > 1.3, OOS pozitif).
- Veri: `data/1h/*.csv.gz` (GitHub Actions `fetch-data` iş akışı data.binance.vision'dan çeker;
  oturum ağı borsa API'lerini engelliyor). Yenilemek için `data/REFRESH` dosyasını değiştirip push et.
- Kod: `algo/` (data, indicators, features, backtest, strategies, run). IS: 2020-2023, OOS: 2024-2026.
- Maliyet: taraf başına %0.07 (komisyon+kayma) + funding.

## Adımlar
- [x] PDF -> metinler/*.md
- [x] Veri çekme (25 coin, 2020-01 .. 2026-10)
- [x] Backtest motoru
- [x] S1 (1H RSI/BB trend geri çekilme) — maliyet sonrası kenar yok (PF<1), elendi
- [x] S2 (1H Donchian) — 1H kırılımlar sahte (Davey bulgusu ile tutarlı), elendi
- [x] Teşhis: 2024-26 OOS'ta basit EMA trend filtresinin öngörü gücü yok; aşırı uçlar (kapitülasyon / güçlü momentum) iki dönemde de anlamlı
- [x] **Strateji A (s5)**: 4H Donchian20 kırılımı + 4H hacim>1.5x, 1H giriş, SL=1x4H ATR, %25 kısmi 1R, BE, 10x4H ATR iz/4H EMA100 çıkış, max 480 bar
      => IS WR %52-54 PF 1.39-1.48 | OOS WR %52-53 PF 1.34 (results/grid_s5_d.csv)
- [x] s3 Fibonacci/ölçülü hareket — OOS'ta kenar yok, elendi
- [x] **Strateji B (s4)**: coin'e özgü kapitülasyon dönüşü — WR %63, PF 2.12/1.75
- [x] **Strateji C (s5, günlük Donchian)**: WR %48, PF 1.56/1.36
- [x] Açık pozisyonlar dahil düşüş ve korelasyon analizi
- [x] Stres testi (20 eski/delist edilmiş coin, parametreler değiştirilmeden): A PF 1.35, B 1.56, C 1.37
- [x] Rapor: STRATEJILER.md

## Denetim turu (2. aşama) — TAMAMLANDI
- [x] Kod incelemesi + sayısal doğrulama (DENETIM.md §1): 2 bug, 1 belge-kod çelişkisi, 1 aşırı uyumlu filtre, 1 mükerrer strateji
- [x] PDF uygunluk denetimi (DENETIM.md §2)
- [x] C -> A2 (A'nın ikinci giriş modülü); sistem = A (A1+A2) + B
- [x] Stres evreni + gecikme testi + 8 birim testi

## Kağıt al-sat botu (3. aşama) — DEVAM EDİYOR
- Kullanıcı isteği: 2 ay 7/24, 10.000$ sanal bakiye. strateji-sg reposundaki botla aynı mimari (GitHub Actions + kagit-durum dalı + günlük issue).
- [x] paper/engine.py (kağıt dönemini backtest koduyla yeniden oynatır), paper/fetch_live.py (Binance spot + OKX funding)
- [x] Yerel doğrulama: 2026-08-01 + 60 gün; ortak işlemlerde R farkı 0
- [x] GitHub'da uçtan uca deneme (kagit-deneme.yml): canlı veri 30 sn, motor 18 sn, başarılı
- [x] PR #2 -> main birleştirildi (cron :43); ilk çalıştırmalar ve günlük issue raporu başarılı
- [x] 2026-10-11 09:17 UTC'den itibaren çökme (son_rapor_gunu tz-naive vs tz-aware) -> PR #4 ile düzeltildi, main'e birleştirildi
- [ ] PR #4 sonrası ilk zamanlanmış çalıştırmanın başarısını ve ozsermaye.csv'nin boşluğu doldurduğunu doğrula
- [ ] Haftalık değerlendirme rutini (trig_011SN5xv3ZTEG6hVqMhdyr3M) kapalı; açılması kullanıcı onayına bağlı ("diğer stratejiden zayıfsa gerek yok" kararı)
- Kota notu: iki gizli repo aynı ücretsiz Actions kotasını (2.000 dk/ay) paylaşıyor; bu bot 2 saatte bir (~360 dk/ay).

## 4. aşama — Haftalık yön + günlük işlem (1W/1D) — TAMAMLANDI (rapor: STRATEJILER_GUNLUK.md)
- Teşhis: Elder Impulse haftalık yön filtresi IS/OOS'ta tutarlı (EMA40 OOS'ta ters).
- D1: Elder + Halsey %50 geri çekilme (L/S), ana WR %49 PF 1.58 (IS 1.64 / OOS 1.51), stres PF 1.33 (IS 1.08 zayıf).
- D2: Elder kırmızı değil + 2 günde %20 kapitülasyon (long), ana WR %77 PF 4.1, stres WR %68 PF 2.3.
- Kombine (MTM, bileşiksiz): yıllık %8.3, DD −%11.3, her yıl pozitif. Kağıt bota eklenmedi (kullanıcı kararı bekliyor).

## 5. aşama — Dış depo strateji analizi — TAMAMLANDI (rapor: DIS_STRATEJILER.md)
- Kullanıcının verdiği 10 GitHub deposundaki tüm stratejiler (altyapı örnekleri dahil) çıkarıldı, bizim ölçütlerle test edildi (dis_kaynak/).
- 142 kural (≥1h) + 40 dakikalık freqtrade stratejisi (Actions, kendi zaman diliminde) + Mag7/BIST10/altın/petrol evreni.
- Ön elemeyi 7 aday geçti; sağlamlık testlerini (komşu parametre, 1 gün gecikme, al-tut, 2022) geçen yok. Bota eklenecek strateji yok.
- En yüksek görünen freqtrade sonuçları (GodStraNew, Zeus) geleceği görüyor; düzeltilince kenar kayboluyor.
- Araştırma fikri: QuantDinger "üç ortalama boğa mumu + SMA60 trend" (sağlam ama zayıf, OOS Sh ~0.5).
