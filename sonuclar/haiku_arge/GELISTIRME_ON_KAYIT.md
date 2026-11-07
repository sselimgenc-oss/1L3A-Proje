# Geliştirme ön kaydı — sınırdaki adaylar (Aşama 4)

Tarih: 2026-11-07. Bu dosya koşudan ÖNCE commit edilir. Eşikler ve varyant listesi sonuca bakılarak değişmez.

## Adaylar (sınırda)
- **A** `daytrade__donchian-kirilim` — WF geçti (XU30 1h), sağlamlık K2 (rastgele giriş p = 0.053, eşik 0.05): sınırda.
- **B** `dis__atr-rsi-liwei` — WF geçti (XU30 1h), sağlamlık K2 p = 0.058 ve K3 (bootstrap alt sınır): sınırda.
- **C** `swing__rsi-momentum-esik` — WF geçti (DK_XAU 1d), sağlamlık K2 + K3 başarısız: sınırda.

## Varyantlar (her aday için 4; bir seferde tek değişiklik ya da tek kombinasyon; toplam 12 < 20/aday)
Filtre eşikleri a priori sabittir (ayar ızgarası yok):
- **EMA200 trend:** long yalnız kapanış > EMA(200), short yalnız kapanış < EMA(200).
- **Oynaklık:** ATR(14)/kapanış, son 200 mumun medyanının ÜSTÜNDEyse giriş serbest (düşük oynaklık gürültüsünü eler).

| Aday | V1 (ekle) | V2 (ekle) | V3 (ekle, V1+V2) | V4 (çıkar / ekle) |
|---|---|---|---|---|
| A | EMA200 | oynaklık | EMA200 + oynaklık | SMA50 trend filtresini KALDIR (`trend_ma=0`) |
| B | EMA200 | oynaklık | EMA200 + oynaklık | ATR bandı filtresini KALDIR (norm_min=0, norm_maks=1e9) |
| C | EMA200 | oynaklık | EMA200 + oynaklık | hedef ekle: hedef_r = 2 (R katı kâr al) |

Varyant sınıfları `motor/strateji/dis/haiku__varyant.py` içinde (yeni dosya, `haiku__` önek; mevcut modüllere dokunulmaz).

## Geçme kuralı (değişmez)
Varyant, ana projedeki ile aynı kapılardan geçer:
1. Walk-forward (karar 13): net > 0, PF ≥ 1.2, işlem ≥ 50, en iyi %5 hariç PF ≥ 0.9 — aynı enstrüman/TF'de.
2. Sağlamlık (K1–K4 kapıları, `saglamlik.py`): maliyet×2, rastgele giriş p ≤ 0.05, bootstrap PF alt sınırı > 1, komşu parametrelerin ≥ %60'ı PF > 1.

Kazanan ancak ikisini de geçerse sayılır ve kazanansa kilit ön kaydı ayrıca yazılır. Hiçbiri geçmezse "geliştirilemedi" diye raporlanır.

## Veri ve kısıtlar
- Yalnız 2025-11-01 öncesi veri (kilit). Tüm varyantlar 5 enstrümanda aynı WF ile koşulur (base ile karşılaştırılabilir).
- XU30 1h yalnız 2024'ten; A ve B için OOS çok kısa (2025-01 → 2025-09). Bu bilinen zayıflık.
- Deneme kaydı: her varyant `sonuclar/haiku_arge/deneme_kaydi.jsonl`'e yazılır.
