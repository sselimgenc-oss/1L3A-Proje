"""Kapanış turu, kodlama partisi g9_kod_4 (girdi: sonuclar/kapanis/kod_girdi/g9_kod_4.csv, 30 kaynak satırı, Robotic HAM:B001).

Her sınıf, satırın `kanit` sütunundaki kaynak dosyanın (RoboticAutomations/freqtradestrategies, bollinger / channels /
cycle-oscillators / heikin-ashi / ichimoku klasörleri) populate_entry/exit mantığından kendi cümlelerimle yazılmış bir
uyarlamadır; kaynak çalıştırılmadı, kod kopyalanmadı. Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor). Hepsi nedensel
(gelecek verisi yok); üst TF yalnız `motor.strateji.htf.ust_zaman` ile KAPANMIŞ mumdan alınır.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa (ya da <= -%50 ise) stop = kapanış - 3 x ATR(14) (ön kayıt uyarlaması); yüzde stoplar sinyal kapanışından.
- Freqtrade `minimal_roi` (dakika anahtarlı) `CikisAyarlari.azalan_roi` ile (mum = yukarı yuvarlanmış dakika / TF dakikası); "0" anahtarlı
  son basamak "kâr >= 0 ise çık" demektir; ROI {0: 100} (%10000) fiilen kapalıdır ama harfiyen yazıldı. Kapanışta sınanır, çıkış sonraki
  açılışta (kaynakta mum içi). `ignore_roi_if_buy_signal` motorda ifade edilemez (ROI giriş sinyali sürerken de uygulanır).
- `trailing_stop_positive` + offset -> `geri_cekilme_yuzde` (iz) + `geri_cekilme_min_kar_yuzde` (offset; `trailing_only_offset_is_reached=False`
  ise 0). Kâr basamaklı `custom_stoploss` kapanış bazlı `pozisyon_cikisi` kancasıyla (KancaDestek).
- Bollinger: motorun `gostergeler.bollinger` (ddof=0, qtpylib ddof=1 yerine); fiyat satırda "tipik" ise (H+L+C)/3. TA-Lib STOCH/STOCHF/MFI/CCI/
  SAR'ın karşılıkları motor göstergeleri ya da küçük yerel yazımlardır (SAR > kapanış == psar.yon == -1).
- Protections (StoplossGuard, LowProfitPairs, MaxDrawdown, CooldownPeriod) portföy katmanı kuralıdır; sinyale eklenmedi.
- `volume > 0` süzgeci `hacim > 0` olarak korundu.

KODLANAMADI satırları dosya sonundaki listededir (HAM:B001:543: BTC bilgi paritesi).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b2
from motor.strateji._gosterge_d11j import mfi as _mfi
from motor.strateji._gosterge_d11j import williams_r as _williams_r
from motor.strateji._gosterge_d11j import wma as _wma
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, roi_tablosu
from motor.strateji.temel import Strateji

yukari = b2.yukari_kesis
asagi = b2.asagi_kesis
_roi = roi_tablosu


# ---------------------------------------------------------------- yardımcılar
def _atr_mesafe(m: pd.DataFrame, n: int = 14, k: float = 3.0) -> pd.Series:
    return k * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], n)


def _bitir(sonuc: pd.DataFrame, cikis_long=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _tipik(m: pd.DataFrame) -> pd.Series:
    return (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0


def _hepsi(kosul: pd.Series, n: int) -> pd.Series:
    """Son n mumun (bu mum dahil) hepsinde koşul doğru mu."""
    return kosul.fillna(False).astype(float).rolling(n, min_periods=n).min() == 1.0


def _herhangi(kosul: pd.Series, n: int) -> pd.Series:
    """Son n mumun (bu mum dahil) en az birinde koşul doğru mu."""
    return kosul.fillna(False).astype(float).rolling(n, min_periods=n).max() == 1.0


def _stokf(m: pd.DataFrame, k: int = 5, d: int = 3) -> pd.DataFrame:
    """TA-Lib STOCHF karşılığı: fastk (ham %K) ve fastd (fastk'nın SMA'sı)."""
    st = g.stokastik(m["yuksek"], m["dusuk"], m["kapanis"], k, d)
    return pd.DataFrame({"k": st["k"], "d": st["d"]})


def _stok_yavas(m: pd.DataFrame, k: int = 5, d: int = 3, s: int = 3) -> pd.DataFrame:
    """TA-Lib STOCH karşılığı (SMA yumuşatma): slowk = SMA(fastk, d), slowd = SMA(slowk, s)."""
    st = g.stokastik(m["yuksek"], m["dusuk"], m["kapanis"], k, d)
    slowk = st["d"]
    return pd.DataFrame({"k": slowk, "d": g.sma(slowk, s)})


def _fisher_rsi(r: pd.Series) -> pd.Series:
    """0,1 x (RSI - 50) üzerinde (e^2x - 1)/(e^2x + 1) = tanh."""
    return np.tanh(0.1 * (r - 50.0))


def _ha(m: pd.DataFrame) -> pd.DataFrame:
    return b2.heikin_ashi(m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"])


def _t3(kap: pd.Series, n: int = 5, b: float = 0.7) -> pd.Series:
    """T3 ortalaması (6 ardışık EMA, hacim faktörü b)."""
    e = kap
    seri = []
    for _ in range(6):
        e = g.ema(e, n)
        seri.append(e)
    c1 = -b ** 3
    c2 = 3 * b ** 2 + 3 * b ** 3
    c3 = -6 * b ** 2 - 3 * b - 3 * b ** 3
    c4 = 1 + 3 * b + b ** 3 + 3 * b ** 2
    return c1 * seri[5] + c2 * seri[4] + c3 * seri[3] + c4 * seri[2]


def _ewo(kap: pd.Series, taban: pd.Series, hizli: int, yavas: int) -> pd.Series:
    """Elliott dalga osilatörü yüzdesi: (EMA hızlı - EMA yavaş) / taban x 100."""
    return (g.ema(kap, hizli) - g.ema(kap, yavas)) / taban * 100.0


def _tr_sma(m: pd.DataFrame, n: int) -> pd.Series:
    return g.gercek_aralik(m["yuksek"], m["dusuk"], m["kapanis"]).rolling(n, min_periods=n).mean()


def _ssl(yuk: pd.Series, dus: pd.Series, kap: pd.Series, n: int, atr: pd.Series | None = None):
    """SSL kanalı: ortalama yüksek/düşük (isteğe bağlı +/- ATR); kapanış üstü aşarsa hlv=+1, altını delerse -1, arada son değer.
    Dönen (ssl_down, ssl_up); hlv hiç belirlenmemişse (NaN) kaynaktaki gibi up = ortalama yüksek, down = ortalama düşük."""
    sh = yuk.rolling(n, min_periods=n).mean()
    sd = dus.rolling(n, min_periods=n).mean()
    if atr is not None:
        sh, sd = sh + atr, sd - atr
    hlv = pd.Series(np.where(kap > sh, 1.0, np.where(kap < sd, -1.0, np.nan)), index=kap.index).ffill()
    neg = (hlv < 0).to_numpy()
    down = pd.Series(np.where(neg, sh, sd), index=kap.index)
    up = pd.Series(np.where(neg, sd, sh), index=kap.index)
    return down, up


def _kademe_ihlali(kv: np.ndarray, bas: int, i: int, giris: float, kademeler: tuple) -> bool:
    """Kâr basamaklı iz süren stop (custom_stoploss), KAPANIŞ BAZLI. kademeler: ((kâr oranı eşiği, stop mesafe oranı), ...).
    Giriş mumundan (bas) i'ye her kapanış j için kâr p_j = kapanış_j / giriş - 1; p_j eşiği aşan en yüksek basamağın mesafesi d_j ile
    stop_j = kapanış_j x (1 - d_j) (basamak yoksa stop yok); stop yalnız yukarı taşınır (en büyük stop_j). Kapanış_i <= stop ise çık."""
    seg = kv[max(int(bas), 0):i + 1]
    if len(seg) == 0 or not np.isfinite(giris) or giris <= 0:
        return False
    p = seg / giris - 1.0
    d = np.ones(len(seg))
    for esik, mes in sorted(kademeler):
        d = np.where(p > esik, mes, d)
    stop = np.nanmax(seg * (1.0 - d))
    return bool(np.isfinite(stop) and kv[i] <= stop)


# ================================================================ HAM:B001:504 / 505
class FrostStokBb3B0504(Strateji):
    """HAM:B001:504 (15m, long; FrostAuraM3): RSI(14) > 22 VE yavaş stokastik (5,3,3) slowK < slowD VE kapanış < Bollinger(tipik, 20, 3s)
    alt bandı VE kapanış > 1,5e-6 -> long. Çıkış: slowK < slowD VE RSI > 72 VE kapanış > Bollinger(tipik, 20) orta bandı. ROI {0dk %18,418;
    36 %10,736; 91 %2,998; 438 0}; sabit stop -%41,114."""

    ad, stil = "kapanis__frost-stok-bb3-b0504", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_alt": 22.0, "rsi_cik": 72.0, "stok_k": 5, "stok_d": 3, "stok_s": 3,
                               "bb_n": 20, "bb_giris_k": 3.0, "min_fiyat": 1.5e-6, "sl": 0.41114}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.18418, 36: 0.10736, 91: 0.02998, 438: 0}, 15))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        st = _stok_yavas(mumlar, int(p["stok_k"]), int(p["stok_d"]), int(p["stok_s"]))
        tp = _tipik(mumlar)
        alt3 = g.bollinger(tp, int(p["bb_n"]), float(p["bb_giris_k"]))["alt"]
        orta = g.sma(tp, int(p["bb_n"]))
        ters = st["k"] < st["d"]
        sl = float(p["sl"])
        s = cerceve(mumlar, (r > float(p["rsi_alt"])) & ters & (kap < alt3) & (kap > float(p["min_fiyat"])), False,
                    kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, ters & (r > float(p["rsi_cik"])) & (kap > orta))


class FrostStokBb3B0505(FrostStokBb3B0504):
    """HAM:B001:505 (1h, long; FrostAuraM3 1h): 504 ile aynı kural; eşikler RSI > 10 (giriş), RSI > 70 (çıkış); ROI {0dk %23,044; 312 %16,026;
    870 %6,786; 2273 0}; sabit stop -%44,439."""

    ad, stil = "kapanis__frost-stok-bb3-b0505", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_alt": 10.0, "rsi_cik": 70.0, "stok_k": 5, "stok_d": 3, "stok_s": 3,
                               "bb_n": 20, "bb_giris_k": 3.0, "min_fiyat": 1.5e-6, "sl": 0.44439}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.23044, 312: 0.16026, 870: 0.06786, 2273: 0}, 60))


# ================================================================ HAM:B001:510
class GumboT3EwoB0510(Strateji):
    """HAM:B001:510 (5m, long; Gumbo1): EWO(EMA5 - EMA35, düşüğe bölünmüş, x100) < 0 VE 1h Bollinger(20; kapanış) orta bandı >= 1h T3(5) VE
    5m T3(5) <= EMA(30) -> long. Çıkış: stoch_sma(80) > 80 VEYA 5m T3(5) >= Bollinger(40) orta bandı (kapanış SMA40). stoch_sma = yavaş
    stokastik (pencere 80, 3/3 SMA) K ve D ortalamasının SMA(10)'u. ROI {0dk %10; 20 %5; 64 %3; 168 0}; sabit stop -%25.
    Uyarlama: 1h değerler htf.ust_zaman ile yalnız kapanmış 1h mumdan (kaynakta merge_informative_pair)."""

    ad, stil = "kapanis__gumbo-t3-ewo-b0510", "daytrade"
    varsayilan_parametreler = {"ewo_hizli": 5, "ewo_yavas": 35, "ewo_alt": 0.0, "t3_n": 5, "ema_n": 30, "ust_bb_n": 20,
                               "bb_cikis_n": 40, "stok_pencere": 80, "stok_ust": 80.0, "stok_yum": 10, "sl": 0.25}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.10, 20: 0.05, 64: 0.03, 168: 0}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ewo = _ewo(kap, mumlar["dusuk"], int(p["ewo_hizli"]), int(p["ewo_yavas"]))
        t3 = _t3(kap, int(p["t3_n"]))
        ust = ust_zaman(mumlar, "1h", lambda u: pd.DataFrame(
            {"bb_orta": g.sma(u["kapanis"], int(p["ust_bb_n"])), "t3": _t3(u["kapanis"], int(p["t3_n"]))}))
        st = _stok_yavas(mumlar, int(p["stok_pencere"]), 3, 3)
        stoch_sma = g.sma((st["k"] + st["d"]) / 2.0, int(p["stok_yum"]))
        al = (ewo < float(p["ewo_alt"])) & (ust["bb_orta"] >= ust["t3"]) & (t3 <= g.ema(kap, int(p["ema_n"])))
        cik = (stoch_sma > float(p["stok_ust"])) | (t3 >= g.sma(kap, int(p["bb_cikis_n"])))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ HAM:B001:514
class MontrealBbRsiB0514(Strateji):
    """HAM:B001:514 (15m, long; Montreal): RSI(14) > 30 VE kapanış < Bollinger(tipik, 20, 2s) alt bandı VE hacim > 0 -> long; çıkış: kapanış >
    Bollinger(tipik, 20, 2s) üst bandı VE hacim > 0. ROI {0dk %31,651; 79 %7,068; 147 %4,049; 345 0}; sabit stop -%28,646."""

    ad, stil = "kapanis__montreal-bb-rsi-b0514", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_alt": 30.0, "bb_n": 20, "bb_k": 2.0, "sl": 0.28646}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.31651, 79: 0.07068, 147: 0.04049, 345: 0}, 15))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        hv = mumlar["hacim"] > 0
        sl = float(p["sl"])
        s = cerceve(mumlar, (r > float(p["rsi_alt"])) & (kap < bb["alt"]) & hv, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, (kap > bb["ust"]) & hv)


# ================================================================ HAM:B001:515
class OnurBbOrtaB0515(Strateji):
    """HAM:B001:515 (15m, long; ONUR): RSI(14) < 74 VE kapanış > Bollinger(tipik, 20, 2s) orta bandı -> long (durum). Sinyal çıkışı yok. ROI
    {0dk %13,1; 109 %8; 226 %3}; iz süren %29,3 (offset %36,2, offset sonrası). Kaynak stopu -%99 (stopsuz): ATR(14)x3 felaket stopu."""

    ad, stil = "kapanis__onur-bb-orta-b0515", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_ust": 74.0, "bb_n": 20, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.131, 109: 0.08, 226: 0.03}, 15),
                                   geri_cekilme_yuzde=29.3, geri_cekilme_min_kar_yuzde=36.2)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        orta = g.sma(_tipik(mumlar), int(p["bb_n"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return cerceve(mumlar, (r < float(p["rsi_ust"])) & (kap > orta), False, kap - mes, kap + mes)


# ================================================================ HAM:B001:516 / 517
class RothMfiCciBbB0516(Strateji):
    """HAM:B001:516 (5m, long; Roth01): MFI(14) < 24 VE kapanış < Bollinger(tipik, 20, 2s) alt bandı VE CCI(14) <= -57 -> long. Çıkış: SAR >
    kapanış VE RSI(14) > 75 VE kapanış > Bollinger üst bandı VE CCI >= 83 VE MFI < 92. ROI {0dk %14,696; 29 %6,698; 75 %2,449; 181 0}; sabit
    stop -%29,585."""

    ad, stil = "kapanis__roth-mfi-cci-bb-b0516", "daytrade"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "mfi_n": 14, "mfi_alt": 24.0, "mfi_ust": 92.0, "cci_n": 14,
                               "cci_alt": -57.0, "cci_ust": 83.0, "rsi_n": 14, "rsi_ust": 75.0, "sl": 0.29585}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.14696, 29: 0.06698, 75: 0.02449, 181: 0}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        mf = _mfi(y, d, kap, mumlar["hacim"], int(p["mfi_n"]))
        cci = b2.cci(y, d, kap, int(p["cci_n"]))
        r = g.rsi(kap, int(p["rsi_n"]))
        sar_ust = g.psar(y, d)["yon"] == -1
        sl = float(p["sl"])
        s = cerceve(mumlar, (mf < float(p["mfi_alt"])) & (kap < bb["alt"]) & (cci <= float(p["cci_alt"])), False,
                    kap * (1 - sl), kap * (1 + sl))
        cik = (sar_ust & (r > float(p["rsi_ust"])) & (kap > bb["ust"]) & (cci >= float(p["cci_ust"]))
               & (mf < float(p["mfi_ust"])))
        return _bitir(s, cik)


class RothFastdMfiBbB0517(Strateji):
    """HAM:B001:517 (5m, long; Roth03): kapanış < Bollinger(tipik, 20, 2s) alt bandı VE fastD (STOCHF 5,3) > 37 VE MFI(14) < 20 -> long. Çıkış:
    SAR > kapanış VE RSI(14) > 69 VE MFI > 86 VE fastD > 79. ROI {0dk %24,553; 33 %7,203; 90 %1,452; 111 0}; sabit stop -%31,939."""

    ad, stil = "kapanis__roth-fastd-mfi-bb-b0517", "daytrade"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "mfi_n": 14, "mfi_alt": 20.0, "mfi_ust": 86.0, "fastd_alt": 37.0,
                               "fastd_ust": 79.0, "rsi_n": 14, "rsi_ust": 69.0, "sl": 0.31939}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.24553, 33: 0.07203, 90: 0.01452, 111: 0}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        mf = _mfi(y, d, kap, mumlar["hacim"], int(p["mfi_n"]))
        fd = _stokf(mumlar)["d"]
        r = g.rsi(kap, int(p["rsi_n"]))
        sar_ust = g.psar(y, d)["yon"] == -1
        sl = float(p["sl"])
        s = cerceve(mumlar, (kap < bb["alt"]) & (fd > float(p["fastd_alt"])) & (mf < float(p["mfi_alt"])), False,
                    kap * (1 - sl), kap * (1 + sl))
        cik = sar_ust & (r > float(p["rsi_ust"])) & (mf > float(p["mfi_ust"])) & (fd > float(p["fastd_ust"]))
        return _bitir(s, cik)


# ================================================================ HAM:B001:518
class SmaBbrsiEwoB0518(KancaDestek, Strateji):
    """HAM:B001:518 (5m, long; SMA_BBRSI): EMA ofset + EWO + RSI-bant kolları (VEYA). Kaynak dosyadan: EWO = (EMA50 - EMA200) / kapanış x 100;
    ma_al = EMA(16), ma_sat = EMA(20). Giriş: (a) kapanış < ma_al x 0,973 VE EWO > 5,672 VE RSI14 < 59; (b) kapanış < ma_al x 0,973 VE EWO < -19,931;
    (c) RSI14 < EMA22(RSI) - 1,74 x STD22(RSI) VE ((4,86 < EWO < 10) VEYA (EWO >= 10 VE RSI < 40)) VE RSI(4) < 25 VE CCI(20) < 100 VE moderi_96
    (VWMA96'nın EMA96'sı yükseliyor); hepsi hacim > 0. Anti-pump: (ZEMA30 - ZEMA200)/ZEMA30 > 0,25 ise giriş yok (ZEMA = EMA + (EMA - EMA(EMA)),
    kaynak kütüphane tanımı kendi okumam). Çıkış: (kapanış > ma_sat x 1,01) VEYA (((RSI > 72 VEYA RSI > EMA65(RSI) + 1,895 x STD65(RSI)) VE moderi_96) VEYA
    kapanış ATR-yüksek [(yüksek - 3,5 x ATR14)'in 2 mumluk en büyüğü] çizgisini aşağı keser), hacim > 0. ROI {0dk %2,8; 10 %1,8; 30 %1; 40 %0,5}.
    Başlangıç stopu custom_stoploss HSL -%17,8 (sinyal kapanışından); kâr basamakları kancada, kapanış bazlı: zirve kâr > %1 ise stop kâr
    %0,9 ile %4,3 arası doğrusal (PF1 %1, SL1 %0,9; PF2 %4,8, SL2 %4,3; üstünde kâr - %0,5); kâr zirveden hesaplanan stop kârına inerse çık."""

    ad, stil = "kapanis__sma-bbrsi-ewo-b0518", "daytrade"
    varsayilan_parametreler = {"ma_al_n": 16, "ma_sat_n": 20, "dusuk_ofset": 0.973, "yuksek_ofset": 1.01, "ewo_hizli": 50,
                               "ewo_yavas": 200, "ewo_yuksek": 5.672, "ewo_alt": -19.931, "ewo_yuksek_bb": 4.86, "rsi_al": 59.0,
                               "rsi_yuksek": 72.0, "rsi_n": 14, "rsi_kisa_n": 4, "rsi_kisa_ust": 25.0, "bb_ma_al": 22,
                               "bb_sigma_al": 1.74, "bb_ma_sat": 65, "bb_sigma_sat": 1.895, "cci_n": 20, "cci_ust": 100.0,
                               "moderi_n": 96, "pump_hizli": 30, "pump_yavas": 200, "pump_esik": 0.25, "atr_n": 14,
                               "atr_k": 3.5, "hsl": 0.178, "pf1": 0.01, "sl1": 0.009, "pf2": 0.048, "sl2": 0.043}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.028, 10: 0.018, 30: 0.010, 40: 0.005}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def _zema(kap: pd.Series, n: int) -> pd.Series:
        e1 = g.ema(kap, n)
        return e1 + (e1 - g.ema(e1, n))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, y, d, hc = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["hacim"]
        hv = hc > 0
        r = g.rsi(kap, int(p["rsi_n"]))
        r4 = g.rsi(kap, int(p["rsi_kisa_n"]))
        ewo = _ewo(kap, kap, int(p["ewo_hizli"]), int(p["ewo_yavas"]))

        def bant(n: int):
            return g.ema(r, n), r.rolling(n, min_periods=n).std(ddof=0)

        b_al, s_al = bant(int(p["bb_ma_al"]))
        b_sat, s_sat = bant(int(p["bb_ma_sat"]))
        vw = (kap * hc).rolling(int(p["moderi_n"]), min_periods=int(p["moderi_n"])).mean() / \
            hc.rolling(int(p["moderi_n"]), min_periods=int(p["moderi_n"])).mean()
        yavas = g.ema(vw, int(p["moderi_n"]))
        moderi = yavas >= yavas.shift(1)
        cci_h = b2.cci(y, d, kap, int(p["cci_n"]))
        z30, z200 = self._zema(kap, int(p["pump_hizli"])), self._zema(kap, int(p["pump_yavas"]))
        pump = (z30 - z200) / z30
        ma_al, ma_sat = g.ema(kap, int(p["ma_al_n"])), g.ema(kap, int(p["ma_sat_n"]))
        alt_ofset = kap < ma_al * float(p["dusuk_ofset"])
        a = alt_ofset & (ewo > float(p["ewo_yuksek"])) & (r < float(p["rsi_al"])) & hv
        b = alt_ofset & (ewo < float(p["ewo_alt"])) & hv
        ewo_bb = ((ewo > float(p["ewo_yuksek_bb"])) & (ewo < 10.0)) | ((ewo >= 10.0) & (r < 40.0))
        c = ((r < b_al - s_al * float(p["bb_sigma_al"])) & ewo_bb & (r4 < float(p["rsi_kisa_ust"])) & hv
             & (cci_h < float(p["cci_ust"])) & moderi)
        al = (a | b | c) & ~(pump > float(p["pump_esik"]))
        atr = g.atr(y, d, kap, int(p["atr_n"]))
        atr_yuksek = (y - atr * float(p["atr_k"])).rolling(2, min_periods=2).max()
        cik1 = (kap > ma_sat * float(p["yuksek_ofset"])) & hv
        cik2 = ((((r > float(p["rsi_yuksek"])) | (r > b_sat + s_sat * float(p["bb_sigma_sat"]))) & moderi)
                | asagi(kap, atr_yuksek)) & hv
        hsl = float(p["hsl"])
        self._sakla(kap=kap)
        s = cerceve(mumlar, al, False, kap * (1 - hsl), kap * (1 + hsl))
        return _bitir(s, cik1 | cik2)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi) or not np.isfinite(d.giris_fiyati) or d.giris_fiyati <= 0:
            return False
        p = self.parametreler
        seg = self._kd["kap"][max(d.giris_mum_indeksi, 0):d.mum_indeksi + 1]
        if len(seg) == 0:
            return False
        zirve = float(np.nanmax(seg)) / d.giris_fiyati - 1.0
        pf1, pf2, sl1, sl2 = float(p["pf1"]), float(p["pf2"]), float(p["sl1"]), float(p["sl2"])
        if zirve <= pf1:
            return False            # HSL bölgesi: başlangıç stopu (sinyaldeki stop) korur
        if zirve > pf2:
            sl_kar = sl2 + (zirve - pf2)
        else:
            sl_kar = sl1 + (zirve - pf1) * (sl2 - sl1) / (pf2 - pf1)
        return d.kar_yuzde / 100.0 <= sl_kar


# ================================================================ HAM:B001:519 / 520
class RsiSinirBbB0519(Strateji):
    """HAM:B001:519 (5m, long; STRATEGY_RSI_BB_BOUNDS_CROSS): Bollinger(tipik, 14, 2s) alt bandı, "RSI(14)=30 olduran fiyat" sınırının (rsi_lb)
    altında; bu son 14 mumun hepsinde (şimdiki dahil) VE bir önceki mumda da doğru VE EMA(2) yükseliyor -> long. rsi_lb: auc/adc = EMA(27)
    (yükseliş/düşüş farkları); x2 = 13 x (adc x 30/70 - auc); rsi_lb = kapanış + x2 (x2 >= 0) ya da kapanış + x2 x 70/30. Çıkış: EMA(2)
    düşüyor. ROI {0dk %4; 30 %2; 60 %1}; sabit stop -%10."""

    ad, stil = "kapanis__rsi-sinir-bb-b0519", "daytrade"
    varsayilan_parametreler = {"bb_n": 14, "bb_k": 2.0, "rsi_n": 14, "rsi_seviye": 30.0, "trend_n": 14, "ema_n": 2, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.04, 30: 0.02, 60: 0.01}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        n = int(p["rsi_n"])
        ep = 2 * n - 1
        fark = kap.diff()
        auc = g.ema(fark.clip(lower=0.0), ep)
        adc = g.ema((-fark).clip(lower=0.0), ep)
        sv = float(p["rsi_seviye"])
        x2 = (n - 1) * (adc * sv / (100.0 - sv) - auc)
        rsi_lb = kap + np.where(x2 >= 0, x2, x2 * (100.0 - sv) / sv)
        rsi_lb = pd.Series(rsi_lb, index=kap.index).where(x2.notna())
        bb_lb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))["alt"]
        alt = bb_lb < rsi_lb
        ema = g.ema(kap, int(p["ema_n"]))
        al = _hepsi(alt, int(p["trend_n"])) & alt & alt.shift(1, fill_value=False) & (ema > ema.shift(1))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), ema < ema.shift(1))


class BbRsiYuzdeKesisB0520(Strateji):
    """HAM:B001:520 (5m, long; STRATEGY_RSI_BB_CROSS): bb_percent = (kapanış - alt)/(üst - alt), Bollinger(tipik, 20, 2s); rsi_percent = (RSI14 - 30)/40.
    Giriş: bb_percent rsi_percent'i yukarı keser VE ikisi de < 0,5 VE önceki mumda son 14 mumun hepsinde bb_percent < rsi_percent. Çıkış: aşağı
    keser VE ikisi de > 0,5 VE önceki mumda son 14 mumun hepsinde bb_percent > rsi_percent. ROI {0dk %4; 30 %2; 60 %1}; sabit stop -%10."""

    ad, stil = "kapanis__bb-rsi-yuzde-kesis-b0520", "daytrade"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "rsi_n": 14, "rsi_limit": 30.0, "trend_n": 14, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.04, 30: 0.02, 60: 0.01}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        bbp = (kap - bb["alt"]) / (bb["ust"] - bb["alt"])
        lim = float(p["rsi_limit"])
        rsp = (g.rsi(kap, int(p["rsi_n"])) - lim) / (100.0 - 2 * lim)
        n = int(p["trend_n"])
        alti = _hepsi(bbp < rsp, n).shift(1, fill_value=False)
        ustu = _hepsi(bbp > rsp, n).shift(1, fill_value=False)
        al = yukari(bbp, rsp) & (bbp < 0.5) & (rsp < 0.5) & alti
        cik = asagi(bbp, rsp) & (bbp > 0.5) & (rsp > 0.5) & ustu
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ HAM:B001:529
class PullbackDipKirilimB0529(Strateji):
    """HAM:B001:529 (5m, long; TheRealPullbackV2): dip: RMI(8, mom 4) < 20 VE CCI(30) <= -150 VE StochRSI(RSI15, pencere 20) fastK < 20 VE MFI(14) < 25
    VE CMF(20) <= -0,1; kırılım: Bollinger(KAPANIŞ, 20, 2s) genişlik (üst-alt)/orta > 0,025 VE son 10 mumda kapanışın alt bandı aşağı kesme sayısı > 1 VE
    kapanış < 0,99 x alt bant; ikisi birden -> long. Çıkış: kapanış orta VEYA üst bandı aşağı keser. ROI {0: 100} (kapalı); sabit stop -%3,5.
    RMI: (kapanış - 4 mum önceki) farkının pozitif/negatif kısımlarının EMA(8) oranı; EMA'sı 0 ise 0."""

    ad, stil = "kapanis__pullback-dip-kirilim-b0529", "daytrade"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "genislik": 0.025, "kesis_pencere": 10, "kirilim_carpan": 0.99,
                               "rmi_n": 8, "rmi_mom": 4, "rmi_ust": 20.0, "cci_n": 30, "cci_ust": -150.0, "srsi_rsi_n": 15,
                               "srsi_pencere": 20, "srsi_ust": 20.0, "mfi_n": 14, "mfi_ust": 25.0, "cmf_n": 20, "cmf_ust": -0.1,
                               "sl": 0.035}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 100}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, y, d, hc = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["hacim"]
        bb = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        genislik = (bb["ust"] - bb["alt"]) / bb["orta"]
        kesis = asagi(kap, bb["alt"])
        # RMI
        mom = kap - kap.shift(int(p["rmi_mom"]))
        ei = g.ema(mom.clip(lower=0.0).fillna(0.0), int(p["rmi_n"]))
        ed = g.ema((-mom).clip(lower=0.0).fillna(0.0), int(p["rmi_n"]))
        with np.errstate(divide="ignore", invalid="ignore"):
            rmi = (100.0 - 100.0 / (1.0 + ei / ed)).where(ed != 0, 0.0)
        # StochRSI fastK
        r = g.rsi(kap, int(p["srsi_rsi_n"]))
        rn = int(p["srsi_pencere"])
        lo, hi = r.rolling(rn, min_periods=rn).min(), r.rolling(rn, min_periods=rn).max()
        srsi = 100.0 * (r - lo) / (hi - lo).where(lambda x: x > 0)
        # CMF
        aralik = (y - d).where(lambda x: x > 0)
        mfv = (((kap - d) - (y - kap)) / aralik).fillna(0.0) * hc
        cn = int(p["cmf_n"])
        cmf = mfv.rolling(cn, min_periods=cn).sum() / hc.rolling(cn, min_periods=cn).sum()
        dip = ((rmi < float(p["rmi_ust"])) & (b2.cci(y, d, kap, int(p["cci_n"])) <= float(p["cci_ust"]))
               & (srsi < float(p["srsi_ust"])) & (_mfi(y, d, kap, hc, int(p["mfi_n"])) < float(p["mfi_ust"]))
               & (cmf <= float(p["cmf_ust"])))
        kw = int(p["kesis_pencere"])
        kirilim = ((genislik > float(p["genislik"])) & (kesis.astype(float).rolling(kw, min_periods=kw).sum() > 1)
                   & (kap < float(p["kirilim_carpan"]) * bb["alt"]))
        sl = float(p["sl"])
        s = cerceve(mumlar, dip & kirilim, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, asagi(kap, bb["orta"]) | asagi(kap, bb["ust"]))


