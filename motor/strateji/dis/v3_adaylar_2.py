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


def _saatten_onceki_son_kapanis(index: pd.DatetimeIndex, saat: int, dakika: int = 0,
                                 zaman_dilimi: str = "UTC") -> pd.Series:
    """Hedef saatten önceki son mum kapanışını, yalnız o ana kadarki indeks farklarıyla işaretler."""
    if len(index) < 2:
        return pd.Series(False, index=index)
    fark = ((index[1:] - index[:-1]) / pd.Timedelta(seconds=1)).to_numpy()
    sure_sn = np.r_[np.nan, np.minimum.accumulate(fark)]
    gecerli = np.isfinite(sure_sn) & (sure_sn > 0)
    sure = pd.to_timedelta(np.where(gecerli, sure_sn, 0.0), unit="s")
    kapanis = index + sure
    yerel = kapanis.tz_convert(zaman_dilimi)
    hedef = yerel.normalize() + pd.Timedelta(hours=int(saat), minutes=int(dakika))
    sonraki_teorik_kapanis = kapanis + sure
    sonuc = gecerli & (kapanis <= hedef.tz_convert("UTC")) & (sonraki_teorik_kapanis > hedef.tz_convert("UTC"))
    return pd.Series(sonuc, index=index)


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
        cikis = _saatten_onceki_son_kapanis(idx, int(p["cikis_saat"]))
        return cerceve(m, long_ok, short_ok, alt, ust, hedef_l, hedef_s, cikis)


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
    """UTC gününün ilk dört saatini hacimli kıran simetrik ORB.

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
        if len(idx) < 2:
            raise ValueError("v3__orb-4s-hacim-atr: mum süresi için en az iki mum gerekli")
        fark = pd.TimedeltaIndex(idx[1:] - idx[:-1])
        sure = pd.Timedelta(fark.value_counts().idxmax())
        if sure <= pd.Timedelta(0) or sure > pd.Timedelta(hours=4) or pd.Timedelta(hours=4) % sure:
            raise ValueError(f"v3__orb-4s-hacim-atr: mum süresi ilk 4 saati tam bölmeli; bulunan {sure}")
        gun = pd.Series(idx.floor("D"), index=idx)
        ilk = pd.Series(idx.hour < 4, index=idx)
        orh = m["yuksek"].where(ilk).groupby(gun).cummax().groupby(gun).ffill()
        orl = m["dusuk"].where(ilk).groupby(gun).cummin().groupby(gun).ffill()
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
        cikis = _saatten_onceki_son_kapanis(
            idx, int(p["cikis_saat"]), int(p["cikis_dakika"]), "America/New_York"
        )
        long_ok = pd.Series(yon == 1, index=idx)
        return cerceve(m, long_ok, False, pd.Series(stop, index=idx), None,
                       pd.Series(hedef, index=idx), None, cikis)
