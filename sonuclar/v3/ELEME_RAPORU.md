# v3 eleme raporu

> Bu rapor yalnız ELEME sonucudur (geçmiş veri). Geçen strateji "işe yarıyor" sayılmaz; kanıt yalnız ileri veridir (ON_KAYIT_V3 bölüm 4). Buradaki sayılar performans beklentisi olarak okunmamalıdır.

- Dondurma: git `d381b83f8c1e`, ön kayıt sha256 `aa7075f83d90`, maliyet tablosu sha256 `d32acbdd8b44`
- Veri sonu: 2026-10-31 00:00:00+00:00; tohum 20261111; rastgele test tekrarı B = 2000

**Sonuç: 0 / 9 satır elemeyi geçti.**

Eleme sıfır strateji verdi; v3 sonucu "0"dır (bölüm 5). Eşik gevşetilmez, yeni varyant denenmez.

| # | Kart | Tür | Durum | Kalan kapılar | p (rastgele) |
|---|---|---|---|---|---|
| 1 | donchian-ansambl-vol-hedef__zarattini | portföy | ELENDİ | P6 | - |
| 2 | funding-7g-haftalik-tercil__vine | portföy | ELENDİ | P4 | 0.1159 |
| 3 | fip-kesitsel-momentum__baptoudur | portföy | ELENDİ | P1, P4, P5 | 0.2529 |
| 4 | kripto-max-piyango-kesit__ozdamar | portföy | ELENDİ | P1, P4 | 0.1934 |
| 5 | vol-yonetimli-long__moreira | portföy | ELENDİ | P6 | - |
| 6 | gunici-momentum-noise-alani__zarattini | tek grafik | ELENDİ | V1, V3, V5 | 0.0005 |
| 7 | btc-gecelik-max10-hafta-sonu__dujava | tek grafik | ELENDİ | V1, V3, V4 | 0.5837 |
| 8 | cuma-15-est-tutma-saatlik__miralles | tek grafik | ELENDİ | V1, V3, V4 | 0.2379 |
| 9 | pre-fomc-surunme__delphic | tek grafik | ELENDİ | V1, V3, V4 | 0.2749 |

## Satır ayrıntıları (kapı sonuçları)

### 1. donchian-ansambl-vol-hedef__zarattini  (pf__v3-donchian-ansambl)
- P1 Kârlılık (net×2 > 0 ve Sharpe×1 eşiği): GEÇTİ
- P2 Örnek (gün ve yeniden dengeleme): GEÇTİ
- P3 Yoğunlaşma (en iyi yıl çıkarılınca net > 0): GEÇTİ
- P4 Rastgele ağırlıktan ayrışma (p): yok
- P5 Hayatta kalma (kill yok): GEÇTİ
- P6 Al-tut kıyası (Sharpe): KALDI
- Nedenler: P6 strateji Sharpe 0.9776626581498848 <= al-tut kıyası 0.9945712836177595 ya da hesaplanamadı

### 2. funding-7g-haftalik-tercil__vine  (pf__v3-funding-7g-haftalik-tercil)
- P1 Kârlılık (net×2 > 0 ve Sharpe×1 eşiği): GEÇTİ
- P2 Örnek (gün ve yeniden dengeleme): GEÇTİ
- P3 Yoğunlaşma (en iyi yıl çıkarılınca net > 0): GEÇTİ
- P4 Rastgele ağırlıktan ayrışma (p): KALDI
- P5 Hayatta kalma (kill yok): GEÇTİ
- P6 Al-tut kıyası (Sharpe): yok
- Nedenler: P4 rastgele-ağırlık p 0.11594202898550725 > 0.1 ya da hesaplanamadı

### 3. fip-kesitsel-momentum__baptoudur  (pf__v3-fip-kesitsel-momentum)
- P1 Kârlılık (net×2 > 0 ve Sharpe×1 eşiği): KALDI
- P2 Örnek (gün ve yeniden dengeleme): GEÇTİ
- P3 Yoğunlaşma (en iyi yıl çıkarılınca net > 0): GEÇTİ
- P4 Rastgele ağırlıktan ayrışma (p): KALDI
- P5 Hayatta kalma (kill yok): KALDI
- P6 Al-tut kıyası (Sharpe): yok
- Nedenler: P1 net(x2) 0.25837962542477366 / Sharpe(x1) 0.4361608669936987 (> 0 ve >= 0.5); P4 rastgele-ağırlık p 0.25287356321839083 > 0.1 ya da hesaplanamadı; P5 kill_olayi(x1) 1

### 4. kripto-max-piyango-kesit__ozdamar  (pf__v3-kripto-max-piyango)
- P1 Kârlılık (net×2 > 0 ve Sharpe×1 eşiği): KALDI
- P2 Örnek (gün ve yeniden dengeleme): GEÇTİ
- P3 Yoğunlaşma (en iyi yıl çıkarılınca net > 0): GEÇTİ
- P4 Rastgele ağırlıktan ayrışma (p): KALDI
- P5 Hayatta kalma (kill yok): GEÇTİ
- P6 Al-tut kıyası (Sharpe): yok
- Nedenler: P1 net(x2) -0.1423373907637694 / Sharpe(x1) 0.4834290889246243 (> 0 ve >= 0.5); P4 rastgele-ağırlık p 0.1934032983508246 > 0.1 ya da hesaplanamadı

