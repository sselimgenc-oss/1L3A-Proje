# Proje Durumu (otomatik kontrol noktası)

Bu dosya, 15 dakikalık kontrol mekanizmasının (Routine) her tetiklenişinde okunur.
Kullanım limiti dolup oturum kesilirse, buradan kalınan yerden devam edilir.

## Hedef
- 1 saat (H1) yön + 5 dakika (M5) giriş ile 2-3 scalp stratejisi
- Kazanma oranı >= %45 ve yüksek kârlılık (Profit Factor > 1.3, pozitif beklenti, örneklem dışı doğrulama)
- Enstrümanlar: ilk 20 kripto, Magnificent 7, BIST30'un en büyük 10 hissesi, altın, petrol
- Kaynak: metinler/*.md (PDF'ler yerine)

## Adımlar
- [x] 1. PDF -> metinler/*.md (commit edildi)
- [x] 2. Doküman analizi -> analiz/ortak_strateji_analizi.md (S1 trend geri çekilme, S2 trend yönlü ortalamaya dönüş, S3 sıkışma kırılımı)
- [ ] 3. Veri kaynağı tespiti (yapıldı: Binance + Yahoo) + veri indirme `python3 -m src.data` (AĞ ENGELİ BEKLENİYOR)
- [x] 4. Backtest motoru (src/) — rastgele yürüyüşle doğrulandı (ileriye bakma yok)
- [ ] 5. 2-3 strateji uygulaması + ilk sonuçlar
- [ ] 6. Optimizasyon döngüsü (dokümanlardaki kurallarla) + örneklem dışı test
- [ ] 7. Final rapor (SONUC.md)

## Engeller
- Ağ politikası: api.binance.com, data-api.binance.vision, query1/2.finance.yahoo.com ve diğer veri siteleri 403 (izinli değil).
  Kullanıcının ortam ayarlarından bu alan adlarını eklemesi gerekiyor. Her kontrolde tekrar test et:
  `curl -s -o /dev/null -w "%{http_code}" "https://data-api.binance.vision/api/v3/ping"`

## Son not
2026-10-10 14:48 UTC: Analiz + motor + optimizer + pipeline + Pine scriptleri hazır ve push edildi.
BEKLENEN: kullanıcının ağ izni (data-api.binance.vision, api.binance.com, query1/query2.finance.yahoo.com).

## Kontrolde yapılacak (sırayla)
1. `curl -s -o /dev/null -w "%{http_code}" https://data-api.binance.vision/api/v3/ping` ve Yahoo testi.
2. Açıksa: `python3 -m src.pipeline` (indir + optimize + SONUC.md). Kapalıysa: sadece yeniden kur, kullanıcıya mesaj tekrarı yapma.
3. Sonuçlara göre (OOS kazanma ≥%45, PF ≥1.3 değilse) dokümanlardaki kurallarla strateji revizyonu:
   - S1: H1 filtre EMA50 eğimi, giriş mumu EMA21 üstü kapanış, seans filtresi (Londra/NY), BE 1R
   - S2: BB 2.5σ, ADX<25, RSI(7), hedef orta bant + kısmi
   - S3: kutu ≤1.0 ATR, H1+M15 mum uyumu (Price Action Scalper), 2R
4. Final: SONUC.md + README güncelle, push, Routine'i kapat.