# ================================================================ HAM:B001:531
class AdxBbFastdB0531(Strateji):
    """HAM:B001:531 (1h, long; adxbbrsi2): ADX(14) > 47 VE fastD (STOCHF 5,3) < 41 VE kapanış < Bollinger(tipik, 20, 2s) alt bandı -> long. Çıkış: ADX > 67
    VE MFI(14) > 97 VE fastD < 74. ROI {0dk %16,083; 33 %4,139; 85 %1,225; 197 0}; sabit stop -%32,237; iz süren %11,95 (offset %15,68, offset sonrası)."""

    ad, stil = "kapanis__adx-bb-fastd-b0531", "swing"
    varsayilan_parametreler = {"adx_n": 14, "adx_giris": 47.0, "adx_cikis": 67.0, "fastd_giris": 41.0, "fastd_cikis": 74.0,
                               "mfi_n": 14, "mfi_cikis": 97.0, "bb_n": 20, "bb_k": 2.0, "sl": 0.32237}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.16083, 33: 0.04139, 85: 0.01225, 197: 0}, 60),
                                   geri_cekilme_yuzde=11.95, geri_cekilme_min_kar_yuzde=15.68)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        adx = g.adx(y, d, kap, int(p["adx_n"]))["adx"]
        fd = _stokf(mumlar)["d"]
        alt = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))["alt"]
        mf = _mfi(y, d, kap, mumlar["hacim"], int(p["mfi_n"]))
        sl = float(p["sl"])
        s = cerceve(mumlar, (adx > float(p["adx_giris"])) & (fd < float(p["fastd_giris"])) & (kap < alt), False,
                    kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, (adx > float(p["adx_cikis"])) & (mf > float(p["mfi_cikis"])) & (fd < float(p["fastd_cikis"])))


