"""Kapanış turu, kodlama partisi g9_kod_2 (girdi: sonuclar/kapanis/kod_girdi/g9_kod_2.csv, 30 kaynak satırı; Robotic HAM:B001).

Her sınıf kaynak Freqtrade dosyasından (kural_tam özetinden değil) okunan kuralın kendi cümlelerimizle yazılmış uyarlamasıdır; üçüncü taraf
kodu kopyalanmadı. Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor). Hepsi nedensel; üst zaman dilimi yalnız `htf.ust_zaman` ile
KAPANMIŞ mumdan alınır.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa (ya da <= -%50 ise) stop = kapanış -/+ 3 x ATR(14) (ön kayıt). Kaynak yüzde stopu sinyal kapanışından hesaplanır.
- Freqtrade `minimal_roi` (dakika anahtarlı) `CikisAyarlari.azalan_roi` ile: mum sayısı = yukarı yuvarlanmış dakika / TF dakikası, aynı muma
  düşen basamaklarda büyük dakikalı olan geçerli; kapanışta sınanır, çıkış sonraki açılışta (kaynakta mum içi).
- `trailing_stop_positive` (+offset) -> `geri_cekilme_yuzde` + `geri_cekilme_min_kar_yuzde` (offset); kapanış bazlı. `trailing_only_offset_is_reached`
  tanımsız/False ise (yalnız 146) lider kuralı: min kâr 0.
- `custom_stoploss` (Freqtrade: yalnız yukarı taşınan, GÜNCEL FİYATA göre uzaklık) -> `pozisyon_cikisi` kancası: her kapanışta giriş mumundan
  beri hesaplanan stop'un en büyüğü (kapanış bazlı) ihlal edildi mi. `custom_exit` -> aynı kanca. `exit_profit_only` -> `yalniz_karda_cikis`.
- `confirm_trade_exit` içindeki yalnız-mum-koşullu 'sell_signal' süzgeçleri (kaynak dosyada varsa) çıkış sinyalinden düşülür; slippage
  koruması/canlı emir mantığı yok sayıldı. Kaldıraç (leverage) yok sayıldı (motor 1x), kaynak stop yüzdeleri aynen korundu.
- İki yönlü kurallarda aynı mumda hem long hem short koşulu doğruysa Freqtrade gibi sinyal verilmez.
- qtpylib Bollinger std'si örneklem (ddof=1), TA-Lib BBANDS ve repo `gostergeler.bollinger` ddof=0'dır; kaynağa göre seçildi.

KODLANAMADI satırları dosya sonundaki listededir (neden satır başına yazılı).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b2
from motor.strateji._gosterge_d11j import hma as _hma
from motor.strateji._gosterge_d11j import mama_fama as _mama_fama
from motor.strateji._gosterge_d11j import obv as _obv
from motor.strateji._gosterge_d11j import wma as _wma
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d5 import kama as _kama
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, _stochf, _stoch_yavas, roi_tablosu
from motor.strateji.temel import Strateji

yukari = b2.yukari_kesis
asagi = b2.asagi_kesis


# ---------------------------------------------------------------- yardımcılar
def _roi(tablo: dict, tf_dk: float) -> tuple:
    return roi_tablosu(tablo, tf_dk)


def _bitir(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _b(x, idx) -> pd.Series:
    return x.fillna(False).astype(bool) if isinstance(x, pd.Series) else pd.Series(bool(x), index=idx)


def _atr_mes(m: pd.DataFrame, n: int = 14, k: float = 3.0) -> pd.Series:
    return k * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], n)


def _cift(m: pd.DataFrame, al, sat, stop_l, stop_s) -> pd.DataFrame:
    """Long/short çerçevesi; aynı mumda ikisi de doğruysa ikisi de düşer (Freqtrade çatışma kuralı)."""
    a, s = _b(al, m.index), _b(sat, m.index)
    cak = a & s
    return cerceve(m, a & ~cak, s & ~cak, stop_l, stop_s)


def _tipik(m: pd.DataFrame) -> pd.Series:
    return (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0


def _bb(seri: pd.Series, n: int, k: float, ddof: int) -> pd.DataFrame:
    orta = seri.rolling(n, min_periods=n).mean()
    std = seri.rolling(n, min_periods=n).std(ddof=ddof)
    return pd.DataFrame({"orta": orta, "ust": orta + k * std, "alt": orta - k * std})


def _tema(seri: pd.Series, n: int) -> pd.Series:
    e1 = g.ema(seri, n)
    e2 = g.ema(e1, n)
    e3 = g.ema(e2, n)
    return 3.0 * e1 - 3.0 * e2 + e3


def _linreg(seri: pd.Series, n: int):
    """En küçük kareler doğrusu: (uç nokta [TA-Lib LINEARREG], eğim [LINEARREG_SLOPE]); TSF = uç + eğim. Nedensel."""
    a = seri.to_numpy(dtype=float)
    uc = np.full(len(a), np.nan)
    eg = np.full(len(a), np.nan)
    if len(a) >= n:
        x = np.arange(n, dtype=float)
        xm = x.mean()
        sxx = float(np.sum((x - xm) ** 2))
        w_eg = (x - xm) / sxx
        w_uc = 1.0 / n + (x - xm) * ((n - 1) / 2.0) / sxx
        pen = sliding_window_view(a, n)
        uc[n - 1:] = pen @ w_uc
        eg[n - 1:] = pen @ w_eg
    return pd.Series(uc, index=seri.index), pd.Series(eg, index=seri.index)


def _cmo(kap: pd.Series, n: int) -> pd.Series:
    """Chande momentum (TA-Lib CMO, Wilder düzleştirme) = 2 x RSI - 100."""
    return 2.0 * g.rsi(kap, n) - 100.0


def _williams(m: pd.DataFrame, n: int) -> pd.Series:
    hh = m["yuksek"].rolling(n, min_periods=n).max()
    ll = m["dusuk"].rolling(n, min_periods=n).min()
    return -100.0 * (hh - m["kapanis"]) / (hh - ll).where(lambda x: x > 0)


def _cti(kap: pd.Series, n: int) -> pd.Series:
    """Ehlers korelasyon trend göstergesi (pandas_ta cti): pencere kapanışları ile 0..n-1 doğrusunun Pearson korelasyonu."""
    a = kap.to_numpy(dtype=float)
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        x = np.arange(n, dtype=float) - (n - 1) / 2.0
        pen = sliding_window_view(a, n)
        yc = pen - pen.mean(axis=1, keepdims=True)
        pay = yc @ x
        payda = np.sqrt(np.sum(yc * yc, axis=1)) * np.sqrt(np.sum(x * x))
        with np.errstate(divide="ignore", invalid="ignore"):
            out[n - 1:] = np.where(payda > 0, pay / payda, np.nan)
    return pd.Series(out, index=kap.index)


def _di(m: pd.DataFrame, n: int) -> pd.DataFrame:
    """TA-Lib tarzı ADX/DI/DX (Wilder): sütunlar adx, pdi, mdi, dx."""
    d = g.adx(m["yuksek"], m["dusuk"], m["kapanis"], n)
    dx = 100.0 * (d["arti_di"] - d["eksi_di"]).abs() / (d["arti_di"] + d["eksi_di"])
    return pd.DataFrame({"adx": d["adx"], "pdi": d["arti_di"], "mdi": d["eksi_di"], "dx": dx})


def _ewo(m: pd.DataFrame, hizli: int, yavas: int, payda: str) -> pd.Series:
    kap = m["kapanis"]
    return (g.ema(kap, hizli) - g.ema(kap, yavas)) / m["dusuk" if payda == "low" else "kapanis"] * 100.0


def _ha(m: pd.DataFrame) -> pd.DataFrame:
    return b2.heikin_ashi(m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"])


def _iz_ihlali(kv: np.ndarray, b: int, i: int, giris: float, mesafe) -> bool:
    """Kapanış bazlı, yalnız yukarı taşınan stop: b..i arasında her kapanıştan `kapanış x (1 - mesafe(kâr, sıra))` stopları hesaplanır,
    en büyüğü (Freqtrade custom_stoploss'un güncel fiyata göre uzaklığı) kapanış tarafından ihlal edildi mi."""
    b = max(int(b), 0)
    c = kv[b:i + 1]
    if len(c) == 0 or not giris > 0:
        return False
    d = mesafe(c / giris - 1.0, np.arange(len(c)))
    s = c * (1.0 - d)
    s = s[np.isfinite(s)]
    return bool(len(s)) and bool(kv[i] <= s.max())


class _Taban(KancaDestek, Strateji):
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def _kapanis_dizisi(self, m: pd.DataFrame, **ek) -> None:
        self._sakla(kap=m["kapanis"], **ek)


# ================================================================ Elliott/NASOS ailesi
def _onay_a(hma50: pd.Series, ema100: pd.Series, kap: pd.Series) -> pd.Series:
    """confirm_trade_exit (NASOS dosyaları): hma50 x 1,149 > ema100 VE kapanış < ema100 x 0,951 ise sell_signal verilmez."""
    return (hma50 * 1.149 > ema100) & (kap < ema100 * 0.951)


class _ElliotTaban(_Taban):
    """ElliotV7 / Elliotv8 çekirdeği: EMA(al) x low_offset altında + EWO(50,200; /kapanış) iki kollu RSI4 dip girişi, EMA(sat) x ofset üstü
    çıkış. `trend_1h`: giriş için 1h EMA20 > EMA25 (yalnız V7). `cikis_ref`: çıkışta SMA9 (V7) ya da kapanış (V8) ile HMA50 karşılaştırması."""

    parametre_izgarasi = {}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ma_al, ma_sat = g.ema(kap, int(p["ma_al_n"])), g.ema(kap, int(p["ma_sat_n"]))
        ewo = _ewo(mumlar, 50, 200, "kapanis")
        rsi, rsi_h, rsi_y = g.rsi(kap, 14), g.rsi(kap, 4), g.rsi(kap, 20)
        hma50 = _hma(kap, 50)
        ref = g.sma(kap, 9) if p["cikis_ref"] == "sma9" else kap
        hacim = mumlar["hacim"] > 0
        taban = ((rsi_h < 35) & (kap < ma_al * float(p["low_offset"])) & hacim
                 & (kap < ma_sat * float(p["high_offset"])))
        if p["trend_1h"]:
            yt = ust_zaman(mumlar, "1h", lambda u: (g.ema(u["kapanis"], 20) > g.ema(u["kapanis"], 25)).astype(float)) > 0
            taban = taban & yt
        al = taban & (((ewo > float(p["ewo_yuksek"])) & (rsi < float(p["rsi_al"]))) | (ewo < float(p["ewo_dusuk"])))
        cik = (((ref > hma50) & (kap > ma_sat * float(p["high_offset_2"])) & (rsi > 50) & hacim & (rsi_h > rsi_y))
               | ((ref < hma50) & (kap > ma_sat * float(p["high_offset"])) & hacim & (rsi_h > rsi_y)))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ B001:564
class ElliotV7B0564(_ElliotTaban):
    """HAM:B001:564 (ElliotV7.py, 5m long): 1h EMA20>EMA25 yükseliş VE RSI(4)<35 VE kapanış < EMA(14) x 0,975 VE kapanış < EMA(24) x 0,991 VE
    hacim>0 VE ((EWO>2,327 VE RSI(14)<69) VEYA EWO<-19,988); EWO = (EMA50-EMA200)/kapanış x 100. Çıkış sinyali: (SMA9>HMA50 VE kapanış>EMA(24)x0,997
    VE RSI14>50 VE RSI4>RSI20) VEYA (SMA9<HMA50 VE kapanış>EMA(24)x0,991 VE RSI4>RSI20). ROI {0:5,1; 10dk:3,1; 22:1,8; 66:0}; stop -%32; iz süren
    %0,5 (offset %3, yalnız offset sonrası). Uyarlama: kural_tam'daki 'custom_stoploss kâr<-%10 ve >720 dk -%1' kaynakta use_custom_stoploss=False
    olduğu için ETKİSİZDİR ve kodlanmadı."""

    ad, stil = "kapanis__ewo-ofset-v7-b0564", "daytrade"
    varsayilan_parametreler = {"ma_al_n": 14, "ma_sat_n": 24, "low_offset": 0.975, "high_offset": 0.991, "high_offset_2": 0.997,
                               "ewo_yuksek": 2.327, "ewo_dusuk": -19.988, "rsi_al": 69, "trend_1h": True, "cikis_ref": "sma9",
                               "sl": 0.32}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.051, 10: 0.031, 22: 0.018, 66: 0.0}, 5),
                                   geri_cekilme_yuzde=0.5, geri_cekilme_min_kar_yuzde=3.0)


