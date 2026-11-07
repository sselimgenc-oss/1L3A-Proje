# Elenen swing havuzu — 5 enstrüman WF sonucu (ara sonuç)

Koşu: `sonuclar/haiku_arge/wf_kos.py --stil swing` (motor/arastirma/wf_tarama ile aynı yöntem, ızgara açık, kilit 2025-11-01).
Çıktı: `wf/haiku_elenen_swing.csv`. Havuz: `elenen_havuz.csv` (42 swing stratejisi; önceki WF'de hiç geçmemiş).

## Özet
- 42 strateji × 5 enstrüman × 2 TF (4h, 1d) = 420 görev; 19 satır hata (aşağıda), 401 satır sonuç.
- **Karar 13'ü geçen: 1 satır.** `swing__rsi-momentum-esik` — **DK_XAU 1d**.
  - OOS 2021-12 → 2025-05; 60 işlem; PF 1.53; net +%6.8; max düşüş %3.2; Sharpe 0.59; en iyi %5 hariç PF 0.93 (eşik 0.90).
  - **Uyarı:** aynı OOS aralığında al-tut %83.5. Strateji bu dönemde al-tutun çok altında kaldı; "kazanan" değil,
    yalnız bir aday. Sağlamlık paketi (maliyet×2, rastgele giriş, bootstrap, komşu parametre) ve deflated Sharpe geçmeden
    kazanan sayılmaz.
- Diğer enstrümanlarda hiçbir strateji geçmedi. BTC 1d'de 1 ve XAU 4h'de 1 aday PF ~1.5–2.5 verdi ama işlem sayısı
  ya da en iyi %5 hariç PF kriteri kaldı.
- XU30 4h: 2024'ten kısa veri nedeniyle 0 işlem.

## Hatalar (19 satır)
- `1d üst TF olarak kullanılamaz` (5): motor, 1d'yi üst TF olarak almayan stratejiler için hata verdi (kayıtlı, atlanmadı).
- `FundingYokHatasi` (funding gerektiren carry stratejileri, ör. `dis__ewmac-carry`): bu enstrümanlarda funding verisi
  yok; bu stratejiler bu evrende test edilemez.

## Deneme sayısı (çoklu test)
- `sonuclar/haiku_arge/deneme_kaydi.jsonl`: 401 kayıt, toplam 9.257 backtest koşusu (yalnız bu koşu).
  Deflated Sharpe için bu bir alt sınır; önceki projelerin kayıtları dahil değil.
