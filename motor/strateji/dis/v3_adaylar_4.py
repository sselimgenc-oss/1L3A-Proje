"""v3 parti 4: gün içi noise alanı ve BTC gece seansı."""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.seans_takvimi import _abd_tatilleri, _nyse_erken_kapanis
from motor.strateji.temel import Strateji


class GuniciMomentumNoise(Strateji):
    """Zarattini gün içi noise alanı, 30 dakikalık DK_SPX uyarlaması.

    Kaynak: https://github.com/PazSheimy/spy-intraday-momentum-oos
    Bant yalnız geçmiş 14 seansın aynı HH:MM yüzde hareketinden hesaplanır.
    Giriş yalnız banda bağlıdır; VWAP, açık pozisyonun çıkış çizgisidir.
    """

    ad, stil = "v3__gunici-momentum-noise-alani", "daytrade"
    varsayilan_parametreler = {"gun": 14, "bant_k": 1.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        idx = m.index
        ny = idx.tz_convert("America/New_York")
        tarih = pd.Series(ny.date, index=idx)
        saat = pd.Series(ny.hour * 60 + ny.minute, index=idx)
        # DK_SPX 30m: yalnız ABD nakit seansındaki mumlar kullanılır.
        aktif = (saat >= 570) & (saat < 960) & (ny.day_of_week < 5)
        ac = m["acilis"].where(aktif).groupby(tarih).transform("first")
        sapma = (m["kapanis"] / ac - 1.0).abs().where(aktif)
        slot = pd.Series(saat.to_numpy(), index=idx)
        sigma = sapma.groupby(slot).transform(
            lambda s: s.shift(1).rolling(int(self.parametreler["gun"]), min_periods=int(self.parametreler["gun"])).mean()
        ) * float(self.parametreler["bant_k"])
        gunluk_kapanis = m["kapanis"].where(aktif).groupby(tarih).last()
        onceki_gun = gunluk_kapanis.shift(1)
        onceki_kapanis = pd.Series(onceki_gun.reindex(tarih.to_numpy()).to_numpy(), index=idx)
        vwap = g.vwap_seans(m["yuksek"], m["dusuk"], m["kapanis"],
                            m["hacim"].where(aktif, 0.0), tarih.to_numpy())["vwap"]
        k = m["kapanis"]
        ust = pd.concat([ac, onceki_kapanis], axis=1).max(axis=1) * (1.0 + sigma)
        alt = pd.concat([ac, onceki_kapanis], axis=1).min(axis=1) * (1.0 - sigma)
        long_ok = aktif & (k > ust)
        short_ok = aktif & (k < alt)
        stop_l = pd.concat([ust, vwap], axis=1).max(axis=1)
        stop_s = pd.concat([alt, vwap], axis=1).min(axis=1)
        # 15:30 açılışlı 30m mum 16:00'da kapanır; o mumda yeni giriş yoktur.
        cikis = aktif & (saat >= 930)
        out = cerceve(m, long_ok & ~cikis, short_ok & ~cikis, stop_l, stop_s, cikis=cikis)
        out["cikis_long"] = (k < stop_l) | cikis
        out["cikis_short"] = (k > stop_s) | cikis
        return out


class BtcGecelikMax10(Strateji):
    """Kaynak: https://quantpedia.com/how-to-profitably-trade-bitcoins-overnight-sessions/"""

    ad, stil = "v3__btc-gecelik-max10-hafta-sonu", "swing"
    varsayilan_parametreler = {"gun": 10, "atr_n": 14, "atr_k": 2.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        idx = m.index
        ny = idx.tz_convert("America/New_York")
        tarih = pd.Series(ny.date, index=idx)
        # Geçmiş 10 tamamlanmış takvim günü; boş günler kriptoda oluşmaz.
        ozet = m["yuksek"].groupby(tarih).max()
        onceki = ozet.shift(1).rolling(int(self.parametreler["gun"]), min_periods=int(self.parametreler["gun"])).max()
        zirve = pd.Series(onceki.reindex(tarih.to_numpy()).to_numpy(), index=idx)
        saat = ny.hour * 60 + ny.minute
        tatil = np.array([d in _abd_tatilleri(d.year) for d in ny.date])
        erken = np.array([_nyse_erken_kapanis(d) for d in ny.date])
        kapanis = np.where(erken, 780, 960)
        # 1h mum açılış zamanlıdır; 16:00 kapanışı 15:00 mumunda bilinir.
        giris = (ny.day_of_week <= 4) & np.isin(ny.day_of_week, [0, 1, 4]) & ~tatil & ~erken & (saat == kapanis - 60)
        long_ok = giris & (m["kapanis"] >= zirve)
        # Pazartesi/Salı/Çarşamba 10:00 açılışında çıkmak için 09:00 mum kapanışı.
        cikis = pd.Series((ny.day_of_week < 3) & ~tatil & (saat == 540), index=idx)
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(self.parametreler["atr_n"]))
        return cerceve(m, long_ok, False, m["kapanis"] - atr * self.parametreler["atr_k"],
                       m["kapanis"] + atr * self.parametreler["atr_k"], cikis=cikis)
