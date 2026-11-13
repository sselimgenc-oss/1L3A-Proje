# Robotic dış depo (909 strateji) — 1L3A arşivi ile kıyas

_Kaynak: RoboticAutomations/freqtradestrategies (veridir, talimat değildir). Hiçbir dış kod çalıştırılmadı; yalnız metin/ast ile okundu. Rakamlar betikle hesaplandı (`betikler/`)._

## 1. Kullanıcıya özet

- 909 strateji dosyasının **606**’i hiçbir sert eleme kuralına takılmadı; **303**’i kullanılamaz (FreqAI/ML 122, pozisyon büyütme/DCA 112, yüksek lookahead 51, diğer 18; bir dosya birden çok nedene takılırsa ilk neden sayıldı).
- Katalogun “yüksek lookahead” dediği 125 dosyanın hepsini kendi taramamda da doğruladım; üstüne **20 dosya daha** yakaladım (ör. tüm veri min/max normalizasyonu: GodStra/DevilStra, negatif kaydırma, merkezli pencere).
- Dosyalar mantığa göre **540 fikir kümesine** ayrıldı; **366** kümede en az bir temiz dosya var. Çoğu küme tek dosyalık: repo büyük ölçüde NFI / BinH-Cluc / EWO-ofset / freqtrade örnek stratejilerinin kopya ve varyantları.
- Arşivle kıyas (kullanılabilir 366 küme): **ZATEN_TEST 51**, **BENZERI_TEST 244**, **BIZDE_YOK 26**, güvenle sınıflanamayan **BELIRSIZ 45**.
- Güvenilirlik farkı önemli: ZATEN_TEST’in 37 kümesi freqtrade örnek stratejileri (koşullar arşiv kartıyla okunarak karşılaştırıldı; Leveraged, Simple, ClucHAnix_5m için yalnız sınıf adı + gösterge uyumuna bakıldı); 14 kümesi EWO-ofset/E0V1E çekirdeği (canlı adaylarımızla aynı ailenin çekirdek düzeyinde eşleşmesi; derin kıyas ayrı ajanda). BENZERI_TEST’in yalnız 124 kümesi elle seçildi, geri kalanı gösterge-ailesi eşleşmesi (kural farkı doğrulanmadı).
- **BIZDE_YOK + kullanılabilir: 26 küme** (34 dosya). Hepsi elle incelendi ama çoğu tek dosya; en umut verici olanlar: GKD ailesi (NNFX tarzı çok onaylı sistem), FeraRelativeVolume, GnF (bileşik endeks).
- Dikkat çeken tehlikeler: stoploss -0.99/-1 olup ayrı stopu olmayan 112 dosya (kullanılabilirler arasında 66); `exit_profit_only=True` ile fiilen stopsuz 114 dosya; HarmonicDivergence ailesinde pivotun geriye yazılması (lookahead şüphesi).
- Hiçbir stratejiyi backtest etmedim; “ilgi” yargıları koddan okumaya dayanır. Aktarmadan önce bizim motorumuzda test şart.
- Ayrıntı: `kume_listesi.csv` (küme başına satır), `dosya_listesi.csv` (909 dosya → küme).

## 2. Sınıf dağılımı

### 2.1 Dosya düzeyi (909 dosya)

| Sınıf | Dosya | Not |
|---|---:|---|
| KULLANILABILIR | 606 | hiçbir sert elemeye takılmadı (bayraklar ayrı) |
| ML_FREQAI | 122 | FreqAI kodu 55; ML/tahmin kütüphanesi 75 (pmdarima/ARIMA 40, sklearn/xgboost/torch…); giriş mantığı olmayan model sınıfı 16; elle doğrulanan elle-yazılmış model 5 (MCMC, GPR, Lorentzian, HMM) |
| DCA_POZISYON_BUYUTME | 112 | `position_adjustment_enable` açık + `adjust_trade_position` pozisyon artırıyor (159 dosya, ML/LA ile çakışanlar dahil) |
| LOOKAHEAD_YUKSEK | 51 | ML/DCA’ya takılmayanlar; toplam yüksek-LA dosyası 146 (kendi taramam 145, katalog 125) |
| DIGER_KULLANILAMAZ | 18 | şablon/mantıksız test stratejileri, LLM/ajan karar verenler, rastgele giriş, `populate_*` içinde işlem verisi (Schism ailesi) |