# ================================================================ B001:570
class ElliotV8B0570(_ElliotTaban):
    """HAM:B001:570 (Elliotv8.py, 5m long): 564 ile aynı iki kollu giriş AMA 1h trend süzgeci YOK; çıkışta SMA9 yerine kapanış: (kapanış>HMA50 VE
    kapanış>EMA(24)x0,997 VE RSI14>50 VE RSI4>RSI20) VEYA (kapanış<HMA50 VE kapanış>EMA(24)x0,991 VE RSI4>RSI20). ROI {0:21,5; 40dk:3,2; 87:1,6;
    201:0}; stop -%32; iz süren %0,1 (offset %2, yalnız offset sonrası). Kaynakta custom_stoploss yok."""

    ad, stil = "kapanis__ewo-ofset-v8-b0570", "daytrade"
    varsayilan_parametreler = {"ma_al_n": 14, "ma_sat_n": 24, "low_offset": 0.975, "high_offset": 0.991, "high_offset_2": 0.997,
                               "ewo_yuksek": 2.327, "ewo_dusuk": -19.988, "rsi_al": 69, "trend_1h": False, "cikis_ref": "kapanis",
                               "sl": 0.32}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.215, 40: 0.032, 87: 0.016, 201: 0.0}, 5),
                                   geri_cekilme_yuzde=0.1, geri_cekilme_min_kar_yuzde=2.0)


# ---------------------------------------------------------------- NASOS v5 çekirdeği (573, 574, 670)
class _Nasos5Taban(_Taban):
    """NASOS v5 çekirdeği, üç giriş kolu (ewo1/ewo2/ewolow): RSI(hızlı) < eşik VE kapanış < EMA(al) x ofset VE EWO (50,200; /DÜŞÜK) koşulu VE
    kapanış < EMA(sat) x high_offset. ewo2 ayrıca RSI(ana)<25. Çıkış: (kapanış>SMA9 VE kapanış>EMA(sat)xhigh_offset_2 VE RSI(ana)>50 VE RSI hızlı>yavaş)
    VEYA (kapanış<HMA50 VE kapanış>EMA(sat)xhigh_offset VE RSI hızlı>yavaş); confirm_trade_exit: hma50x1,149>ema100 VE kapanış<ema100x0,951 ise
    sinyal çıkışı verilmez. `geri_bakis`>0: giriş engeli (15m kapanışın son N 5m-satırlık max'ı < kapanış x profit_threshold ise giriş iptal)."""

    parametre_izgarasi = {}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ma_al, ma_sat = g.ema(kap, int(p["ma_al_n"])), g.ema(kap, int(p["ma_sat_n"]))
        ewo = _ewo(mumlar, 50, 200, "low")
        rsi = g.rsi(kap, int(p["rsi_n"]))
        rsi_h, rsi_y = g.rsi(kap, int(p["rsi_hizli_n"])), g.rsi(kap, int(p["rsi_yavas_n"]))
        hma50, ema100, sma9 = _hma(kap, 50), g.ema(kap, 100), g.sma(kap, 9)
        hacim = mumlar["hacim"] > 0
        sat_ust = kap < ma_sat * float(p["high_offset"])
        hizli = rsi_h < float(p["rsi_hizli_al"])
        ewo1 = (hizli & (kap < ma_al * float(p["low_offset"])) & (ewo > float(p["ewo_yuksek"]))
                & (rsi < float(p["rsi_al"])) & hacim & sat_ust)
        ewo2 = (hizli & (kap < ma_al * float(p["low_offset_2"])) & (ewo > float(p["ewo_yuksek_2"]))
                & (rsi < float(p["rsi_al"])) & hacim & sat_ust & (rsi < 25))
        ewol = hizli & (kap < ma_al * float(p["low_offset"])) & (ewo < float(p["ewo_dusuk"])) & hacim & sat_ust
        al = ewo1 | ewo2 | ewol
        if int(p["geri_bakis"]) > 0:
            k15 = ust_zaman(mumlar, "15m", lambda u: u["kapanis"])
            engel = k15.rolling(int(p["geri_bakis"])).max() < kap * float(p["profit_threshold"])
            al = al & ~engel.fillna(False)
        cik = (((kap > sma9) & (kap > ma_sat * float(p["high_offset_2"])) & (rsi > 50) & hacim & (rsi_h > rsi_y))
               | ((kap < hma50) & (kap > ma_sat * float(p["high_offset"])) & hacim & (rsi_h > rsi_y)))
        cik = cik & ~_onay_a(hma50, ema100, kap)
        self._kapanis_dizisi(mumlar)
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


def _nasos5_mesafe(kar: np.ndarray, sira: np.ndarray) -> np.ndarray:
    """NASOSv5 custom_stoploss: kâr kademesine göre güncel fiyatın altında sabit uzaklık (>%30: %5, >10: 3, >6: 2, >4: 1, >2,5: 0,5, >1,8: 0,5,
    aksi %15)."""
    return np.select([kar > 0.3, kar > 0.1, kar > 0.06, kar > 0.04, kar > 0.025, kar > 0.018],
                     [0.05, 0.03, 0.02, 0.01, 0.005, 0.005], default=0.15)


# ================================================================ B001:573
class NasosV5B0573(_Nasos5Taban):
    """HAM:B001:573 (NASOSv5.py, 5m long): NASOS v5 çekirdeği; EMA(8) x 0,981/0,942, EMA(16) x 1,097, RSI4<37, RSI14<78, EWO>3,553 / >-5,585 / <-14,378;
    giriş engeli 15m kapanışın son 32 satırlık max'ı < kapanış x 1,037. Çıkış çarpanları 1,472/1,097. ROI {360dk: 0}; stop -%15; trailing kapalı;
    custom_stoploss kâr kademeli (kancada: `_nasos5_mesafe`, kapanış bazlı). Uyarlama: confirm_trade_exit slippage koruması yok sayıldı."""

    ad, stil = "kapanis__nasos-v5-b0573", "daytrade"
    varsayilan_parametreler = {"ma_al_n": 8, "ma_sat_n": 16, "low_offset": 0.981, "low_offset_2": 0.942, "high_offset": 1.097,
                               "high_offset_2": 1.472, "ewo_yuksek": 3.553, "ewo_yuksek_2": -5.585, "ewo_dusuk": -14.378,
                               "rsi_n": 14, "rsi_hizli_n": 4, "rsi_yavas_n": 20, "rsi_al": 78, "rsi_hizli_al": 37,
                               "geri_bakis": 32, "profit_threshold": 1.037, "sl": 0.15}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({360: 0.0}, 5))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        return _iz_ihlali(self._kd["kap"], d.giris_mum_indeksi, d.mum_indeksi, d.giris_fiyati, _nasos5_mesafe)


# ================================================================ B001:574
class NasosV5Mod1B0574(_Nasos5Taban):
    """HAM:B001:574 (NASOSv5_mod1.py, 5m long): NASOS v5 çekirdeği; ÖNEMLİ: dosyada RSI periyotları 20 (ana) / 5 (hızlı) / 25 (yavaş) (kural_tam'daki
    14/4/20 değil); EMA(20) her iki yanda; çarpanlar 0,984/0,901/1,01/1,142; RSI5<27, RSI20<80; EWO>4,299 / >8,492 / <-8,476; giriş engeli 15m kapanışın
    son 7 satırlık max'ı < kapanış x 1,036. ROI {0: %40}; stop -%30; iz süren %0,1 (offset %3, yalnız offset sonrası). Kaynakta use_custom_stoploss=False
    (custom_stoploss sınıf içinde var ama etkisiz) ve TrailingBuy canlı emir mekanizması yok sayıldı."""

    ad, stil = "kapanis__nasos-v5-mod1-b0574", "daytrade"
    varsayilan_parametreler = {"ma_al_n": 20, "ma_sat_n": 20, "low_offset": 0.984, "low_offset_2": 0.901, "high_offset": 1.01,
                               "high_offset_2": 1.142, "ewo_yuksek": 4.299, "ewo_yuksek_2": 8.492, "ewo_dusuk": -8.476,
                               "rsi_n": 20, "rsi_hizli_n": 5, "rsi_yavas_n": 25, "rsi_al": 80, "rsi_hizli_al": 27,
                               "geri_bakis": 7, "profit_threshold": 1.036, "sl": 0.30}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.4}, 5), geri_cekilme_yuzde=0.1, geri_cekilme_min_kar_yuzde=3.0)


# ================================================================ B001:670
class NasosSmaOfsetB0670(_Nasos5Taban):
    """HAM:B001:670 (NotAnotherSMAOffsetStrategy.py, 5m long): NASOS çekirdeği, giriş engeli yok; EMA(14) x 0,975/0,955, EMA(24) x 0,991; RSI4<35,
    RSI14<69, EWO(/düşük)>2,327 / >-2,327 / <-20,988; çıkış çarpanları 0,997/0,991. ROI {0:21,5; 40dk:3,2; 87:1,6; 201:0}; stop -%35; iz süren %0,5 (offset %3,
    yalnız offset sonrası); confirm_trade_exit süzgeci (hma50x1,149>ema100 VE kapanış<ema100x0,951 ise sinyal çıkışı yok) uygulandı."""

    ad, stil = "kapanis__nasos-sma-ofset-b0670", "daytrade"
    varsayilan_parametreler = {"ma_al_n": 14, "ma_sat_n": 24, "low_offset": 0.975, "low_offset_2": 0.955, "high_offset": 0.991,
                               "high_offset_2": 0.997, "ewo_yuksek": 2.327, "ewo_yuksek_2": -2.327, "ewo_dusuk": -20.988,
                               "rsi_n": 14, "rsi_hizli_n": 4, "rsi_yavas_n": 20, "rsi_al": 69, "rsi_hizli_al": 35,
                               "geri_bakis": 0, "profit_threshold": 1.0, "sl": 0.35}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.215, 40: 0.032, 87: 0.016, 201: 0.0}, 5),
                                   geri_cekilme_yuzde=0.5, geri_cekilme_min_kar_yuzde=3.0)