### 5. vol-yonetimli-long__moreira  (pf__v3-vol-yonetimli-long)
- P1 Kârlılık (net×2 > 0 ve Sharpe×1 eşiği): GEÇTİ
- P2 Örnek (gün ve yeniden dengeleme): GEÇTİ
- P3 Yoğunlaşma (en iyi yıl çıkarılınca net > 0): GEÇTİ
- P4 Rastgele ağırlıktan ayrışma (p): yok
- P5 Hayatta kalma (kill yok): GEÇTİ
- P6 Al-tut kıyası (Sharpe): KALDI
- Nedenler: P6 strateji Sharpe 0.9180085924145794 <= al-tut kıyası 1.3426854888426505 ya da hesaplanamadı

### 6. gunici-momentum-noise-alani__zarattini  (v3__gunici-momentum-noise-alani)
- V1 Kârlılık (net×2 > 0 ve PF×1 eşiği): KALDI
- V2 Örnek (işlem sayısı): GEÇTİ
- V3 Yoğunlaşma (en iyi yıl çıkarılınca ΣR > 0): KALDI
- V4 Rastgele girişten ayrışma (p): GEÇTİ
- V5 Hayatta kalma (kill yok): KALDI
- Nedenler: V1 net(x2) -0.20168884504887696 <= 0 ya da hesaplanamadı; V1 PF(x1) 0.13056560336385042 < 1.2 ya da hesaplanamadı; V3 en iyi yıl çıkarılınca ΣR <= 0 ya da hesaplanamadı; V5 kill_olayi(x1) 1

### 7. btc-gecelik-max10-hafta-sonu__dujava  (v3__btc-gecelik-max10-hafta-sonu)
- V1 Kârlılık (net×2 > 0 ve PF×1 eşiği): KALDI
- V2 Örnek (işlem sayısı): GEÇTİ
- V3 Yoğunlaşma (en iyi yıl çıkarılınca ΣR > 0): KALDI
- V4 Rastgele girişten ayrışma (p): KALDI
- V5 Hayatta kalma (kill yok): GEÇTİ
- Nedenler: V1 net(x2) -0.016102192612904243 <= 0 ya da hesaplanamadı; V1 PF(x1) 0.9557492392336445 < 1.2 ya da hesaplanamadı; V3 en iyi yıl çıkarılınca ΣR <= 0 ya da hesaplanamadı; V4 rastgele-giriş p 0.5837081459270365 > 0.1 ya da hesaplanamadı

### 8. cuma-15-est-tutma-saatlik__miralles  (v3__cuma-15-est-tutma)
- V1 Kârlılık (net×2 > 0 ve PF×1 eşiği): KALDI
- V2 Örnek (işlem sayısı): GEÇTİ
- V3 Yoğunlaşma (en iyi yıl çıkarılınca ΣR > 0): KALDI
- V4 Rastgele girişten ayrışma (p): KALDI
- V5 Hayatta kalma (kill yok): GEÇTİ
- Nedenler: V1 net(x2) -0.20161250002849018 <= 0 ya da hesaplanamadı; V1 PF(x1) 0.6069336380242267 < 1.2 ya da hesaplanamadı; V3 en iyi yıl çıkarılınca ΣR <= 0 ya da hesaplanamadı; V4 rastgele-giriş p 0.23788105947026486 > 0.1 ya da hesaplanamadı

### 9. pre-fomc-surunme__delphic  (v3__pre-fomc-surunme)
- V1 Kârlılık (net×2 > 0 ve PF×1 eşiği): KALDI
- V2 Örnek (işlem sayısı): GEÇTİ
- V3 Yoğunlaşma (en iyi yıl çıkarılınca ΣR > 0): KALDI
- V4 Rastgele girişten ayrışma (p): KALDI
- V5 Hayatta kalma (kill yok): GEÇTİ
- Nedenler: V1 net(x2) -0.19722897833197472 <= 0 ya da hesaplanamadı; V1 PF(x1) 0.4372632433613715 < 1.2 ya da hesaplanamadı; V3 en iyi yıl çıkarılınca ΣR <= 0 ya da hesaplanamadı; V4 rastgele-giriş p 0.2748625687156422 > 0.1 ya da hesaplanamadı

## Notlar

- Rapor ekleri (Sharpe, düşüş, maliyet ×3, yıllara göre net, geniş stop ATR×20 koşusu, satır 7-8 tüm dönem, satır 9 BTCUSDT) `eleme.csv`'de; kapı değildir.
- Hata veren satır elenmiş sayılır; altyapı hatası (veri okuma/bellek) hiçbir metrik üretilmeden olduysa bir kez yeniden koşulur ve "Güncelleme" olarak yazılır.
