# Üç PDF için derin strateji taraması

Tarih: 14 Ekim 2026

## Ana bulgu

Üç PDF aynı amaçla hazırlanmış görünse de listeler doğrudan sıralanabilir değildir:

- `codex.pdf` sayısal sonuç bulabildiği az sayıdaki örnek ile popülerlik listesini ayırıyor.
- `en-begenilen-100-strateji.pdf` popülerliği gösteriyor; birçok satırda test sonucu yok.
- `en_iyi_100_strateji.pdf` yazar beyanlarını puanlıyor; sembol, dönem, maliyet ve kaldıraç
  varsayımları farklı.

Performans listesindeki 100 kaydın en az 33'ü adında açıkça DCA veya grid taşıyor. Bu
modeller küçük ve sık kazançlarla yüksek kazanma/PF üretebilir; zarar kuyruğu, açık pozisyon
sermayesi ve tasfiye riski tabloya tam yansımadığı için üst sıralar yanıltıcıdır. Popülerlik de
kârlılık kanıtı değildir.

Bu nedenle öncelik sırası şu şekilde kuruldu:

1. Maliyet sonrası toplam ve dönem-dışı net kâr.
2. Farklı rejimlerde/varlıklarda pozitif kalma.
3. Düşüşe göre getiri (Calmar) ve iki kat maliyet stresi.
4. İşlem sayısı ve test döneminin uzunluğu.
5. PF, Sharpe ve kazanma oranı; yardımcı göstergedir, tek başına veto değildir.
6. Kuralların yeniden üretilebilir olması.

## A grubu — önce doğrulanacak adaylar

| Aday | PDF beyanı | Güçlü taraf | Ana risk | Durum |
|---|---:|---|---|---|
| Mean Reversion Setup LliterH | 1.232 işlem, %73,05 kazanma, PF 2,10, DD %14,82 | S&P, Nasdaq ve altın; 2006–2026 | Net getiri ayrıntısı ve tam kurallar eksik | Kaynak kuralı bekliyor; kanal modeliyle aile testi var |
| Compression Breakout System | AAPL PF 4,33, DD %14,4; ayrık dönem ve NVDA/MSFT | Uzun dönem ve çapraz hisse örneği | Aşırı iyi AAPL sonucu seçim yanlı olabilir | Codex uyarlaması hazır |
| Channel Reversion System | QQQ PF 2,28/DD %15,2; SPY PF 1,80/DD %8,5 | 1999–2026 dönemi | Yalnız 58 QQQ işlemi | Codex uyarlaması hazır |
| ETH Momentum Breakout | PF 3,08, DD %14, getiri %197 | Getiri/zarar dengesi güçlü | Yaklaşık yılda 12 işlem; tam kural eksik | Kaynak kuralı bulunmadan uygulanmayacak |
| Silver Risk Management | PF 3,70, DD %16, getiri %326 | Emtia çeşitlendirmesi | Yalnız 37 işlem | Kaynak kuralı bulunmadan uygulanmayacak |
| AO/AC Trading Zones | 278 işlem, PF 2,20, DD %5,4 | İşlem sayısı ve düşük düşüş | Yalnız BTC ve yaklaşık iki yıl | Standart-formül uyarlaması hazır |
| KST Strategy | 120 işlem, PF 1,75, DD %9,1 | Dengeli metrikler | Yalnız BTC 1 saat ve kısa dönem | Codex uyarlaması arşiv genişliğinde elendi |
| NORN WEAVE / FEHU | 557 işlem, PF 1,80, DD %1,71 | Büyük örneklem | Düşüş olağandışı düşük; kaynak/hesap denetlenmeli | İzleme listesi |
| Triple CCI + MFI | 108 işlem, PF 2,01, DD %7,8 | Basit göstergeler | Yalnız BTC 2 saat | Codex uyarlaması genişlikte zayıf |
| Double CCI + HMA | 104 işlem, PF 2,31, DD %9,6 | PF ve düşüş dengeli | Yalnız BTC; yazar beyanı | Üç hissede güçlü, genişlikte zayıf |
| Fractal Breakout | 83 işlem, PF 1,95, DD %8,3 | Basit trend ailesi | Örnek sayısı sınırlı | Codex uyarlaması hazır |
| MACD + SMA200 | Çok uzun endeks testlerinde PF 6,4/10,8 iddiası | Çok popüler ve kural adı şeffaf | İddialar olağanüstü; maliyet bilgisi yok | Ayrı Codex uyarlaması hazır |

