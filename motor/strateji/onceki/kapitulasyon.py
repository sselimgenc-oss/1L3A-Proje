"""onceki__kapitulasyon — kapitülasyon dönüşü: 24 saatte >= %X düşüş sonrası long (algo-sg B). YEDEK aday.

ORİJİNAL KAYNAK
  arsiv/algo-sg/algo/final.py:24-25 (B sözlüğü), mantık arsiv/algo-sg/algo/strategies.py:255-322
  (`s4_stretch_reversion`, drop24 kolu :280-281, trigger="none" :292-293), backtest arsiv/algo-sg/algo/backtest.py.
  Kural: coinin 24 saatlik BASİT getirisi (kapanış / 24 mum önceki kapanış - 1) < -%15 olan her 1H mumun
  kapanışında long (bias_win=1, ek tetik yok); BTC filtresi denetimde kaldırıldı (aşırı uyum). Stop = 4 x ATR(4H);
  +1R'de stop başabaşa (be_R=1.0); en çok 96 saat (96 x 1H mum); hedef/başka çıkış yok. Eşik önce log getiri
  iken belgede "%15" yazıyordu; denetimde basit %'ye düzeltildi (ANALIZ_algo-sg.md §4 "Belge-kod").
  Koşul sürdükçe her mumda sinyal üretilir; motor pozisyon açıkken yok sayar, çıkıştan sonra koşul hâlâ doğruysa
  yeniden girilir (orijinal döngü de böyleydi).

1L3A'YA UYARLAMADA DEĞİŞENLER
  - Tek sembol; risk %0.75 / 25 pozisyon portföyü yok. 4H ATR ust_zaman ile (kapanmış 4H mumdan), mum TF'si
    4h veya üstüyse kendi ATR'si.
  - Pencere `pencere` MUM sayısıdır (1h TF'de 24 saat); başka TF'de saat karşılığı değişir.
  - Başabaş: motorda 1R'ye ulaşılan mumun kapanışında stop girişe çekilir (orijinal: giriş + 2 x maliyet).
  - Zaman çıkışı `zaman_cikisi_mum` sütunuyla (max_mum), iz süren stop/kısmi kâr yok.
  - Giriş sonraki mum açılışında, kriz anı kayma/dolum gerçekçiliği motor kayma modeline bağlı (limit_modu "olc"
    ve stop_kayma_bps).

ORİJİNAL RAPORLANAN SONUÇLAR (25 coin, 2020-2026, %0.07/taraf)
  996 işlem, WR %64.0, PF 1.78; IS 645 işlem PF 1.41; OOS 351 işlem PF 2.67; MTM yıllık %12.1, DD -%18.5.
  Yıllık PF: 2022 0.95 (n=168), 2023 16.7 (n=35), 2024 2.85, 2025 2.55.

KIRMIZI BAYRAKLAR (arsiv/ANALIZ_algo-sg.md)
  - Bağımsız örneklem küçük: 996 işlem ~234 ayrı günde; >=5 işlemli 53 günün R'si toplamın %56'sı -> ~50-60
    bağımsız olay. Tek sembolde (BTC) çok daha az olay beklenir.
  - Kâr merkezi kriz günleri (2024-08-05, 2025-10-10, 2025-04-07): o saatlerde defter boş, açılış fiyatından dolum
    gerçekçi değil (kayma sabit 2 bp idi).
  - OOS PF (2.67) IS'ten (1.41) çok yüksek: rapor şans olabilir diyor; gerçekçi PF 1.4-1.8.
  - Stop mesafesi medyan %22: WR yüksek olması stopun çok uzak olmasıyla ilgili (kayıpların çoğu zaman çıkışı,
    stop vuran yalnız 157/996). Davey'in en kötü bulduğu "Percent Decrease" yöntemi.
  - OOS kirli (~3600 ızgara satırı); evren seçim yanlılığı; 2022 PF 0.95.
"""
import numpy as np
import pandas as pd

from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.onceki._ortak import cerceve, ust_atr
from motor.strateji.temel import Strateji


class Kapitulasyon(Strateji):
    ad = "onceki__kapitulasyon"
    stil = "swing"
    varsayilan_parametreler = {
        "esik": 0.15,              # pencere mumda basit getiri < -esik
        "pencere": 24,             # mum sayısı (1h TF'de 24 saat)
        "stop_atr": 4.0,           # x ATR(4H)
        "atr_periyot": 14,
        "max_mum": 96,             # zaman çıkışı (mum); 0 = kapalı
    }
    parametre_izgarasi = {
        "esik": [0.10, 0.15, 0.20],
        "stop_atr": [3.0, 4.0, 5.0],
        "max_mum": [48, 96, 144],
    }
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=1.0)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = mumlar["kapanis"]
        getiri = kap / kap.shift(int(p["pencere"])) - 1.0
        atr4 = ust_atr(mumlar, "4h", int(p["atr_periyot"]))
        long_ok = (getiri < -p["esik"]) & atr4.notna()
        stop_l = kap - p["stop_atr"] * atr4
        no = pd.Series(False, index=mumlar.index)
        return cerceve(mumlar.index, long_ok, no, stop_l, pd.Series(np.nan, index=mumlar.index),
                       None, p["max_mum"] or None)

    def cikis_var_mi(self) -> bool:
        """Zaman çıkışı (max_mum > 0) `zaman_cikisi_mum` sütunuyla verilir."""
        return bool(self.parametreler["max_mum"])
