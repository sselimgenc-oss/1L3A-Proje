"""D9-B — dis_envanter.csv'de "atlandi:" işaretli satırların (indeks >= 229) ve ek_77 belgesinde (stratejiler/ek_kaynaklar/
ek_77_strateji.md) kodlanmamış tek-grafik maddelerin KODU. KOD KOPYALANMADI: kaynak metinler (Pine/freqtrade/kural özetleri,
belge) VERİDİR; kurallar kendi yapımızla yazıldı. Ad öneki `dis__`. Hepsi nedensel (lookahead yok).

Ortak uyarlamalar
  * Stopu olmayan orijinallere ATR felaket stopu (stop_atr_k x ATR) ya da yüzde stop eklendi.
  * freqtrade `minimal_roi` / `trailing_stop` motorda yok: hedef_yuzde + zaman_cikisi ya da CikisAyarlari ile yaklaşıldı.
  * 1m orijinaller >= 5m tabanda (scalp için 15m önerilir); kaynak TF'sine göre stil: <=15m scalp, 1h daytrade, >=4h swing.
  * Kuralda tanımsız kalan eşik / periyot varsayımları sınıfın docstring'inde "VARSAYIM" olarak yazılıdır.

--- dış envanter (TradingView) ---
dis__pivot-kirilim-hacim, dis__williams-r-supertrend, dis__dar-durum-ema-sma, dis__bolge-akis-sr
--- freqtrade ---
dis__ft-awesome-macd, dis__ft-bandtastic, dis__ft-cci-cmf-mfi, dis__ft-cluc-may2018, dis__ft-cmc-winner, dis__ft-cofibit,
dis__ft-binh-cluc, dis__ft-fott, dis__ft-fsupertrend, dis__ft-supertrend3, dis__ft-low-bb, dis__ft-macd-cci,
dis__ft-macd-cci-kesisim, dis__ft-multi-rsi, dis__ft-highwave, dis__ft-reinforced-quickie, dis__ft-reinforced-smoothscalp,
dis__ft-scalp-ema-adx, dis__ft-simple-macd-rsi, dis__ft-smoothscalp, dis__ft-strategy002, dis__ft-strategy003,
dis__ft-strategy004, dis__ft-swinghightosky
--- kural / jesuistm ---
dis__btfd-gunluk-dip, dis__gosterge-rezonansi, dis__ma-dizilim-5-10-30, dis__macd-kdj-4h, dis__macd-sma-cift,
dis__rsi-ma-normal, dis__rsi-ma-uc, dis__stochrsi-uc-4h, dis__gmma-ls, dis__bollinger-w-dibi, dis__bas-omuz-rsi-short,
dis__shooting-star-onay
--- ek_77 ---
dis__cryptofrog-dip (#14), dis__solipsis-rmi (#15), dis__ha-guclu-dusus-al (#38), dis__bbrsi-donus (#59), dis__ema-esik-trend (#63),
dis__acrypto-agirlikli (#70), dis__mtf-rsi-trend (#72), dis__ma-cift-cross (#73, #74), dis__sma20-scalp (#75),
dis__alpaca-momentum (#76)

KODLANMAYANLAR (stratejiler/kodlama_2026-11-07_b.csv'de gerekçeli): FReinforcedStrategy (kural belirsiz), mabStra (eşik yok),
UniversalMACD (aralık sayıları yok), JT_Dual_Thrust (dis__dual-thrust ile aynı kural), ek_77 #58 EA31337 (kural yok), #68 Turtle
(swing__donchian-kirilim kapsar), #29 (dis__ay-donumu kapsar), grid/DCA/martingale/L2/DEX/ML/opsiyon maddeleri.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d1 import kur
from motor.strateji.dis._gosterge_d2 import var_ma
from motor.strateji.dis._gosterge_d2 import stoch_rsi
from motor.strateji.dis._gosterge_d3 import ORTAK, D3Taban, cmf, hizli_stokastik, mfi
from motor.strateji.dis._gosterge_d5 import gun_ici_cerceve, kama, ott, onceki_seans_hlc, seans_bilgi
from motor.strateji.gostergeler_b2 import asagi_kesis, cci, gecis, heikin_ashi, yukari_kesis
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji

from ._gosterge_d9 import (
    ardisik_say, cekic, cmo, ema_low_high, fisher_rsi, kdj, mum_govde, pinball, pivot_seviye, r_hedefi, rmi,
    ters_cekic, vfi)


def _bos(index):
    return pd.Series(False, index=index)


def _izgara3(**kw):
    return kw


# =============================================================================== TradingView
class PivotKirilimHacim(D3Taban):
    """dis__pivot-kirilim-hacim (daytrade, 1h) — "Volume-Confirmed Support/Resistance Breakout Strategy" (TV).
    Kural: son onaylı pivot tepesi (sol/sag mum) KAPANIŞLA yukarı kırılırsa VE hacim > hacim_k x SMA(hacim, 20) VE kapanış >
    EMA(200) -> long. Pivot dibi aşağı kırılır, hacim teyidi, kapanış < EMA200 -> short. Çıkış: hedef_r x R hedefi ya da ATR
    stop. VARSAYIM: pivot sol=sag=5; stop = stop_atr_k x ATR; hedef 2R (kaynakta çıkış tarif edilmemiş)."""
    ad = "dis__pivot-kirilim-hacim"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 2.0, "hedef_yuzde": 0.0, "pivot_n": 5,
                               "ema_n": 200, "hacim_n": 20, "hacim_k": 1.5, "hedef_r": 2.0}
    parametre_izgarasi = {"pivot_n": [3, 5, 8], "hacim_k": [1.0, 1.5, 2.0], "stop_atr_k": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        ust = pivot_seviye(m["yuksek"], int(p["pivot_n"]), int(p["pivot_n"]), True)
        alt = pivot_seviye(m["dusuk"], int(p["pivot_n"]), int(p["pivot_n"]), False)
        hac = m["hacim"] > p["hacim_k"] * m["hacim"].rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean()
        ema = g.ema(k, int(p["ema_n"]))
        return {"long": yukari_kesis(k, ust) & hac & (k > ema), "short": asagi_kesis(k, alt) & hac & (k < ema)}

    def sinyaller(self, m):
        out = super().sinyaller(m)
        return r_hedefi(out, m["kapanis"], float(self.parametreler["hedef_r"]))


class WilliamsRSupertrend(D3Taban):
    """dis__williams-r-supertrend (scalp, 15m) — "Williams R Zone Scalper v1.0 [BullByte]" (TV).
    Kural: Williams %R(14) -80'i yukarı keserse long (Supertrend yükselişteyse); -20'yi aşağı keserse short (Supertrend
    düşüşteyse). Ters sinyal pozisyonu kapatır/çevirir. Stop: ATR (kaynakta SL/TP yok -> felaket stopu)."""
    ad = "dis__williams-r-supertrend"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 2.5, "wr_n": 14, "wr_alt": -80.0, "wr_ust": -20.0,
                               "st_n": 10, "st_k": 3.0}
    parametre_izgarasi = {"wr_n": [10, 14, 21], "st_k": [2.0, 3.0, 4.0], "stop_atr_k": [2.0, 2.5, 3.5]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        n = int(p["wr_n"])
        hh, ll = y.rolling(n, min_periods=n).max(), d.rolling(n, min_periods=n).min()
        wr = -100.0 * (hh - k) / (hh - ll).where(hh != ll)
        st = g.supertrend(y, d, k, int(p["st_n"]), float(p["st_k"]))["yon"]
        yuk, asg = yukari_kesis(wr, p["wr_alt"]), asagi_kesis(wr, p["wr_ust"])
        return {"long": yuk & (st == 1), "short": asg & (st == -1), "cikis_long": asg, "cikis_short": yuk}


class DarDurumEmaSma(D3Taban):
    """dis__dar-durum-ema-sma (daytrade, 1h) — "Yuri Garcia Narrow State Strategy" (TV).
    Kural: |EMA20 - SMA200| <= dar_k x ATR ("dar durum") iken, SMA200 eğimi yönünde (5 mum öncesine göre) gövdeli mum
    (gövde >= govde_oran x aralık, yön rengiyle) ya da dönüş mumu (yutan boğa/ayı) -> giriş. Stop 2 ATR, hedef 2R (kaynak).
    VARSAYIM: 'dar' eşiği dar_k = 1.0 ATR; trend yönü = SMA200 eğimi."""
    ad = "dis__dar-durum-ema-sma"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 2.0, "hedef_r": 2.0, "dar_k": 1.0, "govde_oran": 0.6,
                               "egim_n": 5}
    parametre_izgarasi = {"dar_k": [0.5, 1.0, 1.5], "govde_oran": [0.5, 0.6, 0.7], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        o, k = m["acilis"], m["kapanis"]
        a = g.atr(m["yuksek"], m["dusuk"], k, 14)
        e20, s200 = g.ema(k, 20), g.sma(k, 200)
        dar = (e20 - s200).abs() <= p["dar_k"] * a
        f = mum_govde(m)
        gov = f["govde"] >= p["govde_oran"] * f["aralik"].where(f["aralik"] > 0)
        boga, ayi = k > o, k < o
        yut_b = boga & (o <= k.shift(1)) & (k >= o.shift(1)) & (k.shift(1) < o.shift(1))
        yut_a = ayi & (o >= k.shift(1)) & (k <= o.shift(1)) & (k.shift(1) > o.shift(1))
        egim = s200 - s200.shift(int(p["egim_n"]))
        return {"long": dar & (egim > 0) & ((gov & boga) | yut_b),
                "short": dar & (egim < 0) & ((gov & ayi) | yut_a)}

    def sinyaller(self, m):
        return r_hedefi(super().sinyaller(m), m["kapanis"], float(self.parametreler["hedef_r"]))


class BolgeAkisSr(Strateji):
    """dis__bolge-akis-sr (daytrade, 1h) — "Zone Flow S/R Strategy" (TV).
    Kural: onaylı pivot dibi/tepesi çevresinde ATR genişlikli bölge (seviye +/- bolge_k x ATR). Mumun dibi desteğin bölgesine
    girer ve mum onay verirse (yutan boğa YA DA pin bar: alt fitil >= 2 x gövde, kapanış aralığın üst yarısında) VE RSI(14) <
    rsi_ust -> long; direnç aynası -> short. Stop: bölge dışı + 0.5 ATR; hedef hedef_r x R.
    ATLANDI: kısmi/tam kâr alma kademeleri (kaynakta oranlar yok; CikisAyarlari.kismi ile dışarıdan verilebilir).
    VARSAYIM: pivot 5/5, bolge_k = 0.5, rsi_ust = 55 (long) / 100-rsi_ust (short)."""
    ad = "dis__bolge-akis-sr"
    stil = "daytrade"
    varsayilan_parametreler = {"pivot_n": 5, "bolge_k": 0.5, "rsi_ust": 55.0, "hedef_r": 2.0, "tampon_atr": 0.5,
                               "short": True}
    parametre_izgarasi = {"bolge_k": [0.3, 0.5, 1.0], "rsi_ust": [50.0, 55.0, 65.0], "hedef_r": [1.5, 2.0, 3.0]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        o, y, d, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        a = g.atr(y, d, k, 14)
        des = pivot_seviye(d, int(p["pivot_n"]), int(p["pivot_n"]), False)
        dir_ = pivot_seviye(y, int(p["pivot_n"]), int(p["pivot_n"]), True)
        r = g.rsi(k, 14)
        f = mum_govde(m)
        yut_b = (k > o) & (o <= k.shift(1)) & (k >= o.shift(1)) & (k.shift(1) < o.shift(1))
        yut_a = (k < o) & (o >= k.shift(1)) & (k <= o.shift(1)) & (k.shift(1) > o.shift(1))
        pin_b = (f["alt_fitil"] >= 2 * f["govde"]) & (k >= (y + d) / 2.0) & (f["aralik"] > 0)
        pin_a = (f["ust_fitil"] >= 2 * f["govde"]) & (k <= (y + d) / 2.0) & (f["aralik"] > 0)
        zl = d <= des + p["bolge_k"] * a
        zs = y >= dir_ - p["bolge_k"] * a
        long_ok = zl & (k > des) & (yut_b | pin_b) & (r < p["rsi_ust"])
        short_ok = (zs & (k < dir_) & (yut_a | pin_a) & (r > 100.0 - p["rsi_ust"])) if p["short"] else _bos(m.index)
        stop_l = np.minimum(d, des - p["bolge_k"] * a) - p["tampon_atr"] * a
        stop_s = np.maximum(y, dir_ + p["bolge_k"] * a) + p["tampon_atr"] * a
        out = kur(m, long_ok, short_ok, stop_l, stop_s)
        return r_hedefi(out, k, float(p["hedef_r"]))


# =============================================================================== freqtrade
class FtAwesomeMacd(D3Taban):
    """dis__ft-awesome-macd (daytrade, 1h) — freqtrade AwesomeMacd. Kural: MACD(12,26,9) çizgisi > 0 VE Awesome Oscillator
    yukarı dönüş yaptı (AO[t] > AO[t-1] ve AO[t-1] <= AO[t-2]) VE ADX(14) >= adx_min -> long. Çıkış: MACD < 0 ya da AO < 0.
    Short ayna (yonler='ls'). VARSAYIM: ADX eşiği 20; orijinal ADX koşulu belgede sayısal verilmemiş."""
    ad = "dis__ft-awesome-macd"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "adx_min": 20.0, "macd_hizli": 12, "macd_yavas": 26}
    parametre_izgarasi = {"adx_min": [0.0, 20.0, 25.0], "macd_yavas": [21, 26, 34], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        hl2 = (m["yuksek"] + m["dusuk"]) / 2.0
        ao = g.sma(hl2, 5) - g.sma(hl2, 34)
        ml = g.macd(m["kapanis"], int(p["macd_hizli"]), int(p["macd_yavas"]), 9)["macd"]
        adx = g.adx(m["yuksek"], m["dusuk"], m["kapanis"], 14)["adx"] >= p["adx_min"]
        dn_u = (ao > ao.shift(1)) & (ao.shift(1) <= ao.shift(2))
        dn_d = (ao < ao.shift(1)) & (ao.shift(1) >= ao.shift(2))
        return {"long": (ml > 0) & dn_u & adx, "short": (ml < 0) & dn_d & adx,
                "cikis_long": (ml < 0) | (ao < 0), "cikis_short": (ml > 0) | (ao > 0)}


class FtBandtastic(D3Taban):
    """dis__ft-bandtastic (scalp, 15m) — freqtrade Bandtastic. Kural: RSI(14) < rsi_alt VE MFI(14) < mfi_alt VE EMA(hizli) >
    EMA(yavas) VE kapanış < alt Bollinger(20, 2) bandı x (1 - bant_pay). Çıkış: RSI > rsi_cikis. Yalnız long (orijinal).
    VARSAYIM: eşikler 35/35/65, EMA 20/50, bant_pay 0.0 (orijinalde birden çok bant seviyesinden biri seçiliyor)."""
    ad = "dis__ft-bandtastic"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "rsi_alt": 35.0, "mfi_alt": 35.0, "rsi_cikis": 65.0,
                               "ema_h": 20, "ema_y": 50, "bant_pay": 0.0}
    parametre_izgarasi = {"rsi_alt": [30.0, 35.0, 40.0], "rsi_cikis": [55.0, 65.0, 75.0], "bant_pay": [0.0, 0.005, 0.015]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, 20, 2.0)
        r = g.rsi(k, 14)
        mf = mfi(m["yuksek"], m["dusuk"], k, m["hacim"], 14)
        giris = (r < p["rsi_alt"]) & (mf < p["mfi_alt"]) & (g.ema(k, int(p["ema_h"])) > g.ema(k, int(p["ema_y"]))) \
            & (k < bb["alt"] * (1.0 - p["bant_pay"]))
        return {"long": giris, "cikis_long": r > p["rsi_cikis"]}


class FtCciCmfMfi(D3Taban):
    """dis__ft-cci-cmf-mfi (scalp, 15m; orijinal 1m) — freqtrade CCIStrategy. Kural: CCI(20) < cci_esik VE CCI(10) < cci_esik
    (iki periyot) VE CMF(21) < cmf_esik VE MFI(14) < mfi_esik -> long. Çıkış: CCI(20) > 100. VARSAYIM: eşikler -100 / -0.1 /
    30; iki CCI periyodu 20 ve 10 (orijinal belgede periyot yok)."""
    ad = "dis__ft-cci-cmf-mfi"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "cci_esik": -100.0, "cmf_esik": -0.1, "mfi_esik": 30.0,
                               "cci_a": 20, "cci_b": 10}
    parametre_izgarasi = {"cci_esik": [-150.0, -100.0, -80.0], "cmf_esik": [-0.2, -0.1, 0.0], "mfi_esik": [20.0, 30.0, 40.0]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        ca, cb = cci(y, d, k, int(p["cci_a"])), cci(y, d, k, int(p["cci_b"]))
        giris = (ca < p["cci_esik"]) & (cb < p["cci_esik"]) & (cmf(y, d, k, m["hacim"], 21) < p["cmf_esik"]) \
            & (mfi(y, d, k, m["hacim"], 14) < p["mfi_esik"])
        return {"long": giris, "cikis_long": ca > 100.0}


class FtClucMay2018(D3Taban):
    """dis__ft-cluc-may2018 (scalp, 5m) — freqtrade ClucMay72018. Kural: kapanış < EMA(100) VE kapanış < alt Bollinger(20, 2)
    x (1 - alt_pay) VE hacim < hacim_k x SMA(hacim, 30) (aşırı hacim patlaması yok). Çıkış: kapanış > Bollinger ortası.
    Orijinaldeki ADX/MACD/RSI sütunları belgede koşul olarak tarif edilmediğinden KULLANILMADI. alt_pay=0.015 (%1.5)."""
    ad = "dis__ft-cluc-may2018"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "ema_n": 100, "alt_pay": 0.015, "hacim_k": 20.0}
    parametre_izgarasi = {"alt_pay": [0.005, 0.015, 0.025], "ema_n": [50, 100, 200], "hacim_k": [5.0, 10.0, 20.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, 20, 2.0)
        hac = m["hacim"] < p["hacim_k"] * m["hacim"].rolling(30, min_periods=30).mean().shift(1)
        return {"long": (k < g.ema(k, int(p["ema_n"]))) & (k < bb["alt"] * (1.0 - p["alt_pay"])) & hac,
                "cikis_long": k > bb["orta"]}


class FtCmcWinner(D3Taban):
    """dis__ft-cmc-winner (scalp, 15m) — freqtrade CMCWinner. Kural: CCI(20) < -100 VE MFI(14) < 20 VE CMO(14) < -50 ->
    long. Çıkış: CCI > 100 VE MFI > 80. Short ayna (yonler='ls')."""
    ad = "dis__ft-cmc-winner"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "cci_esik": 100.0, "mfi_esik": 20.0, "cmo_esik": 50.0}
    parametre_izgarasi = {"cci_esik": [80.0, 100.0, 150.0], "mfi_esik": [15.0, 20.0, 30.0], "cmo_esik": [30.0, 50.0, 70.0]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        c, mf, co = cci(y, d, k, 20), mfi(y, d, k, m["hacim"], 14), cmo(k, 14)
        al = (c < -p["cci_esik"]) & (mf < p["mfi_esik"]) & (co < -p["cmo_esik"])
        sat = (c > p["cci_esik"]) & (mf > 100.0 - p["mfi_esik"]) & (co > p["cmo_esik"])
        return {"long": al, "short": sat, "cikis_long": (c > p["cci_esik"]) & (mf > 100.0 - p["mfi_esik"]),
                "cikis_short": (c < -p["cci_esik"]) & (mf < p["mfi_esik"])}


class FtCofiBit(D3Taban):
    """dis__ft-cofibit (scalp, 5m-15m) — freqtrade CofiBitStrategy. Kural: açılış < EMA(5, düşük) x ac_k VE hızlı stokastik
    %K, %D'yi yukarı keser VE %K < 30 VE %D < 30 VE ADX(14) > 20 -> long. Çıkış: açılış > EMA(5, yüksek) x cik_k VEYA %K ve %D
    > 70. VARSAYIM: ac_k 0.99 / cik_k 1.01 (belgede sayı yok), ADX eşiği 20."""
    ad = "dis__ft-cofibit"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "ac_k": 0.99, "cik_k": 1.01, "stoch_esik": 30.0, "adx_min": 20.0}
    parametre_izgarasi = {"ac_k": [0.98, 0.99, 1.0], "stoch_esik": [20.0, 30.0, 40.0], "adx_min": [0.0, 20.0, 30.0]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        e = ema_low_high(y, d, 5)
        st = hizli_stokastik(y, d, k, 5, 3)
        adx = g.adx(y, d, k, 14)["adx"] > p["adx_min"]
        giris = (m["acilis"] < e["alt"] * p["ac_k"]) & yukari_kesis(st["k"], st["d"]) & (st["k"] < p["stoch_esik"]) \
            & (st["d"] < p["stoch_esik"]) & adx
        cik = (m["acilis"] > e["ust"] * p["cik_k"]) | ((st["k"] > 70.0) & (st["d"] > 70.0))
        return {"long": giris, "cikis_long": cik}


class FtBinhCluc(D3Taban):
    """dis__ft-binh-cluc (scalp, 5m-15m) — freqtrade CombinedBinHAndCluc. Birleşim (VEYA):
    A (BinH tarzı): kapanış < alt Bollinger(40, 2) x (1 - alt_pay) VE düşüş mumu (kapanış < açılış) VE alt fitil <= 0.5 x
    aralık (satış baskısı sürüyor, dip fitili yok).
    B (Cluc tarzı): kapanış < EMA(100) VE kapanış < alt Bollinger(20, 2) x 0.985 VE hacim < 20 x SMA(hacim, 30).
    Çıkış: kapanış > Bollinger(20) ortası. VARSAYIM: iki alt-kuralın tam eşikleri belgede yok; yukarıdaki değerler bizim
    seçimimiz (belge: 'alt bant dışı düşüş mumu ile long; orta bantta çıkış')."""
    ad = "dis__ft-binh-cluc"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "alt_pay": 0.003, "fitil_maks": 0.5, "kol": "ikisi"}
    parametre_izgarasi = {"alt_pay": [0.0, 0.003, 0.01], "fitil_maks": [0.3, 0.5, 0.8], "kol": ["ikisi", "binh", "cluc"]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb20, bb40 = g.bollinger(k, 20, 2.0), g.bollinger(k, 40, 2.0)
        f = mum_govde(m)
        a = (k < bb40["alt"] * (1.0 - p["alt_pay"])) & (k < m["acilis"]) & (f["alt_fitil"] <= p["fitil_maks"] * f["aralik"])
        b = (k < g.ema(k, 100)) & (k < bb20["alt"] * 0.985) & (m["hacim"] < 20.0 * m["hacim"].rolling(30, min_periods=30).mean().shift(1))
        giris = {"ikisi": a | b, "binh": a, "cluc": b}[p["kol"]]
        return {"long": giris, "cikis_long": k > bb20["orta"]}


class FtFott(D3Taban):
    """dis__ft-fott (daytrade, 1h) — freqtrade FOttStrategy. Kural: VAR (Chande VIDYA) çizgisi OTT'yi (VAR üzerinde, yuzde %)
    yukarı keserse long; aşağı keserse short; ters kesişimde çıkış. Pine OTT'nin standardı gibi kesişim, OTT'nin 2 mum öncesi
    değerine göre. İlk 150 mum VAR ısınması için sinyalsiz. İsteğe bağlı ADX(14) >= adx_min filtresi (0 = kapalı)."""
    ad = "dis__ft-fott"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "var_n": 9, "yuzde": 0.6, "adx_min": 0.0}
    parametre_izgarasi = {"var_n": [2, 5, 9], "yuzde": [0.4, 0.6, 1.0], "adx_min": [0.0, 15.0, 25.0]}

    def kosullar(self, m):
        p = self.parametreler
        v = var_ma(m["kapanis"], int(p["var_n"]))
        o = ott(v, float(p["yuzde"]))
        yuk, asg = yukari_kesis(v, o.shift(2)), asagi_kesis(v, o.shift(2))
        hazir = pd.Series(np.arange(len(m)) >= 150, index=m.index)
        adx = g.adx(m["yuksek"], m["dusuk"], m["kapanis"], 14)["adx"] >= p["adx_min"]
        return {"long": yuk & hazir & adx, "short": asg & hazir & adx, "cikis_long": asg & hazir, "cikis_short": yuk & hazir}


class _UcSupertrend(D3Taban):
    """Üç Supertrend alım teyidi / üç Supertrend satım çıkışı ortak gövdesi."""
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "carpan_olcek": 1.0}
    parametre_izgarasi = {"carpan_olcek": [0.8, 1.0, 1.25], "stop_atr_k": [2.0, 3.0, 4.0]}
    _AL = ((8, 4.0), (9, 7.0), (8, 1.0))
    _SAT = ((16, 1.0), (18, 3.0), (18, 6.0))

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        s = float(p["carpan_olcek"])
        al = [g.supertrend(y, d, k, n, c * s)["yon"] for n, c in self._AL]
        sat = [g.supertrend(y, d, k, n, c * s)["yon"] for n, c in self._SAT]
        hepsi_yuk = (al[0] == 1) & (al[1] == 1) & (al[2] == 1)
        hepsi_asg = (sat[0] == -1) & (sat[1] == -1) & (sat[2] == -1)
        return {"long": hepsi_yuk, "cikis_long": hepsi_asg}


class FtFSupertrend(_UcSupertrend):
    """dis__ft-fsupertrend (daytrade, 1h) — freqtrade FSupertrendStrategy. Kural: üç Supertrend (periyot, çarpan = 8/4, 9/7, 8/1)
    ÜÇÜ DE yükselişteyse long; üç ayrı 'satım' Supertrend'i (16/1, 18/3, 18/6) ÜÇÜ DE düşüşteyse çıkış. VARSAYIM: periyot ve
    çarpanlar freqtrade topluluğundaki yaygın hyperopt değerleridir (belgede sayı yok); carpan_olcek hepsini ölçekler."""
    ad = "dis__ft-fsupertrend"
    _AL = ((8, 4.0), (9, 7.0), (8, 1.0))
    _SAT = ((16, 1.0), (18, 3.0), (18, 6.0))


class FtSupertrend3(_UcSupertrend):
    """dis__ft-supertrend3 (daytrade, 1h) — freqtrade Supertrend. FSupertrend ile aynı mantık, farklı varsayılan seviyeler:
    alım 10/1, 11/2, 12/3; satım 10/1, 11/2, 12/3 ters yön (hepsi düşüşte -> çıkış). VARSAYIM: periyot/çarpanlar bizim
    seçimimiz (orijinal hyperopt değerleri belgede yok)."""
    ad = "dis__ft-supertrend3"
    _AL = ((10, 1.0), (11, 2.0), (12, 3.0))
    _SAT = ((10, 1.0), (11, 2.0), (12, 3.0))


class FtLowBb(D3Taban):
    """dis__ft-low-bb (scalp, 5m; orijinal 1m) — freqtrade Low_BB. Kural: kapanış < alt Bollinger(20, 2) x (1 - alt_pay) ->
    long (kısa vadeli ortalamaya dönüş). Çıkış: hedef_yuzde (%1) kâr ya da zaman_cikisi (12 mum) ya da kapanış > orta bant.
    Orijinal: ROI/stop freqtrade ayarlarında; ATR stop eklendi."""
    ad = "dis__ft-low-bb"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "alt_pay": 0.02, "hedef_yuzde": 0.01, "zaman_cikisi": 12}
    parametre_izgarasi = {"alt_pay": [0.01, 0.02, 0.03], "hedef_yuzde": [0.005, 0.01, 0.02], "zaman_cikisi": [6, 12, 24]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, 20, 2.0)
        return {"long": k < bb["alt"] * (1.0 - p["alt_pay"]), "cikis_long": k > bb["orta"]}


class FtMacdCci(D3Taban):
    """dis__ft-macd-cci (scalp, 5m-15m) — freqtrade MACDStrategy. Kural: MACD > sinyal VE CCI(20) < cci_al (-50) -> long.
    Çıkış: MACD < sinyal VE CCI > cci_sat (100). VARSAYIM: orijinalin çok uç optimize eşikleri yerine -50 / 100."""
    ad = "dis__ft-macd-cci"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "cci_al": -50.0, "cci_sat": 100.0}
    parametre_izgarasi = {"cci_al": [-100.0, -50.0, 0.0], "cci_sat": [50.0, 100.0, 150.0], "stop_atr_k": [2.0, 2.5, 3.5]}

    def kosullar(self, m):
        p = self.parametreler
        mc = g.macd(m["kapanis"])
        c = cci(m["yuksek"], m["dusuk"], m["kapanis"], 20)
        return {"long": gecis((mc["macd"] > mc["sinyal"]) & (c < p["cci_al"])),
                "cikis_long": (mc["macd"] < mc["sinyal"]) & (c > p["cci_sat"])}


class FtMacdCciKesisim(D3Taban):
    """dis__ft-macd-cci-kesisim (scalp, 5m-15m) — freqtrade MACDStrategy_crossed. Kural: MACD sinyali yukarı KESERKEN CCI(20)
    <= cci_al (-50) -> long. Çıkış: MACD sinyali aşağı keserken CCI >= cci_sat (100)."""
    ad = "dis__ft-macd-cci-kesisim"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "cci_al": -50.0, "cci_sat": 100.0}
    parametre_izgarasi = {"cci_al": [-100.0, -50.0, 0.0], "cci_sat": [50.0, 100.0, 150.0], "stop_atr_k": [2.0, 2.5, 3.5]}

    def kosullar(self, m):
        p = self.parametreler
        mc = g.macd(m["kapanis"])
        c = cci(m["yuksek"], m["dusuk"], m["kapanis"], 20)
        return {"long": yukari_kesis(mc["macd"], mc["sinyal"]) & (c <= p["cci_al"]),
                "cikis_long": asagi_kesis(mc["macd"], mc["sinyal"]) & (c >= p["cci_sat"])}


class FtMultiRsi(D3Taban):
    """dis__ft-multi-rsi (scalp, 15m; orijinal 5m) — freqtrade MultiRSI. Kural: SMA(5) >= SMA(200) VE RSI(14) < rsi_alt VE
    üst zaman dilimi (ust_tf, kapanmış mumlar) RSI(14) < ust_esik -> long. Çıkış: üst TF RSI > ust_cikis. Üst TF 'htf.ust_zaman'
    (yalnız kapanmış mumlar). VARSAYIM: üst TF 1h; belgede çoklu üst TF eşikleri verilmemiş -> tek üst TF ve eşikler 35/50/70."""
    ad = "dis__ft-multi-rsi"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "ust_tf": "1h", "rsi_alt": 35.0, "ust_esik": 50.0, "ust_cikis": 70.0}
    parametre_izgarasi = {"rsi_alt": [30.0, 35.0, 40.0], "ust_esik": [40.0, 50.0, 60.0], "ust_cikis": [60.0, 70.0, 80.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        ust = ust_zaman(m, p["ust_tf"], lambda u: pd.DataFrame({"rsi": g.rsi(u["kapanis"], 14)}))["rsi"]
        return {"long": (g.sma(k, 5) >= g.sma(k, 200)) & (g.rsi(k, 14) < p["rsi_alt"]) & (ust < p["ust_esik"]),
                "cikis_long": ust > p["ust_cikis"]}


class FtHighwave(D3Taban):
    """dis__ft-highwave (swing, 1d) — freqtrade PatternRecognition (CDLHIGHWAVE). 'High wave' mumu: gövde <= govde_oran x aralık
    ve hem üst hem alt fitil >= fitil_oran x aralık. TA-Lib işareti mum rengine bağlı: yeşil (kapanış > açılış) -> long girişi,
    kırmızı -> long çıkışı (short yonler='ls' ile aynası). VARSAYIM: TA-Lib'in ortalama-tabanlı 'kısa gövde / çok uzun fitil'
    ölçüleri aralık oranına çevrildi (0.15 / 0.3)."""
    ad = "dis__ft-highwave"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "govde_oran": 0.15, "fitil_oran": 0.3}
    parametre_izgarasi = {"govde_oran": [0.1, 0.15, 0.25], "fitil_oran": [0.2, 0.3, 0.4], "stop_atr_k": [2.0, 2.5, 3.5]}

    def kosullar(self, m):
        p = self.parametreler
        f = mum_govde(m)
        hw = (f["aralik"] > 0) & (f["govde"] <= p["govde_oran"] * f["aralik"]) \
            & (f["ust_fitil"] >= p["fitil_oran"] * f["aralik"]) & (f["alt_fitil"] >= p["fitil_oran"] * f["aralik"])
        yesil, kirmizi = hw & (m["kapanis"] > m["acilis"]), hw & (m["kapanis"] < m["acilis"])
        return {"long": yesil, "short": kirmizi, "cikis_long": kirmizi, "cikis_short": yesil}


class FtReinforcedQuickie(D3Taban):
    """dis__ft-reinforced-quickie (scalp, 5m-15m) — freqtrade ReinforcedQuickie. Kural: kapanış < EMA(20) VE < EMA(50) VE <=
    alt Bollinger(20, 2) VE düşük, önceki dip_n mumun en düşüğüne eşit/altında (dipte) -> long. Çıkış: kapanış > EMA(20).
    VARSAYIM: EMA periyotları 20/50, dip_n 20 (belgede yok)."""
    ad = "dis__ft-reinforced-quickie"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "ema_a": 20, "ema_b": 50, "dip_n": 20}
    parametre_izgarasi = {"ema_a": [10, 20, 30], "ema_b": [50, 100], "dip_n": [10, 20, 40]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        ea, eb = g.ema(k, int(p["ema_a"])), g.ema(k, int(p["ema_b"]))
        dip = m["dusuk"] <= m["dusuk"].rolling(int(p["dip_n"]), min_periods=int(p["dip_n"])).min().shift(1)
        return {"long": (k < ea) & (k < eb) & (k <= g.bollinger(k, 20, 2.0)["alt"]) & dip, "cikis_long": k > ea}


def _stoch_ema_kanal(m, adx_min, mfi_esik, st_esik, ac_k, cik_k, mfi_gerekli):
    y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
    e = ema_low_high(y, d, 5)
    st = hizli_stokastik(y, d, k, 5, 3)
    kos = (m["acilis"] < e["alt"] * ac_k) & (st["k"] < st_esik) & (st["d"] < st_esik)
    if adx_min > 0:
        kos &= g.adx(y, d, k, 14)["adx"] > adx_min
    if mfi_gerekli:
        kos &= mfi(y, d, k, m["hacim"], 14) < mfi_esik
    cik = (m["acilis"] > e["ust"] * cik_k) | ((st["k"] > 70.0) & (st["d"] > 70.0))
    return kos, cik


class FtReinforcedSmoothScalp(D3Taban):
    """dis__ft-reinforced-smoothscalp (scalp, 15m; orijinal 1m) — freqtrade ReinforcedSmoothScalp. Kural: MFI(14) < mfi_esik VE
    hızlı stokastik %K ve %D < st_esik VE açılış < EMA(5,düşük) x ac_k -> long. Çıkış: açılış > EMA(5,yüksek) x cik_k.
    ADX koşulu YOK (SmoothScalp'tan farkı). VARSAYIM: eşikler 20/30, ac_k 1.0 (EMA düşüğün altı), cik_k 1.0."""
    ad = "dis__ft-reinforced-smoothscalp"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "mfi_esik": 20.0, "st_esik": 30.0, "ac_k": 1.0, "cik_k": 1.0}
    parametre_izgarasi = {"mfi_esik": [15.0, 20.0, 30.0], "st_esik": [20.0, 30.0, 40.0], "ac_k": [0.98, 1.0, 1.02]}

    def kosullar(self, m):
        p = self.parametreler
        kos, cik = _stoch_ema_kanal(m, 0.0, p["mfi_esik"], p["st_esik"], p["ac_k"], p["cik_k"], True)
        return {"long": kos, "cikis_long": cik}