# ================================================================ HAM:B001:534
class Bb3AltB0534(Strateji):
    """HAM:B001:534 (1h, long; bbrsi4Freq): kapanış < Bollinger(tipik, 20, 3s) alt bandı -> long; çıkış: kapanış > Bollinger(tipik, 20, 1s) alt bandı
    (neredeyse sürekli doğru: pozisyon fiilen bir sonraki mumda kapanır). ROI {0dk %18,656; 21 %9,694; 73 %3,081; 180 0}; sabit stop -%36,727; iz süren
    %32,349 (offset %34,683, offset sonrası)."""

    ad, stil = "kapanis__bb3-alt-b0534", "swing"
    varsayilan_parametreler = {"bb_n": 20, "giris_k": 3.0, "cikis_k": 1.0, "sl": 0.36727}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.18656, 21: 0.09694, 73: 0.03081, 180: 0}, 60),
                                   geri_cekilme_yuzde=32.349, geri_cekilme_min_kar_yuzde=34.683)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tp = _tipik(mumlar)
        alt3 = g.bollinger(tp, int(p["bb_n"]), float(p["giris_k"]))["alt"]
        alt1 = g.bollinger(tp, int(p["bb_n"]), float(p["cikis_k"]))["alt"]
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, kap < alt3, False, kap * (1 - sl), kap * (1 + sl)), kap > alt1)


