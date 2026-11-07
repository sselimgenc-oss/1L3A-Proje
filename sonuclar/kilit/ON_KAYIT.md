# Kilitli dönem testi — ön kayıt (Katman 4)

Tarih: 2026-11-07. Kullanıcı onayı: "aç" (2026-11-07). Bu dosya kilit AÇILMADAN önce yazılıp commit edildi.
Kilitli dönem: 2025-11-01 00:00 UTC → verinin sonu (kripto ~2026-10-31, Dukascopy 2026-10-30).
Kilit **bir kez** açılır; sonuçlara bakarak strateji, parametre, ölçüt ya da liste DEĞİŞTİRİLMEZ.

## Yöntem (sabit)
- Her aday için ayar, walk-forward ile aynı kuralla seçilir: eğitim penceresi = kilitten önceki son pencere
  (swing ve portföy: 730 gün, daytrade/scalp: 365 gün; bitiş 2025-11-01), aynı aday kümesi, aynı skor ve min işlem.
  Seçilen ayar kilitli dönemde **değiştirilmeden** koşulur. Isınma için kilit öncesi veri kullanılabilir.
- Motor, maliyet, sert limitler, sembol kuralları ve veri kaynağı kuralları walk-forward ile aynıdır.
- Portföy stratejileri wf_portfoy ile aynı yöntemle (ağırlık motoru, karar 25 risk bütçesi) koşulur.

## Gruplar
- **A — Final set:** `sonuclar/secim/oneri.csv` içinde rol=secim (swing 3, daytrade 1, portföy 3).
- **B — Yedekler:** aynı dosyada rol=yedek.
- **C — Sağlam havuz:** `sonuclar/final_aday_havuzu_tek_grafik.csv` (51 satır) + portföy sağlamları
  (`sonuclar/saglamlik_portfoy/*_v3.csv` ve `p3_kripto_v2.csv` içinde saglam_mi=True).
- **D — Kontrol grubu (seçimde kullanılmaz, yalnız ölçüm):** walk-forward'ı geçip sağlamlıktan kalan tüm satırlar
  (k3_kripto, k3_dk_v2, k3_hisse_kisa — scalp dahil) + walk-forward'dan kalanlardan sabit tohumla (42) rastgele 60 satır.
  Amaç: elemelerimiz gerçekten ayırt ediyor mu? (A/C'nin kilitli dönem sonucu D'den iyi mi?)

## Başarı ölçütleri (önceden sabit)
- Aday düzeyi (A, B, C): kilitli dönemde net > 0 ve PF ≥ 1.0. (1 yılda swing işlem sayısı düşük; PF ≥ 1.2 bilgi amaçlı raporlanır.)
- Set düzeyi (A, tek kasa, sert limitlerle yeniden oynatma): net > 0, max düşüş ≤ %20, Sharpe > 0.
- Ayırt edicilik: C grubunun medyan kilitli-dönem R'si (veya portföyde Sharpe) > D grubununki.
- Raporlanacak: her adayın kilitli dönem net/PF/işlem/düşüş, WF OOS beklentisiyle fark, al-tut kıyası.

## Sonuca göre (önceden sabit)
- A set ölçütünü geçerse: Aşama 3 (Pano) ve Aşama 4 (paper trading) bu setle başlar.
- Geçmezse: kilitli döneme bakarak yeniden seçim YAPILMAZ. Kullanıcıyla birlikte karar: (a) setle yine paper trading
  (bağımsız ileri test), ya da (b) yeni araştırma turu (yeni dönem verisi gelene kadar kilitli dönem "kullanılmış" sayılır).
- Scalp (D içinde) kilitli dönemde iyi çıksa bile scalp ajanı bu sonuçla açılmaz (seçim sızıntısı olur).