class FtScalpEmaAdx(D3Taban):
    """dis__ft-scalp-ema-adx (scalp, 15m; orijinal 1m) — freqtrade Scalp. Kural: açılış < EMA(5,düşük) x ac_k VE ADX(14) > 30
    VE hızlı stokastik %K ve %D < 30 -> long. Çıkış: açılış > EMA(5,yüksek) x cik_k VEYA %K ve %D > 70. MFI koşulu YOK."""
    ad = "dis__ft-scalp-ema-adx"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "adx_min": 30.0, "st_esik": 30.0, "ac_k": 1.0, "cik_k": 1.0}
    parametre_izgarasi = {"adx_min": [20.0, 30.0, 40.0], "st_esik": [20.0, 30.0, 40.0], "ac_k": [0.98, 1.0, 1.02]}

    def kosullar(self, m):
        p = self.parametreler
        kos, cik = _stoch_ema_kanal(m, p["adx_min"], 0.0, p["st_esik"], p["ac_k"], p["cik_k"], False)
        return {"long": kos, "cikis_long": cik}


class FtSmoothScalp(D3Taban):
    """dis__ft-smoothscalp (scalp, 15m; orijinal 1m) — freqtrade SmoothScalp. Kural: açılış < EMA(5,düşük) x ac_k VE ADX(14) >
    30 VE MFI(14) < mfi_esik VE hızlı stokastik %K ve %D < 30 -> long (Scalp'ın MFI'lı hali). Çıkış: EMA(5,yüksek) üstü VEYA
    stokastik > 70. VARSAYIM: mfi_esik 30."""
    ad = "dis__ft-smoothscalp"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "adx_min": 30.0, "mfi_esik": 30.0, "st_esik": 30.0, "ac_k": 1.0,
                               "cik_k": 1.0}
    parametre_izgarasi = {"adx_min": [20.0, 30.0, 40.0], "mfi_esik": [20.0, 30.0, 40.0], "st_esik": [20.0, 30.0, 40.0]}

    def kosullar(self, m):
        p = self.parametreler
        kos, cik = _stoch_ema_kanal(m, p["adx_min"], p["mfi_esik"], p["st_esik"], p["ac_k"], p["cik_k"], True)
        return {"long": kos, "cikis_long": cik}


