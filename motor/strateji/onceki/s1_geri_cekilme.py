"""onceki__s1-geri-cekilme — haftalık yön + günlük EMA'ya geri çekilme + RSI soğuma (swing-sg S1).

ORİJİNAL KAYNAK
  arsiv/swing-sg/swing/stratejiler.py:12-35 (`haftalik_yon`, mod "ha"), :77-112 (`s1_geri_cekilme`),
  seçilmiş parametreler arsiv/swing-sg/swing/ayarlar.py:3-4 (S1), çıkış/yürütme arsiv/swing-sg/swing/motor.py:
  haftalık yön "ha": haftalık Heikin Ashi yeşil VE haftalık kapanış > haftalık SMA20 (Pazartesi 00:00'dan itibaren
  kullanılır, veri.py:72-79). Günlük trend: kapanış > EMA50 ve EMA10 > EMA50 ve EMA50 > 5 gün önceki EMA50.
  Geri çekilme: son 3 günde (bugün dahil) low <= EMA10 + 0.3 ATR ve RSI14'ün son 3 günlük en düşüğü < 65.
  Tetik: kapanış > önceki günün yükseği ve kapanış > EMA10. Giriş ertesi açılış. Stop = min(son 4 günün dibi,
  kapanış - ATR) - 0.5 x stop_atr x ATR. Çıkış: +1R'de %50 sat + stop başabaşa; kapanış < EMA50 -> ertesi
  açılış; en çok 30 gün; iz süren stop yok.
  Orijinal yalnız long (short kodda vardı ama kapalı: `short=False`).

1L3A'YA UYARLAMADA DEĞİŞENLER
  - Haftalık yön ust_zaman(mumlar, "1w") ile (kapanmış haftadan; Pazartesi 00:00 UTC hizası).
  - Piyasa rejimi filtresi (rejim="ha": sınıf endeksi, kripto için BTC haftalık HA) KODLANMADI: tek sembolde
    BTC için kendi yön filtresiyle aynıdır; başka sembollerde BTC yönü gerekir (sonraki iş).
  - Heikin Ashi açılışı özyinelemelidir: seri başından hesaplanır; walk-forward pencereleri farklı başlarsa HA
    açılışı birkaç hafta içinde yakınsar ama birebir aynı olmaz.
  - Kısmi kâr + başabaş CikisAyarlari ile (kismi=((1.0, 0.5),), basabas_r_esigi=1.0). Orijinalde stop kısmi
    dolunca başabaşa çekilirdi; motorda 1R'ye ulaşılan mumun kapanışında.
  - EMA50 altı kapanış (short'ta üstü) `cikis` sinyali, 30 gün zaman çıkışı (zaman_cikisi_mum).
  - short parametre ile, varsayılan False. Short'ta yön = haftalık HA kırmızı + kapanış < haftalık SMA20 (ayna).
  - Orijinal "momentum_n", "hacim_azalan" seçenekleri alınmadı (seçili ayarda kapalıydı).

ORİJİNAL RAPORLANAN SONUÇLAR (swing-sg, kripto+Mag7+emtia, günlük, rejim filtreli)
  n=1186, KO %52.4, PF_R 1.82, ort R +0.32, yıllık %19.8, DD -%16.0 (tek başına). IS 591 işlem R +0.39,
  OOS 595 işlem R +0.25. Kripto IS 253 işlem R +0.68 -> OOS 429 işlem R +0.19 (KO %58.5 -> %48.0).

KIRMIZI BAYRAKLAR (arsiv/ANALIZ_swing-sg.md)
  - OOS kirli: S1 için 1.158 ızgara noktası hepsinde OOS görüldü; ham S1 (haftalık HA yönü ve rejim olmadan)
    OOS'ta çöküyordu (IS R +0.48 -> OOS -0.02); "ha" yönü, rejim filtresi ve RSI eşiğinin 40 -> 65 gevşetilmesi
    OOS görülerek seçildi.
  - KO hedefi beklentiyi aşındırdı: kısmi kâr KO'yu artırıp ortalama R'yi düşürdü (IS 0.289 -> 0.206-0.232).
  - Kripto IS ~ tek boğa dalgası (2019-21); kripto OOS R +0.19'a düştü; 2025'te kripto ortalama R -0.03.
  - Spot veri, funding yok: ortalama 16 gün tutma ile funding ~0.04R (S1); perp'te maliyet ek.
  - Aynı gün çok sayıda kripto girişi (bağımsız olmayan işlemler); stop mesafesi kriptoda medyan %13.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.htf import ust_zaman
from motor.strateji.onceki._ortak import cerceve, heikin_ashi, yone_gore_cikis
from motor.strateji.temel import Strateji


class S1GeriCekilme(Strateji):
    ad = "onceki__s1-geri-cekilme"
    stil = "swing"
    varsayilan_parametreler = {
        "hizli": 10, "yavas": 50,          # günlük EMA'lar (geri çekilme MA'sı = hızlı; trend/çıkış = yavaş)
        "rsi_n": 14, "rsi_esik": 65.0,     # son `bakis` mumun RSI en düşüğü < eşik (short: en yükseği > 100-eşik)
        "temas_atr": 0.3, "bakis": 3,
        "yavas_egim": 5,                   # EMA(yavaş) > `yavas_egim` mum önceki EMA(yavaş)
        "stop_atr": 1.0, "atr_periyot": 14,
        "haftalik_sma": 20,                # haftalık yön: HA renk + kapanış SMA(haftalık_sma) tarafında
        "max_mum": 30,                     # zaman çıkışı (gün)
        "short": False,
    }
    parametre_izgarasi = {
        "rsi_esik": [55.0, 65.0, 75.0],
        "hizli": [10, 15, 20],
        "stop_atr": [0.5, 1.0, 1.5],
    }
    cikis_ayarlari = CikisAyarlari(kismi=((1.0, 0.5),), basabas_r_esigi=1.0)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = mumlar.index
        a, yu, du, kap = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(yu, du, kap, int(p["atr_periyot"]))
        eh, ey = g.ema(kap, int(p["hizli"])), g.ema(kap, int(p["yavas"]))
        r = g.rsi(kap, int(p["rsi_n"]))
        b = int(p["bakis"])
        ws = int(p["haftalik_sma"])

        def haftalik(u):
            ho, hc = heikin_ashi(u["acilis"], u["yuksek"], u["dusuk"], u["kapanis"])
            s = g.sma(u["kapanis"], ws)
            yon = np.where(s.isna(), np.nan,
                           np.where((hc > ho) & (u["kapanis"] > s), 1.0,
                                    np.where((hc < ho) & (u["kapanis"] < s), -1.0, 0.0)))
            return pd.Series(yon, index=u.index)

        wy = ust_zaman(mumlar, "1w", haftalik)
        egim = int(p["yavas_egim"])
        trend_up = (kap > ey) & (eh > ey) & (ey > ey.shift(egim))
        temas_up = (du <= eh + p["temas_atr"] * atr).astype(float).rolling(b, min_periods=b).max() > 0
        soguma_up = r.rolling(b, min_periods=b).min() < p["rsi_esik"]
        tetik_up = (kap > yu.shift(1)) & (kap > eh)
        long_ok = (wy > 0) & trend_up & temas_up & soguma_up & tetik_up

        trend_dn = (kap < ey) & (eh < ey) & (ey < ey.shift(egim))
        temas_dn = (yu >= eh - p["temas_atr"] * atr).astype(float).rolling(b, min_periods=b).max() > 0
        soguma_dn = r.rolling(b, min_periods=b).max() > 100.0 - p["rsi_esik"]
        tetik_dn = (kap < du.shift(1)) & (kap < eh)
        short_ok = ((wy < 0) & trend_dn & temas_dn & soguma_dn & tetik_dn) if p["short"] \
            else pd.Series(False, index=idx)

        sw_l = du.rolling(b + 1, min_periods=b + 1).min()
        sw_h = yu.rolling(b + 1, min_periods=b + 1).max()
        stop_l = np.minimum(sw_l, kap - atr) - p["stop_atr"] * atr * 0.5
        stop_s = np.maximum(sw_h, kap + atr) + p["stop_atr"] * atr * 0.5
        long_ok = long_ok.fillna(False)
        short_ok = short_ok.fillna(False)
        yon_ham = pd.Series(np.where(long_ok, 1, np.where(short_ok, -1, 0)), index=idx)
        cikis = yone_gore_cikis(yon_ham, (kap < ey), (kap > ey))
        return cerceve(idx, long_ok, short_ok, stop_l, stop_s, cikis, p["max_mum"])

    def cikis_var_mi(self) -> bool:
        """Kapanış EMA(yavaş) ters tarafında -> `cikis` (her zaman)."""
        return True
