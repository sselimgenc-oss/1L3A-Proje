"""RSI(32) kaynak kodundaki dönüş çıkışının kapanış turu uyarlaması."""
from __future__ import annotations

import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis.v3_adaylar_3 import Rsi32Yon


class Rsi32Kaynak(Rsi32Yon):
    """RSI50 yön; 4% hedef; 77/23 geriye kesişim ve 85/15 uç çıkışı.

    Kaynak satırı: stratejiler/v3_adaylar/kartlar/daytrade__rsi32-yon-hedef4-btc-1h__noahroboros.json
    Birincil kod: https://github.com/upupnoah/noahroboros/blob/main/src/strategy/baseline.rs
    Kaynak `baseline.rs` 280-318: long 77'nin üstünden altına, short 23'ün
    altından üstüne dönünce çıkış; ayrıca 85/15 uç çıkışı. Eski v3 sınıfı
    77/23'e ilk erişimde çıkıyordu. Kaynakta fiyat stopu kapalıdır; ATR(14)×3
    felaket stopu bu turun açık uyarlamasıdır.
    """

    ad = "kapanis__rsi32-kaynak"
    parametre_izgarasi = {}

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kapanis = mumlar["kapanis"]
        rsi = g.rsi(kapanis, int(p["rsi_n"]))
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kapanis, int(p["atr_n"]))
        mesafe = float(p["atr_k"]) * atr
        sonuc = cerceve(
            mumlar, rsi > p["orta"], rsi < p["orta"],
            kapanis - mesafe, kapanis + mesafe,
            kapanis * (1.0 + float(p["hedef"])),
            kapanis * (1.0 - float(p["hedef"])),
        )
        sonuc["cikis_long"] = (
            ((rsi.shift(1) >= p["cikis_ust"]) & (rsi < p["cikis_ust"]))
            | (rsi >= p["guven_ust"])
        ).fillna(False)
        sonuc["cikis_short"] = (
            ((rsi.shift(1) <= p["cikis_alt"]) & (rsi > p["cikis_alt"]))
            | (rsi <= p["guven_alt"])
        ).fillna(False)
        return sonuc
