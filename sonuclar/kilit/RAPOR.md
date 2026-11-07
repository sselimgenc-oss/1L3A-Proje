# Kilitli dönem testi — sonuç raporu

Kilitli dönem: 2025-11-01 -> veri sonu. Yöntem ve ölçütler `ON_KAYIT.md`'de koşudan önce sabitlendi; sonuçlara bakılarak hiçbir şey değiştirilmedi.

Kilit açılış kaydı: `sonuclar/kilit_acilis.jsonl` (505 satır; her veri okuması + başlangıç kaydı). Gerekçe: "Katman 4 kilitli dönem testi, ON_KAYIT.md, kullanıcı onayı 2026-11-07".

## Kısa özet (sade)

- A grubu (final set, 7 aday): 3 tanesi tek tek ölçütü geçti (net > 0 ve PF >= 1.0), 4 tanesi kaldı.
- Set (tek kasa, sert limitler, portföy kolu %50/%50): **GEÇTİ**.
- B grubu: 6 satırın 3 tanesi geçti (50.0%).
- C grubu: 55 satırın 15 tanesi geçti (27.3%).
- D grubu: 267 satırın 90 tanesi geçti (33.7%).
- Elemelerimiz ayırt ediyor mu? Tek-grafikte C'nin medyan işlem başı R'si -0.107, D'ninki -0.054 -> ölçüt (C > D): **SAĞLANMADI**. Portföyde medyan Sharpe C 0.35 (n=4), D -0.18 (n=11).
- Walk-forward PF ile kilitli PF arasındaki Spearman korelasyonu: -0.095 (n=306); 0'a yakınsa walk-forward başarısı kilitli dönemi öngörmemiş demektir.
- ON_KAYIT 'sonuca göre': A seti ölçütü geçti -> Aşama 3 (Pano) ve Aşama 4 (paper trading) bu setle başlar.

## Dürüstlük notları