# ================================================================ HAM:B001:538
class KeltnerKirilimB0538(Strateji):
    """HAM:B001:538 (6h, long; keltnerchannel): Keltner kanalı (orta = SMA20 tipik fiyat, bant = orta +/- 1 x SMA20(gerçek aralık)); kapanış üst bandı yukarı
    keser VE RSI(14) > 55 -> long. Çıkış: kapanış orta bandı aşağı keser. ROI {0: 100} (kapalı); sabit stop -%25,4."""

    ad, stil = "kapanis__keltner-kirilim-b0538", "swing"
    varsayilan_parametreler = {"kc_n": 20, "kc_k": 1.0, "rsi_n": 14, "rsi_esik": 55.0, "sl": 0.254}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 100}, 360))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        orta = g.sma(_tipik(mumlar), int(p["kc_n"]))
        ust = orta + float(p["kc_k"]) * _tr_sma(mumlar, int(p["kc_n"]))
        r = g.rsi(kap, int(p["rsi_n"]))
        sl = float(p["sl"])
        s = cerceve(mumlar, yukari(kap, ust) & (r > float(p["rsi_esik"])), False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, asagi(kap, orta))


# ================================================================ HAM:B001:541
class BesMumDipRsiB0541(Strateji):
    """HAM:B001:541 (1h, long; Divergences): "boğa diverjansı" = 5 mumluk fiyat dibi: kapanış[t-4] > kapanış[t-2] VE kapanış[t-3] > kapanış[t-2] VE
    kapanış[t-2] < kapanış[t-1] VE kapanış[t-2] < kapanış[t] (gerçek RSI diverjansı yok); RSI(14) <= 40 ile birlikte -> long. Çıkış: "ayı diverjansı" (aynı
    kalıbın tepe versiyonu). ROI {0: %100}; sabit stop -%10; iz süren %5 (offset %20, offset sonrası)."""

    ad, stil = "kapanis__bes-mum-dip-rsi-b0541", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_ust": 40.0, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 1}, 60), geri_cekilme_yuzde=5.0, geri_cekilme_min_kar_yuzde=20.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        c1, c2, c3, c4 = kap.shift(1), kap.shift(2), kap.shift(3), kap.shift(4)
        dip = (c4 > c2) & (c3 > c2) & (c2 < c1) & (c2 < kap)
        tepe = (c4 < c2) & (c3 < c2) & (c2 > c1) & (c2 > kap)
        r = g.rsi(kap, int(p["rsi_n"]))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, (r <= float(p["rsi_ust"])) & dip, False, kap * (1 - sl), kap * (1 + sl)), tepe)


