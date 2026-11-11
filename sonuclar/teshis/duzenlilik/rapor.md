# Test D — Düzenlilik teşhisi (sade anlatım)

**Soru:** 'Düzenli işlem açan, istikrarlı strateji istiyorum.'
**Bu bir TEŞHİS:** yeni ayar/strateji aranmadı; canlı planı değiştirmez. Veri: v2 ham sonuçları, maliyet ×2, geliştirme dönemi (< 2025-11-08), tüm semboller birlikte. Ön kayıt: `sonuclar/teshis/ON_KAYIT_TESHIS.md`.

## Kısa cevap

- **10 stratejiden yalnız 1'i 'DÜZENLİ': ewo-ema-ofset** (ayda 13 işlem, işlemli ay %83, 9 yılın 9'u artı, en iyi %5 işlem çıkınca ΣR hâlâ +74R). 9'u DÜZENSİZ.
- En sık tutmayan şart: **'en iyi %5 işlem çıkınca ΣR > 0'** (8 strateji tutmadı): kâr az sayıda büyük işlemde toplanıyor. Bu trend takipçilerinin doğası (az kazanıp çok kazanma); 'düzenli akan gelir' beklentisiyle uyuşmuyor.
- Artı yıl şartını ewo (%100) ve e0v1en (%78) geçiyor; swing'lerin hepsi %33-61 ile geçemiyor.
- 'İstikrarlı' ile 'iyi trader tarifi' (Test C) birbirine zıt: Test C'de 'kayıp kısa/kâr uzun' çıkan stratejilerin hepsi burada DÜZENSİZ; Test C'de 'çok kazan az kazan' çıkan iki 15 dk strateji ise en düzenliler.

## Tablo

| Strateji | İşlem/ay (ort / medyan) | İşlemli ay % | Artı yıl | Artı ay % | En iyi %5 işlemin ΣR payı | En iyi %5 çıkınca ΣR | Etiket | Tutmayan şart |
|---|---|---|---|---|---|---|---|---|
| e0v1en | 24.7 / 9 | %94 | 7/9 (%78) | %69 | %161 | -63 | **DÜZENSİZ** | en iyi %5 çıkınca ΣR <= 0 |
| ewo-ema-ofset | 13.0 / 7 | %83 | 9/9 (%100) | %58 | %56 | +74 | **DÜZENLİ** | - |
| hma-atr-rider | 10.0 / 5 | %91 | 11/18 (%61) | %39 | %362 | -195 | **DÜZENSİZ** | artı yıl %61 < %70; en iyi %5 çıkınca ΣR <= 0 |
| lube | 0.9 / 0 | %39 | 8/16 (%50) | %20 | %94 | +8 | **DÜZENSİZ** | işlemli ay %39 < %80; artı yıl %50 < %70 |
| gauss-stoch-eth | 6.6 / 3 | %77 | 8/17 (%47) | %26 | %150 | -98 | **DÜZENSİZ** | işlemli ay %77 < %80; artı yıl %47 < %70; en iyi %5 çıkınca ΣR <= 0 |
| haftalik-macd-gunluk-ma | 3.0 / 2 | %70 | 6/18 (%33) | %21 | %194 | -89 | **DÜZENSİZ** | işlemli ay %70 < %80; artı yıl %33 < %70; en iyi %5 çıkınca ΣR <= 0 |
| uc-ortalama-boga-sma60 | 1.8 / 1 | %55 | 7/17 (%41) | %18 | %284 | -52 | **DÜZENSİZ** | işlemli ay %55 < %80; artı yıl %41 < %70; en iyi %5 çıkınca ΣR <= 0 |
| jt-awesome-osilator | 8.7 / 4 | %87 | 9/18 (%50) | %31 | %135 | -235 | **DÜZENSİZ** | artı yıl %50 < %70; en iyi %5 çıkınca ΣR <= 0 |
| voltarget-trend | 6.9 / 4 | %74 | 6/18 (%33) | %23 | %211 | -269 | **DÜZENSİZ** | işlemli ay %74 < %80; artı yıl %33 < %70; en iyi %5 çıkınca ΣR <= 0 |
| pf__sabit_sepet | 2.1 / 2 | %97 | 6/9 (%67) | %45 | %312 | -270 | **DÜZENSİZ** | artı yıl %67 < %70; en iyi %5 çıkınca ΣR <= 0 |