class FtSimpleMacdRsi(D3Taban):
    """dis__ft-simple-macd-rsi (scalp, 5m-15m) — freqtrade Simple. Kural (momentum): MACD > 0 VE MACD > sinyal VE Bollinger
    üst bandı yükseliyor (ust[t] > ust[t-1]) VE RSI(14) > rsi_al (70) -> long. Çıkış: RSI > rsi_sat (80)."""
    ad = "dis__ft-simple-macd-rsi"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "rsi_al": 70.0, "rsi_sat": 80.0}
    parametre_izgarasi = {"rsi_al": [60.0, 70.0, 75.0], "rsi_sat": [75.0, 80.0, 90.0], "stop_atr_k": [2.0, 2.5, 3.5]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        mc = g.macd(k)
        ust = g.bollinger(k, 20, 2.0)["ust"]
        r = g.rsi(k, 14)
        return {"long": (mc["macd"] > 0) & (mc["macd"] > mc["sinyal"]) & (ust > ust.shift(1)) & (r > p["rsi_al"]),
                "cikis_long": r > p["rsi_sat"]}


class FtStrategy002(D3Taban):
    """dis__ft-strategy002 (scalp, 5m-15m) — freqtrade Strategy002. Kural: RSI(14) < 30 VE yavaş stokastik %K(14,3) < 20 VE
    kapanış < alt Bollinger(20, 2) VE çekiç mumu (alt fitil >= 2 x gövde, üst fitil <= %10 aralık) -> long. Çıkış: Parabolik
    SAR fiyatın üstüne geçti (trend düşüş) VE Fisher RSI > 0.3."""
    ad = "dis__ft-strategy002"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "rsi_alt": 30.0, "stoch_alt": 20.0, "fisher_cikis": 0.3,
                               "cekic_alt_k": 2.0, "cekic_ust": 0.1}
    parametre_izgarasi = {"rsi_alt": [25.0, 30.0, 40.0], "stoch_alt": [20.0, 30.0, 40.0], "fisher_cikis": [0.0, 0.3, 0.6]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        st = g.stokastik(y, d, k, 14, 3)
        giris = (g.rsi(k, 14) < p["rsi_alt"]) & (st["k"] < p["stoch_alt"]) & (k < g.bollinger(k, 20, 2.0)["alt"]) \
            & cekic(m, float(p["cekic_alt_k"]), float(p["cekic_ust"]))
        cik = (g.psar(y, d)["yon"] == -1) & (fisher_rsi(k) > p["fisher_cikis"])
        return {"long": giris, "cikis_long": cik}


class FtStrategy003(D3Taban):
    """dis__ft-strategy003 (scalp, 5m-15m) — freqtrade Strategy003. Kural: RSI(14) < 28 VE Fisher RSI < -0.94 VE kapanış <
    SMA(40) VE MFI(14) < 16 -> long. Çıkış: Parabolik SAR fiyatın üstünde (düşüş) VEYA Fisher RSI > 0.3."""
    ad = "dis__ft-strategy003"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "rsi_alt": 28.0, "fisher_alt": -0.94, "mfi_alt": 16.0, "fisher_cikis": 0.3}
    parametre_izgarasi = {"rsi_alt": [25.0, 28.0, 35.0], "fisher_alt": [-0.98, -0.94, -0.8], "mfi_alt": [10.0, 16.0, 25.0]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        fr = fisher_rsi(k)
        giris = (g.rsi(k, 14) < p["rsi_alt"]) & (fr < p["fisher_alt"]) & (k < g.sma(k, 40)) \
            & (mfi(y, d, k, m["hacim"], 14) < p["mfi_alt"])
        return {"long": giris, "cikis_long": (g.psar(y, d)["yon"] == -1) | (fr > p["fisher_cikis"])}


class FtStrategy004(D3Taban):
    """dis__ft-strategy004 (scalp, 5m-15m) — freqtrade Strategy004. Kural: (ADX(14) > 50 VEYA yavaş ADX(35) > 26) VE CCI(20) <
    -100 VE yavaş stokastik %K, %D'yi yukarı keser (dönüş) -> long. Çıkış: ADX(14) < 25. VARSAYIM: 'yavaş ADX' periyodu 35."""
    ad = "dis__ft-strategy004"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "adx_yuksek": 50.0, "adx_yavas_esik": 26.0, "adx_cikis": 25.0}
    parametre_izgarasi = {"adx_yuksek": [40.0, 50.0, 60.0], "adx_yavas_esik": [20.0, 26.0, 30.0], "adx_cikis": [15.0, 25.0, 35.0]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        adx = g.adx(y, d, k, 14)["adx"]
        yavas = g.adx(y, d, k, 35)["adx"]
        st = g.stokastik(y, d, k, 14, 3)
        giris = ((adx > p["adx_yuksek"]) | (yavas > p["adx_yavas_esik"])) & (cci(y, d, k, 20) < -100.0) \
            & yukari_kesis(st["k"], st["d"])
        return {"long": giris, "cikis_long": adx < p["adx_cikis"]}


class FtSwingHighToSky(D3Taban):
    """dis__ft-swinghightosky (scalp, 15m) — freqtrade SwingHighToSky. Kural: `kayma` mum ÖNCEKİ CCI(20) < -cci_esik VE `kayma` mum
    önceki RSI(14) < rsi_alt (zaman kaydırmalı aşırı satım; kayma >= 0, geriye doğru -> lookahead yok) -> long. Çıkış: anlık
    CCI > cci_esik VEYA RSI > rsi_ust. VARSAYIM: eşikler 100 / 30 / 70, kayma 1 (belgede sayı yok)."""
    ad = "dis__ft-swinghightosky"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "cci_esik": 100.0, "rsi_alt": 30.0, "rsi_ust": 70.0, "kayma": 1}
    parametre_izgarasi = {"cci_esik": [100.0, 150.0, 200.0], "rsi_alt": [25.0, 30.0, 35.0], "kayma": [0, 1, 2]}

    def kosullar(self, m):
        p = self.parametreler
        c = cci(m["yuksek"], m["dusuk"], m["kapanis"], 20)
        r = g.rsi(m["kapanis"], 14)
        s = int(p["kayma"])
        return {"long": (c.shift(s) < -p["cci_esik"]) & (r.shift(s) < p["rsi_alt"]),
                "cikis_long": (c > p["cci_esik"]) | (r > p["rsi_ust"])}


