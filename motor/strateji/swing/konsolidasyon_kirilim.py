"""swing__konsolidasyon-kirilim — dar konsolidasyon / aralık kırılımı (hacim onaylı).

Kural (kartların ortak çekirdeği):
  Kutu = önceki `uzunluk` mumun en yüksek/en düşüğü (o anki mum hariç). Kutu "dar" ise
  (yükseklik <= maks_genislik_atr * ATR) ve mum kapanışı üst sınırın `tampon_atr*ATR` üstündeyse
  long (alt sınırın altındaysa short, ayna). Hacim: mum hacmi kutu ortalama hacminin
  `hacim_k` katından büyük olmalı (hacim_k=0: kapalı). Opsiyonel trend EMA filtresi.
  Stop: kutunun karşı ucu (stop_modu="uc") veya kutu ortası ("orta").
  Hedef: kutu yüksekliği kadar ölçülen hareket (kapanıştan itibaren).

Kaynak kartlar: kopus-hacim-onayi__hogan, kirilim-hacim-onayli__johnson,
  kesilmis-fiyat-kopusu__make, tikanikliktan-kirilim__bulkowski (+ ailedeki diğer kartlar).
Kanıt/uyarı (aile kanıtı, negatif): Scheier: kırılımların çoğu başarısız olur, duraklama/retest
  filtresi gerekir; Bulkowski kişisel: destek kırılımı satışlarının %70'i zararla bitmiş.
  Bu yüzden hacim ve trend filtreleri parametre olarak var; tek başına zayıf kabul edilmeli.
Varsayımlar: "dar kutu" eşiği (maks_genislik_atr) kartlarda sayısal değil, tarafımızdan konuldu;
  Hogan'ın "onay mumu" (boğa mumu) kapanışın kendisiyle karşılandı; retest beklenmiyor
  (giriş kırılım mumu kapanışında). Kartlardaki hisse likidite filtreleri (300k hacim, 5$) yok.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.pivotlar import sinyal_cercevesi
from motor.strateji.temel import Strateji


class KonsolidasyonKirilim(Strateji):
    ad = "swing__konsolidasyon-kirilim"
    stil = "swing"
    varsayilan_parametreler = {
        "uzunluk": 15, "maks_genislik_atr": 5.0, "tampon_atr": 0.1,
        "hacim_k": 1.5, "trend_ema": 0, "stop_modu": "uc",
        "hedef_olcu": 1.0, "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "uzunluk": [10, 20, 30],
        "hacim_k": [0.0, 1.5, 2.0],
        "tampon_atr": [0.0, 0.25, 0.5],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        yu, du, kap = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        L = int(p["uzunluk"])
        atr = g.atr(yu, du, kap, p["atr_periyot"])
        ust = yu.shift(1).rolling(L, min_periods=L).max()
        alt = du.shift(1).rolling(L, min_periods=L).min()
        genislik = ust - alt
        dar = genislik <= p["maks_genislik_atr"] * atr.shift(1)
        tampon = p["tampon_atr"] * atr
        ok = dar & atr.notna()
        if p["hacim_k"] > 0:
            ort_hacim = mumlar["hacim"].shift(1).rolling(L, min_periods=L).mean()
            ok = ok & (mumlar["hacim"] > p["hacim_k"] * ort_hacim)
        long_ok = ok & (kap > ust + tampon)
        short_ok = ok & (kap < alt - tampon) & bool(p["short"])
        if p["trend_ema"]:
            ema = g.ema(kap, int(p["trend_ema"]))
            long_ok = long_ok & (kap > ema)
            short_ok = short_ok & (kap < ema)
        long_ok, short_ok = long_ok.fillna(False).to_numpy(), short_ok.fillna(False).to_numpy()

        stop_l = alt if p["stop_modu"] == "uc" else (ust + alt) / 2.0
        stop_s = ust if p["stop_modu"] == "uc" else (ust + alt) / 2.0
        yon = np.where(long_ok, 1, np.where(short_ok, -1, 0))
        stop = np.where(long_ok, stop_l, np.where(short_ok, stop_s, np.nan))
        olcu = (p["hedef_olcu"] * genislik).to_numpy()
        hedef = np.where(long_ok, kap.to_numpy() + olcu, np.where(short_ok, kap.to_numpy() - olcu, np.nan))
        return sinyal_cercevesi(mumlar.index, yon, stop, hedef)