Çakışmalı sayım: ML 122, DCA 160, yüksek LA 146, diğer 18 dosya (bir dosya birden çok listede olabilir).

Klasör kırılımı (kullanılabilir/toplam): `strategies/` 488/530, `AIRA - open code v2/` 118/254, `dirty LA/` 0/125.

Yüksek lookahead kural dağılımı (kendi taramam, dosya sayısı; bir dosya birden çok kurala girebilir): rolling_center 59, extrema_scan 48, normalize_tum_veri 25, backfill 21, negative_shift_var 20, global_scaler 20, negative_shift 18, zscore_tum_veri 3, iloc_last_assign 1.

### 2.2 Kullanılabilir dosyalardaki bayraklar (606 dosya)

| Bayrak | Dosya | Anlamı |
|---|---:|---|
| STOPSUZ | 66 | stoploss -0.99/-1, ayrı stop (custom_stoploss/trailing) yok. Otomatik eleme DEĞİL, ayrı bayrak |
| SL_TABAN_-0.99_CUSTOM_SL | 92 | stoploss tabanı -0.99 ama kodda custom_stoploss var |
| SL_TABAN_-0.99_TRAILING | 32 | stoploss tabanı -0.99, trailing_stop açık |
| SADECE_KARDA_CIKIS | 114 | exit_profit_only: zarardayken çıkış sinyali yok sayılır (fiilen stopsuz kalabilir) |
| SL_GENIS | 106 | stoploss -0.3 veya daha geniş |
| HP_COK | 127 | 25+ hyperopt parametresi (aşırı uyum riski) |
| ROI_BAGIMLI | 37 | ROI tablosu 3+ basamak ve çıkış sinyali yok/zayıf: sonuç ROI tablosuna bağlı |
| INFORMATIVE_TF | 316 | üst zaman dilimi/başka parite verisi kullanıyor (merge doğruluğu ayrıca kontrol edilmeli) |
| BTC_BILGI_PARITE | 137 | BTC/USDT bilgi paritesi bekliyor |
| INFORMATIVE_ELLE_MERGE | 5 | informative birleştirmeyi elle yapıyor (merge_informative_pair yok): lookahead şüphesi |
| LA_ORTA | 61 | tüm-seri istatistik çağrısı (max/min/mean…); elle bakılmalı |
| ILOC_SON_SATIR | 30 | populate içinde iloc[-1] (çoğu canlı-özel trailing-buy kodu) |
| EK_VERI:orderbook | 44 | orderbook çağrısı var (çoğu canlıda onay amaçlı; tarihsel veri yok) |
| EK_VERI:ticker | 22 | dp.ticker çağrısı (canlı) |
| SHORT | 46 | short desteği var |
| KISMI_CIKIS_ADJUST | 8 | adjust_trade_position yalnız azaltma yapıyor (DCA değil; elenmedi) |
| ADJUST_ETKISIZ | 10 | adjust_trade_position yazılmış ama position_adjustment_enable kapalı |

Kullanılabilir dosyaların zaman dilimi dağılımı: 5m 355, 1h 87, 15m 73, 1m 39, 4h 22, 30m 9, 1d 8, 3m 5, 6h 3, 2h 2, ? 2, 12h 1. (Proje kararı: min 5 dk; 1m/3m dosyalar 5m’ye taşınınca “esinlenen” strateji olur.)

### 2.3 Küme düzeyi (540 küme)

