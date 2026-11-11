# Yeni sembol sınavı — rapor

Keşif testi; canlı planı DEĞİŞTİRMEZ. Ön kayıt: `ON_KAYIT_YENI_SEMBOL.md`. Tek koşu, parametre/ayar değişikliği yok.

## Kısa sonuç (yeni evren, ×2 maliyet)
| Strateji | Etiket |
|---|---|
| dis__e0v1en | **GENELLEŞMİYOR** |
| dis__ewo-ema-ofset | **GENELLEŞMİYOR** |
| dis__hma-atr-rider | **GENELLEŞMİYOR** |
| dis__lube | **GENELLEŞMİYOR** |

Dört strateji de hiç görmedikleri 40 sembolde **GENELLEŞMİYOR** (ortalama R ≤ 0, güven aralığı üst sınırları bile sıfırın altında).
Aynı dört strateji eski 11 sembolde artıda: avantaj geliştirildikleri sembollere özgü görünüyor. Bu, kriptoda dört stratejinin
"genel bir kenarı" olduğu varsayımını destekleMİyor. Canlı kararı bu rapordan otomatik çıkmaz (keşif testi), ama risk kararı için ciddi bir uyarıdır.

## Ne yapıldı (sade)
- S = 2023-11-01'de Binance USDⓈ-M'de işlem gören, ≥730 gün geçmişi olan USDT perp'lerden hariç tutulanlar çıkarıldı, son 30 gün
  hacmine göre ilk 40 alındı (`semboller.csv`; elenenlerin nedeni `adaylar_tum.csv`). 12 sembol sonradan delist oldu
  (`delist_duzeltme.csv`: MATIC, EOS, TOMO, FTM, WAVES, BLZ, STMX, LINA, UNFI, BAKE, MKR, STORJ); bunlar dahildir, açık işlem son gerçek işlem mumunda kapanır.
- 4 strateji varsayılan ayarla, 2023-11-01 → 2026-10-31 koşuldu; maliyet: v2 tablosunun en pahalı kripto satırı (komisyon %0,05, kayma 5 bps,
  stop kayması 12 bps) ×1 ve ×2; funding gerçek seriyle dahil. Eski evren (BTC, ETH, SOL, BNB, XRP, ADA, DOGE, LINK, BCH, TRX, XLM) kendi satırlarıyla.
- Sembol düzeyinde bootstrap (10.000, tohum 20261111); "en iyi 3 sembol çıkınca" testi.

## Yeni evren (40 sembol) — ×1 ve ×2
| Strateji | İşlem | ΣR ×1 | ΣR ×2 | Ort R ×2 | PF ×1 | PF ×2 | Kazanma ×2 | Ort kazanç / ort kayıp ×2 | ΣR>0 sembol % | Sembol medyan ΣR | GA %90 (ort R ×2) | En iyi 3 çıkınca ΣR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dis__e0v1en | 2008 | -12.4 | -82.2 | -0.041 | 0.97 | 0.84 | %58.5 | 0.37 / 0.62 = 0.60 | %35.0 | -1.28 | [-0.062; -0.019] | -97.5 |
| dis__ewo-ema-ofset | 1152 | -2.7 | -42.8 | -0.037 | 0.99 | 0.90 | %57.8 | 0.57 / 0.87 = 0.66 | %40.0 | -0.22 | [-0.057; -0.017] | -50.7 |
| dis__hma-atr-rider | 973 | -40.0 | -52.2 | -0.054 | 0.84 | 0.79 | %35.5 | 0.58 / 0.40 = 1.44 | %25.0 | -1.54 | [-0.080; -0.027] | -63.8 |
| dis__lube | 119 | -36.1 | -36.9 | -0.311 | 0.39 | 0.39 | %23.5 | 0.83 / 0.66 = 1.26 | %27.5 | -1.01 | [-0.415; -0.199] | -41.4 |

## Eski evren (11 sembol, referans) — ×1 ve ×2
| Strateji | İşlem | ΣR ×1 | ΣR ×2 | Ort R ×2 | PF ×1 | PF ×2 | Kazanma ×2 | Ort kazanç / ort kayıp ×2 | ΣR>0 sembol % | Sembol medyan ΣR | GA %90 (ort R ×2) | En iyi 3 çıkınca ΣR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dis__e0v1en | 267 | 17.3 | 9.3 | 0.035 | 1.34 | 1.17 | %71.2 | 0.33 / 0.70 = 0.48 | %63.6 | 0.47 | [-0.021; 0.100] | -3.2 |
| dis__ewo-ema-ofset | 179 | 32.1 | 26.4 | 0.147 | 1.62 | 1.49 | %68.7 | 0.65 / 0.96 = 0.68 | %81.8 | 2.94 | [0.102; 0.193] | 12.7 |
| dis__hma-atr-rider | 309 | 44.3 | 39.4 | 0.127 | 1.67 | 1.57 | %41.7 | 0.84 / 0.38 = 2.19 | %72.7 | 1.90 | [0.044; 0.234] | 7.6 |
| dis__lube | 35 | 37.4 | 36.8 | 1.050 | 3.52 | 3.43 | %45.7 | 3.24 / 0.79 = 4.08 | %72.7 | 2.14 | [0.274; 1.914] | 7.1 |

Not: eski evren stratejilerin geliştirildiği/seçildiği semboller; dönem de geliştirme+kilit+holdout ile örtüşür. Referanstır, bağımsız sınav değildir.

## Strateji başına yorum
**dis__e0v1en** — GENELLEŞMİYOR