## B grubu — potansiyelli fakat özel veri/zamanlama isteyenler

- 15 Min ORB MNQ: %71 kazanma, PF 1,62, DD %11,3. Vadeli seans saatleri ve gerçekçi
  slipaj olmadan test edilmemeli.
- Gold Breakout 15M: yaklaşık 4.000 işlem ve DD %14, fakat PF yaklaşık 1,27; küçük bir
  modelleme hatası veya maliyet artışı avantajı silebilir.
- Gold NY ORB: %73 kazanma yalnız eğitim kümesinden; dönem bilgisi yok.
- ICT Sessions & Liquidity Sweeps: NQ/MNQ PF 2,18/2,01 fakat 53/126 işlem ve seans/veri
  ayrıntısı gerekir.
- ATR-RSI no-repaint: Sharpe 1,40 ve 116 işlem; net kâr/PF/düşüş eksik.
- MACD + günlük Stochastic: 123 işlem, PF 1,62, DD %5,5; PDF'de net getiri rakamı kendi
  içinde tutarsız.
- SMC Pro BTC: PF 1,95/DD %1,36 görünen agresif sonuç 90 işlem; seçici mod yalnız 29
  işlem. Modlar birbirine karıştırılmamalı.
- BIST30→S&P ATR Momentum Rider: dönem-dışı vadeli medyan PF 3,46 ilginç; BIST stres
  testi medyan PF 0,77 ve komisyon yok. BIST için doğrudan aday değildir.

## C grubu — ilk turda elenenler

- Bütün DCA, grid ve martingale modelleri: sermaye kuyruğu ve açık pozisyon riski.
- Mutanabby ONEUSDT: DD %51,1 ve tek altcoin bağımlılığı.
- Vol-Target TQQQ: %41,9 düşüş ve kaldıraçlı ürün bağımlılığı.
- RSI-Gauss-Velocity ve Flawless Victory ML: olağanüstü optimize/in-sample iddialar.
- Strict SMC+ORB ve Drop's ORB: yalnız 30–54 günlük veya 19 işlemlik örnek.
- BTC MTF Engulfing/Pyramid: 2x kaldıraç, 73–74 işlem, yaklaşık %20 düşüş ve aşırı
  bileşik getiri; optimizasyon riski yüksek.
- BTC 10 saniye mean reversion: yalnız bir haftalık test.
- XAUUSD 10 dakika: DD %56,3.
- Gap Filling: yüksek kazanma oranına rağmen AMD/NVDA/Seagate örneklerinin net sonucu
  negatif; kazanma oranının neden tek başına kullanılmadığını gösteriyor.
- Trendline Fibonacci Supertrend: yayın güncellemeleri arasında PF/Sharpe çelişkisi.
- XGBoost Mini: 2018–2026 toplam getiri yalnız %20,1; karmaşıklığına göre avantaj zayıf.
- Şablon/araç betikleri ve yalnız popülerliği bulunan, kural/sonuç vermeyen kayıtlar.

## Kârlılık merkezli kabul kuralı

Bir model düşük Sharpe veya düşük kazanma oranıyla yine de kabul edilebilir. İlk paper
adaylığı için gerekenler:

- En az 15 kapanan işlem; 30 altı sonuçta düşük güven etiketi.
- Tam dönem ve son %30 dönem-dışı net sonuç pozitif.
- İki kat işlem maliyetinde net sonuç ve PF pozitif; PF en az 1,00.
- Normal maliyette PF en az 1,05 ve maksimum düşüş %35'i aşmıyor.
- Test edilen enstrümanların en az %60'ında ve maliyet streslerinin en az %60'ında sonuç
  pozitif.

Sharpe, kazanma oranı ve yazar puanı sıralamada gösterilir; yukarıdaki kârlılık ve dayanıklılık
koşulları geçiliyorsa tek başlarına eleme yapmazlar.

## Henüz doğrulanmayan nokta

TradingView/Pine kaynak uç noktası ve piyasa veri alanları çalışan ortamda proxy 403 dönüyor.
Bu nedenle PDF beyanları gerçek sonuç gibi panoya yazılmadı. Gerçek veri erişimi açılınca dokuz
şeffaf Codex modeli tüm piyasa matrisinde çalıştırılacak; yalnız `paper_eligible=true` olanlar
ortak 10.000 USD ileri teste alınacaktır.