# ================================================================ HAM:B001:542
class FisherCciSslB0542(Strateji):
    """HAM:B001:542 (1h, long; Inverse): Fisher-CCI = tanh(WMA9(0,1 x CCI(31)/4)). Giriş: Fisher-CCI -0,42'yi yukarı keser VEYA (son 8 mumda 0,41'i aşağı
    kesmiş VE şimdi 0,41'i yukarı keser); VE 4h SSL(20; ATR14 ile) up > down VE 1h EMA50 > EMA200 VE 4h EMA50 > EMA100 VE 4h EMA50 > EMA200 (4h değerler
    htf.ust_zaman ile kapanmış 4h mumdan); hacim > 0. Çıkış: Fisher-CCI 0,42'yi VEYA -0,34'ü aşağı keser (hacim > 0); kaynaktaki confirm_trade_exit
    süzgeci: DI(3) +DI > -DI VE ADX(3) yükseliyorsa sinyal çıkışı yapılmaz. ROI {0: 100} (kapalı); sabit stop -%20; iz süren %7,8 (trailing_only_offset
    False: harfiyen min kâr 0; Freqtrade'de offset öncesi iz mesafesi stoploss'tur, burada ekip eşlemesi uygulandı)."""

    ad, stil = "kapanis__fisher-cci-ssl-b0542", "swing"
    varsayilan_parametreler = {"fisher_uzun": 31, "fisher_wma": 9, "giris_1": -0.42, "giris_2": 0.41, "cikis_1": 0.42, "cikis_2": -0.34,
                               "geri_bak": 8, "ema_a": 50, "ema_b": 200, "ust_tf": "4h", "ust_ema_b": 100, "ssl_n": 20,
                               "atr_n": 14, "adx_n": 3, "sl": 0.20}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 100}, 60), geri_cekilme_yuzde=7.8, geri_cekilme_min_kar_yuzde=0.0)

    def cikis_var_mi(self) -> bool:
        return True

    def _fisher(self, mumlar: pd.DataFrame) -> pd.Series:
        p = self.parametreler
        cci = b2.cci(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], int(p["fisher_uzun"]))
        return np.tanh(_wma(0.1 * (cci / 4.0), int(p["fisher_wma"])))

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        f = self._fisher(mumlar)

        def ust_f(u):
            atr = g.atr(u["yuksek"], u["dusuk"], u["kapanis"], int(p["atr_n"]))
            dn, up = _ssl(u["yuksek"], u["dusuk"], u["kapanis"], int(p["ssl_n"]), atr)
            e_a, e_b, e_c = (g.ema(u["kapanis"], int(p[k])) for k in ("ema_a", "ust_ema_b", "ema_b"))
            ok = ((up > dn) & (e_a > e_b) & (e_a > e_c)) & up.notna() & dn.notna()
            return pd.DataFrame({"ok": ok.astype(float), "gecerli": (e_c.notna() & up.notna()).astype(float)})

        ust = ust_zaman(mumlar, str(p["ust_tf"]), ust_f)
        ust_ok = (ust["ok"] == 1.0) & (ust["gecerli"] == 1.0)
        hv = mumlar["hacim"] > 0
        gir = yukari(f, float(p["giris_1"])) | (
            _herhangi(asagi(f, float(p["giris_2"])), int(p["geri_bak"])) & yukari(f, float(p["giris_2"])))
        al = gir & ust_ok & (g.ema(kap, int(p["ema_a"])) > g.ema(kap, int(p["ema_b"]))) & hv
        sat = (asagi(f, float(p["cikis_1"])) | asagi(f, float(p["cikis_2"]))) & hv
        ad_ = g.adx(y, d, kap, int(p["adx_n"]))
        veto = (ad_["arti_di"] > ad_["eksi_di"]) & (ad_["adx"] > ad_["adx"].shift(1))
        sl = float(p["sl"])
        s = cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, sat & ~veto)


# ================================================================ HAM:B001:544
class KcBbHaB0544(KancaDestek, Strateji):
    """HAM:B001:544 (5m, long; KC_BB): Keltner alt bandı (SMA28 - 1 x SMA28(TR)) Bollinger(tipik, 20, 2s) alt-üst arasında VE (KC(SMA20 - 2 x SMA20(TR)) alt - BB alt) /
    BB alt x 100 in (0,928; 1,5) VE Williams %R(14) in (-90; -80) VE |HA kapanış farkı| > HA kapanış x 0,008 -> long. Çıkış: Fisher-RSI (0,1 x (RSI-50) tanh) >
    0,39075 VE HA yüksek 2 mum düşüyor/eşit VE HA kapanış önceki HA kapanıştan büyük değil VE EMA3(HA kapanış) > HA kapanış VE HA kapanış x 0,99754 >
    BB orta bandı VE hacim > 0. ROI {0: %2050} (kapalı). Kaynak stopu yok (-%99): ATR(14)x3 felaket stopu. custom_stoploss (kâr > %3: kapanıştan %1,5; > %6: %2;
    > %10: %3; > %20: %5 geride iz süren) kapanış bazlı kancada, stop yalnız yukarı taşınır."""

    ad, stil = "kapanis__kc-bb-ha-b0544", "daytrade"
    varsayilan_parametreler = {"kc_n_uzun": 28, "kc_k_uzun": 1.0, "kc_n": 20, "kc_k": 2.0, "bb_n": 20, "bb_k": 2.0, "delta_alt": 0.928,
                               "delta_ust": 1.5, "wr_n": 14, "wr_alt": -90.0, "wr_ust": -80.0, "ha_delta": 0.008, "rsi_n": 14,
                               "fisher_esik": 0.39075, "ema_n": 3, "bb_orta_carpan": 0.99754, "atr_n": 14, "atr_k": 3.0,
                               "kademeler": ((0.03, 0.015), (0.06, 0.02), (0.10, 0.03), (0.20, 0.05))}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 20.5}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        bb = g.bollinger(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))
        kc_uzun_alt = g.sma(kap, int(p["kc_n_uzun"])) - float(p["kc_k_uzun"]) * _tr_sma(mumlar, int(p["kc_n_uzun"]))
        kc_alt = g.sma(kap, int(p["kc_n"])) - float(p["kc_k"]) * _tr_sma(mumlar, int(p["kc_n"]))
        delta = (kc_alt - bb["alt"]) / bb["alt"] * 100.0
        wr = _williams_r(y, d, kap, int(p["wr_n"]))
        ha = _ha(mumlar)
        hk, hy = ha["ha_kapanis"], ha["ha_yuksek"]
        hdelta = (hk - hk.shift(1)).abs()
        al = ((kc_uzun_alt < bb["ust"]) & (kc_uzun_alt > bb["alt"]) & (delta < float(p["delta_ust"]))
              & (delta > float(p["delta_alt"])) & (wr < float(p["wr_ust"])) & (wr > float(p["wr_alt"]))
              & (hdelta > hk * float(p["ha_delta"])))
        fisher = _fisher_rsi(g.rsi(kap, int(p["rsi_n"])))
        cik = ((fisher > float(p["fisher_esik"])) & (hy <= hy.shift(1)) & (hy.shift(1) <= hy.shift(2)) & (hk <= hk.shift(1))
               & (g.ema(hk, int(p["ema_n"])) > hk) & (hk * float(p["bb_orta_carpan"]) > bb["orta"]) & (mumlar["hacim"] > 0))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        self._sakla(kap=kap)
        return _bitir(cerceve(mumlar, al, False, kap - mes, kap + mes), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        return _kademe_ihlali(self._kd["kap"], d.giris_mum_indeksi, d.mum_indeksi, d.giris_fiyati,
                              tuple(self.parametreler["kademeler"]))


# ================================================================ HAM:B001:549
class FisherRsiHacimB0549(Strateji):
    """HAM:B001:549 (5m, long; quantumfirst): kapanış > 2e-6 VE hacim > 4 x SMA200(hacim) VE kapanış < SMA(40) VE fastD (STOCHF) > fastK VE RSI(14) > 0 VE
    fastD > 0 VE Fisher-RSI normalize (50 x (tanh(0,1 x (RSI-50)) + 1)) < 38,9 -> long. Çıkış: (RSI 50'yi yukarı keser VE MACD(12,26,9) < 0 VE -DI(14) > 0) VEYA
    (SAR > kapanış VE Fisher-RSI > 0,3); yalnız kârda (exit_profit_only). ROI {0dk %5; 20 %4; 40 %3; 80 %2; 1440 %1}; sabit stop -%10; trailing_stop kapalı."""

    ad, stil = "kapanis__fisher-rsi-hacim-b0549", "daytrade"
    varsayilan_parametreler = {"min_fiyat": 2e-6, "hacim_n": 200, "hacim_k": 4.0, "sma_n": 40, "rsi_n": 14, "fisher_norma": 38.9,
                               "rsi_kesis": 50.0, "fisher_cik": 0.3, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.05, 20: 0.04, 40: 0.03, 80: 0.02, 1440: 0.01}, 5),
                                   yalniz_karda_cikis=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, y, d, hc = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["hacim"]
        r = g.rsi(kap, int(p["rsi_n"]))
        fisher = _fisher_rsi(r)
        norma = 50.0 * (fisher + 1.0)
        sf = _stokf(mumlar)
        hn = int(p["hacim_n"])
        al = ((kap > float(p["min_fiyat"])) & (hc > hc.rolling(hn, min_periods=hn).mean() * float(p["hacim_k"]))
              & (kap < g.sma(kap, int(p["sma_n"]))) & (sf["d"] > sf["k"]) & (r > 0) & (sf["d"] > 0)
              & (norma < float(p["fisher_norma"])))
        mc = g.macd(kap)
        eksi_di = g.adx(y, d, kap, 14)["eksi_di"]
        sar_ust = g.psar(y, d)["yon"] == -1
        cik = (yukari(r, float(p["rsi_kesis"])) & (mc["macd"] < 0) & (eksi_di > 0)) | (sar_ust & (fisher > float(p["fisher_cik"])))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ HAM:B001:610
