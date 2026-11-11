# Seçim meta-testi sonucu: SEÇİM ÇALIŞIYOR

- Karar etiketi: **SEÇİM ÇALIŞIYOR**
- D̄ (ort. fark, yüzdelik puan): **7.92**
- p_yukarı: **0.0464**   p_aşağı: **0.9541**  (2^11 = 2048 işaret çevirme)
- %90 GA (t, sd=10): **[0.17 ; 15.67]**

Kural (önceden yazıldı): D̄ ≥ +5 ve p_yukarı ≤ 0.10 → çalışıyor; D̄ ≤ −5 ve p_aşağı ≤ 0.10 → zararlı; aksi halde rastgeleden ayırt edilemiyor. Bu test strateji seçmez, seçim YÖNTEMİMİZİN rastgeleden iyi olup olmadığını ölçer.

## Pencere başına (ana karşılaştırma: S_k − N1)

| kesim | pencere sonu | uygun | kapı geçen | S_k n | P(S) | P(N1) | D_k | S ort ΣR | N1 ort ΣR |
|---|---|---|---|---|---|---|---|---|---|
| 2020-05-08 | 2020-11-07 | 180 | 16 | 10 | 55.64 | 61.56 | **-5.91** | 11.44 | 9.91 |
| 2020-11-08 | 2021-05-07 | 180 | 37 | 10 | 71.68 | 62.12 | **9.55** | 140.47 | 172.96 |
| 2021-05-08 | 2021-11-07 | 180 | 57 | 10 | 53.69 | 61.52 | **-7.83** | -14.79 | -79.09 |
| 2021-11-08 | 2022-05-07 | 191 | 72 | 10 | 44.63 | 51.85 | **-7.22** | -27.61 | -31.11 |
| 2022-05-08 | 2022-11-07 | 192 | 50 | 10 | 40.16 | 54.46 | **-14.30** | -21.22 | -17.43 |
| 2022-11-08 | 2023-05-07 | 192 | 47 | 10 | 70.05 | 58.28 | **11.78** | 3.77 | -11.17 |
| 2023-05-08 | 2023-11-07 | 192 | 37 | 10 | 84.55 | 61.97 | **22.59** | 20.74 | 5.52 |
| 2023-11-08 | 2024-05-07 | 193 | 36 | 10 | 89.79 | 67.47 | **22.32** | 64.80 | 41.00 |
| 2024-05-08 | 2024-11-07 | 193 | 57 | 10 | 69.22 | 55.44 | **13.77** | -3.46 | -16.41 |
| 2024-11-08 | 2025-05-07 | 193 | 49 | 10 | 88.49 | 64.04 | **24.45** | 64.58 | 19.87 |
| 2025-05-08 | 2025-11-07 | 193 | 59 | 10 | 76.25 | 58.34 | **17.91** | 25.89 | -5.13 |

D_k pozitif pencere sayısı: 7 / 11.

## Sadakat kontrolü (yalnız rapor)

T = 2025-11-08'de tam geliştirme verisiyle vekilin kapıları, gerçek `gecti` (18) satırlarıyla karşılaştırıldı.

- Vekil kapıyı geçen: 63; gerçek gecti: 18 (havuzda 16); örtüşen: **15**; Jaccard 0.23.
- Yalnız vekilde: dis__ao-ac-bolgeleri|1d, dis__ao-tabak|1d, dis__ay-donumu|1d, dis__ay-mevsimsellik|1d, dis__bant-kirilim-trend|1d, dis__codex-wd-cift-momentum|1d, dis__confluence-rank|1d, dis__ema-esik-trend|1d, dis__ewmac-carver|1d, dis__fraktal-alligator-sky|1d, dis__ft-highwave|1d, dis__gmma-ls|1d, dis__golden-trident|1d, dis__gosterge-rezonansi|1d, dis__hma-atr-rider|1d, dis__jt-awesome-osilator|1d, dis__kapanis-ma5|1d, dis__kelly-atr-bant|1d, dis__laguerre-rsi|1d, dis__ma-cift-cross|1d, dis__ma-dizilim-5-10-30|1d, dis__osilator-esik-birlesimi|1d, dis__rsi-ma-normal|1d, dis__rsi-t3-sqz|1d, dis__rsrs-egim-esigi|1d, dis__sma200-bant-trend|1d, dis__son1ay-donchian-adx|1d, dis__son1ay-kanal-20-10|1d, dis__sott|1d, dis__sst-dmi-50ma|1d, dis__stockbee-momentum-burst|1d, dis__trend-yargisi|1d, dis__uc-ortalama-boga-sma60|1d, dis__uclu-rsi|1d, dis__ust-tf-trend-60dk-donus|1d, dis__vixfix-stoch|1d, dis__voltarget-trend|1d, dis__voltran-1b|1d, dis__yeni-zirve-trend-filtresi|1d, dis__z65-rejim|1d, onceki__kapitulasyon|1d, onceki__s1-geri-cekilme|1d, swing__bb-sikisma-kirilim|1d, swing__bollinger-cift-bant-trend|1d, swing__donchian-kirilim|1d, swing__ma-geri-cekilme|1d, swing__ma-kesisim|1d, v2__trend-funding-suzgec|1d
- Yalnız gerçekte: dis__sma200-ls|1d, pf__cta|1d, pf__ref_filtreli_long|1d
- Spearman(puan, −p) vekil geçenler (n=63): 0.38; kesişimde (n=15): 0.05