15 dakikalık, yalnız long, kısa vadeli dip alım stratejisi. Yeni evrende ortalama işlem başına -0.041 R kaybettirdi; 40 sembolün yalnızca %35'i artıda. Eski 11 sembolde ise hafif artıydı (ort. R 0.035) ama orada da güven aralığı sıfırı kapsıyor. Yani eski evrendeki avantaj zaten ince; yeni sembollerde maliyeti (×2) karşılayamıyor.

**dis__ewo-ema-ofset** — GENELLEŞMİYOR

15 dakikalık dip alım. Yeni evrende ×1 maliyetle neredeyse başa baş (ΣR -2.7), ×2 maliyetle zarar (ΣR -42.8); güven aralığı tamamen sıfırın altında. Eski evrendeki güçlü sonuç (ort. R 0.147, 11 sembolün %82'i artı) yeni sembollere taşınmadı. Maliyete çok duyarlı: ×1→×2 farkı küçük bir kenarı silip eksiye çeviriyor.

**dis__hma-atr-rider** — GENELLEŞMİYOR

Günlük trend takipçisi. Yeni evrende ×1 maliyetle bile zarar (ort. R -0.041); sembollerin yalnızca %25.0'i artıda. Eski evrende ise 0.127 R ortalama ve %73 artı sembol vardı. Trend stratejisi olduğu için dönem etkisi (2023-26 dalgalı/yatay altcoin piyasası) de olabilir; ama sonuç net: geliştirildiği büyük sembollerin dışına çıkınca avantaj görünmüyor.

**dis__lube** — GENELLEŞMİYOR

Günlük, düşük işlem sıklığı. Yeni evrende 119 işlemde ortalama -0.311 R kayıp (PF 0.39), en kötü sonuç. Eski evrende ise 35 işlemde ortalama 1.05 R ile en parlak sonuçtu; bu fark, eski evrendeki sonucun az sayıda işlem ve belli sembollere (XRP, XLM, BCH) bağlı olduğunu, yani uydurma/şans riskini güçlü biçimde düşündürür.


## Uyarılar
- **Kripto korelasyonu:** semboller birbirine bağlı (BTC hareketiyle birlikte oynar); 40 sembol 40 bağımsız deneme değil. Bootstrap güven aralığı bu yüzden olduğundan dar olabilir. (Sonuç zaten olumsuz yönde net.)
- **Tek dönem:** 2023-11 → 2026-10. Başka bir dönemde sonuç farklı çıkabilir; özellikle trend stratejisi (hma-atr-rider) rejime duyarlıdır.
- **Survivorship kalıntısı:** adaylar arşiv listesinden süzüldü; delist olanlar dahil (12/40) ama arşivde hiç yer almayan sembol görünmez.
  Delist öncesi son dönem (likidite çöküşü, kayma) modelde tablo maliyetinin ötesinde zarar yaratmış olabilir; model bunu yakalamaz.
- Maliyet yeni semboller için "en pahalı kripto satırı" olarak sabit alındı (tutucu); gerçekte küçük altlarda kayma daha da yüksek olabilir.
- Tick/step değerleri exchangeInfo olmadan türetildi (varsayım; yalnız yuvarlama etkisi).
- Veri kapsama kontrolü: ölçüm döneminde 5m mumlarda 1 saatten uzun boşluk yok; 2022-02-26/28 ve 2022-04-01/02 arşiv boşlukları bazı sembollerde var (ısınma döneminde, ölçüm dışı). Bazı delist olmuş sembollerin funding kaydı son işlemden sonra da/önce de eksik uçlu olabilir (delist sonrası zaten işlem yok).

## Ön kayıt düzeltmesi (koşudan ÖNCE yapıldı, sonuç görülmeden)
Arşiv delist sonrası düz, sıfır hacimli mumlarla uzuyor; bu yüzden "son gerçek işlem mumu" (hacim>0) esas alındı. Ön kayıtta
düzeltme bölümü ve yeni betik sha256 koşudan önceki commit'tedir. SONUÇ SONRASI DEĞİŞİKLİK: yok.

## Kendi denetimim (ayrı yoldan)
`araclar/yeni_sembol_denetim.py` → `denetim.json`. Rastgele 3 sembol (DOTUSDT, ENJUSDT, STMXUSDT) × 4 strateji:
- (a) ΣR ayrı yoldan hesaplandı (parquet'i doğrudan okuma, elle yeniden örnekleme, elle yazılmış maliyet sayıları): 24 karşılaştırma (×1 ve ×2),
  hepsinde işlem sayısı ve ΣR birebir aynı: True.
- (b) ×2 maliyet gerçekten uygulanıyor: elle ×2 değerleriyle (komisyon %0,10, kayma 10 bps, stop 24 bps) kayıtlı sonuçla birebir eşleşti; ×1 ve ×2'de
  işlem zamanları aynı, hiçbir işlemde ×2 R'si ×1'den iyi değil (iyi olan sayısı: 0).
- (c) Lookahead yok: veri 2025-06-01'de kesilip yeniden koşuldu; kesim öncesi kapanan işlemler tam koşuyla birebir aynı: True.
- Sert tarih doğrulaması: okunan en büyük mum açılışı 2026-10-31 23:45:00+00:00 (≤ 2026-10-31 23:59); en büyük funding zamanı 2026-10-31 20:00:00.003000+00:00.

## Dosyalar
`semboller.csv`, `adaylar_tum.csv`, `delist_duzeltme.csv`, `maliyet_tablosu_yeni_sembol.csv`, `sonuc_strateji.csv`, `sonuc_sembol.csv`,
`ozet.json` (girdi sha256, commit, işlem dosyası hash'leri), `denetim.json`, `kilit_acilis.jsonl` (kilitli dönem okuma kaydı). İşlem listeleri
`islemler/` altında (parquet; git dışı, hash'leri ozet.json'da).
