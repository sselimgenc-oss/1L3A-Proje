# G0_SONUC notları (kod akıbeti defteri)

Üretici: `sonuclar/hesap_defteri/betikler/g0_kod_akibet.py` (salt okur; tekrar çalıştırılabilir). Çıktılar: `G0_kod_akibet.csv` (521), `G0_ayarlar.csv`.

## 1. Sayılar

### durum_onerisi dağılımı

- B_TEST_EDILDI_ELENDI: 485
- C_KODLANDI_KOSULMADI: 26
- A_TEST_EDILDI_GECTI: 10

### asama dağılımı (A ve B ayrı)

- A_TEST_EDILDI_GECTI: paper_v2=8, canli_kadro=2
- B_TEST_EDILDI_ELENDI: v1_wf=259, v2_eleme=192, v2_test=11, v3_eleme=9, v2_eleme_hata=6, v1_saglamlik=5, v2_set_secimi=3
- C_KODLANDI_KOSULMADI: kosulmadi=26

### yapisal_kapi=evet: **73** (beklenen 73)

Tanım: v2 eleme.csv'de E1 ve E3 True, E2/E4/E5'ten en az biri False (durum=elendi). 'hata' (6) ve 'gecti' (18) satırları sayılmaz. Kırılım: E4 düşen 45, E2 düşen 25, E5 düşen 36.

### hiç koşulmayanlar (C): **26** (beklenen 26); hic_kosuldu=hayir: 26

