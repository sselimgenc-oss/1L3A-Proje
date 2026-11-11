# Yeni sembol sınavı — ÖN KAYIT

Tarih: 2026-11-11. Amaç: canlıya gidecek 4 strateji, ayarlarına HİÇ dokunulmadan, hiç görmedikleri Binance USDⓈ-M perpetual
paritelerinde koşulur; genelleşiyorlar mı, yoksa geliştirildikleri sembollere mi uydurulmuşlar? **KEŞİF testi; canlı planı
değiştirmez.** Tek koşu; sonuç görüldükten sonra kural/sembol/dönem değişmez (zorunlu düzeltme rapor.md'de "SONUÇ SONRASI DEĞİŞİKLİK").

## Stratejiler (kayıt defteri id, varsayılan ayar, ızgara/optimizasyon YOK)
dis__e0v1en (15m), dis__ewo-ema-ofset (15m), dis__hma-atr-rider (1d), dis__lube (1d). Motor: motor.backtest.motor.backtest,
`ham.varsayilan_strateji` ile (kart ayarı varsa ilk kayıt, yoksa sınıf varsayılanı; dördü de "varsayılan"), `limit_modu='olc'`
(araştırma modu, v2 ham ile aynı), funding dahil net R. Kaynak veri 5m (15m ve 1d buradan yeniden örneklenir).

## Sabit kurallar
- Seçim tarihi S = 2023-11-01. Aday: S'de işlem gören (son mum >= S ve S öncesi 30 günde mum var), quote USDT, USDⓈ-M PERPETUAL
  (arşivde 'XUSDT' biçimli; teslimli '_YYMMDD', 'SETTLED' kopyaları ve USDT dışı quote değil); sonradan delist olanlar DAHİL.
- Şart: ilk mum <= S - 730 gün (2021-11-01) (1d arşivinden).
- Hariç: ADA, BCH, BNB, BTC, DOGE, ETH, HYPE, LINK, SOL, TRX, XLM, XRP, ZEC, XAU, NVDA, TSLA; stablecoin'ler; endeks kontratları
  (DEFI, BTCDOM, FOOTBALL, BLUEBIRD, ...); aynı varlığın ikinci kontratı (taban ad: 1000/1000000/1M öneki atılır; S'de işlem
  göreni, ikisi de görürse 30g hacmi yükseği kalır). Tüm kümeler betikte (HARIC_TABAN, STABLE_TABAN, ENDEKS_TABAN).
- Sıralama: [S-30g, S) toplam quote_volume (1d arşiv mumları); ilk 40. Liste koşudan ÖNCE kilitlendi: `semboller.csv`
  (sha256 `ea92b692cbcceaadb19dd1d4b2b452a98f59662bd05b9bd6e4ba04605918358b`); elenenlerin nedenleri `adaylar_tum.csv`.
- Ölçüm dönemi 2023-11-01 00:00 UTC → 2026-10-31 23:59 UTC. Okuma 2021-11-01'den başlar (ısınma; iki evren için aynı; lube 500 gün
  ister). Yalnız S sonrası AÇILAN işlem sayılır (motor `islem_baslangic`). Delist/veri sonunda açık işlem son mumun kapanışından
  kapanır (motor "veri_sonu"). Betik okunan en büyük zamanın 2026-10-31 23:59'u aşmasını SERT hata sayar.
- Eski evren: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, LINK, BCH, TRX, XLM (aynı dönem, aynı kurallar, aynı okuma başı).
- Maliyet: yeni semboller için v2 tablosunun kripto satırlarının EN PAHALISI (efektif komisyon + kayma + stop kayması toplamı en
  büyük; eşitlikte alfabetik ilk) tüm yeni sembollere kopyalanır; eski evren kendi v2 satırlarıyla. ×1 ve ×2 (komisyon+kayma
  çarpılır, funding çarpılmaz; funding gerçek seri). Ana ölçü ×2.
- Tick/step (exchangeInfo erişilemediği için VARSAYIM; yalnız yuvarlama): tick = 10^(floor(log10 p)-4), step = 10^floor(log10(1/p)),
  p = S öncesi 30 gün 1d kapanış medyanı (semboller.csv). Eski evren mevcut kurallarıyla.

