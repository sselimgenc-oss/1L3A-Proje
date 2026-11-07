# Ar-Ge kolu (Haiku) — 5 enstrüman durum raporu

Tarih: 2026-11-07. Dal: `claude/haiku-arge-5-enstruman`.
Kapsam (kullanıcı talebi): elenen stratejiler scalp / daytrade / swing olarak yalnız şu 5 enstrümanda:
XU30, SPX, XAUUSD, UKOIL (Brent), BTCUSDT.

## 1. Veri durumu

| Enstrüman | Kaynak planı | Bu konteynerde durum | Sonuç |
|---|---|---|---|
| BTCUSDT | Binance arşivi (`data.binance.vision`) | `veri/mumlar/` yok (repoda değil, .gitignore). Arşiv erişilebilir (HTTP 200). | İndirilmedi: BTC için walk-forward sonuçları zaten var (aşağıda), yeniden koşmak aynı sonucu verir ve deneme sayısını şişirir. |
| XAUUSD | Dukascopy `XAUUSD` (repo kodunda `DK_XAU`) | `DK_XAU` verisi yok. Dukascopy erişilemiyor (proxy tünelini kapatıyor, tüm denemeler kod 000). | Yeni test yapılamadı; eski WF sonuçları var (aşağıda). |
| SPX (S&P 500) | Dukascopy `USA500IDXUSD` (doğrulanmadı) | Dukascopy erişilemiyor. | Test yapılamadı. |
| UKOIL (Brent) | Dukascopy `BRENTCMDUSD` / `UKOUSD` (doğrulanmadı) | Dukascopy erişilemiyor. DK_WTI (WTI) Brent yerine geçmez. | Test yapılamadı. |
| XU30 (BIST 30) | Ücretsiz kaynak bulunmadı | Yahoo Finance 429 (hız sınırı); Stooq erişilemiyor. Hız sınırını aşmak için istek kimliği taklidi yapılmadı. | Test yapılamadı. Kaynak bulunursa yalnız günlük veriyle yalnız swing (kullanıcı kuralı). |

Ağ engelleri (kullanıcıya bildirilmeli): `datafeed.dukascopy.com` tünel seviyesinde kapanıyor (`ws_closed_mid_exchange`),
`stooq.com` ulaşılamıyor, Yahoo 429 veriyor, `api.binance.com` 451 (coğrafi kısıt; arşiv çalışıyor).

## 2. Mevcut sonuçlar (kilit öncesi walk-forward, karar 13)

Kaynak: `sonuclar/wf/k3_kripto.csv` (BTCUSDT), `sonuclar/wf/k3_dk_v2.csv` (DK_XAU).

| Enstrüman | Stil | Denenen strateji | Denenen satır (strateji×TF) | Karar 13 geçen |
|---|---|---|---|---|
| BTCUSDT | swing | 110 | 220 | 7 (1d 3, 4h 4) |
| BTCUSDT | daytrade | 51 | 102 | 0 |
| BTCUSDT | scalp | 46 | 92 | 0 |
| XAUUSD (DK_XAU) | swing | 109 | 218 | 7 (1d 6, 4h 1) |
| XAUUSD (DK_XAU) | daytrade | 50 | 100 | 0 |
| XAUUSD | scalp | — | — | veri yok (dakikalık XAU hiç indirilmedi) |

Geçen swing stratejileri: BTC — `dis__ac-cok-katman`, `dis__norn-weave-thurisaz`, `dis__vixfix-stoch`, `swing__mum-yutan-donus`
(4h); `dis__sqz-donus`, `swing__rsi-asiri-donus`, `swing__bant-donus` (1d). XAU — `dis__heracles`, `dis__ema50-sapma`,
`dis__ay-donumu`, `dis__jt-awesome-osilator`, `dis__ifr2`, `dis__ibs-donus` (1d); `dis__trend-yargisi` (4h).
Sağlamlık (`sonuclar/saglamlik/`) bu sayıların bir kısmını eler; yukarıdaki sayılar yalnız WF kapısıdır.

## 3. Önemli uyarılar

1. **Kilitli dönem kullanılmış.** 2026-11-07 kilit testi (`sonuclar/kilit/RAPOR.md`) 2025-11-01 sonrası veriyi kullandı.
   BTCUSDT ve altın bu testte yer aldığı için bu iki enstrümanda kilit artık temiz bir "sınav" değil. SPX/Brent/XU30
   için henüz kilit sonrası veriye bakılmadı; bu kural (karar 20) korunacak.
2. **Evren değişti.** Bu talep DURUM karar 22'deki evreni (BTC/ETH/SOL + Mag7 + XAU/WTI/bakır) değiştirir. Karar 22'nin
   ETH/SOL/Mag7/WTI/bakır kısmı bu 5 enstrümanla çakışmaz ama uygulanmayacak; kullanıcı onayı ile DURUM'a karar 27 olarak
   işlendi.
3. **WTI ≠ Brent.** Mevcut `DK_WTI` sonuçları UKOIL yerine kullanılamaz.
4. **Scalp veri sorunu.** Dakikalık veri olmadan scalp (15m/30m) hiçbir enstrümanda koşulamaz. BTC scalp kayıtları zaten
   0 geçiş (kilit öncesi, sağlamlık yok).
5. **Deneme kaydı.** Bu aşamada yeni varyant/strateji koşulmadı; `sonuclar/deneme_kaydi.jsonl` değişmedi.

## 4. Sıradaki adımlar (veri gelince)

- SPX, UKOIL (1h + 1d + 15m/5m scalp için dakikalık), XAUUSD (dakikalık, `DK_XAU`) verisi → yalnız 2025-11-01 öncesi.
- Elenen havuz (WF'de geçmeyen strateji×TF, stil başına) bu 3 enstrümanda `wf_tarama` ile koşulur.
- XU30: kaynak bulunana kadar beklemede. Bulunursa yalnız günlük swing.
- Geçen adaylar için sağlamlık (`saglamlik.py`) ve ardından geliştirme (varyant sayısı deneme kaydına yazılır).

## 5. Kullanıcıdan istenenler

- Dukascopy erişimi açılmazsa: SPX, Brent (UKOIL), XAUUSD ve XU30 için CSV dosyası (tarih, açılış, yüksek, düşük, kapanış,
  hacim; tercihen 1h ve günlük, scalp için 15m/5m). Veri 2025-11-01'de kesilmeli (kilit). Dosyalar repoya girmez; yerelde
  `veri/mumlar/` altına alınır.
- Evren değişikliğinin (karar 22 → 5 enstrüman) onayı.