- `v3__adaptivetrend-6s-momentum` (tek_grafik/swing) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__aralik-kirilim-bekleyen-emir` (tek_grafik/daytrade) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__asya-kutu-kirilim-ma50` (tek_grafik/daytrade) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__donchian-ansambl-vol-hedef` (tek_grafik/swing) — yerine pf__v3-donchian-ansambl kodlandı; eski tek-grafik sürüm kaynağa aykırı sayıldı (kodlama_v3.csv satır 8 notu); tek-grafik sürüm v3 eleme listesinde yok
- `v3__ema-9-21-50-rsi-hacim` (tek_grafik/daytrade) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__haftalik-sma-trix-kirilim` (tek_grafik/swing) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__kirmizi-mum-2x-hacim` (tek_grafik/swing) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__l-sekli-ma-kirilim-long` (tek_grafik/daytrade) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__londra-volatilite-kirilim` (tek_grafik/daytrade) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__momentum-sifir-kesisim` (tek_grafik/swing) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__orb-4s-hacim-atr` (tek_grafik/daytrade) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__pazartesi-dip-endeks` (tek_grafik/swing) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__rsi14-ema200-izleyen-stop` (tek_grafik/swing) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__rsi2-sma200-hacim` (tek_grafik/swing) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__rsi30-hacim-ema200` (tek_grafik/swing) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__rsi32-yon-hedef4` (tek_grafik/daytrade) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__saat-21-23-utc` (tek_grafik/daytrade) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__saatlik-asiri-tepki` (tek_grafik/daytrade) — aile temsilcisi değil + birincil metin okunana dek bekletildi (ON_KAYIT_V3 0.4: 'saatlik-asiri-tepki birincil metin okunamadığı için bu turda yok'; DURUM.md 2026-11-11 'saatlik-aşırı-tepki birincil me
- `v3__sma-trend-rsi-atr` (tek_grafik/daytrade) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__ters-fvg-nq-long` (tek_grafik/daytrade) — koşulamadı: veri yok — NQ verisi yok; mevcut DK hisse verisi 1h ve NQ sabit puanları ile 5m New York seans kuralını karşılamıyor; kod ileride uygun veri için korunuyor
- `v3__volatilite-kirilim-k05` (tek_grafik/swing) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__yarim-fitil` (tek_grafik/daytrade) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `v3__z-skor-karsit` (tek_grafik/swing) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `pf__v3-funding-1s-devam` (portfoy/portfoy) — koşulamadı: altyapı yok — Saatlik veri ve funding_orani gerekir; portföy araştırma hattı yalnız 1d çalıştığı için ölçülemez
- `pf__v3-funding-kesit-decil-carry` (portfoy/portfoy) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis
- `pf__v3-funding-z90-3gun` (portfoy/portfoy) — aile temsilcisi değil: v3 test bütçesi yalnız 9-10 aile temsilcisi; aynı ailenin diğer kodlu varyantları bu turda koşulmaz (ON_KAYIT_V3 0.4, DURUM.md 2026-11-11 'Test bütçesi: yalnız 10 aile temsilcis

### v1 evren zincirinde olup v2 havuzunda olmayan: 264 / v1'de olan 479 (v2 havuzu 222)

- stil v2 dışı (daytrade/scalp): 208
- stil v2 dışı (daytrade/scalp) + swing__ klonu havuzda: 46
- stil v2 dışı (daytrade/scalp) + swing__ karşılığı yok: 9
- küme temsilcisi değil (2.7): 1

v1 WF'de (g1/g2) kalma, v2 havuzuna girişin ÖLÇÜTÜ DEĞİLDİR: `araclar/havuz_v2_olustur.py::aday_satirlari` yalnız stil, klon kuralı, kümeleme ve etiketlere bakar. v1 sonuçları yalnız 2.7(b) kümelemesinde haftalık OOS serisi olarak kullanılır.

### havuzda olmayıp kod_kaydi'nda olan (v1'de olmayanlar dahil) toplam

- stil v2 dışı (daytrade/scalp): 208
- stil v2 dışı (daytrade/scalp) + swing__ klonu havuzda: 46
- havuz sonrası eklendi: 35
- stil v2 dışı (daytrade/scalp) + swing__ karşılığı yok: 9
- küme temsilcisi değil (2.7): 1

### v2 aşamaları (kod_kaydi'ndaki strateji sayısı)

- v2 eleme: gecti 18, elendi 198, hata 6
- v2 keşif (BH): 7; sağlamlık satırı: 7 (saglam=True 5); sete girdi: 2; paper_v2: 10; canlı: 2; paper(hma/lube dahil): 2

### adil_test_onerisi etiket sayıları (B satırlarında; bir satır birden çok etiket taşıyabilir)

- evet: 62
- zayif_temsilci: 1
- yalniz_tek_TF: 95
- yalniz_varsayilan_ayar: 190
- yapisal_kapi: 67
- kisa_veri: 14
- hiç etiket almayan B: 279

## 2. Ayarlar (G0_ayarlar.csv)

- Satır: 421 (kart 226, dis 177, d11j 11, d12b 7)
- v1_aday_havuzunda=evet, kosuldu_mu=evet_aday: 129
- v1_aday_havuzunda=evet, kosuldu_mu=evet_secildi: 202
- v1_aday_havuzunda=evet_esdeger, kosuldu_mu=evet_aday: 54
- v1_aday_havuzunda=evet_esdeger, kosuldu_mu=evet_secildi: 18
- v1_aday_havuzunda=hayir, kosuldu_mu=hayir: 18
- v1_en_sik_ayar_mi=evet: 152; v2_secilen_ayar_mi=evet: 45

## 3. Öz kontrol: rastgele 10 satırın kaynağa geri izlenmesi (tohum 20261113)

- `dis__ha-guclu-dusus-al` → B_TEST_EDILDI_ELENDI/v2_eleme: sonuclar/evren/2017_gelistirme/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/2017_gelistirme/arsiv_g7_oncesi/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/meta_test/secilenler.csv:4/4 satırda id görüldü; stratejiler/havuz_v2.csv:1/1 satırda id görüldü; sonuclar/evren/v2/eleme.csv:1/1 satırda id görüldü; sonuclar/evren/v2/test.csv:1/1 satırda id görüldü
- `daytrade__pivot-seviye` → B_TEST_EDILDI_ELENDI/v1_wf: sonuclar/tarama/k2_ana_ozet.csv:1/1 satırda id görüldü; sonuclar/tarama/k2_izgara_ozet.csv:1/1 satırda id görüldü; sonuclar/wf/k3_kripto.csv:4/4 satırda id görüldü; sonuclar/wf/k3_dk.csv:4/4 satırda id görüldü; sonuclar/wf/k3_dk_v2.csv:4/4 satırda id görüldü; sonuclar/wf/k3_hisse_kisa.csv:4/4 satırda id görüldü; sonuclar/evren/2017_gelistirme/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/2017_gelistirme/arsiv_g7_oncesi/wf_evren.csv:2/2 satırda id görüldü
- `dis__fraktal-alligator-sky` → B_TEST_EDILDI_ELENDI/v2_eleme: sonuclar/tarama/k2_ana_ozet.csv:1/1 satırda id görüldü; sonuclar/tarama/k2_izgara_ozet.csv:1/1 satırda id görüldü; sonuclar/wf/k3_kripto.csv:4/4 satırda id görüldü; sonuclar/wf/k3_dk.csv:4/4 satırda id görüldü; sonuclar/wf/k3_dk_v2.csv:4/4 satırda id görüldü; sonuclar/saglamlik/k3_dk.csv:4/4 satırda id görüldü; sonuclar/saglamlik/k3_dk_v2.csv:4/4 satırda id görüldü; sonuclar/final_aday_havuzu_tek_grafik.csv:4/4 satırda id görüldü; sonuclar/secim/adaylar.csv:4/4 satırda id görüldü; sonuclar/secim/oneri.csv:1/1 satırda id görüldü; sonuclar/kilit/sonuc.csv:4/4 satırda id görüldü; sonuclar/evren/2017_gelistirme/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/2017_gelistirme/arsiv_g7_oncesi/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/meta_test/secilenler.csv:4/4 satırda id görüldü; stratejiler/havuz_v2.csv:1/1 satırda id görüldü; sonuclar/evren/v2/eleme.csv:1/1 satırda id görüldü; sonuclar/evren/v2/test.csv:1/1 satırda id görüldü
- `dis__vwap-reclaim` → B_TEST_EDILDI_ELENDI/v1_wf: sonuclar/evren/2017_gelistirme/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/2017_gelistirme/arsiv_g7_oncesi/wf_evren.csv:2/2 satırda id görüldü
- `daytrade__gap-devam` → B_TEST_EDILDI_ELENDI/v1_wf: sonuclar/tarama/k2_ana_ozet.csv:1/1 satırda id görüldü; sonuclar/tarama/k2_izgara_ozet.csv:1/1 satırda id görüldü; sonuclar/wf/k3_kripto.csv:4/4 satırda id görüldü; sonuclar/wf/k3_dk.csv:4/4 satırda id görüldü; sonuclar/wf/k3_dk_v2.csv:4/4 satırda id görüldü; sonuclar/wf/k3_hisse_kisa.csv:4/4 satırda id görüldü; sonuclar/saglamlik/k3_dk.csv:1/1 satırda id görüldü; sonuclar/saglamlik/k3_dk_v2.csv:1/1 satırda id görüldü; sonuclar/saglamlik/k3_hisse_kisa.csv:2/2 satırda id görüldü; sonuclar/kilit/sonuc.csv:3/3 satırda id görüldü; sonuclar/evren/2017_gelistirme/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/2017_gelistirme/arsiv_g7_oncesi/wf_evren.csv:2/2 satırda id görüldü
- `v3__btc-gecelik-max10-hafta-sonu` → B_TEST_EDILDI_ELENDI/v3_eleme: sonuclar/v3/eleme.csv:1/1 satırda id görüldü; stratejiler/v3_adaylar/kodlama_v3.csv:1/1 satırda id görüldü
- `dis__bolge-akis-sr` → B_TEST_EDILDI_ELENDI/v1_wf: sonuclar/evren/2017_gelistirme/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/2017_gelistirme/arsiv_g7_oncesi/wf_evren.csv:2/2 satırda id görüldü
- `dis__fraktal-ok-girisi` → B_TEST_EDILDI_ELENDI/v1_wf: sonuclar/evren/2017_gelistirme/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/2017_gelistirme/arsiv_g7_oncesi/wf_evren.csv:2/2 satırda id görüldü
- `dis__cok-osilator-ekstrem` → B_TEST_EDILDI_ELENDI/v1_wf: sonuclar/evren/2017_gelistirme/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/2017_gelistirme/arsiv_scalp4/wf_scalp4.csv:2/2 satırda id görüldü
- `dis__aroon-uc-deger` → B_TEST_EDILDI_ELENDI/v1_wf: sonuclar/evren/2017_gelistirme/wf_evren.csv:2/2 satırda id görüldü; sonuclar/evren/2017_gelistirme/arsiv_g7_oncesi/wf_evren.csv:2/2 satırda id görüldü

## 4. Kullanılan dosyalar ve sütun anlamları (kanıt: `kanit` sütununda `yol:satır` = dosyadaki fiziksel satır, başlık=1)
- `sonuclar/tarama/k2_ana_ozet.csv`, `k2_izgara_ozet.csv` (192 strateji): satir_sayisi, medyan_pf, umutsuz (K2 geniş tarama özeti; geçti/kaldı kararı YOK, yalnız bilgi). Örnek satır: k2_ana_ozet.csv:2.
- `sonuclar/wf/*.csv` (k3_kripto 3 sembol; k3_dk ve k3_dk_v2 10 DK sembol; k3_hisse_kisa; son1ay_k3_kripto): strateji×sembol×tf; `gecti` = karar 13 kapısı; `nedenler`. k3_dk ile k3_dk_v2 aynı 3180 görev (v2 sonradan yeniden koşu); ikisi de raporlandı, aşama kaydı "any gecti".
- `sonuclar/saglamlik/*.csv`: `saglam_mi` (K1 maliyet×2 PF≥1.05, K2 rnd_p≤0.05, K3 boot alt>1, K4 komşu≥%60), `kapi_basarisiz`.
- `sonuclar/wf_portfoy/*.csv`, `saglamlik_portfoy/*.csv` (parça klasörlerine girilmedi): pf__ için `gecti`/`atlandi`, `saglam_mi`.
- `final_aday_havuzu_tek_grafik.csv`, `secim/adaylar.csv`, `secim/oneri.csv`, `stratejiler/final_set.json` (v1 final 7; karar 27 ile paper'dan kaldırıldı, DURUM.md satır 371), `kilit/sonuc.csv` (gruplar A/B/C/D, `gecti`, `neden`; A seti birlikte GEÇTİ ama 4/7 tek tek kaldı: kilit/RAPOR.md).
- `evren/2017_gelistirme/wf_evren.csv` (939 satır = 479 strateji × tf): g1 (kârlılık: net, PF≥1.2, ≥100 işlem, pf5≥0.9, Sharpe≥0.5, DD≤0.2), g2 (genişlik: kârlı enstrüman ≥%50, tek enstrüman ≤%40, ≥2 sınıf), `gecti`, `nedenler` (kısaltmalar: pf5=en iyi %5 hariç PF, DD, karli_enstr, tek_enstr_pay, karli_sinif; "=NA" hesaplanamadı). 39 satır geçti. `saglamlik.csv` 58 satır, hepsi saglam_mi=False. `secim.csv`, `iyi_liste.csv`, `iyiye_yakin_liste.csv` 0 satır. `arsiv_*`: yalnız v1_arsiv sütunu ve hic_kosuldu.
- `stratejiler/havuz_v2.csv` (222), `evren/v2/eleme.csv` (E1-E5, ON_KAYIT_V2 §4; 198 elendi, 18 gecti, 6 hata), `test.csv` (K2 p, BH keşif; 7 keşif), `saglamlik.csv` (S1-S4; 7 satır, 5 saglam_kesif, 2 izleme), `set.csv` (2), `set_ozet.json` ("atlanan" nedenleri), `holdout/holdout.csv` (set, 2 kaldı), `holdout_kesif/holdout_kesif.csv` (55; kanıt değil), `stratejiler/paper_v2_seti.json` (10), `canli_ayar.ornek.json` + `CANLI_PLAN_V2.md` (canlı: ewo-ema-ofset, e0v1en; paper'da bekleyen: hma-atr-rider, lube).
- v2 havuz dışı nedeni `araclar/havuz_v2_olustur.py::aday_satirlari` mantığından türetildi (stil → 2.2/2.5, klon kuralı 2.3, kümeleme 2.7: havuz satırlarının `not` alanındaki `kume_uyeleri_havuz_disi`). Doğrulama: havuzda olmayan 299 stratejinin hepsi bir kurala bağlandı (BELIRSIZ 0).
- v2 sonrası: `meta_test/secilenler.csv`, `yeni_sembol/sonuc_strateji.csv`, `teshis/*/sonuc.csv`: yalnız bilgi sütunu (sonrasi_testler); durum/aşamayı değiştirmez. `portfoy_boyutu/` strateji bazlı satır içermez (atlandı).
- v3: `v3/eleme.csv` (9 satır, hepsi elendi), `v3_adaylar/kodlama_v3.csv` (koşulmayanların nedeni; kod_kaydi'ndaki 35 v3 adından 34'ü satırda var; eksik `v3__donchian-ansambl-vol-hedef` pf sürümüyle değiştirilmiş), ON_KAYIT_V3 §0.4, DURUM.md 2026-11-11.
- Haiku Ar-Ge (kopya): wf/*.csv + saglamlik/*.csv; 120 elenen strateji 5 enstrümanda; yalnız `haiku_arge` sütunu, durumu etkilemez. Kanıt yolu `dal:claude/haiku-arge-5-enstruman:...`.

## 5. Kurallar (betikteki tanımlar)
- Aşama sırası (kronolojik): k3_wf < k3_saglamlik < v1_final < kilit_k4 < v1_wf < v1_saglamlik < v2_eleme < v2_test < v2_saglamlik < v2_set < v2_holdout < paper_v2 < canli_kadro < v3_eleme. Durum = en son aşamanın sonucu. A = son aşama geçti ya da paper/canlı kadro; C = hiçbir sonuç dosyasında satır yok.
- v2'de elenip holdout keşfiyle paper'a alınanlar A/paper_v2 (not: "keşif yolu (kanıt değil)"): jt-awesome, uc-ortalama-boga-sma60, sabit_sepet, haftalik-macd (v2'de sağlamlık izleme), e0v1en (izleme), lube, hma-atr-rider, voltarget. gauss-stoch-eth ve ewo-ema-ofset resmi holdout'tan geçti.
- v2 `hata` (6 satır: 4 "1d üst TF olarak kullanılamaz", 2 pf "uygun değil") B/`v2_eleme_hata` yazıldı; gerçekte sınanmadılar: lider isterse C benzeri ele alsın.
- adil_test_onerisi etiketleri (betik tanımı, lider onayına tabi): `evet` = v2'de tek kapıdan düştü / v2 elemeyi geçip test-sağlamlık-set'te düştü / v2 teknik hata; `zayif_temsilci` = küme (2.7) temsilcisi (ya da üyesi) elendi, kümedeki diğer üyeler hiç koşulmadı; `yalniz_tek_TF` = v2 tek TF koştu, v1'de diğer TF'de gecti ya da PF≥1.2 ya da PF 0.1+ yüksek; `yalniz_varsayilan_ayar` = v2 varsayılan, v1 WF en sık seçilen ayar farklı (n_aday>1); `yapisal_kapi` = E1 ve E3 geçti, yalnız E2/E4/E5 düştü; `kisa_veri` = E1 geçti ama n<100, ya da v3'te kısa eleme dönemi. daytrade/scalp (v2 dışı) satırlarında v1 dışında test olmadığı için yalnız v1 gerekçesi var; adil_test etiketi çoğunlukla boş.
- G0_ayarlar: v1_aday_havuzunda = `wf_tarama.aday_listesi(ad, True)` etiketi (v1 evren WF n_aday ile 460/460 strateji için güncel sayı eşleşti = havuz doğrulandı); `evet_esdeger` = etkin parametre+çıkış başka adayla aynı olduğu için tekilleştirildi. K3 erken koşuda 21 stratejide n_aday farklı (ayarlar sonradan eklenmiş). d11j/d12b (18 ayar): hiçbir araştırma kodu okumaz (yalnız testler/test_d11j_modlar.py, test_d12b_151.py); wf_evren.csv'de 'd11j:'/'d12b:' etiketi yok (en_sik_ayar ve secimler tarandı); pf için aday kümesi = baglama.BAGLAMA + varsayilan + ızgara (lider doğruladı).

## 6. Belirsizlikler
- 2.7(b) küme kararının korelasyon değeri doğrulanamadı: `oos/*.parquet` repoda yok. Yalnız 1 swing strateji küme üyesi olarak elendi (diğer ~255 v2 dışı strateji stil/klon/havuz-sonrası nedenli).
- k3_kripto sağlamlık dosyasında 15 saglam_mi=True var (DURUM'daki "13" ile fark: dosya sonradan yenilenmiş olabilir); satır bazlı raporlandı.
- yapisal_kapi sayısı 73 tuttu. yalniz_tek_TF / yalniz_varsayilan_ayar eşikleri benim tanımım (yukarıda).
- hic_kosuldu: meta_test gibi yöntem-testi dosyalarındaki satırlar da "koşuldu" sayıldı (hepsi zaten v2 havuzunda).
