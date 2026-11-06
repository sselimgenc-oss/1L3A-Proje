"""swing__fib-geri-cekilme — trendde Fibonacci geri çekilme bölgesinden trend yönünde giriş.

Kural (kartların ortak çekirdeği: Johnson, Graham, Boxer, Landry, Hogan):
  Bacak (long): son onaylı tepe T (pivotlar.py, nedensel) ve önceki tepe ile T arasındaki en düşük
  dip D; T > önceki tepe (yükseliş yapısı). R = T - D. T'den sonra yeni zirve yapılmamışsa ve fiyat
  `stop_seviyesi` Fib seviyesini (varsayılan 1.0 = D) aşmamışsa bacak geçerlidir. Tepki mumu:
  yükseliş mumu (kapanış > açılış) ve mum dibi geri çekilme bölgesinde
  [T - giris_ust*R, T - giris_alt*R] -> long, mum kapanışında. Bacak başına tek sinyal.
  Short: aynası (son dip, iki dip arasındaki en yüksek tepe, düşüş mumu).
  Stop: T - stop_seviyesi*R - tampon_atr*ATR (Fib %100 = bacak başlangıcının ötesi; Johnson
  kartı %78.6 altı der -> stop_seviyesi=0.786 ile denenebilir).
  Hedef: T + (hedef_uzatma-1)*R (1.0 = önceki swing tepesi, 1.272/1.618 = uzatma; Johnson/Landry).
  Opsiyonel trend EMA filtresi (trend_ema, 0=kapalı).

Kaynak kartlar: fib-geri-cekilme-alimi__johnson, fibonacci-geri-cekilme__graham,
  fibonacci-geri-cekilme-hedef__boxer, fibonacci-geri-cekilme__make, fibonacci-61-8-geri-cekilme__hogan,
  gatekeeper__landry, alis-satis-penceresi-60__crane.
Kanıt: ailede sayısal kanıt yok; Graham: swing tepe/dip seçimi hatalıysa seviyeler yanlış olur.
Çelişki/varsayım: kartlarda bölge 38.2-61.8 (Johnson, Graham: 38.2/50) ile 61.8-78.6 (Landry, ters
  dönüş tipi) ve Make'te 35/46/70 arasında değişir; varsayılan 0.382-0.618, ızgarada 0.5-0.786'ya
  kadar. Landry'nin 10-11 gün süre kısıtı ve 2 aylık zirve şartı kodlanmadı. "Güçlü trend" için
  yalnızca pivot yapısı (yüksek tepe) ve isteğe bağlı EMA kullanıldı. MACD/Stokastik onayı yok.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.pivotlar import pivot_tablosu, sinyal_cercevesi
from motor.strateji.temel import Strateji


class FibGeriCekilme(Strateji):
    ad = "swing__fib-geri-cekilme"
    stil = "swing"
    varsayilan_parametreler = {
        "pivot_yontemi": "fraktal", "pivot_k": 3, "zigzag_esik_k": 2.0,
        "giris_alt": 0.382, "giris_ust": 0.618, "stop_seviyesi": 1.0, "tampon_atr": 0.1,
        "hedef_uzatma": 1.0, "trend_ema": 0, "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "giris_alt": [0.382, 0.5, 0.618],
        "giris_ust": [0.618, 0.786],
        "hedef_uzatma": [1.0, 1.272, 1.618],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        n = len(mumlar)
        ac, yu, du, kap = (mumlar[c].to_numpy(float) for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], p["atr_periyot"]).to_numpy()
        ema = g.ema(mumlar["kapanis"], int(p["trend_ema"])).to_numpy() if p["trend_ema"] else None
        pv = pivot_tablosu(mumlar, p["pivot_yontemi"], int(p["pivot_k"]),
                           int(p["atr_periyot"]), p["zigzag_esik_k"])
        st_f, st_i = pv["son_tepe_fiyat"].to_numpy(), pv["son_tepe_idx"].to_numpy()
        ot_f, ot_i = pv["onceki_tepe_fiyat"].to_numpy(), pv["onceki_tepe_idx"].to_numpy()
        sd_f, sd_i = pv["son_dip_fiyat"].to_numpy(), pv["son_dip_idx"].to_numpy()
        od_f, od_i = pv["onceki_dip_fiyat"].to_numpy(), pv["onceki_dip_idx"].to_numpy()
        alt, ust, ss, tamp, uz = (p["giris_alt"], p["giris_ust"], p["stop_seviyesi"],
                                  p["tampon_atr"], p["hedef_uzatma"])

        yon = np.zeros(n, dtype="int64")
        stop = np.full(n, np.nan)
        hedef = np.full(n, np.nan)
        kullanilan_l = kullanilan_s = -1   # sinyal verilen bacağın pivot idx'i

        for t in range(n):
            if np.isnan(atr[t]):
                continue
            # ---- long: son tepe T, önceki tepe ile T arasındaki en düşük dip D
            if not np.isnan(ot_f[t]) and st_f[t] > ot_f[t] and int(st_i[t]) != kullanilan_l:
                ti, pi = int(st_i[t]), int(ot_i[t])
                T = st_f[t]
                D = du[pi:ti + 1].min()
                R = T - D
                if R > 0 and (ti + 1 <= t):
                    zirve_sonrasi = yu[ti + 1:t + 1].max()
                    onceki_dip = du[ti + 1:t].min() if t > ti + 1 else np.inf
                    seviye_ust = T - ust * R
                    seviye_alt = T - alt * R
                    stop_fiyat = T - ss * R
                    if (zirve_sonrasi <= T and onceki_dip >= stop_fiyat
                            and seviye_ust <= du[t] <= seviye_alt
                            and kap[t] > ac[t] and kap[t] < T and kap[t] > stop_fiyat - tamp * atr[t]
                            and (ema is None or kap[t] > ema[t])):
                        yon[t] = 1
                        stop[t] = stop_fiyat - tamp * atr[t]
                        hedef[t] = T + (uz - 1.0) * R
                        kullanilan_l = ti
            # ---- short aynası: son dip, önceki dip ile arasındaki en yüksek tepe
            if p["short"] and yon[t] == 0 and not np.isnan(od_f[t]) and sd_f[t] < od_f[t] \
                    and int(sd_i[t]) != kullanilan_s:
                di, pi = int(sd_i[t]), int(od_i[t])
                B = sd_f[t]
                Z = yu[pi:di + 1].max()
                R = Z - B
                if R > 0 and (di + 1 <= t):
                    dip_sonrasi = du[di + 1:t + 1].min()
                    onceki_tepe = yu[di + 1:t].max() if t > di + 1 else -np.inf
                    seviye_alt = B + ust * R
                    seviye_ust = B + alt * R
                    stop_fiyat = B + ss * R
                    if (dip_sonrasi >= B and onceki_tepe <= stop_fiyat
                            and seviye_ust <= yu[t] <= seviye_alt
                            and kap[t] < ac[t] and kap[t] > B and kap[t] < stop_fiyat + tamp * atr[t]
                            and (ema is None or kap[t] < ema[t])):
                        yon[t] = -1
                        stop[t] = stop_fiyat + tamp * atr[t]
                        hedef[t] = B - (uz - 1.0) * R
                        kullanilan_s = di
        return sinyal_cercevesi(mumlar.index, yon, stop, hedef)

    def cikis_var_mi(self) -> bool:
        """Hedef her zaman var."""
        return True
