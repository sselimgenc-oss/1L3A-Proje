# Kakushadze & Serur, "151 Trading Strategies" - envanter özeti

Kaynak: arXiv 1912.04492. Dikkat: bu arXiv numarası makalenin **İspanyolca baskısı** (398 s., 30 Mayıs 2019 sürümü; İngilizce 17 Ağustos 2018). Metin `veri/pdf_metin_2/kitap_diger/151_Trading_Strategies.txt` (gitignored, doğrulandı); PDF scratchpad'de, repoda yok.
Tablo: `kakushadze_151.csv` (173 satır = numaralı strateji ve alt varyantlar; bölüm 2-20). Kitap "151" der, ama alt varyantlar (3.9.1, 4.1.1, 5.8.1, 7.3.1 ...) ayrı satır sayıldığı için 173 çıkıyor.
Okuma derinliği: bölüm 3, 4, 6.5, 8, 9, 10, 18, 19 ana metinden satır satır okundu; bölüm 2, 5, 7, 11-17, 20 başlık + giriş düzeyinde (hepsi evren dışı/veri yok, kural ayrıntısı sonuç değiştirmez).

## Bölüm bazında sayı ve durum

| Bölüm | Konu | Sayı | Dağılım |
|---|---|---|---|
| 2 | Opsiyonlar | 56 | veri_yok 56 |
| 3 | Hisseler | 21 | mevcut 5, ayar 8, yeni 1, veri_yok 5, ml 2 |
| 4 | ETF'ler | 8 | mevcut 3, ayar 2, yeni 2, kapsam_disi 1 |
| 5 | Sabit getirili | 15 | kapsam_disi 14, veri_yok 1 (CDS bazı) |
| 6 | Endeksler | 5 | ayar 1, veri_yok 4 |
| 7 | Volatilite | 7 | veri_yok 7 |
| 8 | FX | 6 | yeni 1, veri_yok 5 |
| 9 | Emtia | 6 | mevcut 2, ayar 1, veri_yok 3 |
| 10 | Vadeliler | 7 | mevcut 1, ayar 1, veri_yok 2, kapsam_disi 3 |
| 11 | Yapılandırılmış | 6 | kapsam_disi 6 |
| 12 | Dönüştürülebilir | 2 | kapsam_disi 2 |
| 13 | Vergi arbitrajı | 3 | kapsam_disi 3 |
| 14 | Çeşitli (enflasyon, hava, enerji) | 4 | veri_yok 4 |
| 15 | Sıkıntılı varlık | 7 | kapsam_disi 5, veri_yok 2 |
| 16 | Gayrimenkul | 8 | kapsam_disi 8 |
| 17 | Nakit | 5 | yasak 1 (kara para), kapsam_disi 4 |
| 18 | Kripto | 2 | ml 2 |
| 19 | Küresel makro | 4 | yeni 1, veri_yok 2, kapsam_disi 1 |
| 20 | Altyapı | 1 | kapsam_disi 1 |
| **Toplam** | | **173** | veri_yok 91, kapsam_disi 48, ayar 13, mevcut 11, yeni 5, ml 4, yasak 1 |

Kullanılabilir (mevcut + ayar + yeni) = 29 satır. Gerisi veri/evren dışı.

## Kapsam dışı / veri yok bölümler ve nedeni