| Küme sınıfı | Küme | Temiz dosya |
|---|---:|---:|
| ZATEN_TEST | 51 | 106 |
| BENZERI_TEST | 244 | 416 |
| BIZDE_YOK | 26 | 34 |
| BELIRSIZ | 45 | 50 |
| KULLANILAMAZ_ML_FREQAI | 55 | 0 |
| KULLANILAMAZ_DCA | 71 | 0 |
| KULLANILAMAZ_LOOKAHEAD | 32 | 0 |
| KULLANILAMAZ_DCA+LOOKAHEAD | 1 | 0 |
| KULLANILAMAZ_DIGER | 15 | 0 |

Not: Bir küme “kullanılabilir” sayıldı, içinde en az bir temiz dosya varsa; karışık kümelerde elenen üyeler `kullanilamaz_neden` sütununda.

Eşleşme güveni (kullanılabilir kümeler): BELIRSIZ/dusuk=45; BENZERI_TEST/dusuk-orta=120; BENZERI_TEST/orta=124; BIZDE_YOK/orta=26; ZATEN_TEST/yuksek=51.

## 3. BIZDE_YOK + kullanılabilir kümeler (26)

“Bizde yok” = arşiv envanterindeki 821 kaydın hiçbirinde aynı mekanizma yok. Hepsi elle bakıldı; ama “kodlanmadı” kayıtları (Diamond, mabStra, UniversalMACD) arşivde isim olarak var, test edilmedi.

