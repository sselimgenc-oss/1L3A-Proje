# Kart ayarları

Bir strateji ailesinin (sınıf `ad`'ı, örn. `swing__bant-donus`) belirli bir kitap kartına göre ayarlanmış hâli.
Dosya: `stratejiler/kart_ayarlari/<ad>.json`, içerik bir liste:

```json
[
  {
    "kart_id": "swing__bant-donus__ornek-yazar",
    "parametreler": {"periyot": 20},
    "cikis_ayarlari": {"kismi": [[1.0, 0.25]], "basabas_r_esigi": 1.0},
    "not": "Kitaptaki 20 periyot varyantı"
  }
]
```

- `kart_id`: `veri/kartlar_ham` içinde var olmalı ve ailenin `kaynak_kartlar` listesinde olmalı.
- `parametreler`: yalnız sınıfın `varsayilan_parametreler` anahtarları; yazılmayanlar varsayılan kalır.
- `cikis_ayarlari`: `null` (sınıf varsayılanı) veya `CikisAyarlari` alanları (`kismi` iç içe liste yazılır).
- `not`: serbest metin.

Kullanım: `motor.strateji.kayit.kart_ayarli_strateji(ad, kart_id)`. Denetim: `kayit.dogrula()` (testler/test_kayit.py).