- Ayar seçimi kilit KAPALIYKEN, yalnız 2025-11-01 öncesi veriyle yapıldı (`secilen_ayarlar.csv`, `gruplar.csv` kilit açılmadan önce yazıldı).
- Her aşama bir kez koşuldu; sonuç görüldükten sonra yöntem/ölçüt/liste değişmedi, kod hatası yüzünden yeniden koşu olmadı.
- Gruplar örtüşür (A ve B, C'nin alt kümesidir). D-portföy tanımı ON_KAYIT'ta açık değildi; koşudan önce 'sağlamlıktan kalan portföy satırları' olarak belirlendi (modül belgesi).
- Araştırma modu motoru (walk-forward ile aynı): günlük -%3 ve %20 kill switch işlemi durdurmaz. Portföy kollarının max düşüşü bu yüzden %20'yi aşabilir (bkz. tablo); set testinde sert limitler yeniden oynatıcıyla uygulandı.
- Örneklem küçük: A kollarında 12-55 işlem; tek yıllık tek dönem. Sonuç kesin hüküm değil, bir tanık.

## Set sonucu (A grubu, tek kasa, sert limitler)

**Karar: GECTI** (ölçüt: net > 0, max düşüş <= %20, Sharpe > 0)

| kol | net | Sharpe | max düşüş | gün |
|---|---|---|---|---|
| tek_grafik | 17.8% | 1.21 | 8.0% | 370 |
| portfoy | -2.8% | -0.26 | 11.8% | 362 |
| set_harman_50_50 | 7.2% | 0.85 | 4.2% | 362 |

## A grubu (final set)

| strateji | sembol | tf | seçilen ayar | işlem | net | PF | max düşüş | WF PF | WF net | al-tut | ölçüt |
|---|---|---|---|---|---|---|---|---|---|---|---|
| pf__kanarya | hisse_emtia | 1d | csv:4 | 33 | 4.9% | 0.68 | 15.2% | 2.80 | 198.3% | 12.0% | kaldi (PF < 1.0) |
| pf__kesit_ls | kripto | 1d | izgara:{"k": 1, "lookback_gun": 14, "tak | 24 | 1.1% | 1.15 | 6.5% | 1.21 | 51.7% | -37.5% | gecti |
| pf__rotasyon | hepsi | 1d | izgara:{"k": 2, "lookback_gun": 30, "tak | 47 | -13.7% | 0.57 | 25.4% | 1.77 | 224.2% | -0.7% | kaldi (net <= 0) |
| dis__dual-thrust | ETHUSDT | 30m | izgara:{"k1": 0.7, "n": 5, "stop_atr_k": | 55 | 13.4% | 1.86 | 3.5% | 1.46 | 41.7% | -41.8% | gecti |
| dis__fraktal-alligator-sky | DK_NVDA | 4h | izgara:{"atr_esik": 50.0, "atr_ort": 3,  | 12 | -3.8% | 0.59 | 4.7% | 4.85 | 138.5% | -1.5% | kaldi (net <= 0) |
| swing__cci-esik | SOLUSDT | 1d | izgara:{"cci_periyot": 5, "mod": "lamber | 53 | 10.0% | 2.47 | 2.7% | 2.16 | 14.2% | -52.3% | gecti |
| swing__konsolidasyon-kirilim | SOLUSDT | 4h | izgara:{"hacim_k": 0.0, "tampon_atr": 0. | 14 | -0.6% | 0.90 | 4.0% | 1.64 | 16.7% | -52.3% | kaldi (net <= 0) |

## B grubu özeti

- Satır: 6; geçen: 3 (50.0%); işlemli: 6; hatalı: 0; ayarsız: 0
- Medyan kilitli PF (işlemli): 0.95; medyan işlem başı R: -0.038

## C grubu özeti

- Satır: 55; geçen: 15 (27.3%); işlemli: 55; hatalı: 0; ayarsız: 0
- Medyan kilitli PF (işlemli): 0.68; medyan işlem başı R: -0.107

## D grubu özeti

- Satır: 267; geçen: 90 (33.7%); işlemli: 251; hatalı: 0; ayarsız: 15
- Medyan kilitli PF (işlemli): 0.83; medyan işlem başı R: -0.046

## Ayırt edicilik (C vs D)

- tek_C: `{"n": 51, "n_islemli": 51, "medyan_ortalama_r": -0.1068856539628538, "medyan_pf": 0.671129053535699, "gecen_oran": 0.2549019607843137, "medyan_ortalama_r_islemsiz_0": -0.1068856539628538}`
- tek_D: `{"n": 256, "n_islemli": 240, "medyan_ortalama_r": -0.054185132889547655, "medyan_pf": 0.8228010450320531, "gecen_oran": 0.33984375, "medyan_ortalama_r_islemsiz_0": -0.03837571634444645}`
- tek_D_saglamlik_kalan: `{"n": 196, "n_islemli": 189, "medyan_ortalama_r": -0.046425632530226, "medyan_pf": 0.8228990648497676, "gecen_oran": 0.3673469387755102, "medyan_ortalama_r_islemsiz_0": -0.03837571634444645}`
- tek_D_rastgele: `{"n": 60, "n_islemli": 51, "medyan_ortalama_r": -0.0724091130744985, "medyan_pf": 0.8227030252143385, "gecen_oran": 0.25, "medyan_ortalama_r_islemsiz_0": -0.03690986338948333}`
- tek_C_gt_D: `false`
- portfoy_C: `{"n": 4, "medyan_sharpe": 0.35426847729870414, "gecen_oran": 0.5}`
- portfoy_D: `{"n": 11, "medyan_sharpe": -0.1778737629600078, "gecen_oran": 0.2727272727272727}`
- portfoy_C_gt_D: `true`
- spearman_tum: `{"n": 306, "rho": -0.09538987569789509}`
- spearman_tek: `{"n": 291, "rho": -0.11407995999005932}`
- spearman_en_az_10_islem: `{"n": 237, "rho": -0.08879566832372908}`

## Tüm satırlar

Ayrıntı: `sonuc.csv` (her satır), `set.csv`, `secilen_ayarlar.csv`, `gruplar.csv`.