Etiket (ön kayıtlı): DÜZENLİ = işlemli ay ≥ %80 VE artı yıl ≥ %70 VE en iyi %5 işlem çıkınca kalan ΣR > 0. pf__sabit_sepet portföy: 'işlem' = dengeleme günü, ΣR yerine günlük getiri toplamı (yüzde puan), en iyi %5 = en iyi %5 GÜN.

## Diğer ölçüler

| Strateji | En uzun işlemsiz gün | En iyi 10 işlemin payı | ΣR toplam | En iyi sembol (çıkınca ΣR) | En uzun ardışık kayıp | En uzun düşüş (gün) | Veri sonu kapanışı |
|---|---|---|---|---|---|---|---|
| e0v1en | 69 | %24 | +104 | ADAUSDT (+82) | 15 | 1669 | 1 |
| ewo-ema-ofset | 115 | %13 | +169 | BNBUSDT (+147) | 17 | 784 | 0 |
| hma-atr-rider | 118 | %64 | +74 | ETHUSDT (+58) | 23 | 3240 | 2 |
| lube | 779 | %98 | +124 | ZECUSDT (+70) | 12 | 1363 | 7 |
| gauss-stoch-eth | 182 | %65 | +198 | ZECUSDT (+162) | 23 | 2754 | 8 |
| haftalik-macd-gunluk-ma | 217 | %131 | +95 | ZECUSDT (+22) | 22 | 2983 | 1 |
| uc-ortalama-boga-sma60 | 741 | %214 | +28 | BNBUSDT (+10) | 18 | 3246 | 0 |
| jt-awesome-osilator | 110 | %58 | +665 | BNBUSDT (+541) | 25 | 2857 | 13 |
| voltarget-trend | 309 | %75 | +242 | DK_LLY (+200) | 58 | 3534 | 17 |
| pf__sabit_sepet | 85 | %53 | +128 | - | - | 737 | 0 |