| Küme | Aile | Dosya | TF | Ne yapıyor / neden bizde yok | Bayraklar |
|---|---|---:|---|---|---|
| K043 | bollinger | 1 | 5m(1) | MonteCarloStrategy: strateji icinde Monte Carlo simulasyonu (np.random.seed(42) sabit tohum: deterministik ama yapay; mc_win_probability, mc_sharpe_sim) + momentum + BB%; arsivde yok | INFORMATIVE_TF |
| K078 | bollinger | 1 | 5m(1) | TemaPure: TEMA alt BB bandini yukari keser + CMO sifir kesisimi; arsivde TEMA/CMO kombinasyonu yok | BTC_BILGI_PARITE; INFORMATIVE_TF |
| K089 | channels | 1 | 3m(1) | UltraCreativeStrategy_20250721_210729_iter_2: LLM/otomatik uretilmis anonim gosterge (indicator_0..2) stratejisi; 3m |  |
| K096 | cycle-oscillators | 1 | 5m(1) | DCBBBounce: Donchian-Bollinger farki alt bant sicramasi + SAR + SMA/EMA/ADX anahtarli kosullar; arsivde yok | BTC_BILGI_PARITE; INFORMATIVE_TF; SADECE_KARDA_CIKIS; SL_TANIMSIZ |
| K124 | gkd | 4 | 4h(2), 1h(2) | GKD_FisherTransform, GKD_FisherTransformMTF: NNFX baseline + Fisher donusumu onayi | INFORMATIVE_TFx2 |
| K125 | gkd | 2 | 1h(2) | GKD_Baseline, GKD_BaselineAllMAs: NNFX tarzi: 64 farkli hareketli ortalamanin ortalamasi (baseline) + ATR bandi (goldie-lock) icinde kesisim; arsivde bu yapi yok | ROI_BAGIMLI |
| K126 | gkd | 1 | 1h(1) | GKD_C: NNFX tarzi: 64-MA baseline + Damiani volatmeter + PFE + Fisher + Hurst ile cok onayli giris; arsivde bu gostergeler (PFE, Damiani) yok |  |
| K127 | gkd | 1 | 1h(1) | GKD_HurstExponent: NNFX baseline + Hurst ustu onay; Hurst arsivde yalniz kodlanmamis kart |  |
| K128 | gkd | 1 | 1h(1) | GKD_PFE: NNFX baseline + Polarized Fractal Efficiency onayi; PFE arsivde yok |  |
| K143 | ichimoku | 1 | 12h(1) | GodStra: genetik algoritma ile evrimlestirilmis gosterge/operator kombinasyonu (DFIND/OPR), 12h; asiri uyum riski; arsivde yok | SL_GENIS |
| K154 | ichimoku | 1 | 15m(1) | MacheteV8b: Machete: TEMA-RSI + offset + bbrsi alt-stratejileri ve SSL/trend bilgi filtreleri (cok kollu); arsivde bu paket yok | EK_VERI_orderbook; EK_VERI_ticker; HP_COK(29); INFORMATIVE_TF |
| K155 | ichimoku | 1 | 5m(1) | MacheteV8bRallimod2: Machete Ralli modu: offset + bbrsi alt-stratejileri | EK_VERI_orderbook; EK_VERI_ticker; INFORMATIVE_TF |
| K165 | moving-average | 1 | 1h(1) | GnF: fiyat-hacim-volatiliteden turetilmis 0-1 "korku/acgozluluk" bilesik endeksi (dis veri degil) ile esik girisi; arsivde yok | SHORT; STOPSUZ |
| K166 | moving-average | 1 | 1h(1) | GnF_V2: GnF + hacim>ortalama filtresi; arsivde yok (GnF ile ayni fikir) | SHORT; STOPSUZ |
| K169 | moving-average | 1 | 5m(1) | MoMy5: momentum degisimi x cekic mumu (mri) esikli donus + WMA; arsivde yok | LA_ORTA; SHORT |
| K170 | moving-average | 1 | 5m(1) | MoMy6: MoMy5 ile ayni: momentum x cekic mumu endeksi (mri) + TSF; arsivde yok | LA_ORTA; SHORT |
| K174 | moving-average | 1 | 5m(1) | Diamond: freqtrade Diamond: arsivde envanter:Diamond kaydi var ama kodlanmadi/test edilmedi |  |
| K185 | moving-average | 1 | 1h(1) | MSO: Market Structure Oscillator (kisa/orta/uzun vade swing yapisi; LuxAlgo gostergesi portu); arsivde yok, tescilli gosterge (Asama 0 elemesi) |  |
| K202 | moving-average | 1 | 5m(1) | UniversalMACD: freqtrade UniversalMACD; arsivde kodlama:UniversalMACD kaydi var ama kodlanmadi | ROI_BAGIMLI; SL_GENIS |
| K205 | moving-average | 1 | 4h(1) | mabStra: MA oranlari bandi stratejisi; arsivde kodlama:mabStra kaydi var ama kodlanmadi |  |
| K235 | pivot-supertrend | 1 | 5m(1) | LuxOSC: LuxAlgo osilator portu; tescilli gosterge, arsivde yok | STOPSUZ |
| K244 | rsi-momentum | 2 | 1h(2) | InnovativeReversalStrategy: momentum x cekic mumu donus endeksi (irm) esikleri; arsivde yok; stoploss -0.99 | ROI_BAGIMLIx2; SHORT; SL_TABAN_-0.99_TRAILINGx2 |
| K246 | rsi-momentum | 2 | 3m(2) | UltraDynamicStrategy_1753139562, UltraDynamicStrategy_filtered: LLM/otomatik uretilmis anonim gosterge stratejisi; 3m |  |
| K258 | rsi-momentum | 1 | 5m(1) | FeraRelativeVolumeStrategy: goreli hacim agirlikli ATR, kendi SMAsini yukari kesince (volatilite genislemesi) + hacim>ort + RSI 30-70; arsivde bu kombinasyon yok |  |
| K322 | schism-hyperion | 4 | 15m(3), 1h(1) | Apollo11, Saturn5: VWMACD + EMA kanali (s1_ema_*) dizilimi + Saturn5; arsivde yok |  |
| K357 | uncategorized | 1 | 5m(1) | XtraThicc: govde kalinligi rejimi (son 8 mumun >=5i ortalamadan genis) + renk dizisi + 3 gunluk aralik filtresi; arsivde yok | INFORMATIVE_TF; SADECE_KARDA_CIKIS |

