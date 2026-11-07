# Kripto day trade kağıt al-sat botu (10.000 $, 60 gün)

Gerçek para kullanmadan, canlı Binance verisiyle **60 gün** (2026-10-11 00:00 UTC → 2026-12-10)
7/24 kripto day trade sistemini işletir.

- **Stratejiler** (`kagit/ayarlar.json`, kaynak `daytrade/secili.py`, rapor `docs/kripto_sonuc2.md`):
  S10 geç seans momentum, S13 Lien yanlış kırılma filtresi, S15 trend günü EMA20 geri çekilme.
  Hepsi yalnız alış, 4s/1s yön + 15dk giriş, BTC 4s trend filtresi, gün sonunda (UTC 24:00) çıkış.
- **Evren:** ilk 25 kripto (CoinGecko, stablecoin hariç), ilk çalıştırmada sabitlenir (`evren.json`).
- **Portföy:** her stratejiye ayrı alt hesap (3.333 $, 3 pozisyon), işlem başına %0,5 risk, kaldıraç
  yok, aynı coinde tek pozisyon, günlük −%3 zarar limiti. Maliyet %0,08/yön (spot).
- **Beklenti (backtest):** kazanma ~%49, PF ~1,6, 60 günde 80–120 işlem, ~+%2–4.

## Nasıl çalışır
Her çalıştırmada veri güncellenir ve kağıt döneminin başından bugüne tüm **kapanmış** 15dk mumlar
backtest koduyla yeniden oynatılır; çalıştırma kaçsa bile işlem kaçmaz.

## Nerede çalışır
- GitHub Actions `.github/workflows/kagit.yml`, günde 2 kez (00:41 ve 12:41 UTC).
- Durum dalı `kagit-durum`: `ozet.md`, `durum.json`, `islemler.csv`, `pozisyonlar.csv`, `ozsermaye.csv`.
- Günlük rapor: "Kağıt al-sat raporu (day-trade-sg kripto S10+S13+S15, 10.000 USD)" issue'su.

## Kontrol
- Hemen çalıştırmak: Actions → kagit-al-sat → Run workflow. Durdurmak: Disable workflow.
- Sıfırdan başlatmak: `kagit-durum` dalını silmek yeterli.
- Deneme: `kagit/DENEME` dosyasını (ilk satır başlangıç tarihi) main dışı bir dalda değiştirip push et.