(Payın %100'ü aşması: en iyi işlemler toplamdan büyük, geri kalanı toplam olarak negatif demektir.)

## Yıl bazında ΣR (×2 maliyet; çıkış yılına göre; 2025 = 7 Kasım'a kadar)

| Strateji | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|
| e0v1en | +4 | +37 | +24 | +18 | +13 | -11 | +6 | -0 | +14 |
| ewo-ema-ofset | +25 | +9 | +13 | +46 | +15 | +19 | +14 | +27 | +1 |
| hma-atr-rider | +0 | -17 | +6 | +34 | +30 | -22 | +8 | +26 | +30 |
| lube | -0 | +3 | -2 | -9 | +23 | +4 | -8 | +26 | +85 |
| gauss-stoch-eth | -4 | -9 | -3 | +38 | +56 | -7 | -7 | +80 | +54 |
| haftalik-macd-gunluk-ma | -5 | -18 | -6 | +34 | -1 | -9 | -7 | +35 | +69 |
| uc-ortalama-boga-sma60 | -1 | -0 | -3 | +1 | +18 | -4 | +3 | +18 | -2 |
| jt-awesome-osilator | -3 | -8 | +30 | +102 | +309 | -72 | +43 | +182 | +105 |
| voltarget-trend | -20 | -3 | -14 | +43 | +54 | -8 | -7 | +145 | +72 |
| pf__sabit_sepet | +6 | -12 | +56 | +31 | +21 | -18 | +48 | +3 | -6 |

(Swing stratejileri hisse/emtia verisiyle 2008'e kadar uzanıyor; artı yıl sayısı o yıllar dahil tüm yıllar üzerinden. Tablo yalnız 2017+ gösterir.)

## Her strateji için 1-2 cümle

- **e0v1en:** İşlemli ay %94, 7/9 yıl artı; ama en iyi %5 işlem (124 işlem) çıkınca ΣR −63R: kâr az sayıda iyi işlemde; yıllar içinde yalnız 2022 belirgin eksi (−11R). 'Düzensiz' yalnız bu şart yüzünden.
- **ewo-ema-ofset:** Tek 'DÜZENLİ'. Her yıl artı (9/9), işlemli ay %83, en iyi %5 çıkınca +74R. En uzun işlemsiz süre 115 gün, en uzun düşüş 784 gün (swing'lerin 1.400-3.500 günlük düşüşlerinden çok kısa).
- **Not:** swing stratejilerinin kârı çoğunlukla 2020-21 ve 2024-25 gibi güçlü yıllarda; 2017-19 ve 2022 çoğunda eksi.
- **hma-atr-rider:** Ayda 10 işlem, işlemli ay %91; ama yılların %61'i artı ve kâr 107 en iyi işleme yüklü (en iyi %5 çıkınca −195R).
- **lube:** Ayda 0,9 işlem, işlemli ay %39, en uzun işlemsiz 779 gün: 'düzenli işlem açan' değil. Artı yıl %50.
- **gauss-stoch-eth:** Ayda 6,6 işlem ama işlemli ay %77 (sınırda), artı yıl %47; en iyi %5 çıkınca −98R; en uzun düşüş 7,5 yıl.
- **haftalik-macd-gunluk-ma:** İşlemli ay %70, artı yıl %33; en iyi 10 işlem toplam ΣR'nin %131'i.
- **uc-ortalama-boga-sma60:** En seyrek (ayda 1,8; işlemli ay %55, 741 gün işlemsiz), artı yıl %41; ΣR yalnız +28R ve en iyi 10 işlem %214.
- **jt-awesome-osilator:** İşlemli ay %87 (tutuyor), artı yıl %50; en iyi %5 çıkınca −235R. En büyük ΣR (+665) ama en iyi sembol (BNB) çıkınca +541R: yoğunlaşma yüksek, sembole bağlı değil işlemlere bağlı.
- **voltarget-trend:** İşlemli ay %74, artı yıl %33, 58 işlik kayıp serisi (en uzun), en iyi %5 çıkınca −269R.
- **pf__sabit_sepet (portföy):** İşlemli ay (dengeleme) %97, artı yıl %67 (eşiğin hemen altı), en iyi %5 GÜN çıkınca −270 puan; kill switch olayı çok (25). 'Düzenli' değil.

## Sınırlar

- ΣR 'R' biriminde ham toplamdır: aynı anda çok sembolde açılan işlemler birlikte toplanır; portföy getirisi veya sert risk limitleri uygulanmış getiri DEĞİLDİR (limitsiz ham).
- Aylık sayımlar GİRİŞ ayına, ΣR yıl/ay çıkış zamanına göre. Takvim aralığı ilk girişten 2025-10'a; 2025-11'in ilk 7 günü aylık ölçülerde yok, yıl ΣR'ye dahil. Veri sonunda zorunlu kapanan işlemler dahil (sayıları tabloda).
- Strateji başlangıçları farklı (kripto 2017-18, hisse/emtia swing 2008-10): yıl sayısı ve 'işlemli ay %' paydası buna göre değişir; stratejiler arası kıyas birebir değildir.
- Düşüş süresi kümülatif R (tüm semboller toplamı) zirvesinden; gerçek hesap düşüşü değil.

## Denetim notu

Betikler sentetik testlerle sınandı (ay/yıl/seri/düşüş/tarih sınırı); sonuç csv'leri ham verideki işlem sayılarıyla uyumlu (n_islem = ham satır sayıları toplamı). Test D'de sonuç sonrası değişiklik yok. (Ek-1: veri sonu zorunlu kapanış damgası kuralı, koşu başlamadan, ön kayıtta.)
