"""swing__dar-aralik-kirilim: NR7 / iç bar sonrası kırılım.

Kaynak kartlar: bulkowski (NR7), graham + day (iç bar). Singhal VCP kartı kodlanmadı (daralma sayısı/oranı belirsiz).
Ortak çekirdek: dar mum (NR-n: aralık son n mumun en dar aralığı; iç bar: yüksek<=önceki yüksek ve dip>=önceki dip)
oluşur; sonraki mumlar dar mumun (iç barda ana mumun) bir ucunu kapanışla kırarsa kırılım yönünde giriş.
Kanonik kural ile çelişki: kanon "yüksek kırılırsa buy-stop" der; Bulkowski KAPANIŞ ile kırılım ister. Motor
sinyali kapanışta üretip sonraki açılışta işlem yaptığı için kapanış tabanlı kırılım kullanıldı.
Bulkowski kırılımı 7 mumluk ekstrem üzerinden tanımlar; burada setup mumunun (iç barda ana mumun) ucu esastır
(Graham/Day ile uyumlu). Geçerlilik: setup'tan sonra en çok `gecerlilik` mum (Bulkowski: 7).

Varsayımlar: stop = dar mumun karşı ucu -/+ stop_tampon_atr*ATR (kanon; kartlar vermiyor); hedef = hedef_r*R
(0 ise NaN; kitaplarda sabit hedef yok, Singhal 1:3); trend_ma>0 ise trend yönü filtresi (day: yalnız trendde).
İç bar modunda `nr_pencere` kullanılmaz. Çıkış sinyali yok.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.swing._ortak import sinyal_cercevesi
from motor.strateji.temel import Strateji


class DarAralikKirilim(Strateji):
    ad = "swing__dar-aralik-kirilim"
    stil = "swing"
    varsayilan_parametreler = {
        "mod": "nr",               # "nr" | "ic_bar"
        "nr_pencere": 7,
        "gecerlilik": 7,
        "kirilim_tampon_atr": 0.0,
        "trend_ma": 0,             # 0: kapalı; SMA
        "atr_periyot": 14, "stop_tampon_atr": 0.0,
        "hedef_r": 0.0,
        "short": True,
    }
    parametre_izgarasi = {
        "mod": ["nr", "ic_bar"],
        "nr_pencere": [5, 7, 10],
        "kirilim_tampon_atr": [0.0, 0.25],
        "hedef_r": [0.0, 2.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"].to_numpy(), mumlar["dusuk"].to_numpy(), mumlar["kapanis"].to_numpy()
        n = len(mumlar)
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], p["atr_periyot"])
        atr_v = atr.to_numpy()
        aralik = y - d
        if p["mod"] == "nr":
            w = p["nr_pencere"]
            en_dar = pd.Series(aralik).rolling(w, min_periods=w).min().to_numpy()
            kurulum = aralik <= en_dar
            kurulum[:w - 1] = False
        else:
            kurulum = np.zeros(n, dtype=bool)
            kurulum[1:] = (y[1:] <= y[:-1]) & (d[1:] >= d[:-1])

        yon = np.zeros(n, dtype=bool), np.zeros(n, dtype=bool)
        sl, ss = np.full(n, np.nan), np.full(n, np.nan)
        ust = alt = np.nan          # kırılım seviyeleri
        dar_ust = dar_alt = np.nan  # stop için dar mum uçları
        akt_i = -10**9
        for i in range(n):
            if i - akt_i <= p["gecerlilik"] and i > akt_i and not np.isnan(atr_v[i]):
                tm = p["kirilim_tampon_atr"] * atr_v[i]
                if k[i] > ust + tm:
                    yon[0][i] = True
                    sl[i] = dar_alt - p["stop_tampon_atr"] * atr_v[i]
                    akt_i = -10**9
                elif k[i] < alt - tm:
                    yon[1][i] = True
                    ss[i] = dar_ust + p["stop_tampon_atr"] * atr_v[i]
                    akt_i = -10**9
            if kurulum[i]:
                if p["mod"] == "ic_bar":
                    if i - 1 == akt_i and akt_i >= 0 and kurulum[i - 1]:
                        pass        # iç bar kümesi: ana mum seviyeleri aynı kalır
                    else:
                        ust, alt = y[i - 1], d[i - 1]
                    dar_ust, dar_alt = y[i], d[i]
                else:
                    ust, alt = y[i], d[i]
                    dar_ust, dar_alt = ust, alt
                akt_i = i

        idx = mumlar.index
        long_ok = pd.Series(yon[0], index=idx)
        short_ok = pd.Series(yon[1], index=idx) & bool(p["short"])
        stop_l, stop_s = pd.Series(sl, index=idx), pd.Series(ss, index=idx)
        if p["trend_ma"]:
            tr = g.sma(mumlar["kapanis"], p["trend_ma"])
            long_ok &= mumlar["kapanis"] > tr
            short_ok &= mumlar["kapanis"] < tr
        kap = mumlar["kapanis"]
        # stop kapanışın doğru tarafında olmalı (kırılım mumu kapanışı seviyeyi aştığı için garanti)
        long_ok &= stop_l < kap
        short_ok &= stop_s > kap
        if p["hedef_r"]:
            h_l = kap + p["hedef_r"] * (kap - stop_l)
            h_s = kap - p["hedef_r"] * (stop_s - kap)
        else:
            h_l = h_s = None
        return sinyal_cercevesi(idx, long_ok, short_ok, stop_l, stop_s, h_l, h_s)

    def cikis_var_mi(self) -> bool:
        """hedef_r=0 ise hedef yok."""
        return bool(self.parametreler["hedef_r"])
