# Canlı boyut yeniden oynatma raporu (165 USD strateji hesabı)

> **GEÇMİŞ SİMÜLASYON, GELECEK TAHMİNİ DEĞİL.** v2 geliştirme dönemi (en geç 2025-11-07; holdout okunmadı) işlem listeleri, yeni canlı risk kuralıyla
> (`CANLI_LIMITLER`, karar 2026-11-11) yeniden oynatıldı. Strateji ya da parametre araştırması yok; mevcut backtest makinesi (varsayılan ayar, v2 maliyet tablosu ×1,
> funding dahil) kullanıldı. Her strateji **kendi** 165 USD hesabında tek başına oynatıldı (strateji arası etkileşim ve hesap -%20 kill'i bu tabloda yok).
> Tablo: `sonuclar/canli/boyut_yeniden_oynatma.csv`; kod: `araclar/canli_boyut_yeniden_oynat.py`.

## Kural (özet)
İşlem başı stopta kayıp (maliyet dahil) ≤ kasanın %3'ü; marj ≤ %50, nominal ≤ 1.5x; toplam açık stop riski ≤ %6, brüt ≤ 1.5x; günlük -%6 = o gün yeni giriş yok;
zirve kasadan -%30 = strateji durur; stop ≤ %15 ise 3x, üstü 2x izole kaldıraç. Kasa = min(özsermaye, 165). Miktar borsa minimumunun altında kalırsa işlem **atlanır**.

## Sonuç tablosu (yeni kural, 165 USD)
Strateji sayısı: 9 oynatıldı; `pf__sabit_sepet` **oynatılamadı** (portföy/hedef-ağırlık stratejisi: işlem başına stop yok, canlı yürütücü zaten reddediyor).

| Strateji | Alınan / toplam sinyal | Min tutar nedeniyle atlanan | Son özsermaye (USD) | Yıllık getiri (CAGR) | Maks. düşüş | En kötü gün | En uzun kayıp serisi (işlem) | Kill -%30 | Tavan bağlayan: nominal / risk |
|---|---|---|---|---|---|---|---|---|---|
| dis__gauss-stoch-eth | 379 / 1336 | 737 | 274 | %3.1 | %-31.1 | %-9.5 | 19 | hayır | %0 / %100 |
| dis__ewo-ema-ofset | 730 / 1287 | 527 | 682 | %18.9 | %-19.2 | %-6.4 | 6 | hayır | %3 / %97 |
| dis__jt-awesome-osilator | 193 / 1851 | 126 | 115 | %-2.0 | %-52.3 | %-6.2 | 20 | evet, 2018-05-03 | %5 / %95 |
| dis__uc-ortalama-boga-sma60 | 248 / 367 | 83 | 195 | %1.0 | %-31.4 | %-8.3 | 13 | hayır | %0 / %100 |
| dis__lube | 83 / 175 | 78 | 324 | %4.5 | %-20.9 | %-7.3 | 7 | hayır | %2 / %98 |
| dis__hma-atr-rider | 682 / 2124 | 1206 | 237 | %2.1 | %-42.9 | %-6.2 | 12 | hayır | %2 / %98 |
| dis__voltarget-trend | 244 / 1421 | 435 | 115 | %-2.1 | %-55.3 | %-7.8 | 33 | evet, 2022-04-22 | %11 / %89 |
| dis__haftalik-macd-gunluk-ma | 306 / 618 | 291 | 536 | %7.2 | %-39.1 | %-6.0 | 13 | hayır | %2 / %98 |
| dis__e0v1en | 1935 / 2461 | 513 | 750 | %20.2 | %-28.2 | %-8.8 | 10 | hayır | %0 / %100 |

Toplam: 11640 sinyalin 3996 tanesi (34%) min tutar nedeniyle atlandı. "Tavan bağlayan": alınan işlemlerde miktarı sınırlayan kural; nominal (1.5x / marj / brüt) mi, yoksa risk (%3 kayıp / %6 toplam risk) mi.
Yaklaşık tüm işlemlerde **risk tavanı** bağlar (stoplar çoğunlukla fiyatın %1'inden uzak); nominal tavanı yalnız çok dar stoplarda devreye girer.

## %1 boyutla (eski kural) karşılaştırma — aynı işlemler, aynı 165 USD
Eski: işlem başı %1 (maliyet dahil), toplam stop riski %5, brüt 3x, günlük -%3, kill -%20. (Paper seti fiilen %0.5 ile koşuyor; burada %1 ile kıyaslandı.) Hücreler "eski → yeni".

| Strateji | Son özsermaye (USD) | CAGR | Maks. düşüş | En kötü gün | Kill tetiklendi |
|---|---|---|---|---|---|
| dis__gauss-stoch-eth | 225 → 274 | %1.8 → %3.1 | %-15.2 → %-31.1 | %-3.9 → %-9.5 | hayır → hayır |
| dis__ewo-ema-ofset | 395 → 682 | %11.2 → %18.9 | %-12.2 → %-19.2 | %-5.7 → %-6.4 | hayır → hayır |
| dis__jt-awesome-osilator | 131 → 115 | %-1.3 → %-2.0 | %-31.4 → %-52.3 | %-4.1 → %-6.2 | evet → evet |
| dis__uc-ortalama-boga-sma60 | 196 → 195 | %1.0 → %1.0 | %-17.4 → %-31.4 | %-6.4 → %-8.3 | hayır → hayır |
| dis__lube | 370 → 324 | %5.4 → %4.5 | %-11.7 → %-20.9 | %-5.0 → %-7.3 | hayır → hayır |
| dis__hma-atr-rider | 178 → 237 | %0.4 → %2.1 | %-25.3 → %-42.9 | %-3.0 → %-6.2 | hayır → hayır |
| dis__voltarget-trend | 131 → 115 | %-1.4 → %-2.1 | %-33.2 → %-55.3 | %-3.2 → %-7.8 | evet → evet |
| dis__haftalik-macd-gunluk-ma | 324 → 536 | %4.1 → %7.2 | %-17.6 → %-39.1 | %-3.3 → %-6.0 | hayır → hayır |
| dis__e0v1en | 395 → 750 | %11.2 → %20.2 | %-11.5 → %-28.2 | %-4.5 → %-8.8 | hayır → hayır |

## Okuma (sade)
- Yeni kural riski yaklaşık 3 kat artırır: getiri de, **düşüş de** büyür. Maks. düşüşler yeni kuralda belirgin biçimde daha derindir (çoğunda %20-55 arası); en kötü gün çoğunlukla -%6 civarı ve bazen onun altına iner, çünkü günlük blok yalnız YENİ girişi durdurur, açık pozisyonların günlük dalgalanmasını durdurmaz.
- İki strateji (`dis__jt-awesome-osilator`, `dis__voltarget-trend`) geçmişte -%30 strateji kill'ine çarpardı (eski %1/-%20 kuralında da kill olurlardı); kill sonrası işlemler yapılmaz, hesap kalıcı durur.
- 165 USD gibi küçük bir kasada borsa minimum tutarı baskındır: özellikle BTC (100 USD) ve ETH (20 USD) işlemleri atlanır. Yeni kuralda atlanan işlem sayısı çoğu stratejide eskisinden DAHA fazladır, çünkü işlem başı %3 ile toplam %6 bütçesi yalnız iki pozisyonda dolar; aynı anda gelen sonraki sinyallere kalan bütçe küçük kalır, miktar aşağı yuvarlanınca min tutarın altına düşer ve işlem atlanır (yukarı yuvarlanmaz). Tek başına (eşzamanlı pozisyon yokken) yeni kural daha az atlar. Atlanan işlem kâr da zarar da getirmez.
- Stop mesafesi %25'ten uzak sinyaller her iki kuralda da atlanır (özellikle `gauss-stoch-eth`, `hma-atr-rider`).

## Varsayımlar ve sınırlar (dürüstçe)
1. **Min tutar tablosu (tutucu varsayım):** BTCUSDT 100 USDT, ETHUSDT 20 USDT, diğer tüm semboller 5 USDT. Gerçek borsa filtreleri (adım/minQty, DK_ tradfi perp'leri) farklı olabilir; adım (stepSize) yuvarlaması modellenmedi.
2. K/Z = backtest R'si × yeni miktar × stop mesafesi; maliyet (komisyon, kayma, funding) notional ile orantılı ölçeklenir. Kısmi çıkışlar, stop yükseltmesi ve gerçek dolum farkı modellenmedi; stop riski girişteki stopla ölçüldü.
3. Günlük blok ve kill, **gün sonu** MTM özsermayesiyle kontrol edilir (gün içi tetik yakalanamaz; gerçekte daha erken tetiklenebilir). Canlı yürütücü de günlük limitte yalnız yeni girişi durdurur (açık pozisyonlar kapatılmaz; karar 2026-11-11), simülasyonla aynıdır.
4. Kasa = min(özsermaye, 165): kâr kasayı büyütmez. Son özsermaye/CAGR bu yüzden bileşik getiri değildir.
5. Her strateji tek başına; gerçekte aynı anda birden çok canlı strateji varsa hesap kill'i (-%20 toplam) ayrıca devreye girer.
6. Sonuçlar geliştirme dönemidir (seçilmiş set; "iyi_gorundu" etiketli kısmı sonuç sonrası keşif). Geçmişin tekrarlanacağına dair bir iddia yoktur.
