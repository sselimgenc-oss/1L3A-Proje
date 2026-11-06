# Kaldıraç testi — KGT v3, KMN ve KGT %50 + KMN %50 (2026-10-12)

Kod `backtest/kaldirac.py`. Motora izole teminat tasfiyesi eklendi (`backtest/kripto_motor.py`, varsayılan kapalı). L = 1 satırları önceki nihai sonuçlarla birebir aynı: %33,6 / %29,5 / 1,28; %55,2 / %18,1 / 1,86; %45,7 / %15,6 / 1,99.

**Varsayımlar**
- **Dönem:** 2020 – 2026/09. Masraf %0,07/taraf. Fonlama Binance USDT-M'nin gerçek oranları; OKX geçmişine bu ortamdan erişim yok.
- **Tasfiye mesafesi:** 1/L − %0,5. Tasfiyede kayıp, pozisyonun teminatının tamamı (notional / L); işlem sonradan kârlı kapanacak olsa bile.
- **KGT tasfiye kontrolü:** Stop tasfiye seviyesinden uzaksa ve 1 saatlik dip ya da tepe stoptan önce tasfiyeye değerse işlem tasfiye olur. 1R'de stop başabaşa çekilince risk kalkar.
- **KMN tasfiye kontrolü:** Her coin pozisyonu için, dengelemeden sonraki günlerin en kötü fiyatına bakılır (1 saatlik mumlardan günlük dip ya da tepe). Her dengelemede pozisyon yeniden teminatlandırılır.
- **Senaryo (a), aynı risk:** Pozisyonlar aynı kalır; kaldıraç yalnız teminatı azaltır.
- **Senaryo (b), büyütme:** KGT'de işlem riski ve brüt sınırı × L; KMN'de brüt maruziyet × L.

## Sonuçlar
Sütunlar: yıllık getiri (%), en büyük düşüş (%, günlük piyasa değeriyle), Sharpe, 2022 getirisi (%), 2024+ dönemi (yıllık getiri / düşüş / Sharpe), tasfiye sayısı. Tasfiye sayısı KGT'de alt portföy başına; KMN'de 14 kaydırmanın ortalaması.

| Senaryo | L | KGT | KMN | KGT + KMN %50/%50 |
|---|---|---|---|---|
| a / b | 1 | 33,6 / 29,5 / 1,28; 2022: −19,8; 2024+: 28,7 / 19,2 / 1,31; tasfiye 0 | 55,2 / 18,1 / 1,86; 2022: +18,1; 2024+: 56,1 / 16,8 / 2,03; tasfiye 0 | 45,7 / 15,6 / 1,99; 2022: −2,2; 2024+: 43,1 / 10,3 / 2,20 |
| a | 1,5 | aynı (tasfiye 0) | 28,8 / 32,9 / 1,08; tasfiye 36 | 32,8 / 18,1 / 1,47 |
| a | 2 | aynı (tasfiye 0) | 14,1 / 41,4 / 0,62; tasfiye 80 | 24,9 / 25,6 / 1,16 |
| a | 3 | aynı (tasfiye 0) | −17,0 / 84,0 / −0,55; tasfiye 223 | 6,4 / 54,5 / 0,40 |
| a | 5 | aynı (tasfiye 0,3) | −38,3 / 97,3 / −1,70; tasfiye 542 | −8,4 / 76,9 / −0,29 |
| b | 1,5 | 48,8 / 41,0 / 1,32; 2022: −28,1 | 41,3 / 49,3 / 1,05 | 48,9 / 28,2 / 1,48 |
| b | 2 | 62,8 / 51,1 / 1,34; 2022: −35,6 | 19,4 / 67,6 / 0,60 | 45,6 / 47,4 / 1,15 |
| b | 3 | 87,4 / 66,7 / 1,36; 2022: −48,3 | −58,9 / 99,9 (iflas) | −4,2 / 92,9 / 0,21 |
| b | 5 | 123,2 / 85,1 / 1,36; 2022: −66,7; tasfiye 0,3 | iflas | 14,0 / 91,5 / 0,51 |
| **Yalnız KGT kaldıraçlı (b) + KMN 1x** | 1,5 | | | **54,7 / 20,5 / 1,95**; 2022: −7,3; 2024+: 50,7 / 14,2 / 2,12 |
| | 2 | | | **63,0 / 25,2 / 1,91**; 2022: −12,1; 2024+: 57,7 / 17,7 / 2,05 |
| | 3 | | | 77,9 / 35,1 / 1,84; 2022: −20,8; 2024+: 70,2 / 24,1 / 1,93 |

**Stop ve ters hareket dağılımı, güvenli en yüksek kaldıraç.** Güvenli kaldıraç = stopların ya da ters hareketlerin %95'inin tasfiye mesafesinin içinde kaldığı en yüksek L.

| | Medyan | %75 | %95 | %99 | Güvenli en yüksek L |
|---|---|---|---|---|---|
| KGT stop mesafesi (7.349 işlem) | %3,9 | %5,7 | %9,4 | %13,1 | ≈ 10x (test edilen en yüksek: 5x, tasfiye ≈ 0) |
| KMN: pozisyon başına tutma süresindeki en kötü ters hareket (23.440 pozisyon) | %12,6 | %23,7 | %48,6 | %86,6 | ≈ 2x (pratikte 1,5x'te bile zarar veriyor) |

**Duyarlılık (KMN):** Binance tasfiyeyi son işlem fiyatıyla değil, anlık iğneleri yumuşatan işaret fiyatıyla yapar. KMN tasfiyesi günlük kapanışla hesaplanınca (iyimser sınır), (a) senaryosunda 1,5x: 42,3 / 28,8 / 1,48; 2x: 35,8 / 28,4 / 1,31. Yine de 1x'in (55,2 / 18,1 / 1,86) belirgin altında. Gerçek sonuç iki hesabın arasında olur.

## Sonuç
- **KGT kaldıraca dayanıklı.** Stoplar dar: medyan %3,9, %95'i %9,4'ün içinde. 5x'e kadar tasfiye neredeyse yok. (a) senaryosunda yalnız teminat serbest kalır, sonuç değişmez. (b) senaryosunda getiri kaldıraçla büyür ve Sharpe 1,32–1,36'da sabit kalır, ama düşüş de büyür: 2x'te %51, 3x'te %67. Tek başına 1,5x'in üstü taşınamaz.
- **KMN'ye kaldıraç verilmemeli.** Stopu yok ve sepetteki coinlerin %5'i 14 günde %49'dan fazla ters gidiyor. 1,5x'te bile tasfiyeler getiriyi yarıya indiriyor (%55 → %29); 3x'te iflas.
- **En iyi düzen:** Kaldıraç yalnız KGT'ye, KMN 1x. KGT 1,5x + KMN 1x: yıllık %54,7, düşüş %20,5, Sharpe 1,95. KGT 2x + KMN 1x: %63,0 / %25,2 / 1,91. Kaldıraçsız birleşim %45,7 / %15,6 / 1,99. Sharpe neredeyse aynı kalıyor; ek getirinin bedeli 5–10 puan daha fazla düşüş.
- **Öneri:** Kaldıraç istenirse yalnız KGT'de, en fazla 2x, izole teminatla; KMN kaldıraçsız. Kağıt bot değiştirilmedi.
