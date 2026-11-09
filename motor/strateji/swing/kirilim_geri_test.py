"""swing__kirilim-geri-test: kırılan direnç/destek seviyesine geri test (rol değişimi) (4h/1d).

Kural: Seviye = önceki `uzunluk` mumun en yüksek (direnç) / en düşüğü (destek). Kapanış seviyeyi
`kirilim_tampon_atr*ATR` aşarsa kırılım olur (giriş YOK). Sonraki 1..`pencere` mum içinde fiyat seviyeye
`temas_atr*ATR` yakınına geri döner, seviyenin üstünde (short: altında) kapanır ve tepki mumu (kapanış>açılış;
short: <) oluşursa trend yönünde giriş. Kapanış seviyenin yanlış tarafına geçerse kurulum iptal; kurulum açıkken yeni
kırılım seviyeyi değiştirmez. Kırılım başına en çok bir giriş. Stop = geri test mumu ucu ve seviyenin ötesi -/+
stop_tampon_atr*ATR. Hedef = hedef_r*R. Çıkış: hedef veya stop (gün sonu YOK).
Mekanik `daytrade__kirilim-geri-test` ile aynıdır (aynı döngü; o sınıf gün sonu çıkışını kendi içinde zorunlu kıldığı için
gün sonu olmayan kopya yazıldı). Scalp sürümü bu sınıftan türer.
Kaynak kartlar: daytrade__geri-cekilme-girisi__bulkowski (1D; kırılımdan sonra gerileme tamamlanıp çıkış yönüne
  dönünce giriş, gerileme 1-5 gün; stop gerilemenin 1 kuruş altı; iz süren: önceki mum dibi -> iz süren stop
  CikisAyarlari ile verilebilir), swing__direnc-destek-rol-degisimi__jordan (seviye geri dönüş, stop seviyenin ters
  tarafı, sayısal değer yok).
Varsayımlar: seviye Donchian (swing pivot değil); pencere 10 mum (4h'de ~2 gün; 1d'de 2 hafta, Bulkowski 1-5 gün için
  ızgarada 5); teyit mumu basit tepki mumu; Bulkowski'nin "alternatif: önceki mum zirvesi stop-buy" girişi yok.
Negatif kanıt: Bulkowski kırılım sonrası geri dönüş oranı %54-58 (aile kaydı) — yarısı geri gelmez, atlanır.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class KirilimGeriTest(Strateji):
    ad = "swing__kirilim-geri-test"
    stil = "swing"
    varsayilan_parametreler = {
        "uzunluk": 20, "kirilim_tampon_atr": 0.1, "pencere": 10, "temas_atr": 0.3,
        "stop_tampon_atr": 0.5, "hedef_r": 2.0, "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "uzunluk": [20, 30, 50],
        "pencere": [5, 10, 20],
        "hedef_r": [1.5, 2.0, 3.0],
    }

    def cikis_var_mi(self) -> bool:
        return self.parametreler["hedef_r"] > 0

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        L = int(p["uzunluk"])
        atr = g.atr(y, d, k, p["atr_periyot"])
        ust = y.shift(1).rolling(L, min_periods=L).max()
        alt = d.shift(1).rolling(L, min_periods=L).min()
        n = len(k)
        A, Y, D, K, AT = (x.to_numpy() for x in (a, y, d, k, atr))
        UST, ALT = ust.to_numpy(), alt.to_numpy()
        tb, tc, pen, st = p["kirilim_tampon_atr"], p["temas_atr"], int(p["pencere"]), p["stop_tampon_atr"]
        long_ok = np.zeros(n, bool)
        short_ok = np.zeros(n, bool)
        stop_l = np.full(n, np.nan)
        stop_s = np.full(n, np.nan)
        sl = ss = np.nan          # aktif kırılım seviyesi (yukarı / aşağı)
        yl = ys = 0               # kırılımdan beri geçen mum
        for i in range(n):
            if np.isnan(AT[i]):
                continue
            if not np.isnan(sl):
                yl += 1
                if K[i] < sl or yl > pen:
                    sl = np.nan
                elif D[i] <= sl + tc * AT[i] and K[i] > A[i]:
                    long_ok[i] = True
                    stop_l[i] = min(D[i], sl) - st * AT[i]
                    sl = np.nan
            if not np.isnan(ss):
                ys += 1
                if K[i] > ss or ys > pen:
                    ss = np.nan
                elif Y[i] >= ss - tc * AT[i] and K[i] < A[i]:
                    short_ok[i] = True
                    stop_s[i] = max(Y[i], ss) + st * AT[i]
                    ss = np.nan
            if np.isnan(sl) and not np.isnan(UST[i]) and K[i] > UST[i] + tb * AT[i]:
                sl, yl = UST[i], 0
            if np.isnan(ss) and not np.isnan(ALT[i]) and K[i] < ALT[i] - tb * AT[i]:
                ss, ys = ALT[i], 0
        if not p["short"]:
            short_ok[:] = False
        idx = mumlar.index
        stop_l, stop_s = pd.Series(stop_l, index=idx), pd.Series(stop_s, index=idx)
        h_l = k + p["hedef_r"] * (k - stop_l)
        h_s = k - p["hedef_r"] * (stop_s - k)
        return cerceve(mumlar, pd.Series(long_ok, index=idx), pd.Series(short_ok, index=idx),
                       stop_l, stop_s, h_l, h_s, gun_sonu=False)
