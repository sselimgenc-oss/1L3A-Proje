"""daytrade__bb-sikisma-kirilim: Bollinger bant genişliği sıkışması sonrası bant dışı kırılım, gün sonunda kapanır.

Kural: Bant genişliği bw=(üst-alt)/orta. Sıkışma = bw, son `sikisma_pencere` mumdaki bw'nin alt
`sikisma_yuzdelik` yüzdeliğinin altında (veya eşit). Son `sikisma_son` mum (önceki mumlar) içinde sıkışma
görülmüşse, kapanış üst bandın üstüne İLK kez çıkarsa ve bw artıyorsa long (alt bandın altı: short, ayna).
Hacim filtresi: hacim > hacim_k * 20 mum ortalama hacim (hacim_k=0: kapalı).
Stop: stop_modu="orta" -> orta bant -/+ stop_tampon_atr*ATR (kart); "kutu" -> sıkışma bölgesinin karşı ucu.
Hedef: hedef_r*R (0: yok). Çıkış: kapanış orta bandı karşıya keserse `cikis` (kart: orta bandın altında
kapanışta çık), ayrıca seansın son mumunda gün sonu `cikis`.
Kaynak kart (tek): daytrade__bb-genislik-kirilim__singhal (30dk, BB 20/2; 1:3.8 ve 1:5.1 R/R tek tek örnekler).
Varsayımlar: sıkışma eşiği kartta sayısal değil (kanon: son 20-120 mumun alt %10-20'si — ızgarada);
  "bant genişliği düz kalır" şartı kodlanmadı, yerine "sıkışma son N mumda görüldü + genişlik artıyor".
Kanıt: tek yazar, tek tek örnekler; negatif kanıt yok ama kanıt da yok.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


class BbSikismaKirilim(Strateji):
    ad = "daytrade__bb-sikisma-kirilim"
    stil = "daytrade"
    varsayilan_parametreler = {
        "bb_periyot": 20, "bb_sapma": 2.0,
        "sikisma_pencere": 100, "sikisma_yuzdelik": 15.0, "sikisma_son": 6,
        "hacim_k": 0.0, "stop_modu": "orta", "stop_tampon_atr": 0.25, "hedef_r": 3.0,
        "atr_periyot": 14, "seans_saat": 0.0, "short": True,
    }
    parametre_izgarasi = {
        "sikisma_pencere": [60, 120],
        "sikisma_yuzdelik": [10.0, 20.0],
        "stop_modu": ["orta", "kutu"],
        "hedef_r": [0.0, 2.0, 3.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        bb = g.bollinger(k, p["bb_periyot"], p["bb_sapma"])
        atr = g.atr(y, d, k, p["atr_periyot"])
        bw = (bb["ust"] - bb["alt"]) / bb["orta"]
        W = int(p["sikisma_pencere"])
        esik = bw.rolling(W, min_periods=W).quantile(p["sikisma_yuzdelik"] / 100.0)
        sik = (bw <= esik).astype(float).where(esik.notna())
        S = int(p["sikisma_son"])
        yakin = sik.shift(1).rolling(S, min_periods=1).max() == 1.0
        ok = yakin & (bw > bw.shift(1)) & atr.notna() & bb["orta"].notna()
        if p["hacim_k"] > 0:
            ok &= mumlar["hacim"] > p["hacim_k"] * mumlar["hacim"].shift(1).rolling(20, min_periods=20).mean()
        long_ok = ok & (k > bb["ust"]) & (k.shift(1) <= bb["ust"].shift(1))
        short_ok = ok & (k < bb["alt"]) & (k.shift(1) >= bb["alt"].shift(1)) & bool(p["short"])
        tampon = p["stop_tampon_atr"] * atr
        if p["stop_modu"] == "orta":
            stop_l, stop_s = bb["orta"] - tampon, bb["orta"] + tampon
        else:
            kutu_alt = d.shift(1).rolling(S + 1, min_periods=1).min()
            kutu_ust = y.shift(1).rolling(S + 1, min_periods=1).max()
            stop_l, stop_s = kutu_alt - tampon, kutu_ust + tampon
        if p["hedef_r"]:
            h_l = k + p["hedef_r"] * (k - stop_l)
            h_s = k - p["hedef_r"] * (stop_s - k)
        else:
            h_l = h_s = None
        cikis = ((k < bb["orta"]) & (k.shift(1) >= bb["orta"].shift(1))) | \
                ((k > bb["orta"]) & (k.shift(1) <= bb["orta"].shift(1)))
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis,
                       gun_sonu=True, seans_saat=p["seans_saat"])
