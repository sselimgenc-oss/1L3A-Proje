"""Jesse kaynak biçimlerinin araştırma uyarlamaları; mevcut stratejiler değişmez."""
from __future__ import annotations

import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.gostergeler_b1 import donchian_kanal
from motor.strateji.temel import Strateji


class DonchianS0002(Strateji):
    """S0002: önceki 20 mum Donchian üstünde kapanış ve SMA200 üstü long.

    Kaynak satırı: sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/ajan1/strateji_listesi.csv#S0002
    Link: https://github.com/jesse-ai/example-strategies/blob/master/Donchian/__init__.py
    Kaynak çıkışı: önceki Donchian alt bandı altında kapanış. Kaynak stopu yok;
    ATR(14)×3 felaket stopu 1L3A uyarlamasıdır. Kaynak TF 6h, short yok.
    """

    ad, stil = "kapanis__donchian-s0002", "swing"
    varsayilan_parametreler = {"kanal_n": 20, "trend_n": 200, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = mumlar["kapanis"]
        kanal = donchian_kanal(mumlar["yuksek"], mumlar["dusuk"], int(p["kanal_n"]))
        sma = g.sma(kap, int(p["trend_n"]))
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_n"]))
        gir = (kap > kanal["ust"]) & (kap > sma)
        cik = (kap < kanal["alt"]).fillna(False)
        sonuc = cerceve(mumlar, gir, False, kap - float(p["atr_k"]) * atr,
                        kap + float(p["atr_k"]) * atr)
        sonuc["cikis_long"] = cik
        return sonuc


class MacdEmaS0005(Strateji):
    """S0005: MACD çizgisi sinyalin üstünde VE fiyat EMA100 üstünde long.

    Kaynak satırı: sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/ajan1/strateji_listesi.csv#S0005
    Link: https://github.com/jesse-ai/example-strategies/blob/master/MACD_EMA/__init__.py
    Kaynak çıkışı iki şartın birlikte tersine dönmesidir: MACD sinyal altı VE
    kapanış EMA100 altı. Kaynak stopu yok; ATR(14)×3 felaket stopu uyarlamadır.
    Kaynak TF 1h, long-only, MACD(12,26,9).
    """

    ad, stil = "kapanis__macd-ema-s0005", "swing"
    varsayilan_parametreler = {"ema_n": 100, "macd_hizli": 12, "macd_yavas": 26,
                               "macd_sinyal": 9, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = mumlar["kapanis"]
        macd = g.macd(kap, int(p["macd_hizli"]), int(p["macd_yavas"]), int(p["macd_sinyal"]))
        ema = g.ema(kap, int(p["ema_n"]))
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_n"]))
        ust = macd["macd"] > macd["sinyal"]
        alt = macd["macd"] < macd["sinyal"]
        sonuc = cerceve(mumlar, ust & (kap > ema), False,
                        kap - float(p["atr_k"]) * atr, kap + float(p["atr_k"]) * atr)
        sonuc["cikis_long"] = (alt & (kap < ema)).fillna(False)
        return sonuc