# =============================================================================== kural / jesuistm (çoğu 1d)
class BtfdGunlukDip(D3Taban):
    """dis__btfd-gunluk-dip (swing, 1d) — kural 'BTFD: low/high-1 <= -%1, 2 gün tut'. Kural: mumun düşüğü / yükseği - 1 <=
    -dusus (0.01) ise (gün içi aralık en az %1 aşağı) kapanışta long; zaman_cikisi (2) mum sonra çık. Tek yönlü, tek pozisyon;
    ek alım/ortalama düşürme YOK (motor açıkken sinyali yok sayar). ATR stop eklendi (orijinalde yok)."""
    ad = "dis__btfd-gunluk-dip"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "zaman_cikisi": 2, "dusus": 0.01}
    parametre_izgarasi = {"dusus": [0.01, 0.02, 0.03], "zaman_cikisi": [1, 2, 3], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        return {"long": (m["dusuk"] / m["yuksek"] - 1.0) <= -self.parametreler["dusus"]}


class GostergeRezonansi(D3Taban):
    """dis__gosterge-rezonansi (swing, 1d) — kural 'MACD>0, 50<RSI<75, ADX>20'. Durum: MACD(12,26,9) çizgisi > 0 VE rsi_alt < RSI(14)
    < rsi_ust VE ADX(14) > adx_min. Durum başlayınca long; durum bozulunca çık."""
    ad = "dis__gosterge-rezonansi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "rsi_alt": 50.0, "rsi_ust": 75.0, "adx_min": 20.0}
    parametre_izgarasi = {"rsi_alt": [45.0, 50.0, 55.0], "rsi_ust": [70.0, 75.0, 80.0], "adx_min": [15.0, 20.0, 25.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        r = g.rsi(k, 14)
        durum = (g.macd(k)["macd"] > 0) & (r > p["rsi_alt"]) & (r < p["rsi_ust"]) \
            & (g.adx(m["yuksek"], m["dusuk"], k, 14)["adx"] > p["adx_min"])
        return {"long": gecis(durum), "cikis_long": ~durum}


class MaDizilim51030(D3Taban):
    """dis__ma-dizilim-5-10-30 (swing, 1d) — kural 'SMA5>SMA10>SMA30 dizilimi'. Dizilim başlayınca long; bozulunca çık
    (kısa SMA'lar parametre: hizli/orta/yavas). Short aynası: SMA5<SMA10<SMA30 (yonler='ls')."""
    ad = "dis__ma-dizilim-5-10-30"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "hizli": 5, "orta": 10, "yavas": 30}
    parametre_izgarasi = {"hizli": [3, 5, 8], "orta": [10, 13, 20], "yavas": [30, 50]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        a, b, c = g.sma(k, int(p["hizli"])), g.sma(k, int(p["orta"])), g.sma(k, int(p["yavas"]))
        yuk, asg = (a > b) & (b > c), (a < b) & (b < c)
        return {"long": gecis(yuk), "short": gecis(asg), "cikis_long": ~yuk, "cikis_short": ~asg}


class MacdKdj4h(D3Taban):
    """dis__macd-kdj-4h (swing, 4h) — kural 'MACD+KDJ (4h), %2 stop, +%5 sonra %1 iz'. Kural: MACD(12,26,9) > sinyal VE KDJ(9)
    K > D (onay) durumu BAŞLAYINCA long; çıkış: MACD < sinyal VE K < D. Stop %2 (stop_yuzde). İzleyen stop: kaynaktaki '+%5
    sonrası %1 iz' motorda yok -> YAKLAŞIK: basabas_r_esigi = 2.5 R (=%5 kâr, %2 stop) sonrası stop girişe çekilir.
    Short ayna (yonler='ls')."""
    ad = "dis__macd-kdj-4h"
    stil = "swing"
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=2.5)
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.02, "kdj_n": 9}
    parametre_izgarasi = {"stop_yuzde": [0.015, 0.02, 0.03], "kdj_n": [6, 9, 14]}

    def kosullar(self, m):
        p = self.parametreler
        mc = g.macd(m["kapanis"])
        kd = kdj(m["yuksek"], m["dusuk"], m["kapanis"], int(p["kdj_n"]))
        yuk, asg = (mc["macd"] > mc["sinyal"]) & (kd["k"] > kd["d"]), (mc["macd"] < mc["sinyal"]) & (kd["k"] < kd["d"])
        return {"long": gecis(yuk), "short": gecis(asg), "cikis_long": asg, "cikis_short": yuk}


class MacdSmaCift(D3Taban):
    """dis__macd-sma-cift (swing, 1d) — kural 'MACD+SMA çift sinyal (SMA10/30 & MACD 12/26/9)'. Kural: SMA(10) SMA(30)'u yukarı
    keser VE MACD sinyali yukarı keser; iki kesişim en fazla `pencere` mum arayla gerçekleşmişse ('aynı anda') long (ikincisi
    gerçekleştiği mumda). Çıkış: SMA(10) SMA(30)'u aşağı keser VEYA MACD sinyali aşağı keser. Short ayna (yonler='ls').
    VARSAYIM: 'aynı anda' = pencere (varsayılan 2) mum içinde."""
    ad = "dis__macd-sma-cift"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "sma_h": 10, "sma_y": 30, "pencere": 2}
    parametre_izgarasi = {"sma_h": [5, 10, 20], "sma_y": [30, 50], "pencere": [1, 2, 4]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        a, b = g.sma(k, int(p["sma_h"])), g.sma(k, int(p["sma_y"]))
        mc = g.macd(k)
        w = int(p["pencere"])
        s_u, s_d = yukari_kesis(a, b), asagi_kesis(a, b)
        m_u, m_d = yukari_kesis(mc["macd"], mc["sinyal"]), asagi_kesis(mc["macd"], mc["sinyal"])

        def son(x):
            return x.rolling(w, min_periods=1).max().astype(bool)
        return {"long": (s_u | m_u) & son(s_u) & son(m_u), "short": (s_d | m_d) & son(s_d) & son(m_d),
                "cikis_long": s_d | m_d, "cikis_short": s_u | m_u}


class _RsiMa(D3Taban):
    """RSI-MA ortak gövdesi: RSI(rsi_n)'in SMA(ma_n)'sı = RSI-MA. mod 'trend': RSI-MA > ust -> long, < alt -> short (momentum);
    mod 'donus': RSI-MA < alt -> long, > ust -> short (ortalamaya dönüş). Çıkış: RSI-MA iki seviyenin ortasına döner (long
    için trend modunda orta altına, dönüş modunda orta üstüne). VARSAYIM: kaynak yalnız 'seviyelerde giriş' diyor; yön
    belirsiz -> mod parametresi ızgarada."""
    stil = "swing"

    def kosullar(self, m):
        p = self.parametreler
        if p["mod"] not in ("trend", "donus"):
            raise ValueError("mod 'trend' veya 'donus' olmalı")
        rm = g.sma(g.rsi(m["kapanis"], int(p["rsi_n"])), int(p["ma_n"]))
        orta = (p["alt"] + p["ust"]) / 2.0
        yuk, asg = rm > p["ust"], rm < p["alt"]
        if p["mod"] == "trend":
            return {"long": gecis(yuk), "short": gecis(asg), "cikis_long": rm < orta, "cikis_short": rm > orta}
        return {"long": gecis(asg), "short": gecis(yuk), "cikis_long": rm > orta, "cikis_short": rm < orta}


class RsiMaNormal(_RsiMa):
    """dis__rsi-ma-normal (swing, 1d) — kural 'RSI-MA normal seviyeler 48.62/53.63'. Bkz. _RsiMa."""
    ad = "dis__rsi-ma-normal"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "rsi_n": 14, "ma_n": 14, "alt": 48.62,
                               "ust": 53.63, "mod": "trend"}
    parametre_izgarasi = {"mod": ["trend", "donus"], "ma_n": [7, 14, 21], "rsi_n": [9, 14]}


