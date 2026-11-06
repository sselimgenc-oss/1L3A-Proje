"""D2 / freqtrade örnek stratejileri: ADXMomentum, BinHV27, BinHV45, EMASkipPump, FSampleStrategy.

`dis__ft-adx-momentum`, `dis__ft-binhv27`, `dis__ft-binhv45`, `dis__ft-ema-skip-pump`, `dis__ft-fsample`.
freqtrade `minimal_roi` ("0": x) sabit kâr hedefi (giriş kapanışı * (1+x)) olarak, `stoploss` sabit yüzde stop olarak çevrilir.
TA-Lib yerine `gostergeler.py` (Wilder) kullanıldığından DI/ADX değerleri birkaç ondalık oynayabilir. Tüm-veri normalizasyonu
yoktur (bu beş stratejide zaten yok).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis import _gosterge_d2 as gd
from motor.strateji.daytrade._ortak import cerceve, gun_sonu_uygula
from motor.strateji.temel import Strateji


def _yuzde_cerceve(mumlar, long_c, short_c, stop_yuzde, hedef_yuzde):
    k = mumlar["kapanis"]
    s, h = stop_yuzde / 100.0, hedef_yuzde / 100.0
    return cerceve(mumlar, long_c, short_c, k * (1 - s), k * (1 + s), k * (1 + h), k * (1 - h))


def _ters(mumlar: pd.DataFrame) -> pd.DataFrame:
    """Ayna veri: fiyat tersi (1/fiyat). yüksek <-> düşük yer değiştirir. Aynı kuralı bunun üstünde uygulamak
    orijinal kuralın short karşılığını verir (oran/yüzde tabanlı kurallar için ölçekten bağımsız)."""
    t = mumlar.copy()
    t["acilis"], t["kapanis"] = 1.0 / mumlar["acilis"], 1.0 / mumlar["kapanis"]
    t["yuksek"], t["dusuk"] = 1.0 / mumlar["dusuk"], 1.0 / mumlar["yuksek"]
    return t


class FtAdxMomentum(Strateji):
    """ADXMomentum (freqtrade, 1h daytrade, orijinal yalnız long).

    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/ADXMomentum.py (Gert Wohlgemuth; Mynt'ten).
    Kural: ADX(14) > 25, momentum(14) = kapanış - kapanış[14] > 0, +DI(25) > 25 ve +DI > -DI iken long. Çıkış sinyali:
    ADX > 25, momentum < 0, -DI(25) > 25 ve +DI < -DI. minimal_roi {"0": %1} -> sabit +%1 hedef; stoploss -%25 (stop_yuzde).
    short=True ayna (çıkış sinyali koşulları short girişidir; çıkışı long koşulları). Uyarlama: UTC gün sonu zorunlu çıkış
    (daytrade); %25 stop orijinal değerdir (ızgarada 5 ve 2 de var; geniş stop motorun risk boyutlandırmasında küçük pozisyon verir).
    Eski proje sonucu: PF IS 1.10 / OOS 1.09; Sharpe IS 0.77 / OOS 0.63; stres PF 1.00 -> kaldı (sonuc_freqtrade.csv).
    """
    ad = "dis__ft-adx-momentum"
    stil = "daytrade"
    varsayilan_parametreler = {"adx_n": 14, "di_n": 25, "mom_n": 14, "adx_esik": 25.0, "di_esik": 25.0,
                               "stop_yuzde": 25.0, "hedef_yuzde": 1.0, "short": False}
    parametre_izgarasi = {"adx_esik": [20.0, 25.0, 30.0], "stop_yuzde": [2.0, 5.0, 25.0], "hedef_yuzde": [1.0, 2.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        adx = g.adx(y, d, k, p["adx_n"])["adx"]
        di = g.adx(y, d, k, p["di_n"])
        mom = k - k.shift(p["mom_n"])
        long_c = (adx > p["adx_esik"]) & (mom > 0) & (di["arti_di"] > p["di_esik"]) & (di["arti_di"] > di["eksi_di"])
        short_c = (adx > p["adx_esik"]) & (mom < 0) & (di["eksi_di"] > p["di_esik"]) & (di["arti_di"] < di["eksi_di"])
        sig = _yuzde_cerceve(mumlar, long_c, short_c & bool(p["short"]), p["stop_yuzde"], p["hedef_yuzde"])
        return gun_sonu_uygula(gd.yonlu_cerceve(sig, short_c, long_c))


class FtBinHV27(Strateji):
    """BinHV27 (freqtrade, 5m -> 15m scalp, orijinal yalnız long).

    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/BinHV27.py (BinH, Slack).
    Kural: EMA60/EMA120 altında (kapanış < ikisi), -DI(14) kendi EMA25'inin üstünde ve RSI(5) yükselirken; dört trend/ADX/RSI
    kombinasyonundan biri: (trend dönmüyor, yükseliş sürmüyor, ADX>25, büyük düşüş, EMA5(RSI)<=20) | (dönmüyor, yükseliş sürüyor,
    ADX>30, büyük düşüş, emaRSI<=20) | (yükseliş sürmüyor, ADX>35, büyük yükseliş, emaRSI<=20) | (sürüyor, ADX>30, büyük yükseliş,
    emaRSI<=25). "büyük yükseliş" = SMA120 > SMA240 ve aradaki fark > fiyat/300. Çıkış: beş koşuldan biri (EMA/SMA üstüne dönüş,
    emaRSI >= 75/80 vb.; ayrıntı kodda). stoploss -%50 (orijinal); minimal_roi %100 (fiilen yok).
    Uyarlama: 5m yerine 15m (scalp min 15m), MA periyotları mum sayısı olarak AYNEN korundu (15m'de 3 kat uzun zaman). short=True
    ayna: aynı kural 1/fiyat serisi üzerinde (bkz. `_ters`). Orijinaldeki numpy.nan_to_num yerine ısınma (SMA240) maskelenir.
    Eski proje sonucu: PF IS 0.93 / OOS 0.80; Sharpe IS -0.50 / OOS -1.54 -> kaldı (sonuc_freqtrade_dakika.csv, 5m).
    """
    ad = "dis__ft-binhv27"
    stil = "scalp"
    varsayilan_parametreler = {"rsi_n": 5, "ema_rsi_n": 5, "ema_alt": 60, "ema_ust": 120, "sma_hizli": 120,
                               "sma_yavas": 240, "adx_1": 25.0, "adx_2": 30.0, "adx_3": 35.0, "rsi_giris": 20.0,
                               "stop_yuzde": 50.0, "short": False}
    parametre_izgarasi = {"rsi_giris": [15.0, 20.0, 25.0], "stop_yuzde": [3.0, 10.0, 50.0], "adx_1": [20.0, 25.0, 30.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def _kural(self, m: pd.DataFrame):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        rsi = g.rsi(k, p["rsi_n"])
        emarsi = g.ema(rsi, p["ema_rsi_n"])
        di = g.adx(y, d, k, 14)
        adx, minusdi, plusdi = di["adx"], di["eksi_di"], di["arti_di"]
        minusdiema = g.ema(minusdi, 25)
        lowsma, highsma = g.ema(k, p["ema_alt"]), g.ema(k, p["ema_ust"])
        fast, slow = g.sma(k, p["sma_hizli"]), g.sma(k, p["sma_yavas"])
        bigup = (fast > slow) & ((fast - slow) > k / 300.0)
        bigdown = ~bigup
        trend = fast - slow
        prep = trend > trend.shift(1)
        prepc = prep & (trend.shift(1) > trend.shift(2))
        cu = (slow > slow.shift(1)) & (slow.shift(1) > slow.shift(2))
        delta = fast - fast.shift(1)
        slowing = delta < delta.shift(1)
        hazir = slow.notna() & lowsma.notna() & highsma.notna() & emarsi.notna() & adx.notna() & minusdiema.notna()
        taban = hazir & (k < highsma) & (k < lowsma) & (minusdi > minusdiema) & (rsi >= rsi.shift(1))
        giris = taban & (
            (~prep & ~cu & (adx > p["adx_1"]) & bigdown & (emarsi <= p["rsi_giris"]))
            | (~prep & cu & (adx > p["adx_2"]) & bigdown & (emarsi <= p["rsi_giris"]))
            | (~cu & (adx > p["adx_3"]) & bigup & (emarsi <= p["rsi_giris"]))
            | (cu & (adx > p["adx_2"]) & bigup & (emarsi <= p["rsi_giris"] + 5.0)))
        cikis = hazir & (
            (~prepc & ~cu & ((k > lowsma) | (k > highsma)) & bigdown)
            | (~prepc & ~cu & (k > highsma) & ((emarsi >= 75) | (k > slow)) & bigdown)
            | (~prepc & (k > highsma) & (adx > 30) & (emarsi >= 80) & bigup)
            | (prepc & ~cu & slowing & (emarsi >= 75))
            | (prepc & (minusdi < plusdi) & (k > lowsma)))
        return giris, cikis

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        long_c, cik_l = self._kural(mumlar)
        if p["short"]:
            short_c, cik_s = self._kural(_ters(mumlar))
        else:
            short_c = cik_s = pd.Series(False, index=mumlar.index)
        sig = _yuzde_cerceve(mumlar, long_c, short_c, p["stop_yuzde"], 0.0)
        sig["hedef"] = np.nan                       # minimal_roi %100 -> hedef yok
        return gd.yonlu_cerceve(sig, cik_l, cik_s)


class FtBinHV45(Strateji):
    """BinHV45 (freqtrade, 1m -> 15m scalp, orijinal yalnız long).

    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/BinHV45.py.
    Kural: Bollinger(40, 2 sapma, ddof=1) alt bandı. Önceki alt band > 0 ve: (orta - alt) > kapanış*bbdelta/1000,
    |kapanış - önceki kapanış| > kapanış*closedelta/1000, kuyruk (kapanış - düşük) < (orta - alt)*tail/1000, kapanış < önceki alt
    band ve kapanış <= önceki kapanış ise long (buy_params: 7, 17, 25 — IntParameter varsayılanları (30) değil, dosyadaki
    buy_params). Çıkış sinyali yok; minimal_roi %1.25 sabit hedef, stoploss -%5.
    Uyarlama: 1m yerine 15m (scalp min 15m); eşikler oran olduğu için aynen korundu ama 15m'de çok daha seyrek tetiklenir.
    short=True ayna: aynı kural 1/fiyat serisinde (`_ters`). Eski proje sonucu: sonuç yok (sonuc_freqtrade_dakika.csv).
    """
    ad = "dis__ft-binhv45"
    stil = "scalp"
    varsayilan_parametreler = {"bb_n": 40, "bb_sapma": 2.0, "bbdelta": 7, "closedelta": 17, "tail": 25,
                               "stop_yuzde": 5.0, "hedef_yuzde": 1.25, "short": False}
    parametre_izgarasi = {"bbdelta": [4, 7, 15], "closedelta": [10, 17, 30], "hedef_yuzde": [1.25, 2.5]}

    def cikis_var_mi(self) -> bool:
        return True   # sabit %1.25 hedef

    def _kural(self, m: pd.DataFrame) -> pd.Series:
        p = self.parametreler
        k, d = m["kapanis"], m["dusuk"]
        orta = k.rolling(p["bb_n"], min_periods=p["bb_n"]).mean()
        sd = k.rolling(p["bb_n"], min_periods=p["bb_n"]).std()
        alt = orta - p["bb_sapma"] * sd
        bbdelta = (orta - alt).abs()
        closedelta = (k - k.shift(1)).abs()
        kuyruk = (k - d).abs()
        return ((alt.shift(1) > 0) & (bbdelta > k * p["bbdelta"] / 1000.0) & (closedelta > k * p["closedelta"] / 1000.0)
                & (kuyruk < bbdelta * p["tail"] / 1000.0) & (k < alt.shift(1)) & (k <= k.shift(1)))

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        long_c = self._kural(mumlar)
        short_c = self._kural(_ters(mumlar)) if p["short"] else pd.Series(False, index=mumlar.index)
        return _yuzde_cerceve(mumlar, long_c, short_c, p["stop_yuzde"], p["hedef_yuzde"])


class FtEmaSkipPump(Strateji):
    """EMASkipPump (freqtrade, 5m -> 15m scalp, orijinal yalnız long).

    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/EMASkipPump.py (TradingView Slack).
    Kural: "pump ve dump'tan kaçınma": hacim < 20 * (önceki 30 mumun ortalama hacmi) VE kapanış < EMA5 ve EMA12 VE kapanış =
    son 12 kapanışın en düşüğü VE kapanış <= Bollinger(20, 2, tipik fiyat) alt bandı ise long. Çıkış sinyali: kapanış EMA5 ve
    EMA12 üstünde, son 12 kapanışın en yükseği ve >= üst band. minimal_roi %10 hedef; stoploss -%5.
    Uyarlama: 15m (scalp min 15m). short=True ayna (aşırı alım: kapanış EMA5/EMA12 üstünde, 12'lik tepe, >= üst band; çıkış:
    long girişinin tersi koşullar). Orijinal EMA21 hesaplanıyor ama kullanılmıyor.
    Eski proje sonucu: sonuç yok (sonuc_freqtrade_dakika.csv).
    """
    ad = "dis__ft-ema-skip-pump"
    stil = "scalp"
    varsayilan_parametreler = {"ema_kisa": 5, "ema_orta": 12, "bb_n": 20, "bb_sapma": 2.0, "hacim_n": 30,
                               "hacim_k": 20.0, "stop_yuzde": 5.0, "hedef_yuzde": 10.0, "short": False}
    parametre_izgarasi = {"hedef_yuzde": [2.5, 5.0, 10.0], "stop_yuzde": [2.5, 5.0], "ema_orta": [12, 21]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k, h = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], mumlar["hacim"]
        e1, e2 = g.ema(k, p["ema_kisa"]), g.ema(k, p["ema_orta"])
        tp = (y + d + k) / 3.0
        orta = tp.rolling(p["bb_n"], min_periods=p["bb_n"]).mean()
        sd = tp.rolling(p["bb_n"], min_periods=p["bb_n"]).std()
        alt, ust = orta - p["bb_sapma"] * sd, orta + p["bb_sapma"] * sd
        mn = k.rolling(p["ema_orta"], min_periods=p["ema_orta"]).min()
        mx = k.rolling(p["ema_orta"], min_periods=p["ema_orta"]).max()
        normal_hacim = h < h.rolling(p["hacim_n"], min_periods=p["hacim_n"]).mean().shift(1) * p["hacim_k"]
        long_c = normal_hacim & (k < e1) & (k < e2) & (k == mn) & (k <= alt)
        asiri_alim = (k > e1) & (k > e2) & (k >= mx) & (k >= ust)
        short_c = normal_hacim & (k > e1) & (k > e2) & (k == mx) & (k >= ust) & bool(p["short"])
        sig = _yuzde_cerceve(mumlar, long_c, short_c, p["stop_yuzde"], p["hedef_yuzde"])
        return gd.yonlu_cerceve(sig, asiri_alim, (k < e1) & (k < e2) & (k <= mn) & (k <= alt))


class FtFSample(Strateji):
    """FSampleStrategy (freqtrade, 1h daytrade, long+short).

    Kaynak: arsiv/algo-sg/dis_kaynak/ft/strategies/FSampleStrategy.py.
    Kural: long: RSI(14) 30'u yukarı keser, TEMA(9) <= Bollinger(20, 2, tipik fiyat) orta bandı ve TEMA yükseliyor. Short: RSI
    70'i yukarı keser, TEMA > orta bant ve TEMA düşüyor. Long çıkışı = short girişi koşulu (RSI 70 yukarı kesişi, TEMA orta
    bandın üstünde ve düşüyor); short çıkışı = long girişi koşulu. stoploss -%5 (stop_yuzde); minimal_roi {"0": 1} (fiilen yok).
    Uyarlama: UTC gün sonu zorunlu çıkış (daytrade). Kullanılmayan göstergeler (MACD, MFI, HT_SINE, SAR vb.) alınmadı.
    Eski proje sonucu: PF IS 1.60 / OOS 1.14; Sharpe IS 1.67 / OOS 0.38; stres PF 1.17 -> kaldı (sonuc_freqtrade.csv).
    """
    ad = "dis__ft-fsample"
    stil = "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_alt": 30.0, "rsi_ust": 70.0, "tema_n": 9, "bb_n": 20, "bb_sapma": 2.0,
                               "stop_yuzde": 5.0, "short": True}
    parametre_izgarasi = {"rsi_alt": [25.0, 30.0, 35.0], "rsi_ust": [65.0, 70.0, 75.0], "stop_yuzde": [3.0, 5.0, 8.0]}

    def cikis_var_mi(self) -> bool:
        return True   # ters koşul çıkışı + gün sonu

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        r = g.rsi(k, p["rsi_n"])
        tm = gd.tema(k, p["tema_n"])
        tp = (y + d + k) / 3.0
        orta = g.sma(tp, p["bb_n"])
        yukari, asagi = tm > tm.shift(1), tm < tm.shift(1)
        long_c = gd.kesis_yukari(r, p["rsi_alt"]) & (tm <= orta) & yukari
        short_c = gd.kesis_yukari(r, p["rsi_ust"]) & (tm > orta) & asagi
        sig = _yuzde_cerceve(mumlar, long_c, short_c & bool(p["short"]), p["stop_yuzde"], 0.0)
        sig["hedef"] = np.nan
        return gun_sonu_uygula(gd.yonlu_cerceve(sig, short_c, long_c))