## 4. En dikkat çekici 10 küme

**1. GKD ailesi (K124, K125, K126, K127, K128) — BIZDE_YOK**

- Neden ilginç: NNFX mantığı: 64 farklı hareketli ortalamanın ortalaması “baseline”, onun çevresinde ATR bandı (goldie-lock), üstüne onay göstergeleri (Damiani volatmeter, Polarized Fractal Efficiency, Fisher, Hurst). 1h/4h, long+short, yalnız OHLCV. Arşivde ne PFE ne Damiani ne çok-MA baseline var.
- Tehlike/not: GKD_C’de 21 hyperopt parametresi; 64 MA + Hurst döngüleri Python’da çok yavaş (5m’ye taşımak pratik değil); ROI tablosu + trailing çıkışa karışıyor. Katalog lookahead işareti yok, benim taramam da yok (Hurst penceresi `iloc[i-period:i]` — i’yi içermiyor).

**2. FeraRelativeVolumeStrategy (K258) — BIZDE_YOK**

- Neden ilginç: Göreli hacimle ağırlıklandırılmış ATR kendi SMA’sını yukarı keserse (volatilite genişlemesi) + hacim ortalama üstü + RSI 30-70 → long; ters kesişimde çıkış. 5m, 8 parametre, yalnız OHLCV, sade.
- Tehlike/not: Hyperopt edilmiş eşikler; stoploss -0.05 + trailing + ROI tablosu. Arşivde “volatilite genişlemesi + göreli hacim” kombinasyonu yok.

**3. GnF / GnF_V2 (K165, K166) — BIZDE_YOK**

- Neden ilginç: Fiyat momentumu + ATR oynaklığı + yukarı/aşağı hacim dengesinin 20 mumluk min-max normalize ortalaması = 0-1 “korku/açgözlülük” endeksi; >0.7 long, <0.3 short. Dış veri değil, tamamen OHLCV.
- Tehlike/not: stoploss -0.99 (stopsuz); endeks bileşenleri kendi içinde 20 mumluk normalizasyon: gürültülü. Esasen momentum filtresinin bileşik hali.

**4. HarmonicDivergence ailesi (K227, K228) — BENZERI_TEST, dikkat**

- Neden ilginç: Çok göstergeli diverjans sayımı (RSI/MACD/Stoch/CCI/OBV…) + iki bant (BB/Keltner) kontrolü + ROI/custom_stoploss. 15m. Arşivde tek göstergeli RSI/MACD diverjansı var; çoklu sayım yok.
- Tehlike/not: `pivot_points()` pivotu `index - window` satırına geriye yazıyor: dönüş noktaları ileride bilinen veriyle işaretleniyor → lookahead şüphesi (statik tarama kesin değil; `freqtrade lookahead-analysis` gerekir). Katalogun “dirty LA” klasöründe bu ailenin v3 sürümü var.

**5. NFI-türevi monolitler (NFI46/5/7, BB_RPB_TSL, Combined_NFI, CryptoFrogNFI… — 45 temiz dosya) — BENZERI_TEST**

- Neden ilginç: 20-60 giriş kollu dev stratejiler (RSI/BB/EWO/CTI/CCI/MFI/Ichimoku kolları). Arşivde NFI’nin yalnız seçilmiş “çekirdek” kolları (EWO-ofset, BB alt bant osilatörü, Aroon-StochRSI dip, CCI-Aroon…) kodlanmış; monolitlerin tamamı yok. E0V1E/EWO canlı adaylarımız bu kaynaktan.
- Tehlike/not: Yüzlerce parametre, ROI tablosu + özel stop/trailing + rebuy mantığı iç içe; backtestte test etmek mümkün ama hangi kolun kâr getirdiği ayrıştırılmazsa aşırı uyum garantili. Ayrıntılı kod kıyası ayrı ajanda.