## Ölçüler (strateji başına; yeni ve eski evren ayrı)
İşlem sayısı, ΣR, ortalama R, PF (brüt kazanç / brüt kayıp), kazanma oranı, ort. kazanç / ort. kayıp (×1 ve ×2); ΣR(×2) > 0 olan
sembol yüzdesi (payda = evrendeki TÜM semboller, işlemsiz olanlar dahil); sembol başına ΣR(×2) medyanı; sembol düzeyinde
bootstrap (10.000 çekiliş, tohum 20261111, numpy PCG64; semboller iadeli yeniden örneklenir, işlemler birlikte taşınır; çekiliş
ortalaması = ΣR toplamı / işlem toplamı; %90 GA = 5. ve 95. yüzdelik) ortalama R(×2); ΣR(×2)'ye göre en iyi 3 sembol çıkınca ΣR(×2).

## Yorum (yalnız yeni evren, ×2)
- GENELLEŞİYOR: GA alt sınırı > 0 VE sembollerin >= %50'si artı VE en iyi 3 çıkınca ΣR > 0.
- ZAYIF / BELİRSİZ: ortalama R > 0 ama bu üç koşuldan biri tutmuyor.
- GENELLEŞMİYOR: ortalama R <= 0.

## Uyarılar (baştan)
Kripto semboller birbirine yüksek korelasyonlu → semboller bağımsız değil, GA iyimser; tek dönem (2023-11→2026-10); 40 sembolün
bir kısmı delist (kesin sayı: koşu çıktısı delist_duzeltme.csv; bkz. düzeltme) ama liste "arşivde adı geçen" evrenle sınırlı → survivorship kalıntısı (S'den sonra listelenmeyen ya da
arşive girmeyen yok; S'de işlem görüp arşivden silinmiş sembol varsa görünmez). Arşivde 2026-10-28 günü bazı sembollerde eksik olabilir.
Ölçüm dönemi eski evrenin geliştirme/kilit/holdout dönemleriyle örtüşür (eski evren burada referanstır, bağımsız sınav değildir).

## Yeni evren listesi (kilitli, 40)
1. TRB, 2. AVAX, 3. MATIC (delist 2024-09-11), 4. GALA, 5. LTC, 6. RUNE, 7. STORJ, 8. BLZ, 9. DOT, 10. CRV, 11. MKR, 12. 1000SHIB, 13. DYDX, 14. OGN, 15. ETC, 16. ZRX, 17. ATOM, 18. EOS (delist 2025-05-21), 19. FIL, 20. STMX, 21. FTM, 22. AAVE, 23. BAKE, 24. TOMO (delist 2024-05-28), 25. UNFI, 26. AXS, 27. BAND, 28. MASK, 29. NEAR, 30. UNI, 31. HOT, 32. WAVES, 33. KNC, 34. SAND, 35. COMP, 36. LINA, 37. NEO, 38. ENJ, 39. MANA, 40. ALGO

## ÖN KAYIT DÜZELTMESİ (koşudan ÖNCE, 2026-11-11; sonuç görülmedi)
Veri indirilirken fark edildi: arşiv, delist sonrası günlük/5m mumları SIFIR hacimli ve sabit kapanışlı "düz" mumlarla uzatıyor.
Sonuçları: (a) \`semboller.csv\`'deki son_mum/delist sütunları (1d arşivinden) delist'i kaçırıyor (orada yalnız 3 görünüyordu; gerçek
sayı çok daha yüksek); (b) "delist sembolde açık işlem son mumun kapanışından kapanır" kuralı düz mumlarla boşa çıkardı.
Düzeltme (kural aynı, uygulaması netleşti): betik her sembolde 5m quote_hacim > 0 olan SON mumu "son gerçek işlem" sayar, tf mumları
ve funding bu mumu içeren mumda kesilir; açık işlem o mumun kapanışından kapanır. Sembol listesi ve sıralaması DEĞİŞMEDİ
(seçim S öncesi hacimle yapıldı; 40 sembolün hepsinin son gerçek işlemi >= S doğrulandı). \`semboller.csv\` kilitli kalır; doğru
delist bilgisi koşu çıktısı \`delist_duzeltme.csv\`'dedir. Delist eşiği: son gerçek işlem, koşudaki en yeni son işlemden >7 gün eski.
Betik bu düzeltmeyle güncellendi; aşağıdaki sha256 GEÇERLİDİR (ilk commit'teki eski sha geçersiz).

## Betik sha256 (koşudan önce)
525a41e3576213237085cac9ecc6d0f9dba6864f0d017db6dedb859769d3b5b7  araclar/yeni_sembol_sinavi.py
