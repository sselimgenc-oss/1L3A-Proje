# Kripto Day Trade Sistemi (4s/1s yön + 15dk giriş)

Kaynak dokümanlar: kök dizindeki 28 day trading kitabının PDF'leri → metinleri `metinler/*.md`.
İlerleme ve durum: [`PROGRESS.md`](PROGRESS.md).

## Şu anki durum
- **Kağıt al-sat botu çalışıyor:** 10.000 $ sanal, 2026-10-11 → 2026-12-10, yalnızca kripto.
  Ayrıntı: [`kagit/README.md`](kagit/README.md). Günlük raporlar GitHub issue'sunda.
- **Seçili stratejiler** (hepsi yalnız alış, BTC 4s trend filtresi, ayrı alt hesap, gün sonu çıkış):

| Kod | Strateji | Kural özeti | Kitap dayanağı |
|---|---|---|---|
| S10 | Geç seans momentum | 16–20 UTC, fiyat gün açılışının ≥1 günlük ATR üstünde ve 4s/1s yükselişte → al | Lien (momentum, çoklu zaman dilimi), Velez, Tranquil Trader |
| S13 | Yanlış kırılma filtresi | 20 saatlik yeni tepe → 12 mumluk dibe çekilme → 12 mum içinde yeniden kırılım; 1s mükemmel düzen + ADX>25 | Kathy Lien |
| S15 | Trend günü EMA20 geri çekilme | 14 UTC sonrası güçlü günde (≥1 ATR) 15dk EMA20'ye çekilip dönüşte al | Lien, Backus, Christensen |

- **Backtest (25 kripto, 2023-10 → 2026-10, spot maliyet):** 1752 işlem, kazanma %48,8 / %49,5
  (eğitim/test), PF 1,56 / 1,76, 10.000 $ → 15.634 $, maks. düşüş −%5,0. Rapor:
  [`docs/kripto_sonuc2.md`](docs/kripto_sonuc2.md).

## Çalışma geçmişi (raporlar)
1. [`docs/strateji_analizi.md`](docs/strateji_analizi.md) — 28 kitabın ortak paydası, ilk 3 strateji.
2. [`docs/test_sonuclari.md`](docs/test_sonuclari.md) — tüm varlık sınıfları, 8 strateji: hedef tutmadı.
3. [`docs/kripto_sonuc.md`](docs/kripto_sonuc.md) — kripto 1. tur: S10 geç seans momentum.
4. [`docs/kripto_sonuc2.md`](docs/kripto_sonuc2.md) — kripto 2. tur: S13, S15, ayrı alt hesap, BTC filtresi.

## Kod
- `daytrade/` — veri (Binance/Yahoo), göstergeler, özellikler (üst TF hizalama ön-bakışsız), 15 strateji,
  olay tabanlı backtest, seçili parametreler (`secili.py`).
- `kagit/` — kağıt al-sat motoru (geçmişi yeniden oynatma, portföy, raporlama).
- `scripts/` — `fetch_data.py` (veri), `kripto_tara.py` (parametre taraması, eğitim/test),
  `portfoy.py` (portföy simülasyonu), `arastir.py` (strateji × sınıf tablosu).
- `.github/workflows/` — `kagit.yml` (zamanlanmış bot), `kagit_deneme.yml` (deneme),
  `fetch-data.yml` (veriyi `market-data` / `market-data-uzun` dallarına çeker).

## Kullanım
```bash
pip install -r requirements.txt
python scripts/fetch_data.py --days 1100 --tfs 15m 1h 4h --only crypto
python scripts/kripto_tara.py S13_falsebreak '{"n_high":[60,80,120]}' --sabit '{"trend":"po_h1"}'
STR=S10_gec,S13_falsebreak,S15_tdpullback MAXP=9 YON=long BTC=1 AYRI=1 python scripts/portfoy.py 0.0008
python tests/run_tests.py
```

## Backtest varsayımları
Sinyal mum kapanışında, giriş sonraki mum açılışında; aynı mumda stop ve hedef → önce stop; gün
sonunda tüm pozisyonlar kapanır; maliyet (komisyon + kayma) kripto spot %0,08 / vadeli %0,05 tek yön;
parametreler yalnızca eğitim dönemine (ilk %70) göre seçilir, test (son %30) yalnızca doğrulamadır.
