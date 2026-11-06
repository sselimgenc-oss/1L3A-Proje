# Codex ikinci liste ("derinlemesine araştırma", 12 strateji) — denetim ve test (2026-10-11)

4'ü ilk listede zaten denetlendi/test edildi (EMA altın EA, volatilite momentum, altcoin arbitrajı, KA-MATS; bkz. `CODEX_ADAYLAR.md`).
Yeni 6 repo yalnızca okundu, çalıştırılmadı.

## Kod denetimi
| Repo | Karar | Neden |
|---|---|---|
| Javier-Garzo/ern-wo-options-backtester | RED | Çıplak SPXW opsiyon satışı, stop yok; nadir ama büyük kayıp; opsiyon verisi gerekir |
| Yugo25/ema-strategy-validation | RED | Elle (manuel) işaretlenmiş 5 dk döviz işlemleri; kodlanamaz, ileri dönem testi yok |
| logiccrafterdz/Argus | RED | Ortalanmış pivot = geleceği görme; 2023 doğrulama yılı PF 1,03 |
| remy-rm511/nasdaq-quant-ml-research | BELKİ | Yürütme bizimle aynı (kapanış sinyali, ertesi açılış) ama PF ~1,24, 2022'de zarar |
| maxs231/lsob-backtest | RED | 1 saatlik BTC, kaldıraçlı long/short, limit emir dolumu; yüksek kaymada negatif |
| MajidUppal/CSCI278 (S2) | BELKİ | Bugünün kazananlarıyla geriye test (hayatta kalma yanlılığı), OOS yok, DD −%51 |

## Bizim çerçevede test (`deneyler/codex2_adaylar.py`)
"bizim" = haftalık HA yönü + sınıf rejim filtresi. ML eşiği yalnızca 2019–2022 tahminlerinde seçildi.

| Aday (bizim) | OOS işlem | OOS KO | OOS PF | Tek başına yıllık | Maks. düşüş | Sisteme eklenince OOS Sharpe (mevcut 1,45) |
|---|---|---|---|---|---|---|
| D1 ML (LightGBM, 11 özellik) | 182 | %41 | 0,99 | %7,3 | −%22,6 | 1,19 ↓ |
| D2 Bileşik 10 gösterge skoru | 1074 | %29 | 1,50 | %23,8 | −%46,5 | (tüm dönem 0,88 ↓) |
| D3 Gizli boğa uyumsuzluğu | 285 | %51 | 1,04 | %4,5 | −%18,8 | **1,56 ↑** |

- D1: Sisteme eklenince tüm dönem Sharpe'ı 1,52'ye çıkıyor gibi görünüyor, ama bu yalnızca 2019–2022'den geliyor; 2023+ zayıflıyor → RED.
- D2: KO %29 (hedef %45), düşüş −%46 → RED.
- D3: Tek başına zayıf (ort. +0,09R) ama mevcut sistemle korelasyonu düşük. 9 komşu ayarın hepsinde tek başına
  beklenti pozitif (+0,03…+0,13R), sisteme eklenince IS Sharpe 1,35 → 1,42–1,58, OOS Sharpe 1,38–1,61 (8/9'u ≥ 1,44).
  Küçük ama sağlam bir çeşitlendirici → **S4 adayı**; kağıt test bitene kadar bota eklenmez, Aralık değerlendirmesinde
  "S1+S2+S3+S4" sürümü olarak masaya gelir.

Kural (D3): 3 mum sonra teyitli dip (low[t−3] = son 7 mumun en düşüğü), bir önceki teyitli dipten (≤60 gün) yüksek,
RSI(14) o dipte öncekinden düşük, kapanış > SMA200; giriş ertesi açılış, stop 2 ATR, hedef 1,5R, en fazla 10 gün.
