"""Kapanış turu, "pozisyon bilinçli çıkış" modülüyle yeniden kodlanan G8 satırları (g8 kod partileri 1-8'den taşınanlar).

Motorun yeni alanları kullanılır: `CikisAyarlari.yalniz_karda_cikis`, `min_tutma_mum`, `yasa_bagli_zarar_cikisi`, `kismi_yuzde`,
`kapanis_chandelier_*` ve strateji kancası `pozisyon_cikisi(durum) -> bool` (motor her KAPANIŞTA gerçek açık pozisyon için çağırır;
çıkış sonraki açılışta, neden "kanca"). Kanca yalnız `PozisyonDurumu` (giriş fiyatı, giriş mumu, tutulan, giriş sonrası en yüksek/en
düşük, kapanış, kâr%) ve `sinyaller()`in önceden hesapladığı NEDENSEL dizileri okur (i'den sonrasına bakmaz). Sanal pozisyon yoktur.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa (ya da <= -%50 ise) stop = kapanış -/+ 3 x ATR(14) (ön kayıt uyarlaması); yüzde stoplar sinyal kapanışından.
- Kapanış bazlı kurallar kapanışta sınanır, çıkış sonraki açılışta olur (motor); kaynakta mum içi olan iz süren/ROI kuralları da aynı
  biçimde kapanışta sınanır (ortak uyarlama).
- Kanca dizileri `sinyaller()` çağrısında örneğe yazılır (aynı örnekle backtest edilir: motor önce sinyaller(), sonra kanca).
- Haftalık satır (726) 1d mumlarla koşulur: haftalık değerler `htf.ust_zaman("1w")` ile yalnız KAPANMIŞ haftadan, karar yeni haftanın
  ilk günü (VARYANTLAR tf = "1d").

Kodlanamayanlar dosya sonundaki `KODLANAMADI` listesindedir (114, 419).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b2
from motor.strateji._gosterge_d11j import mfi as _mfi
from motor.strateji._gosterge_d11j import wma as _wma
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d5 import kama
from motor.strateji.gostergeler_b2 import asagi_kesis, gecis, yukari_kesis
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.k2_kaynak import FlipperS0879
from motor.strateji.temel import Strateji


# ================================================================ ortak yardımcılar (diğer kod_g8 dosyaları da kullanır)
def roi_tablosu(tablo: dict, tf_dk: float) -> tuple:
    """Freqtrade minimal_roi {dakika: oran} -> ((mum, kâr%), ...) (aynı muma düşende büyük dakikalı basamak geçerli)."""
    d = {}
    for dk in sorted(tablo):
        d[int(math.ceil(dk / tf_dk))] = round(float(tablo[dk]) * 100.0, 6)
    return tuple(sorted(d.items()))


class KancaDestek:
    """`sinyaller()`in hesapladığı nedensel dizileri kanca için saklar (strateji sınıfına karıştırılır)."""

    _kd: dict = {}

    def _sakla(self, **diziler) -> None:
        self._kd = {k: np.asarray(v, dtype=float) for k, v in diziler.items()}

    def _dz(self, ad: str, i: int) -> float:
        a = self._kd.get(ad)
        if a is None or i < 0 or i >= len(a):
            return math.nan
        return float(a[i])

    def _var(self, i: int) -> bool:
        return bool(self._kd) and 0 <= i < len(next(iter(self._kd.values())))


class RoiTek:
    """Tek basamaklı (zamansız) ROI: `roi_anahtar` parametresindeki oran (örn. 0.10) -> CikisAyarlari.azalan_roi = ((0, yüzde),).
    Kapanıştaki kâr% >= hedef ise sonraki açılışta çıkılır (tüm kod_g8 dosyalarında tek biçim; eskiden limit `hedef`)."""

    roi_anahtar = "roi"

    def __init__(self, cikis_ayarlari: CikisAyarlari = None, **parametreler):
        super().__init__(cikis_ayarlari=cikis_ayarlari, **parametreler)
        if cikis_ayarlari is None:
            self.cikis_ayarlari = CikisAyarlari(
                azalan_roi=((0, round(float(self.parametreler[self.roi_anahtar]) * 100.0, 6)),))


def hafta_degerleri(mumlar: pd.DataFrame, fonk):
    """1d mumlarla haftalık kural: fonk(haftalık_df) -> DataFrame (haftalık değerler); `htf.ust_zaman("1w")` ile yalnız KAPANMIŞ haftadan, yeni
    haftanın ilk gününden itibaren 1d indekse taşınır. Döner: (w, yeni): `yeni` = bir haftalık mumun değerinin ilk göründüğü gün (karar günü)."""
    def f(u: pd.DataFrame) -> pd.DataFrame:
        d = fonk(u).copy()
        d["_no"] = np.arange(len(u), dtype=float)
        return d

    w = ust_zaman(mumlar, "1w", f)
    yeni = w["_no"].notna() & (w["_no"] != w["_no"].shift(1))
    return w, yeni


def ay_sonu_bayragi(index: pd.DatetimeIndex) -> pd.Series:
    """1d mumlarda ay sonu günü (takvimde ertesi gün başka ayda); yalnız zaman damgasından (gelecek veri yok)."""
    return pd.Series((index + pd.Timedelta(days=1)).month != index.month, index=index)


def tepe_geri_cekilme(d: PozisyonDurumu, yuzde: float, min_kar: float = 0.0, tepe: float | None = None) -> bool:
    """Giriş sonrası zirveden (long: en yüksek HIGH, short: en düşük LOW; `tepe` verilirse o) fiyatın %`yuzde`'si kadar
    geri çekilmede kapanış çıkışı. Zirve kârı >= min_kar% iken geçerli."""
    y = yuzde / 100.0
    if d.yon == 1:
        t = d.en_yuksek if tepe is None else tepe
        return (t / d.giris_fiyati - 1.0) * 100.0 >= min_kar and d.kapanis <= t * (1.0 - y)
    t = d.en_dusuk if tepe is None else tepe
    return (1.0 - t / d.giris_fiyati) * 100.0 >= min_kar and d.kapanis >= t * (1.0 + y)


def kapanis_iz_ihlali(kv: np.ndarray, atr: np.ndarray, bas: int, i: int, k: float, yon: int = 1,
                      tepe_modu: bool = True) -> bool:
    """Kapanış bazlı iz süren stop (yalnız lehine taşınır). bas..i arası kapanışlardan:
    tepe_modu=True : stop_j = (bas..j en yüksek kapanış) - k*ATR_j, stop = en büyük stop_j (long; short ayna).
    tepe_modu=False: stop_j = kapanış_j - k*ATR_j, stop = en büyük stop_j.
    Kapanış stop'a eşit/altındaysa True (short: eşit/üstündeyse)."""
    bas = max(int(bas), 0)
    c, a = kv[bas:i + 1], atr[bas:i + 1]
    if len(c) == 0:
        return False
    if yon == 1:
        s = (np.maximum.accumulate(c) if tepe_modu else c) - k * a
        s = s[np.isfinite(s)]
        return bool(len(s)) and bool(kv[i] <= s.max())
    s = (np.minimum.accumulate(c) if tepe_modu else c) + k * a
    s = s[np.isfinite(s)]
    return bool(len(s)) and bool(kv[i] >= s.min())


def _bitir(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _atr_mesafe(m: pd.DataFrame, n: int = 14, k: float = 3.0) -> pd.Series:
    return k * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], n)


def _stoch_ham(m: pd.DataFrame, n: int) -> pd.Series:
    """Hızlı stokastik %K (TA-Lib STOCHF fastk): 100 x (kapanış - en düşük) / (en yüksek - en düşük)."""
    hh = m["yuksek"].rolling(n, min_periods=n).max()
    ll = m["dusuk"].rolling(n, min_periods=n).min()
    return 100.0 * (m["kapanis"] - ll) / (hh - ll).where(lambda x: x > 0)