class RsiMaUc(_RsiMa):
    """dis__rsi-ma-uc (swing, 1d) — kural 'RSI-MA uç seviyeler 39.57/67.45'. Bkz. _RsiMa."""
    ad = "dis__rsi-ma-uc"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "rsi_n": 14, "ma_n": 14, "alt": 39.57,
                               "ust": 67.45, "mod": "trend"}
    parametre_izgarasi = {"mod": ["trend", "donus"], "ma_n": [7, 14, 21], "rsi_n": [9, 14]}


class StochRsiUc4h(D3Taban):
    """dis__stochrsi-uc-4h (swing, 4h) — kural 'StochRSI uç değerlerinde ters yönde giriş (4h)'. Kural: StochRSI %K (14,14,3) <
    alt (20) -> long (aşırı satım); > ust (80) -> short. Çıkış: %K 50'yi geçince (long için yukarı, short için aşağı)."""
    ad = "dis__stochrsi-uc-4h"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "alt": 20.0, "ust": 80.0, "rsi_n": 14}
    parametre_izgarasi = {"alt": [10.0, 20.0, 30.0], "rsi_n": [7, 14, 21], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        kk = stoch_rsi(m["kapanis"], int(p["rsi_n"]), 14, 3, 3)["k"]
        return {"long": gecis(kk < p["alt"]), "short": gecis(kk > p["ust"]),
                "cikis_long": kk > 50.0, "cikis_short": kk < 50.0}


class GmmaLs(D3Taban):
    """dis__gmma-ls (swing, 1d) — kural 'TechIndicator GMMA L/S'. GMMA: kısa grup EMA(3,5,8,10,12,15), uzun grup EMA(30,35,40,45,50,60)
    (x olcek). Kısa grubun EN DÜŞÜĞÜ uzun grubun EN YÜKSEĞİNİN üstüne çıkınca long (gruplar ayrışmış yükseliş); kısa grup uzun
    gruba geri girince çık. Short ayna. VARSAYIM: standart Guppy periyotları."""
    ad = "dis__gmma-ls"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "olcek": 1.0}
    parametre_izgarasi = {"olcek": [0.5, 1.0, 2.0], "stop_atr_k": [2.0, 3.0, 4.0]}
    _KISA = (3, 5, 8, 10, 12, 15)
    _UZUN = (30, 35, 40, 45, 50, 60)

    def kosullar(self, m):
        k = m["kapanis"]
        o = float(self.parametreler["olcek"])
        kisa = pd.concat([g.ema(k, max(2, int(round(n * o)))) for n in self._KISA], axis=1)
        uzun = pd.concat([g.ema(k, max(2, int(round(n * o)))) for n in self._UZUN], axis=1)
        yuk = kisa.min(axis=1, skipna=False) > uzun.max(axis=1, skipna=False)
        asg = kisa.max(axis=1, skipna=False) < uzun.min(axis=1, skipna=False)
        return {"long": gecis(yuk), "short": gecis(asg), "cikis_long": ~yuk, "cikis_short": ~asg}