# ================================================================ B001:590
def _ralli_mesafe(kar: np.ndarray, sira: np.ndarray) -> np.ndarray:
    """RalliV1 custom_stoploss: kâr < %0,1 VE 140 dakikadan (28 x 5m) uzun tutulduysa güncel fiyatın %0,5 altı; aksi stop değişmez (1 = stop yok)."""
    return np.where((kar < 0.001) & (sira * 5 > 140), 0.005, 1.0)


class RalliV1B0590(_Taban):
    """HAM:B001:590 (RalliV1.py, 5m long): altı kollu giriş (hepsinde hacim>0, RSI4 4..35, kapanış<EMA(24)x0,991). EMA(14)<EMA100 VE SMA9<EMA(14)
    rejiminde: [kol1 kapanış<EMA14x0,975 VE EWO>2,327 VE RSI14<45], [kol2 x0,955 VE EWO>-2,327 VE RSI14<45 VE RSI14<25], [kol3 x0,975 VE EWO<-20,988];
    EMA(14)>EMA100 rejiminde: aynı üç kol ama RSI14<60 (kol4, kol5 RSI14<60 VE RSI14<25, kol6). EWO = (EMA50-EMA200)/DÜŞÜK x 100. Çıkış: (HMA50>EMA100 VE
    kapanış>SMA9 VE kapanış>EMA(24)x0,997 VE RSI4>RSI20) VEYA (kapanış<EMA100 VE kapanış>EMA(24)x0,991 VE RSI4>RSI20); confirm_trade_exit: RSI14<45 VE
    HMA50>EMA100 ise sinyal çıkışı yok. ROI {0:4; 40dk:3,2; 87:1,8; 201:0}; stop -%30; trailing kapalı; custom_stoploss (kancada): kâr<%0,1 ve 140 dk sonra
    güncel fiyatın %0,5 altı (kapanış bazlı). Kural_tam'daki 'ROI dosyada' değerleri dosyadan alındı; 'kol4+ dosyada' kolları dosyadan okundu."""

    ad, stil = "kapanis__ralli-v1-b0590", "daytrade"
    varsayilan_parametreler = {"ma_al_n": 14, "ma_sat_n": 24, "low_offset": 0.975, "low_offset_2": 0.955, "high_offset": 0.991,
                               "high_offset_2": 0.997, "ewo_yuksek": 2.327, "ewo_yuksek_2": -2.327, "ewo_dusuk": -20.988,
                               "rsi_al": 60, "rsi_al_2": 45, "sl": 0.30}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.04, 40: 0.032, 87: 0.018, 201: 0.0}, 5))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ma_al, ma_sat = g.ema(kap, int(p["ma_al_n"])), g.ema(kap, int(p["ma_sat_n"]))
        ewo = _ewo(mumlar, 50, 200, "low")
        rsi, rsi_h, rsi_y = g.rsi(kap, 14), g.rsi(kap, 4), g.rsi(kap, 20)
        hma50, ema100, sma9 = _hma(kap, 50), g.ema(kap, 100), g.sma(kap, 9)
        hacim = mumlar["hacim"] > 0
        ortak = (rsi_h < 35) & (rsi_h > 4) & hacim & (kap < ma_sat * float(p["high_offset"]))
        asagi_r = (ma_al < ema100) & (sma9 < ma_al)
        yukari_r = ma_al > ema100

        def kollar(rsi_esik):
            k1 = (kap < ma_al * float(p["low_offset"])) & (ewo > float(p["ewo_yuksek"])) & (rsi < rsi_esik)
            k2 = ((kap < ma_al * float(p["low_offset_2"])) & (ewo > float(p["ewo_yuksek_2"])) & (rsi < rsi_esik)
                  & (rsi < 25))
            k3 = (kap < ma_al * float(p["low_offset"])) & (ewo < float(p["ewo_dusuk"]))
            return k1 | k2 | k3

        al = ortak & ((asagi_r & kollar(float(p["rsi_al_2"]))) | (yukari_r & kollar(float(p["rsi_al"]))))
        cik = (((hma50 > ema100) & (kap > sma9) & (kap > ma_sat * float(p["high_offset_2"])) & hacim & (rsi_h > rsi_y))
               | ((kap < ema100) & (kap > ma_sat * float(p["high_offset"])) & hacim & (rsi_h > rsi_y)))
        cik = cik & ~((rsi < 45) & (hma50 > ema100))
        self._kapanis_dizisi(mumlar)
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        return _iz_ihlali(self._kd["kap"], d.giris_mum_indeksi, d.mum_indeksi, d.giris_fiyati, _ralli_mesafe)


# ================================================================ B001:828
class SupertrendEmaObvB0828(_Taban):
    """HAM:B001:828 (ForexRobootSuperScalper.py, 5m long): ham Supertrend (hl2 +/- 1,8 x ATR(10); bantlar iz sürmez, yön = kapanışın ÖNCEKİ mumun bantlarına göre
    kırılımı, başlangıç yönü yukarı; çizgi yön yukarıysa alt, aşağıysa üst band) VE kapanış > çizgi VE EMA5>EMA9>EMA21 VE ADX14>25 VE VOSC>0 (VOSC = OBV -
    EMA20(OBV)) -> long. Çıkış sinyali: kapanış < çizgi VE EMA5<EMA9<EMA21 VE ADX14>25 VE VOSC<0. custom_stoploss: güncel fiyatın 3 x ATR(10) altı
    (yalnız yukarı; kancada, kapanış bazlı); custom_exit: kapanış >= giriş + 1 x ATR(10) (kancada). Uyarlama: kaynakta `atr_period`=14 parametresi
    KULLANILMIYOR, ATR(10) esas (satırın 'ATR(14)x3 uyarlaması' notu yerine kaynağın kendi dinamik stopu); ilk stop kapanış - 3 x ATR(10)."""

    ad, stil = "kapanis__supertrend-ema-obv-b0828", "daytrade"
    varsayilan_parametreler = {"vol_n": 10, "carpan": 1.8, "ema_k": 5, "ema_o": 9, "ema_u": 21, "adx_n": 14, "adx_esik": 25.0,
                               "vosc_n": 20, "stop_k": 3.0, "tp_k": 1.0}
    parametre_izgarasi = {}

    @staticmethod
    def _supertrend_ham(m: pd.DataFrame, per: int, carpan: float):
        h, l, c = m["yuksek"], m["dusuk"], m["kapanis"]
        atr = g.atr(h, l, c, per)
        hl2 = ((h + l) / 2.0).to_numpy()
        a = atr.to_numpy()
        ub, lb = hl2 + carpan * a, hl2 - carpan * a
        cv = c.to_numpy()
        n = len(cv)
        yon = np.ones(n, dtype=int)
        st = np.zeros(n)
        for i in range(1, n):
            if cv[i] > ub[i - 1]:
                yon[i] = 1
            elif cv[i] < lb[i - 1]:
                yon[i] = -1
            else:
                yon[i] = yon[i - 1]
            st[i] = lb[i] if yon[i] == 1 else ub[i]
        return pd.Series(st, index=m.index), atr

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        st, atr = self._supertrend_ham(mumlar, int(p["vol_n"]), float(p["carpan"]))
        e1, e2, e3 = g.ema(kap, int(p["ema_k"])), g.ema(kap, int(p["ema_o"])), g.ema(kap, int(p["ema_u"]))
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["adx_n"]))["adx"] > float(p["adx_esik"])
        obv = _obv(kap, mumlar["hacim"])
        vosc = obv - g.ema(obv, int(p["vosc_n"]))
        al = (kap > st) & (e1 > e2) & (e2 > e3) & adx & (vosc > 0)
        cik = (kap < st) & (e1 < e2) & (e2 < e3) & adx & (vosc < 0)
        mes = float(p["stop_k"]) * atr
        self._kapanis_dizisi(mumlar, atr=atr)
        return _bitir(cerceve(mumlar, al, False, kap - mes, kap + mes), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        kv, av = self._kd["kap"], self._kd["atr"]
        b = max(int(d.giris_mum_indeksi), 0)
        k = float(self.parametreler["stop_k"])
        s = kv[b:i + 1] - k * av[b:i + 1]
        s = s[np.isfinite(s)]
        if len(s) and kv[i] <= s.max():
            return True
        return bool(np.isfinite(av[i]) and kv[i] >= d.giris_fiyati + float(self.parametreler["tp_k"]) * av[i])


# ================================================================ B001:814
class MacdToparlanmaB0814(_Taban):
    """HAM:B001:814 (macd_recovery.py, 5m long): son 8 mumun en düşük RSI(14)'ü < 41 VE kapanış > EMA(200) VE MACD(12,26,9) sinyalini yukarı keser. Çıkış:
    son 8 mumun en yüksek RSI(14)'ü > 93 VE MACD > 0 VE MACD sinyalini aşağı keser. ROI 11 basamaklı (0:3,024 ... 2113dk:0); stop -%4,032."""

    ad, stil = "kapanis__macd-toparlanma-b0814", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "pencere": 8, "rsi_alt": 41.0, "rsi_ust": 93.0, "ema_n": 200, "sl": 0.04032}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.03024, 296: 0.02924, 596: 0.02545, 840: 0.02444, 966: 0.02096,
                                                    1258: 0.01709, 1411: 0.01598, 1702: 0.0122, 1893: 0.00732,
                                                    2053: 0.00493, 2113: 0.0}, 5))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        w = int(p["pencere"])
        mc = g.macd(kap)
        al = (r.rolling(w).min() < float(p["rsi_alt"])) & (kap > g.ema(kap, int(p["ema_n"]))) & yukari(mc["macd"], mc["sinyal"])
        cik = (r.rolling(w).max() > float(p["rsi_ust"])) & (mc["macd"] > 0) & asagi(mc["macd"], mc["sinyal"])
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ B001:251
class MarketCipherB0251(_Taban):
    """HAM:B001:251 (MarketCypherHyperStrategy.py, 1h long): ADX(14), DI(25) ile trend: ADX>20 VE +DI<-DI aşağı; ADX<20 yatay; ADX>20 VE +DI>-DI yukarı. WaveTrend:
    ap=(H+L+C)/3; esa=EMA3(ap); d=EMA3(|ap-esa|); ci=(ap-esa)/(0,015 d); wt1=EMA21(ci); wt2=SMA4(wt1). Giriş: (wt2<=wt1) VE (wt2<=aşırı-satım[trend]) iken
    wt ağırlığı VE (bullish_div VE RSI14<=eşik[trend]) iken diverjans ağırlığı; kaynakta ağırlık sütunları NaN başlangıçlı olduğu için İKİ koşul AYNI
    mumda gerekir, toplam >= gereken[trend]. bullish_div: kapanış[-4]>kapanış[-2], kapanış[-3]>kapanış[-2], kapanış[-2]<kapanış[-1], kapanış[-2]<kapanış.
    Çıkış: (wt2>=wt1) VE (wt2>=aşırı-alım[trend]) ağırlığı + bearish_div ağırlığı, ikisi aynı mumda, toplam >= gereken. Sideways giriş kolu fiilen ölü
    (5+35<80). ROI {0:23,733; 238dk:20,624; 846:8,939; 1834:0}; stop -%2,47; iz süren %1,658 (offset %10,224, yalnız offset sonrası)."""

    ad, stil = "kapanis__market-cipher-b0251", "swing"
    varsayilan_parametreler = {
        "adx_n": 14, "di_n": 25, "trend_esik": 20.0, "wt_n1": 3, "wt_n2": 21, "wt_ort": 4,
        "os_down": -37.0, "os_side": -28.0, "os_up": -43.0, "div_rsi_down": 79.0, "div_rsi_side": 45.0, "div_rsi_up": 93.0,
        "al_wt_down": 96.0, "al_wt_side": 5.0, "al_wt_up": 91.0, "al_div_down": 50.0, "al_div_side": 35.0, "al_div_up": 84.0,
        "al_gerekli_down": 70.0, "al_gerekli_side": 80.0, "al_gerekli_up": 25.0,
        "ob_down": 75.67481, "ob_side": 1.93351, "ob_up": 37.98512,
        "sat_wt_down": 30.0, "sat_wt_side": 83.0, "sat_wt_up": 43.0, "sat_div_down": 90.0, "sat_div_side": 59.0,
        "sat_div_up": 99.0, "sat_gerekli_down": 51.0, "sat_gerekli_side": 36.0, "sat_gerekli_up": 93.0, "sl": 0.0247}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.23733, 238: 0.20624, 846: 0.08939, 1834: 0.0}, 60),
                                   geri_cekilme_yuzde=1.658, geri_cekilme_min_kar_yuzde=10.224)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["adx_n"]))["adx"]
        di = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["di_n"]))
        esik = float(p["trend_esik"])
        down = (adx > esik) & (di["arti_di"] < di["eksi_di"])
        side = adx < esik
        up = (adx > esik) & (di["arti_di"] > di["eksi_di"])
        ap = _tipik(mumlar)
        esa = g.ema(ap, int(p["wt_n1"]))
        d = g.ema((ap - esa).abs(), int(p["wt_n1"]))
        ci = (ap - esa) / (0.015 * d)
        wt1 = g.ema(ci, int(p["wt_n2"]))
        wt2 = g.sma(wt1, int(p["wt_ort"]))
        cross_up, cross_down = wt2 <= wt1, wt2 >= wt1
        rsi = g.rsi(kap, 14)
        bull = ((kap.shift(4) > kap.shift(2)) & (kap.shift(3) > kap.shift(2)) & (kap.shift(2) < kap.shift(1))
                & (kap.shift(2) < kap))
        bear = ((kap.shift(4) < kap.shift(2)) & (kap.shift(3) < kap.shift(2)) & (kap.shift(2) > kap.shift(1))
                & (kap.shift(2) > kap))
        al = pd.Series(False, index=mumlar.index)
        cik = pd.Series(False, index=mumlar.index)
        for ad_, maske in (("down", down), ("side", side), ("up", up)):
            wt_ok = cross_up & (wt2 <= float(p[f"os_{ad_}"]))
            dv_ok = bull & (rsi <= float(p[f"div_rsi_{ad_}"]))
            toplam = float(p[f"al_wt_{ad_}"]) + float(p[f"al_div_{ad_}"])
            if toplam >= float(p[f"al_gerekli_{ad_}"]):
                al = al | (maske & wt_ok & dv_ok)
            wt_s = cross_down & (wt2 >= float(p[f"ob_{ad_}"]))
            toplam_s = float(p[f"sat_wt_{ad_}"]) + float(p[f"sat_div_{ad_}"])
            if toplam_s >= float(p[f"sat_gerekli_{ad_}"]):
                cik = cik | (maske & wt_s & bear)
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ B001:723
def _ssl(u: pd.DataFrame, uzunluk: int) -> tuple:
    """SSL kanalı (1h): smaHigh/smaLow = HL ortalaması +/- ATR(14); hlv yönü ffill; (aşağı çizgi, yukarı çizgi)."""
    atr = g.atr(u["yuksek"], u["dusuk"], u["kapanis"], 14)
    sh = u["yuksek"].rolling(uzunluk).mean() + atr
    sl_ = u["dusuk"].rolling(uzunluk).mean() - atr
    hlv = pd.Series(np.where(u["kapanis"] > sh, 1.0, np.where(u["kapanis"] < sl_, -1.0, np.nan)), index=u.index).ffill()
    neg = (hlv < 0).to_numpy()
    return (pd.Series(np.where(neg, sh, sl_), index=u.index), pd.Series(np.where(neg, sl_, sh), index=u.index))