def _stochf(m: pd.DataFrame, fastk: int, fastd: int = 3):
    """TA-Lib STOCHF: fastk = ham %K(fastk), fastd = SMA(fastk, fastd)."""
    k = _stoch_ham(m, fastk)
    return k, g.sma(k, fastd)


def _stoch_yavas(m: pd.DataFrame, fastk: int = 5, slowk: int = 3, slowd: int = 3):
    """TA-Lib STOCH: slowk = SMA(ham %K(fastk), slowk), slowd = SMA(slowk, slowd)."""
    sk = g.sma(_stoch_ham(m, fastk), slowk)
    return sk, g.sma(sk, slowd)


def fisher_rsi(kap: pd.Series, n: int = 14) -> pd.Series:
    """Fisher-RSI: x = 0,1 x (RSI(n) - 50); (e^(2x) - 1) / (e^(2x) + 1) (= tanh x), -1..+1."""
    return np.tanh(0.1 * (g.rsi(kap, n) - 50.0))


def fisher_rsi_norma(kap: pd.Series, n: int = 14) -> pd.Series:
    """Normalleştirilmiş Fisher-RSI: 50 x (fisher_rsi + 1), 0..100."""
    return 50.0 * (fisher_rsi(kap, n) + 1.0)


def cdl_hammer(m: pd.DataFrame) -> pd.Series:
    """Çekiç mumu (TA-Lib CDLHAMMER mantığı, standart tanım; True = 100): gövde < önceki 10 gövdenin ortalaması; alt gölge > gövde;
    üst gölge < 0,1 x önceki 10 mumun ortalama (yüksek-düşük) aralığı; gövdenin altı önceki mumun düşüğünün 0,2 x önceki 5 mumun
    ortalama aralığı kadar yakınından aşağıda/yakınında (min(açılış, kapanış) < düşük[-1] + 0,2 x ort.aralık[-1])."""
    o, h, l, c = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
    govde = (c - o).abs()
    ust_g = h - np.maximum(o, c)
    alt_g = np.minimum(o, c) - l
    aralik = h - l
    govde_ort = govde.shift(1).rolling(10, min_periods=10).mean()
    ust_ort = aralik.shift(1).rolling(10, min_periods=10).mean()
    yakin = 0.2 * aralik.shift(2).rolling(5, min_periods=5).mean()
    return ((govde < govde_ort) & (alt_g > govde) & (ust_g < 0.1 * ust_ort)
            & (np.minimum(o, c) < l.shift(1) + yakin)).fillna(False).astype(bool)


class _Taban(KancaDestek, Strateji):
    stil = "swing"
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True


class ParametreliCikis(_Taban):
    """CikisAyarlari örnek düzeyinde parametrelerden kurulur (`_cikis(p)`); açık verilen cikis_ayarlari önceliklidir."""

    def __init__(self, cikis_ayarlari: CikisAyarlari = None, **parametreler):
        super().__init__(cikis_ayarlari=cikis_ayarlari, **parametreler)
        if cikis_ayarlari is None:
            self.cikis_ayarlari = self._cikis(self.parametreler)

    @staticmethod
    def _cikis(p: dict) -> CikisAyarlari:
        raise NotImplementedError


# ================================================================ X005:4
class KdjJdS0004(_Taban):
    """HAM:X005:4 (1d, long-only): KDJ(9,3,3): ham %K(9), K = SMA(ham, 3), D = SMA(K, 3), J = 3K - 2D. Giriş J > D (kaynak kodundaki
    fiili koşul; metindeki 'J>K ve D' değil); çıkış: pozisyon KÂRDAYKEN J bir önceki J'den düşükse (kanca: kâr% > 0) VEYA J < D
    (cikis_long). Stop giriş - 2 x ATR(14) (kaynakta var; sinyal kapanışından). Durum tabanlı giriş."""

    ad = "kapanis__kdj-j-d-s0004"
    varsayilan_parametreler = {"fastk": 9, "slowk": 3, "slowd": 3, "stop_atr": 2.0, "atr_n": 14}

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        k = g.sma(_stoch_ham(m, int(p["fastk"])), int(p["slowk"]))
        d = g.sma(k, int(p["slowd"]))
        j = 3.0 * k - 2.0 * d
        mes = _atr_mesafe(m, int(p["atr_n"]), float(p["stop_atr"]))
        self._sakla(j=j)
        return _bitir(cerceve(m, j > d, False, kap - mes, kap + mes), j < d)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        j0, j1 = self._dz("j", i), self._dz("j", i - 1)
        return bool(d.kar_yuzde > 0 and j0 < j1)


# ================================================================ X005:20 / 21 / 22 (Freqtrade Strategy002/003/005)
_ROI_5M_A = roi_tablosu({0: 0.05, 20: 0.04, 30: 0.03, 60: 0.01}, 5)
_ROI_5M_B = roi_tablosu({0: 0.05, 20: 0.04, 40: 0.03, 80: 0.02, 1440: 0.01}, 5)