class HaEgimTahminB0610(Strateji):
    """HAM:B001:610 (5m, long; HSI): Heikin-Ashi açılış/kapanış eğimleri (bir önceki HA değerine fark) ve tahminleri (HA + eğim; bir mum geriden kullanılır).
    Giriş: (önceki HA açılış tahmini < önceki HAM açılış VE açılış > o tahmin VE HA açılış eğimi > 0 VE HA kapanış eğimi > 0 VE kapanış > önceki HA kapanış
    tahmini) VEYA (HA kapanış eğimi önceki mumda < 0, şimdi > 0). Çıkış: (HA kapanış eğimi önceki > 0, şimdi < 0) VEYA ayna kural (aşağı yön). Karşılaştırmalar
    kaynaktaki gibi HAM açılış/kapanışla. ROI {0dk %1,5}; sabit stop -%1."""

    ad, stil = "kapanis__ha-egim-tahmin-b0610", "daytrade"
    varsayilan_parametreler = {"sl": 0.01}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.015}, 5))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, ac = mumlar["kapanis"], mumlar["acilis"]
        ha = _ha(mumlar)
        ho, hk = ha["ha_acilis"], ha["ha_kapanis"]
        ho_e, hk_e = ho - ho.shift(1), hk - hk.shift(1)
        ho_t, hk_t = (ho + ho_e).shift(1), (hk + hk_e).shift(1)
        al = (((ho_t < ac.shift(1)) & (ac > ho_t) & (ho_e > 0) & (hk_e > 0) & (kap > hk_t))
              | ((hk_e.shift(1) < 0) & (hk_e > 0)))
        cik = (((hk_e.shift(1) > 0) & (hk_e < 0))
               | ((ho_t > ac.shift(1)) & (ac < ho_t) & (ho_e < 0) & (hk_e < 0) & (kap < hk_t)))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ HAM:B001:614
class HaSslMomMacdB0614(Strateji):
    """HAM:B001:614 (1h, long; cryptohassle): Heikin-Ashi mumları üzerinde: SSL kanalı(10; HA yüksek/düşük ortalaması, HA kapanışla yön) up'ın down'u
    yukarı kesmesi, momentum(14; HA kapanış farkı) 0'ı yukarı kesmesi, MACD(12,26,9; HA kapanış) sinyali yukarı kesmesi: son 5 mumda (şimdiki dahil) her
    biri en az bir kez gerçekleşmiş VE hacim > 1000 -> long. Çıkış: SSL up down'ı aşağı keser (hacim > 0). ROI {0dk %50}; sabit stop -%20; iz süren %1 (offset
    %7, offset sonrası). Uyarlama: hacim eşiği 1000, sembolün hacim biriminde (baz coin) harfiyen."""

    ad, stil = "kapanis__ha-ssl-mom-macd-b0614", "swing"
    varsayilan_parametreler = {"ssl_n": 10, "mom_n": 14, "pencere": 5, "hacim_alt": 1000.0, "sl": 0.20}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.50}, 60), geri_cekilme_yuzde=1.0, geri_cekilme_min_kar_yuzde=7.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ha = _ha(mumlar)
        hk = ha["ha_kapanis"]
        mom = hk - hk.shift(int(p["mom_n"]))
        mc = g.macd(hk)
        dn, up = _ssl(ha["ha_yuksek"], ha["ha_dusuk"], hk, int(p["ssl_n"]))
        w = int(p["pencere"])
        al = (_herhangi(yukari(up, dn), w) & _herhangi(yukari(mom, 0.0), w) & _herhangi(yukari(mc["macd"], mc["sinyal"]), w)
              & (mumlar["hacim"] > float(p["hacim_alt"])))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), asagi(up, dn) & (mumlar["hacim"] > 0))


# ================================================================ HAM:B001:621
def _kesisim_skoru(x, y, x1, y1, sa, sb) -> np.ndarray:
    """Ichess çapraz skoru: x, y'yi yukarı keserse kesişim noktası bulutun üstündeyse 2, altındaysa 0,5, içindeyse 1; aşağı keserse sırasıyla -0,5 / -2 / -1."""
    with np.errstate(divide="ignore", invalid="ignore"):
        kes = (x1 * (y - y1) - y1 * (x - x1)) / ((y - y1) - (x - x1))
        ust, alt = (kes > sa) & (kes > sb), (kes < sa) & (kes < sb)
        yk, ak = (x > y) & (x1 <= y1), (x < y) & (x1 >= y1)
    sk = np.zeros(len(x))
    sk = np.where(yk, np.where(ust, 2.0, np.where(alt, 0.5, 1.0)), sk)
    sk = np.where(ak, np.where(ust, -0.5, np.where(alt, -2.0, -1.0)), sk)
    return sk


class IchimokuSkorB0621(Strateji):
    """HAM:B001:621 (1d, long; Ichess): Heikin-Ashi mumlarında Ichimoku (9/26/52/26) bileşen skorları: tenkan/kijun kesişimi, HA kapanış/kijun kesişimi
    (kesişim noktasının buluta göre yeri 2 / 1 / 0,5; aşağı -0,5 / -1 / -2), bulut kırılımı (+/-2), senkou (öncü A/B) kesişimi ve chikou (HA kapanış / 26 mum
    önceki HA kapanış) kesişimi. Toplam skor kümülatif toplanır (cumsum, nedensel). Giriş: SMA(9)(skor) SMA(10)(skor)'u yukarı keser; çıkış: SMA(15)
    SMA(16)'yı aşağı keser. ROI {0dk %64,2; 8834 %37; 25392 %11,8; 55146 0} (gün mumuna yuvarlandı); sabit stop -%31,4. Hesap başlangıcına bağımlı değildir:
    SMA farkları yalnız son 10-16 skor artışına bağlıdır."""

    ad, stil = "kapanis__ichimoku-skor-b0621", "swing"
    varsayilan_parametreler = {"tenkan": 9, "kijun": 26, "senkou_b": 52, "kaydir": 26, "al_hizli": 9, "al_yavas": 10,
                               "sat_hizli": 15, "sat_yavas": 16, "sl": 0.314}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.642, 8834: 0.37, 25392: 0.118, 55146: 0}, 1440))

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def _skor(m: pd.DataFrame, tn: int, kn: int, bn: int, kay: int) -> pd.Series:
        ha = _ha(m)
        hh, hl, hk = ha["ha_yuksek"], ha["ha_dusuk"], ha["ha_kapanis"]

        def orta(n):
            return (hh.rolling(n, min_periods=n).max() + hl.rolling(n, min_periods=n).min()) / 2.0

        ten, kij = orta(tn), orta(kn)
        lead_a = (ten + kij) / 2.0
        lead_b = orta(bn)
        sa, sb = lead_a.shift(kay), lead_b.shift(kay)
        chik = hk.shift(kay)
        a = lambda s: s.to_numpy(dtype=float)  # noqa: E731
        A1, B1 = a(lead_a.shift(1)), a(lead_b.shift(1))
        sa_n, sb_n, hk_n = a(sa), a(sb), a(hk)
        sa1, sb1, hk1 = a(sa.shift(1)), a(sb.shift(1)), a(hk.shift(1))
        tk = _kesisim_skoru(a(ten), a(kij), a(ten.shift(1)), a(kij.shift(1)), sa_n, sb_n)
        pk = _kesisim_skoru(hk_n, a(kij), hk1, a(kij.shift(1)), sa_n, sb_n)
        ck = _kesisim_skoru(hk_n, a(chik), hk1, a(chik.shift(1)), sa_n, sb_n)
        with np.errstate(invalid="ignore"):
            yk = ((hk_n > sa_n) & (hk1 <= sa1) & (sa_n > sb_n)) | ((hk_n > sb_n) & (hk1 <= sb1) & (sa_n < sb_n))
            ak = ((hk_n < sa_n) & (hk1 >= sa1) & (sa_n < sb_n)) | ((hk_n < sb_n) & (hk1 >= sb1) & (sa_n > sb_n))
            kumo = np.where(yk, 2.0, np.where(ak, -2.0, 0.0))
            la, lb = a(lead_a), a(lead_b)
            yu = (la > lb) & (A1 <= B1)
            as_ = (la < lb) & (A1 >= B1)
            ust, alt = (hk_n > sa_n) & (hk_n > sb_n), (hk_n < sa_n) & (hk_n < sb_n)
        sen = np.where(yu, np.where(ust, 2.0, np.where(alt, 0.5, 1.0)), 0.0)
        sen = np.where(as_ & ~yu, np.where(ust, -0.5, np.where(alt, -2.0, -1.0)), sen)
        return pd.Series((tk + pk + kumo + sen + ck), index=m.index).cumsum()

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        skor = self._skor(mumlar, int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]), int(p["kaydir"]))
        al = yukari(g.sma(skor, int(p["al_hizli"])), g.sma(skor, int(p["al_yavas"])))
        cik = asagi(g.sma(skor, int(p["sat_hizli"])), g.sma(skor, int(p["sat_yavas"])))
        sl = float(p["sl"])
        return _bitir(cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ HAM:B001:623
class IchimokuTkKirmiziB0623(Strateji):
    """HAM:B001:623 (5m, long; Ichimoku): Ichimoku (9/26/52/26): tenkan kijun'u yukarı keser (önceki tenkan < kijun) VE bulut kırmızı (senkou B > senkou A) -> long.
    Sinyal çıkışı yok. ROI {0: %100}; sabit stop -%10; iz süren %1 (offset %2, offset sonrası)."""

    ad, stil = "kapanis__ichimoku-tk-kirmizi-b0623", "daytrade"
    varsayilan_parametreler = {"tenkan": 9, "kijun": 26, "senkou_b": 52, "kaydir": 26, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 1}, 5), geri_cekilme_yuzde=1.0, geri_cekilme_min_kar_yuzde=2.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ich = b2.ichimoku(mumlar["yuksek"], mumlar["dusuk"], int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]), int(p["kaydir"]))
        al = (ich["tenkan"].shift(1) < ich["kijun"].shift(1)) & (ich["tenkan"] > ich["kijun"]) & (ich["span_b"] > ich["span_a"])
        sl = float(p["sl"])
        return cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))


