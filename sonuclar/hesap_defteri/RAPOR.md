# Hesap defteri — getirilen tüm stratejilerin akıbeti

_2026-11-13. Yalnız okuma; test koşulmadı, kod değişmedi. Sayılar `betikler/` altındaki betiklerle hesaplandı._

## Kullanıcıya özet

1. **520 kaynak dosya** (199'i strateji listesi), **8941 ham satır**, tekilleştirme sonrası **6223 tekil strateji** (521 kodlu + 16 kodlu ama koşulmamış ek ayar + 5686 kodlanmamış).
2. Geçen (A): **10** (2 canlı kadro, 8 paper — bunlar holdout 'keşif yolu', kanıt değil). Elenen (B): **485**. Kodlu ama hiç koşulmamış (C): **42** (26 strateji + 16 ek ayar; kaynak satırına bağlanmayan 2 ek ayar daha koşulmadı).
3. Kodlanmadı, nedeni yazılı (D): **3824** — bunun 2174'i "benzeri var" denip **fark hiç test edilmemiş** olanlar.
4. **Kodlanmadı, hiçbir dosyada akıbeti yok (E): 161** — çoğu RoboticAutomations (96), 906 dış liste (29) ve TV kuyruğu (29).
5. Yasak tip (F): 304 · ML (G): 526 · bizim evrende uygulanamaz (H): 836 · belirsiz: 35.
6. Elenen 485'in yalnız **270'i adil testte** elendi; 215'i son testte tek TF / sabit ayar / yapısal kapı / kısa veri ile elendi.
7. v2'de kârlılığı (E1) ve yoğunlaşmayı (E3) geçip yalnız yapısal kapıdan (E2 örnek / E4 genişlik / E5 kill) düşen: **73** (6'sı sonradan keşif yoluyla paper'da).
8. Belgelerdeki "~460 test edildi" sayısı v1 evren testindeki tek-grafik sayısıyla tutuyor (460); ama bugün kodda 492 tek-grafik + 29 portföy var, test edilen kodlu strateji 495.
9. `ayarlar_d11j_ek.json` (11) ve `ayarlar_d12b_ek.json` (7) **hiçbir araştırma kodunca okunmuyor**: 18 ek ayar kodlandı ama hiç koşulmadı.
10. Öz denetim: 40 rastgele tekil satır (tohum 20261113) → **3 hata (%7.5)**; hataların hepsi doğrulanmamış "benzer" eşlemelerinde.
11. Emin olmadıklarım: 909 "benzer" eşlemesi kodla karşılaştırılmadı (kaynak/önceki ajan kararı); kaynaklar arası tekilleştirme yalnız açık kanıtla yapıldı → tekil sayısı üst sınır (URL'si aynı 60 grupta en çok 113 tekil daha birleşebilir).

## 1. Kaynaklar ve sayım

| Grup | Kapsam | Ham satır |
|---|---|---|
| G10_ARSIV | Eski projeler (arsiv/), haiku dalları | 105 |
| G1_KITAP | Kitap/PDF kartları (137 dosya, 810 kart) | 810 |
| G2_DIS_ESKI | dis_envanter (TV/freqtrade/kural), portföy adayları, eski TV meta | 758 |
| G3_REPO | repo_kodlari, repo_raporlari, ek_77, sg-arge Excel/md listeleri | 1446 |
| G4_GITHUB | 50 GitHub reposu (g1..g7) | 1198 |
| G5_151_SON1AY | Kakushadze 151 + son 1 ay | 189 |
| G6_V3 | v3 aday katalogları (17 dosya) + dal ekleri | 2603 |
| G8_DIS_ARASTIRMA | Dış ajan 906 liste + ajan2 (dal) | 923 |
| G9_ROBOTIC | RoboticAutomations 909 Freqtrade (dal) | 909 |
| **Toplam** | | **8941** |

Her grubun kaynak satırı = ham satır sayısı denetlendi (`ara/<GRUP>_NOTLAR.md`). Eşleme dağılımı: YOK 4149, BENZER 2328, TEKRAR 1279, KOD 615, AYAR 488, ESDEGER 82.
TEKRAR = aynı stratejinin başka ham satırı (ör. iki Excel sürümü, `b_duzeyi` ⊂ `tumu` kataloglar: 837 satır lider betiğiyle bağlandı).

**Not:** 906 liste, derin geçiş, tur 4 ve RoboticAutomations 909 dosyaları main'de değil, birleşmemiş `claude/adoring-maxwell-q7t60g` dalında; kanıt yolları `dal:...` önekiyle yazıldı.

## 2. Durum dağılımı (tekil)

| Durum | Sayı | Açıklama |
|---|---|---|
| A_TEST_EDILDI_GECTI | 10 | paper/canlı kadroda |
| B_TEST_EDILDI_ELENDI | 485 | son tabi tutulduğu testte elendi |
| C_KODLANDI_KOSULMADI | 42 | kodda var, hiçbir sonuç dosyasında yok |
| D_KODLANMADI_NEDENLI | 3824 | nedeni bir dosyada yazılı |
| E_KODLANMADI_NEDENSIZ | 161 | hiçbir dosyada akıbeti yok |
| F_YASAK_TIP | 304 | martingale/DCA/ort. düşürme/stopsuz grid |
| G_ML | 526 | makine öğrenmesi / LLM |
| H_BIZIM_EVRENDE_UYGULANAMAZ | 836 | hisse kesitsel, opsiyon, pairs, seans, orderbook… |
| BELIRSIZ | 35 | kanıt yetersiz |
| **Toplam** | **6223** | |

- B son aşama: v1_wf 259, v2_eleme 192, v2_test 11, v3_eleme 9, v2_eleme_hata 6, v1_saglamlik 5, v2_set_secimi 3.
- D nedenleri (ilk 10): benzer_var 2174, kural_belirsiz 507, kod_yok 297, arac_sablon 271, veri_yok 224, lookahead 125, oncelik_disi 55, tekrar_kart_yok 42, cikis_modulu 40, kapsam_disi 22.
- H nedenleri: hisse_kesitsel 284, opsiyon 149, seans_gap 69, pairs 61, kapsam_disi 48, orderbook 45, forex_veri 41, veri_diger 35, veri_yok 25, alt_1dk 16, vix 15, onchain 11.
- F: dca 155, martingale 67, stopsuz_grid 51, ortalama_dusurme 31. (Ön elemenin "yasak" torbasındaki lookahead/model satırları D/G'ye taşındı.)

## 3. A — geçenler

| Strateji | Aşama | Test / işlem |
|---|---|---|
| `dis__e0v1en` | canli_kadro | k3_kripto:15m,30m/3sembol; k3_hisse_kisa:15m,30m/7sembol; v1 · holdout_kesif:83 |
| `dis__ewo-ema-ofset` | canli_kadro | v1_evren:5m,15m/21enstrüman; v2:15m/kripto · holdout:46 |
| `dis__gauss-stoch-eth` | paper_v2 | k3_kripto:4h,1d/3sembol; k3_dk_v2:4h,1d/10sembol; v1_evren:4 · holdout:159 |
| `dis__haftalik-macd-gunluk-ma` | paper_v2 | v1_evren:4h,1d/34enstrüman; v2:1d/genel · holdout_kesif:65 |
| `dis__hma-atr-rider` | paper_v2 | k3_kripto:4h,1d/3sembol; k3_dk_v2:4h,1d/10sembol; v1_evren:4 · holdout_kesif:282 |
| `dis__jt-awesome-osilator` | paper_v2 | k3_kripto:4h,1d/3sembol; k3_dk_v2:4h,1d/10sembol; v1_evren:4 · holdout_kesif:208 |
| `dis__lube` | paper_v2 | k3_kripto:4h,1d/3sembol; k3_dk_v2:4h,1d/10sembol; v1_evren:4 · holdout_kesif:20 |
| `dis__uc-ortalama-boga-sma60` | paper_v2 | k3_kripto:4h,1d/3sembol; k3_dk_v2:4h,1d/10sembol; v1_evren:4 · holdout_kesif:48 |
| `dis__voltarget-trend` | paper_v2 | k3_kripto:4h,1d/3sembol; k3_dk_v2:4h,1d/10sembol; v1_evren:4 · holdout_kesif:140 |
| `pf__sabit_sepet` | paper_v2 | v1_evren:1d/35enstrüman; v2:1d/genel · holdout_kesif:363 |

## 4. C — kodlandı, hiç koşulmadı

| Kod | Neden (dosyadan) |
|---|---|
| `AYAR:dis__funding-carry:d11j:funding-pozitif-short:esik0_short` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__kesit_ls:d11j:kesit-skor-kombinasyonu-momentum-carry:kombine_07_03` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__kesit_ls:d12b:kesit-dusuk-vol-ls:dusuk_vol_90` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__kesit_ls:d12b:kesit-ibs:ibs_k3_gunluk` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__kesit_ls:d12b:kesit-orantili-agirlik:donus_orantili` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__kesit_ls:d12b:r2-secicilik-alfa:evren_faktor_90` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__pairs:d11j:uzun-yonlu-cift-dunku-getiri:dunku_getiri` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__ref_filtreli_long:d11j:piyasa-rejim-filtreleri-genislik-ftd-dagitim:dagitim_spx` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__ref_filtreli_long:d11j:piyasa-rejim-filtreleri-genislik-ftd-dagitim:ftd_spx` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__ref_filtreli_long:d11j:piyasa-rejim-filtreleri-genislik-ftd-dagitim:genislik_hisse` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__rotasyon:d11j:rotasyon-skor-modlari-triplersi-bb:bb_uzaklik_k1` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__rotasyon:d11j:rotasyon-skor-modlari-triplersi-bb:triple_rsi_hacim_top5` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__rotasyon:d12b:rotasyon-getiri-vol-agirlik:getiri_vol_k3` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__sabit_sepet:d11j:portfoy-agirlik-semalari-hrp-minvar-mvo:hrp` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__sabit_sepet:d11j:portfoy-agirlik-semalari-hrp-minvar-mvo:min_var` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `AYAR:pf__sabit_sepet:d11j:portfoy-agirlik-semalari-hrp-minvar-mvo:mvo` | ayar araştırma hattının aday kümesine girmiyor (motor/arastirma/tarama.py::_ayar_listesi) |
| `KOD:pf__v3-funding-1s-devam` | koşulamadı: altyapı yok — Saatlik veri ve funding_orani gerekir; portföy araştırma hattı yalnız 1d çalıştığı için ölçülemez  |
| `KOD:pf__v3-funding-kesit-decil-carry` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:pf__v3-funding-z90-3gun` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__adaptivetrend-6s-momentum` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__aralik-kirilim-bekleyen-emir` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__asya-kutu-kirilim-ma50` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__donchian-ansambl-vol-hedef` | yerine pf__v3-donchian-ansambl kodlandı; eski tek-grafik sürüm kaynağa aykırı sayıldı (kodlama_v3.csv satır 8 notu); tek-grafik sürüm v3 eleme listesinde yok  |
| `KOD:v3__ema-9-21-50-rsi-hacim` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__haftalik-sma-trix-kirilim` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__kirmizi-mum-2x-hacim` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__l-sekli-ma-kirilim-long` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__londra-volatilite-kirilim` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__momentum-sifir-kesisim` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__orb-4s-hacim-atr` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__pazartesi-dip-endeks` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__rsi14-ema200-izleyen-stop` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__rsi2-sma200-hacim` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__rsi30-hacim-ema200` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__rsi32-yon-hedef4` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__saat-21-23-utc` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__saatlik-asiri-tepki` | aile temsilcisi değil + birincil metin okunana dek bekletildi (ON_KAYIT_V3 0.4: 'saatlik-asiri-tepki birincil metin okunamadığı için bu turda yok'; DURUM.md 2026-11-11 's |
| `KOD:v3__sma-trend-rsi-atr` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__ters-fvg-nq-long` | koşulamadı: veri yok — NQ verisi yok; mevcut DK hisse verisi 1h ve NQ sabit puanları ile 5m New York seans kuralını karşılamıyor; kod ileride uygun veri için korunuyor  |
| `KOD:v3__volatilite-kirilim-k05` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__yarim-fitil` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `KOD:v3__z-skor-karsit` | aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test büt |
| `AYAR:pf__kesit_ls:d12b:kesit-orantili-agirlik:getiri_orantili` | ek ayar dosyası araştırma hattında okunmuyor (kaynak satırı bağlanmadı) |
| `AYAR:pf__kesit_ls:d12b:r2-secicilik-alfa:btc_faktor_90` | ek ayar dosyası araştırma hattında okunmuyor (kaynak satırı bağlanmadı) |

Toplam koşulmamış: 26 strateji + 18 ek ayar. Kanıt: `motor/arastirma/tarama.py::_ayar_listesi`, `motor/arastirma/wf_portfoy.py::aday_listesi` (yalnız kart_ayarlari + dis_ayarlari + BAGLAMA + ızgara); `ayarlar_d11j_ek.json`/`ayarlar_d12b_ek.json` yalnız `testler/` içinde okunuyor.

## 5. E — kodlanmadı, akıbeti hiçbir yerde yazmıyor (161)

Kaynağa göre: B001 (ar/dis_arastirma/2026-11_freqtrade_robotic/dosya_listesi.csv) 96, P002 (stratejiler/ek_kaynaklar/repo_raporlari.csv) 29, X005 (ma/2026-11_trend_ortalamaya_donus/ajan1/strateji_listesi.csv) 29, D001 (stratejiler/dis_envanter.csv) 3, A001 (arsiv/algo-sg/STRATEJILER.md) 1, A002 (arsiv/algo-sg/STRATEJILER_GUNLUK.md) 1, A007 (arsiv/swing-sg/trend/stratejiler.py) 1, P001 (stratejiler/ek_kaynaklar/repo_kodlari.csv) 1.

| Tekil | Ad | Mantık |
|---|---|---|
| `A001:8` | algo-sg elenen: 24 saatlik momentum patlamasi | 24 saatlik log getiri esigi asilinca trend yonunde momentum devami girisi (s5 ret24_min kolu). |
| `A002:6` | algo-sg elenen: Elder Impulse ilk gun girisi | Haftalik Elder Impulse renk degisiminin ilk gununde yonde giris. |
| `A007:8` | brainbrick 089 - emtia degeri (5 yil once fiyat / bugun) | 5 yil onceki fiyat / bugunku fiyat orani en yuksek ucte biri long (emtia degeri). |
| `B001:132` | AIRA - open code v2/strategies/hyperopt-and-tools/backtest-result-2025 | Giriş: cok kollu/dolayli giris (koddan atom cikmadi); gosterge havuzu=BB; kod: 'pattern_bullish_4h = (\n (df[" |
| `B001:147` | AIRA - open code v2/strategies/moving-average/GnF.py | Giriş: greed_fear_index > 0.7 ve greed_fear_index < 0.3 / Çıkış: greed_fear_index < 0.3 veya greed_fear_index  |
| `B001:148` | AIRA - open code v2/strategies/moving-average/GnF_V2.py | Giriş: greed_fear_index > 0.7 ve volume > volume_mean ve greed_fear_index < 0.3 / Çıkış: greed_fear_index < 0. |
| `B001:152` | AIRA - open code v2/strategies/moving-average/MoMy5.py | Giriş: mri > self.mri_threshold_high.value ve close > wma ve mri < self.mri_threshold_low.value ve close < wma |
| `B001:153` | AIRA - open code v2/strategies/moving-average/MoMy6.py | Giriş: close > tsf ve close < tsf ve mri > self.mri_threshold_high.value ve mri < 80 ve mri < self.mri_thresho |
| `B001:155` | AIRA - open code v2/strategies/moving-average/ZeroLag.py | Giriş: volume > 0 ve trend == 1 ve trend.shift() != 1 ve trend_4h_4h_x == 1 ve trend_4h_4h_x.shift() != 1 / Çı |
| `B001:21` | AIRA - open code v2/strategies/arima-statistical/ARIMA_5_N.py | Giriş: volume > 0 ve sma_dn.shift() > sma_dn ve max_l < atr_pcnt ve OHLC4 < sma ve sma_up.shift() < sma / Çıkı |
| `B001:210` | AIRA - open code v2/strategies/rsi-momentum/InnovativeReversalStrategy | Giriş: irm > self.irm_threshold_high.value ve irm < self.irm_threshold_low.value / Çıkış: irm < self.irm_thres |
| `B001:211` | AIRA - open code v2/strategies/rsi-momentum/InnovativeReversalStrategy | Giriş: irm > self.irm_threshold_high.value ve irm < self.irm_threshold_low.value / Çıkış: irm < self.irm_thres |
| `B001:213` | AIRA - open code v2/strategies/rsi-momentum/RSIBB_V3.py | Giriş: qtpylib.crossed_above(close, bbu) ve qtpylib.crossed_above(volume, vbbu) ve qtpylib.crossed_below(close |
| `B001:222` | AIRA - open code v2/strategies/rsi-momentum/feratrading_rv_strategy.py | Giriş: rsi < 70 ve rsi > 30 ve volume > volume_sma ve atr_weighted > atr_sma1 ve atr_weighted.shift(1) <= atr_ |
| `B001:228` | AIRA - open code v2/strategies/rsi-momentum/ultra_creative_strategy.py | Giriş: indicator_0_macd.diff() > 0 ve indicator_0_signal > 0 ve close.diff() < 0 / Çıkış: indicator_0_hist > i |
| `B001:229` | AIRA - open code v2/strategies/rsi-momentum/ultra_creative_strategy_fi | Giriş: indicator_0_macd.diff() > 0 ve indicator_0_signal > 0 ve close.diff() < 0 / Çıkış: indicator_0_hist > i |
| `B001:234` | AIRA - open code v2/strategies/scalping/ScalpInUptrend.py | Giriş: rsi < self.rsi_overbought.value ve sma50 > sma200 ve adx > self.adx_threshold.value / Çıkış: close >= o |
| `B001:236` | AIRA - open code v2/strategies/schism-hyperion/Apollo11.py | Giriş: vwmacd < signal ve low < s1_ema_xxl ve close > s1_ema_xxl ve qtpylib.crossed_above(s1_ema_sm, s1_ema_md |
| `B001:246` | AIRA - open code v2/strategies/uncategorized/SlopeV2.py | Giriş: volume > 0 ve plus_di > self.threshold_di_buy.value ve plus_di < self.threshold_di_buy.value ve volume_ |
| `B001:254` | AIRA - open code v2/strategies/wavetrend/dualwave.py | Giriş: qtpylib.crossed_above(auto_buy_decision, self.auto_buy.value) ve volume > 0 ve qtpylib.crossed_above(au |
| `B001:412` | strategies/bigz-bcmbigz/BigZ0307HO.py | Giriş: cok kollu/dolayli giris (koddan atom cikmadi); gosterge havuzu=BB,MA,RSI,VOL; kod: dataframe.loc[self.b |
| `B001:43` | AIRA - open code v2/strategies/bollinger/.py | Giriş: atr > 1.5 * atr.rolling(window=14).mean() ve atr < atr.rolling(window=14).mean() ve mfi < 20 ve mfi > 8 |
| `B001:431` | strategies/binh-cluc-mad/BinHV45HO.py | Giriş: cok kollu/dolayli giris (koddan atom cikmadi); gosterge havuzu=BB; kod: dataframe.loc[lower.shift().gt( |
| `B001:452` | strategies/binh-cluc-mad/CombinedBinHAndClucV6H.py | Giriş: self.cust_log_verbose == True ve row['buy'] == 1 / Çıkış: volume > 0 veya close > bb_upperband veya clo |
| `B001:479` | strategies/bollinger/BBands.py | Giriş: tema > tema.shift(1) ve volume > 0 / Çıkış: tema < tema.shift(1) veya volume > 0 / Risk: SL=-0.05, ROI= |
| `B001:481` | strategies/bollinger/BBlower.py | Giriş: qtpylib.crossed_above(TEMA, bb_lowerbandTA1) ve RSI < 50 ve RSI.shift(3) > RSI.shift(4) ve RSI > RSI.sh |
| `B001:489` | strategies/bollinger/Chandemtwo.py | Giriş: CMO >= 0 ve qtpylib.crossed_above(CMO.shift(2), 0) ve CMO.shift(1) >= 0 / Çıkış: qtpylib.crossed_above( |
| `B001:498` | strategies/bollinger/Dracula.py | Giriş: prev['bb_bbl_i'] == 1 ve prev['close'] >= prev1['support'] ve prev['ema'] < prev['close'] ve prev['open |
| `B001:500` | strategies/bollinger/EXPERIMENTAL_STRATEGY.py | Giriş: plus_di > 0.5 ve adx > 65 ve rsi < 35 ve fastd < 35 / Çıkış: minus_di > 0 veya adx > 70 veya qtpylib.cr |
| `B001:51` | AIRA - open code v2/strategies/bollinger/StarRise_V2.py | Giriş: self.config['runmode'].value in ('live', 'dry_run') ve last_candle['enter_long'] == 1 ve trailing_buy[' |
| `B001:521` | strategies/bollinger/Saturn5.py | Giriş: vwmacd < signal ve low < s1_ema_xxl ve close > s1_ema_xxl ve qtpylib.crossed_above(s1_ema_sm, s1_ema_md |
| `B001:526` | strategies/bollinger/TemaPure.py | Giriş: TEMA <= bb_lowerbandTA ve qtpylib.crossed_above(CMO, 0) / Çıkış: qtpylib.crossed_above(TEMA, bb_upperba |
| `B001:540` | strategies/cycle-oscillators/DCBBBounce.py | Giriş: close < sar ve close > sma ve close > ema50 ve qtpylib.crossed_above(dcbb_diff_lower, 0) ve adx > self. |
| `B001:546` | strategies/cycle-oscillators/TenderEnter.py | Giriş: volume > 0 / Çıkış: volume > 0 / Risk: SL=-0.25933, ROI={0:0.21296, 94:0.13203, 190:0.04443, 374:0}, tr |
| `B001:55` | AIRA - open code v2/strategies/bollinger/ZaratustraV11.py | Giriş: pdi_5m > mdi_5m ve mdi_5m > pdi_5m ve pdi_15m > mdi_15m ve mdi_15m > pdi_15m ve pdi_30m > mdi_30m / Çık |
| `B001:60` | AIRA - open code v2/strategies/bollinger/bbw1h.py | Giriş: mfi < 25 ve mfi > 75 ve close < zone_long_limit_1h ve close > zone_short_limit_1h ve adx_falling_1h ==  |
| `B001:601` | strategies/gkd/GKD_Baseline.py | Giriş: close <= goldie_max ve close >= goldie_min ve price_above.shift(1) == False ve price_below.shift(1) ==  |
| `B001:602` | strategies/gkd/GKD_BaselineAllMAs.py | Giriş: close <= goldie_max ve close >= goldie_min ve price_above.shift(1) == False ve price_below.shift(1) ==  |
| `B001:603` | strategies/gkd/GKD_C.py | Giriş: close <= goldie_max ve close >= goldie_min ve hurst_smooth > self.hurst_threshold.value ve volatmeter > |
| `B001:604` | strategies/gkd/GKD_FisherTransform.py | Giriş: self.can_short == True / Çıkış: self.can_short == True veya fisher_smooth_6h > fisher_6h veya fisher_sm |
| `B001:605` | strategies/gkd/GKD_FisherTransformMTF.py | Giriş: self.can_short == True / Çıkış: self.can_short == True veya fisher_smooth_6h > fisher_6h veya fisher_sm |
| `B001:606` | strategies/gkd/GKD_FisherTransform__2.py | Giriş: self.can_short == True / Çıkış: self.can_short == True veya fisher_smooth_6h > fisher_6h veya fisher_sm |
| `B001:607` | strategies/gkd/GKD_HurstExponent.py | Giriş: close <= goldie_max ve close >= goldie_min ve hurst_smooth > self.hurst_threshold / Çıkış: hurst_smooth |
| `B001:608` | strategies/gkd/GKD_PFE.py | Giriş: self.can_short == True / Çıkış: self.can_short == True veya pfe_smooth < 0 veya pfe_smooth > 0 / Risk:  |
| `B001:61` | AIRA - open code v2/strategies/bollinger/monte_carlo_strategy.py | Giriş: momentum > 0 ve mc_win_probability > 0.6 ve volume_ratio > 1.1 ve mc_sharpe_sim > 0 ve bb_percent < 0.2 |
| `B001:615` | strategies/heikin-ashi/grad.py | Giriş: volume > 0 ve frac_diff > 0 ve frac_diff.shift() < 0 / Çıkış: volume > 0 veya frac_diff < 0 veya frac_d |
| `B001:616` | strategies/heikin-ashi/heikin.py | Giriş: emao < emac / Çıkış: emao > emac / Risk: SL=-0.99, ROI={0:10} |
| `B001:617` | strategies/heikin-ashi/tacos1.py | Giriş: qtpylib.crossed_above(dataframe[f'ema_bshort_{self.buy_ema_short.value}'], dataframe[f'ema_blong_{self. |
| `B001:63` | AIRA - open code v2/strategies/channels/KC_NOBB.py | Giriş: low < kc_lowerband ve high > kc_upperband ve bb_width_4h > 7.0 ve rsi_30m > rsi_ma_30m ve rsi_30m < rsi |
| `B001:632` | strategies/ichimoku/MacheteV8b.py | Giriş: go_long_inf > 0 ve up_trend_inf > 0 ve sslUp_inf > sslDown_inf ve self.get_buy_signal_tema_rsi_strategy |
| `B001:633` | strategies/ichimoku/MacheteV8bRallimod2.py | Giriş: self.get_buy_signal_offset_strategy(dataframe) == True ve self.get_buy_signal_bbrsi_strategy(dataframe) |
| `B001:641` | strategies/ichimoku/epretrace.py | Giriş: volume > 0 / Çıkış: close > 1000000 veya volume > 0 veya date == trade_date veya current_rate >= eptarg |
| `B001:644` | strategies/moving-average/ActionZone.py | Giriş: volume > 0 ve fastMA > slowMA ve close > fastMA / Çıkış: volume > 0 veya fastMA < slowMA veya close < f |
| `B001:65` | AIRA - open code v2/strategies/channels/ultra_creative_strategy_202507 | Giriş: indicator_0 > indicator_1 ve indicator_1 > 0 ve indicator_2_k.diff() > 0 ve indicator_2_d.diff() > 0 /  |
| `B001:652` | strategies/moving-average/EMAPriceCrossoverWithThresh.py | Giriş: qtpylib.crossed_above(close, ema800) ve volume > 0 / Çıkış: qtpylib.crossed_below(close, ema_threshold) |
| `B001:654` | strategies/moving-average/EMAVolume.py | Giriş: qtpylib.crossed_above(ema13, ema34) ve volume > volume.rolling(window=10).mean() / Çıkış: qtpylib.cross |
| `B001:66` | AIRA - open code v2/strategies/cycle-oscillators/GEAR.py | Giriş: volume > 0 / Çıkış: ROI/stop/trailing / Risk: SL=-0.06, ROI={0:0.03, 40:0.015, 120:0.0} |
| `B001:661` | strategies/moving-average/MSO.py | Giriş: ms_osc > self.buy_threshold.value ve cycle_osc > 50 / Çıkış: ms_osc < self.sell_threshold.value veya cy |
| `B001:684` | strategies/moving-average/PumpDetector.py | Giriş: qtpylib.crossed_above(j, 0) ve volume > 0 / Çıkış: volume > 0 veya qtpylib.crossed_above(j, 90) veya qt |
| `B001:686` | strategies/moving-average/RobotradingBody.py | Giriş: volume > 0 ve open > close ve body > body_sma / Çıkış: close > open veya volume > 0 / Risk: SL=-0.99, R |
| `B001:687` | strategies/moving-average/SMAIP3.py | Giriş: self.config['runmode'].value == 'hyperopt' / Çıkış: self.config['runmode'].value == 'hyperopt' veya clo |
| `B001:688` | strategies/moving-average/SMAIP3v2.py | Giriş: self.config['runmode'].value == 'hyperopt' / Çıkış: self.config['runmode'].value == 'hyperopt' veya clo |
| `B001:689` | strategies/moving-average/SMAOG.py | Giriş: self.config['runmode'].value == 'hyperopt' / Çıkış: self.config['runmode'].value == 'hyperopt' veya clo |
| `B001:691` | strategies/moving-average/SMAOffset.py | Giriş: self.config['runmode'].value == 'hyperopt' / Çıkış: self.config['runmode'].value == 'hyperopt' veya clo |
| `B001:706` | strategies/moving-average/moonhouse.py | Giriş: volume > 0 ve Mercury_dec > Mercury_dec.shift(1) ve Jupiter_rax < Sun_rax ve Mercury_dec < Sun_dec ve M |
| `B001:709` | strategies/murrey-gann/TD.py | Giriş: qtpylib.crossed_above(dataframe[f'sma_ha_close{self.sma_ha_close.value}'], dataframe[f'sma_ha_open{self |
| `B001:743` | strategies/orderbook-volume/redditMA.py | Giriş: qtpylib.crossed_above(FASTMA, SLOWMA) / Çıkış: qtpylib.crossed_below(FASTMA, SLOWMA) / Risk: SL=-0.5, R |
| `B001:749` | strategies/pivot-supertrend/LuxOSC.py | Giriş: volume > 0 ve qtpylib.crossed_above(osc, int(self.cross_buy.value)) ve supertrend > close / Çıkış: qtpy |
| `B001:750` | strategies/pivot-supertrend/MostOfAll.py | Giriş: qtpylib.crossed_above(most, exma) ve volume > 0 / Çıkış: qtpylib.crossed_above(exma, most) veya volume  |
| `B001:756` | strategies/pivot-supertrend/slope_is_dopeCT.py | Giriş: dataframe[f'rsi_{self.rsi_length.value}'] > self.rsi_buy.value ve close > close.shift(+self.slope_lengt |
| `B001:785` | strategies/rsi-momentum/MADisplaceV3.py | Giriş: self.config['runmode'].value == 'hyperopt' / Çıkış: self.config['runmode'].value == 'hyperopt' veya 'up |
| `B001:790` | strategies/rsi-momentum/Persia.py | Giriş: cok kollu/dolayli giris (koddan atom cikmadi); gosterge havuzu=MA,RSI; kod: conditions = [] for i in ra |
| `B001:791` | strategies/rsi-momentum/RSI.py | Giriş: rsi < 30 ve rperc < -80 / Çıkış: rsi_30m > 70 veya rperc_30m > -20 / Risk: SL=-0.99, ROI={0:0.09} |
| `B001:802` | strategies/rsi-momentum/Trend_Strength_Directional.py | Giriş: ta.PLUS_DI(dataframe, timeperiod=int(self.buy_plusdi.value)) > ta.MINUS_DI(dataframe, timeperiod=int(se |
| `B001:807` | strategies/rsi-momentum/UltimateMomentumIndicator.py | Giriş: qtpylib.crossed_above(utmi, 50) ve volume > 0 / Çıkış: qtpylib.crossed_below(utmi, 70) veya volume > 0  |
| `B001:808` | strategies/rsi-momentum/Uptrend.py | Giriş: self.config['runmode'].value in 'backtest' ve self.config['runmode'].value in 'hyperopt' / Çıkış: mama_ |
| `B001:809` | strategies/rsi-momentum/YOLO.py | Giriş: volume > 0 ve aroon-down < params['aroon-down'] ve adx > params['adx'] ve aroon-up > params['aroon-up'] |
| `B001:835` | strategies/schism-hyperion/Apollo11.py | Giriş: vwmacd < signal ve low < s1_ema_xxl ve close > s1_ema_xxl ve qtpylib.crossed_above(s1_ema_sm, s1_ema_md |
| `B001:842` | strategies/schism-hyperion/apollo.py | Giriş: vwmacd < signal ve low < s1_ema_xxl ve close > s1_ema_xxl ve qtpylib.crossed_above(s1_ema_sm, s1_ema_md |
| `B001:855` | strategies/smart-money-concepts/FVGChannel.py | Giriş: close.shift(3) < lower_extreme.shift(3) ve volume > 0 ve close > lower_extreme ve close > lower_inner v |
| `B001:857` | strategies/smart-money-concepts/Guacamole.py | Giriş: self.config['runmode'].value in ('live', 'dry_run') ve Trade.pair == metadata['pair'] / Çıkış: self.con |
| `B001:858` | strategies/smart-money-concepts/Hacklemore2.py | Giriş: self.config['runmode'].value in ('live', 'dry_run') ve Trade.pair == metadata['pair'] / Çıkış: self.con |
| `B001:859` | strategies/smart-money-concepts/Hacklemore3.py | Giriş: self.config['runmode'].value in ('live', 'dry_run') ve Trade.pair == metadata['pair'] / Çıkış: self.con |
| `B001:860` | strategies/smart-money-concepts/Kamaflage.py | Giriş: self.config['runmode'].value in ('live', 'dry_run') ve Trade.pair == metadata['pair'] / Çıkış: self.con |
| `B001:862` | strategies/smart-money-concepts/MomStrategy.py | Giriş: signal == 1 / Çıkış: signal == -1 / Risk: SL=-1, ROI={0:0.04, 30:0.02, 60:0.01} |
| `B001:863` | strategies/smart-money-concepts/PRICEFOLLOWING.py | Giriş: rsi < self.rsi_value.value ve qtpylib.crossed_below(ema7, tema) ve (last_tema - last_ema7) / last_tema  |
| `B001:864` | strategies/smart-money-concepts/PRICEFOLLOWING2.py | Giriş: rsi < self.rsi_value.value ve qtpylib.crossed_below(ema7, tema) ve (last_tema - last_ema7) / last_tema  |
| `B001:877` | strategies/two-candle/TwoCandleTheory.py | Giriş: self.buy_params['ema_length'] > 0 / Çıkış: 'take_profit_price' in custom_info veya current_rate <= cust |
| `B001:882` | strategies/uncategorized/HilbertSineWave.py | Giriş: close <= support_green / Çıkış: close >= resistance_red / Risk: SL=-0.05, ROI={0:0.1} |
| `B001:888` | strategies/uncategorized/MFI.py | Giriş: MFI.shift() <= 14 / Çıkış: MFI >= 75 / Risk: SL=-0.1, ROI={0:0.05, 20:0.04, 40:0.03, 80:0.02, 1440:0.01 |
| `B001:889` | strategies/uncategorized/NormalizerStrategy.py | Giriş: pct_sum < 0.2 ve volume > 0 / Çıkış: pct_sum > 8 veya volume > 0 / Risk: SL=-0.99, ROI={0:0.18}, traili |
| `B001:890` | strategies/uncategorized/NormalizerStrategyHO2.py | Giriş: pct_sum < 0.2 ve volume > 0 / Çıkış: pct_sum > 8 veya volume > 0 / Risk: SL=-0.99, ROI={0:0.18}, traili |
| `B001:893` | strategies/uncategorized/SlowPotato.py | Giriş: low <= low.rolling(1440).mean() ve volume > 0 / Çıkış: high >= high.rolling(1440).mean() veya volume >  |
| `B001:898` | strategies/uncategorized/XtraThicc.py | Giriş: close < dataframe[f'3d-high_{self.inf_timeframe}'] ve close > dataframe[f'3d-low_{self.inf_timeframe}'] |
| `B001:901` | strategies/wavetrend/TRIWAVE.py | Giriş: qtpylib.crossed_above(auto_buy_decision, self.auto_buy.value) ve volume > 0 ve qtpylib.crossed_above(au |
| `B001:902` | strategies/wavetrend/WTHO.py | Giriş: dataframe[f'wave_t1_{self.buy_wt1_length.value}'] > dataframe[f'wave_t2_{self.buy_wt2_length.value}'] v |
| `B001:904` | strategies/wavetrend/dualwave.py | Giriş: volume > 0 ve 200_SMA > 200_SMA.shift(1) ve 200_SMA < 200_SMA.shift(1) ve 200_SMA_2h > 200_SMA_2h.shift |
| `B001:905` | strategies/wavetrend/pcb20.py | Giriş: rsi_ma_slope > 0 ve rsi_ma >= self.buy_rsil.value ve wave_t1 >= wave_t2 ve rsi_ma <= self.buy_rsiu.valu |
| `B001:906` | strategies/wavetrend/tacos.py | Giriş: rsi_ma_slope > 0 ve rsi_ma >= self.buy_rsil.value ve wave_t1 >= wave_t2 ve rsi_ma <= self.buy_rsiu.valu |
| `D001:141` | NQ/MNQ Super Scalper [BACKTEST] | NQ/MNQ çok girişli süper scalper; 20 kademeli ekleme ve 20 desenli akıllı çıkış. |
| `D001:347` | Minervini trend şablonu + %10 stop | Minervini trend şablonu sağlanınca long; %10 stop. |
| `D001:383` | Trailing Trade (1h, örnek ayar) | Binance bot örnek ayarı: iz süren giriş-çıkış. |
| `P001:190` | M1 Countertrend Scalping Strategy | Fiyat 9/20/50 EMA'lardan yeterince uzaklaşınca trende karşı girilen ve kârdaki en yakın EMA'da çıkılan scalpin |
| `P002:128` | Bitcoin SuperFlip / Supertrend EMA Trend-Following Strategy |  |
| `P002:131` | Heikin-Ashi MACD |  |
| `P002:148` | Fibonacci Cloud / Multi-Timeframe Fibonacci Scanner |  |
| `P002:152` | Supertrend adapted to strategy |  |
| `P002:155` | Apex Trail / Trend Agreement Scalper with ATR Trailing Stop |  |
| `P002:156` | Trend Engine / Scored Trend Strategy with Squeeze Breakout |  |
| `P002:157` | Gradient Ribbon / EMA Ribbon Slope-Acceleration System |  |
| `P002:168` | Gravity Trend / ADX Strength Meter & Quality-Scored DMI System |  |
| `P002:172` | Harmonic Pulse / XABCD Fibonacci Pattern Strategy |  |
| `P002:174` | Power Surge / BB Momentum Squeeze Release |  |
| `P002:179` | Breakout Pulse / Volume-Confirmed Support/Resistance Strategy |  |
| `P002:180` | Liquidity Sweep Tracker / Smart Money Stop Hunts |  |
| `P002:183` | Liquidity Hunter / SMC System - Full Suite |  |
| `P002:194` | TrendBreaker Pro / Auto Trendline Break Strategy with Momentum |  |
| `P002:195` | Momentum Bands / Breakout |  |
| `P002:196` | Bull & Wolf Nifty Indicator |  |
| `P002:200` | Z-Edge / Confluence Z-score Strategy |  |
| `P002:214` | VWAP Suite / Trend & Mean Reversion with Adaptive Filters |  |
| `P002:229` | HVN Fade & Break / Volume Profile Fade & Breakout Strategy |  |
| `P002:246` | Hammer Long strategy with filtered and enforced alerts |  |
| `P002:278` | [Bybit BTCUSD.P] 7Years Backtest Results. 2,609% +Non-Repainting |  |
| `P002:306` | SuperTrend AI Adaptive - Strategy [BTC] |  |
| `P002:312` | [3Commas] Alligator Strategy |  |
| `P002:314` | XAUUSD 10-Minute Strategy |  |
| `P002:319` | [3Commas] Trail Hunter - Reversal Long |  |
| `P002:328` | Alpha AI Essential - Multi-Market Trading Strategy |  |
| `P002:329` | Scalping Strategy Signal v2 |  |
| `P002:330` | ICT Sessions & Liquidity Sweeps Strategy |  |
| `P002:331` | The Rook Algo PRO |  |
| `X005:112` | A different indicator (DV2) | DIGER_MR: Önceki günün DV2 değeri 10'un altında, kapanış 200 günlük SMA üzerinde ve 6 aylık getiri pozitifse a |
| `X005:236` | ATRくん | KELTNER_ENVELOPE_FADE: Her barda bir önceki kapanış ± c×ATR(14) seviyelerine ters yönde alış ve satış limit em |
| `X005:362` | Backtest Larry Williams 9.1 (exemplo) - JB | DIGER_TREND: 9 periyotluk EMA'nın altında açılıp üstünde kapanan ilk mumun tepesinin kırılmasında al |
| `X005:363` | Advanced Larry Williams 9.2- By Edu | DIGER_TREND: EMA9 yükselirken en yüksek kapanışlı referans mumdan sonra bir mum referansın dibinin altında kap |
| `X005:377` | Reversal closing price (Preço de Fechamento de Reversão, PFR) | SHORT_TERM_REVERSAL: Uzun: cari mumun dibi son 2 mumun diplerinin altında ve kapanışı önceki kapanışın üstünde |
| `X005:378` | MY BOX by Gustavo (PFR com alvo Fibonacci 1,618) | SHORT_TERM_REVERSAL: Alış PFR mumu oluşunca sonraki mum PFR mumunun kapanışını kırarsa al; satış PFR'de kapanı |
| `X005:418` | CDC ActionZone V3 2020 | DIGER_TREND: Hızlı EMA yavaş EMA'nın üstünde ve fiyat hızlı EMA'nın üstündeyken oluşan ilk 'yeşil' bar kapanış |
| `X005:419` | action zone - ATR stop reverse order strategy v0.1 by 9nck | MA_CROSS: Pozisyon yokken hızlı EMA yavaş EMA'yı yukarı keserse long, aşağı keserse short emri; pozisyon varke |
| `X005:465` | Contrarian EMA50 & DMS rule (Contrarian Technical Trading Rules: Evide | DIGER_MR: Klasik trend sinyalinin tersini uygula: endeks 50 günlük EMA'nın altında (kontrarian EMA50 al) ve Wi |
| `X005:466` | Contrarian Parabolic SAR rule (Nairobi Stock Index) | DIGER_MR: Fiyat Wilder Parabolic SAR'ın altındayken (normalde sat sinyali) endekse uzun gir |
| `X005:467` | Contrarian Stochastic rule (Nairobi Stock Index) | STOCH_WILLIAMS_MR: %K(14) %D'nin altında VE %D düşüyorsa (normalde sat sinyali) endekse uzun gir |
| `X005:515` | Traders' Tips – The Vortex Indicator (Botes & Siepman) | DIGER_TREND: VI+ (Σ/Yüksek − önceki Düşük/ / ΣTR) VI−'yi yukarı kesince kesişim barının yükseğine buy-stop; aş |
| `X005:578` | SlowPotato | MA_SAPMA_MR: Mumun düşüğü son 1440 mumun (5 dk × 1440 = 5 gün) düşüklerinin ortalamasına eşit ya da altındaysa |
| `X005:583` | MMM (Média Móvel de Máximas e Mínimas) | KELTNER_ENVELOPE_FADE: Kapanış SMA(30) üstündeyken kapanış, son 3 mumun düşüklerinin SMA(3)'ü altına inerse uz |
| `X005:584` | MongeYokohama | MA_SAPMA_MR: Kapanış, düşüklerin EMA(5)'inin 1.02'ye bölünmüş değerinin altına inerse (yaklaşık %2 aşağı sapma |
| `X005:626` | 成交量的奥秘：另类价量共振指标的择时 (华创证券 研报复现, VM_Strategy) | DIGER_TREND: Fiyat momentumu = HMA(50)/3 bar önceki HMA(50); hacim momentumu = HMA(hacim,5)/HMA(hacim,100); si |
| `X005:683` | Un sistema con indicadores clásicos | DIGER_TREND: SMA20 aşağı eğimden sonra ilk kez yukarı döndüğünde ertesi gün al; dönüş anında RSI(10) 70 ya da  |
| `X005:69` | DMI Swings (by Coinrule) | DIGER_MR: '-DI > +DI ve ADX > 45 iken al (güçlü düşüş hareketinde ters yönlü giriş). |
| `X005:697` | Setup Larry Williams Clássico (STP0003, médias de 3 máximas/mínimas) | KELTNER_ENVELOPE_FADE: SMA20 yükseliyorsa ve mumun düşüğü son 3 mumun düşüklerinin ortalamasının (SMA3 low) al |
| `X005:702` | _EXEC_VIRADA_HILOW (virada do HiLo Activator) | DIGER_TREND: Pozisyon yokken kapanış HiLo Activator(7) çizgisinin üstüne çıkınca piyasadan al (yalnız uzun). |
| `X005:715` | The Stiffness Indicator – Traders' Tips Kasım 2018 (TradeStation) | DIGER_TREND: Stiffness (son 60 barda 100 günlük ortalamanın üstünde kapanan bar oranı; ortalama 0.2 std aşağı  |
| `X005:716` | Stiffness pullback strategy (Pullback=1) – Traders' Tips Kasım 2018 (W | DIGER_TREND: Kapanış SMA(100) üstünde, Stiffness ≥ 90, SPY EMA'sı yükseliyor ve RSI(3) 40'ın altından yukarı d |
| `X005:717` | Correlation Trend strategy – Correlation As A Trend Indicator – Trader | DIGER_TREND: Fiyatın zaman ekseniyle 20 barlık korelasyonu (CorrF) 0.5 eşiğini yukarı keserse bir sonraki bard |
| `X005:718` | CorrelationTrend long-only – Traders' Tips Mayıs 2020 (Wealth-Lab) | DIGER_TREND: 20 günlük CorrelationTrend sıfırı yukarı kesince bir sonraki barda al. |
| `X005:745` | Reversion Index – Python sinyali – Traders' Tips Ocak 2026 | DIGER_MR: Reversion index (20) üzerinde SuperSmoother(4) tetik çizgisi SuperSmoother(8) yumuşatma çizgisini yu |
| `X005:746` | Elegant Oscillator BB strategy – Traders' Tips Şubat 2022 (Wealth-Lab) | DIGER_MR: Elegant Oscillator(20), kendi üzerinde hesaplanan Bollinger alt bandını (100, 1.5) yukarı kesince pi |
| `X005:747` | Elegant Oscillator peak/valley – Traders' Tips Şubat 2022 (Zorro) | DIGER_MR: EO −0.5 eşiğinin altında bir dip (valley) yaptığında uzun; +0.5 üstünde tepe (peak) yaptığında kısa  |
| `X005:869` | mr_wings (mean reversion in the wings) | DIGER_MR: EWMAC(Lfast, 4×Lfast) sinyali, kendi 5000 günlük kayan std'sinin 3 katını aşarsa sinyalin tersi kada |
| `X005:883` | Strat_Mean_revers_Hurst (HighPass + Fisher + Hurst filter) | DIGER_MR: HighPass(30) ile trend çıkarılır, FisherN(500) ile normalize; Hurst(500) < 0,5 iken sinyal −1'in alt |

## 6. Adil olmayan elemeler

Elenen 485 kodlu stratejiden 270'i "adil" (birden çok TF, ızgara, geniş evren) testte elendi. Diğerleri (bir strateji birden çok etikette olabilir): yalniz_varsayilan_ayar 201, yalniz_tek_TF 107, yapisal_kapi 67, kisa_veri 14, zayif_temsilci 1.
- `yalniz_varsayilan_ayar`: son test (çoğunlukla v2 elemesi) tek sabit ayarla yapıldı; v1'de ızgara vardı ama v2 tek ayar taşıdı.
- `yalniz_tek_TF`: son testte tek zaman dilimi. `kisa_veri`: v3/kısa dönem. `yapisal_kapi`: kârlı ama örnek/genişlik/kill kapısı.
- Tam liste: `ara/liste_adil_olmayan.csv`.

### Kârlılığı geçip yapısal kapıdan düşen 73 strateji (v2, yapisal_kapi=evet)

Kapı dağılımı: E4 17, E4+E5 16, E5 15, E2 11, E2+E4 9, E2+E4+E5 3, E2+E5 2. En yüksek net (maliyet ×1) ilk 15:

| Strateji | TF | Düştüğü kapı | Net ×1 | PF ×1 | İşlem | paper_v2 |
|---|---|---|---|---|---|---|
| `dis__kelly-atr-bant` | 1d | E4 | 5.4037 | 1.907 | 504 | hayir |
| `dis__gauss-kanal` | 1d | E4 | 5.3188 | 2.663 | 669 | hayir |
| `pf__rotasyon` | 1d | E5 | 4.7400 | NA | NA | hayir |
| `swing__macd-sinyal` | 1d | E4+E5 | 3.9653 | 1.482 | 1154 | hayir |
| `swing__bb-sikisma-kirilim` | 1d | E4 | 3.6943 | 1.669 | 690 | hayir |
| `swing__rsi-momentum-esik` | 1d | E4+E5 | 3.3749 | 1.894 | 1089 | hayir |
| `swing__heikin-ashi-donus` | 1d | E4+E5 | 3.2258 | 1.294 | 1821 | hayir |
| `dis__ma-cift-cross` | 1d | E4 | 2.6314 | 2.921 | 340 | hayir |
| `dis__pivot-ters-stop` | 1d | E4+E5 | 2.2415 | 1.579 | 773 | hayir |
| `dis__laguerre-rsi` | 1d | E4 | 2.1871 | 2.213 | 493 | hayir |
| `dis__roc20-ls` | 1d | E4+E5 | 2.1718 | 1.656 | 1371 | hayir |
| `swing__ma-geri-cekilme` | 1d | E4+E5 | 2.1003 | 1.838 | 561 | hayir |
| `pf__kanarya` | 1d | E5 | 1.9090 | NA | NA | hayir |
| `pf__sabit_sepet` | 1d | E5 | 1.8313 | NA | NA | evet |
| `dis__z65-rejim` | 1d | E4 | 1.7766 | 1.664 | 733 | hayir |

Tam liste: `ara/liste_yapisal_kapi.csv`. Not: net değerleri 2017→2025 geliştirme dönemi (kanıt değil).

### Benzeri var denip fark test edilmeyenler

2226 kodlanmamış tekil strateji, kodlu bir sınıfa "benzer" denerek bırakıldı; mantık farkı (filtre, çıkış, TF, yön, evren) hiç test edilmedi. Bunların 909'inde benzerlik iddiası bile kodla doğrulanmadı (kaynak heuristiği/önceki ajan). Kodla açılan örneklerde önceki "aynı" kararlarının çoğu tutmadı (G8: 174'te 118 fark; G9: 16 eşleşme reddedildi; G1: 81 `mevcut:X` kartının 8'i eşdeğer). Liste: `ara/liste_fark_test_edilmedi.csv`.

### Diğer adalet bulguları

- 31 kodlu stratejinin birebir kaynak satırı yok: kaynak kartlarının hepsi koda "benzer" (aile kodu kartın kuralını uygulamıyor) ya da v2/v3 eklemesi.
- 102 kitap kartı aile üyesi ama aile kodu kartın kuralını uygulamıyor (G1 NOTLAR). 93 kart `ayar:X` önerilmiş ama `kart_ayarlari`'na yazılmamış; repo envanterinde 374 `ayar:X` satırının ayar kaydı yok.
- v3'te 22 kodlu strateji "aile temsilcisi değil" (test bütçesi) diye koşulmadı (ON_KAYIT_V3 0.4).
- Eski projelerde iyi sonuç verip 1L3A'da aynı biçimi test edilmeyenler (G10 NOTLAR): Argus gizli diverjans, Ichimoku 20/60/120 (eski OOS PF 2.52; bizde ızgara 26/52), günlük kapitülasyon D2, EPA-B, ABD trend portföyü.
- Pairs (61), hisse kesitsel (284), seans/gap (69) tekilleri tanım gereği H; ama `pf__pairs`, `pf__rotasyon`, `pf__kesit_ls`, `daytrade__orb`, `daytrade__gap-doldurma` kodda var ve kendi evrenimizde test edildi — H burada "kaynaktaki enstrümanlar evrenimizde yok" demektir.
- v3 ön elemede "kod yok" gerekçesiyle elenen ama kuralı metinde açık olan satırlar (G6 NOTLAR: V014:440, V013:445, V005:4/5/25, V010:19).

## 7. Belgelerdeki sayılar ↔ tablo

| Belge iddiası | Kaynak | Tablo | Sonuç |
|---|---|---|---|
| 460 tek grafik strateji + 19 portföy sınıfı | `DURUM.md:407` | v1 evren WF: 460 + 19; kodda bugün 492 + 29 | v1 için tutuyor; kod sonra büyüdü (+42) |
| ~120 ek ayar/mod kaydı | `DURUM.md:407` | dis_ayarlari 177 + d11j_ek 11 + d12b_ek 7 (kart_ayarlari 226 ayrı) | TUTMUYOR (195; 18'i hiç koşulmadı) |
| 192 kodlu (105 kitap + 87 dış), 226 kart ayarı, 110 dış ayar | `DURUM.md:103` | kart_ayarlari 226; dış KOD eşlemesi 162 satır; dis_ayarlari 177 | 226 tutuyor; 87/110 eski (Katman 1 anı) |
| ~700 aday: 438 kart + 160 TV + 68 freqtrade + ~30 dış kural | `DURUM.md:74` | kart 810; dis_envanter tv 247, freqtrade 68, kural+awesome+jesuistm 116 | freqtrade tutuyor; TV/kural sayıları TUTMUYOR |
| ~430 strateji (2026-11-07 gece) | `DURUM.md:391` | kodda 521 | ara sayı; bugünle tutmaz (beklenen) |
| 810 kart, 100 aile, 70 elenen | `DURUM.md:24-25,392` | 810 / 100 / 70 | tutuyor |
| rapor 314 (65 yeni, 54 yasak); kod 398 (44 yeni) | `DURUM.md:385` | G3 sayımı birebir (rapor CSV'sinde ayrıca 17 arac_sablon) | tutuyor |
| GitHub 1198 satır | `DURUM.md:392` | 1198 | tutuyor |
| v2: eleme 222 → 18; keşif 7; sağlam 5; set 2 | `DURUM.md:207-211` | G0: 18 geçti, 198 elendi, 6 hata; keşif 7; sağlam 5; set 2 | tutuyor |
| Katman 3b: 32 adaydan 13'ü sağlam | `DURUM.md:109` | sonuclar/saglamlik/k3_kripto.csv'de saglam_mi=True 15 (35 satır) | TUTMUYOR (15; dosya sonradan yenilenmiş olabilir) |
| 26 kodlu strateji hiç koşulmamış | `görev metni` | C: 26 strateji (+18 ek ayar) | tutuyor (ayarlarla 44) |
| v2'de E1+E3 geçip E2/E4/E5'ten düşen 73 | `görev metni` | 73 | tutuyor |
| v3 eleme 0/9 | `DURUM.md:143` | v3 eleme.csv 9 satır, 0 geçen | tutuyor |
| dis_envanter 'kodlandi' yazan satırlar | `stratejiler/dis_envanter.csv` | 7 satırın sınıfı kodda yok (G2 NOTLAR) | TUTMUYOR |
| CODEX_ADAYLAR '12 strateji' | `arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md` | tabloda 11 repo | TUTMUYOR (küçük) |

## 8. Öz denetim

`betikler/oz_denetim_ornek.py`: tekil tablodan tohum 20261113 ile 40 satır; her biri kaynak satırına ve kanıt dosyasına geri izlendi (`ara/oz_denetim.csv`). **Hata: 3/40 = %7.5** (eşik %10 aşılmadı; düzeltmeler `ara/lider_duzeltmeleri.csv`'de uygulandı).
- #10 `HAM:H001:151`: neden_kodu yanlış (martingale değil; kodlanamaz risk modülü, kuyruk C). Durum D doğru.
- #24 `HAM:X005:802`: Coke/Pepsi eşbütünleşme pairs; osilatör sınıfına BENZER bağlanmış. Doğrusu H (pairs, enstrümanlar evrende yok).
- #27 `HAM:P001:190`: M1 trende karşı (EMA uzaklığı, MR) → swing__ma-kesisim BENZER yanlış hedef; ayar hiç yazılmamış → akıbet yok (E).

Ayrıca her ajan çıktısından 10–12 satır kaynağa izlendi (ILERLEME.md denetim günlüğü): 1 hata (G3 P001:135) dışında tutarlı. Hataların hepsi doğrulanmamış "benzer" eşlemelerinde → bu alt kümenin hata oranı genelden yüksektir (örnekte ~10 satırda 2).

## 9. Emin olmadıklarım

- 909 "benzer" eşlemesinin hedef sınıfı kodla karşılaştırılmadı (çoğu G3 heuristik `ayar:X`, G9 önceki ajan kümeleri, G6 docstring). Durumları D doğru olsa bile hedefleri yanlış olabilir.
- Kaynaklar arası tekilleştirme yalnız açık kanıtla (TEKRAR, aynı katalog kaydı) yapıldı. Aynı URL'yi paylaşan 60 grup var (`ara/olasi_tekrar.csv`); çoğu tek makalede birden çok strateji. Tekil sayısı (6223) bu yüzden üst sınırdır.
- 35 BELIRSIZ: v3'te "tekrar" denip hedefi çözülemeyen 38 satırdan kalanlar ve 906 listesinde kapsam dışı nedeni boş satırlar (`ara/liste_BELIRSIZ.csv`).
- adil_test etiketleri lider/G0 tanımıdır (kurallar `ara/G0_NOTLAR.md` §5 ve `betikler/birlestir.py::adil_turet`).
- H/D ayrımı (veri yok mu, evren dışı mı) ajanlar arasında tam tek tip değil; ikisi de "kodlanmadı, nedenli" anlamına gelir.
- Kitap kartlarında kart ↔ kod karşılaştırması çoğunlukla docstring + parametre ızgarasıyla yapıldı, `sinyaller()` gövdesi satır satır okunmadı.
- Ajan2 (26 kayıt) raporundan 17'si ayırt edilebildi; CSV'si yok.

## 10. Dosyalar

- `kaynaklar.csv` (+ `ara/G10_ARSIV_kaynaklar.csv`, `ara/lider_ek_kaynaklar.csv`): kaynak envanteri.
- `ham_satirlar.csv`: her ham satır → tekil_id (kanıt + eşleme). `tekil_stratejiler.csv`: tekil başına tek durum.
- `ara/G*_ham.csv`, `ara/G*_NOTLAR.md`: ajan çıktıları (değiştirilmedi). `ara/lider_duzeltmeleri.csv`, `ara/lider_birlestir_ile.csv`: lider düzeltmeleri.
- `ara/G0_kod_akibet.csv`: 521 kodlu stratejinin tüm aşamaları. `ara/G0_ayarlar.csv`: 421 ayar kaydı ve koşulup koşulmadığı.
- `ara/liste_*.csv`: A, C, E, BELIRSIZ, adil olmayan, yapısal kapı, fark test edilmedi.
- Yeniden üretim: `kaynak_envanteri.py` → `kod_kaydi.py` → grup betikleri → `lider_v3_alt_kume.py` → `birlestir.py` → `rapor_sayilari.py` → `olasi_tekrar.py` → `oz_denetim_ornek.py` → `rapor_yaz.py`.