class NfiV2B0723(_Taban):
    """HAM:B001:723 (NostalgiaForInfinityV2.py, 5m long, 1h bilgi): üç giriş kolu. Kol1: kapanış<SMA9 VE kapanış>1h EMA200 VE EMA50>EMA200 VE 1h EMA50>1h EMA200
    VE önceki BB40-alt>0 VE bbdelta(|BB40 orta-alt|)>kapanış x 0,017 VE |kapanış-önceki kapanış|>kapanış x 0,013 VE (kapanış-düşük)<bbdelta x 0,445 VE kapanış<önceki
    BB40-alt VE kapanış<=önceki kapanış. Kol2: kapanış<SMA9 VE >EMA200 VE >1h EMA200 VE <EMA50 VE kapanış<0,992 x BB(20,2s; tipik) alt VE hacim<önceki 30 mum ort.
    hacim x 27. Kol3: kapanış<SMA5 VE >EMA200 VE >1h EMA200 VE 1h SSL(20) yukarı>aşağı VE EMA50>EMA200 VE 1h EMA50>1h EMA200 VE RSI14 < 1h RSI14 - 52,438.
    Çıkış (VEYA): RSI14>79,706 VE 3 ardışık kapanış>BB(20,2s tipik) üst; RSI14>85,023; kapanış<EMA200 VE kapanış>EMA50 VE RSI14>87,545; kapanış<EMA200 VE
    (EMA200-kapanış)/kapanış<0,03 VE RSI14>1h RSI14+0,873. ROI {0:1000%} (fiilen yok); stop -1,0 -> ATR(14)x3 uyarlaması."""

    ad, stil = "kapanis__nfi-v2-b0723", "daytrade"
    varsayilan_parametreler = {"bb40_bbdelta": 0.017, "bb40_closedelta": 0.013, "bb40_tail": 0.445, "bb20_alt": 0.992,
                               "bb20_hacim": 27.0, "rsi_fark": 52.438, "sat_rsi_bb": 79.706, "sat_rsi_ana": 85.023,
                               "sat_rsi_2": 87.545, "sat_ema_goreli": 0.03, "sat_rsi_fark": 0.873, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, dus, hac = mumlar["kapanis"], mumlar["dusuk"], mumlar["hacim"]

        def bilgi(u):
            sd, su = _ssl(u, 20)
            return pd.DataFrame({"ema50": g.ema(u["kapanis"], 50), "ema200": g.ema(u["kapanis"], 200),
                                 "rsi": g.rsi(u["kapanis"], 14), "ssl_d": sd, "ssl_u": su})

        h1 = ust_zaman(mumlar, "1h", bilgi)
        bb40 = _bb(kap, 40, 2.0, 1)
        alt40 = bb40["alt"]
        bbdelta = (bb40["orta"] - alt40).abs()
        cdelta = (kap - kap.shift(1)).abs()
        kuyruk = (kap - dus).abs()
        bb20 = _bb(_tipik(mumlar), 20, 2.0, 1)
        ema50, ema200, sma5, sma9 = g.ema(kap, 50), g.ema(kap, 200), g.sma(kap, 5), g.sma(kap, 9)
        hort = hac.rolling(30).mean()
        rsi = g.rsi(kap, 14)
        hacim = hac > 0
        k1 = ((kap < sma9) & (kap > h1["ema200"]) & (ema50 > ema200) & (h1["ema50"] > h1["ema200"])
              & (alt40.shift(1) > 0) & (bbdelta > kap * float(p["bb40_bbdelta"])) & (cdelta > kap * float(p["bb40_closedelta"]))
              & (kuyruk < bbdelta * float(p["bb40_tail"])) & (kap < alt40.shift(1)) & (kap <= kap.shift(1)) & hacim)
        k2 = ((kap < sma9) & (kap > ema200) & (kap > h1["ema200"]) & (kap < ema50)
              & (kap < float(p["bb20_alt"]) * bb20["alt"]) & (hac < hort.shift(1) * float(p["bb20_hacim"])))
        k3 = ((kap < sma5) & (kap > ema200) & (kap > h1["ema200"]) & (h1["ssl_u"] > h1["ssl_d"]) & (ema50 > ema200)
              & (h1["ema50"] > h1["ema200"]) & (rsi < h1["rsi"] - float(p["rsi_fark"])) & hacim)
        ust = bb20["ust"]
        c1 = ((rsi > float(p["sat_rsi_bb"])) & (kap > ust) & (kap.shift(1) > ust.shift(1)) & (kap.shift(2) > ust.shift(2)) & hacim)
        c2 = (rsi > float(p["sat_rsi_ana"])) & hacim
        c3 = (kap < ema200) & (kap > ema50) & (rsi > float(p["sat_rsi_2"])) & hacim
        c4 = ((kap < ema200) & (((ema200 - kap) / kap) < float(p["sat_ema_goreli"])) & (rsi > h1["rsi"] + float(p["sat_rsi_fark"])) & hacim)
        mes = _atr_mes(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(cerceve(mumlar, k1 | k2 | k3, False, kap - mes, kap + mes), c1 | c2 | c3 | c4)


# ================================================================ B001:54
def _starrise_stop_orani(p: dict):
    """StarRise custom_stoploss: açılışa göre kâr kademeli stop (stoploss_from_open): kâr>PF2: SL2+(kâr-PF2); kâr>PF1: SL1+(kâr-PF1)(SL2-SL1)/(PF2-PF1);
    aksi pHSL. Stop fiyatı = giriş x (1+sl_kar); sl_kar >= kâr ise stop yok. Dönen: fonksiyon(kâr) -> stop oranı (giriş=1)."""
    hsl, pf1, sl1, pf2, sl2 = (float(p[k]) for k in ("pHSL", "pPF_1", "pSL_1", "pPF_2", "pSL_2"))

    def f(kar: np.ndarray) -> np.ndarray:
        sl = np.where(kar > pf2, sl2 + (kar - pf2), np.where(kar > pf1, sl1 + (kar - pf1) * (sl2 - sl1) / (pf2 - pf1), hsl))
        return np.where(sl >= kar, 0.0, 1.0 + sl)
    return f


class StarriseDipB0054(_Taban):
    """HAM:B001:54 (StarRise__2.py, 5m long, 1h bilgi): kapanış<MAMA(hl2; 0,5/0,05) VE Williams%R(14)<-30 VE CTI(20)<3 VE ADX(14)>26 VE 1h mama_diff>0,003 VE
    MAMA>FAMA VE SMA50>SMA200 x 1,01 VE 1h MAMA>1h FAMA x 1,01 VE RSI84<55 VE RSI112<55 VE 1h CTI(40)<0,73 VE 1h %R(96)<-6 VE 1h mama_diff<0,027 VE son-288 mum
    max kapanış >= kapanış x 1,03 (mama_diff=(MAMA-FAMA)/hl2). Çıkış sinyali (yalnız kârda): kapanış > BB(17, 1s; tipik) üst x 0,999 VE RSI14>76. ROI {0:9,2; 29dk:4,2;
    85:3; 128:0,5}; stop -0,998 -> ATR(14)x3 felaket stopu. custom_stoploss (kancada, kapanış bazlı): kâr>%1,1 olunca açılışa göre kilitleme (pPF/pSL)."""

    ad, stil = "kapanis__starrise-dip-b0054", "daytrade"
    varsayilan_parametreler = {"wr_n": 14, "wr_al": -30.0, "cti_n": 20, "cti_al": 3.0, "adx_esik": 26.0, "mama_fark_alt": 0.003,
                               "mama_fark_ust": 0.027, "rsi_a": 84, "rsi_b": 112, "rsi_esik": 55.0, "cti1_al": 0.73, "wr1_al": -6.0,
                               "tepe_pencere": 288, "tepe_oran": 1.03, "bb_n": 17, "bb_k": 1.0, "bb_carpan": 0.999, "sat_rsi": 76.0,
                               "pHSL": -0.998, "pPF_1": 0.011, "pSL_1": 0.011, "pPF_2": 0.065, "pSL_2": 0.062,
                               "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.092, 29: 0.042, 85: 0.03, 128: 0.005}, 5), yalniz_karda_cikis=True)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]

        def bilgi(u):
            mama, fama = _mama_fama((u["yuksek"] + u["dusuk"]) / 2.0, 0.5, 0.05)
            hl2 = (u["yuksek"] + u["dusuk"]) / 2.0
            return pd.DataFrame({"cti40": _cti(u["kapanis"], 40), "r96": _williams(u, 96), "mama": mama, "fama": fama,
                                 "fark": (mama - fama) / hl2})

        h1 = ust_zaman(mumlar, "1h", bilgi)
        hl2 = (mumlar["yuksek"] + mumlar["dusuk"]) / 2.0
        mama, fama = _mama_fama(hl2, 0.5, 0.05)
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, 14)["adx"]
        al = ((kap < mama) & (_williams(mumlar, int(p["wr_n"])) < float(p["wr_al"])) & (_cti(kap, int(p["cti_n"])) < float(p["cti_al"]))
              & (adx > float(p["adx_esik"])) & (h1["fark"] > float(p["mama_fark_alt"])) & (mama > fama)
              & (g.sma(kap, 50) > g.sma(kap, 200) * 1.01) & (h1["mama"] > h1["fama"] * 1.01)
              & (g.rsi(kap, int(p["rsi_a"])) < float(p["rsi_esik"])) & (g.rsi(kap, int(p["rsi_b"])) < float(p["rsi_esik"]))
              & (h1["cti40"] < float(p["cti1_al"])) & (h1["r96"] < float(p["wr1_al"])) & (h1["fark"] < float(p["mama_fark_ust"]))
              & (kap.rolling(int(p["tepe_pencere"])).max() >= kap * float(p["tepe_oran"])) & (mumlar["hacim"] > 0))
        bb = _bb(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]), 1)
        cik = (kap > bb["ust"] * float(p["bb_carpan"])) & (g.rsi(kap, 14) > float(p["sat_rsi"])) & (mumlar["hacim"] > 0)
        mes = _atr_mes(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        self._kapanis_dizisi(mumlar)
        return _bitir(cerceve(mumlar, al, False, kap - mes, kap + mes), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i) or not d.giris_fiyati > 0:
            return False
        c = self._kd["kap"][max(int(d.giris_mum_indeksi), 0):i + 1]
        oran = _starrise_stop_orani(self.parametreler)(c / d.giris_fiyati - 1.0)
        s = (oran * d.giris_fiyati)[np.isfinite(oran)]
        return bool(len(s)) and bool(s.max() > 0) and bool(self._kd["kap"][i] <= s.max())


# ================================================================ B001:527 / 528
class TemaBbCmo14B0527(_Taban):
    """HAM:B001:527 (TemaPureNeat.py, 5m long): TEMA(18) Bollinger(25, 1,5s; tipik fiyat; qtpylib ddof=1) alt bandını yukarı keser VE CMO(14) > -5. Çıkış
    sinyali: CMO(14) -58'i aşağı keser. ROI {0:20,934; 238dk:6,449; 1931:1,703; 3474:0}; stop -%10,145; iz süren %29,846 (offset %30,425, yalnız offset sonrası)."""

    ad, stil = "kapanis__tema-bb-cmo14-b0527", "daytrade"
    varsayilan_parametreler = {"tema_n": 18, "bb_n": 25, "bb_k": 1.5, "cmo_n": 14, "cmo_al": -5.0, "cmo_cik": -58.0, "sl": 0.10145}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.20934, 238: 0.06449, 1931: 0.01703, 3474: 0.0}, 5),
                                   geri_cekilme_yuzde=29.846, geri_cekilme_min_kar_yuzde=30.425)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tema = _tema(kap, int(p["tema_n"]))
        alt = _bb(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]), 1)["alt"]
        cmo = _cmo(kap, int(p["cmo_n"]))
        al = yukari(tema, alt) & (cmo > float(p["cmo_al"]))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), asagi(cmo, float(p["cmo_cik"])))