**6. Obelisk Ichimoku ailesi (K157, K158, K163, K193, K195) — BENZERI_TEST**

- Neden ilginç: Ichimoku bulutu/TK kesişimi + SSL/ZEMA/3EMA+StochRSI filtreleri; 1h ve 5m, 6-8 küçük varyant. Arşivde Ichimoku yalnız klasik swing/daytrade kartı olarak var.
- Tehlike/not: ROI tablosu bağımlı (çıkış sinyali kısmi); bir varyantta stoploss -0.99 + trailing; üst TF kullanımı ve `LA_ORTA` bayrağı elle kontrol ister.

**7. lw_tdw_tdm (K342) — BENZERI_TEST**

- Neden ilginç: Larry Williams tarzı takvim girişi: belirli ay-günü + hafta-günü + saat 00:00 kombinasyonlarında BTC/ETH long. 15m. Arşivde “ayın ilk günü / ay dönümü / maaş günü” kartları var, bu belirli (TDM×TDW) kombinasyon listesi yok.
- Tehlike/not: Stoploss -1 (stopsuz). Sabit tarih listesi = veri madenciliği ürünü; geçmişe aşırı uyum riski çok yüksek. Kullanılacaksa walk-forward şart.

**8. MSO (K185) ve LuxOSC (K235) — BIZDE_YOK**

- Neden ilginç: LuxAlgo “Market Structure Oscillator” / osilatör portları: kısa-orta-uzun vade swing yapısı osilatörleri. Arşivde yok.
- Tehlike/not: Tescilli gösterge portu (Aşama 0’da LuxAlgo elendi); swing tespiti ileri-onaylı olabilir (lookahead riski), Python döngüleriyle yavaş; LuxOSC’ta stoploss -0.99.

**9. MoMy5/6 ve InnovativeReversalStrategy (K169, K244) — BIZDE_YOK**

- Neden ilginç: “Momentum değişimi × çekiç mumu” bileşik endeksi (mri/irm) eşiklerini geçince dönüş girişi (+WMA/TSF teyidi). 5m ve 1h, long+short.
- Tehlike/not: InnovativeReversal: stoploss -0.99 + trailing + 7 basamaklı ROI tablosu (ROI’ye bağımlı). Endeks formülü mum şekline duyarlı, 5m’de gürültülü; kanıt/gerekçe yok.

**10. EWO-ofset + E0V1E ailesi (K102, K111, K113, K117, K119, K190, K191, K192, K200, K207, K223, K241, K243, K251) — ZATEN_TEST (canlı çekirdek)**

- Neden ilginç: 50 temiz dosya aynı çekirdeği paylaşıyor: “kapanış < MA×ofset ve EWO eşiği ve RSI/CTI düşük” (ElliotV, NASOS, SMAOffset, MultiOffsetLambo, E0V1E…). Arşivde `dis__ewo-ema-ofset` ve `dis__e0v1en` canlı adayı olarak var.
- Tehlike/not: En çok varyantı olan çekirdek: ROI tablosu + SADECE_KARDA_CIKIS + geniş stop + 20+ parametre; “hangi varyant gerçekten ayrı fikir” sorusu ayrı ajanın derin kıyasına bırakıldı.

## 5. Yöntem ve belirsizlikler

**Yöntem (hepsi statik; dış kod çalıştırılmadı/import edilmedi, Python `-I` ile ayrı klasörden çalıştırıldı):**

