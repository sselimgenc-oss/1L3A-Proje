"""v3 adayları, parti 1.

Kaynak kartlar ``stratejiler/v3_adaylar/kartlar`` altındadır. Üçüncü taraf kodu
kopyalanmadı; mekanik kurallar proje strateji arayüzüyle yeniden yazıldı. Mum
indeksi açılış zamanıdır, sinyal mum kapanışında hesaplanır ve sonraki açılışta
dolar. Kaynakta stop olmayan kurallara ATR felaket stopu eklendi.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve, seans_kimligi, seans_son_mumu
from motor.strateji.dis._gosterge_d11g import trix
from motor.strateji.temel import Strateji


def _atr_cerceve(m, long_ok, short_ok, atr_k=2.0, atr_n=14, hedef_r=0.0, zaman=None, cikis=None):
    k = m["kapanis"]
    a = g.atr(m["yuksek"], m["dusuk"], k, int(atr_n)) * float(atr_k)
    hedef_l = k + float(hedef_r) * a if hedef_r else None
    hedef_s = k - float(hedef_r) * a if hedef_r else None
    out = cerceve(m, long_ok, short_ok, k - a, k + a, hedef_l, hedef_s, cikis)
    if zaman is not None:
        out["zaman_cikisi_mum"] = pd.Series(
            np.where(out["yon"] != 0, float(zaman), np.nan), index=m.index
        )
    return out


class AsyaKutuKirilimMa50(Strateji):
    """23:00-03:00 UTC kutusu; SMA50 yönünde ilk kapanış kırılımı, 13:00 çıkışı.

    Kaynak: https://www.mql5.com/ja/articles/17239. Bekleyen emrin mum içi
    sırasını OHLC ile varsaymamak için kırılım kapanışta doğrulanır. Kaynaktaki
    belirsiz 10 point sapma yerine 0.1 ATR tampon kullanılır.
    """

    ad, stil = "v3__asya-kutu-kirilim-ma50", "daytrade"
    varsayilan_parametreler = {
        "kutu_bas": 23.0, "kutu_bit": 3.0, "cikis_saat": 13.0, "ma_n": 50,
        "tampon_atr": 0.1, "atr_n": 14, "hedef_r": 1.3,
    }
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p, idx = self.parametreler, m.index
        saat = pd.Series(idx.hour + idx.minute / 60.0, index=idx)
        sid = pd.Series(seans_kimligi(idx, p["kutu_bas"]), index=idx)
        rel = (saat - p["kutu_bas"]) % 24.0
        kutu_sure = (p["kutu_bit"] - p["kutu_bas"]) % 24.0
        kutu = rel < kutu_sure
        yuk = m["yuksek"].where(kutu).groupby(sid).cummax()
        dus = m["dusuk"].where(kutu).groupby(sid).cummin()
        kh = yuk.groupby(sid).ffill()
        kl = dus.groupby(sid).ffill()
        aktif = (rel >= kutu_sure) & (rel < ((p["cikis_saat"] - p["kutu_bas"]) % 24.0))
        a = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))
        ma = g.sma(m["kapanis"], int(p["ma_n"]))
        ust, alt = kh + p["tampon_atr"] * a, kl - p["tampon_atr"] * a
        lham = aktif & (m["kapanis"] > ma) & (m["kapanis"] > ust)
        sham = aktif & (m["kapanis"] < ma) & (m["kapanis"] < alt)
        olay = lham | sham
        ilk = olay & (olay.astype(int).groupby(sid).cumsum() == 1)
        long_ok, short_ok = ilk & lham, ilk & sham
        risk_l, risk_s = m["kapanis"] - alt, ust - m["kapanis"]
        hedef_l = m["kapanis"] + p["hedef_r"] * risk_l
        hedef_s = m["kapanis"] - p["hedef_r"] * risk_s
        cikis = aktif.shift(1, fill_value=False) & ~aktif
        return cerceve(m, long_ok, short_ok, alt, ust, hedef_l, hedef_s, cikis)


class Saat2123Utc(Strateji):
    """Her gün 21:00 UTC açılışında long, iki saat tut.

    Kaynak: https://quantpedia.com/are-there-seasonal-intraday-or-overnight-anomalies-in-bitcoin/
    Sinyal önceki mum kapanışında verilir. Kaynakta stop yok; 2 ATR kullanılır.
    """

    ad, stil = "v3__saat-21-23-utc", "daytrade"
    varsayilan_parametreler = {"giris_saat": 21, "tut_mum": 2, "atr_k": 2.0, "atr_n": 14}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        idx = m.index
        if len(idx) < 2:
            return _atr_cerceve(m, False, False, self.parametreler["atr_k"], self.parametreler["atr_n"], zaman=2)
        fark = ((idx[1:] - idx[:-1]) / pd.Timedelta(seconds=1)).to_numpy()
        sure = np.r_[np.nan, np.minimum.accumulate(fark)]
        kapanis = idx + pd.to_timedelta(np.nan_to_num(sure), unit="s")
        ok = pd.Series((kapanis.hour == int(self.parametreler["giris_saat"])) & np.isfinite(sure), index=idx)
        return _atr_cerceve(m, ok, False, self.parametreler["atr_k"], self.parametreler["atr_n"],
                            zaman=int(self.parametreler["tut_mum"]))


class SaatlikAsiriTepki(Strateji):
    """Bir saatlik getiri önceki 48 saatin 2 standart sapmasını aşınca ters yön.

    Kaynak: https://epub.ub.uni-muenchen.de/97651/. Kaynakta bulunmayan eşik,
    stop ve süre için standart 2 sigma, 2 ATR ve bir mum seçildi.
    """

    ad, stil = "v3__saatlik-asiri-tepki", "daytrade"
    varsayilan_parametreler = {"sigma_n": 48, "k": 2.0, "tut_mum": 1, "atr_k": 2.0, "atr_n": 14}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        r = m["kapanis"].pct_change()
        sd = r.shift(1).rolling(int(p["sigma_n"]), min_periods=int(p["sigma_n"])).std()
        return _atr_cerceve(m, r < -p["k"] * sd, r > p["k"] * sd, p["atr_k"], p["atr_n"],
                            zaman=int(p["tut_mum"]))


class AdaptiveTrend6s(Strateji):
    """6 saatlik momentum ve ATR iz stopunun tek-grafik çekirdeği.

    Kaynak: https://arxiv.org/html/2602.11708v1. Eksik L/theta/ATR değerleri
    20 mum, sıfır ve ATR(14)*3 olarak sabitlendi. Aylık evren seçimi ve 70/30
    tahsis portföy katmanının işidir; bu sınıf yön sinyalini üretir.
    """

    ad, stil = "v3__adaptivetrend-6s-momentum", "swing"
    varsayilan_parametreler = {"mom_n": 20, "esik": 0.0, "atr_k": 3.0, "atr_n": 14, "short": True}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        mom = m["kapanis"].pct_change(int(p["mom_n"]))
        short = mom < -p["esik"] if p["short"] else pd.Series(False, index=m.index)
        out = _atr_cerceve(m, mom > p["esik"], short, p["atr_k"], p["atr_n"])
        out["cikis_long"] = (mom <= 0).fillna(False)
        out["cikis_short"] = (mom >= 0).fillna(False)
        return out


class DonchianAnsambl(Strateji):
    """20/55/100 günlük Donchian oylarının long-only ansamblı.

    Kaynak: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5209907.
    Özet sayfasında bulunmayan pencereler havuzdaki Turtle/Donchian standartlarıdır.
    Boyutlandırma motorun stop riskine bırakılır; 3 ATR stop zorunlu korunmadır.
    """

    ad, stil = "v3__donchian-ansambl-vol-hedef", "swing"
    varsayilan_parametreler = {"pencereler": (20, 55, 100), "cikis_n": 20, "atr_k": 3.0, "atr_n": 14}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        oy = pd.Series(0, index=m.index, dtype="int64")
        for n in p["pencereler"]:
            oy += (k > m["yuksek"].shift(1).rolling(int(n), min_periods=int(n)).max()).astype(int)
        cikis = k < m["dusuk"].shift(1).rolling(int(p["cikis_n"]), min_periods=int(p["cikis_n"])).min()
        return _atr_cerceve(m, oy >= 2, False, p["atr_k"], p["atr_n"], cikis=cikis)


class HaftalikSmaTrixKirilim(Strateji):
    """30 SMA trendinde 20 haftalık kırılım ve TRIX teyidi.

    Kaynak: https://github.com/ccadic/yahoo-weekly-trading-bot (GPL; kod
    kopyalanmadı). Eksik TRIX/ATR değerleri 15/9 ve 14; piyasa endeksi ayrı
    seri gerektirdiğinden tek-grafik çekirdekte hisse kendi SMA30 filtresini kullanır.
    """

    ad, stil = "v3__haftalik-sma-trix-kirilim", "swing"
    varsayilan_parametreler = {"sma_n": 30, "donchian_n": 20, "trix_n": 15, "trix_sinyal": 9,
                               "cikis_ema": 10, "cikis_dip": 10, "atr_k": 2.0, "atr_n": 14}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p, k = self.parametreler, m["kapanis"]
        sma = g.sma(k, int(p["sma_n"]))
        tx = trix(k, int(p["trix_n"]))
        ts = g.ema(tx, int(p["trix_sinyal"]))
        tepe = m["yuksek"].shift(1).rolling(int(p["donchian_n"]), min_periods=int(p["donchian_n"])).max()
        long_ok = (k > sma) & (sma > sma.shift(1)) & (k > tepe) & (tx > ts)
        cikis = (k < g.ema(k, int(p["cikis_ema"]))) | (
            k < m["dusuk"].shift(1).rolling(int(p["cikis_dip"]), min_periods=int(p["cikis_dip"])).min()
        )
        return _atr_cerceve(m, long_ok, False, p["atr_k"], p["atr_n"], cikis=cikis)


class KirmiziMumHacim(Strateji):
    """Kırmızı mum ve önceki 60 gün ortalamasının 2 katı hacim sonrası bir gün long.

    Kaynak: https://habr.com/ru/articles/960670/. Kaynakta stop yok; 2 ATR.
    """

    ad, stil = "v3__kirmizi-mum-2x-hacim", "swing"
    varsayilan_parametreler = {"hacim_n": 60, "hacim_k": 2.0, "tut_mum": 1, "atr_k": 2.0, "atr_n": 14}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        hv = m["hacim"].shift(1).rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean()
        ok = (m["kapanis"] < m["acilis"]) & (m["hacim"] >= p["hacim_k"] * hv)
        return _atr_cerceve(m, ok, False, p["atr_k"], p["atr_n"], zaman=int(p["tut_mum"]))


class VolatiliteKirilimK05(Strateji):
    """Önceki seans aralığının yarısı üstündeki gün içi kırılım.

    Kaynak: https://mskim8717.tistory.com/122. Günlük OHLC'de mum içi sıra
    bilinmediğinden gün içi mumlarda kapanışla doğrulanır. Kaynakta stop yok;
    2 ATR stop kullanılır ve seans değişiminde çıkılır.
    """

    ad, stil = "v3__volatilite-kirilim-k05", "swing"
    varsayilan_parametreler = {"k": 0.5, "trend_n": 3, "atr_k": 2.0, "atr_n": 14, "seans_saat": 0.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p, idx = self.parametreler, m.index
        sid = pd.Series(seans_kimligi(idx, p["seans_saat"]), index=idx)
        gby = m.groupby(sid)
        ozet = pd.DataFrame({"h": gby["yuksek"].max(), "l": gby["dusuk"].min(),
                             "c": gby["kapanis"].last()})
        onceki = ozet.shift(1)
        ac = gby["acilis"].transform("first")
        h = pd.Series(onceki["h"].reindex(sid).to_numpy(), index=idx)
        l = pd.Series(onceki["l"].reindex(sid).to_numpy(), index=idx)
        trend = ozet["c"].shift(1).rolling(int(p["trend_n"]), min_periods=int(p["trend_n"])).mean()
        tr = pd.Series(trend.reindex(sid).to_numpy(), index=idx)
        seviye = ac + p["k"] * (h - l)
        ham = (ac > tr) & (m["kapanis"] > seviye)
        ilk = ham & (ham.astype(int).groupby(sid).cumsum() == 1)
        cikis = pd.Series(seans_son_mumu(idx, p["seans_saat"]), index=idx)
        return _atr_cerceve(m, ilk, False, p["atr_k"], p["atr_n"], cikis=cikis)