class TemaBbCmo50B0528(_Taban):
    """HAM:B001:528 (TemaPureTwo.py, 5m long): TEMA(18) Bollinger(25, 1,0s; TA-Lib BBANDS = kapanış üzerinden, ddof=0) alt bandını yukarı keser VE CMO(50) > 0.
    Çıkış sinyali: CMO(50) -25'i aşağı keser. ROI {0:12,607; 331dk:12,606; 865:12,605; 1945:1}; stop -%11; iz süren %29,846 (offset %30,425, yalnız offset sonrası).
    Uyarlama: kural_tam 'BB(TA-Lib)' kapanış üzerindendir (dosya ta.BBANDS(dataframe) = kapanış), tipik fiyat DEĞİL."""

    ad, stil = "kapanis__tema-bb-cmo50-b0528", "daytrade"
    varsayilan_parametreler = {"tema_n": 18, "bb_n": 25, "bb_k": 1.0, "cmo_n": 50, "cmo_al": 0.0, "cmo_cik": -25.0, "sl": 0.11}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.12607, 331: 0.12606, 865: 0.12605, 1945: 0.01}, 5),
                                   geri_cekilme_yuzde=29.846, geri_cekilme_min_kar_yuzde=30.425)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tema = _tema(kap, int(p["tema_n"]))
        alt = _bb(kap, int(p["bb_n"]), float(p["bb_k"]), 0)["alt"]
        cmo = _cmo(kap, int(p["cmo_n"]))
        al = yukari(tema, alt) & (cmo > float(p["cmo_al"]))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), asagi(cmo, float(p["cmo_cik"])))


# ================================================================ B001:871
class LamboWrStochB0871(_Taban):
    """HAM:B001:871 (flawless_lambo__2.py, 5m long): hacim>5000 VE OBV eğimi>0 (OBV farkı) VE -92,098 < Williams%R(14) <= -58,201 VE 2,342 < RSI14 <= 51,22 VE
    STOCHF fastk, STOCH slowd'yi (SMA3(SMA3(fastk5))) yukarı keser VE kapanış < BB(20, 2s; tipik) orta. Çıkış (Python önceliği: & önce): (hacim>1000 VE kapanış>=BB üst VE
    %R>-19,308) VEYA (RSI14>60,631 VE +DI(14) -DI'yı aşağı keser) VEYA MACD sinyali aşağı keser VEYA fastk slowd'yi aşağı keser VEYA vpci>=BB üst; yalnız kârda
    (sell_profit_only). ROI {0:6,25; 28dk:5; 76:4; 125:3; 240:2; 360:0}; stop -%6,25; trailing kapalı. Uyarlama: vpci (technical kütüphanesi) formülü kaynak dosyada
    yok; standart tanım kullanıldı: (VWMA14-SMA14) x (VWMA7/SMA7) x (SMA hacim7/SMA hacim14); ölçeği fiyat birimindedir, BB üstüne nadiren ulaşır (kol fiilen sönük)."""

    ad, stil = "kapanis__lambo-wr-stoch-b0871", "daytrade"
    varsayilan_parametreler = {"hacim_al": 5000.0, "wr_alt": -92.098, "wr_ust": -58.201, "rsi_alt": 2.342, "rsi_ust": 51.22,
                               "hacim_sat": 1000.0, "wr_sat": -19.308, "rsi_sat": 60.631, "vpci_uzun": 14, "sl": 0.0625}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.0625, 28: 0.05, 76: 0.04, 125: 0.03, 240: 0.02, 360: 0.0}, 5),
                                   yalniz_karda_cikis=True)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, hac = mumlar["kapanis"], mumlar["hacim"]
        bb = _bb(_tipik(mumlar), 20, 2.0, 1)
        obv_egim = _obv(kap, hac).diff()
        wr = _williams(mumlar, 14)
        rsi = g.rsi(kap, 14)
        fastk, _ = _stochf(mumlar, 5, 3)
        _, slowd = _stoch_yavas(mumlar, 5, 3, 3)
        mc = g.macd(kap)
        di = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, 14)
        n_u = int(p["vpci_uzun"])
        n_k = max(n_u // 2, 1)

        def vwma(n):
            return (kap * hac).rolling(n).sum() / hac.rolling(n).sum().where(lambda x: x > 0)

        vpci = (vwma(n_u) - g.sma(kap, n_u)) * (vwma(n_k) / g.sma(kap, n_k)) * (g.sma(hac, n_k) / g.sma(hac, n_u))
        al = ((hac > float(p["hacim_al"])) & (obv_egim > 0) & (wr <= float(p["wr_ust"])) & (wr > float(p["wr_alt"]))
              & (rsi > float(p["rsi_alt"])) & (rsi <= float(p["rsi_ust"])) & yukari(fastk, slowd) & (kap < bb["orta"]))
        cik = (((hac > float(p["hacim_sat"])) & (kap >= bb["ust"]) & (wr > float(p["wr_sat"])))
               | ((rsi > float(p["rsi_sat"])) & asagi(di["arti_di"], di["eksi_di"]))
               | asagi(mc["macd"], mc["sinyal"]) | asagi(fastk, slowd) | (vpci >= bb["ust"]))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ B001:136 / 138 (ichiV1, 30m)
class _IchiTaban(_Taban):
    """ichiV1 çekirdeği (30m long): Heikin-Ashi AÇILIŞ/YÜKSEK/DÜŞÜK + gerçek kapanış; Ichimoku (20/60/120; öteleme 30; Tenkan/Kijun/Span-B yüksek-düşük orta noktası, HA
    yüksek/düşük üzerinden; bulut nedensel: geçmiş değer ileri taşınır). Trend seviyeleri: 5m = (kapanış, HA açılış), diğer 7 seviye = EMA(kapanış)/EMA(HA açılış)
    (periyotlar `ema_periyot`, sırayla '15m,30m,1h,2h,4h,6h,8h'). Giriş (hepsi VE): kapanış > senkou_a VE > senkou_b VE ilk 6 seviyede trend_close>trend_open VE
    fan=EMA(1h)/EMA(8h) için fan/fan[-1] >= 1,004 VE fan>1 VE fan[-k] < fan (k=1..fan_shift). Not: ftt.ichimoku öteleme farkı (+/-1 mum) uygulanmadı."""

    parametre_izgarasi = {}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ha = _ha(mumlar)
        ho, hh, hl = ha["ha_acilis"], ha["ha_yuksek"], ha["ha_dusuk"]
        per = [int(x) for x in p["ema_periyot"]]
        tc = [kap] + [g.ema(kap, n) for n in per]
        to = [ho] + [g.ema(ho, n) for n in per]
        t1, t2, t3, k = (int(x) for x in p["ichimoku"])

        def orta(n):
            return (hh.rolling(n).max() + hl.rolling(n).min()) / 2.0

        sa = ((orta(t1) + orta(t2)) / 2.0).shift(k)
        sb = orta(t3).shift(k)
        fan = tc[3] / tc[7]
        gain = fan / fan.shift(1)
        al = (kap > sa) & (kap > sb) & (gain >= float(p["fan_gain_min"])) & (fan > 1)
        for lv in range(int(p["bullish_seviye"])):
            al = al & (tc[lv] > to[lv])
        for x in range(int(p["fan_shift"])):
            al = al & (fan.shift(x + 1) < fan)
        mes = _atr_mes(mumlar, 14, 3.0)
        s = cerceve(mumlar, al, False, kap * (1 - float(p["sl"])) if float(p["sl"]) > 0 else kap - mes,
                    kap * (1 + float(p["sl"])) if float(p["sl"]) > 0 else kap + mes)
        if p["cikis"] == "kapanis_ema2h_asagi":
            return _bitir(s, asagi(kap, tc[4]))
        return s


class IchiV1B0136(_IchiTaban):
    """HAM:B001:136 (ichiV1.py, 30m long): ichiV1 çekirdeği; EMA periyotları 2/3/5/8/13/21/34; fan_shift=3; çıkış sinyali kapalı. ROI {0:1; 30dk:0,2; 60:-1} (60 dk
    sonra kâr/zarar fark etmeksizin çık -> zaman çıkışı 2 mum + azalan_roi); iz süren %0,2 (offset %0,5, yalnız offset sonrası); stop -0,99 -> ATR(14)x3. protections
    (CooldownPeriod/MaxDrawdown) motor dışı."""

    ad, stil = "kapanis__ichi-v1-30m-b0136", "daytrade"
    varsayilan_parametreler = {"ema_periyot": (2, 3, 5, 8, 13, 21, 34), "ichimoku": (20, 60, 120, 30), "bullish_seviye": 6,
                               "fan_shift": 3, "fan_gain_min": 1.004, "cikis": "yok", "sl": 0.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.01, 30: 0.002}, 30), zaman_cikisi_mum=2,
                                   geri_cekilme_yuzde=0.2, geri_cekilme_min_kar_yuzde=0.5)


