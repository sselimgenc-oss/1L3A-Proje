# Veri sözleşmesi (modüller arası ortak format)

## Mum DataFrame
- İndeks: `pandas.DatetimeIndex`, **UTC**, mumun **açılış** zamanı, artan sırada, tekrarsız. İndeks adı: `zaman`.
- Sütunlar (float64): `acilis, yuksek, dusuk, kapanis, hacim, quote_hacim`; `islem_sayisi` (int64).
- Eksik mum doldurulmaz (boşluk varsa boşluk kalır); boşluklar raporlanır.

## Funding DataFrame
- İndeks: UTC `DatetimeIndex` (funding zamanı), adı `zaman`. Sütun: `oran` (float64, ör. 0.0001 = %0.01).
- Pozitif oran: long öder, short alır.

## Diskte
- `veri/mumlar/<SEMBOL>/<aralik>.parquet` (ör. `veri/mumlar/BTCUSDT/5m.parquet`)
- `veri/mumlar/<SEMBOL>/funding.parquet`
- `veri/mumlar/` repoya girmez (.gitignore).

## Okuma API'si (motor/veri/depo.py)
- `mum_oku(sembol: str, aralik: str, baslangic=None, bitis=None) -> pd.DataFrame`
- `funding_oku(sembol: str, baslangic=None, bitis=None) -> pd.DataFrame`
