# Canlı geçiş planı (kullanıcı onaylı, 2026-11-11)

> **YERİNİ ALDI (2026-11-11, kullanıcı onayı):** geçerli plan `CANLI_PLAN_V2.md`. Bu dosyadaki 4 × 250 USD kadrosu,
> %2/%3 risk artış takvimi, "atlanan > %50 → %2" maddesi ve Aşama 2 artık geçerli DEĞİL. Yalnız SWING SEÇİM KURALI,
> trend kolu ileride canlıya geçerse aday sırası olarak geçerlidir (V2 §6).

Fable + lider ortak önerisi; kullanıcı madde 1 ve 2'yi onayladı, madde 3 (Aşama 2 kasası) sonra karar.
Bu dosyadaki SEÇİM KURALI, sonuç (paper / yeniden oynatma sıralaması) görülmeden yazıldı ve kilitlidir.

## Başlangıç şartı
- v2 paper sadakat kontrolü (2026-12-08) ve Binance testnet denemesi geçilmiş olmalı.
- Sadakati geçemeyen strateji canlıya girmez. Hedef başlangıç: Aralık ortası.

## Aşama 1 — 4 strateji × 250 USD (toplam 1.000 USD)
| Strateji | Tür | İşlem başı stopta kayıp |
|---|---|---|
| dis__e0v1en | 15m | %1,5 → 6. hafta %2 → 12. hafta %3 (şartlı) |
| dis__ewo-ema-ofset | 15m | aynı |
| Swing 1 (kurala göre) | 1d | %1,5 sabit |
| Swing 2 (kurala göre) | 1d | %1,5 sabit |

Diğer limitler CANLI_LIMITLER ile aynı: toplam açık stop riski ≤ %6, brüt ≤ 1,5x, günlük −%6 yalnız yeni giriş
yok, kill −%30 strateji (kalıcı) / −%20 hesap toplamı, izole, kaldıraç stop ≤ %15 → 3x, aksi 2x.

**15m risk artışı şartları (hepsi; kâr/zarar şart DEĞİL):** sistem hatası yok; canlı kayma+komisyon ≤ modelin 1,5 katı;
canlı işlemler paper ile ≥ %95 eşleşme; kill yok. Şart tutmazsa o adım ertelenir (risk düşürülmez, artırılmaz).

**Ölçüm şartı (başlamadan önce):** 250 USD ve %1,5 ile yeniden oynatmada bir stratejinin atlanan sinyal oranı
> %50 ise o strateji %2 ile başlar (15m'de takvim %2 → %3 olarak devam eder).

## SWING SEÇİM KURALI (KİLİTLİ)
Aday havuzu: dis__haftalik-macd-gunluk-ma, dis__lube, dis__gauss-stoch-eth, dis__hma-atr-rider.
1. 2026-12-08 sadakat kontrolünü geçemeyen aday düşer.
2. Kalan her aday için, v2 GELİŞTİRME dönemi (holdout okunmaz) işlem listesinden iki ölçü:
   - T = en büyük tek işlemin R'si / toplam net R (küçük = iyi). Toplam net R ≤ 0 ise aday düşer.
   - K = 250 USD kasa, %1,5 işlem riski ve CANLI_LIMITLER ile yeniden oynatmada, R > 3 işlemlerin
     atlanan payı (küçük = iyi).
3. Sıra puanı = T sırası + K sırası (her ölçüde 1 = en iyi). En düşük puanlı iki aday seçilir.
   Eşitlikte T küçük olan; o da eşitse alfabetik.
4. Paper sonucu, yeniden oynatma getirisi ya da Sharpe bu kurala GİRMEZ.
5. Kalan aday 2'den azsa Aşama 1 eksik sayıyla başlar (yerine kural dışı aday alınmaz).

## Aşama 2 (6–8 hafta sonra, şartlar tutarsa)
2 strateji eklenip 6'ya çıkılır. Kasa kararı kullanıcıda: ek 2 × 250 USD ya da 4 stratejide kalmak.
1.000 USD altıya bölünmez (165 USD'de büyük işlemler daha çok kaçıyor).

## Disiplin
- Kill kalıcıdır; kill olan stratejinin parametresi değiştirilmez, yeniden açılmaz.
- Her hafta canlı–paper raporu (kayma, komisyon, atlanan sinyal, eşleşme).
- jt-awesome-osilator ve voltarget-trend yalnız paper'da izlenir.
- Beklenti (Fable, kaba yargı): en olası sonuç "yatay civarı"; amaç ölçüm ve kontrollü öğrenme.