class IchiV1Fan1B0138(_IchiTaban):
    """HAM:B001:138 (ichiV1__3.py, 30m long): ichiV1 çekirdeği; EMA periyotları 3/6/12/24/48/72/96 (fan = EMA12/EMA96); fan_shift=1. Çıkış sinyali: kapanış, EMA(24)'ü
    (2h) aşağı keser (kâr şartı yok). ROI {0:5; 60dk:1; 90:0,5; 120:0,1}; stop -%27,5; iz süren %0,2 (offset %2,5, yalnız offset sonrası)."""

    ad, stil = "kapanis__ichi-v1-fan1-b0138", "daytrade"
    varsayilan_parametreler = {"ema_periyot": (3, 6, 12, 24, 48, 72, 96), "ichimoku": (20, 60, 120, 30), "bullish_seviye": 6,
                               "fan_shift": 1, "fan_gain_min": 1.004, "cikis": "kapanis_ema2h_asagi", "sl": 0.275}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.05, 60: 0.01, 90: 0.005, 120: 0.001}, 30),
                                   geri_cekilme_yuzde=0.2, geri_cekilme_min_kar_yuzde=2.5)


# ================================================================ B001:250
_TDW_TABLO = frozenset(
    w * 100 + d for w, d in (
        (0, 4), (0, 6), (0, 8), (0, 14), (0, 18), (0, 25), (0, 26), (0, 29), (1, 16), (1, 22), (1, 29), (1, 31), (2, 1), (2, 3),
        (2, 4), (2, 5), (2, 6), (2, 9), (2, 10), (2, 12), (2, 13), (2, 15), (2, 16), (2, 20), (2, 21), (2, 25), (2, 26), (2, 27),
        (2, 29), (4, 6), (4, 13), (4, 19), (5, 4), (5, 10), (5, 19), (5, 20), (5, 28), (6, 3)))


class TakvimTdwTdmB0250(_Taban):
    """HAM:B001:250 (lw_tdw_tdm_btc_v1__2.py, 15m long, takvim): UTC saat==0 (00:00-00:45 mumları) VE (haftanın günü:ayın günü) 38 çiftlik tabloda -> long. Çıkış
    sinyali: saat==23 VE dakika==45 VE aynı tablo. KAYNAK DOSYADA giriş ve çıkış tabloları AYNIDIR (38 çift; kural_tam 'çıkışta 1:29 yok, 37 çift' demişti, dosyada
    1:29 çıkışta da var). ROI tanımsız; stop -1 -> ATR(14)x3 uyarlaması."""

    ad, stil = "kapanis__takvim-tdw-tdm-b0250", "daytrade"
    varsayilan_parametreler = {"giris_saat": 0, "cikis_saat": 23, "cikis_dakika": 45, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        idx = mumlar.index
        anahtar = pd.Series(idx.dayofweek * 100 + idx.day, index=idx)
        tabloda = anahtar.isin(_TDW_TABLO)
        al = (pd.Series(idx.hour, index=idx) == int(p["giris_saat"])) & tabloda
        cik = ((pd.Series(idx.hour, index=idx) == int(p["cikis_saat"])) & (pd.Series(idx.minute, index=idx) == int(p["cikis_dakika"]))
               & tabloda)
        mes = _atr_mes(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(cerceve(mumlar, al, False, kap - mes, kap + mes), cik)


# ================================================================ B001:227
class Mk4RsiGraB0227(_Taban):
    """HAM:B001:227 (mk4__2.py, 15m long+short): RSI14; rsi_ema = EWM(RSI14, span=24); rsi_gra = EWM(span=3) of rsi_ema farkı; MACD(12,26,9); KDJ(9; com=2).
    Long: RSI14<41 VE rsi_gra 0'ı yukarı keser VE MACD<sinyal VE (düşük<önceki düşük VE MACD>önceki MACD). Short (kaynakta doğru sütuna yazılıyor): RSI14>59 VE
    rsi_gra 0'ı aşağı keser VE MACD>sinyal VE (yüksek>önceki yüksek VE MACD<önceki MACD). Sinyal çıkışı kaynakta ölü (rolling pencere mevcut mumu içerdiğinden
    düşük<min(düşük,20) asla doğru değil). custom_exit (kancada): long için girişten beri MACD altın kesişimi olmuş VE MACD>sinyal VE KDJ ölüm kesişimi (K D'yi aşağı
    keser); short ayna. ROI {0:12,8; 15dk:..} (5 basamak); stop -%21,3; iz süren %2,8 (offset %12,8, yalnız offset sonrası). DCA parametreleri pasif; kaldıraç yok sayıldı."""

    ad, stil = "kapanis__mk4-rsi-gra-b0227", "daytrade"
    varsayilan_parametreler = {"rsi_al": 41.0, "rsi_sat": 59.0, "rsi_ema_span": 24, "rsi_gra_span": 3, "sl": 0.213}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.128, 16: 0.102, 31: 0.078, 46: 0.046, 61: 0.038}, 15),
                                   geri_cekilme_yuzde=2.8, geri_cekilme_min_kar_yuzde=12.8)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, yuk, dus = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        rsi = g.rsi(kap, 14)
        rsi_ema = rsi.ewm(span=int(p["rsi_ema_span"])).mean()
        gra = rsi_ema.diff().ewm(span=int(p["rsi_gra_span"])).mean()
        mc = g.macd(kap, 12, 26, 9)
        macd, sinyal = mc["macd"], mc["sinyal"]
        al = ((rsi < float(p["rsi_al"])) & yukari(gra, 0.0) & (macd < sinyal) & (dus < dus.shift(1)) & (macd > macd.shift(1)))
        sat = ((rsi > float(p["rsi_sat"])) & asagi(gra, 0.0) & (macd > sinyal) & (yuk > yuk.shift(1)) & (macd < macd.shift(1)))
        dmin = dus.rolling(9).min()
        hmax = yuk.rolling(9).max()
        rsv = (kap - dmin) / (hmax - dmin) * 100.0
        k = rsv.ewm(com=2).mean()
        dd = k.ewm(com=2).mean()
        altin = yukari(macd, sinyal).astype(float)
        olum = asagi(macd, sinyal).astype(float)
        self._sakla(altin_ks=altin.cumsum(), olum_ks=olum.cumsum(), macd_ustte=(macd > sinyal).astype(float),
                    macd_altta=(macd < sinyal).astype(float), kdj_olum=asagi(k, dd).astype(float),
                    kdj_altin=yukari(k, dd).astype(float))
        sl = float(p["sl"])
        return _cift(mumlar, al, sat, kap * (1 - sl), kap * (1 + sl))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        b = max(int(d.giris_mum_indeksi), 0)
        if d.yon == 1:
            onceki = self._dz("altin_ks", b - 1) if b > 0 else 0.0
            if np.isnan(onceki):
                onceki = 0.0
            return bool(self._dz("altin_ks", i) - onceki > 0 and self._dz("macd_ustte", i) == 1.0 and self._dz("kdj_olum", i) == 1.0)
        onceki = self._dz("olum_ks", b - 1) if b > 0 else 0.0
        if np.isnan(onceki):
            onceki = 0.0
        return bool(self._dz("olum_ks", i) - onceki > 0 and self._dz("macd_altta", i) == 1.0 and self._dz("kdj_altin", i) == 1.0)