## İkincil sonuçlar (ikincil, kararı değiştirmez)

- D̄ vs N2: 17.65; p_yukarı 0.0054; p_aşağı 0.9951; %90 GA [8.29 ; 27.01]
- D̄ vs N3: 7.93; p_yukarı 0.0405; p_aşağı 0.9600; %90 GA [0.67 ; 15.20]
- Sıra IC (geriye bakış puanı ↔ ölçüm puanı), ortalama 0.404; p_yukarı 0.0005; p_aşağı 1.0000
- İsabet (S ort ΣR > N1 medyanı): 8 / 11
- Strateji başı ort. ölçüm ΣR(×2) (pencereler ortalaması): S 24.05; N1 8.08; N2 -3.49; kapıyı geçen 23.87; kalan -12.63

Pencere içi rastgeleleştirme p_yukarı (N1'den aynı boyutta 10.000 çekiliş): 2020-05-08: 0.809, 2020-11-08: 0.059, 2021-05-08: 0.817, 2021-11-08: 0.837, 2022-05-08: 0.979, 2022-11-08: 0.051, 2023-05-08: 0.000, 2023-11-08: 0.000, 2024-05-08: 0.034, 2024-11-08: 0.000, 2025-05-08: 0.008

## Dayanıklılık koşulları (ikincil, kararı değiştirmez; ek örnek sayılmaz)

| koşul | pencere | D̄ | p_yukarı | p_aşağı | %90 GA | (kural etiketi, bilgi) |
|---|---|---|---|---|---|---|
| 12 aylık ufuk (5 pencere) | 5 | 9.81 | 0.1875 | 0.8438 | [-3.94 ; 23.55] | RASTGELEDEN AYIRT EDİLEMİYOR |
| 24 aylık kayan geriye bakış | 11 | 3.79 | 0.1240 | 0.8765 | [-1.80 ; 9.37] | RASTGELEDEN AYIRT EDİLEMİYOR |
| +3 ay kaydırılmış kesimler (10 pencere) | 10 | 11.58 | 0.0107 | 0.9902 | [3.94 ; 19.22] | SEÇİM ÇALIŞIYOR |
| ilk 5 | 11 | 7.49 | 0.0659 | 0.9346 | [-0.72 ; 15.71] | SEÇİM ÇALIŞIYOR |
| ilk 20 | 11 | 7.00 | 0.0278 | 0.9727 | [1.29 ; 12.71] | SEÇİM ÇALIŞIYOR |
| v1 havuzu (9 pencere, 2021-05-08'den) | 9 | 8.95 | 0.1484 | 0.8535 | [-6.32 ; 24.23] | RASTGELEDEN AYIRT EDİLEMİYOR |

## Yanlılık uyarıları (ön kayıttan)

- Evren 2026'da seçildi (hayatta kalan/seçilmiş strateji havuzu): sonradan bakıldığında zaten iyi görünenler var → yanlılık "seçim çalışıyor" yönünde.
- Kapılar (G1–G3 ve eşikleri) geliştirme verisi görüldükten SONRA tasarlandı → yine "çalışıyor" yönünde yanlılık.
- Yalnız 11 pencere var, güç düşük: "ayırt edilemiyor" kanıt eksikliğidir, "seçim işe yaramaz" kanıtı değildir. Olumsuz bulgu güvenilir, olumlu bulgu indirimle okunur.
- Stratejiler birbirine bağımlı; çıkarım birimi pencere (11 sayı). Strateji başı ya da pencere içi p karara girmez.

## Veri ve doğrulama

- Veri kökü: /home/user/1L3A-Proje/sonuclar/evren/v2; havuz: 197 strateji (eleme.csv hata dışı satır 216, dosyasız 19).
- kum_r = r doğrulaması: 803558 kapanan işlem, en büyük fark 0.00e+00 (fonlama_r ≠ 0 olan 345088 işlemde r'ye eklenirse uyuşmayan 345088: yani fonlama r'ye dahil).
- Kullanılan en büyük tarih: 2025-11-07 22:00:00+00:00 (< 2025-11-08 doğrulandı). Süzülen: 4800 işlem (çıkış ≥ 2025-11-08), 2400 mtm satırı.
- Betik sha256: 432ebfff77f39a304945caa52f7cd4cbd994314215c4c19dbba0c5c8677d083b; commit: 7213aeebf3c0b66092c35b2838419f53f1e15f59.

## Uygulama notları

1. ΣR(×2), PF(×1), kapanan işlem sayısı, en iyi enstrüman/yıl çıkarma: yalnız T_k'den ÖNCE KAPANAN (çıkış < T_k) işlemler, girişi analiz başlangıcından sonra olanlar (sıkı okuma, ileriye sızıntı yok). En iyi yıl = giriş yılı (UTC), eleme.py ile aynı.
2. G2 sayacı: x1 ve x2 kapanan işlem sayısının küçüğü (sıkı okuma). Geriye bakış yılı = (T_k − geriye bakış başı) gün / 365,25.
3. Günlük seri (puan, sd, pencere ΣR): mtm kum_r farkı, işlem+enstrüman toplamı, eksik gün = 0; analiz başlangıcından sonra girilen işlemler; T_k'den önce başlayıp sonra bitenlerin günlük artışları ilgili güne yazılır (takvim günü sayısıyla: geriye bakışta takvim günü, pencerede takvim günü). sd: ddof=1 (takvim günleri üzerinden).
4. Geriye bakış günlük sd'si 0 olan (hiç etkinlik yok) strateji 'uygun' sayılmaz (puan/ölçek tanımsız); N2 bu uygunlar üzerindedir.
5. P_i,k = (ortalama sıra − 1)/(n − 1) × 100 (0–100 aralığı; eşitlikte ortalama sıra). N2'ye karşı D_k bu yüzden = ort P(S_k) − 50.
6. Havuz: eleme.csv'de durum != hata VE ham x1, ham x2 ve mtm x2 dosyası olan satırlar. Portföy (pf__) satırlarının mtm dosyası yoktur; MTM serisi kurulamadığı için dışarıda (sıkı okuma). Bu yüzden havuz beklenen ~212'den küçüktür (bkz. ozet.json).
7. Yükleme süzgeci: çıkışı ≥ 2025-11-08 olan işlemler (veri sonunda zorla kapananlar) ve gün ≥ 2025-11-08 mtm satırları atılır; kum_r = r doğrulaması kalan (kapanan) işlemlerde yapılır. Atılan MTM satırlarının öncesindeki günlük artışlar pencerede kalır.
8. kum_r doğrulaması: son kum_r = net r (tol 1e-4) tüm kapanan işlemlerde sağlandı; fonlama_r ayrıca EKLENMEZ (r'ye zaten dahil).
9. N3: S_k etiket payları × o etiketin N1 ortalama P'si. N1 ve S_k'de aynı etiketler olduğundan boş tabaka olmaz (S_k ⊂ N1).
10. Sadakat: Spearman(puan, −p) için test.csv'deki `p` (geliştirme dönemi resmi test p'si) kullanıldı; eleme.csv'de gecti satırlarında p_ust boş. Yalnız vekil geçenler içinde p'si olanlar üzerinde; ayrıca vekil ∩ gerçek kümesinde.
11. Pencere içi rastgeleleştirme p: (sayı+1)/(10001) (sıkı); tek rng (tohum 20261111), kesim sırasıyla ana koşuda.
12. Dayanıklılık: 12 ay ufku = 5 pencere (T_0, T_2, …, T_8 = 2020-05 … 2024-05; kesin işaret çevirme 2^5=32). +3 ay kaydırma = T_0…T_9 + 3 ay (10 pencere; T_10+3 ay holdout'a taşar, atıldı). 24 ay kayan: geriye bakış = [max(analiz_bas, T−24 ay), T). v1: kabul==True işlem pnl'i (hesap kesri, R değil); günlük seri pnl'nin çıkış gününe toplamı; PF ve G1–G3 aynı pnl üzerinden; analiz başlangıcı = oos_bas; etiket yok (yalnız N1'e karşı); 9 pencere (2021-05-08…2025-05-08); v1 oos verisi 2025-09 civarında biter (sonraki günler 0).
13. secilenler.csv yalnız seçilenleri değil, her kesimde tüm uygun stratejileri (S bayrağıyla) içerir (kapılar/P/ölçüm için).
