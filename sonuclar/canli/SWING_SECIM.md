# Swing seçimi (KİLİTLİ kural uygulandı)

**Seçim, 2026-12-08 sadakat kontrolünü geçmeleri şartıyla geçerli; geçemeyen düşer ve sıradaki alınır.**

Kural: `CANLI_PLAN.md` -> SWING SEÇİM KURALI (değiştirilmedi). Girdi yalnız v2 GELİŞTİRME dönemi işlem listesi (holdout okunmadı) ve 250 USD / %1,5 yeniden oynatma (`olcum_250_15.csv`). Paper sonucu, getiri ve Sharpe kullanılmadı.

- T = en büyük tek işlemin R'si / toplam net R (küçük = iyi). Toplam net R <= 0 ise aday düşer.
- K = 250 USD, %1,5, CANLI_LIMITLER yeniden oynatmasında R>3 işlemlerin ATLANAN payı (küçük = iyi).
- Sıra puanı = T sırası + K sırası (1 = en iyi; aynı değerde olanlar aynı (en iyi) sırayı alır). En düşük puan kazanır; eşitlikte küçük T; o da eşitse alfabetik.

## Tablo (puana göre sıralı)

| sira | strateji | T | K | T_sira | K_sira | puan | toplam_r | en_buyuk_r |
|---|---|---|---|---|---|---|---|---|
| 1 | dis__hma-atr-rider | 0.0511 | 53.8% | 1 | 3 | 4 | 131.1 | 6.7 |
| 2 | dis__lube | 0.4123 | 23.8% | 3 | 1 | 4 | 127.9 | 52.7 |
| 3 | dis__gauss-stoch-eth | 0.1840 | 65.6% | 2 | 4 | 6 | 220.9 | 40.6 |
| 4 | dis__haftalik-macd-gunluk-ma | 0.6291 | 29.4% | 4 | 2 | 6 | 111.6 | 70.2 |

## Seçilen iki strateji

1. **dis__hma-atr-rider**
2. **dis__lube**

Eşitlik notu: puan eşitliği vardı, T küçük olan öne alındı.

## Tam sıralı liste (yedek sırası; mekanik)

Seçilen bir aday 2026-12-08 sadakat kontrolünü geçemezse düşer; yerine bu listede sıradaki, kontrolü geçmiş aday alınır (kural dışı aday alınmaz):

1. dis__hma-atr-rider (puan 4, T 0.0511, K 53.8%)
2. dis__lube (puan 4, T 0.4123, K 23.8%)
3. dis__gauss-stoch-eth (puan 6, T 0.1840, K 65.6%)
4. dis__haftalik-macd-gunluk-ma (puan 6, T 0.6291, K 29.4%)

Kalan aday sayısı 2'den azsa Aşama 1 eksik sayıyla başlar (kural 5).