# ================================================================ B001:230 / 820
class SampleRsiTemaB0230(_Taban):
    """HAM:B001:230 (sample_strategy.py, 5m long; can_short=False): RSI14 30'u yukarı keser VE TEMA(9) <= BB(20, 2s; tipik) orta VE TEMA yükseliyor (TEMA>TEMA[-1])
    VE hacim>0. Çıkış sinyali: RSI14 70'i yukarı keser VE TEMA>BB orta VE TEMA düşüyor VE hacim>0. ROI {0:4; 30dk:2; 60:1}; stop -%10; trailing kapalı."""

    ad, stil = "kapanis__sample-rsi-tema-b0230", "daytrade"
    varsayilan_parametreler = {"rsi_al": 30.0, "rsi_sat": 70.0, "tema_n": 9, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.04, 30: 0.02, 60: 0.01}, 5))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        rsi = g.rsi(kap, 14)
        tema = _tema(kap, int(p["tema_n"]))
        orta = _bb(_tipik(mumlar), 20, 2.0, 1)["orta"]
        hacim = mumlar["hacim"] > 0
        al = yukari(rsi, float(p["rsi_al"])) & (tema <= orta) & (tema > tema.shift(1)) & hacim
        cik = yukari(rsi, float(p["rsi_sat"])) & (tema > orta) & (tema < tema.shift(1)) & hacim
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


class SampleV2HaTrendB0820(_Taban):
    """HAM:B001:820 (SampleStrategyV2.py, 5m long): 230 kuralı + HA trendi: trend_dir = SMA5(SMA5(SMA288(HA kapanış) - SMA288(HA açılış))) > 0. Çıkış sinyali 230 ile aynı.
    ROI {0:4; 30dk:2; 60:1}; stop -%20; iz süren %0,5 (offset %1, yalnız offset sonrası). 1h MACD bilgi sütunu hesaplanıyor ama kullanılmıyor (kodlanmadı)."""

    ad, stil = "kapanis__sample-v2-ha-trend-b0820", "daytrade"
    varsayilan_parametreler = {"rsi_al": 30.0, "rsi_sat": 70.0, "tema_n": 9, "trend_n": 288, "sl": 0.20}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.04, 30: 0.02, 60: 0.01}, 5),
                                   geri_cekilme_yuzde=0.5, geri_cekilme_min_kar_yuzde=1.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ha = _ha(mumlar)
        n = int(p["trend_n"])
        trend = g.sma(g.sma(g.sma(ha["ha_kapanis"], n) - g.sma(ha["ha_acilis"], n), 5), 5)
        rsi = g.rsi(kap, 14)
        tema = _tema(kap, int(p["tema_n"]))
        orta = _bb(_tipik(mumlar), 20, 2.0, 1)["orta"]
        hacim = mumlar["hacim"] > 0
        al = yukari(rsi, float(p["rsi_al"])) & (trend > 0) & (tema <= orta) & (tema > tema.shift(1)) & hacim
        cik = yukari(rsi, float(p["rsi_sat"])) & (tema > orta) & (tema < tema.shift(1)) & hacim
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ B001:56 / 57 / 58 (Zaratustra)
class ZaratustraV13B0056(_Taban):
    """HAM:B001:56 (ZaratustraV13.py, 5m long+short): TA-Lib DX/ADX/+DI/-DI (14); BB(20, 2s; tipik; qtpylib). Long: (DX>-DI VE ADX>-DI VE +DI>-DI) VEYA kapanış BB üstü
    yukarı keser. Short (DOSYADA, ayna değil): (DX>-DI VE ADX>+DI VE -DI>+DI) VEYA kapanış BB altı aşağı keser. Çıkış sinyali yok (use_exit_signal=False); stop -%29,6;
    iz süren %1 (offset %10, yalnız offset sonrası). Kaldıraç 10 yok sayıldı."""

    ad, stil = "kapanis__zaratustra-v13-b0056", "daytrade"
    varsayilan_parametreler = {"di_n": 14, "bb_n": 20, "bb_k": 2.0, "sl": 0.296}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=1.0, geri_cekilme_min_kar_yuzde=10.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        d = _di(mumlar, int(p["di_n"]))
        bb = _bb(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]), 1)
        al = ((d["dx"] > d["mdi"]) & (d["adx"] > d["mdi"]) & (d["pdi"] > d["mdi"])) | yukari(kap, bb["ust"])
        sat = ((d["dx"] > d["mdi"]) & (d["adx"] > d["pdi"]) & (d["mdi"] > d["pdi"])) | asagi(kap, bb["alt"])
        sl = float(p["sl"])
        return _cift(mumlar, al, sat, kap * (1 - sl), kap * (1 + sl))


class ZaratustraV17B0057(_Taban):
    """HAM:B001:57 (ZaratustraV17.py, 5m long+short): LINEARREG_SLOPE(14), TSF(14) = doğru uç + eğim, DI(14), BB(8, 2s; tipik; qtpylib). Long: [kapanış BB üstü yukarı keser VEYA
    kapanış TSF'yi yukarı keser VEYA (DX>-DI VE ADX>-DI VE +DI>-DI)] VE eğim artıyor (eğim>önceki eğim) VE eğim>0. Short: [kapanış BB altı aşağı VEYA TSF'yi aşağı VEYA
    (DX>+DI VE ADX>+DI VE -DI>+DI)] VE eğim azalıyor VE eğim<0. Çıkış sinyali yok; stop -%20; iz süren %1,2 (offset %8, yalnız offset sonrası)."""

    ad, stil = "kapanis__zaratustra-v17-b0057", "daytrade"
    varsayilan_parametreler = {"di_n": 14, "lr_n": 14, "bb_n": 8, "bb_k": 2.0, "sl": 0.20}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(geri_cekilme_yuzde=1.2, geri_cekilme_min_kar_yuzde=8.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        d = _di(mumlar, int(p["di_n"]))
        uc, egim = _linreg(kap, int(p["lr_n"]))
        tsf = uc + egim
        bb = _bb(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]), 1)
        art, azl = (egim.shift(1) < egim) & (egim > 0), (egim.shift(1) > egim) & (egim < 0)
        al = (yukari(kap, bb["ust"]) | yukari(kap, tsf)
              | ((d["dx"] > d["mdi"]) & (d["adx"] > d["mdi"]) & (d["pdi"] > d["mdi"]))) & art
        sat = (asagi(kap, bb["alt"]) | asagi(kap, tsf)
               | ((d["dx"] > d["pdi"]) & (d["adx"] > d["pdi"]) & (d["mdi"] > d["pdi"]))) & azl
        sl = float(p["sl"])
        return _cift(mumlar, al, sat, kap * (1 - sl), kap * (1 + sl))


class ZaratustraV4B0058(_Taban):
    """HAM:B001:58 (ZaratustraV4.py, 5m long+short, 15m bilgi): Long: 15m VE 5m için +DI>-DI VE +DI>25 VE kapanış>BB(20, 2s; tipik) orta; ayrıca 5m MACD(12,26,9) > sinyal VE
    sinyal>0 VE MACD>0 (15m değerler yalnız KAPANMIŞ 15m mumdan). Short ayna (-DI>+DI, -DI>25, kapanış<orta, MACD<sinyal<0). Çıkış sinyali yok; ROI {0:100%; 7200dk:0}; stop
    -%29,6; iz süren %1,3 (offset %7,1, yalnız offset sonrası)."""

    ad, stil = "kapanis__zaratustra-v4-b0058", "daytrade"
    varsayilan_parametreler = {"di_n": 14, "di_esik": 25.0, "bb_n": 20, "bb_k": 2.0, "sl": 0.296}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 1.0, 7200: 0.0}, 5), geri_cekilme_yuzde=1.3, geri_cekilme_min_kar_yuzde=7.1)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        n, k = int(p["bb_n"]), float(p["bb_k"])

        def ust(u):
            d = _di(u, int(p["di_n"]))
            return pd.DataFrame({"pdi": d["pdi"], "mdi": d["mdi"], "kap": u["kapanis"],
                                 "orta": _bb(_tipik(u), n, k, 1)["orta"]})

        h15 = ust_zaman(mumlar, "15m", ust)
        d5 = _di(mumlar, int(p["di_n"]))
        orta5 = _bb(_tipik(mumlar), n, k, 1)["orta"]
        mc = g.macd(kap, 12, 26, 9)
        esik = float(p["di_esik"])
        al = ((h15["pdi"] > h15["mdi"]) & (d5["pdi"] > d5["mdi"]) & (h15["pdi"] > esik) & (d5["pdi"] > esik)
              & (h15["kap"] > h15["orta"]) & (kap > orta5) & (mc["macd"] > mc["sinyal"]) & (mc["sinyal"] > 0) & (mc["macd"] > 0))
        sat = ((h15["mdi"] > h15["pdi"]) & (d5["mdi"] > d5["pdi"]) & (h15["mdi"] > esik) & (d5["mdi"] > esik)
               & (h15["kap"] < h15["orta"]) & (kap < orta5) & (mc["macd"] < mc["sinyal"]) & (mc["sinyal"] < 0) & (mc["macd"] < 0))
        sl = float(p["sl"])
        return _cift(mumlar, al, sat, kap * (1 - sl), kap * (1 + sl))


# ================================================================ B001:64
class KeltnerBbrB0064(_Taban):
    """HAM:B001:64 (keltner.py, 15m long+short): long taban = EMA(23), std = STD(26; kapanış, ddof=1); bbr = (kapanış-(taban-2 std))/(4 std); long: bbr[-1]<0 VE bbr>0
    (alt banttan içeri dönüş) VE kapanış<taban. Short (taban EMA(30), std 40): short_bbr[-1]>1 VE short_bbr<1 VE kapanış>short_taban. Çıkış: karşı yön sinyali (long için short
    sinyali, short için long sinyali). ROI {0:27,6; 93dk:6; 158:4,2; 255:0}; stop -%24; kaldıraç yok sayıldı. (atr/kc_min/max sütunları kaynakta kullanılmıyor.)"""

    ad, stil = "kapanis__keltner-bbr-b0064", "daytrade"
    varsayilan_parametreler = {"ma_n": 23, "std_n": 26, "kisa_ma_n": 30, "kisa_std_n": 40, "carpan": 2.0, "sl": 0.24}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.276, 93: 0.06, 158: 0.042, 255: 0.0}, 15))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        c = float(p["carpan"])

        def bbr(ma_n, std_n):
            taban = g.ema(kap, ma_n)
            std = kap.rolling(std_n).std()
            alt, ust = taban - c * std, taban + c * std
            return (kap - alt) / (ust - alt), taban

        r, taban = bbr(int(p["ma_n"]), int(p["std_n"]))
        kr, ktaban = bbr(int(p["kisa_ma_n"]), int(p["kisa_std_n"]))
        al = (r.shift(1) < 0) & (r > 0) & (kap < taban)
        sat = (kr.shift(1) > 1) & (kr < 1) & (kap > ktaban)
        sl = float(p["sl"])
        s = _cift(mumlar, al, sat, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, sat.fillna(False), al.fillna(False))


