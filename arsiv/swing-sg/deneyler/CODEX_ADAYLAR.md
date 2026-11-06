# Codex'in bulduğu 12 GitHub stratejisi — denetim ve test (2026-10-11)

Kaynak: kullanıcının yüklediği `github_trading_stratejileri.pdf` (Codex). Repolar yalnızca okundu, kodları çalıştırılmadı.

## Kod denetimi (11 repo)
| # | Repo | Karar | Neden |
|---|---|---|---|
| 1 | erhungn/volatility-regime-momentum | TEST | Basit, OHLCV, günlük; ama dolum sinyal mumunun kapanışında, parametreler tüm dönemde ayarlanmış |
| 2 | fridary/options-flow | RED | Kod yok, opsiyon verisi + dakikalık, test kısmında 9 işlem, 880 ayardan seçilmiş |
| 3 | koichi055/ema-gold-trader-ea | RED | Başlangıç stopu yok; yalnızca 2025 altın boğasında tek MT5 koşusu |
| 4 | kunal14901/KA-MATS | BELKİ | Reponun kendi doğrulama dosyası başlık rakamların tekrarlanamadığını söylüyor (OOS beklenti CI'si sıfırı içeriyor) |
| 5 | abailey81/Crypto-Statistical-Arbitrage | RED | Piyasa nötr çift işlem (açığa satış), veri yok; vadeli eğri PF 28 inandırıcı değil |
| 6 | jicheolha/crypto-trading-bot | BELKİ | Sinyal kodu gizlenmiş, işlemlerin %60'ı açığa satış, Optuna tüm dönemde |
| 7 | niranjan-kamal/ES_futures | RED | 6,5× kaldıraç, 43 işlem, opsiyon verisi yok |
| 8 | lutfi-zain/quant-lttd-ichimoku | BELKİ | Tek varlıkta 10 işlem, eşikler aşırı ayarlı |
| 9 | a1shmuk/xauusd-algo-trader | RED | Geleceği görme hatası (swing dipleri sonraki mumlarla bulunuyor) + 4.374 ayar |
| 10 | jehumtine/markov-chain | RED | Geleceği görme hatası (4s kapanışı 1s mumuna erken sızıyor, bfill) |
| 11 | michael05josh-netizen/eurusd-london-bot | RED | Süre dolumuyla kapanan işlemler kâr/zarardan tamamen atılmış |

## Bizim çerçevede test (`deneyler/codex_adaylar.py`)
Günlük mum, kapanışta sinyal / ertesi açılışta giriş, sınıf maliyetleri, tüm evren. "bizim" = haftalık HA yönü + sınıf rejim filtresi eklenmiş.

| Aday | OOS işlem | OOS KO | OOS PF | 2022 PF | Yıllık | Maks. düşüş | Sharpe |
|---|---|---|---|---|---|---|---|
| Mevcut S1+S2+S3 | 1070 | %55 | 1,62 | 1,70 | %29,2 | −%12,6 | 1,40 |
| C1 vol. momentum (bizim) | 1349 | %52 | 1,46 | 1,35 | %14,7 | −%10,3 | 1,20 |
| C2 KA-MATS geri çekilme (bizim) | 638 | %41 | 1,17 | 1,30 | %10,7 | −%23,3 | 0,80 |
| C3 sıkışma kırılımı (bizim) | 52 | %35 | 0,55 | — | %0,4 | −%6,8 | 0,24 |
| C4 Ichimoku trend (bizim) | 301 | %41 | 2,52 | 1,35 | %30,8 | −%13,2 | 0,64 |

Mevcut sisteme eklendiğinde hiçbiri Sharpe'ı artırmadı (1,40 → C1 1,35 · C2 1,19 · C3 1,37 · C4 0,66).

## Sonuç
- Hiçbiri sisteme eklenmiyor; kağıt botlarına dokunulmadı.
- C1 bağımsız olarak kabul edilebilir ama mevcut S1/S2 ile aynı fırsatları daha düşük kaliteyle yakalıyor.
- C4 OOS'ta yüksek beklenti (ort. +0,68R) veriyor ama KO %41 < %45 ve oynaklık yüksek; aylarca tutan bir trend
  sistemi olduğu için zaten `trend/` kollarının (BTC/ABD trend) işlevini görüyor.
- Codex'in tablosundaki rakamlar repolarda gerçekten yazıyor, ama 11 reponun 3'ünde geleceği görme/P&L hatası,
  4'ünde eksik kod/veri var; başlık rakamlar bizim kurallarla tekrarlanamadı.
