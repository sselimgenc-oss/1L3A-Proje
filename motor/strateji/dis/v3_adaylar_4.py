"""v3 parti 4: gün içi noise alanı ve BTC gece seansı."""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, gun_sonu_kapanis_ekle
from motor.strateji.seans_takvimi import _abd_tatilleri, _nyse_erken_kapanis
from motor.strateji.temel import Strateji


class GuniciMomentumNoise(Strateji):
    """Zarattini gün içi noise alanı, 30 dakikalık DK_SPX uyarlaması.

    Kaynak: https://github.com/PazSheimy/spy-intraday-momentum-oos
    Bant yalnız geçmiş 14 seansın aynı HH:MM yüzde hareketinden hesaplanır.
    Giriş yalnız banda bağlıdır; VWAP, açık pozisyonun çıkış çizgisidir.

    Çıkış kaynakla aynıdır ve KAPANIŞ tabanlıdır: her 30 dk mum kapanışında long için
    kapanış < o andaki max(UB, VWAP), short için kapanış > o andaki min(LB, VWAP);
    ayrıca gün sonu. Motorun mum-içi stopu bizim eklememizdir: giriş kapanışı -/+ 1 x
    günlük ATR(14) felaket stopu; günlük ATR yalnız TAMAMLANMIŞ önceki nakit seansların
    (09:30-16:00 ET) yüksek/düşük/kapanışından hesaplanır (bugünkü seans dahil değil).
    Gün sonu çıkışı: 15:30 açılışlı mum (kapanışı 16:00 ET) gün sonu bayrağı taşır; motor
    pozisyonu o mumun KAPANIŞ fiyatından (= 16:00 fiyatı) kapatır, 16:00 mumunun varlığına
    ya da gece boşluğuna bağlı değildir (DK_SPX 24/5 CFD: 16:00 mumu bazı günlerde yok).
    """

    ad, stil = "v3__gunici-momentum-noise-alani", "daytrade"
    varsayilan_parametreler = {"gun": 14, "bant_k": 1.0, "atr_n": 14, "atr_k": 1.0}
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
        # Kaynağın çıkış çizgisi: her mumda CARİ max(UB, VWAP) / min(LB, VWAP).
        cizgi_l = pd.concat([ust, vwap], axis=1).max(axis=1)
        cizgi_s = pd.concat([alt, vwap], axis=1).min(axis=1)
        # Günlük ATR(14): yalnız tamamlanmış önceki nakit seanslar (shift(1) ile bugün dışarıda).
        gh = m["yuksek"].where(aktif).groupby(tarih).max().dropna()
        gl = m["dusuk"].where(aktif).groupby(tarih).min().dropna()
        gc = gunluk_kapanis.dropna()
        gatr = g.atr(gh, gl, gc, int(self.parametreler["atr_n"])).shift(1)
        atr = pd.Series(gatr.reindex(tarih.to_numpy()).to_numpy(), index=idx)
        felaket = float(self.parametreler["atr_k"]) * atr
        # 15:30 açılışlı 30m mum 16:00'da kapanır; o mumda yeni giriş yoktur.
        cikis = aktif & (saat >= 930)
        out = cerceve(m, long_ok & ~cikis, short_ok & ~cikis, k - felaket, k + felaket, cikis=cikis)
        out["cikis_long"] = (k < cizgi_l) | cikis
        out["cikis_short"] = (k > cizgi_s) | cikis
        # Gün sonu: pozisyon 15:30 mumunun kapanışından (16:00 ET fiyatı) kapanır.
        return gun_sonu_kapanis_ekle(out, cikis.to_numpy())


def islem_gunleri(baslangic, bitis) -> pd.DatetimeIndex:
    """[baslangic, bitis] arası NYSE işlem günleri (hafta içi, ABD borsa tatilleri hariç; erken kapanış günleri DAHİL)."""
    gunler = pd.bdate_range(pd.Timestamp(baslangic).normalize(), pd.Timestamp(bitis).normalize())
    return gunler[[d.date() not in _abd_tatilleri(d.year) for d in gunler]]


class BtcGecelikMax10(Strateji):
    """Kaynak: https://quantpedia.com/how-to-profitably-trade-bitcoins-overnight-sessions/

    Ön kayıt: MAX(10) = 16:00 ET kapanışı, önceki 10 NYSE işlem gününün 16:00 ET kapanışlarının
    en yükseğine eşit ya da üstündeyse (bugün dahil değil) Cuma/Pzt/Salı gecesi long.
    16:00 kapanışı = 15:00 ET açılışlı 1h mumun kapanışı. Pencerede eksik gün (veri yok) varsa sinyal yok.
    Stop kaynakta yok; bizim eklememiz: giriş kapanışı - 2 x günlük ATR(14); günlük çubuklar
    tamamlanmış önceki NY takvim günlerinin (24 saat) yüksek/düşük/kapanışından, nedensel.
    """

    ad, stil = "v3__btc-gecelik-max10-hafta-sonu", "swing"
    varsayilan_parametreler = {"gun": 10, "atr_n": 14, "atr_k": 2.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        idx = m.index
        ny = idx.tz_convert("America/New_York")
        tarih = pd.Series(ny.date, index=idx)
        saat = ny.hour * 60 + ny.minute
        n = int(self.parametreler["gun"])
        tatil = np.array([d in _abd_tatilleri(d.year) for d in ny.date])
        erken = np.array([_nyse_erken_kapanis(d) for d in ny.date])
        # Her NYSE işlem gününün 16:00 ET kapanışı (15:00 ET açılışlı 1h mumun kapanışı).
        islem = (ny.day_of_week <= 4) & ~tatil
        k16 = pd.Series(m["kapanis"].to_numpy()[islem & (saat == 900)],
                        index=pd.DatetimeIndex(pd.to_datetime(np.asarray(ny.date)[islem & (saat == 900)])))
        gunler = islem_gunleri(ny[0].date(), ny[-1].date())
        k16 = k16.reindex(gunler)   # eksik gün NaN: pencere tam değilse zirve NaN, sinyal yok
        # Önceki n işlem günü (bugün dışarıda: shift(1)); yalnız tamamlanmış günler.
        zirve_gun = k16.shift(1).rolling(n, min_periods=n).max()
        zirve = pd.Series(zirve_gun.reindex(pd.DatetimeIndex(pd.to_datetime(np.asarray(ny.date)))).to_numpy(), index=idx)
        kapanis = np.where(erken, 780, 960)
        # 1h mum açılış zamanlıdır; 16:00 kapanışı 15:00 mumunda bilinir.
        giris = np.isin(ny.day_of_week, [0, 1, 4]) & ~tatil & ~erken & (saat == kapanis - 60)
        long_ok = giris & (m["kapanis"] >= zirve)
        # Pazartesi/Salı/Çarşamba 10:00 açılışında çıkmak için 09:00 mum kapanışı.
        cikis = pd.Series((ny.day_of_week < 3) & ~tatil & (saat == 540), index=idx)
        # Günlük ATR(14): tamamlanmış önceki NY takvim günleri (24 saat yüksek/düşük/kapanış).
        gh = m["yuksek"].groupby(tarih).max()
        gl = m["dusuk"].groupby(tarih).min()
        gc = m["kapanis"].groupby(tarih).last()
        gatr = g.atr(gh, gl, gc, int(self.parametreler["atr_n"])).shift(1)
        atr = pd.Series(gatr.reindex(tarih.to_numpy()).to_numpy(), index=idx)
        k = float(self.parametreler["atr_k"])
        return cerceve(m, long_ok, False, m["kapanis"] - atr * k, m["kapanis"] + atr * k, cikis=cikis)
