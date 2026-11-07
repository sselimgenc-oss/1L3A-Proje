# PDF strateji incelemesi ve ilk adaylar

Tarih: 14 Ekim 2026

Bu çalışma `codex.pdf`, `en-begenilen-100-strateji.pdf` ve
`en_iyi_100_strateji.pdf` içindeki adayları bağımsız bir araştırma havuzu olarak ele alır.
PDF'lerdeki performans rakamları strateji yazarlarının beyanıdır; yeniden üretilebildikleri
kanıtlanana kadar doğrulanmış kabul edilmez.

## Kesin dışlananlar

Claude'un seçip test ettiği şu üç strateji bu kod tabanında uygulanmaz ve backtest/paper
matrisine girmez:

- Hybrid Breakout (`hezSShJr`)
- Squeeze Momentum (`G40dtEbK`, LazyBear)
- MACD ReLoaded (`VO6DY8s1`)

DCA, grid ve martingale adayları da yüksek görünen kazanma oranlarının kuyruk riskini ve
sermaye ihtiyacını gizlemesi nedeniyle ilk havuzdan çıkarılmıştır. Kapalı kaynak, makine
öğrenmesi iddiası doğrulanamayan ve yalnız çok kısa dönem sonucu bulunan betikler seçilmemiştir.

## İlk bağımsız adaylar

### 1. Sıkışma Kırılımı — Codex

PDF kaynağı: Compression Breakout System (`97gxVA5b`). PDF'de AAPL günlük 2005–2026
için PF 4,33, %59 kazanma ve %14,4 düşüş; ayrıca ayrık dönemler ile NVDA/MSFT örnekleri
bildiriliyor. Özgün Pine kaynağı bu ortamda doğrulanamadığı için birebir kopya değildir.

Uygulanan kural: EMA50 > EMA200, fiyat EMA50 üstünde; Bollinger bant genişliği son 120
barın alt %20'sine son 10 bar içinde girmiş; fiyat önceki 20 bar tepesini ortalama üstü
hacimle kırmışsa uzun. EMA20 veya önceki 10 bar dibi altına geçince nakit.

### 2. Kanal Ortalamaya Dönüş — Codex

PDF kaynağı: Channel Reversion System (`XRZCjbFr`). PDF'de QQQ günlük 1999–2026 için
PF 2,28, %64 kazanma ve %15,2 düşüş; SPY için PF 1,80 ve %8,5 düşüş bildiriliyor.

Uygulanan kural: fiyat EMA200 üstündeyken alt Bollinger bandının altına iner ve RSI(2)<10
olursa uzun. Orta banda dönüş, RSI(2)>70 veya EMA200 rejim kaybında nakit.

### 3. SuperTrend Rejim — Codex

PDF kaynağı: SuperTrend Regime Confluence (`mpjNqADq`). Yazarın BTC 4 saatlik örneğinde
PF 1,80 ve 168 işlem verilse de %24,55 düşüş, proje eşiği olan %20'yi aşıyor. Bu nedenle
yalnız araştırma adayıdır.

Uygulanan kural: SuperTrend(10, 3) pozitif ve EMA50 > EMA200 iken uzun; rejim veya trend
filtresi bozulduğunda nakit. Kaldıraç ve short kullanılmaz.

### 4. Fraktal Kırılım — Codex

PDF kaynağı: Fractal Breakout Trend Following (`IqUET4xO`). PDF'de BTC 4 saatlik örnekte
PF 1,95, %8,3 düşüş ve 83 işlem bildiriliyor; örnek sayısı sınırlıdır.

Uygulanan kural: fiyat önceki 20 bar tepesini kırar, EMA50 > EMA200 ve fiyat EMA100
üstündedir. Önceki 10 bar dibi veya EMA50 altına geçince nakit. Aşırı oynak barlar elenir.

### 5. MACD + SMA200 — Codex