class BollingerWDibi(D3Taban):
    """dis__bollinger-w-dibi (daytrade, 1h) — jesuistm JT_Bollinger_W (Bollinger(75), W dibi). Kural (Merrill W dibi): son `pencere`
    mum içinde bir ilk dip (düşüğü alt banda değmiş/altına inmiş), ondan en az `ara` mum sonra ikinci dip (düşüğü ilk dipten
    YUKARIDA ve alt banda DEĞMEMİŞ), ve kapanış orta bandı yukarı keserse long. Çıkış: bant genişliği (üst-alt)/orta, son
    `bw_n` mumun ortalamasının bw_k katından küçük kalırsa (bantlar daraldı). Stop: ATR. VARSAYIM: pencere 40, ara 5, bw_k 0.8."""
    ad = "dis__bollinger-w-dibi"
    stil = "daytrade"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "bb_n": 75, "bb_sapma": 2.0, "pencere": 40, "ara": 5,
                               "bw_n": 50, "bw_k": 0.8}
    parametre_izgarasi = {"pencere": [30, 40, 60], "ara": [3, 5, 8], "bw_k": [0.6, 0.8, 1.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, d = m["kapanis"], m["dusuk"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_sapma"]))
        dn, al = d.to_numpy(), bb["alt"].to_numpy()
        n, w, ara = len(m), int(p["pencere"]), int(p["ara"])
        dokun = (dn <= al) & ~np.isnan(al)
        w_ok = np.zeros(n, dtype=bool)
        for i in range(n):
            lo = max(0, i - w)
            if i - lo < ara + 2:
                continue
            seg = slice(lo, i - ara + 1)
            idxs = np.nonzero(dokun[seg])[0]
            if len(idxs) == 0:
                continue
            # ilk dip: dokunan mumlar arasında en düşük düşük
            j = lo + idxs[np.argmin(dn[seg][idxs])]
            sonra = slice(j + ara, i + 1)
            if j + ara > i:
                continue
            ikinci = np.argmin(dn[sonra]) + j + ara
            w_ok[i] = (dn[ikinci] > dn[j]) and (not dokun[ikinci])
        w_ok = pd.Series(w_ok, index=m.index)
        giris = yukari_kesis(k, bb["orta"]) & w_ok
        bw = (bb["ust"] - bb["alt"]) / bb["orta"]
        dar = bw < p["bw_k"] * bw.rolling(int(p["bw_n"]), min_periods=int(p["bw_n"])).mean()
        return {"long": giris, "cikis_long": dar}


class BasOmuzRsiShort(Strateji):
    """dis__bas-omuz-rsi-short (swing, 1d) — jesuistm JT_RSI_omuz_bas_omuz. Kural: ardışık üç onaylı pivot tepesi (pivot_n sol/sağ)
    sol omuz, baş, sağ omuz: baş iki omuzdan yüksek, omuzlar birbirine omuz_tol (%5) içinde, RSI(14) sağ omuzda baştakinden
    düşük (RSI teyidi = ayı uyumsuzluğu). Boyun çizgisi = iki omuz arasındaki en düşük DÜŞÜK. Sağ omuz onaylandıktan sonra
    `bekle` mum içinde kapanış boyun çizgisinin altına inerse SHORT. Stop: baş + 0.2 ATR. Çıkış: RSI, girişteki RSI'dan
    rsi_artis (4) puan yükselirse VEYA zaman_cikisi (5) mum sonra. Yalnız short. Pivotlar `pivot_n` mum gecikmeyle bilinir
    (nedensel)."""
    ad = "dis__bas-omuz-rsi-short"
    stil = "swing"
    varsayilan_parametreler = {"pivot_n": 3, "omuz_tol": 0.05, "bekle": 10, "rsi_artis": 4.0, "zaman_cikisi": 5,
                               "stop_tampon_atr": 0.2}
    parametre_izgarasi = {"pivot_n": [2, 3, 5], "omuz_tol": [0.03, 0.05, 0.08], "bekle": [5, 10, 20]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"].to_numpy(), m["dusuk"].to_numpy(), m["kapanis"].to_numpy()
        n, pn = len(m), int(p["pivot_n"])
        rsi = g.rsi(m["kapanis"], 14)
        r = rsi.to_numpy()
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], 14).to_numpy()
        # onaylı pivot tepeleri: j mumu, solundaki pn mumdan KESİN, sağındaki pn mumdan en az eşit yüksek; i = j + pn anında bilinir
        piv = []   # (j, onay_i)
        short = np.zeros(n, dtype=bool)
        stop_s = np.full(n, np.nan)
        aktif = None   # (boyun, baş_yuksek, bitis_i)
        for i in range(n):
            j = i - pn
            if j >= pn and y[j] > y[j - pn:j].max() and y[j] >= y[j + 1:i + 1].max():
                piv.append(j)
                if len(piv) >= 3:
                    a, b, c = piv[-3], piv[-2], piv[-1]
                    if y[b] > y[a] and y[b] > y[c] and abs(y[a] - y[c]) <= p["omuz_tol"] * y[b] \
                            and not np.isnan(r[c]) and not np.isnan(r[b]) and r[c] < r[b]:
                        aktif = (d[a:c + 1].min(), y[b], i + int(p["bekle"]))
            if aktif is not None:
                boyun, bas, bitis = aktif
                if i > bitis:
                    aktif = None
                elif k[i] < boyun and not np.isnan(atr[i]):
                    short[i] = True
                    stop_s[i] = bas + p["stop_tampon_atr"] * atr[i]
                    aktif = None
        ss = pd.Series(short, index=m.index)
        sig = cerceve(m, _bos(m.index), ss, pd.Series(np.nan, index=m.index), pd.Series(stop_s, index=m.index))
        giris_rsi = rsi.where(sig["yon"] == -1).ffill()
        sig["cikis_long"] = _bos(m.index)
        sig["cikis_short"] = (rsi >= giris_rsi + p["rsi_artis"]).fillna(False)
        sig["zaman_cikisi_mum"] = pd.Series(np.where(sig["yon"] != 0, float(p["zaman_cikisi"]), np.nan), index=m.index)
        return sig


class ShootingStarOnay(D3Taban):
    """dis__shooting-star-onay (swing, 1d) — jesuistm JT_Shooting_Star. Kural: ters çekiç (shooting star: üst fitil >= 2 x gövde,
    alt fitil <= %10 aralık) VE önceki `yukselis_n` mumda yükseliş (kapanış > yukselis_n mum önceki kapanış) VE ertesi mum
    ONAY verirse (kapanış, yıldız mumunun düşüğünün altında) kapanışta SHORT; zaman_cikisi (7) mum tut. Stop: ATR
    (yıldızın yükseği ATR stoptan yakınsa o kullanılmaz; basit ATR stop). yonler sabit short."""
    ad = "dis__shooting-star-onay"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "short", "stop_atr_k": 3.0, "zaman_cikisi": 7, "yukselis_n": 3, "ust_k": 2.0}
    parametre_izgarasi = {"zaman_cikisi": [3, 7, 10], "yukselis_n": [2, 3, 5], "ust_k": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        yildiz = ters_cekic(m, float(p["ust_k"])) & (m["kapanis"] > m["kapanis"].shift(int(p["yukselis_n"])))
        onay = yildiz.shift(1, fill_value=False) & (m["kapanis"] < m["dusuk"].shift(1))
        return {"short": onay}


# =============================================================================== ek_77 belgesi
class CryptoFrogDip(D3Taban):
    """dis__cryptofrog-dip (scalp, 15m; orijinal 5m) — ek_77 #14 CryptoFrog (froggleston). Long-only 'dip alma'.
    Ön koşul: kapanış < düzleştirilmiş Heikin-Ashi dibi (HA düşüğünün EMA(duz_n)'si) VE 1h HA kapanışının EMA(20)'si düşüyor
    (htf.ust_zaman, yalnız kapanmış mumlar) VE VFI < 0 (hacim akışı negatif). Dört tetikten biri:
      T1 Bollinger genişliyor (genişlik > önceki) VE sıkışma yok VE (MFI < 20 VEYA DMI- > 30)
      T2 Parabolik SAR fiyatın üstünde VE StochRSI %K < 20 VE hızlı stokastik %K < 20 VE MFI < 30
      T3 DMI- yukarı keser DMI+ (dmi_minus_kesis) VE kapanış < alt Bollinger(20, 2)
      T4 sıkışma VE hızlı stokastik %D < 20
    Çıkış (simetrik aşırı alım): kapanış > üst Bollinger VE MFI > 80. Orijinalin ROI tablosu, +%4.7 izleyen stopu ve sönümlenen
    özel stopu motorda yok: ATR stop + zaman_cikisi. VARSAYIM / ATLANAN: 'any old SQZMI' notundaki sıkışma tanımı belgede
    yok -> Bollinger(20,2) Keltner(20, 1.5 ATR) içinde = sıkışma; T3'teki 'DMI- kesişimi' belirsiz -> DMI-, DMI+'yı yukarı
    keser; orijinaldeki hyperopt sayıları belgede yok -> yukarıdaki eşikler bizim seçimimiz. Belge bu stratejiyi overfit
    işaretli sayar (README: 'DO NOT USE FOR LIVE'); katalogda aday olarak test edilir, kanıt değil."""
    ad = "dis__cryptofrog-dip"
    stil = "scalp"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.5, "zaman_cikisi": 48, "duz_n": 10, "vfi_esik": 0.0,
                               "mfi_alt": 20.0, "dmi_esik": 30.0, "ust_tf": "1h"}
    parametre_izgarasi = {"duz_n": [5, 10, 20], "mfi_alt": [15.0, 20.0, 30.0], "dmi_esik": [25.0, 30.0, 35.0]}

    def kosullar(self, m):
        p = self.parametreler
        o, y, d, k, v = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"], m["hacim"]
        ha = heikin_ashi(o, y, d, k)
        on = k < g.ema(ha["ha_dusuk"], int(p["duz_n"]))

        def ust_f(u):
            h = heikin_ashi(u["acilis"], u["yuksek"], u["dusuk"], u["kapanis"])["ha_kapanis"]
            e = g.ema(h, 20)
            return pd.DataFrame({"dusus": (e < e.shift(1)).astype(float).where(e.notna() & e.shift(1).notna())})
        ust_dusus = ust_zaman(m, p["ust_tf"], ust_f)["dusus"] > 0.5
        on &= ust_dusus & (vfi(y, d, k, v) < p["vfi_esik"])

        bb = g.bollinger(k, 20, 2.0)
        gen = (bb["ust"] - bb["alt"])
        kc_a = g.atr(y, d, k, 20) * 1.5
        sik = (bb["alt"] > g.ema(k, 20) - kc_a) & (bb["ust"] < g.ema(k, 20) + kc_a)
        mf = mfi(y, d, k, v, 14)
        dmi = g.adx(y, d, k, 14)
        st = hizli_stokastik(y, d, k, 5, 3)
        srsi = stoch_rsi(k)["k"]
        t1 = (gen > gen.shift(1)) & ~sik & ((mf < p["mfi_alt"]) | (dmi["eksi_di"] > p["dmi_esik"]))
        t2 = (g.psar(y, d)["yon"] == -1) & (srsi < 20.0) & (st["k"] < 20.0) & (mf < 30.0)
        t3 = yukari_kesis(dmi["eksi_di"], dmi["arti_di"]) & (k < bb["alt"])
        t4 = sik & (st["d"] < 20.0)
        return {"long": on & (t1 | t2 | t3 | t4), "cikis_long": (k > bb["ust"]) & (mf > 80.0)}


class SolipsisRmi(D3Taban):
    """dis__solipsis-rmi (scalp, 15m; orijinal 5m) — ek_77 #15 Solipsis v5 (werkkrew). Düşüş trendinde dönüş. Kural (long): RMI(14,
    mom=3) önceki mumda en az `dus_seri` (3) mumdur düşüyordu VE şimdi yukarı döndü (RMI[t] > RMI[t-1]) VE RMI rmi_alt..rmi_ust
    (20..50) arasında VE kapanış art arda en az `ma_seri` (1) mumdur KAMA(10)'un altında VE Momentum Pinball (RSI(3) of ROC(1))
    <= pinball_maks (30) VE kapanış, son gun_mum mumun (≈1 gün) dibinden en fazla adr_k (0.8) x ADR yukarıda (ADR = son adr_gun
    günlük kayan aralığın ortalaması). Çıkış: izleyen ATR stopu (CikisAyarlari atr_iz_suren_k=2) ve zaman_cikisi (48 mum =
    720 dk/15m; orijinal custom_sell %1 geri çekilme + 720 dk ROI basamağı). ATLANAN: BTC bilgilendirici filtresi (çok
    sembollü), 25+ hyperopt parametresi. VARSAYIM: gun_mum 96 (15m taban), ADR kayan-24s aralığından türetildi (belgede tam
    formül yok)."""
    ad = "dis__solipsis-rmi"
    stil = "scalp"
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=2.0)
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "zaman_cikisi": 48, "dus_seri": 3, "ma_seri": 1, "rmi_alt": 20.0,
                               "rmi_ust": 50.0, "pinball_maks": 30.0, "adr_k": 0.8, "gun_mum": 96, "adr_gun": 5}
    parametre_izgarasi = {"dus_seri": [2, 3, 4], "pinball_maks": [20.0, 30.0, 40.0], "adr_k": [0.5, 0.8, 1.2]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        r = rmi(k, 14, 3)
        dusen = r < r.shift(1)
        seri_onceki = ardisik_say(dusen).shift(1)
        gm, ag = int(p["gun_mum"]), int(p["adr_gun"])
        alt24 = d.rolling(gm, min_periods=gm).min()
        aralik24 = y.rolling(gm, min_periods=gm).max() - alt24
        adr = aralik24.rolling(gm * ag, min_periods=gm * ag).mean()
        ma_seri = ardisik_say(k < kama(k, 10))
        giris = (seri_onceki >= p["dus_seri"]) & (r > r.shift(1)) & (r >= p["rmi_alt"]) & (r <= p["rmi_ust"]) \
            & (ma_seri >= p["ma_seri"]) & (pinball(k, 3) <= p["pinball_maks"]) & ((k - alt24) <= p["adr_k"] * adr)
        return {"long": giris}


class HaGucluDususAl(D3Taban):
    """dis__ha-guclu-dusus-al (swing, 1d) — ek_77 #38 Heikin-Ashi (je-suis-tm/quant-trading). HA kapanış (O+H+L+C)/4, HA açılış =
    (önceki HA açılış + önceki HA kapanış)/2. Al: HA düşüş mumu (HA açılış > HA kapanış) VE üst fitil yok (HA yüksek - HA açılış
    <= fitil_tol x aralık) VE gövde, önceki gövdenin govde_k katından büyük VE önceki mum da düşüş. (Yani güçlenen düşüşte alım:
    kaynak kodun gerçek davranışı; belge bunu açıkça not ediyor.) Sat/çık: iki ardışık HA yükseliş mumu VE alt fitil yok. Yalnız
    long, tek pozisyon (orijinaldeki 3 lota kadar ekleme YASAK/atlandı: ortalama düşürme). ATR stop eklendi. Sinyal kapanışta,
    dolum sonraki açılışta (kaynaktaki aynı-kapanış iyimserliği yok)."""
    ad = "dis__ha-guclu-dusus-al"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "fitil_tol": 0.0, "govde_k": 1.0}
    parametre_izgarasi = {"fitil_tol": [0.0, 0.05, 0.1], "govde_k": [0.8, 1.0, 1.3], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        ha = heikin_ashi(m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"])
        ho, hc, hy, hd = ha["ha_acilis"], ha["ha_kapanis"], ha["ha_yuksek"], ha["ha_dusuk"]
        aralik = hy - hd
        kirmizi, yesil = ho > hc, hc > ho
        govde = (ho - hc).abs()
        al = kirmizi & ((hy - ho) <= p["fitil_tol"] * aralik) & (govde > p["govde_k"] * govde.shift(1)) & kirmizi.shift(1, fill_value=False)
        sat = yesil & yesil.shift(1, fill_value=False) & ((ho - hd) <= p["fitil_tol"] * aralik)
        return {"long": al, "cikis_long": sat}


class BbrsiDonus(Strateji):
    """dis__bbrsi-donus (scalp, 5m-15m) — ek_77 #59 Geraked BBRSI (MIT, XAUUSD 5m), YALNIZ SAF GİRİŞ KURALI. Kural (long): bir önceki
    mumda RSI(7) < 30 ve kapanış < alt Bollinger(500, 2); şimdi RSI > 30'a döndü ve kapanış alt bandın üstüne döndü ama orta
    bandın altında -> long. Short ayna (70, üst bant). Stop: alt bandın sl_k (0.9) x (orta - alt) altı (short: üstü); hedef:
    giriş-stop mesafesinin tp_k (1) katı. ATLANDI/YASAK: belgedeki commit edilmiş ayar (Grid=true, GridVolMult 1.1, 20 kademe,
    IgnoreSL/IgnoreTP) martingale benzeri pozisyon büyütme + stopsuzdur -> KODLANMADI; kod belgenin önerdiği 'Grid=false,
    IgnoreSL=false' sürümüdür. %50 izleyen stop ve 'orta banda dönüşte kârdayken kapat' orijinal EA'ya özgü, bu sürümde yok."""
    ad = "dis__bbrsi-donus"
    stil = "scalp"
    varsayilan_parametreler = {"bb_n": 500, "bb_sapma": 2.0, "rsi_n": 7, "rsi_alt": 30.0, "rsi_ust": 70.0, "sl_k": 0.9,
                               "tp_k": 1.0, "short": True}
    parametre_izgarasi = {"bb_n": [100, 200, 500], "sl_k": [0.5, 0.9, 1.3], "tp_k": [0.75, 1.0, 1.5]}

    def cikis_var_mi(self):
        return True

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_sapma"]))
        r = g.rsi(k, int(p["rsi_n"]))
        long_ok = (r.shift(1) < p["rsi_alt"]) & (r > p["rsi_alt"]) & (k.shift(1) < bb["alt"].shift(1)) \
            & (k > bb["alt"]) & (k < bb["orta"])
        short_ok = ((r.shift(1) > p["rsi_ust"]) & (r < p["rsi_ust"]) & (k.shift(1) > bb["ust"].shift(1))
                    & (k < bb["ust"]) & (k > bb["orta"])) if p["short"] else _bos(m.index)
        stop_l = bb["alt"] - p["sl_k"] * (bb["orta"] - bb["alt"])
        stop_s = bb["ust"] + p["sl_k"] * (bb["ust"] - bb["orta"])
        out = kur(m, long_ok, short_ok, stop_l, stop_s)
        return r_hedefi(out, k, float(p["tp_k"]))


class EmaEsikTrend(D3Taban):
    """dis__ema-esik-trend (swing, 1d) — ek_77 #63 Lean Futures Momentum. Kural: EMA(20) > EMA(60) x (1 + esik) (esik 0.001) olunca
    long (durum başlayınca); EMA(20) < EMA(60) x (1 + esik) olunca çık. Orijinalde short ve stop yok, sabit 1 kontrat -> ATR
    stop, short isteğe bağlı (yonler='ls', ayna eşik: EMA20 < EMA60 x (1 - esik)). Vadeli roll / kontrat seçimi ilgisiz (perp)."""
    ad = "dis__ema-esik-trend"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "ema_h": 20, "ema_y": 60, "esik": 0.001}
    parametre_izgarasi = {"ema_h": [10, 20, 30], "ema_y": [50, 60, 100], "esik": [0.0, 0.001, 0.005]}

    def kosullar(self, m):
        p = self.parametreler
        a, b = g.ema(m["kapanis"], int(p["ema_h"])), g.ema(m["kapanis"], int(p["ema_y"]))
        yuk, asg = a > b * (1.0 + p["esik"]), a < b * (1.0 - p["esik"])
        return {"long": gecis(yuk), "short": gecis(asg), "cikis_long": a < b * (1.0 + p["esik"]),
                "cikis_short": a > b * (1.0 - p["esik"])}


class AcryptoAgirlikli(D3Taban):
    """dis__acrypto-agirlikli (swing, 4h) — ek_77 #70 Acrypto Weighted Strategy (Pine, CC BY-NC-SA; KOD KOPYALANMADI, yalnız
    kural anlatımı). Beş alt durum, her biri +1 (yükseliş) / -1 (düşüş) x ağırlık (0..5): MACD > sinyal; StochRSI %K > %D; RSI(14)
    > 50; Supertrend(10, 3) yönü; EMA(9) > EMA(21). Toplam skor >= tetik -> long; <= -tetik -> short (skora yeni girişte
    sinyal). Çıkış: ters tetik. Stop yuzde stop_yuzde (%6); kâr al hedef_yuzde (0 = yok; orijinal %6.8 long / %13 short
    kademeli). ATLANDI: kademeli kâr alma (her TP'de pozisyonun %15/%10'u + stopu TP-2'ye taşıma), tepe/dip tespiti kısmi
    kapanışı (belgede kuralı yok; kismi CikisAyarlari ile dışarıdan verilebilir). VARSAYIM: alt sinyal tanımları durum
    tabanlı; 40+ girdinin kalanı belgede yok. Belge: tipik eğri uydurma işaretleri."""
    ad = "dis__acrypto-agirlikli"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_yuzde": 0.06, "hedef_yuzde": 0.0, "tetik": 3,
                               "w_macd": 1, "w_srsi": 1, "w_rsi": 1, "w_st": 1, "w_ma": 1}
    parametre_izgarasi = {"tetik": [2, 3, 5], "stop_yuzde": [0.04, 0.06, 0.08], "hedef_yuzde": [0.0, 0.068, 0.13]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        mc = g.macd(k)
        sr = stoch_rsi(k)
        sgn = lambda b: np.where(b, 1.0, -1.0)   # noqa: E731
        skor = (p["w_macd"] * sgn(mc["macd"] > mc["sinyal"]) + p["w_srsi"] * sgn(sr["k"] > sr["d"])
                + p["w_rsi"] * sgn(g.rsi(k, 14) > 50.0) + p["w_st"] * g.supertrend(y, d, k, 10, 3.0)["yon"].replace(0, np.nan).to_numpy()
                + p["w_ma"] * sgn(g.ema(k, 9) > g.ema(k, 21)))
        skor = pd.Series(skor, index=m.index)
        hazir = sr["k"].notna() & mc["sinyal"].notna()
        al, sat = (skor >= p["tetik"]) & hazir, (skor <= -p["tetik"]) & hazir
        return {"long": gecis(al), "short": gecis(sat), "cikis_long": sat, "cikis_short": al}


class MtfRsiTrend(D3Taban):
    """dis__mtf-rsi-trend (swing, 1d) — ek_77 #72 backtesting.py 'çok zaman dilimli RSI' (AGPL; KOD KOPYALANMADI). Kural (long): günlük
    RSI(rsi_n=30) > seviye (70) VE haftalık RSI(30) > seviye VE haftalık RSI > günlük RSI VE SMA10 > SMA20 > SMA50 > SMA100 VE
    kapanış > SMA10. Haftalık RSI htf.ust_zaman('1w') ile (yalnız kapanmış haftalar). Çıkış: kapanış SMA10'un %2 altına
    iner. Stop sabit %8 (orijinal). Taban TF günlük olmalı. Belge: 125 kombinasyon aynı veride optimize edilmiş, kenar iddiası yok."""
    ad = "dis__mtf-rsi-trend"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_yuzde": 0.08, "rsi_n": 30, "seviye": 70.0, "cikis_pay": 0.02}
    parametre_izgarasi = {"rsi_n": [14, 21, 30], "seviye": [55.0, 60.0, 70.0], "stop_yuzde": [0.05, 0.08, 0.12]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        n = int(p["rsi_n"])
        gun = g.rsi(k, n)
        hafta = ust_zaman(m, "1w", lambda u: pd.DataFrame({"rsi": g.rsi(u["kapanis"], n)}))["rsi"]
        s10, s20, s50, s100 = (g.sma(k, x) for x in (10, 20, 50, 100))
        giris = (gun > p["seviye"]) & (hafta > p["seviye"]) & (hafta > gun) & (s10 > s20) & (s20 > s50) & (s50 > s100) & (k > s10)
        return {"long": giris, "cikis_long": k < s10 * (1.0 - p["cikis_pay"])}


class MaCiftCross(D3Taban):
    """dis__ma-cift-cross (swing, 4h-1d) — ek_77 #73 vectorbt BTC çift MA çaprazı ve #74 NautilusTrader EMA cross (ma_tipi='ema',
    10/20). Kural: hızlı MA yavaşı yukarı keser -> long, aşağı keser -> short (her zaman piyasada eğilimi; ters kesişim
    çevirir). Orijinalde stop yok -> ATR felaket stopu. Belge: #73 asıl olarak walk-forward doğrulama şablonudur (780 çift,
    Sharpe seçimi): burada o şablon KODLANMADI (walk-forward motorun işi); #74 100 tick'lik barlar verimizde yok -> mum
    verisinde çalışır. Izgara hızlı 10-30, yavaş 40-60 (orijinal 10-49 aralığına yakın)."""
    ad = "dis__ma-cift-cross"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "ma_tipi": "sma", "hizli": 20, "yavas": 50}
    parametre_izgarasi = {"hizli": [10, 20, 30], "yavas": [40, 50, 60], "ma_tipi": ["sma", "ema"]}

    def kosullar(self, m):
        p = self.parametreler
        if p["ma_tipi"] not in ("sma", "ema"):
            raise ValueError("ma_tipi 'sma' veya 'ema' olmalı")
        f = g.sma if p["ma_tipi"] == "sma" else g.ema
        a, b = f(m["kapanis"], int(p["hizli"])), f(m["kapanis"], int(p["yavas"]))
        yuk, asg = yukari_kesis(a, b), asagi_kesis(a, b)
        return {"long": yuk, "short": asg, "cikis_long": asg, "cikis_short": yuk}


class _GunIciTaban(Strateji):
    seans_varsayilan = "abd_hisse"

    def cikis_var_mi(self):
        return True

    def _seans(self, m):
        s = self.parametreler["seans"]
        if s not in ("utc_gun", "abd_hisse"):
            raise ValueError("seans 'abd_hisse' veya 'utc_gun' olmalı")
        return seans_bilgi(m, s)


class Sma20Scalp(_GunIciTaban):
    """dis__sma20-scalp (daytrade, 5m; orijinal 1m) — ek_77 #75 Alpaca Scalping. Kural: kapanış önceki mumda SMA(sma_n=20)'nin altında
    veya eşit, bu mumda üstünde (yukarı kesiş) -> long. Çıkış: hedef = kapanış x (1 + hedef_yuzde) (orijinal: maliyet + 1 sent,
    bunun yüzde karşılığı) VEYA ATR stop (orijinalde STOP YOK, zarardaki pozisyon gün sonuna taşınıyordu: negatif çarpıklık;
    ATR felaket stopu eklendi) VEYA seans sonu zorunlu çıkış (gün içi). Yalnız long. Limit-emir / 2 dk iptal mantığı yok
    (piyasa dolumu sonraki açılışta). seans: 'abd_hisse' (09:30-16:00 NY) ya da 'utc_gun'."""
    ad = "dis__sma20-scalp"
    stil = "daytrade"
    varsayilan_parametreler = {"sma_n": 20, "hedef_yuzde": 0.004, "stop_atr_k": 1.5, "atr_periyot": 14, "seans": "abd_hisse"}
    parametre_izgarasi = {"sma_n": [10, 20, 30], "hedef_yuzde": [0.002, 0.004, 0.008], "stop_atr_k": [1.0, 1.5, 2.5]}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bilgi = self._seans(m)
        ma = g.sma(k, int(p["sma_n"]))
        long_ok = yukari_kesis(k, ma)
        a = g.atr(m["yuksek"], m["dusuk"], k, int(p["atr_periyot"])) * p["stop_atr_k"]
        return gun_ici_cerceve(m, p["seans"], bilgi["c"], long_ok, _bos(m.index), k - a, k + a,
                               hedef_l=k * (1.0 + p["hedef_yuzde"]))


class AlpacaMomentum(_GunIciTaban):
    """dis__alpaca-momentum (daytrade, 5m; orijinal 1s/1dk) — ek_77 #76 Alpaca Momentum day trading (kural anlatımı; kod/Polygon
    yok). Kural (long): seans açılışından sonra ilk_dk (15) ile son_dk (60) dakika arasında: kapanış, önceki seans kapanışına göre
    > min_yuk (%4) yükselmiş VE ilk ilk_dk dakikanın tepesinin üstünde VE mum hacmi > hacim_k x SMA(hacim, 20) VE MACD(12,26,9)
    histogramı pozitif ve son iki mumdur artıyor VE MACD(40,60) çizgisi pozitif ve artıyor. Stop: son stop_n (5) mumun dibi - tampon
    x ATR; hedef: giriş + hedef_r (3) x risk. Seans sonunda zorunlu çıkış. ATLANAN: evren filtresi (fiyat 2-13 USD, önceki gün
    dolar hacmi > 500 bin, gün içi %3.5): tek grafik/enstrüman seçimi dışarıda; mutlak 30.000 hacim eşiği birim bağımlı ->
    hacim_k oranına çevrildi; portföy %0.1 risk boyutlandırması motorun işi."""
    ad = "dis__alpaca-momentum"
    stil = "daytrade"
    varsayilan_parametreler = {"min_yuk": 0.04, "ilk_dk": 15.0, "son_dk": 60.0, "hacim_k": 1.0, "stop_n": 5, "tampon_atr": 0.1,
                               "hedef_r": 3.0, "seans": "abd_hisse", "atr_periyot": 14}
    parametre_izgarasi = {"min_yuk": [0.02, 0.04, 0.06], "son_dk": [45.0, 60.0, 90.0], "hedef_r": [2.0, 3.0, 4.0]}

    def sinyaller(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        bilgi = self._seans(m)
        c, sid, ici = bilgi["c"], bilgi["sid"], bilgi["ici"]
        onc = onceki_seans_hlc(m, sid, ici)["c"]
        dur_dk = c["dur_s"] / 60.0
        sira = pd.Series(ici.astype(int), index=m.index).groupby(sid).cumsum()
        dk = sira * dur_dk            # mum KAPANIŞINDA seans açılışından geçen dakika
        pencere = ici & (dk > p["ilk_dk"]).to_numpy() & (dk <= p["son_dk"]).to_numpy()
        ilk_tepe = y.where(ici & (dk <= p["ilk_dk"]).to_numpy()).groupby(sid).transform("max")
        hac = m["hacim"] > p["hacim_k"] * m["hacim"].rolling(20, min_periods=20).mean()
        h = g.macd(k, 12, 26, 9)["histogram"]
        m2 = g.macd(k, 40, 60, 9)["macd"]
        giris = pd.Series(pencere, index=m.index) & (k / onc - 1.0 > p["min_yuk"]) & (k > ilk_tepe) & hac \
            & (h > 0) & (h > h.shift(1)) & (h.shift(1) > h.shift(2)) & (m2 > 0) & (m2 > m2.shift(1))
        a = g.atr(y, d, k, int(p["atr_periyot"]))
        stop_l = d.rolling(int(p["stop_n"]), min_periods=int(p["stop_n"])).min() - p["tampon_atr"] * a
        out = gun_ici_cerceve(m, p["seans"], c, giris, _bos(m.index), stop_l, k + a)
        return r_hedefi(out, k, float(p["hedef_r"]))