- **Bölüm 2 (56 opsiyon payoff'u), 7 (VIX, vol swap), 6.3 (dispersiyon):** opsiyon zinciri ve zımni oynaklık verisi yok. Ayrıca kitap bu stratejilerde sinyal kuralı vermiyor, yalnız payoff şeması anlatıyor.
- **Bölüm 5, 11, 12, 13, 14.2, 15, 19.4:** tahvil, CDS, CDO/MBS, dönüştürülebilir, vergi, sıkıntılı borç: evrenimizde yok.
- **Bölüm 16, 17, 20:** gayrimenkul, nakit/repo/rehin, altyapı: yatırım evreni dışı. 17.2 (kara para aklama) yasa dışı olduğu için `yasak`.
- **3.2, 3.3, 3.5, 3.16 (bilanço, opsiyon IV, M&A) ve 3.19 (market-making):** temel veri / emir defteri yok.
- **8.2-8.5 (FX carry), 9.1-9.2 (roll yield, COT), 10.2-10.3.1 (takvim spreadi, açık pozisyon):** faiz farkı, vade eğrisi, COT, açık pozisyon verisi yok. Kripto karşılığı (fonlama carry'si) zaten `dis__funding-carry` / `dis__ewmac-carry` ile var.
- **19.2-19.3 makro:** GDP/CPI/politika faizi verisi yok.
- **ml:** 3.17 (KNN), 3.20 (alfa kombinasyonu), 18.2 (ANN), 18.3 (duyarlılık/naive Bayes).

## Mevcut 1L3A ile eşleşenler (kod okunarak)

- 3.1 momentum, 3.4 düşük vol, 3.6 çok faktör, 3.7 kalıntı mom., 3.9/10.3 kesit dönüş, 4.2 alfa rotasyonu, 9.4/9.5 -> `pf__kesit_ls` (skorlar: getiri, risk_ayarli, artik, zirve, carpiklik, asimetri, beta, donus, kombine).
- 3.8 çiftler -> `pf__pairs`; 3.10 -> `pf__pca_statarb`; 4.1/4.1.1/4.6 -> `pf__rotasyon`; 4.1.2 -> `pf__gem`; 10.4 -> `pf__cta`/`dis__tsmom`; 6.5 -> `dis__voltarget-trend`; 9.3 -> `pf__sabit_sepet`.
- 3.11-3.15 (tek MA, iki MA, üç MA, pivot, Donchian) -> `dis__sma200-ls`, `swing__ma-kesisim`, `dis__ma-dizilim-5-10-30`, `swing__pivot-seviye`, `swing__donchian-kirilim`. Yani 151'in teknik kısmı zaten kodda var.
- awesome-systematic-trading ile örtüşenler (`github_g6_liste_notebook.csv`): 3.1, 3.3, 3.4, 3.7, 3.8, 3.9, 3.10, 4.1, 4.1.2, 6.2, 6.5, 8.2-8.4, 9.1, 9.5, 10.3, 10.3.1, 10.4, 12.1, 2.52 (not sütununda "g6 örtüşme"). Makalenin kendisi g6'da yalnız başlık olarak vardı (kural_yok); şimdi içi dolduruldu.

## Kodlanması önerilen `yeni` stratejiler

| Öncelik | Bölüm | Strateji | Neden / not |
|---|---|---|---|
| **A** | 4.4 | **Kesitsel IBS dönüşü (L/S)** | IBS=(C-L)/(H-L) önceki gün; evreni IBS'ye göre sırala, üst decil short, alt decil long, dolar-nötr, eşit veya 1/σ. Kural tam, yalnız OHLC. `pf__ibs_donus` sembol başına bağımsız long-only; bu kesitsel. `pf__kesit_ls`'e skor='ibs' olarak eklenebilir. 13 enstrümanlık evrende k küçük kalır, dikkat. |
| B | 3.9.1 | Grup-nötr ortalamaya dönüş | Sektör/küme içinde sapma; sektör etiketi elle yazılır. Evrende grup başına 3 hisse, çok ince. |
| B | 4.3 | R² seçicilik + alfa (5x5) | Faktör verisi yok, tek faktörle (SPX/BTC) vekil; kanıt fon verisinde, kriptoda belirsiz. |
| B | 8.1 | HP filtreli MA kesişimi | HP iki taraflı: nedensel (tek yönlü) sürüm şart, pahalı. Mevcut yumuşatılmış MA'lar (HMA/KAMA/Gauss) büyük ölçüde karşılar; kazanç düşük. |
| B | 19.5 | FOMC günü long, diğer günler nakit | Kural tam; FOMC tarihleri dışarıdan statik tablo gerekir. Yalnız ABD hisse/SPX. Takvim ailesine (maas-gunu vb.) eklenir. |

Küçük kod eklemeleri (yeni sınıf değil, `ayar` içine girmeyen ufak eksikler; karar sizde):
- `pf__kesit_ls`: ağırlık='orantili' (w=-γ·sapma, 3.9 ve 10.3 için), skor='dusuk_vol' (3.4 L/S), skor='ibs' (4.4).
- `pf__rotasyon`: ağırlık ∝ R/σ (4.6).

## Notlar

- Kitaptaki "strateji"lerin çoğu çerçeve düzeyinde; parametre ve çıkış kuralı yok (ör. 3.18, 3.20, 5.x). Bu yüzden `yeni` listesi kısa; kitabın değeri yeni sinyalden çok sınıflandırma.
- Test dönemi 2020 sonrası olduğundan 9.4/3.3 vekili (5 yıl geri dönüş) için 2015 öncesi veriye ihtiyaç var; Dukascopy/Binance geçmişi yeterli mi kontrol edilmeli.
- Karar 27 ile uyumlu: önerilenlerin hepsi evren stratejisi (tek parametre seti, çok enstrüman); tek sembol-strateji ikilisi önerilmedi.
