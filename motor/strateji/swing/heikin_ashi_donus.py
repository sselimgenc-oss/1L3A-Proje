"""swing__heikin-ashi-donus: Heikin Ashi mum renginin değişmesi yeni yön sinyalidir.

Kural: HA mumu (varyant "standart": hClose=(O+H+L+C)/4, hOpen=(önceki hOpen+önceki hClose)/2). Renk = hClose>hOpen
(yeşil) / < (kırmızı). Long: bu mum yeşil, bir önceki kırmızı ve önceki kırmızı serinin uzunluğu >= onceki_n; golgesiz=True ise
sinyal mumunun alt gölgesi yok (hOpen - hLow <= golge_tol*ATR, "gölgesiz güçlü mum"). Short ayna. trend_ma>0: EMA(trend_ma) yön
filtresi. Stop: son stop_n mumun dibi/zirvesi (gerçek fiyat) -/+ stop_tampon_atr*ATR, risk <= stop_max_atr ATR (kanonik "HA mum ucu").
Çıkış: HA rengi ters döner (`cikis`, yön-bağımsız: renk değişimi). Hedef: hedef_r>0 ise.
Kaynak kartlar: swing__heikin-ashi-degistirilmis__graham (varyant="graham": hClose=(O+H+L+2C)/5; kitap tetik/stop formülü
VERMEZ -> yalnız bu HA hesabı alındı, mhHigh/mhLow SMA'ları kodlanmadı), scalp__heikin-ashi-renk-donusu__lama,
scalp__ha-renk-donusu__heikinashi (1m; "kırmızı mumun gölgesi önceki gölgeden düşük değil", "doji/topaç dönüm mumu"
kodlanmadı; yerine onceki_n ve golgesiz).
Varsayımlar: pip/puan stopları ATR'ye çevrildi; HA özyinelemeli olduğundan ilk mumlara bağlı (etki ~10 mumda söner).
Negatif kanıt: aile kaydında yok; arşivde kısa TF dönüş denemeleri (5 dk) başarısız (arsiv/OZET.md §3); kitap iddiaları kanıtsız.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class HeikinAshiDonus(Strateji):
    ad = "swing__heikin-ashi-donus"
    stil = "swing"
    varsayilan_parametreler = {
        "varyant": "standart", "onceki_n": 2, "golgesiz": False, "golge_tol": 0.05, "trend_ma": 0,
        "stop_n": 3, "stop_tampon_atr": 0.25, "stop_max_atr": 3.0, "hedef_r": 0.0, "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "golgesiz": [True, False],
        "onceki_n": [1, 2, 3],
        "trend_ma": [0, 50, 100],
    }

    def cikis_var_mi(self) -> bool:
        return True   # HA rengi ters dönünce

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ha = b.heikin_ashi(a, y, d, k, p["varyant"])
        atr = g.atr(y, d, k, p["atr_periyot"])
        renk = pd.Series(0, index=k.index)
        renk[ha["ha_kapanis"] > ha["ha_acilis"]] = 1
        renk[ha["ha_kapanis"] < ha["ha_acilis"]] = -1
        grup = (renk != renk.shift(1)).cumsum()
        seri_uzun = renk.groupby(grup).cumcount() + 1
        onceki_uzun = seri_uzun.shift(1)
        tol = p["golge_tol"] * atr
        long_ok = (renk == 1) & (renk.shift(1) == -1) & (onceki_uzun >= p["onceki_n"])
        short_ok = (renk == -1) & (renk.shift(1) == 1) & (onceki_uzun >= p["onceki_n"])
        if p["golgesiz"]:
            long_ok &= (ha["ha_acilis"] - ha["ha_dusuk"]) <= tol
            short_ok &= (ha["ha_yuksek"] - ha["ha_acilis"]) <= tol
        if p["trend_ma"]:
            ema = g.ema(k, int(p["trend_ma"]))
            long_ok, short_ok = long_ok & (k > ema), short_ok & (k < ema)
        gecerli = atr.notna()
        long_ok, short_ok = long_ok & gecerli, short_ok & gecerli & bool(p["short"])
        stop_l, stop_s = b.swing_stop(y, d, k, atr, int(p["stop_n"]), p["stop_tampon_atr"], p["stop_max_atr"])
        h_l, h_s = b.hedef_r_ile(k, stop_l, stop_s, p["hedef_r"])
        cikis = (renk != renk.shift(1)) & (renk != 0) & (renk.shift(1) != 0) & gecerli
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis)
