# HGT — Haftalık yön, günlük işlem (kripto) — Sonuç: BAŞARISIZ, kağıt bota eklenmedi

**Kaynak:** 20 Trading Stratejisi, Sistem #5 ("Çoklu Zaman Çerçevesi Sistemi"). Kitapta 15 dakikalık grafikte yön, 5 dakikalıkta işlem önerilir; burada haftalık yön, günlük işlem olarak uyarlandı.
- **Yön (kapanmış haftalık mumlar):** fiyat > EMA3, EMA3 > EMA5 > EMA15 > EMA45, kaydırmalar kitaptaki gibi. Kitaptaki "histogramlar yeşil" şartı için MACD histogramı > 0 kullanıldı.
- **Geri çekilme (isteğe bağlı):** fiyat haftalık EMA5'e değmiş olmalı.
- **Günlük tetik:** kapanış tüm günlük EMA'ların üstünde, EMA15 > EMA45.
- **Giriş ve stop:** giriş ertesi gün açılışta; stop son 5 günün dibinin altında, 1–3 × ATR aralığına sıkıştırılmış.
- **Çıkış:** kitaptaki 1:1 hedef, haftalık dizilimin bozulması, ya da bozulma + günlük EMA15 kırılımı (1R'de %15 kısmi kâr ve başabaş ile).
- **Portföy:** o ayın hacim sıralamasında ilk 20 coin, en fazla 6 pozisyon, işlem başına %1 risk, kaldıraçsız. Masraf %0,07 + fonlama. Aynı backtest motoru kullanıldı (`backtest/kripto_motor.py`).
- **Kod:** `backtest/hgt.py`. Ayarlar 2020–2023'te (IS) seçildi, 2024–2026/09'da (OOS) kontrol edildi.

## Sonuçlar (52 varyant)
Varyant tanımları: `dok` kitaptaki EMA dizilimi; `ema1020` haftalık EMA10/20 kuralı; `haftalik` haftalık dizilim bozulunca çıkış; `trend` dizilim bozulunca ya da günlük EMA15 altında kapanışta çıkış.

| Varyant | IS CAGR | IS DD | IS Sharpe | OOS CAGR | OOS DD | OOS Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| `dok`, `haftalik` çıkış (IS'in en iyisi) | 43,4 | 25,0 | 1,39 | −6,7 | 30,5 | −0,28 |
| `dok`, `trend` çıkış | 31,1 | 18,3 | 1,29 | −2,9 | 33,6 | −0,07 |
| `ema1020`, `trend` çıkış | 34,2 | 41,1 | 1,11 | 1,8 | 31,5 | 0,19 |
| Kitaptaki 1:1 hedef (en iyisi) | 5,0 | 23,7 | 0,44 | −5,5 | 22,6 | −0,38 |
| Kitaptaki geri çekilme şartı ile | ≤ 1,5 | — | ≤ 0,5 | < 0 | — | < 0 |
| BTC tek başına, `dok`, `haftalik` | 16,8 | 23,6 | 1,00 | 0,4 | 8,7 | 0,09 |
| Rastgele giriş (20 deneme ort.) | 4,7 | — | 0,31 | −6,1 | — | −0,16 |
| Karşılaştırma: KGT v3 + KMN (canlıdaki) | | | | | 15,6 (tüm dönem) | 1,99 (tüm dönem) |

- **OOS'ta çalışmıyor.** 52 varyantın hiçbirinde OOS Sharpe 0,25'i geçmiyor; çoğu negatif. Varyantlar şunlardı: evren 5/10/20 coin, BTC rejim filtresi, long+short, histogram şartı var/yok, geri çekilme var/yok.
- **IS kârı tek bir boğa piyasasından geliyor.** Kârın neredeyse tamamı 2020–2021'de. Yıllık getiriler: 2020 +%85, 2021 +%133, 2022 −%9, 2023 +%7, 2024 −%10, 2025 −%11.
- **2024 örneği:** BTC o yıl +%121 yaptığı halde strateji kaybetti. Haftalık sinyal geç geliyor, günlük stoplar ise sık patlıyor.
- **Kitabın kendi kuralları daha da zayıf.** 1:1 hedef kârı kesiyor (CAGR %2–5). Kaydırılmış EMA5'e geri çekilme şartı haftalıkta çok seyrek oluşuyor: 4 yılda 15–28 işlem.
- **Değerlendirme:** 2020–2023'te rastgele girişten iyiydi (Sharpe 1,39'a 0,31). 2024–2026'da ise rastgele girişten farkı yok. Mevcut KGT v3 (günlük yön, saatlik giriş) ve KMN aynı dönemde kârlıydı.

**Karar:** Kağıt bota eklenmedi. Fazla ayar denemesi aşırı uyuma yol açacağı için ızgara genişletilmedi.