# ================================================================ B001:134
class ZaratustraLukeB0134(_Taban):
    """HAM:B001:134 (ZaratustraLukeMod.py, 5m long+short): Long = [kapanış>KAMA(50) VE WMA25>WMA100 VE SMA3>WMA140 VE kapanış>max(senkou_a, senkou_b) VE kapanış>HMA50 VE
    düşük>önceki düşük] VEYA drop>0,004 (drop=(kapanış-açılış)/açılış; Python önceliği: VEYA tek başına giriş verir). Short = [ayna: <KAMA50, WMA25<WMA100, SMA3<WMA140,
    kapanış<min(senkou), <HMA50, yüksek<önceki yüksek] VEYA drop<-0,004. senkou_a=((SMA9+SMA26)/2) 26 mum ÖNCE, senkou_b=SMA52 26 mum önce (nedensel; chikou kullanılmıyor).
    Çıkış sinyali yok; ROI {1dk:25; 3:30; 5:50; 15:60} (5m'de 1,3 -> 1. mum %50, 3. mum %60); stop -%15; iz süren %0,1 (offset %15, yalnız offset sonrası). Kaldıraç yok sayıldı."""

    ad, stil = "kapanis__zaratustra-luke-b0134", "daytrade"
    varsayilan_parametreler = {"kama_n": 50, "wma_a": 25, "wma_b": 100, "sma_hizli": 3, "wma_c": 140, "hma_n": 50,
                               "tenkan": 9, "kijun": 26, "senkou_b": 52, "kaydir": 26, "drop_esik": 0.004, "sl": 0.15}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({1: 0.25, 3: 0.3, 5: 0.5, 15: 0.6}, 5),
                                   geri_cekilme_yuzde=0.1, geri_cekilme_min_kar_yuzde=15.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, ac, yuk, dus = mumlar["kapanis"], mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"]
        kama = _kama(kap, int(p["kama_n"]))
        wa, wb, wc = _wma(kap, int(p["wma_a"])), _wma(kap, int(p["wma_b"])), _wma(kap, int(p["wma_c"]))
        s3 = g.sma(kap, int(p["sma_hizli"]))
        hma = _hma(kap, int(p["hma_n"]))
        k = int(p["kaydir"])
        sa = ((g.sma(kap, int(p["tenkan"])) + g.sma(kap, int(p["kijun"]))) / 2.0).shift(k)
        sb = g.sma(kap, int(p["senkou_b"])).shift(k)
        drop = (kap - ac) / ac
        e = float(p["drop_esik"])
        al = ((kap > kama) & (wa > wb) & (s3 > wc) & (kap > np.maximum(sa, sb)) & (kap > hma) & (dus > dus.shift(1))) | (drop > e)
        sat = ((kap < kama) & (wa < wb) & (s3 < wc) & (kap < np.minimum(sa, sb)) & (kap < hma) & (yuk < yuk.shift(1))) | (drop < -e)
        sl = float(p["sl"])
        return _cift(mumlar, al, sat, kap * (1 - sl), kap * (1 + sl))


# ================================================================ B001:146
class EmaxZlsmaB0146(_Taban):
    """HAM:B001:146 (EMAX.py, 5m long): ZLSMA: lsma=LINEARREG(kapanış,15); lsma2=LINEARREG(lsma,15); zlsma=lsma+(lsma-lsma2). RSI(2). Özel ADX(5): +DM/-DM kaynakta
    BOOLEAN (yön koşulu 1/0, büyüklük değil), +DI=EMA5(+DM)/EMA5(TR) x 100, -DI benzer, ADX = EMA5(|+DI-(-DI)|/(+DI+(-DI))) x 100. Giriş: kapanış>zlsma VE RSI2<=20 VE ADX>30 VE
    kapanış>önceki yüksek. Çıkış sinyali: kapanış<zlsma VE RSI2>=80 VE ADX>30 VE kapanış<önceki düşük. ROI {0:10; 5dk:7; 10:5; 15:4; 20:3; 25:2; 30:1; 50:0}; stop -%30; iz süren %1
    (offset %5; trailing_only_offset_is_reached tanımsız=False -> lider kuralı: min kâr 0)."""

    ad, stil = "kapanis__emax-zlsma-b0146", "daytrade"
    varsayilan_parametreler = {"lr_n": 15, "rsi_n": 2, "rsi_alt": 20.0, "rsi_ust": 80.0, "adx_n": 5, "adx_esik": 30.0, "sl": 0.30}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.1, 5: 0.07, 10: 0.05, 15: 0.04, 20: 0.03, 25: 0.02, 30: 0.01, 50: 0.0}, 5),
                                   geri_cekilme_yuzde=1.0, geri_cekilme_min_kar_yuzde=0.0)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, yuk, dus = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        n = int(p["lr_n"])
        lsma, _ = _linreg(kap, n)
        lsma2, _ = _linreg(lsma, n)
        zlsma = lsma + (lsma - lsma2)
        rsi = g.rsi(kap, int(p["rsi_n"]))
        e = int(p["adx_n"])
        yukari_h, asagi_h = yuk.diff(), -dus.diff()
        arti_dm = ((yukari_h > asagi_h) & (yukari_h > 0)).astype(float)
        eksi_dm = ((asagi_h > yukari_h) & (asagi_h > 0)).astype(float)
        tr = g.gercek_aralik(yuk, dus, kap)
        tr_e = g.ema(tr, e)
        arti = g.ema(arti_dm, e) / tr_e * 100.0
        eksi = g.ema(eksi_dm, e) / tr_e * 100.0
        adx = g.ema((arti - eksi).abs() / (arti + eksi), e) * 100.0
        guclu = adx > float(p["adx_esik"])
        al = (kap > zlsma) & (rsi <= float(p["rsi_alt"])) & guclu & (kap > yuk.shift(1))
        cik = (kap < zlsma) & (rsi >= float(p["rsi_ust"])) & guclu & (kap < dus.shift(1))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ koşu listesi
def _p(sinif) -> dict:
    return dict(sinif.varsayilan_parametreler)


def _v(kaynak: str, no: int, sinif, tf: str, parametreler: dict | None = None) -> dict:
    return {"kimlik": f"{kaynak}#v{no}", "sinif": sinif.ad,
            "parametreler": _p(sinif) if parametreler is None else parametreler, "tf": tf}


SINIFLAR = [ElliotV7B0564, ElliotV8B0570, NasosV5B0573, NasosV5Mod1B0574, RalliV1B0590, NasosSmaOfsetB0670, SupertrendEmaObvB0828,
            MacdToparlanmaB0814, MarketCipherB0251, NfiV2B0723, StarriseDipB0054, TemaBbCmo14B0527, TemaBbCmo50B0528,
            LamboWrStochB0871, IchiV1B0136, IchiV1Fan1B0138, TakvimTdwTdmB0250, Mk4RsiGraB0227, SampleRsiTemaB0230,
            SampleV2HaTrendB0820, ZaratustraV13B0056, ZaratustraV17B0057, ZaratustraV4B0058, KeltnerBbrB0064,
            ZaratustraLukeB0134, EmaxZlsmaB0146]

VARYANTLAR = [
    _v("HAM:B001:564", 1, ElliotV7B0564, "5m"),
    _v("HAM:B001:570", 1, ElliotV8B0570, "5m"),
    _v("HAM:B001:573", 1, NasosV5B0573, "5m"),
    _v("HAM:B001:574", 1, NasosV5Mod1B0574, "5m"),
    _v("HAM:B001:590", 1, RalliV1B0590, "5m"),
    _v("HAM:B001:670", 1, NasosSmaOfsetB0670, "5m"),
    _v("HAM:B001:828", 1, SupertrendEmaObvB0828, "5m"),
    _v("HAM:B001:814", 1, MacdToparlanmaB0814, "5m"),
    _v("HAM:B001:251", 1, MarketCipherB0251, "1h"),
    _v("HAM:B001:723", 1, NfiV2B0723, "5m"),
    _v("HAM:B001:54", 1, StarriseDipB0054, "5m"),
    _v("HAM:B001:527", 1, TemaBbCmo14B0527, "5m"),
    _v("HAM:B001:528", 1, TemaBbCmo50B0528, "5m"),
    _v("HAM:B001:871", 1, LamboWrStochB0871, "5m"),
    _v("HAM:B001:136", 1, IchiV1B0136, "30m"),
    _v("HAM:B001:138", 1, IchiV1Fan1B0138, "30m"),
    _v("HAM:B001:250", 1, TakvimTdwTdmB0250, "15m"),
    _v("HAM:B001:227", 1, Mk4RsiGraB0227, "15m"),
    _v("HAM:B001:230", 1, SampleRsiTemaB0230, "5m"),
    _v("HAM:B001:820", 1, SampleV2HaTrendB0820, "5m"),
    _v("HAM:B001:56", 1, ZaratustraV13B0056, "5m"),
    _v("HAM:B001:57", 1, ZaratustraV17B0057, "5m"),
    _v("HAM:B001:58", 1, ZaratustraV4B0058, "5m"),
    _v("HAM:B001:64", 1, KeltnerBbrB0064, "15m"),
    _v("HAM:B001:134", 1, ZaratustraLukeB0134, "5m"),
    _v("HAM:B001:146", 1, EmaxZlsmaB0146, "5m"),
]

KODLANAMADI = [
    {"kimlik": "HAM:B001:571",
     "neden": "motorda ifade edilemiyor: zema kolu BTC/USDT 5m RSI(14) > 0,49 koşulunu (başka sembol verisi; strateji yalnız kendi mumlarını alır) "
              "gerektiriyor (NASOSRv6_private_Reinuvader_20211121.py btc_df/btc_rsi); 5 kollu kuralın bir kolunu atmak kuralı değiştirir (uydurma yok). "
              "Ayrıca kaynakta 'unclog' çıkışı (current_time - open).seconds/60 > 1440 ölçütü .seconds (gün dışı kalan saniye) nedeniyle hiç tetiklenmez."},
    {"kimlik": "HAM:B001:52",
     "neden": "lookahead: StarRise_V3.py populate_indicators'ta threshold_mean/threshold_1/threshold_2 = kapanış x (1 + move.mean() x k) ve move_mean TÜM SERİNİN "
              "ortalaması (dataframe['move'].mean()); use0/1/2/3/4/5 kollarının hepsi bunu kullanır (yalnız use6 kolu close x 1,03 ile bağımsız ve zaten HAM:B001:54'te "
              "kodlandı). Ayrıca strategy_name uyuşmazlığı nedeniyle JSON yüklenmez (class sözlüğü esas)."},
    {"kimlik": "HAM:B001:78",
     "neden": "motorda ifade edilemiyor: giriş engeli BTC 1h RSI(8) < 35 ('BTC price protection', EI3v2_tag_cofi_green.py:553-554) ve BTC 5m/1h bilgi "
              "sütunları başka sembol verisi; strateji yalnız kendi mumlarını alır."},
    {"kimlik": "HAM:B001:755",
     "neden": "motorda ifade edilemiyor: rejim BTC/USDT 4h EWO(5,35) (BTC_EWO_Fast_4h; başka sembol verisi) üzerine kurulu, dört giriş kolu ve iki çıkış kolu "
              "bu rejime bağlı (eltoro1_4_simple.py:262-290, 496-561); ayrıca kısmi çıkış (adjust_trade_position) ve StoplossGuard korumaları var."},
]