class FtStrategy002S0020(_Taban):
    """HAM:X005:20 (5m, long): RSI(14) < 30 VE yavaş Stokastik slowK < 20 (TA-Lib STOCH 5/3/3) VE kapanış < BB(20, 2σ) alt bandı VE
    çekiç mumu (cdl_hammer, TA-Lib CDLHAMMER mantığı) -> long. Çıkış sinyali: Parabolik SAR > kapanış VE Fisher-RSI > 0,3 YALNIZ
    KÂRDAYKEN (yalniz_karda_cikis). ROI {0dk %5, 20 %4, 30 %3, 60 %1} (azalan_roi, 5m'de mum 0/4/6/12); sabit stop -%10.
    Uyarlama: BB kapanıştan (kural metni)."""

    ad, stil = "kapanis__ft-strategy002-s0020", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_alt": 30.0, "slowk_esik": 20.0, "fastk": 5, "slowk": 3, "slowd": 3,
                               "bb_n": 20, "bb_k": 2.0, "fisher_cikis": 0.3, "sl": 0.10}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_ROI_5M_A, yalniz_karda_cikis=True)

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        sk, _ = _stoch_yavas(m, int(p["fastk"]), int(p["slowk"]), int(p["slowd"]))
        bb = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        al = ((g.rsi(kap, int(p["rsi_n"])) < float(p["rsi_alt"])) & (sk < float(p["slowk_esik"]))
              & (kap < bb["alt"]) & cdl_hammer(m))
        sar = g.psar(m["yuksek"], m["dusuk"])["sar"]
        cik = (sar > kap) & (fisher_rsi(kap, int(p["rsi_n"])) > float(p["fisher_cikis"]))
        sl = float(p["sl"])
        return _bitir(cerceve(m, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


class FtStrategy003S0021(_Taban):
    """HAM:X005:21 (5m, long-only): 0 < RSI(14) < 28 VE kapanış < SMA(40) VE Fisher-RSI < -0,94 VE MFI(14) < 16 VE (EMA50 > EMA100 VEYA
    EMA5 EMA10'u yukarı keser) VE STOCHF(5,3) fastd > fastk VE fastd > 0 -> long. Çıkış: SAR > kapanış VE Fisher-RSI > 0,3 YALNIZ
    KÂRDAYKEN. ROI {0dk %5, 20 %4, 30 %3, 60 %1}; sabit stop -%10."""

    ad, stil = "kapanis__ft-strategy003-s0021", "daytrade"
    varsayilan_parametreler = {"rsi_n": 14, "rsi_ust": 28.0, "sma_n": 40, "fisher_alt": -0.94, "mfi_n": 14, "mfi_ust": 16.0,
                               "ema_a": 50, "ema_b": 100, "ema_h": 5, "ema_y": 10, "fastk": 5, "fastd": 3,
                               "fisher_cikis": 0.3, "sl": 0.10}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_ROI_5M_A, yalniz_karda_cikis=True)

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        rsi = g.rsi(kap, int(p["rsi_n"]))
        fk, fd = _stochf(m, int(p["fastk"]), int(p["fastd"]))
        mfi = _mfi(m["yuksek"], m["dusuk"], kap, m["hacim"], int(p["mfi_n"]))
        ema_ok = (g.ema(kap, int(p["ema_a"])) > g.ema(kap, int(p["ema_b"]))) | yukari_kesis(
            g.ema(kap, int(p["ema_h"])), g.ema(kap, int(p["ema_y"])))
        al = ((rsi > 0) & (rsi < float(p["rsi_ust"])) & (kap < g.sma(kap, int(p["sma_n"])))
              & (fisher_rsi(kap, int(p["rsi_n"])) < float(p["fisher_alt"])) & (mfi < float(p["mfi_ust"]))
              & ema_ok & (fd > fk) & (fd > 0))
        sar = g.psar(m["yuksek"], m["dusuk"])["sar"]
        cik = (sar > kap) & (fisher_rsi(kap, int(p["rsi_n"])) > float(p["fisher_cikis"]))
        sl = float(p["sl"])
        return _bitir(cerceve(m, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


class FtStrategy005S0022(_Taban):
    """HAM:X005:22 (5m, long-only): hacim > SMA(hacim,150) x 4 VE kapanış < SMA(40) VE fastD > fastK (STOCHF 5/3) VE RSI(14) > 26 VE
    fastD > 1 VE Fisher-RSI-normalleştirilmiş < 5 -> long. Çıkış: RSI(14) 74'ü yukarı keser VE MACD < 0 VE -DI(14) > 4 YALNIZ
    KÂRDAYKEN. ROI {0dk %5, 20 %4, 40 %3, 80 %2, 1440 %1}; sabit stop -%10."""

    ad, stil = "kapanis__ft-strategy005-s0022", "daytrade"
    varsayilan_parametreler = {"hacim_n": 150, "hacim_k": 4.0, "sma_n": 40, "fastk": 5, "fastd": 3, "rsi_n": 14, "rsi_alt": 26.0,
                               "fastd_alt": 1.0, "fisher_norma_ust": 5.0, "rsi_sat": 74.0, "di_n": 14, "eksi_di": 4.0, "sl": 0.10}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_ROI_5M_B, yalniz_karda_cikis=True)

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        rsi = g.rsi(kap, int(p["rsi_n"]))
        fk, fd = _stochf(m, int(p["fastk"]), int(p["fastd"]))
        al = ((m["hacim"] > g.sma(m["hacim"], int(p["hacim_n"])) * float(p["hacim_k"]))
              & (kap < g.sma(kap, int(p["sma_n"]))) & (fd > fk) & (rsi > float(p["rsi_alt"]))
              & (fd > float(p["fastd_alt"])) & (fisher_rsi_norma(kap, int(p["rsi_n"])) < float(p["fisher_norma_ust"])))
        mc = g.macd(kap)["macd"]
        eksi = g.adx(m["yuksek"], m["dusuk"], kap, int(p["di_n"]))["eksi_di"]
        cik = yukari_kesis(rsi, float(p["rsi_sat"])) & (mc < 0) & (eksi > float(p["eksi_di"]))
        sl = float(p["sl"])
        return _bitir(cerceve(m, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ X005:60
class KcEmaTrendS0060(_Taban):
    """HAM:X005:60 (iki yön; TF 15m|1h|4h|1d): KC = EMA(20) +/- 1,5 x ATR(20, Wilder). KC modülü: kapanış alt bandı aşağı keserse long,
    üst bandı yukarı keserse short; çıkış long: kapanış EMA20'yi yukarı keser, short: aşağı keser. Trend modülü: EMA9 EMA21'i yukarı
    keser VE kapanış > EMA50 -> long (ayna short); çıkış ters EMA9/21 kesişimi. Çıkış kuralı pozisyonu hangi modülün açtığına bağlıdır
    (kanca: giriş sinyali mumundaki modül; ikisi birlikte doğarsa KC). Her modülde stop = kapanış -/+ 1,5 x ATR(20), limit = kapanış
    +/- 3 x ATR(20); kaynak bu seviyeleri HER barda güncel kapanıştan yeniden verir (kayan stop/TP): kanca, her mumda bir önceki
    kapanıştan hesaplanan kayan stop/TP seviyesinin o mumda değip değmediğini (high/low) kapanışta sınar ve sonraki açılışta çıkar.
    YAKLAŞIK: motorda giriş anındaki sabit stop (ilk seviye) kalır, kayan seviye mum içinde değil kapanışta sınanır, çıkış fiyatı
    seviye değil sonraki açılıştır."""

    ad, stil = "kapanis__kc-ema-trend-s0060", "swing"
    varsayilan_parametreler = {"kc_len": 20, "kc_mult": 1.5, "atr_n": 20, "ema_h": 9, "ema_y": 21, "ema_t": 50,
                               "sl_atr": 1.5, "tp_atr": 3.0}

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        orta = g.ema(kap, int(p["kc_len"]))
        atr = g.atr(m["yuksek"], m["dusuk"], kap, int(p["atr_n"]))
        ust, alt = orta + float(p["kc_mult"]) * atr, orta - float(p["kc_mult"]) * atr
        kc_l, kc_s = asagi_kesis(kap, alt), yukari_kesis(kap, ust)
        eh, ey, et = g.ema(kap, int(p["ema_h"])), g.ema(kap, int(p["ema_y"])), g.ema(kap, int(p["ema_t"]))
        tr_l, tr_s = yukari_kesis(eh, ey) & (kap > et), asagi_kesis(eh, ey) & (kap < et)
        kcl_cik, kcs_cik = yukari_kesis(kap, orta), asagi_kesis(kap, orta)
        trl_cik, trs_cik = asagi_kesis(eh, ey), yukari_kesis(eh, ey)
        ra, rt = float(p["sl_atr"]) * atr, float(p["tp_atr"]) * atr
        self._sakla(kap=kap, atr=atr, yuk=m["yuksek"], dus=m["dusuk"], kc_l=kc_l, kc_s=kc_s,
                    kcl_cik=kcl_cik, kcs_cik=kcs_cik, trl_cik=trl_cik, trs_cik=trs_cik)
        return cerceve(m, kc_l | tr_l, kc_s | tr_s, kap - ra, kap + ra)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i, s = d.mum_indeksi, d.giris_mum_indeksi - 1
        if not self._var(i) or i < 1:
            return False
        p = self.parametreler
        kc = self._dz("kc_l" if d.yon == 1 else "kc_s", s) == 1.0
        if d.yon == 1:
            modul = self._dz("kcl_cik" if kc else "trl_cik", i) == 1.0
        else:
            modul = self._dz("kcs_cik" if kc else "trs_cik", i) == 1.0
        if modul:
            return True
        c0, a0 = self._dz("kap", i - 1), self._dz("atr", i - 1)
        if not (math.isfinite(c0) and math.isfinite(a0)):
            return False
        h, lo = self._dz("yuk", i), self._dz("dus", i)
        ra, rt = float(p["sl_atr"]) * a0, float(p["tp_atr"]) * a0
        if d.yon == 1:
            return bool(lo <= c0 - ra or h >= c0 + rt)
        return bool(h >= c0 + ra or lo <= c0 - rt)


# ================================================================ X005:79
class SupertrendIkiliKademeS0079(_Taban):
    """HAM:X005:79 (6h, iki yön): Supertrend1 (ATR 10, çarpan 3,0) ve Supertrend2 (ATR 11, çarpan 4,0) ikisi de yükselişteyse long, ikisi
    de düşüşteyse short; çıkış: ikisi de ters yöne dönünce. Kademeli kâr al (yüzde, kismi_yuzde): +%6'da ilk pozisyonun %12'si, +%12'de
    %8'i, +%18'de %4'ü kapanır; kalan çıkış sinyaline kadar. Stop kaynakta yok: ATR(14)x3 (uyarlama). Durum tabanlı giriş."""

    ad = "kapanis__supertrend-ikili-kademe-s0079"
    varsayilan_parametreler = {"st1_atr": 10, "st1_k": 3.0, "st2_atr": 11, "st2_k": 4.0, "atr_n": 14, "atr_k": 3.0}
    cikis_ayarlari = CikisAyarlari(kismi_yuzde=((6.0, 0.12), (12.0, 0.08), (18.0, 0.04)))

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        s1 = g.supertrend(m["yuksek"], m["dusuk"], kap, int(p["st1_atr"]), float(p["st1_k"]))["yon"]
        s2 = g.supertrend(m["yuksek"], m["dusuk"], kap, int(p["st2_atr"]), float(p["st2_k"]))["yon"]
        yuk, dus = (s1 == 1) & (s2 == 1), (s1 == -1) & (s2 == -1)
        mes = _atr_mesafe(m, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(cerceve(m, yuk, dus, kap - mes, kap + mes), dus, yuk)


# ================================================================ X005:400 / 401 / 416
class _MinMaksTutma(ParametreliCikis):
    """Ortak çerçeve (400/401/416): pozisyon en az `min_tut`, en çok `maks_tut` mum (işlem günü) tutulur; ilk min_tut mumda sinyal çıkışı
    yok sayılır (min_tutma_mum), maks_tut'ta zorunlu çıkış (zaman_cikisi_mum); min_tut'tan uzun pozisyon başlangıç değerinin %zarar
    kaybederse kapanışta kapatılır (yasa_bagli_zarar_cikisi). Stop: ATR(14)x3 (uyarlama)."""

    @staticmethod
    def _cikis(p: dict) -> CikisAyarlari:
        return CikisAyarlari(min_tutma_mum=int(p["min_tut"]), zaman_cikisi_mum=int(p["maks_tut"]),
                             yasa_bagli_zarar_cikisi=((int(p["min_tut"]), float(p["zarar_yuzde"])),))


class MacdMinMaksS0400(_MinMaksTutma):
    """HAM:X005:400 (1d, iki yön): MACD(12,26,9) sinyali yukarı keserse long, aşağı keserse short; ters kesişimde çıkış YALNIZ 20. günden
    sonra (öncesinde yok sayılır); en çok 40 gün; 20 günden uzun pozisyon %7,5 zararda kapanır. ATR(14)x3 stop (uyarlama)."""

    ad = "kapanis__macd-minmaks-s0400"
    varsayilan_parametreler = {"hizli": 12, "yavas": 26, "sinyal": 9, "min_tut": 20, "maks_tut": 40, "zarar_yuzde": 7.5,
                               "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        mc = g.macd(kap, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        yuk, asa = yukari_kesis(mc["macd"], mc["sinyal"]), asagi_kesis(mc["macd"], mc["sinyal"])
        mes = _atr_mesafe(m, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(cerceve(m, yuk, asa, kap - mes, kap + mes), asa, yuk)


class RocMinMaksS0401(_MinMaksTutma):
    """HAM:X005:401 (1d, long-only): kapanış 60 gün önceki kapanıştan yüksekse al (durum); altına inince sat; en az 20 / en çok 40 gün;
    20 günden uzun pozisyon %7,5 zararda kapanır. ATR(14)x3 stop (uyarlama)."""

    ad = "kapanis__roc60-minmaks-s0401"
    varsayilan_parametreler = {"n": 60, "min_tut": 20, "maks_tut": 40, "zarar_yuzde": 7.5, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        onceki = kap.shift(int(p["n"]))
        mes = _atr_mesafe(m, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(cerceve(m, kap > onceki, False, kap - mes, kap + mes), kap < onceki)


class RsiMinMaksS0416(_MinMaksTutma):
    """HAM:X005:416 (1d, long-only): RSI(60) 5'in altına inince al; 95'in üstüne çıkınca sat; en az 20 / en çok 40 gün; 20 günden uzun
    pozisyon %7,5 zararda kapanır. ATR(14)x3 stop (uyarlama)."""

    ad = "kapanis__rsi60-minmaks-s0416"
    varsayilan_parametreler = {"rsi_n": 60, "alt": 5.0, "ust": 95.0, "min_tut": 20, "maks_tut": 40, "zarar_yuzde": 7.5,
                               "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        r = g.rsi(kap, int(p["rsi_n"]))
        al = (r.shift(1) >= float(p["alt"])) & (r < float(p["alt"]))
        sat = (r.shift(1) < float(p["ust"])) & (r >= float(p["ust"]))
        mes = _atr_mesafe(m, int(p["atr_n"]), float(p["atr_k"]))
        return _bitir(cerceve(m, al.fillna(False), False, kap - mes, kap + mes), sat.fillna(False))


# ================================================================ X005:436
class MacdHistRsiAtrS0436(_Taban):
    """HAM:X005:436 (1d, iki yön, tek pozisyon): MACD hist = (EMA19 - EMA39) - EMA14(MACD), RSI(14, Wilder), ATR(14), çarpan 2,0. Long: hist > 0
    VE RSI < 30; short: hist < 0 VE RSI > 70. Çıkış long: kapanış >= giriş + 2 x ATR(giriş barı) | kapanış <= giriş - 2 x ATR | RSI >= 50 |
    hist < 0; short: |kapanış - giriş| >= 2 x ATR | RSI <= 50 | hist > 0. Giriş fiyatına/giriş barı ATR'sine bağlı kapanış koşulları
    kancadadır (giriş barı = sinyal mumu); kaynakta stop yok -> felaket stopu ATR(14)x3 (uyarlama)."""

    ad = "kapanis__macd-hist-rsi-atr-s0436"
    varsayilan_parametreler = {"macd_h": 19, "macd_y": 39, "macd_s": 14, "rsi_n": 14, "rsi_al": 30.0, "rsi_sat": 70.0,
                               "rsi_cik": 50.0, "atr_n": 14, "atr_x": 2.0, "stop_atr": 3.0}

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        hist = g.macd(kap, int(p["macd_h"]), int(p["macd_y"]), int(p["macd_s"]))["histogram"]
        rsi = g.rsi(kap, int(p["rsi_n"]))
        atr = g.atr(m["yuksek"], m["dusuk"], kap, int(p["atr_n"]))
        mes = float(p["stop_atr"]) * atr
        cl = (rsi >= float(p["rsi_cik"])) | (hist < 0)
        cs = (rsi <= float(p["rsi_cik"])) | (hist > 0)
        self._sakla(atr=atr)
        return _bitir(cerceve(m, (hist > 0) & (rsi < float(p["rsi_al"])), (hist < 0) & (rsi > float(p["rsi_sat"])),
                              kap - mes, kap + mes), cl, cs)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        a = self._dz("atr", d.giris_mum_indeksi - 1)
        if not math.isfinite(a):
            return False
        return bool(abs(d.kapanis - d.giris_fiyati) >= float(self.parametreler["atr_x"]) * a)


# ================================================================ X005:446
class KamaGeriDonusS0446(_Taban):
    """HAM:X005:446 (1d, long-only): kapanış > SMA(100) VE KAMA(26,3,52) bir önceki bardan düşük değil; önceki 5 barda RSI(14) <= 35 olmuş
    ya da kapanış alt Bollinger(20,2σ) altına inmiş olmuş; bugün RSI(14) >= 45, CCI(20) >= -80 ve kapanış > BB orta bandı -> long.
    Çıkış: hedef = giriş + 3,5 x ATR(14) (sinyal hedefi, bar içi), stop = giriş - 2,0 x ATR (sinyal stopu, bar içi), iz süren stop =
    giriş sonrası TEPE KAPANIŞ - 3,0 x ATR (kapanış bazlı, kanca; sabit stopla birlikte büyük olan geçerli), kapanış < SMA(100) ->
    çık, en çok 63 bar (zaman_cikisi_mum). Kesitsel sıralama atıldı (816/818 ölçüsü)."""

    ad = "kapanis__kama-geri-donus-s0446"
    varsayilan_parametreler = {"trend_n": 100, "kama_n": 26, "kama_h": 3, "kama_y": 52, "rsi_n": 14, "rsi_giris": 35.0,
                               "rsi_geri": 45.0, "bb_n": 20, "bb_k": 2.0, "cci_n": 20, "cci_geri": -80.0, "atr_n": 14,
                               "hedef_atr": 3.5, "stop_atr": 2.0, "iz_atr": 3.0, "maks_tutma_bar": 63}

    def __init__(self, cikis_ayarlari: CikisAyarlari = None, **parametreler):
        super().__init__(cikis_ayarlari=cikis_ayarlari, **parametreler)
        if cikis_ayarlari is None:
            self.cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=int(self.parametreler["maks_tutma_bar"]))

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        sma = g.sma(kap, int(p["trend_n"]))
        kam = kama(kap, int(p["kama_n"]), int(p["kama_h"]), int(p["kama_y"]))
        rsi = g.rsi(kap, int(p["rsi_n"]))
        bb = g.bollinger(kap, int(p["bb_n"]), float(p["bb_k"]))
        cci = b2.cci(m["yuksek"], m["dusuk"], kap, int(p["cci_n"]))
        gecmis = ((rsi <= float(p["rsi_giris"])) | (kap < bb["alt"])).astype(float)
        gec5 = gecmis.shift(1).rolling(5, min_periods=5).max() > 0
        gir = ((kap > sma) & (kam >= kam.shift(1)) & gec5 & (rsi >= float(p["rsi_geri"]))
               & (cci >= float(p["cci_geri"])) & (kap > bb["orta"])).fillna(False)
        atr = g.atr(m["yuksek"], m["dusuk"], kap, int(p["atr_n"]))
        self._sakla(kap=kap, atr=atr)
        return _bitir(cerceve(m, gir, False, kap - float(p["stop_atr"]) * atr, kap + float(p["stop_atr"]) * atr,
                              hedef_l=kap + float(p["hedef_atr"]) * atr), kap < sma)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        return kapanis_iz_ihlali(self._kd["kap"], self._kd["atr"], d.giris_mum_indeksi - 1, i,
                                 float(self.parametreler["iz_atr"]), 1, True)


# ================================================================ X005:447
class RejimAdxKapanisIzS0447(_Taban):
    """HAM:X005:447 (1d, long-only): SMA(56) > SMA(60) VE kapanış > SMA(95) VE ADX(13) >= 27,5 (rejim) ise long; koşullardan biri bozulunca
    kapat (cikis_long); stop = max(giriş kapanışı - 5,9 x ATR(27), en yüksek kapanış - 4,5 x ATR(27)): ilk kol sinyal stopu (bar içi),
    tepe-kapanış izi kancada (kapanış bazlı). Stop tetiklenince rejim bozulana kadar yeniden girilmez: giriş = rejimin yeniden
    sağlanması (gecis, yani yanlıştan doğruya geçiş). Yorum: 'tamamen bozulma' = rejim koşulunun (üçünün birlikte) bir kez yanlış olması."""

    ad = "kapanis__rejim-adx-iz-s0447"
    varsayilan_parametreler = {"ma_h": 56, "ma_y": 60, "trend_sma": 95, "adx_n": 13, "adx_min": 27.5, "atr_n": 27,
                               "stop_ilk": 5.9, "iz": 4.5}

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        adx = g.adx(m["yuksek"], m["dusuk"], kap, int(p["adx_n"]))["adx"]
        rejim = ((g.sma(kap, int(p["ma_h"])) > g.sma(kap, int(p["ma_y"]))) & (kap > g.sma(kap, int(p["trend_sma"])))
                 & (adx >= float(p["adx_min"]))).fillna(False)
        atr = g.atr(m["yuksek"], m["dusuk"], kap, int(p["atr_n"]))
        self._sakla(kap=kap, atr=atr)
        return _bitir(cerceve(m, gecis(rejim), False, kap - float(p["stop_ilk"]) * atr, kap + float(p["stop_ilk"]) * atr), ~rejim)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        return kapanis_iz_ihlali(self._kd["kap"], self._kd["atr"], d.giris_mum_indeksi - 1, i,
                                 float(self.parametreler["iz"]), 1, True)


# ================================================================ X005:573
class FtStrategy004S0573(_Taban):
    """HAM:X005:573 (5m, long-only): (ADX(14) > 50 veya ADX(35) > 26) VE CCI(14) < -100 VE önceki mumda fastK/fastD (STOCHF 5) < 20 VE önceki
    mumda STOCHF(50) K/D < 30 VE önceki fastK < önceki fastD VE fastK > fastD VE SMA(hacim,12) > 0,75 -> long. Çıkış: ADX(35) < 25 VE
    (fastK > 70 veya fastD > 70) VE önceki fastK < önceki fastD VE kapanış > EMA(5), YALNIZ KÂRDAYKEN (yalniz_karda_cikis). ROI {0dk
    %5, 20 %4, 30 %3, 60 %1}; sabit stop -%10. 'ort. hacim(12) > 0,75' kural metnindeki mutlak eşiktir."""

    ad, stil = "kapanis__ft-strategy004-s0573", "daytrade"
    varsayilan_parametreler = {"adx": 14, "slowadx": 35, "adx_a": 50.0, "adx_b": 26.0, "cci": 14, "fastk": 5, "yavas": 50,
                               "esik_h": 20.0, "esik_y": 30.0, "hacim_pen": 12, "hacim_esik": 0.75, "cik_adx": 25.0,
                               "cik_st": 70.0, "ema": 5, "sl": 0.10}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_ROI_5M_A, yalniz_karda_cikis=True)

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        fk, fd = _stochf(m, int(p["fastk"]))
        yk, yd = _stochf(m, int(p["yavas"]))
        adx = g.adx(m["yuksek"], m["dusuk"], kap, int(p["adx"]))["adx"]
        adx_y = g.adx(m["yuksek"], m["dusuk"], kap, int(p["slowadx"]))["adx"]
        cci = b2.cci(m["yuksek"], m["dusuk"], kap, int(p["cci"]))
        al = (((adx > float(p["adx_a"])) | (adx_y > float(p["adx_b"]))) & (cci < -100)
              & (fk.shift(1) < float(p["esik_h"])) & (fd.shift(1) < float(p["esik_h"]))
              & (yk.shift(1) < float(p["esik_y"])) & (yd.shift(1) < float(p["esik_y"]))
              & (fk.shift(1) < fd.shift(1)) & (fk > fd)
              & (g.sma(m["hacim"], int(p["hacim_pen"])) > float(p["hacim_esik"])))
        cik = ((adx_y < float(p["cik_adx"])) & ((fk > float(p["cik_st"])) | (fd > float(p["cik_st"])))
               & (fk.shift(1) < fd.shift(1)) & (kap > g.ema(kap, int(p["ema"]))))
        sl = float(p["sl"])
        return _bitir(cerceve(m, al, False, kap * (1 - sl), kap * (1 + sl)), cik)


# ================================================================ X005:584
class EmaDusukYuksekS0584(_Taban):
    """HAM:X005:584 (4h|1d, long-only): kapanış < EMA(düşük fiyat, 5) / 1,02 -> sonraki açılışta long; çıkış: kapanış > EMA(yüksek fiyat, 7)
    (cikis_long) YA DA girişten en az 2 mum sonra kapanış giriş fiyatının üstündeyse (kanca: tutulan >= min_tutma_mum ve kapanış >
    giriş fiyatı). Stop kaynakta yok: ATR(14)x3 (uyarlama)."""

    ad = "kapanis__ema-dusuk-yuksek-s0584"
    varsayilan_parametreler = {"ema_dusuk_n": 5, "sapma_bolen": 1.02, "ema_yuksek_n": 7, "min_tutma_mum": 2, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        mes = _atr_mesafe(m, int(p["atr_n"]), float(p["atr_k"]))
        al = kap < g.ema(m["dusuk"], int(p["ema_dusuk_n"])) / float(p["sapma_bolen"])
        return _bitir(cerceve(m, al, False, kap - mes, kap + mes), kap > g.ema(m["yuksek"], int(p["ema_yuksek_n"])))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return bool(d.tutulan_mum >= int(self.parametreler["min_tutma_mum"]) and d.kapanis > d.giris_fiyati)


# ================================================================ X005:629
class BbKurulumMacdS0629(_Taban):
    """HAM:X005:629 (5m + 1h, iki yön): 1h BB(20,2): bar yüksek >= üst bant -> short kurulumu aktif; bar düşük <= alt bant -> long kurulumu aktif
    (son kurulum geçerli; işlem sinyalinden sonra sıfırlanır). 5m MACD(12,26,9): long: önceki 5m barda MACD sinyali yukarı kesmiş VE
    kapanış > önceki 10 barın en yüksek yükseği (short ayna) -> giriş. Stop = min(giriş - 2 x ATR14, önceki 10 bar dibi) - 0,5 x ATR14;
    TP1 1R'de yarı (kismi), 2R'ye ulaşınca stop girişe (basabas_r_esigi); kalan pozisyon 1h orta banda (SMA20) temasta çıkar (kanca:
    5m mumun yüksek/düşük değerinin kapanmış 1h BB orta bandına değmesi, kapanışta sınanır). Üst TF yalnız kapanmış 1h mumdan.
    YAKLAŞIK: kurulum sıfırlaması sinyal düzeyindedir (sinyal = işlem varsayılır; pozisyon açıkken verilen sinyal motorca atlanırsa
    kurulum yine de tüketilmiş sayılır); orta bant teması mum kapanışında sınanır, çıkış sonraki açılışta."""

    ad, stil = "kapanis__bb-kurulum-macd-s0629", "scalp"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "macd_h": 12, "macd_y": 26, "macd_s": 9, "swing": 10, "atr_n": 14,
                               "stop_atr": 2.0, "tampon_atr": 0.5}
    cikis_ayarlari = CikisAyarlari(kismi=((1.0, 0.5),), basabas_r_esigi=2.0)

    def sinyaller(self, m):
        p = self.parametreler
        kap, h, lo = m["kapanis"], m["yuksek"], m["dusuk"]
        n_bb, k_bb = int(p["bb_n"]), float(p["bb_k"])

        def fonk(u: pd.DataFrame) -> pd.DataFrame:
            bb = g.bollinger(u["kapanis"], n_bb, k_bb)
            return pd.DataFrame({"ust": bb["ust"], "alt": bb["alt"], "orta": bb["orta"], "yuk": u["yuksek"], "dus": u["dusuk"],
                                 "no": pd.Series(np.arange(len(u), dtype=float), index=u.index)})

        s1 = ust_zaman(m, "1h", fonk)
        yeni = (s1["no"].notna() & (s1["no"] != s1["no"].shift(1))).to_numpy()
        ev_l = ((s1["dus"] <= s1["alt"]) & s1["alt"].notna()).to_numpy()
        ev_s = ((s1["yuk"] >= s1["ust"]) & s1["ust"].notna()).to_numpy()
        mc = g.macd(kap, int(p["macd_h"]), int(p["macd_y"]), int(p["macd_s"]))
        kes_l = yukari_kesis(mc["macd"], mc["sinyal"]).shift(1, fill_value=False)
        kes_s = asagi_kesis(mc["macd"], mc["sinyal"]).shift(1, fill_value=False)
        n = int(p["swing"])
        tetik_l = (kes_l & (kap > h.shift(1).rolling(n, min_periods=n).max())).to_numpy()
        tetik_s = (kes_s & (kap < lo.shift(1).rolling(n, min_periods=n).min())).to_numpy()
        gl, gs = np.zeros(len(m), bool), np.zeros(len(m), bool)
        kurulum = 0
        for t in range(len(m)):
            if yeni[t]:
                if ev_l[t] and not ev_s[t]:
                    kurulum = 1
                elif ev_s[t] and not ev_l[t]:
                    kurulum = -1
            if kurulum == 1 and tetik_l[t]:
                gl[t], kurulum = True, 0
            elif kurulum == -1 and tetik_s[t]:
                gs[t], kurulum = True, 0
        atr = g.atr(h, lo, kap, int(p["atr_n"]))
        dip = lo.shift(1).rolling(n, min_periods=n).min()
        tepe = h.shift(1).rolling(n, min_periods=n).max()
        tamp = float(p["tampon_atr"]) * atr
        stop_l = np.minimum(kap - float(p["stop_atr"]) * atr, dip) - tamp
        stop_s = np.maximum(kap + float(p["stop_atr"]) * atr, tepe) + tamp
        self._sakla(orta=s1["orta"], yuk=h, dus=lo)
        return cerceve(m, pd.Series(gl, index=m.index), pd.Series(gs, index=m.index), stop_l, stop_s)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        orta = self._dz("orta", i)
        if not math.isfinite(orta):
            return False
        return bool(self._dz("yuk", i) >= orta) if d.yon == 1 else bool(self._dz("dus", i) <= orta)


# ================================================================ X005:643 / 644
class ZSkorKismiS0643(_Taban):
    """HAM:X005:643 (1d, long-only): kapanışın 20 günlük z-skoru <= -2 VE RSI(14) < 40 VE ADX(14) < 20 -> al; engeller: hacim > 3 x ortalama
    (SMA20), fiyat 52 hafta (364 gün) zirvesinin %30'dan fazla altında, 52 hafta dibine %5'ten yakın. Çıkış: z >= +2 VE RSI > 60 VE ADX < 20
    (cikis_long); +%4'te yarım, +%8'de tam kâr al (kismi_yuzde); zirveden %5 iz süren stop (kanca: giriş sonrası en yüksek HIGH'dan kapanış
    %5 altı); azami 30 gün (zaman_cikisi_mum); stop giriş - 2,5 x ATR(14)."""

    ad = "kapanis__zskor-kismi-s0643"
    varsayilan_parametreler = {"z_n": 20, "z_giris": -2.0, "z_cikis": 2.0, "rsi_n": 14, "rsi_alim": 40.0, "rsi_satim": 60.0,
                               "adx_n": 14, "adx_max": 20.0, "hacim_engel": 3.0, "hacim_n": 20, "zirve52_engel": 0.30,
                               "dip52_engel": 0.05, "yil_gun": 364, "maks_gun": 30, "atr_stop": 2.5, "tp1": 4.0, "tp2": 8.0,
                               "iz": 5.0}

    def __init__(self, cikis_ayarlari: CikisAyarlari = None, **parametreler):
        super().__init__(cikis_ayarlari=cikis_ayarlari, **parametreler)
        if cikis_ayarlari is None:
            p = self.parametreler
            self.cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=int(p["maks_gun"]),
                                                kismi_yuzde=((float(p["tp1"]), 0.5), (float(p["tp2"]), 1.0)))

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        n = int(p["z_n"])
        z = (kap - g.sma(kap, n)) / kap.rolling(n, min_periods=n).std(ddof=0).where(lambda x: x > 0)
        rsi = g.rsi(kap, int(p["rsi_n"]))
        adx = g.adx(m["yuksek"], m["dusuk"], kap, int(p["adx_n"]))["adx"]
        yil = int(p["yil_gun"])
        hh = m["yuksek"].rolling(yil, min_periods=yil).max()
        ll = m["dusuk"].rolling(yil, min_periods=yil).min()
        engel = ((m["hacim"] > float(p["hacim_engel"]) * g.sma(m["hacim"], int(p["hacim_n"])))
                 | (kap < hh * (1.0 - float(p["zirve52_engel"]))) | (kap < ll * (1.0 + float(p["dip52_engel"]))))
        al = ((z <= float(p["z_giris"])) & (rsi < float(p["rsi_alim"])) & (adx < float(p["adx_max"])) & ~engel & hh.notna())
        mes = _atr_mesafe(m, 14, float(p["atr_stop"]))
        cik = (z >= float(p["z_cikis"])) & (rsi > float(p["rsi_satim"])) & (adx < float(p["adx_max"]))
        return _bitir(cerceve(m, al.fillna(False), False, kap - mes, kap + mes), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return tepe_geri_cekilme(d, float(self.parametreler["iz"]))


class RsiAdxKismiS0644(_Taban):
    """HAM:X005:644 (1d, long-only): kapanış > SMA(60) VE RSI(14) < 45 VE ADX(14) > 20 koşulları İLK KEZ birlikte sağlandığı gün (gecis) al;
    çıkış kapanış < SMA(60) ya da RSI(14) > 70 ya da 30 gün (zaman_cikisi_mum); +%4'te yarım, +%8'de tam kâr al (kismi_yuzde); %5 iz süren
    stop (kanca: giriş sonrası en yüksek HIGH'dan kapanış %5 altı); stop giriş - 2,5 x ATR(14)."""

    ad = "kapanis__rsi-adx-kismi-s0644"
    varsayilan_parametreler = {"sma": 60, "rsi_n": 14, "rsi_esik": 45.0, "adx_n": 14, "adx_min": 20.0, "rsi_cikis": 70.0,
                               "atr_stop": 2.5, "tp1": 4.0, "tp2": 8.0, "iz": 5.0, "maks_gun": 30}

    def __init__(self, cikis_ayarlari: CikisAyarlari = None, **parametreler):
        super().__init__(cikis_ayarlari=cikis_ayarlari, **parametreler)
        if cikis_ayarlari is None:
            p = self.parametreler
            self.cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=int(p["maks_gun"]),
                                                kismi_yuzde=((float(p["tp1"]), 0.5), (float(p["tp2"]), 1.0)))

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        sma = g.sma(kap, int(p["sma"]))
        rsi = g.rsi(kap, int(p["rsi_n"]))
        adx = g.adx(m["yuksek"], m["dusuk"], kap, int(p["adx_n"]))["adx"]
        kos = ((kap > sma) & (rsi < float(p["rsi_esik"])) & (adx > float(p["adx_min"]))).fillna(False)
        mes = _atr_mesafe(m, 14, float(p["atr_stop"]))
        return _bitir(cerceve(m, gecis(kos), False, kap - mes, kap + mes), (kap < sma) | (rsi > float(p["rsi_cikis"])))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return tepe_geri_cekilme(d, float(self.parametreler["iz"]))


# ================================================================ X005:699
class BbAgirlikliKapanisS0699(_Taban):
    """HAM:X005:699 (4h|1d, iki yön): kapanış < alt bant ya da düşük <= alt bant (Bollinger 20, 3σ; orta çizgi ağırlıklı MA = WMA(20), σ = kapanış
    popülasyon std) -> sonraki açılışta long; kapanış > üst bant ya da yüksek >= üst bant -> short. Long çıkış: kapanış >= SMA(20) YA DA
    önceki kapanış giriş fiyatının üstünde (kanca: kapanış > giriş fiyatı); short çıkış: kapanış <= SMA(20) YA DA önceki kapanış giriş
    fiyatının ÜSTÜNE çıkarsa (kaynaktaki asimetri aynen: kanca short için de kapanış > giriş fiyatı). Stop kaynakta yok: ATR(14)x3."""

    ad = "kapanis__bb3-agirlikli-s0699"
    varsayilan_parametreler = {"bb_n": 20, "bb_sigma": 3.0, "cikis_sma_n": 20, "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        n = int(p["bb_n"])
        orta = _wma(kap, n)
        std = kap.rolling(n, min_periods=n).std(ddof=0)
        ust, alt = orta + float(p["bb_sigma"]) * std, orta - float(p["bb_sigma"]) * std
        sma = g.sma(kap, int(p["cikis_sma_n"]))
        mes = _atr_mesafe(m, int(p["atr_n"]), float(p["atr_k"]))
        al = ((kap < alt) | (m["dusuk"] <= alt)).fillna(False)
        sat = ((kap > ust) | (m["yuksek"] >= ust)).fillna(False)
        return _bitir(cerceve(m, al, sat, kap - mes, kap + mes), kap >= sma, kap <= sma)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return bool(d.kapanis > d.giris_fiyati)


# ================================================================ X005:726
class RsiIkiBacakHaftalikS0726(_Taban):
    """HAM:X005:726 (1w -> 1d mumlarla; long): yavaş bacak: RSI(17) 60'ı yukarı keser VE kapanış > SMA(40) -> al; çıkış RSI(17) < 40 ya da
    kapanış < SMA(40). Hızlı bacak (yavaş RSI düşüşteyken, RSI17[t] < RSI17[t-1]): RSI(5) 60'ı yukarı keser VE kapanış > SMA(10) -> al; çıkış
    RSI(5) < 40 ya da kapanış < SMA(10). Çıkış kuralı pozisyonu açan bacağa bağlıdır (kanca: giriş sinyali mumundaki bacak; ikisi de
    doğarsa yavaş). Haftalık değerler htf.ust_zaman('1w') ile kapanmış haftadan; karar yeni haftanın ilk günü (VARYANTLAR tf = '1d').
    Stop yok: ATR(14)x3 (günlük)."""

    ad = "kapanis__rsi-iki-bacak-haftalik-s0726"
    varsayilan_parametreler = {"rsi_yavas": 17, "ma_yavas": 40, "rsi_hizli": 5, "ma_hizli": 10, "al": 60.0, "sat": 40.0,
                               "atr_n": 14, "atr_k": 3.0}

    def sinyaller(self, m):
        p = self.parametreler
        ry, my, rh, mh = int(p["rsi_yavas"]), int(p["ma_yavas"]), int(p["rsi_hizli"]), int(p["ma_hizli"])

        def fonk(u: pd.DataFrame) -> pd.DataFrame:
            k = u["kapanis"]
            r17, r5 = g.rsi(k, ry), g.rsi(k, rh)
            return pd.DataFrame({"kw": k, "r17": r17, "r17p": r17.shift(1), "sy": g.sma(k, my), "r5": r5, "r5p": r5.shift(1),
                                 "sh": g.sma(k, mh), "no": pd.Series(np.arange(len(u), dtype=float), index=u.index)})

        w = ust_zaman(m, "1w", fonk)
        yeni = w["no"].notna() & (w["no"] != w["no"].shift(1))
        al_, sat_ = float(p["al"]), float(p["sat"])
        yavas_al = yeni & (w["r17p"] <= al_) & (w["r17"] > al_) & (w["kw"] > w["sy"])
        hizli_al = yeni & (w["r17"] < w["r17p"]) & (w["r5p"] <= al_) & (w["r5"] > al_) & (w["kw"] > w["sh"])
        cik_y = (w["r17"] < sat_) | (w["kw"] < w["sy"])
        cik_h = (w["r5"] < sat_) | (w["kw"] < w["sh"])
        kap = m["kapanis"]
        mes = _atr_mesafe(m, int(p["atr_n"]), float(p["atr_k"]))
        self._sakla(yavas=yavas_al, cik_y=cik_y, cik_h=cik_h)
        return cerceve(m, yavas_al | hizli_al, False, kap - mes, kap + mes)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i, s = d.mum_indeksi, d.giris_mum_indeksi - 1
        if not self._var(i):
            return False
        yavas = self._dz("yavas", s) == 1.0
        return self._dz("cik_y" if yavas else "cik_h", i) == 1.0


# ================================================================ X005:736
class SmaBantIzS0736(_Taban):
    """HAM:X005:736 (4h|1d, long-only): kapanış SMA(10) x 1,03 üzerine çıkınca al; kapanış SMA(10) x 0,96 altına inince sat (cikis_long); stop:
    ilk 3 bar %2 sabit stop (sinyal stopu = kapanış x 0,98, bar içi), ardından %2 izleyen stop (kanca: tutulan >= 3 ve kapanış, giriş sonrası
    en yüksek HIGH'ın %2 altında ya da altında). Sabit stop her zaman geçerlidir (izleyen stop ondan daha gevşek olamaz)."""

    ad = "kapanis__sma-bant-iz-s0736"
    varsayilan_parametreler = {"sma_n": 10, "giris_pct": 3.0, "cikis_pct": 4.0, "stop_pct": 2.0, "stop_ilk_bar": 3}

    def sinyaller(self, m):
        p = self.parametreler
        kap = m["kapanis"]
        sma = g.sma(kap, int(p["sma_n"]))
        sl = float(p["stop_pct"]) / 100.0
        return _bitir(cerceve(m, kap > sma * (1 + float(p["giris_pct"]) / 100.0), False, kap * (1 - sl), kap * (1 + sl)),
                      kap < sma * (1 - float(p["cikis_pct"]) / 100.0))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        p = self.parametreler
        return bool(d.tutulan_mum >= int(p["stop_ilk_bar"]) and tepe_geri_cekilme(d, float(p["stop_pct"])))


# ================================================================ X005:879
class FlipperKancaS0879(_Taban):
    """HAM:X005:879 (1d, long): son salınım dibinden (gün içi diplerle izlenir) kapanış %20 yükselince al; giriş sonrası izlenen en yüksek tepeden
    kapanış %20 düşünce sat (kanca: giriş sonrası en yüksek HIGH, sinyal mumunun yükseği dahil). Giriş zigzag durumu yalnız fiyattan yürür
    (`k2_kaynak.FlipperS0879.zigzag`); çıkış sanal değil gerçek pozisyonun zirvesinden. Koruyucu stop (kaynakta yok; uyarlama): giriş
    sinyal mumunun yükseğinin %20 altı. NOT: K2'deki FlipperS0879 ile aynı hipotez, bu sınıf çıkışı gerçek pozisyondan alır."""

    ad = "kapanis__flipper-kanca-s0879"
    varsayilan_parametreler = {"yuzde": 0.20}

    def sinyaller(self, m):
        y = float(self.parametreler["yuzde"])
        giris, _cikis, gtepe = FlipperS0879.zigzag(m["kapanis"].to_numpy(float), m["yuksek"].to_numpy(float),
                                                    m["dusuk"].to_numpy(float), y)
        idx = m.index
        stop = pd.Series(gtepe * (1 - y), index=idx)
        self._sakla(yuk=m["yuksek"])
        return cerceve(m, pd.Series(giris, index=idx), False, stop, stop)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        y = float(self.parametreler["yuzde"])
        t = max(d.en_yuksek, self._dz("yuk", d.giris_mum_indeksi - 1))
        return bool(d.kapanis <= t * (1.0 - y))


# ================================================================ koşu listesi
SINIFLAR = [KdjJdS0004, FtStrategy002S0020, FtStrategy003S0021, FtStrategy005S0022, KcEmaTrendS0060, SupertrendIkiliKademeS0079,
            MacdMinMaksS0400, RocMinMaksS0401, RsiMinMaksS0416, MacdHistRsiAtrS0436, KamaGeriDonusS0446, RejimAdxKapanisIzS0447,
            FtStrategy004S0573, EmaDusukYuksekS0584, BbKurulumMacdS0629, ZSkorKismiS0643, RsiAdxKismiS0644,
            BbAgirlikliKapanisS0699, RsiIkiBacakHaftalikS0726, SmaBantIzS0736, FlipperKancaS0879]


def _v(no: int, sinif, tf: str, **ek) -> dict:
    k = {"kimlik": f"HAM:X005:{sinif.ad.rsplit('-s', 1)[1].lstrip('0')}#v{no}", "sinif": sinif.ad,
         "parametreler": dict(sinif.varsayilan_parametreler), "tf": tf}
    k.update(ek)
    return k


VARYANTLAR = [
    _v(1, KdjJdS0004, "1d"),
    _v(1, FtStrategy002S0020, "5m"),
    _v(1, FtStrategy003S0021, "5m"),
    _v(1, FtStrategy005S0022, "5m"),
    _v(1, KcEmaTrendS0060, "15m", yaklasik=True),
    _v(2, KcEmaTrendS0060, "1h", yaklasik=True),
    _v(3, KcEmaTrendS0060, "4h", yaklasik=True),
    _v(4, KcEmaTrendS0060, "1d", yaklasik=True),
    _v(1, SupertrendIkiliKademeS0079, "6h"),
    _v(1, MacdMinMaksS0400, "1d"),
    _v(1, RocMinMaksS0401, "1d"),
    _v(1, RsiMinMaksS0416, "1d"),
    _v(1, MacdHistRsiAtrS0436, "1d"),
    _v(1, KamaGeriDonusS0446, "1d"),
    _v(1, RejimAdxKapanisIzS0447, "1d", emin_degil=True),
    _v(1, FtStrategy004S0573, "5m"),
    _v(1, EmaDusukYuksekS0584, "4h"),
    _v(2, EmaDusukYuksekS0584, "1d"),
    _v(1, BbKurulumMacdS0629, "5m", yaklasik=True),
    _v(1, ZSkorKismiS0643, "1d"),
    _v(1, RsiAdxKismiS0644, "1d"),
    _v(1, BbAgirlikliKapanisS0699, "4h"),
    _v(2, BbAgirlikliKapanisS0699, "1d"),
    _v(1, RsiIkiBacakHaftalikS0726, "1d"),
    _v(1, SmaBantIzS0736, "4h"),
    _v(2, SmaBantIzS0736, "1d"),
    _v(1, FlipperKancaS0879, "1d"),
]

KODLANAMADI = [
    {"kimlik": "HAM:X005:114",
     "neden": ("iki kademeli çıkış yine ifade edilemiyor: lot1 hedefi GİRİŞ ANINA göre değişen dinamik orta banttır (SMA20), motorun kısmi çıkışı "
               "yalnız sınıf düzeyinde sabit R / sabit yüzde seviyesidir (kismi, kismi_yuzde); kanca yalnız pozisyonun TAMAMINI kapatır. Hedef "
               "sonrası kalan lotun stopunu başabaşa çekmek de seviye bazlıdır. Tek lota indirgemek kuralı değiştirir.")},
    {"kimlik": "HAM:X005:419",
     "neden": ("stop-and-reverse durum makinesi: pozisyon açıkken her barda kurulan reverseToLong/Short bayrakları (stop-out sonrası ters yöne giriş "
               "yan etkisi), overBand/underBand istisnasında çıkış yerine stop=low[1] / high[1] emri ve bar içi tetiklenen, EMA(12) - 2 x ATR "
               "tabanlı yukarı kayan (max(önceki stop, ...)) stop; motorun iz süren stopu ATR/ekstrem bazlıdır (EMA bazlı yok), kanca yalnız "
               "kapanışta çıkış verebilir ve kaynağın kendi bayrak durumu pozisyon/kanca arayüzüyle yeniden kurulamıyor (uydurma yaklaşık yok)")},
]
