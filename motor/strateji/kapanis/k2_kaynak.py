"""Kapanış turu K2 (hakem kısa listesi): kuralı tam olan kaynak biçimleri.

Her sınıf kendi cümleleriyle yazılmış bir uyarlamadır; üçüncü taraf kodu kopyalanmadı.
Mevcut sınıflara dokunulmaz. Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor).
Kaynak stopu yoksa ATR(14)x3 felaket stopu = "uyarlama" (ön kayıt).

- DonchianEma2RS0083  : MQL5 Code Base 77691 (Gold Breakout EA), H4, long, 2xATR(20) stop, 2R hedef.
- FlipperS0879        : Radge 'Unholy Grails' 20% Flipper, ekansh111/unholy-grails-momentum (lisanssız, yalnız kural).
- VmaBantKaynak       : T21/S0395 Campbell WCE 2011 VMA (S,L,B) kuralları; 10 kural VMA_KURALLARI.
- IchimokuC4Arsiv     : arsiv/swing-sg/deneyler/codex_adaylar.py c4_ichimoku (ham, haftalık yön/rejim filtresiz).
- ArgusGizliBoga D3   : arsiv/swing-sg/deneyler/codex2_adaylar.py d3_gizli_uyumsuzluk (ham).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.gostergeler_b1 import donchian_kanal
from motor.strateji.temel import Strateji


def _atr_sma(mumlar: pd.DataFrame, n: int) -> pd.Series:
    """MT5 iATR: gerçek aralığın basit ortalaması."""
    tr = g.gercek_aralik(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"])
    return tr.rolling(n, min_periods=n).mean()


class DonchianEma2RS0083(Strateji):
    """S0083: H4 kapanış önceki 20 mumun en yükseğini AŞAR (önceki mum aşmamıştı) ve kapanış > EMA200 -> long.

    Stop 2xATR(20) (kaynakta var), hedef 2R, short kapalı. Kaynak XAUUSD; kripto13'e uyarlama.
    Kaynak: https://www.mql5.com/en/code/77691 (sayfa metni). Dolumda stop/hedef kaynakta gerçek dolumdan
    hesaplanır; burada sinyal kapanışından (uyarlama).
    """

    ad, stil = "kapanis__donchian-ema-2r-s0083", "swing"
    varsayilan_parametreler = {"kanal_n": 20, "ema_n": 200, "atr_n": 20, "atr_k": 2.0, "hedef_r": 2.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = mumlar["kapanis"]
        kanal = donchian_kanal(mumlar["yuksek"], mumlar["dusuk"], int(p["kanal_n"]))
        asti = (kap > kanal["ust"]).fillna(False)
        ilk = asti & ~asti.shift(1, fill_value=False)
        ema = g.ema(kap, int(p["ema_n"]))
        atr = _atr_sma(mumlar, int(p["atr_n"]))
        risk = float(p["atr_k"]) * atr
        return cerceve(mumlar, ilk & (kap > ema), False, kap - risk, kap + risk,
                       hedef_l=kap + float(p["hedef_r"]) * risk)


class FlipperS0879(Strateji):
    """20% Flipper: son salınım dibinden (gün içi dipler) KAPANIŞ %20 yükselince al; giriş sonrası gün içi
    tepeden kapanış %20 düşünce sat. Koruyucu stop: giriş gününün tepesinin %20 altı.

    Zigzag durumu yalnız geçmiş mumlardan (sanal pozisyon) yürür; giriş sinyali geçiş mumunda,
    çıkış (cikis_long) geçiş mumunda verilir. Endeks filtresi (hisse) uygulanmaz: ham sürüm.
    Kaynak: github.com/ekansh111/unholy-grails-momentum docs/STRATEGY_SPEC.md ve src/strategies.py (_flipper_zigzag).
    """

    ad, stil = "kapanis__flipper-s0879", "swing"
    varsayilan_parametreler = {"yuzde": 0.20}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def zigzag(kap: np.ndarray, yuk: np.ndarray, dus: np.ndarray, yuzde: float):
        n = len(kap)
        giris = np.zeros(n, bool)
        cikis = np.zeros(n, bool)
        giris_tepe = np.full(n, np.nan)
        basladi, yukari_ara = False, True
        dip = tepe = 0.0
        for t in range(n):
            c, h, l = kap[t], yuk[t], dus[t]
            if not (np.isfinite(c) and np.isfinite(h) and np.isfinite(l)):
                continue
            if not basladi:
                dip, tepe, basladi, yukari_ara = l, h, True, True
                continue
            if yukari_ara:
                dip = min(dip, l)
                if c >= dip * (1 + yuzde):
                    giris[t], giris_tepe[t] = True, h
                    yukari_ara, tepe = False, h
            else:
                tepe = max(tepe, h)
                if c <= tepe * (1 - yuzde):
                    cikis[t] = True
                    yukari_ara, dip = True, l
        return giris, cikis, giris_tepe

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        y = float(self.parametreler["yuzde"])
        giris, cikis, gtepe = self.zigzag(mumlar["kapanis"].to_numpy(float), mumlar["yuksek"].to_numpy(float),
                                          mumlar["dusuk"].to_numpy(float), y)
        idx = mumlar.index
        stop = pd.Series(gtepe * (1 - y), index=idx)
        sonuc = cerceve(mumlar, pd.Series(giris, index=idx), False, stop, stop)
        sonuc["cikis_long"] = pd.Series(cikis, index=idx)
        return sonuc


VMA_KURALLARI = [(1, 50, 0.0), (1, 50, 0.01), (1, 150, 0.0), (1, 150, 0.01), (5, 150, 0.0),
                 (5, 150, 0.01), (1, 200, 0.0), (1, 200, 0.01), (2, 200, 0.0), (2, 200, 0.01)]


class VmaBantKaynak(Strateji):
    """T21: kısa MA (S gün; S=1 kapanış) uzun MA'yı (L gün) B bandı kadar AŞINCA long; kısa MA uzun MA'nın
    B bandı kadar ALTINA inince çık (bant içinde pozisyon korunur). Basit MA, günlük, long/flat.

    Kaynak kaldıraçla maruziyeti ikiye katlar ('double or out') ve boşta fonu faize koyar; ikisi de uygulanmaz
    (risk motoru boyutlar, faiz yok) = uyarlama. Giriş koşulu durumsaldır (stop sonrası koşul sürerse yeniden girer).
    """

    ad, stil = "kapanis__vma-bant", "swing"
    varsayilan_parametreler = {"s": 1, "l": 50, "b": 0.0, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = mumlar["kapanis"]
        s, l, b = int(p["s"]), int(p["l"]), float(p["b"])
        kisa = kap if s == 1 else g.sma(kap, s)
        uzun = g.sma(kap, l)
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_n"]))
        al = kisa > uzun * (1 + b)
        sat = kisa < uzun * (1 - b)
        sonuc = cerceve(mumlar, al, False, kap - float(p["atr_k"]) * atr, kap + float(p["atr_k"]) * atr)
        sonuc["cikis_long"] = sat.fillna(False)
        return sonuc


def _super_smoother(x: np.ndarray, n: int = 7) -> np.ndarray:
    a1 = np.exp(-1.414 * np.pi / n)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / n)
    c2, c3 = b1, -a1 * a1
    c1 = 1 - c2 - c3
    y = np.full(len(x), np.nan)
    for i in range(len(x)):
        if np.isnan(x[i]) or i < 2 or np.isnan(x[i - 1]):
            y[i] = x[i]
            continue
        p1 = y[i - 1] if not np.isnan(y[i - 1]) else x[i - 1]
        p2 = y[i - 2] if not np.isnan(y[i - 2]) else x[i - 2] if not np.isnan(x[i - 2]) else p1
        y[i] = c1 * (x[i] + x[i - 1]) / 2 + c2 * p1 + c3 * p2
    return y


class IchimokuC4Arsiv(Strateji):
    """Ichimoku 20/60/120 bileşik trend (arşiv C4, ham): kaynak lutfi-zain/quant-lttd-ichimoku'nun sadeleştirmesi
    (entropi kapısı yok, çıkış IMO<0). Günlük, long. Sabitler arşiv kodundakiyle aynı.

    IMO = ortalama(tanh((TK)/ATR60), tanh(bulut mesafesi/ATR60), tanh((SA-SB)/ATR60), tanh(5/ATR60 60g getiri)),
    SuperSmoother(7). Giriş: IMO > 0.4*std30(IMO) ve ER(14) > 0.25 ve kapanış >= bulut altı, art arda 2 mum.
    Çıkış: IMO < 0; en fazla 250 mum. Arşivin 4xATR stopu yerine ön kayıt ATR(14)x3 stopu (uyarlama).
    """

    ad, stil = "kapanis__ichimoku-c4-arsiv", "swing"
    varsayilan_parametreler = {"p1": 20, "p2": 60, "p3": 120, "smooth": 7, "er_n": 14, "std_n": 30,
                               "t_giris": 0.4, "er_esik": 0.25, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=250)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        c, h, l = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        p1, p2, p3 = int(p["p1"]), int(p["p2"]), int(p["p3"])

        def orta(n):
            return (h.rolling(n).max() + l.rolling(n).min()) / 2

        ten, kij, sb = orta(p1), orta(p2), orta(p3)
        sa = (ten + kij) / 2
        ust = np.maximum(sa.shift(p2), sb.shift(p2))
        alt = np.minimum(sa.shift(p2), sb.shift(p2))
        a60 = g.atr(h, l, c, p2)
        mesafe = pd.Series(np.where(c > ust, c - ust, np.where(c < alt, c - alt, 0.0)), index=c.index)
        imo = (np.tanh((ten - kij) / a60) + np.tanh(mesafe / a60) + np.tanh((sa - sb) / a60)
               + np.tanh((c - c.shift(p2)) / a60)) / 4
        imo = pd.Series(_super_smoother(imo.to_numpy(float), int(p["smooth"])), index=c.index)
        er_n = int(p["er_n"])
        er = (c - c.shift(er_n)).abs() / c.diff().abs().rolling(er_n).sum()
        kos = ((imo > float(p["t_giris"]) * imo.rolling(int(p["std_n"])).std())
               & (er > float(p["er_esik"])) & (c >= alt)).fillna(False)
        gir = kos & kos.shift(1, fill_value=False)
        atr = g.atr(h, l, c, int(p["atr_n"]))
        sonuc = cerceve(mumlar, gir, False, c - float(p["atr_k"]) * atr, c + float(p["atr_k"]) * atr)
        sonuc["cikis_long"] = (imo < 0).fillna(False)
        return sonuc


class ArgusGizliBogaD3(Strateji):
    """Argus gizli boğa uyumsuzluğu (arşiv D3, ham): 3 mum sonra teyitli dip (düşük[t-3] = son 7 mumun en düşüğü),
    bir önceki teyitli dipten en çok 60 mum önce ve ondan YÜKSEK, RSI(14) o dipte öncekinden DÜŞÜK, kapanış > SMA200.
    Stop 2xATR(14), hedef 1,5R, en fazla 10 mum. Günlük, long. Kaynak Argus EA'sının MQL5 sürümünden (pip eşiği,
    D1 EMA200 yanlılığı, rejim manifesti) farklıdır; kural arşiv D3'ün kendisidir.
    """

    ad, stil = "kapanis__argus-gizli-boga-d3", "swing"
    varsayilan_parametreler = {"yaricap": 3, "geri_bakis": 60, "rsi_n": 14, "sma_n": 200,
                               "atr_n": 14, "atr_k": 2.0, "hedef_r": 1.5}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=10)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        c, h, l = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        r = g.rsi(c, int(p["rsi_n"]))
        atr = g.atr(h, l, c, int(p["atr_n"]))
        lv, rv = l.to_numpy(float), r.to_numpy(float)
        yc, gb = int(p["yaricap"]), int(p["geri_bakis"])
        pen = 2 * yc  # 7 mumluk pencere: t-6..t
        n = len(mumlar)
        long = np.zeros(n, bool)
        onceki = None
        for t in range(pen, n):
            k = t - yc
            if lv[k] == np.nanmin(lv[t - pen:t + 1]):
                if (onceki is not None and k - onceki[0] <= gb and lv[k] > onceki[1] and rv[k] < onceki[2]):
                    long[t] = True
                onceki = (k, lv[k], rv[k])
        gir = pd.Series(long, index=mumlar.index) & (c > g.sma(c, int(p["sma_n"])))
        risk = float(p["atr_k"]) * atr
        return cerceve(mumlar, gir, False, c - risk, c + risk, hedef_l=c + float(p["hedef_r"]) * risk)
