# brainbrick-trades long-only stratejileri — bizim yaklaşımla yeniden test

Kaynak: github.com/brainbrick-trades/Quant-Trading-Strategies (kullanıcının paylaştığı `strategies_long_only.py`).
Kod: `trend/` (`python -m trend.test`, `python -m trend.birlesim`). Ayrıntılı tablolar: `SONUCLAR_TREND.md`, `BIRLESIM.md`.

## Düzeltmeler
- **007 "12 ay trend":** orijinalde günlük koşul 52 gün (≈2,5 ay) idi → 252 gün (BTC 365).
- **İşlem zamanı:** sinyal t kapanışı, işlem t+1 **açılışı** (gece boşluğu eski pozisyonla, gün içi yeni pozisyonla).
- **Maliyet:** sınıf bazlı tek yön (BIST %0,15, kripto %0,10, diğer %0,05).
- **BIST ve XU endeksleri USD'ye çevrildi** (2020–26'da USD/TRY ×8,3).
- **Petrol −37,63 $ (2020-04-20)** ve sıfır/eksi fiyatlar atıldı.
- **Değerlendirme:** 2015–22 (IS) ve 2023–26 (OOS) ayrı; vol hedefi yalnız IS verisinden.

## Sonuç özeti
| Strateji | IS Sharpe | OOS Sharpe | Karar |
|---|---|---|---|
| BTC — T1 (haftalık EMA10/30 + günlük SMA50) | 1,30 | 1,12 | ✅ Al-tut ile benzer Sharpe, düşüş −%77 → −%34 |
| BTC — 037 SMA50 | 1,28 | 1,04 | ✅ (T1'e çok yakın) |
| ABD — 007P trend portföyü + rejim (S&P trendi) | 1,10 | 1,53 | ✅ Düşüş −%13 / −%8 |
| Emtia — 012 düşük volatilite | 1,09 | 1,35 | ✅ (vade geçişi düzeltilmemiş veri — dikkat) |
| ETH, XU100, XU030, S&P, Nasdaq, altın tek kural | – | – | ❌ al-tut'u geçmiyor (BIST USD'de ~0) |
| BIST portföyleri (USD) | 0,4–1,3 | 0,0–0,4 | ❌ OOS'ta dağılıyor; IS getirisi geriye dönük seçilmiş listeden |
| ABD 001/020 momentum | 0,6–0,95 | 1,3–1,4 | ⚠️ Bugünün kazananlarından oluşan liste → şişkin |
| Volatilite hedefleme | – | – | Düşüşü azaltır, getiriyi daha çok keser; BTC'de %12 hedef çok düşük |

Trend kurallarının işlem bazında kazanma oranı düşüktür (BTC SMA50 ~%27): az sayıda büyük kazanç, çok sayıda küçük
zarar. Bu yüzden %45 kazanma hedefine uymazlar; değerleri düşüşü azaltmak ve swing sistemine düşük korelasyon katmaktır.

## Geliştirme ve duyarlılık (`GELISTIRME.md`)
- **BTC trend:** SMA 40–100 arası tüm ayarlarda Sharpe IS 1,21–1,37 / OOS 0,78–1,18; 2× maliyette değişmiyor.
  Varsayılan SMA50 korundu (IS'te en iyi SMA40 idi, aşırı uyumdan kaçınmak için seçilmedi).
- **Kripto portföyüne genişletme (25 coin):** IS'te çok iyi (Sharpe 1,46) ama OOS'ta çöküyor (Sharpe 0,67,
  düşüş −%54) → **reddedildi**; yalnız BTC.
- **ABD trend portföyü:** 6/9/12 ay ve EMA10/30 / SMA200 rejimlerinin hepsinde IS ≥ 0,89, OOS ≥ 1,36;
  2× maliyette aynı; **Mag7 hariç tutulunca da** IS 1,00 / OOS 1,49 → hayatta kalma yanlılığına dayanıklı.
- **Emtia:** vadeli seriler yerine **ETF'ler** (GLD, SLV, USO, DBA, CORN …; vade geçişi maliyeti fiyatta).
  ETF düşük vol. 252g en düşük %20: IS 0,94 / OOS 1,23, düşüş −%17 / −%9 → seçildi.
- **Ay sonu hatası düzeltildi:** bitmemiş ay yeniden dengelemeye alınmıyor (yalnız son günleri etkiliyordu).

## Seçilen trend kolları (kağıt hesap 2)
| Kol | Kural |
|---|---|
| BTC trend | Haftalık EMA10 > EMA30 ve kapanış > EMA30 **ve** günlük kapanış > SMA50 → %100 BTC, değilse nakit |
| ABD trend portföyü | Ay sonu 12 aylık getirisi pozitif tüm hisseler eşit ağırlık; S&P 500 haftalık EMA10/30 aşağıysa nakit |
| Emtia ETF düşük vol. | Ay sonu 252 günlük volatilitesi en düşük %20 (≥3) ETF eşit ağırlık |

Kağıt hesap: `trend/kagit.py`, `.github/workflows/kagit-trend.yml` (günde 1 kez), durum dalı `kagit-trend-durum`,
rapor issue'su "Kağıt al-sat raporu (swing-sg trend kolları, 10.000 USD)". Swing kağıt hesabından bağımsızdır.

## Swing sistemiyle birleşim (günlük piyasa değeri, Sharpe yıllık 365 gün)
| Portföy | IS CAGR | IS maks. düşüş | IS Sharpe | OOS CAGR | OOS maks. düşüş | OOS Sharpe |
|---|---|---|---|---|---|---|
| Swing tek başına | %29 | −%12 | 1,75 | %27 | −%17 | 1,32 |
| Trend kolları (BTC + ABD + emtia ETF, eşit) | %30 | −%19 | 1,62 | %23 | −%7 | 1,79 |
| **%50 swing + %50 trend** | **%30** | **−%12** | **2,00** | **%25** | **−%11** | **1,70** |

Haftalık korelasyon: swing–BTC trend 0,37, swing–ABD trend 0,42, swing–emtia ETF 0,17.
%50/%50 birleşimde 12 yılın 11'i pozitif (en kötü 2018: −%4,2).