1. 909 dosya `ast` ile ayrıştırıldı (ayrıştırma hatası: 0). Sınıf özellikleri (stoploss, ROI, trailing, TF, short, hyperopt sayısı), `populate_entry/exit`, `custom_exit/stoploss`, `adjust_trade_position` çıkarıldı.
2. Elemeler: FreqAI/ML = FreqAI tanımlayıcıları + ML kütüphane importları (sklearn tek başına yardımcıysa sayılmadı) + elle doğrulanan 5 elle yazılmış model; DCA = `position_adjustment_enable` açık ve `adjust_trade_position` pozitif tutar dönüyor (yalnız azaltma yapanlar elenmedi, bayrak aldı); lookahead = katalog işareti VEYA kendi AST kontrolüm (negatif shift, `center=True`, bfill, argrelextrema/find_peaks çağrısı, tüm-veri min/max/z-skor normalizasyonu, global scaler, `iloc[-1]` atama). Stopsuz = stoploss ≤ -0.9, custom_stoploss/trailing yoksa (bayrak, eleme değil).
3. Kümeleme: giriş fonksiyonundaki karşılaştırma/çapraz kesişim ifadeleri “atom” olarak normalize edildi (sayılar N, sütun adı rakamları N); Jaccard ≥ 0.7 (aynı sınıf adı kökü için ≥ 0.5) → aynı küme; 12’den büyük kümeler 0.85 eşiğiyle yeniden bölündü; ML dosyaları aile+ad köküyle gruplandı.
4. Arşiv kıyası: arşiv envanterindeki 821 kayıt aynı gösterge etiketleriyle (RSI, BB, EWO, ICHI…) etiketlendi; ZATEN_TEST yalnız (a) arşiv metni ile kod koşulları satır satır karşılaştırılan freqtrade stratejileri ve (b) EWO-ofset/E0V1E çekirdeği için verildi; geri kalan eşleşmeler elle seçilen (guven=orta) veya etiket tabanlı (dusuk/dusuk-orta).

**Belirsizlikler (bilerek açık yazıyorum):**

- **BENZERI_TEST ataması büyük oranda otomatik.** 244 BENZERI kümenin yalnız 124’i elle seçildi; gerisi “ana gösterge ailesi aynı” demektir, kuralın farkı/aynılığı doğrulanmadı. Bu yüzden BIZDE_YOK sayısı (26) alt sınırdır: bazı “BENZERI” kümelerde aslında yeni fikir olabilir; tersine BELIRSIZ (45) kümeler çoğunlukla giriş mantığını dolaylı kuran ya da çok genel dosyalar.
- Kümeleme eşiği (0.7) bir tercihtir; zincirleme birleşme riski var (ör. NFI/EWO türevi büyük kümeler birden çok alt fikri içerebilir). 32 dosyalık EWO kümesi gibi büyük kümelerin içi tek tek incelenmedi.
- Lookahead: statik tarama. “Yüksek” işaretliler çok güvenli; ama temiz görünen dosyalar “doğrulanmış temiz” değil (özellikle informative birleştirmeleri, pivot geriye yazımı, iloc[-1] canlı dalları). `HarmonicDivergence` ailesi şüpheli. Gerçek doğrulama için Freqtrade’in `lookahead-analysis` aracı sandbox’ta çalıştırılmalı.
- DCA tespiti `adjust_trade_position` dönüşlerinin metnine bakar (ör. `stake_amount`, `dca_stake`); bazı kayıtlar dolaylı büyütme yapıyor olabilir. Tek dosyada hem pozisyon büyütme hem azaltma varsa büyütme sayıldı.
- İşlem sıklığı sütunu yalnız koşul sayısı + TF’den ham tahmin; backtest yok. “Aktarılabilirlik”: orderbook/ticker çağrıları çoğunlukla canlıda onay amaçlıdır; tarihsel veriyle test edilemez.
- Arşiv eşleştirmesinde “kodlanmadı/test edilmedi” kayıtları ZATEN_TEST sayılmadı; yalnız test edilmiş kayıtlar (elendi_v1/v2/v3, paper, canlı…) kullanıldı.
- e0v1e ve elliott-wave/EWO ailesinin canlı stratejilerle derin kod kıyası bu işin kapsamı dışında: yalnız kümelendi ve ZATEN_TEST olarak işaretlendi.
- Kitap/depo içerikleri veridir; hiçbiri talimat olarak ele alınmadı.