# ================================================================ HAM:B001:625
class IchimokuBulutUstuB0625(Strateji):
    """HAM:B001:625 (4h, long; Ichimoku_v12 + Ichimoku_v12.json): Ichimoku (20/60/120/30; json'daki cl/bl/lag/dpl sınıfta parametre olmadığından kullanılmaz):
    kapanış hem senkou A hem senkou B üstünde -> long (durum, kesişim değil). Sinyal çıkışı yok. ROI (json etkin) {0dk %77,9; 18779 %12,1; 41108 %6,7; 77955 0}
    (4h muma yuvarlandı). Kaynak stopu -1 (stopsuz): ATR(14)x3 felaket stopu. json'daki kâr basamaklı iz parametreleri (ts3.., tsl_target..) sınıfta
    kullanılmıyor."""

    ad, stil = "kapanis__ichimoku-bulut-ustu-b0625", "swing"
    varsayilan_parametreler = {"tenkan": 20, "kijun": 60, "senkou_b": 120, "kaydir": 30, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.779, 18779: 0.121, 41108: 0.067, 77955: 0}, 240))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ich = b2.ichimoku(mumlar["yuksek"], mumlar["dusuk"], int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]), int(p["kaydir"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return cerceve(mumlar, (kap > ich["span_a"]) & (kap > ich["span_b"]), False, kap - mes, kap + mes)


# ================================================================ HAM:B001:626
class IchimokuV12IkiGirisB0626(KancaDestek, Strateji):
    """HAM:B001:626 (4h, long; Ichimoku_v12__2): Ichimoku (20/60/120/30). Giriş (VEYA): (a) önceki kapanış < senkou B VE kapanış > senkou A VE kapanış > senkou B;
    (b) kapanış < kijun VE tenkan > kijun VE kapanış > senkou A, B VE kapanış < açılış VE önceki mum da düşüş (kapanış < açılış); hacim > 0. Çıkış: (kapanış
    senkou B'yi aşağı keser VE kapanış < senkou A, B) VEYA (kapanış senkou A'yı aşağı keser VE kapanış < senkou A, B); yalnız kârda (exit_profit_only). ROI
    {0dk %5} (ignore_roi_if_entry_signal motorda yok). Kaynak stopu -1 (stopsuz): ATR(14)x3. custom_stoploss: kâr > %15: kapanıştan %3,5; > %20: %4,5; > %30: %5
    geride iz (basamak değerleri sınıf varsayılanları; kaynaktaki `.range` döngüsü hyperopt dışında tek değer verir, kapanış bazlı kancada). Kaynak notu: custom_stoploss
    döngüsü güvenilmez olabilir (emin değil)."""

    ad, stil = "kapanis__ichimoku-v12-iki-giris-b0626", "swing"
    varsayilan_parametreler = {"tenkan": 20, "kijun": 60, "senkou_b": 120, "kaydir": 30, "atr_n": 14, "atr_k": 3.0,
                               "kademeler": ((0.15, 0.035), (0.20, 0.045), (0.30, 0.05))}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.05}, 240), yalniz_karda_cikis=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, ac = mumlar["kapanis"], mumlar["acilis"]
        ich = b2.ichimoku(mumlar["yuksek"], mumlar["dusuk"], int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]), int(p["kaydir"]))
        sa, sb = ich["span_a"], ich["span_b"]
        hv = mumlar["hacim"] > 0
        ustte = (kap > sa) & (kap > sb)
        a = (kap.shift(1) < sb) & ustte & hv
        b = ((kap < ich["kijun"]) & (ich["tenkan"] > ich["kijun"]) & ustte & (kap < ac)
             & (kap.shift(1) < ac.shift(1)) & hv)
        altta = (kap < sa) & (kap < sb)
        cik = (asagi(kap, sb) & altta) | (asagi(kap, sa) & altta)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        self._sakla(kap=kap)
        return _bitir(cerceve(mumlar, a | b, False, kap - mes, kap + mes), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        return _kademe_ihlali(self._kd["kap"], d.giris_mum_indeksi, d.mum_indeksi, d.giris_fiyati,
                              tuple(self.parametreler["kademeler"]))


# ================================================================ HAM:B001:627 / 629 / 630
def _aksam_dojisi_yildizi(m: pd.DataFrame, n: int = 10, doji_oran: float = 0.1, nufuz: float = 0.3) -> pd.Series:
    """Akşam doji yıldızı (TA-Lib CDLEVENINGDOJISTAR karşılığı, kendi yazımım): 1. mum uzun beyaz (gövde > önceki n mumun ort. gövdesi); 2. mum doji (gövde <=
    doji_oran x önceki n mumun ort. yüksek-düşük aralığı) ve gövdesi 1. gövdenin üstüne boşluk bırakır; 3. mum siyah ve 1. mumun kapanışından en az
    `nufuz` x 1. gövde kadar aşağı kapanır. Tüm bakışlar geriye."""
    o, h, l, c = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
    govde = (c - o).abs()
    ort_g = govde.rolling(n, min_periods=n).mean().shift(1)           # aday mumdan önceki n mum
    ort_a = (h - l).rolling(n, min_periods=n).mean().shift(1)
    g1, o1, c1 = govde.shift(2), o.shift(2), c.shift(2)
    uzun_beyaz = (c1 > o1) & (g1 > ort_g.shift(2))
    doji = govde.shift(1) <= doji_oran * ort_a.shift(1)
    ust_govde2 = pd.concat([o.shift(1), c.shift(1)], axis=1).min(axis=1)
    bosluk = ust_govde2 > pd.concat([o1, c1], axis=1).max(axis=1)
    siyah3 = (c < o) & (c < c1 - g1 * nufuz)
    return (uzun_beyaz & doji & bosluk & siyah3).fillna(False)


class Ichimoku2MumB0627(Strateji):
    """HAM:B001:627 (4h, long; Ichimoku_v30): Ichimoku (20/60/120/30). Giriş: kapanış[t-2] senkou A'yı (ya da B'yi) yukarı keser (kaynaktaki hizayla: kapanış[t-2] >
    SA[t] VE kapanış[t-3] <= SA[t-1]) VE kapanış[t-2] > SA VE kapanış[t-2] > SB (2 mum gecikmeli). Çıkış: akşam doji yıldızı deseni (TA-Lib CDLEVENINGDOJISTAR
    karşılığı: gövde/doji ölçütü 10 mum ortalaması, doji %10, nüfuz %30). ROI {0: 100} (kapalı). Kaynak stopu -1: ATR(14)x3."""

    ad, stil = "kapanis__ichimoku-bulut-2mum-b0627", "swing"
    varsayilan_parametreler = {"tenkan": 20, "kijun": 60, "senkou_b": 120, "kaydir": 30, "gecikme": 2, "ha_kaynak": False,
                               "cikis": "aksam_dojisi", "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 100}, 240))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        ich = b2.ichimoku(y, d, int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]), int(p["kaydir"]))
        sa, sb = ich["span_a"], ich["span_b"]
        fiyat = _ha(mumlar)["ha_kapanis"] if p["ha_kaynak"] else kap
        gec = fiyat.shift(int(p["gecikme"]))
        ustte = (gec > sa) & (gec > sb)
        al = (yukari(gec, sa) | yukari(gec, sb)) & ustte
        altta = (fiyat < sa) & (fiyat < sb)
        tk_asagi = asagi(ich["tenkan"], ich["kijun"]) & altta & (sb > sa)
        tip = str(p["cikis"])
        if tip == "aksam_dojisi":
            cik = _aksam_dojisi_yildizi(mumlar)
        elif tip == "tk_bulut":
            cik = tk_asagi
        elif tip == "tk_bulut_sar":
            cik = tk_asagi | (g.psar(y, d)["yon"] == -1)
        else:
            raise ValueError(f"Bilinmeyen cikis tipi: {tip}")
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(cerceve(mumlar, al, False, kap - mes, kap + mes), cik)


class Ichimoku2MumHaB0629(Ichimoku2MumB0627):
    """HAM:B001:629 (4h, long; Ichimoku_v32): Ichimoku (20/60/120/30), giriş 627 gibi ama HEIKIN-ASHI kapanışla (HA kapanış[t-2] bulutu yukarı keser ve üstündedir).
    Çıkış: tenkan kijun'u aşağı keser VE HA kapanış < senkou A, B VE bulut kırmızı. ROI {0: 100} (kapalı). Kaynak stopu -1: ATR(14)x3."""

    ad = "kapanis__ichimoku-ha-2mum-b0629"
    varsayilan_parametreler = {"tenkan": 20, "kijun": 60, "senkou_b": 120, "kaydir": 30, "gecikme": 2, "ha_kaynak": True,
                               "cikis": "tk_bulut", "atr_n": 14, "atr_k": 3.0}


class Ichimoku2MumSarB0630(Ichimoku2MumB0627):
    """HAM:B001:630 (4h, long; Ichimoku_v33): 627'nin girişi (kapanış[t-2]); çıkış: (tenkan kijun'u aşağı keser VE kapanış < senkou A, B VE bulut kırmızı) VEYA
    kapanış < SAR (psar yönü aşağı). ROI {0: 100} (kapalı). Kaynak stopu -1: ATR(14)x3."""

    ad = "kapanis__ichimoku-2mum-sar-b0630"
    varsayilan_parametreler = {"tenkan": 20, "kijun": 60, "senkou_b": 120, "kaydir": 30, "gecikme": 2, "ha_kaynak": False,
                               "cikis": "tk_bulut_sar", "atr_n": 14, "atr_k": 3.0}


# ================================================================ HAM:B001:628 / 631
class IchimokuHaUstB0628(Strateji):
    """HAM:B001:628 (1h, long; Ichimoku_v31): 4h Heikin-Ashi mumlarında Ichimoku (20/60/120/30), yalnız kapanmış 4h mumdan (htf.ust_zaman; 1h'ye ileri doldurulmuş).
    Giriş (1h serisinde, kaynaktaki gibi): (4h HA kapanış senkou A'yı yukarı keser VE önceki değer < SA VE 4h bulut yeşil) VEYA (4h HA kapanış senkou B'yi
    yukarı keser VE önceki değer < SB VE 4h bulut kırmızı). Çıkış: 4h HA kapanış < SA VEYA < SB. ROI {0: 100} (kapalı). Kaynak stopu -%99: ATR(14)x3."""

    ad, stil = "kapanis__ichimoku-ha4h-bulut-b0628", "swing"
    varsayilan_parametreler = {"ust_tf": "4h", "ha_kaynak": "ust", "tenkan": 20, "kijun": 60, "senkou_b": 120, "kaydir": 30,
                               "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 100}, 60))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]

        def f(u):
            ha = _ha(u)
            ich = b2.ichimoku(ha["ha_yuksek"], ha["ha_dusuk"], int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]), int(p["kaydir"]))
            return pd.DataFrame({"hk": ha["ha_kapanis"], "sa": ich["span_a"], "sb": ich["span_b"]})

        ust = ust_zaman(mumlar, str(p["ust_tf"]), f)
        sa, sb = ust["sa"], ust["sb"]
        hk = ust["hk"] if p["ha_kaynak"] == "ust" else _ha(mumlar)["ha_kapanis"]
        al = ((yukari(hk, sa) & (hk.shift(1) < sa) & (sa > sb)) | (yukari(hk, sb) & (hk.shift(1) < sb) & (sb > sa)))
        cik = (hk < sa) | (hk < sb)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(cerceve(mumlar, al, False, kap - mes, kap + mes), cik)


class IchimokuHaUstB0631(IchimokuHaUstB0628):
    """HAM:B001:631 (4h, long; Ichimoku_v37): 1d Heikin-Ashi Ichimoku (20/60/120/30; yalnız kapanmış günden); 4h HEIKIN-ASHI kapanışı (4h serinin kendi HA'sı) 1d senkou A'yı
    yukarı keser (önceki 4h HA kapanış < SA) VE 1d bulut yeşil, VEYA 1d SB'yi keser VE 1d bulut kırmızı -> long. Çıkış: 4h HA kapanış < 1d SA VEYA < 1d SB. ROI {0: 100}
    (kapalı). Kaynak stopu -%99: ATR(14)x3."""

    ad, stil = "kapanis__ichimoku-ha1d-bulut-b0631", "swing"
    varsayilan_parametreler = {"ust_tf": "1d", "ha_kaynak": "alt", "tenkan": 20, "kijun": 60, "senkou_b": 120, "kaydir": 30,
                               "atr_n": 14, "atr_k": 3.0}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 100}, 240))


