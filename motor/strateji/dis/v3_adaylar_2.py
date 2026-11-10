"""v3 adayları, parti 2: öncelik 2 tek-grafik stratejileri.

Kaynak kartlar ``stratejiler/v3_adaylar/kartlar`` altındadır. Üçüncü taraf
kod kopyalanmadı; kurallar strateji arayüzüyle yeniden yazıldı. Sinyaller mum
kapanışında hesaplanır ve sonraki mum açılışında dolar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji


def _cikis_cercevesi(m, long_ok, short_ok, stop_l, stop_s, hedef_l=None, hedef_s=None, cikis=None, zaman=None):
    out = cerceve(m, long_ok, short_ok, stop_l, stop_s, hedef_l, hedef_s, cikis)
    if zaman is not None:
        out["zaman_cikisi_mum"] = np.where(out["yon"] != 0, float(zaman), np.nan)
    return out


class AralikKirilimBekleyenEmir(Strateji):
    """00:00-07:00 UTC aralığının ilk kapanış kırılımı; karşı uç stop, 1R hedef.

    Kaynak: https://www.mql5.com/en/code/78688. Kaynaktaki sunucu saati UTC,
    20 puanlık sembole bağlı tampon ise 0.1 ATR kabul edildi. Bekleyen emrin
    mum içi dolum sırası bilinmediğinden kırılım kapanışla doğrulanır.
    """

    ad, stil = "v3__aralik-kirilim-bekleyen-emir", "daytrade"
    varsayilan_parametreler = {
        "kutu_bit": 7.0, "emir_iptal": 20.0, "cikis_saat": 22.0,
        "tampon_atr": 0.1, "atr_n": 14, "hedef_r": 1.0,
    }
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p, idx = self.parametreler, m.index
        saat = pd.Series(idx.hour + idx.minute / 60.0, index=idx)
        gun = pd.Series(idx.floor("D"), index=idx)
        kutu = saat < float(p["kutu_bit"])
        kh = m["yuksek"].where(kutu).groupby(gun).cummax().groupby(gun).ffill()
        kl = m["dusuk"].where(kutu).groupby(gun).cummin().groupby(gun).ffill()
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))
        ust, alt = kh + p["tampon_atr"] * atr, kl - p["tampon_atr"] * atr
        aktif = (saat >= p["kutu_bit"]) & (saat < p["emir_iptal"])
        lham, sham = aktif & (m["kapanis"] > ust), aktif & (m["kapanis"] < alt)
        olay = lham | sham
        ilk = olay & (olay.astype(int).groupby(gun).cumsum() == 1)
        long_ok, short_ok = ilk & lham, ilk & sham
        risk_l, risk_s = m["kapanis"] - alt, ust - m["kapanis"]
        hedef_l = m["kapanis"] + p["hedef_r"] * risk_l
        hedef_s = m["kapanis"] - p["hedef_r"] * risk_s
        # 5m mum 21:55'te kapanır; emir sonraki 22:00 açılışında çıkar.
        cikis = (idx.hour == int(p["cikis_saat"]) - 1) & (idx.minute == 55)
        return cerceve(m, long_ok, short_ok, alt, ust, hedef_l, hedef_s, pd.Series(cikis, index=idx))


class LSekliMaKirilimLong(Strateji):
    """20 mumluk düşüş ve üç mumluk sıkışma sonrası SMA100 üstüne boğa kırılımı.

    Kaynak: https://github.com/mgcha85/btc-lshape-long. MA türü kaynakta
    belirtilmediğinden SMA; düşüş, önceki 20 mumun tepe-dip aralığı olarak
    tanımlandı. Karttaki örnek profil TP %10 ve SL %5 ile yalnız longdur.
    """

    ad, stil = "v3__l-sekli-ma-kirilim-long", "daytrade"
    varsayilan_parametreler = {
        "ma_n": 100, "dusus_n": 20, "dusus_yuzde": 0.03,
        "sikisma_n": 3, "sikisma_yuzde": 0.05, "stop_yuzde": 0.05, "hedef_yuzde": 0.10,
    }
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        onceki = k.shift(1)
        tepe = onceki.rolling(int(p["dusus_n"]), min_periods=int(p["dusus_n"])).max()
        dip = onceki.rolling(int(p["dusus_n"]), min_periods=int(p["dusus_n"])).min()
        dusus = dip / tepe - 1.0 <= -float(p["dusus_yuzde"])
        sn = int(p["sikisma_n"])
        sikisma = (onceki.rolling(sn, min_periods=sn).max() / onceki.rolling(sn, min_periods=sn).min() - 1.0
                    <= float(p["sikisma_yuzde"]))
        ma = g.sma(k, int(p["ma_n"]))
        long_ok = dusus & sikisma & (k.shift(1) <= ma.shift(1)) & (k > ma) & (k > m["acilis"])
        return cerceve(m, long_ok, False, k * (1.0 - p["stop_yuzde"]), None,
                       k * (1.0 + p["hedef_yuzde"]), None, None)


class Orb4sHacimAtr(Strateji):
    """UTC gününün ilk 4 saatlik mumunu hacimli kıran simetrik ORB.

    Kaynak: https://github.com/saadtahir995/orb-trading-bot. Kaynakta eksik
    yön ve ATR periyodu simetrik long/short ve ATR(14) kabul edildi. Başlangıç
    stopu 2 ATR, motor çıkışı 1 ATR iz süren stoptur.
    """

    ad, stil = "v3__orb-4s-hacim-atr", "daytrade"
    varsayilan_parametreler = {"hacim_n": 20, "hacim_k": 1.5, "atr_n": 14, "stop_atr": 2.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=1.0, atr_periyot=14)

    def sinyaller(self, m):
        p, idx = self.parametreler, m.index
        gun = pd.Series(idx.floor("D"), index=idx)
        ilk = pd.Series(idx.hour == 0, index=idx)
        orh = m["yuksek"].where(ilk).groupby(gun).ffill()
        orl = m["dusuk"].where(ilk).groupby(gun).ffill()
        hv = m["hacim"].shift(1).rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean()
        hacimli = m["hacim"] >= float(p["hacim_k"]) * hv
        lham = ~ilk & (m["kapanis"] > orh) & hacimli
        sham = ~ilk & (m["kapanis"] < orl) & hacimli
        olay = lham | sham
        tek = olay & (olay.astype(int).groupby(gun).cumsum() == 1)
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))
        mesafe = float(p["stop_atr"]) * atr
        return cerceve(m, tek & lham, tek & sham, m["kapanis"] - mesafe, m["kapanis"] + mesafe, None, None, None)


def _aktif_boga_fvg(ust: pd.DataFrame) -> pd.DataFrame:
    """Her tamamlanmış üst mumdan sonra doldurulmamış son boğa FVG bölgesi."""
    h, l = ust["yuksek"].to_numpy(float), ust["dusuk"].to_numpy(float)
    alt = np.full(len(ust), np.nan)
    ust_kenar = np.full(len(ust), np.nan)
    a = u = np.nan
    for i in range(len(ust)):
        if np.isfinite(a) and l[i] <= a:
            a = u = np.nan
        if i >= 2 and l[i] > h[i - 2]:
            a, u = h[i - 2], l[i]
        alt[i], ust_kenar[i] = a, u
    return pd.DataFrame({"fvg_alt": alt, "fvg_ust": ust_kenar}, index=ust.index)


class TersFvgNqLong(Strateji):
    """Aktif 15m boğa FVG içinde oluşan 5m FVG retestinde long.

    Kaynak: https://github.com/prashanthaitha24/nq-strategy-b-bot. 15m değer
    yalnız mum kapandıktan sonra ``ust_zaman`` ile görünür. Kaynaktaki NQ sabit
    değerleri 5 puan bölge tamponu ve 2 puan stop tamponu olarak korunmuştur.
    """

    ad, stil = "v3__ters-fvg-nq-long", "daytrade"
    varsayilan_parametreler = {
        "ust_tf": "15m", "bolge_tampon": 5.0, "stop_tampon": 2.0,
        "hedef_r": 2.0, "seans_bas_saat": 9, "seans_bas_dakika": 30,
        "seans_bit_saat": 12, "cikis_saat": 15, "cikis_dakika": 45,
    }
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p, idx = self.parametreler, m.index
        ana = ust_zaman(m, p["ust_tf"], _aktif_boga_fvg)
        h, l, k = (m[c].to_numpy(float) for c in ("yuksek", "dusuk", "kapanis"))
        pa, pu = ana["fvg_alt"].to_numpy(float), ana["fvg_ust"].to_numpy(float)
        ny = idx.tz_convert("America/New_York")
        dakika = ny.hour * 60 + ny.minute
        bas = int(p["seans_bas_saat"]) * 60 + int(p["seans_bas_dakika"])
        bit = int(p["seans_bit_saat"]) * 60
        seans = (dakika >= bas) & (dakika < bit)
        tarih = ny.date
        yon = np.zeros(len(m), dtype="int64")
        stop = np.full(len(m), np.nan)
        hedef = np.full(len(m), np.nan)
        a = u = np.nan
        islem_gunu = None
        for i in range(2, len(m)):
            if np.isfinite(a) and l[i] < a:
                a = u = np.nan
            # Retest yalnız FVG oluştuktan sonraki mumlarda değerlendirilir.
            if (seans[i] and tarih[i] != islem_gunu and np.isfinite(a)
                    and l[i] <= u and l[i] >= a and k[i] > u):
                yon[i] = 1
                stop[i] = a - float(p["stop_tampon"])
                hedef[i] = k[i] + float(p["hedef_r"]) * (k[i] - stop[i])
                islem_gunu = tarih[i]
                a = u = np.nan
            if (seans[i] and np.isfinite(pa[i]) and np.isfinite(pu[i]) and l[i] > h[i - 2]
                    and h[i - 2] >= pa[i] and l[i] <= pu[i] + float(p["bolge_tampon"])):
                a, u = h[i - 2], l[i]
        cikis_dk = int(p["cikis_saat"]) * 60 + int(p["cikis_dakika"])
        # Çıkış emri bir önceki 5m mumun kapanışında verilir.
        cikis = pd.Series(dakika == cikis_dk - 5, index=idx)
        long_ok = pd.Series(yon == 1, index=idx)
        return cerceve(m, long_ok, False, pd.Series(stop, index=idx), None,
                       pd.Series(hedef, index=idx), None, cikis)


class Rsi2Sma200GeriCekilme(Strateji):
    """SMA200 üstünde RSI(2)<10 long; RSI>70 veya beş mumda çıkış.

    Kaynak: https://github.com/ZacharyToney/tradingbot. Kaynakta stop yok;
    havuzdaki günlük ortalamaya dönüş ailesinden ATR(14)*3 felaket stopu alındı.
    """

    ad, stil = "v3__rsi2-sma200-geri-cekilme", "swing"
    varsayilan_parametreler = {
        "rsi_n": 2, "rsi_giris": 10.0, "rsi_cikis": 70.0,
        "sma_n": 200, "maks_tutma": 5, "atr_n": 14, "atr_k": 3.0,
    }
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        atr = g.atr(m["yuksek"], m["dusuk"], k, int(p["atr_n"]))
        long_ok = (k > g.sma(k, int(p["sma_n"]))) & (r < float(p["rsi_giris"]))
        cikis = r > float(p["rsi_cikis"])
        return _cikis_cercevesi(m, long_ok, False, k - float(p["atr_k"]) * atr, None,
                                cikis=cikis, zaman=int(p["maks_tutma"]))