PDF kaynağı: MACD + SMA 200 Strategy (`yMCa3XZD`). Popülerlik listesinde 31,6 bin
beğeniye sahip. SPX500 ve Dow için çok uzun dönemli, olağanüstü yüksek PF iddiaları var;
bu değerlerin maliyet ve piyasa yapısı değişimleriyle bağımsız doğrulanması gerekir. Bu model
Claude'un test ettiği MACD ReLoaded değildir.

Uygulanan kural: fiyat SMA200 üstündeyken MACD(12,26) sinyal(9) çizgisini yukarı keserse
uzun; aşağı kesişimde veya SMA200 rejim kaybında nakit.

### 6. AO/AC Bölgeleri — Codex

PDF kaynağı: AO/AC Trading Zones Strategy (`Tkrjao7P`). PDF'de BTC 4 saatlik 2023–2024
örneğinde 278 işlem, PF 2,20, %39,57 kazanma ve %5,4 düşüş bildiriliyor. Düşük kazanma
oranının tek başına sorun olmadığı; kazanç/zarar büyüklüğünün daha önemli olabileceği iyi
bir örnektir.

Uygulanan kural: standart Awesome Oscillator ve Accelerator Oscillator birlikte pozitif ve
AO yükseliyorsa uzun; göstergelerden biri negatife dönünce nakit.

### 7. KST Momentum — Codex

PDF kaynağı: KST Strategy. Standart Pring KST bileşimi ve EMA200 rejimi kullanılır. KST
sinyal çizgisini pozitif bölgede yukarı kesince uzun, aşağı kesişimde veya rejim kaybında
nakit olur. Arşiv genişliğinde medyan PF 0,95 ve pozitif pay %45,8 olduğu için mevcut
uyarlama ilerletilmez.

### 8. Triple CCI + MFI — Codex

PDF kaynağı: Triple CCI + MFI Strategy. CCI(20/40/80) pozitif ve MFI(14)>55 iken uzun;
kısa/orta CCI birlikte negatif veya MFI<45 olduğunda nakit. 483 hissede pozitif pay %54,7,
maliyet stresi pozitif payı %50,3 olduğu için yalnız canlı doğrulama izleme adayıdır.

### 9. Double CCI + HMA — Codex

PDF kaynağı: Double CCI + HMA Strategy. CCI(20/50) pozitif, fiyat HMA55 üstünde ve HMA
yükselirken uzun; iki CCI negatif veya fiyat HMA altındaysa nakit. AAPL/MSFT/NVDA testinde
güçlü görünmüş, fakat 483 hissede stres pozitif payı %47,8'e düşmüştür; doğrudan paper'a
geçmez.

## Test disiplini

- Günlük, kaldıraçsız, uzun/nakit model.
- Sinyal bar kapanışında; pozisyon sonraki bar açılışında.
- Piyasa bazlı komisyon ve kayma her pozisyon değişiminde uygulanır.
- İlk %70 eğitim, son %30 dönem-dışı testtir.
- Maliyet iki kat stres testi ayrıca çalışır.
- Kârlılık geçişi: en az 15 kapanan işlem, toplam ve dönem-dışı net kâr pozitif,
  PF >= 1,05, düşüş <= %35 ve iki kat maliyette sonuç/PF pozitif olmalıdır.
- Eski katı eşikler ayrıca raporlanır fakat düşük Sharpe veya düşük kazanma oranı tek başına
  eleme nedeni değildir.
- Bir stratejinin enstrümanların en az %60'ında kârlı olması genişlik kontrolüdür.
- Aynı dönem al-tut getirisi ayrıca raporlanır; mutlak kârlılık ile piyasa üstünlüğü
  birbirinden ayrılır.

Bu eşikler paper teste alınan modelin iyi olduğunu kanıtlamaz; yalnız araştırma önceliğini
belirler. Gerçek para emri bu sistemin kapsamı dışındadır.