# ================================================================ koşu listesi
def _p(sinif) -> dict:
    return dict(sinif.varsayilan_parametreler)


def _v(kaynak: str, no: int, sinif, tf: str, parametreler: dict | None = None) -> dict:
    return {"kimlik": f"{kaynak}#v{no}", "sinif": sinif.ad,
            "parametreler": _p(sinif) if parametreler is None else parametreler, "tf": tf}


SINIFLAR = [FrostStokBb3B0504, FrostStokBb3B0505, GumboT3EwoB0510, MontrealBbRsiB0514, OnurBbOrtaB0515, RothMfiCciBbB0516,
            RothFastdMfiBbB0517, SmaBbrsiEwoB0518, RsiSinirBbB0519, BbRsiYuzdeKesisB0520, PullbackDipKirilimB0529,
            AdxBbFastdB0531, Bb3AltB0534, KeltnerKirilimB0538, BesMumDipRsiB0541, FisherCciSslB0542, KcBbHaB0544,
            FisherRsiHacimB0549, HaEgimTahminB0610, HaSslMomMacdB0614, IchimokuSkorB0621, IchimokuTkKirmiziB0623,
            IchimokuBulutUstuB0625, IchimokuV12IkiGirisB0626, Ichimoku2MumB0627, IchimokuHaUstB0628, Ichimoku2MumHaB0629,
            Ichimoku2MumSarB0630, IchimokuHaUstB0631]

VARYANTLAR = [
    _v("HAM:B001:504", 1, FrostStokBb3B0504, "15m"),
    _v("HAM:B001:505", 1, FrostStokBb3B0505, "1h"),
    _v("HAM:B001:510", 1, GumboT3EwoB0510, "5m"),
    _v("HAM:B001:514", 1, MontrealBbRsiB0514, "15m"),
    _v("HAM:B001:515", 1, OnurBbOrtaB0515, "15m"),
    _v("HAM:B001:516", 1, RothMfiCciBbB0516, "5m"),
    _v("HAM:B001:517", 1, RothFastdMfiBbB0517, "5m"),
    _v("HAM:B001:518", 1, SmaBbrsiEwoB0518, "5m"),
    _v("HAM:B001:519", 1, RsiSinirBbB0519, "5m"),
    _v("HAM:B001:520", 1, BbRsiYuzdeKesisB0520, "5m"),
    _v("HAM:B001:529", 1, PullbackDipKirilimB0529, "5m"),
    _v("HAM:B001:531", 1, AdxBbFastdB0531, "1h"),
    _v("HAM:B001:534", 1, Bb3AltB0534, "1h"),
    _v("HAM:B001:538", 1, KeltnerKirilimB0538, "6h"),
    _v("HAM:B001:541", 1, BesMumDipRsiB0541, "1h"),
    _v("HAM:B001:542", 1, FisherCciSslB0542, "1h"),
    _v("HAM:B001:544", 1, KcBbHaB0544, "5m"),
    _v("HAM:B001:549", 1, FisherRsiHacimB0549, "5m"),
    _v("HAM:B001:610", 1, HaEgimTahminB0610, "5m"),
    _v("HAM:B001:614", 1, HaSslMomMacdB0614, "1h"),
    _v("HAM:B001:621", 1, IchimokuSkorB0621, "1d"),
    _v("HAM:B001:623", 1, IchimokuTkKirmiziB0623, "5m"),
    _v("HAM:B001:625", 1, IchimokuBulutUstuB0625, "4h"),
    _v("HAM:B001:626", 1, IchimokuV12IkiGirisB0626, "4h"),
    _v("HAM:B001:627", 1, Ichimoku2MumB0627, "4h"),
    _v("HAM:B001:628", 1, IchimokuHaUstB0628, "1h"),
    _v("HAM:B001:629", 1, Ichimoku2MumHaB0629, "4h"),
    _v("HAM:B001:630", 1, Ichimoku2MumSarB0630, "4h"),
    _v("HAM:B001:631", 1, IchimokuHaUstB0631, "4h"),
]

KODLANAMADI = [
    {"kimlik": "HAM:B001:543",
     "neden": "motorda ifade edilemiyor: 542 kuralına ek giriş süzgeci BTC/USDT 4h CCI(14) < 0 (başka sembol verisi; strateji yalnız kendi "
              "mumlarını alır, çapraz-sembol bilgi paritesi sözleşmede yok); uydurma çözüm yok"},
]
