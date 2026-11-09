# swing-sg — Swing Trading Sistemi

Haftalık grafikte yön, günlük grafikte işlem prensibiyle çalışan, 3 stratejili swing trading sistemi.
Stratejiler `metinler/` altındaki 35 swing trading kitabının ortak paydalarından türetildi.

- **Strateji kuralları ve doküman analizi:** [STRATEJILER.md](STRATEJILER.md)
- **Backtest sonuçları:** [SONUCLAR.md](SONUCLAR.md)
- **Kağıt al-sat botu (10.000 $, 60 gün, 7/24):** [kagit/README.md](kagit/README.md) — anlık durum `kagit-durum` dalında `ozet.md`

| | Kazanma oranı | Yıllık getiri | Maks. düşüş |
|---|---|---|---|
| S1 Trend geri çekilme | 52,4% | 19,8% | −16,0% |
| S2 Sıkışma kırılımı | 50,5% | 12,3% | −12,4% |
| S3 Aşırı satım dönüşü | 70,2% | 9,5% | −9,8% |
| **Birleşik sistem** | **56,1%** | **29,1%** | **−12,6%** |

## Klasörler

| Yol | İçerik |
|---|---|
| `metinler/` | PDF'lerden çıkarılmış metinler (.md) |
| `scripts/` | Varlık listesi ve veri indirme |
| `data/raw/`, `data/yardimci/` | Günlük OHLCV verileri, endeks ve kur serileri |
| `swing/` | Göstergeler, stratejiler, backtest motoru, sistem raporu, sinyal taraması |
| `deneyler/` | Parametre taramaları ve sağlamlık testleri |
| `kagit/` | Kağıt al-sat motoru |
| `.github/workflows/` | Veri indirme ve kağıt al-sat iş akışları |

## Kullanım

```bash
pip install pandas numpy tabulate
python -m swing.sistem     # birleşik backtest raporu
python -m swing.tarama     # güncel sinyaller -> sinyaller/GUNCEL.md
BIST_PARA=TL python -m swing.sistem   # BIST'i TL bazında değerlendir
```

Veri kaynakları: kripto için Binance genel piyasa verisi (`data-api.binance.vision`), hisse/emtia/endeks/kur için
Yahoo Finance (`yfinance`). Veri GitHub Actions'ta indirilir (`.github/workflows/fetch-data.yml`).

> Bu çalışma yatırım tavsiyesi değildir. Geçmiş performans gelecekteki sonuçları garanti etmez.
