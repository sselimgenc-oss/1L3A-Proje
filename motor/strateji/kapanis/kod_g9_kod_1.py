"""Kapanış turu, kodlama partisi g9_kod_1 (girdi: sonuclar/kapanis/kod_girdi/g9_kod_1.csv, 29 kaynak satırı, Robotic HAM:B001).

Her sınıf kaynak dosyadan (RoboticAutomations/freqtradestrategies, etkin değerler: .json > buy_params/sell_params > Parameter
varsayılanı) okunup kendi cümlelerimizle yazılmış bir uyarlamadır; üçüncü taraf kodu kopyalanmadı. Sinyal kapanmış mumdan,
dolum sonraki açılıştan (motor). Hepsi nedensel; üst zaman dilimi yalnız `motor.strateji.htf.ust_zaman` ile KAPANMIŞ mumdan.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa ya da <= -%50 ise stop = kapanış -/+ 3 x ATR(14); yüzde stoplar sinyal kapanışından.
- Freqtrade `minimal_roi` (dakika) -> `CikisAyarlari.azalan_roi` (mum = yukarı yuvarlanmış dakika / TF; aynı muma düşen
  basamakta büyük dakikalı geçerli; "0" ROI anahtarı kâr >= 0). `trailing_stop_positive` + offset ->
  `geri_cekilme_yuzde` + `geri_cekilme_min_kar_yuzde` (kâr% farkı, kapanış bazlı); `trailing_only_offset_is_reached=False`
  satırında min kâr 0 (kaynakta offset öncesi mesafe `stoploss`'tur; ön kayıt eşlemesi uygulandı). `sell_profit_only` ->
  `yalniz_karda_cikis`.
- `custom_stoploss` / `custom_sell` / `custom_exit` kapanış bazlı `pozisyon_cikisi` kancasında (çıkış sonraki açılışta, neden
  "kanca"). Freqtrade'in "stop yalnız yukarı taşınır" kuralı, o ana kadarki KAPANIŞLARDAN (giriş mumundan bir önceki kapanışa)
  hesaplanan en yüksek stop seviyesiyle taşınır; kapanış bu seviyenin altına (eşit/altına) inerse çıkılır. Kaynakta mum içi
  (high/low) sınanır; burada kapanış bazlıdır. `trade.max_rate/min_rate` = PozisyonDurumu en_yuksek/en_dusuk.
- Korumalar (cooldown, StoplossGuard, LowProfitPairs, MaxDrawdown), `ignore_roi_if_buy_signal`, kaldıraç, `custom_stake_amount`,
  emir tipi/fiyatı motor dışıdır; uygulanmadı.
- qtpylib/Freqtrade göstergeleri (bollinger_bands, atr) kaynaktaki tanımla (std ddof=1; qtpylib.atr = TR'nin SMA'sı), TA-Lib
  göstergeleri Wilder/EMA ile (mevcut `gostergeler.py`).

KODLANAMADI satırları dosya sonundaki listededir (neden satır başına yazılı).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b2
from motor.strateji._gosterge_d11j import hma as _hma
from motor.strateji._gosterge_d11j import mfi as _mfi
from motor.strateji._gosterge_d11j import stoch_rsi as _stoch_rsi
from motor.strateji._gosterge_d11j import williams_r as _wr
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d5 import cti as _cti
from motor.strateji.dis._gosterge_d5 import kama as _kama
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, roi_tablosu
from motor.strateji.seans_takvimi import mum_suresi
from motor.strateji.temel import Strateji

yukari = b2.yukari_kesis
asagi = b2.asagi_kesis


# ---------------------------------------------------------------- yardımcılar
def _tf_dk(m: pd.DataFrame) -> float:
    return float(mum_suresi(m.index) / pd.Timedelta(minutes=1))


def _tipik(m: pd.DataFrame) -> pd.Series:
    return (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0


def _bb(src: pd.Series, n: int, k: float) -> pd.DataFrame:
    """Kaynaktaki Bollinger: orta = SMA, bant = orta -/+ k x std (pandas varsayılanı, ddof=1)."""
    orta = src.rolling(n, min_periods=n).mean()
    s = src.rolling(n, min_periods=n).std()
    return pd.DataFrame({"alt": orta - k * s, "orta": orta, "ust": orta + k * s})


def _ewo(kap: pd.Series, hizli: int, yavas: int, tur: str = "ema", payda: pd.Series | None = None) -> pd.Series:
    f = g.ema if tur == "ema" else g.sma
    return (f(kap, hizli) - f(kap, yavas)) / (kap if payda is None else payda) * 100.0


def _atr_sma(m: pd.DataFrame, n: int) -> pd.Series:
    """qtpylib.atr(exp=False): gerçek aralığın basit ortalaması."""
    tr = g.gercek_aralik(m["yuksek"], m["dusuk"], m["kapanis"])
    return tr.rolling(n, min_periods=n).mean()


def _stoplar(m: pd.DataFrame, sl: float | None) -> tuple[pd.Series, pd.Series]:
    """(long stop, short stop). sl: kaynak stop oranı (pozitif, örn. 0.05); None ya da >= 0.50 ise ATR(14) x 3."""
    kap = m["kapanis"]
    if sl is None or sl >= 0.50:
        mes = 3.0 * g.atr(m["yuksek"], m["dusuk"], kap, 14)
        return kap - mes, kap + mes
    return kap * (1.0 - sl), kap * (1.0 + sl)


def _bitir(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _ca(roi: dict | None = None, tf_dk: float = 5.0, iz: tuple | None = None, yalniz_kar: bool = False,
        kar_esik: float = 0.0) -> CikisAyarlari:
    """roi: {dakika: oran}; iz: (trailing_stop_positive, offset) (oranlar); yalniz_kar: sell_profit_only."""
    kw: dict = {}
    if roi:
        kw["azalan_roi"] = roi_tablosu(roi, tf_dk)
    if iz:
        kw["geri_cekilme_yuzde"] = round(float(iz[0]) * 100.0, 6)
        kw["geri_cekilme_min_kar_yuzde"] = round(float(iz[1]) * 100.0, 6)
    if yalniz_kar:
        kw["yalniz_karda_cikis"] = True
        kw["yalniz_karda_min_kar_yuzde"] = float(kar_esik)
    return CikisAyarlari(**kw)


def _rmi(kap: pd.Series, n: int, mom: int) -> pd.Series:
    """Relative Momentum Index (technical.RMI tanımı; CryptoFrog.py içindeki kopyasıyla aynı)."""
    art = (kap - kap.shift(mom)).clip(lower=0).fillna(0.0)
    azl = (kap.shift(mom) - kap).clip(lower=0).fillna(0.0)
    ei, ed = g.ema(art, n), g.ema(azl, n)
    return pd.Series(np.where(ed == 0, 0.0, 100.0 - 100.0 / (1.0 + ei / ed)), index=kap.index)


def _fastk(m: pd.DataFrame, n: int) -> pd.Series:
    hh, ll = m["yuksek"].rolling(n, min_periods=n).max(), m["dusuk"].rolling(n, min_periods=n).min()
    return 100.0 * (m["kapanis"] - ll) / (hh - ll).where(lambda x: x > 0)


def _trima(x: pd.Series, n: int) -> pd.Series:
    """TA-Lib TRIMA: ortalamanın ortalaması (tek n: (n+1)/2, çift n: n/2 ve n/2+1)."""
    if n % 2:
        k = (n + 1) // 2
        return g.sma(g.sma(x, k), k)
    return g.sma(g.sma(x, n // 2), n // 2 + 1)


def _t3(x: pd.Series, n: int, v: float = 0.7) -> pd.Series:
    """TA-Lib T3 (vfactor 0,7): altı kat EMA zinciri."""
    e = [g.ema(x, n)]
    for _ in range(5):
        e.append(g.ema(e[-1], n))
    c1, c2 = -v ** 3, 3 * v ** 2 + 3 * v ** 3
    c3, c4 = -6 * v ** 2 - 3 * v - 3 * v ** 3, 1 + 3 * v + v ** 3 + 3 * v ** 2
    return c1 * e[5] + c2 * e[4] + c3 * e[3] + c4 * e[2]


def _ssl(u: pd.DataFrame, n: int) -> tuple[pd.Series, pd.Series]:
    """SSL kanalı (ATR'li): (sslDown, sslUp)."""
    a = g.atr(u["yuksek"], u["dusuk"], u["kapanis"], 14)
    ust = u["yuksek"].rolling(n, min_periods=n).mean() + a
    alt = u["dusuk"].rolling(n, min_periods=n).mean() - a
    hlv = pd.Series(np.where(u["kapanis"] > ust, 1.0, np.where(u["kapanis"] < alt, -1.0, np.nan)), index=u.index).ffill()
    asg = pd.Series(np.where(hlv < 0, ust, alt), index=u.index)
    yks = pd.Series(np.where(hlv < 0, alt, ust), index=u.index)
    return asg, yks


def _cmf(m: pd.DataFrame, n: int = 20) -> pd.Series:
    ara = (m["yuksek"] - m["dusuk"])
    mfv = (((m["kapanis"] - m["dusuk"]) - (m["yuksek"] - m["kapanis"])) / ara).fillna(0.0) * m["hacim"]
    return mfv.rolling(n, min_periods=1).sum() / m["hacim"].rolling(n, min_periods=1).sum()


def _vwma(m: pd.DataFrame, n: int) -> pd.Series:
    pv = (m["kapanis"] * m["hacim"]).rolling(n, min_periods=n).mean()
    return (pv / m["hacim"].rolling(n, min_periods=n).mean()).fillna(0.0)


def _ema_vwma_osc(m: pd.DataFrame, n: int) -> pd.Series:
    e = g.ema(_vwma(m, n), n)
    return (e - e.shift(1)) / e.shift(1) * 100.0


def _ha(m: pd.DataFrame) -> pd.DataFrame:
    return b2.heikin_ashi(m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"])


def _rocr_1h(m: pd.DataFrame, n: int = 168) -> pd.Series:
    """1h Heikin-Ashi kapanışının n bar ROCR'ı (kapanmış 1h mumdan)."""
    def f(u):
        hc = _ha(u)["ha_kapanis"]
        return hc / hc.shift(n)
    return ust_zaman(m, "1h", f)


def _pf_seviye(kar: float, hsl, pf1: float, sl1: float, pf2: float, sl2: float):
    """Freqtrade (pHSL/pPF/pSL) kâr-kilit stop seviyesi (açılışa göre kâr oranı); hsl None ise kâr basamağı yokken None."""
    if kar > pf2:
        return sl2 + (kar - pf2)
    if kar > pf1:
        return sl1 + (kar - pf1) * (sl2 - sl1) / (pf2 - pf1)
    return hsl


class _KancaTaban(KancaDestek, Strateji):
    stil = "daytrade"
    parametre_izgarasi = {}
    _tf = 5.0           # mum süresi (dk); sinyaller() günceller

    def cikis_var_mi(self) -> bool:
        return True

    # ---- ortak kanca parçaları
    def _pf_cik(self, d: PozisyonDurumu, hsl, pf1: float, sl1: float, pf2: float, sl2: float) -> bool:
        """pHSL/pPF/pSL kâr-kilit stopu: seviye, giriş sonrası (önceki) kapanışlardaki zirve kârdan; kâr seviyenin altına inerse çık."""
        kv = self._kd["kap"]
        bas, i = d.giris_mum_indeksi, d.mum_indeksi
        zirve = float(np.nanmax(kv[bas:i])) / d.giris_fiyati - 1.0 if i > bas else d.kar_yuzde / 100.0
        sev = _pf_seviye(zirve, hsl, pf1, sl1, pf2, sl2)
        return sev is not None and d.kar_yuzde / 100.0 <= sev

    def _zarar_kilit(self, d: PozisyonDurumu, sure_dk: float, oran: float = 0.01, ek_esik: float | None = None,
                     ek_dizi: str | None = None) -> bool:
        """custom_stoploss: zararda ve sure_dk'dan uzun süredir açıksa (ya da ek koşul: kâr < ek_esik VE ek_dizi bayrağı) stop = o
        mumun kapanışının %oran altı, yalnız yukarı taşınır; kapanış önceki mumlardan gelen en yüksek stopun altına inerse çık."""
        kv = self._kd["kap"]
        bas, i = d.giris_mum_indeksi, d.mum_indeksi
        if i <= bas:
            return False
        kj = kv[bas:i]
        j = np.arange(bas, i)
        uygun = (kj < d.giris_fiyati) & ((j - bas) * self._tf > sure_dk)
        if ek_esik is not None and ek_dizi is not None:
            uygun |= (kj / d.giris_fiyati - 1.0 < ek_esik) & (self._kd[ek_dizi][bas:i] > 0.5)
        if not uygun.any():
            return False
        return bool(d.kapanis <= np.max(kj[uygun] * (1.0 - oran)))

    def _iz_stop(self, d: PozisyonDurumu, tablo: tuple, varsayilan: float) -> bool:
        """custom_stoploss kâr basamakları: her kapanışta stop = kapanış x (1 - mesafe(kâr)), mesafe tabloda ilk eşleşen
        (kâr > eşik) basamak, yoksa `varsayilan` (kaynak stopu); yalnız yukarı taşınır."""
        kv = self._kd["kap"]
        bas, i = d.giris_mum_indeksi, d.mum_indeksi
        if i <= bas:
            return False
        kj = kv[bas:i]
        kar = kj / d.giris_fiyati - 1.0
        mes = np.full(len(kj), float(varsayilan))
        for esik, m_ in reversed(tablo):
            mes = np.where(kar > esik, float(m_), mes)
        return bool(d.kapanis <= np.nanmax(kj * (1.0 - mes)))


# ================================================================ Elliott / offset ailesi
class _OfsetEwo(Strateji):
    """EMA(n) x low_offset altında kapanış + EWO kolları (VEYA); çıkış kapanış > EMA(m) x high_offset. İsteğe bağlı short
    (221: çıkışın aynası). Parametreler satır sınıflarında."""

    stil = "daytrade"
    parametre_izgarasi = {}
    varsayilan_parametreler = {"ma_al": 31, "low_offset": 0.978, "ma_sat": 99, "high_offset": 1.054, "ewo_hizli": 50,
                               "ewo_yavas": 200, "ewo_tur": "ema", "ewo_yuksek": 4.471, "ewo_dusuk": -13.043,
                               "rsi_al": 63.0, "sl": 0.179, "kisa": False}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        vol = mumlar["hacim"] > 0
        ewo = _ewo(kap, int(p["ewo_hizli"]), int(p["ewo_yavas"]), str(p["ewo_tur"]))
        taban = kap < g.ema(kap, int(p["ma_al"])) * float(p["low_offset"])
        kol = taban & (ewo > float(p["ewo_yuksek"]))
        if p["rsi_al"]:
            kol &= g.rsi(kap, 14) < float(p["rsi_al"])
        if p["ewo_dusuk"] is not None:
            kol |= taban & (ewo < float(p["ewo_dusuk"]))
        kol &= vol
        cik = (kap > g.ema(kap, int(p["ma_sat"])) * float(p["high_offset"])) & vol
        sl_l, sl_s = _stoplar(mumlar, float(p["sl"]))
        if p["kisa"]:
            return _bitir(cerceve(mumlar, kol, cik, sl_l, sl_s), cik, kol)
        return _bitir(cerceve(mumlar, kol, False, sl_l, sl_s), cik)


class OverwatchB0105(_OfsetEwo):
    """HAM:B001:105 (1h, long; overwatch.json etkin): kapanış < EMA(19) x 0,903 VE ((EWO(50,200) > 5,775 VE RSI(14) < 44) VEYA
    EWO < -19,765) VE hacim > 0 -> long; çıkış kapanış > EMA(58) x 1,098. ROI {0:.354, 320:.178, 501:.04, 1841:0}; stop -%31,1;
    iz süren %0,5 (offset %3, yalnız offset sonrası)."""

    ad, stil = "kapanis__overwatch-b0105", "swing"
    varsayilan_parametreler = {"ma_al": 19, "low_offset": 0.903, "ma_sat": 58, "high_offset": 1.098, "ewo_hizli": 50,
                               "ewo_yavas": 200, "ewo_tur": "ema", "ewo_yuksek": 5.775, "ewo_dusuk": -19.765,
                               "rsi_al": 44.0, "sl": 0.311, "kisa": False}
    cikis_ayarlari = _ca({0: 0.354, 320: 0.178, 501: 0.04, 1841: 0.0}, 60, (0.005, 0.03))


class ElB0221(_OfsetEwo):
    """HAM:B001:221 (5m, long+short; el.py): EWO = (SMA5 - SMA35)/kapanış x 100. Long: kapanış < EMA(12) x 0,915 VE ((EWO > 4,428
    VE RSI(14) < 44) VEYA EWO < -12,383) VE hacim > 0; long çıkış: kapanış > EMA(72) x 1,008 VE hacim > 0. Short: giriş = long
    çıkış koşulu; short çıkış = long giriş koşulları. ROI 10 basamaklı tablo; stop -%5; iz süren %0,5 (offset %3). Kaldıraç 10
    kaynakta, motor 1x."""

    ad = "kapanis__el-b0221"
    varsayilan_parametreler = {"ma_al": 12, "low_offset": 0.915, "ma_sat": 72, "high_offset": 1.008, "ewo_hizli": 5,
                               "ewo_yavas": 35, "ewo_tur": "sma", "ewo_yuksek": 4.428, "ewo_dusuk": -12.383,
                               "rsi_al": 44.0, "sl": 0.05, "kisa": True}
    cikis_ayarlari = _ca({0: 0.5, 60: 0.45, 120: 0.4, 240: 0.3, 360: 0.25, 720: 0.2, 1440: 0.15, 2880: 0.1,
                          3600: 0.05, 7200: 0.02}, 5, (0.005, 0.03))


class ElliotV2B0558(_OfsetEwo):
    """HAM:B001:558 (5m, long; ElliotV2.py): kapanış < EMA(31) x 0,978 VE ((EWO(50,200) > 4,471 VE RSI(14) < 63) VEYA EWO <
    -13,043) VE hacim > 0; çıkış kapanış > EMA(99) x 1,054. ROI {0:.154, 18:.074, 50:.039, 165:.02}; stop -%17,9; iz süren %1
    (offset %4,9). custom_stoploss kaynakta tanımlı değil."""

    ad = "kapanis__elliotv2-b0558"
    cikis_ayarlari = _ca({0: 0.154, 18: 0.074, 50: 0.039, 165: 0.02}, 5, (0.01, 0.049))


class ElliotV5HoB0561(_OfsetEwo):
    """HAM:B001:561 (5m, long; ElliotV5HO.py): kapanış < EMA(11) x 0,979 VE ((EWO(50,200) > 2,337 VE RSI(14) < 55) VEYA EWO <
    -15,87) VE hacim > 0; çıkış kapanış > EMA(17) x 0,997. ROI {0:.051, 20:.032, 45:.016, 70:0}; stop -%30,2; iz süren %0,5
    (offset %3). Uyarlama: kaynakta `custom_stoploss` (kâr basamakları) YAZILI ama `use_custom_stoploss=False` olduğundan
    çalışmaz; kural_tam özetindeki basamaklı stop uygulanmadı."""

    ad = "kapanis__elliotv5ho-b0561"
    varsayilan_parametreler = {"ma_al": 11, "low_offset": 0.979, "ma_sat": 17, "high_offset": 0.997, "ewo_hizli": 50,
                               "ewo_yavas": 200, "ewo_tur": "ema", "ewo_yuksek": 2.337, "ewo_dusuk": -15.87,
                               "rsi_al": 55.0, "sl": 0.302, "kisa": False}
    cikis_ayarlari = _ca({0: 0.051, 20: 0.032, 45: 0.016, 70: 0.0}, 5, (0.005, 0.03))


class SmaOfsetProtectB0694(_OfsetEwo):
    """HAM:B001:694 (5m, long; SMAOffsetProtectOptV1.py): kapanış < EMA(16) x 0,978 VE ((EWO(50,200) > 5,638 VE RSI(14) < 61)
    VEYA EWO < -19,993) VE hacim > 0; çıkış kapanış > EMA(49) x 1,006 VEYA ROI %1 (azalan_roi). Kaynak stopu -%50 (fiilen
    stopsuz) -> ATR(14) x 3 (ön kayıt uyarlaması)."""

    ad = "kapanis__smaofset-protect-b0694"
    varsayilan_parametreler = {"ma_al": 16, "low_offset": 0.978, "ma_sat": 49, "high_offset": 1.006, "ewo_hizli": 50,
                               "ewo_yavas": 200, "ewo_tur": "ema", "ewo_yuksek": 5.638, "ewo_dusuk": -19.993,
                               "rsi_al": 61.0, "sl": 0.50, "kisa": False}
    cikis_ayarlari = _ca({0: 0.01}, 5)


class NotAnotherSmaLiteB0673(_OfsetEwo):
    """HAM:B001:673 (5m, long; NotAnotherSMAOffsetStrategyLite.py): kapanış < EMA(14) x 0,975 VE EWO(50,200) > 0 VE hacim > 0;
    çıkış kapanış > EMA(24) x 0,991 VE hacim > 0. ROI %2,5; stop -%10. Uyarlama: kaynakta `custom_stoploss` (12 saat sonra
    kâr < -%5 ise -%1) YAZILI ama `use_custom_stoploss` açılmadığından çalışmaz; uygulanmadı."""

    ad = "kapanis__sma-ofset-lite-b0673"
    varsayilan_parametreler = {"ma_al": 14, "low_offset": 0.975, "ma_sat": 24, "high_offset": 0.991, "ewo_hizli": 50,
                               "ewo_yavas": 200, "ewo_tur": "ema", "ewo_yuksek": 0.0, "ewo_dusuk": None,
                               "rsi_al": 0.0, "sl": 0.10, "kisa": False}
    cikis_ayarlari = _ca({0: 0.025}, 5)


class MultiOffsetLamboB0666(Strateji):
    """HAM:B001:666 (5m, long; MultiOffsetLamboV0.py): MA türleri sma, ema, trima, t3, kama (hepsi 16 mum, kaynakta kural_tam
    özetindeki hma/zema DEĞİL): her tür için kapanış < MA(16) x 0,958 VE (EWO(50,200) < -19,993 VEYA EWO > 5,638) VE hacim > 0
    (türler VEYA); çıkış: türlerden biri için kapanış > MA(49) x 1,012 VE hacim > 0. ROI %1 (azalan_roi). Kaynak stopu -%50 ->
    ATR(14) x 3."""

    ad, stil = "kapanis__multi-offset-lambo-b0666", "daytrade"
    varsayilan_parametreler = {"ma_al": 16, "ma_sat": 49, "low_offset": 0.958, "high_offset": 1.012, "ewo_hizli": 50,
                               "ewo_yavas": 200, "ewo_yuksek": 5.638, "ewo_dusuk": -19.993, "sl": 0.50}
    parametre_izgarasi = {}
    cikis_ayarlari = _ca({0: 0.01}, 5)

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def _ma(kap: pd.Series, tur: str, n: int) -> pd.Series:
        return {"sma": g.sma, "ema": g.ema, "trima": _trima, "t3": _t3, "kama": _kama}[tur](kap, n)

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        vol = mumlar["hacim"] > 0
        ewo = _ewo(kap, int(p["ewo_hizli"]), int(p["ewo_yavas"]))
        kosul = (ewo < float(p["ewo_dusuk"])) | (ewo > float(p["ewo_yuksek"]))
        al = pd.Series(False, index=mumlar.index)
        sat = pd.Series(False, index=mumlar.index)
        for tur in ("sma", "ema", "trima", "t3", "kama"):
            al |= (kap < self._ma(kap, tur, int(p["ma_al"])) * float(p["low_offset"])) & kosul & vol
            sat |= (kap > self._ma(kap, tur, int(p["ma_sat"])) * float(p["high_offset"])) & vol
        sl_l, sl_s = _stoplar(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl_l, sl_s), sat)


# ================================================================ AngleWave ailesi
class _AngleWave(_KancaTaban):
    """EWO(hızlı, yavaş) + ATR'li bant + açı kolları; kâr basamaklı stop kancada (her kapanışta stop = kapanış x (1 - mesafe))."""

    KOLLAR = (1, 2, 3, 4, 5, 6)
    RSI_MA_CIKIS = False
    TABLO = ()
    varsayilan_parametreler = {"hizli": 6, "yavas": 99, "ma_n": 45, "low_offset": 0.98, "high_offset": 1.01,
                               "atr_n": 14, "atr_acilis": False, "atr_bolen_al": 3.0, "atr_bolen_sat": 1.0,
                               "ort_pencere": 45, "norm_tur": "roll", "norm_pencere": 89, "yuksek_x": 1.33, "bull_x": 1.127,
                               "bear_x": 1.69, "lo_limit": -1.4, "rsi_alt": 38.0, "rsi_ust": 61.0, "rsi_ma_n": 10,
                               "rsi_cikis": 89.0, "sl": 0.281}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, ac = mumlar["kapanis"], mumlar["acilis"]
        vol = mumlar["hacim"] > 0
        e1, e2 = g.ema(kap, int(p["hizli"])), g.ema(kap, int(p["yavas"]))
        ewo = (e1 - e2) / kap * 100.0
        rsi = g.rsi(kap, 14)
        poz, neg = ewo.where(ewo > 0).ffill(), ewo.where(ewo < 0).ffill()
        n = int(p["ort_pencere"])
        ewo_hi = poz.rolling(n, min_periods=n).mean() * float(p["yuksek_x"])
        carpan = pd.Series(np.where(e1 < e2, float(p["bear_x"]), float(p["bull_x"])), index=kap.index)
        ewo_lo = neg.rolling(n, min_periods=n).mean() * carpan
        angle_perc = np.arctan((e1 - e1.shift(3)) / 3.0) / kap * 100.0
        w = int(p["norm_pencere"])
        if p["norm_tur"] == "roll":
            mn, mx = ewo.rolling(w, min_periods=w).min(), ewo.rolling(w, min_periods=w).max()
        else:
            mn, mx = ewo.expanding(min_periods=w).min(), ewo.expanding(min_periods=w).max()
        norm = ewo / (mx - mn)
        ewo_aci_yukari = np.arctan(norm - norm.shift(1)) > -0.0001
        atr_pc = _atr_sma(mumlar, int(p["atr_n"])) / ((kap + ac / 2.0) if p["atr_acilis"] else kap)
        ma = g.ema(kap, int(p["ma_n"]))
        ma_lo = ma * (float(p["low_offset"]) - atr_pc / float(p["atr_bolen_al"]))
        ma_hi = ma * (float(p["high_offset"]) + atr_pc / float(p["atr_bolen_sat"]))
        alt = kap < ma_lo
        lim = float(p["lo_limit"])
        kol = {
            1: (ewo > ewo_hi) & alt & vol,
            2: (ewo < ewo_hi) & alt & ewo_aci_yukari & vol,
            3: yukari(ewo, ewo_hi) & alt & ewo_aci_yukari & (rsi < float(p["rsi_ust"])) & vol,
            4: yukari(ewo, ewo_lo) & alt & (ewo < lim) & (rsi < float(p["rsi_alt"])) & vol,
            5: (ewo < ewo_lo) & alt & (ewo < lim) & (rsi < float(p["rsi_alt"])) & vol,
            6: (((angle_perc - angle_perc.shift(1)) > 0.07) & ((angle_perc.shift(1) - angle_perc.shift(2)) < 0)
                & (angle_perc < 0) & (ac < ma * float(p["low_offset"])) & vol),
        }
        al = pd.Series(False, index=kap.index)
        for k in self.KOLLAR:
            al |= kol[k].fillna(False).astype(bool)
        ust = (kap > ma_hi) & vol
        rsi_c = float(p["rsi_cikis"])
        c1 = ust & (ewo > ewo_hi) & (ewo > 0)
        if self.RSI_MA_CIKIS:
            c1 &= rsi <= g.sma(rsi, int(p["rsi_ma_n"]))
        cik = c1 | (ust & (rsi >= rsi_c) & (ewo > 0)) | (ust & (rsi >= rsi_c) & (ewo < 0))
        self._sakla(kap=kap)
        sl_l, _ = _stoplar(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, al, False, sl_l, kap + (kap - sl_l)), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        return self._iz_stop(d, self.TABLO, float(self.parametreler["sl"]))


class AngleWaveCtB0069(_AngleWave):
    """HAM:B001:69 (5m, long; AngleWaveCT.py + AngleWaveCT.json etkin): EWO = (EMA6 - EMA99)/kapanış x 100; ewo_high = SMA45(pozitif
    EWO ileri-doldurulmuş) x 1,33; ewo_low = SMA45(negatif EWO) x (1,127; EMA6 < EMA99 ise 1,69); ma_lo = EMA45 x (0,98 - ATR(14)/
    kapanış/3), ma_hi = EMA45 x (1,01 + ATR/kapanış). 6 kol (VEYA, hepsinde hacim > 0): EWO > high VE kapanış < ma_lo; EWO < high
    VE kapanış < ma_lo VE ewoNorm açısı yukarı (atan(ewoNorm[t]-ewoNorm[t-1]) > -0,0001; ewoNorm = EWO / 89 mum EWO aralığı);
    EWO high'ı yukarı keser (+ma_lo + açı + RSI < 61); EWO low'u yukarı keser (+ma_lo + EWO < -1,4 + RSI < 38); EWO < low (+ma_lo
    + EWO < -1,4 + RSI < 38); açı değişimi (angle_perc[t]-angle_perc[t-1] > 0,07, önceki fark < 0, angle_perc < 0, açılış < EMA45
    x 0,98). Çıkış (VEYA): kapanış > ma_hi VE ((EWO > high VE EWO > 0) VEYA (RSI >= 89 VE EWO > 0) VEYA (RSI >= 89 VE EWO < 0)).
    ROI {0:.202, 141:.094, 380:.017, 1459:0}; stop -%28,1; iz süren %1,1 (offset %2, yalnız offset sonrası); custom_stoploss
    (kâr > %20 -> kapanışın %4 altı, > %16 -> 3, > %11 -> 3,5, > %8 -> 2,1, > %4,5 -> 1,4, > %2,4 -> 0,9; aksi %28,1) kancada.
    Uyarlama: ATR = qtpylib.atr (TR'nin SMA'sı)."""

    ad = "kapanis__anglewave-ct-b0069"
    TABLO = ((0.2, 0.04), (0.16, 0.03), (0.11, 0.035), (0.08, 0.021), (0.045, 0.014), (0.024, 0.009))
    cikis_ayarlari = _ca({0: 0.202, 141: 0.094, 380: 0.017, 1459: 0.0}, 5, (0.011, 0.02))


class AwAtrCtB0156(_AngleWave):
    """HAM:B001:156 (15m, long; AWATRCT.py + AWATRCT.json etkin): EWO = (EMA6 - EMA88)/kapanış x 100; ewo_high = SMA88(pozitif EWO) x
    1,37; ewo_low = SMA88(negatif EWO) x (1,214; EMA6 < EMA88 ise 1,78); ATR(5, SMA)/(kapanış + açılış/2) = atr_pc; ma_lo = EMA51 x
    (0,96 - atr_pc/2,1); ma_hi = EMA51 x (1,0 + atr_pc/0,9); ewoNorm = EWO / (genişleyen pencerede (en az 88) EWO aralığı).
    4 kol (VEYA, hacim > 0): EWO < high VE kapanış < ma_lo VE ewoNorm açısı yukarı; EWO low'u yukarı keser VE kapanış < ma_lo VE
    EWO < -4,8 VE RSI < 32; EWO < low VE aynı koşullar; açı değişimi kolu (açılış < EMA51 x 0,96). Çıkış (VEYA): kapanış > ma_hi VE
    ((EWO > high VE RSI <= SMA10(RSI) VE EWO > 0) VEYA (RSI >= 89 VE EWO > 0) VEYA (RSI >= 89 VE EWO < 0)). ROI {0:.349, 89:.075,
    176:.043, 399:0}; stop -%31,8; iz süren %7 (offset %8, offset şartı YOK -> min kâr 0, ön kayıt eşlemesi); custom_stoploss kâr
    basamakları (> %20 -> %4, %20 -> %5 (erişilmez), > %15 -> 3, > %8,2 -> 2, > %4,3 -> 1,3, > %3,5 -> 1,5; aksi %31,8) kancada.
    Uyarlama: kaynakta `custom_stake_amount` (EMA<EMA'da stake/1,5) motor dışı; korumalar uygulanmadı."""

    ad = "kapanis__awatr-ct-b0156"
    KOLLAR = (2, 4, 5, 6)
    RSI_MA_CIKIS = True
    TABLO = ((0.2, 0.04), (0.2, 0.05), (0.15, 0.03), (0.082, 0.02), (0.043, 0.013), (0.035, 0.015))
    varsayilan_parametreler = {"hizli": 6, "yavas": 88, "ma_n": 51, "low_offset": 0.96, "high_offset": 1.0,
                               "atr_n": 5, "atr_acilis": True, "atr_bolen_al": 2.1, "atr_bolen_sat": 0.9,
                               "ort_pencere": 88, "norm_tur": "exp", "norm_pencere": 88, "yuksek_x": 1.37, "bull_x": 1.214,
                               "bear_x": 1.78, "lo_limit": -4.8, "rsi_alt": 32.0, "rsi_ust": 57.0, "rsi_ma_n": 10,
                               "rsi_cikis": 89.0, "sl": 0.318}
    cikis_ayarlari = _ca({0: 0.349, 89: 0.075, 176: 0.043, 399: 0.0}, 15, (0.07, 0.0))


# ================================================================ BB_RPB_TSL ailesi
class _BbRpbTsl(_KancaTaban):
    """BB_RPB_TSL: 7 giriş kolu (bb = dip VE kırılım, yerel yükseliş, ewo, ewo2, cofi, nfi 32, nfi 33; 399'da ek vwap), çıkış 2 kol,
    pHSL/pPF/pSL kâr-kilit stopu kancada (başlangıç stopu = pHSL)."""

    VWAP = False
    varsayilan_parametreler = {"rmi": 49.0, "cci": -116.0, "srsi_fk": 32.0, "cci_n": 25, "rmi_n": 17, "bb_width": 0.095,
                               "bb_delta": 0.025, "ema_diff": 0.022, "bb_factor": 0.999, "closedelta": 12.148,
                               "rsi_fast": 45.0, "rsi": 35.0, "ewo": -5.585, "ema_low": 0.942, "ema_high": 1.084,
                               "ema_low_2": 0.97, "ema_high_2": 1.087, "ema_cofi": 0.98, "fastk": 22.0, "fastd": 20.0,
                               "adx": 20.0, "ewo_high": 4.179, "ma_sat": 24, "high_offset": 0.991, "high_offset_2": 0.997,
                               "hsl": -0.178, "pf1": 0.019, "sl1": 0.019, "pf2": 0.065, "sl2": 0.062,
                               "vwap_pf1": 0.01, "vwap_sl1": 0.01, "vwap_pf2": 0.05, "vwap_sl2": 0.042}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, ac, yk, ds = mumlar["kapanis"], mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"]
        vol = mumlar["hacim"]
        tp = _tipik(mumlar)
        bb2, bb3 = _bb(tp, 20, 2.0), _bb(tp, 20, 3.0)
        bb_w = (bb2["ust"] - bb2["alt"]) / bb2["orta"]
        bb_d = (bb2["alt"] - bb3["alt"]) / bb2["alt"]
        srsi = _stoch_rsi(kap, 15, 20, 1, 1)["k"]
        cdelta = (kap - kap.shift(1)).abs()
        ema = {n: g.ema(kap, n) for n in (8, 12, 13, 16, 26)}
        sma15, sma9 = g.sma(kap, 15), g.sma(kap, 9)
        cti = _cti(kap, 20)
        rsi, rsi_f, rsi_s = g.rsi(kap, 14), g.rsi(kap, 4), g.rsi(kap, 20)
        ewo = _ewo(kap, 50, 200, payda=ds)
        fk = _fastk(mumlar, 5)
        fd = g.sma(fk, 3)
        adx = g.adx(yk, ds, kap, 14)["adx"]
        r14 = _wr(yk, ds, kap, 14)
        vm4 = vol.rolling(4, min_periods=4).mean().shift(1)

        is_dip = ((_rmi(kap, int(p["rmi_n"]), 4) < float(p["rmi"]))
                  & (b2.cci(yk, ds, kap, int(p["cci_n"])) <= float(p["cci"])) & (srsi < float(p["srsi_fk"])))
        is_break = ((bb_d > float(p["bb_delta"])) & (bb_w > float(p["bb_width"]))
                    & (cdelta > kap * float(p["closedelta"]) / 1000.0) & (kap < bb3["alt"] * float(p["bb_factor"])))
        is_local = ((ema[26] > ema[12]) & (ema[26] - ema[12] > ac * float(p["ema_diff"]))
                    & (ema[26].shift(1) - ema[12].shift(1) > ac / 100.0) & (kap < bb2["alt"] * float(p["bb_factor"]))
                    & (cdelta > kap * float(p["closedelta"]) / 1000.0))
        is_ewo = ((rsi_f < float(p["rsi_fast"])) & (kap < ema[8] * float(p["ema_low"])) & (ewo > float(p["ewo"]))
                  & (kap < ema[16] * float(p["ema_high"])) & (rsi < float(p["rsi"])))
        is_ewo2 = ((rsi_f < float(p["rsi_fast"])) & (kap < ema[8] * float(p["ema_low_2"])) & (ewo > float(p["ewo_high"]))
                   & (kap < ema[16] * float(p["ema_high_2"])) & (rsi < float(p["rsi"])))
        is_cofi = ((ac < ema[8] * float(p["ema_cofi"])) & yukari(fk, fd) & (fk < float(p["fastk"]))
                   & (fd < float(p["fastd"])) & (adx > float(p["adx"])) & (ewo > float(p["ewo_high"])))
        is_nfi32 = ((rsi_s < rsi_s.shift(1)) & (rsi_f < 46) & (rsi > 19) & (kap < sma15 * 0.942) & (cti < -0.86))
        is_nfi33 = ((kap < ema[13] * 0.978) & (ewo > 8) & (cti < -0.88) & (rsi < 32) & (r14 < -98.0) & (vol < vm4 * 2.5))
        kollar = [is_dip & is_break, is_local, is_ewo, is_ewo2, is_cofi, is_nfi32, is_nfi33]
        sadece_vwap = pd.Series(False, index=kap.index)
        if self.VWAP:
            tcp = (ac.rolling(4, min_periods=4).max() - kap) / kap
            vw = (tp * vol).rolling(20, min_periods=20).sum() / vol.rolling(20, min_periods=20).sum()
            vw_low = vw - vw.rolling(20, min_periods=20).std()
            is_vwap = ((kap < vw_low) & (tcp > 0.04) & (cti < -0.8) & (rsi < 35) & (g.rsi(kap, 84) < 60)
                       & (g.rsi(kap, 112) < 60) & (vol > 0))
            diger = pd.Series(False, index=kap.index)
            for k in kollar:
                diger |= k.fillna(False).astype(bool)
            sadece_vwap = is_vwap.fillna(False).astype(bool) & ~diger
            kollar.append(is_vwap)
        al = pd.Series(False, index=kap.index)
        for k in kollar:
            al |= k.fillna(False).astype(bool)
        ma_s = g.ema(kap, int(p["ma_sat"]))
        hma50 = _hma(kap, 50)
        cik = (((kap > sma9) & (kap > ma_s * float(p["high_offset_2"])) & (rsi > 50) & (vol > 0) & (rsi_f > rsi_s))
               | ((sma9 > sma9.shift(1) * 1.005) & (kap < hma50) & (kap > ma_s * float(p["high_offset"])) & (vol > 0)
                  & (rsi_f > rsi_s)))
        self._sakla(kap=kap, sadece_vwap=sadece_vwap.astype(float))
        sl_l, sl_s = _stoplar(mumlar, -float(p["hsl"]))
        return _bitir(cerceve(mumlar, al, False, sl_l, sl_s), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        p = self.parametreler
        if self.VWAP and self._dz("sadece_vwap", d.giris_mum_indeksi - 1) > 0.5:
            return self._pf_cik(d, float(p["hsl"]), float(p["vwap_pf1"]), float(p["vwap_sl1"]), float(p["vwap_pf2"]),
                                float(p["vwap_sl2"]))
        return self._pf_cik(d, float(p["hsl"]), float(p["pf1"]), float(p["sl1"]), float(p["pf2"]), float(p["sl2"]))


class BbRpbTslB0395(_BbRpbTsl):
    """HAM:B001:395 (5m, long; BB_RPB_TSL_RNG.py): tipik fiyat BB(20,2/3); bb_width, bb_delta; is_dip (RMI(17,4) < 49 VE CCI(25) <=
    -116 VE StochRSI(15,20) hızlı K < 32) VE is_break (bb_delta > 0,025 VE bb_width > 0,095 VE |Δkapanış| > kapanış x 12,148/1000 VE
    kapanış < BB3 alt x 0,999); yerel yükseliş, ewo (EWO = (EMA50-EMA200)/DÜŞÜK x 100), ewo2, cofi, nfi 32, nfi 33 kolları (VEYA).
    Çıkış: (kapanış > SMA9 VE kapanış > EMA24 x 0,997 VE RSI > 50 VE RSI4 > RSI20 VE hacim > 0) VEYA (SMA9 > SMA9[-1] x 1,005 VE
    kapanış < HMA50 VE kapanış > EMA24 x 0,991 VE RSI4 > RSI20 VE hacim > 0). ROI %10; custom_stoploss pHSL -0,178, pPF_1 0,019,
    pSL_1 0,019, pPF_2 0,065, pSL_2 0,062 (kâr-kilit, kancada). Uyarlama: kaynakta BTC bilgi çifti yalnız tanımlı, giriş/çıkışta
    KULLANILMAZ (kural_tam notu: gerekmez)."""

    ad = "kapanis__bb-rpb-tsl-b0395"
    cikis_ayarlari = _ca({0: 0.10}, 5)


class BbRpbTslVwapB0399(_BbRpbTsl):
    """HAM:B001:399 (5m, long; BB_RPB_TSL_RNG_VWAP.py): 395 + 8. kol is_vwap (kapanış < VWAP(20) - std(VWAP,20) VE (4 bar en yüksek
    açılış - kapanış)/kapanış > 0,04 VE CTI < -0,8 VE RSI < 35 VE RSI(84) < 60 VE RSI(112) < 60 VE hacim > 0). pHSL -0,25;
    giriş YALNIZ vwap kolundan ise pPF_1 0,01, pSL_1 0,01, pPF_2 0,05, pSL_2 0,042. ROI %10000 (fiilen yok)."""

    ad = "kapanis__bb-rpb-tsl-vwap-b0399"
    VWAP = True
    varsayilan_parametreler = {**_BbRpbTsl.varsayilan_parametreler, "hsl": -0.25}
    cikis_ayarlari = _ca({0: 100.0}, 5)


# ================================================================ Bollinger / RSI sade stratejiler
class BbRsiOptim2020B0469(Strateji):
    """HAM:B001:469 (5m, long; BBRSIOptim2020Strategy.py): kapanış < BB(tipik, 20, 3s) alt bandı -> long; çıkış kapanış > BB(tipik,
    20, 1s) orta bandı. ROI {0:.336, 40:.072, 218:.021, 459:0}; stop -%33,1. Kaynakta hacim şartı yok."""

    ad, stil = "kapanis__bbrsi-optim2020-b0469", "daytrade"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 3.0, "sl": 0.331}
    parametre_izgarasi = {}
    cikis_ayarlari = _ca({0: 0.336, 40: 0.072, 218: 0.021, 459: 0.0}, 5)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tp = _tipik(mumlar)
        sl_l, sl_s = _stoplar(mumlar, float(p["sl"]))
        s = cerceve(mumlar, kap < _bb(tp, int(p["bb_n"]), float(p["bb_k"]))["alt"], False, sl_l, sl_s)
        return _bitir(s, kap > _bb(tp, int(p["bb_n"]), 1.0)["orta"])


class BbRsiOptimB0470(Strateji):
    """HAM:B001:470 (5m, long; BBRSIOptimStrategy.py): RSI(14) > 12 VE kapanış < BB(tipik, 20, 2s) alt bandı -> long; çıkış RSI > 96
    VE kapanış > BB(tipik, 20, 1s) alt bandı. ROI {0:.323, 107:.097, 150:.019, 238:0}; stop -%34,4."""

    ad, stil = "kapanis__bbrsi-optim-b0470", "daytrade"
    varsayilan_parametreler = {"rsi_alt": 12.0, "rsi_cik": 96.0, "bb_n": 20, "sl": 0.344}
    parametre_izgarasi = {}
    cikis_ayarlari = _ca({0: 0.323, 107: 0.097, 150: 0.019, 238: 0.0}, 5)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tp = _tipik(mumlar)
        rsi = g.rsi(kap, 14)
        sl_l, sl_s = _stoplar(mumlar, float(p["sl"]))
        s = cerceve(mumlar, (rsi > float(p["rsi_alt"])) & (kap < _bb(tp, int(p["bb_n"]), 2.0)["alt"]), False, sl_l, sl_s)
        return _bitir(s, (rsi > float(p["rsi_cik"])) & (kap > _bb(tp, int(p["bb_n"]), 1.0)["alt"]))


class GodCardB0506(Strateji):
    """HAM:B001:506 (5m, long; GodCard.py): kapanış < BB(tipik, 20, 2s) alt bandı VE hacim > 0 -> long (buy_trigger bb_two, RSI filtresi
    kapalı); çıkış RSI(14) > 9 VE hacim > 0 ve YALNIZ KÂRDA (sell_profit_only; kaynakta BB sell tetikleri buy_trigger anahtarına bağlı
    olduğundan etkisiz: fiilen ilk kârlı mum). ROI {0:.344, 32:.09, 120:.041, 447:0}; stop -%8,7; iz süren %1 (offset %4,3)."""

    ad, stil = "kapanis__godcard-b0506", "daytrade"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "rsi_cik": 9.0, "sl": 0.087}
    parametre_izgarasi = {}
    cikis_ayarlari = _ca({0: 0.344, 32: 0.09, 120: 0.041, 447: 0.0}, 5, (0.01, 0.043), yalniz_kar=True)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        vol = mumlar["hacim"] > 0
        sl_l, sl_s = _stoplar(mumlar, float(p["sl"]))
        al = (kap < _bb(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))["alt"]) & vol
        return _bitir(cerceve(mumlar, al, False, sl_l, sl_s), (g.rsi(kap, 14) > float(p["rsi_cik"])) & vol)


class Bbrsi1B0533(Strateji):
    """HAM:B001:533 (5m, long; bbrsi1_strategy.py): RSI(14) < 30 VE kapanış < BB(tipik, 20, 2s) alt bandı VE hacim > 0 -> long; çıkış
    RSI(14) > 70 VE hacim > 0. ROI {0:.04, 30:.02, 60:.01}; stop -%10."""

    ad, stil = "kapanis__bbrsi1-b0533", "daytrade"
    varsayilan_parametreler = {"rsi_al": 30.0, "rsi_cik": 70.0, "bb_n": 20, "bb_k": 2.0, "sl": 0.10}
    parametre_izgarasi = {}
    cikis_ayarlari = _ca({0: 0.04, 30: 0.02, 60: 0.01}, 5)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        vol = mumlar["hacim"] > 0
        rsi = g.rsi(kap, 14)
        sl_l, sl_s = _stoplar(mumlar, float(p["sl"]))
        al = (rsi < float(p["rsi_al"])) & (kap < _bb(_tipik(mumlar), int(p["bb_n"]), float(p["bb_k"]))["alt"]) & vol
        return _bitir(cerceve(mumlar, al, False, sl_l, sl_s), (rsi > float(p["rsi_cik"])) & vol)


# ================================================================ Binh/Cluc: HA bant ailesi (ClucHAnix)
def _ha_bant(mumlar: pd.DataFrame) -> dict:
    """ClucHAnix ortak serileri: HA(kapanış, yüksek, düşük), HA tipik fiyat BB(40, 2s) (std ddof=1), bbdelta, closedelta, tail,
    EMA(HA kapanış, 3/50)."""
    ha = _ha(mumlar)
    hc, hh, hl = ha["ha_kapanis"], ha["ha_yuksek"], ha["ha_dusuk"]
    tpk = (hh + hl + hc) / 3.0
    orta = g.sma(tpk, 40)
    alt = orta - 2.0 * tpk.rolling(40, min_periods=40).std()
    return {"hc": hc, "hh": hh, "hl": hl, "alt": alt, "orta": orta, "bbdelta": (orta - alt).abs(),
            "cdelta": (hc - hc.shift(1)).abs(), "tail": (hc - hl).abs(), "ema_hizli": g.ema(hc, 3), "ema_yavas": g.ema(hc, 50)}


def _cluc_ha_kolu(h: dict, rocr1: pd.Series, p: dict) -> pd.Series:
    hc, alt = h["hc"], h["alt"]
    a = ((alt.shift(1) > 0) & (h["bbdelta"] > hc * float(p["bbdelta_close"])) & (h["cdelta"] > hc * float(p["closedelta_close"]))
         & (h["tail"] < h["bbdelta"] * float(p["bbdelta_tail"])) & (hc < alt.shift(1)) & (hc <= hc.shift(1)))
    b = (hc < h["ema_yavas"]) & (hc < float(p["close_bblower"]) * alt)
    return (rocr1 > float(p["rocr_1h"])) & (a | b)


def _ha_cikis(h: dict, p: dict) -> pd.Series:
    """HA fisher çıkışı: fisher(RSI14) > eşik VE HA high 2 mum düşüş VE HA close <= önceki VE EMA3 > HA close VE HA close x k > BB orta."""
    return ((p["_fisher"] > float(p["sell_fisher"])) & (h["hh"] <= h["hh"].shift(1)) & (h["hh"].shift(1) <= h["hh"].shift(2))
            & (h["hc"] <= h["hc"].shift(1)) & (h["ema_hizli"] > h["hc"])
            & (h["hc"] * float(p["sell_bbmiddle_close"]) > h["orta"]))


class ClucHaNix5mB0434(_KancaTaban):
    """HAM:B001:434 (5m, long; ClucHAnix_5m.py): rocr_1h (1h HA kapanış ROCR 168) > 0,79492 VE ((alt[-1] > 0 VE bbdelta > HA kapanış x
    0,01889 VE closedelta > HA kapanış x 0,00916 VE tail < bbdelta x 0,72235 VE HA kapanış < alt[-1] VE HA kapanış <= önceki) VEYA
    (HA kapanış < EMA50(HA) VE HA kapanış < 0,0127 x BB40 alt)); çıkış: fisher > 0,39075 VE HA high 2 mum düşüş VE HA kapanış <=
    önceki VE EMA3 > HA kapanış VE HA kapanış x 0,99754 > BB40 orta. ROI yok (%10000); custom_stoploss pHSL -0,35, pPF_1 0,011,
    pSL_1 0,011, pPF_2 0,064, pSL_2 0,062 (kancada). Çıkış sinyalinde hacim şartı yok."""

    ad = "kapanis__cluchanix-5m-b0434"
    varsayilan_parametreler = {"rocr_1h": 0.79492, "bbdelta_close": 0.01889, "bbdelta_tail": 0.72235, "close_bblower": 0.0127,
                               "closedelta_close": 0.00916, "sell_fisher": 0.39075, "sell_bbmiddle_close": 0.99754,
                               "hsl": -0.35, "pf1": 0.011, "sl1": 0.011, "pf2": 0.064, "sl2": 0.062}
    cikis_ayarlari = _ca({0: 100.0}, 5)

    def sinyaller(self, mumlar):
        p = dict(self.parametreler)
        kap = mumlar["kapanis"]
        h = _ha_bant(mumlar)
        al = _cluc_ha_kolu(h, _rocr_1h(mumlar), p)
        p["_fisher"] = np.tanh(0.1 * (g.rsi(kap, 14) - 50.0))
        self._sakla(kap=kap)
        sl_l, sl_s = _stoplar(mumlar, -float(p["hsl"]))
        return _bitir(cerceve(mumlar, al, False, sl_l, sl_s), _ha_cikis(h, p))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        p = self.parametreler
        return self._pf_cik(d, float(p["hsl"]), float(p["pf1"]), float(p["sl1"]), float(p["pf2"]), float(p["sl2"]))


class FahmibahB0547(_KancaTaban):
    """HAM:B001:547 (5m, long; fahmibah.py): clucHA kolu (434 ile aynı mantık, eşikler rocr_1h 0,79492, 0,01889, 0,00916, 0,72235,
    0,0127) VEYA lambo1 kolu: HA kapanış < EMA14(HA kapanış) x 1,054 VE RSI4(HA kapanış) < 18 VE RSI14(HA kapanış) < 39. Çıkış sinyali
    YOK (use_sell_signal=False); ROI {0:.033, 10:.023, 40:.01}; stop -%10; custom_stoploss pHSL -0,10, pPF_1 0,02, pSL_1 0,015,
    pPF_2 0,03, pSL_2 0,025 (kancada). Lambo1 RSI'ları HA kapanış serisinden (kaynakta öyle)."""

    ad = "kapanis__fahmibah-b0547"
    varsayilan_parametreler = {"rocr_1h": 0.79492, "bbdelta_close": 0.01889, "bbdelta_tail": 0.72235, "close_bblower": 0.0127,
                               "closedelta_close": 0.00916, "lambo_ema": 1.054, "lambo_rsi4": 18.0, "lambo_rsi14": 39.0,
                               "hsl": -0.10, "pf1": 0.02, "sl1": 0.015, "pf2": 0.03, "sl2": 0.025}
    cikis_ayarlari = _ca({0: 0.033, 10: 0.023, 40: 0.01}, 5)

    def sinyaller(self, mumlar):
        p = self.parametreler
        h = _ha_bant(mumlar)
        hc = h["hc"]
        lambo = ((hc < g.ema(hc, 14) * float(p["lambo_ema"])) & (g.rsi(hc, 4) < float(p["lambo_rsi4"]))
                 & (g.rsi(hc, 14) < float(p["lambo_rsi14"])))
        al = _cluc_ha_kolu(h, _rocr_1h(mumlar), p) | lambo
        self._sakla(kap=mumlar["kapanis"])
        sl_l, sl_s = _stoplar(mumlar, -float(p["hsl"]))
        return cerceve(mumlar, al, False, sl_l, sl_s)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        p = self.parametreler
        return self._pf_cik(d, float(p["hsl"]), float(p["pf1"]), float(p["sl1"]), float(p["pf2"]), float(p["sl2"]))


class ClucHaNixHhllB0440(_KancaTaban):
    """HAM:B001:440 (5m, long; ClucHAnix_hhll.py): 434'ün giriş mantığı (rocr_1h > 0,5411, 0,01846, 0,01009, 0,98973, 0,00785) VE
    48 bar en yüksek(yüksek)'ten uzaklık % > 6,867 VE kapanışın 48 bar en düşüğünden yukarı % > -12,884. Çıkış (VEYA, hacim > 0):
    HA fisher kolu (fisher > 0,48492, bb orta x 0,97286) VEYA (kapanış > SMA9 VE kapanış > EMA24 x 1,211 VE RSI > 50 VE RSI4 > RSI20)
    VEYA (SMA9 > SMA9[-1] x 1,005 VE kapanış < HMA50 VE kapanış > EMA24 x 0,907 VE RSI4 > RSI20). ROI {0:.103, 3:.05, 5:.033, 61:.027,
    125:.011, 292:.005}. Stop: pHSL yok (-0,99 -> ATR(14) x 3); kâr-kilit pPF_1 0,011, pSL_1 0,011, pPF_2 0,064, pSL_2 0,062 (yalnız
    kâr > pPF_1 sonrası). custom_sell (kancada): deadfish (kâr < -%6,3 VE kapanış < EMA200 VE bb_width < 0,043 VE kapanış > BB2 orta x
    0,954 VE hacim ort12 < ort24 x 2,37) ve 5 pompa kolu (p_48_1_1, p_48_1_2, p_36_1_1, p_36_2_1, p_24_1_1; ortak: max_loss < 0,08,
    kapanış < EMA200, SMA200 düşüyor, ema_vwma_osc 32/64/96 < 0, CMF < -0,25, 1h CMF < 0). Uyarlamalar: kaynakta `vwma()` fonksiyonu
    `fillna(inplace)` sonucu None döndürür (kaynak hatası); amaçlanan tanım (VWMA, boşlar 0) uygulandı. Giriş onayı (emir fiyatı
    kapanıştan > %0,73 yüksekse ret) sonraki açılışı bilmeden uygulanamaz (lookahead); uygulanmadı."""

    ad = "kapanis__cluchanix-hhll-b0440"
    varsayilan_parametreler = {"rocr_1h": 0.5411, "bbdelta_close": 0.01846, "bbdelta_tail": 0.98973, "close_bblower": 0.00785,
                               "closedelta_close": 0.01009, "hh_fark": 6.867, "ll_fark": -12.884, "sell_fisher": 0.48492,
                               "sell_bbmiddle_close": 0.97286, "high_offset": 0.907, "high_offset_2": 1.211,
                               "pf1": 0.011, "sl1": 0.011, "pf2": 0.064, "sl2": 0.062}
    cikis_ayarlari = _ca({0: 0.103, 3: 0.05, 5: 0.033, 61: 0.027, 125: 0.011, 292: 0.005}, 5)

    def sinyaller(self, mumlar):
        p = dict(self.parametreler)
        kap, yk, ds = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        vol = mumlar["hacim"]
        h = _ha_bant(mumlar)
        hh48 = yk.rolling(48, min_periods=48).max()
        ll48 = ds.rolling(48, min_periods=48).min()
        al = (_cluc_ha_kolu(h, _rocr_1h(mumlar), p) & ((hh48 - kap) / hh48 * 100.0 > float(p["hh_fark"]))
              & ((kap - ll48) / ll48 * 100.0 > float(p["ll_fark"])))
        rsi, rsi_f, rsi_s = g.rsi(kap, 14), g.rsi(kap, 4), g.rsi(kap, 20)
        sma9, ema24, ema200 = g.sma(kap, 9), g.ema(kap, 24), g.ema(kap, 200)
        p["_fisher"] = np.tanh(0.1 * (rsi - 50.0))
        cik = ((_ha_cikis(h, p)
                | ((kap > sma9) & (kap > ema24 * float(p["high_offset_2"])) & (rsi > 50) & (rsi_f > rsi_s))
                | ((sma9 > sma9.shift(1) * 1.005) & (kap < _hma(kap, 50)) & (kap > ema24 * float(p["high_offset"]))
                   & (rsi_f > rsi_s))) & (vol > 0))
        bb2 = _bb(_tipik(mumlar), 20, 2.0)
        sma200 = g.sma(kap, 200)

        def saat(u):
            sma200u = g.sma(u["kapanis"], 200)
            hl = lambda n: ((u["yuksek"].rolling(n, min_periods=n).max() - u["dusuk"].rolling(n, min_periods=n).min())
                            / u["dusuk"].rolling(n, min_periods=n).min())
            return pd.DataFrame({"hl48": hl(48), "hl36": hl(36), "hl24": hl(24),
                                 "dec": (sma200u < sma200u.shift(20)).astype(float), "cmf": _cmf(u, 20)})

        s1 = ust_zaman(mumlar, "1h", saat)
        self._sakla(
            kap=kap, ema200=ema200, bb_width=(bb2["ust"] - bb2["alt"]) / bb2["orta"], bb2_orta=bb2["orta"],
            vm12=vol.rolling(12, min_periods=12).mean().shift(1), vm24=vol.rolling(24, min_periods=24).mean().shift(1),
            hl48=s1["hl48"], hl36=s1["hl36"], hl24=s1["hl24"], dec1h=s1["dec"], cmf1h=s1["cmf"],
            dec=(sma200 < sma200.shift(20)).astype(float), o32=_ema_vwma_osc(mumlar, 32), o64=_ema_vwma_osc(mumlar, 64),
            o96=_ema_vwma_osc(mumlar, 96), cmf=_cmf(mumlar, 20), rsi=rsi)
        sl_l, sl_s = _stoplar(mumlar, None)
        return _bitir(cerceve(mumlar, al, False, sl_l, sl_s), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        p = self.parametreler
        if self._pf_cik(d, None, float(p["pf1"]), float(p["sl1"]), float(p["pf2"]), float(p["sl2"])):
            return True
        z = lambda a: self._dz(a, i)
        kar = d.kar_yuzde / 100.0
        kap = d.kapanis
        mp = (d.en_yuksek - d.giris_fiyati) / d.giris_fiyati
        ml = (d.giris_fiyati - d.en_dusuk) / d.en_dusuk
        if (kar < -0.063 and kap < z("ema200") and z("bb_width") < 0.043 and kap > z("bb2_orta") * 0.954
                and z("vm12") < z("vm24") * 2.37):
            return True
        pompa = (ml < 0.08 and kap < z("ema200") and z("dec") > 0.5 and z("o32") < 0 and z("o64") < 0 and z("o96") < 0
                 and z("cmf") < -0.25 and z("cmf1h") < 0)
        if not pompa:
            return False
        d1h = z("dec1h") > 0.5
        if z("hl48") > 0.95 and -0.08 < kar < -0.04 and (mp < 0.005 or mp < 0.01):
            return True
        if z("hl36") > 0.7 and -0.08 < kar < -0.04 and mp > kar + 0.1 and d1h:
            return True
        if z("hl36") > 0.5 and -0.08 < kar < -0.05 and mp > kar + 0.1 and d1h and z("rsi") < 40.0:
            return True
        return bool(z("hl24") > 0.6 and -0.08 < kar < -0.04 and d1h)


# ================================================================ Binh/Cluc: kapanış bant ailesi (CombinedBinHAndCluc*)
def _bb40_kolu(mumlar: pd.DataFrame, kap_bb40: pd.DataFrame, bb_d: float, c_d: float, t_d: float) -> pd.Series:
    """BinHV45 kolu: alt[-1] > 0 VE bbdelta > kapanış x bb_d VE |Δkapanış| > kapanış x c_d VE kuyruk < bbdelta x t_d VE kapanış < alt[-1]
    VE kapanış <= önceki."""
    kap = mumlar["kapanis"]
    bbd = (kap_bb40["orta"] - kap_bb40["alt"]).abs()
    return ((kap_bb40["alt"].shift(1) > 0) & (bbd > kap * bb_d) & ((kap - kap.shift(1)).abs() > kap * c_d)
            & ((kap - mumlar["dusuk"]).abs() < bbd * t_d) & (kap < kap_bb40["alt"].shift(1)) & (kap <= kap.shift(1)))


class BinhCluc2021B0442(Strateji):
    """HAM:B001:442 (5m, long; CombinedBinHAndCluc2021.py): (BinHV45: BB(kapanış, 40, 2s) alt[-1] > 0 VE bbdelta > kapanış x 0,008 VE
    |Δkapanış| > kapanış x 0,0175 VE kuyruk < bbdelta x 0,25 VE kapanış < alt[-1] VE kapanış <= önceki) VEYA (kapanış < EMA(50) VE
    kapanış < 0,985 x BB(tipik,20,2) alt VE hacim < SMA30(hacim)[-1] x 20) VEYA (RSI(14) < 12 VE kapanış < BB(tipik,20,4) alt);
    çıkış kapanış > BB(tipik,20,2) orta. ROI {0:.0888, 21:.06115, 60:.02667, 80:0}; stop -%9. Kaynakta hacim > 0 şartı yok."""

    ad, stil = "kapanis__binhcluc2021-b0442", "daytrade"
    varsayilan_parametreler = {"bb40_n": 40, "bb_d": 0.008, "c_d": 0.0175, "t_d": 0.25, "ema_n": 50, "bb_carpan": 0.985,
                               "hacim_n": 30, "hacim_k": 20.0, "rsi_alt": 12.0, "bb4_k": 4.0, "sl": 0.09}
    parametre_izgarasi = {}
    cikis_ayarlari = _ca({0: 0.0888, 21: 0.06115, 60: 0.02667, 80: 0.0}, 5)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tp = _tipik(mumlar)
        bb20 = _bb(tp, 20, 2.0)
        a = _bb40_kolu(mumlar, _bb(kap, int(p["bb40_n"]), 2.0), float(p["bb_d"]), float(p["c_d"]), float(p["t_d"]))
        hort = mumlar["hacim"].rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean().shift(1)
        b = ((kap < g.ema(kap, int(p["ema_n"]))) & (kap < float(p["bb_carpan"]) * bb20["alt"])
             & (mumlar["hacim"] < hort * float(p["hacim_k"])))
        c = (g.rsi(kap, 14) < float(p["rsi_alt"])) & (kap < _bb(tp, 20, float(p["bb4_k"]))["alt"])
        sl_l, sl_s = _stoplar(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, a | b | c, False, sl_l, sl_s), kap > bb20["orta"])


def _ust_1h(mumlar: pd.DataFrame, ssl_n: int = 20) -> pd.DataFrame:
    """1h bilgi çerçevesi (kapanmış 1h mumdan): EMA50/100/200, SMA200 (+ düşüş bayrağı), RSI14, SSL(ssl_n) aşağı/yukarı."""
    def f(u):
        k = u["kapanis"]
        asg, yks = _ssl(u, ssl_n)
        s200 = g.sma(k, 200)
        return pd.DataFrame({"ema50": g.ema(k, 50), "ema100": g.ema(k, 100), "ema200": g.ema(k, 200), "sma200": s200,
                             "sma200_dec": (s200 < s200.shift(20)).astype(float), "rsi": g.rsi(k, 14),
                             "ssl_dn": asg, "ssl_up": yks})
    return ust_zaman(mumlar, "1h", f)


class BinhClucV2B0446(Strateji):
    """HAM:B001:446 (5m, long; CombinedBinHAndClucV2.py): 1h go_long (SSL(25) yukarı > aşağı VE SMA3(MFI(30)[-1]) > MFI VE
    SMA3(StochRSI(30,35) hızlı K[-1]) > K; kapanmış 1h mumdan) VE ((BinHV45 kolu: BB(tipik, 40, 2s); 0,008 / 0,0175 / 0,25) VEYA
    (kapanış < EMA50 VE kapanış < 0,985 x BB(tipik,20,2) alt VE hacim < SMA30(hacim)[-1] x 20)); çıkış kapanış BB(tipik,20,2) üst
    bandını aşağı keser. ROI {0:.1, 30:.05, 60:.02, 120:.01}; stop -%5."""

    ad, stil = "kapanis__binhcluc-v2-b0446", "daytrade"
    varsayilan_parametreler = {"bb40_n": 40, "bb_d": 0.008, "c_d": 0.0175, "t_d": 0.25, "ema_n": 50, "bb_carpan": 0.985,
                               "hacim_n": 30, "hacim_k": 20.0, "ssl_n": 25, "mfi_n": 30, "srsi_rsi": 30, "srsi_n": 35,
                               "sl": 0.05}
    parametre_izgarasi = {}
    cikis_ayarlari = _ca({0: 0.1, 30: 0.05, 60: 0.02, 120: 0.01}, 5)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        tp = _tipik(mumlar)
        bb20 = _bb(tp, 20, 2.0)

        def go(u):
            asg, yks = _ssl(u, int(p["ssl_n"]))
            mf = _mfi(u["yuksek"], u["dusuk"], u["kapanis"], u["hacim"], int(p["mfi_n"]))
            fk = _stoch_rsi(u["kapanis"], int(p["srsi_rsi"]), int(p["srsi_n"]), 1, 1)["k"]
            return ((yks > asg) & (mf.shift(1).rolling(3, min_periods=3).mean() > mf)
                    & (fk.shift(1).rolling(3, min_periods=3).mean() > fk)).astype(float)

        go_long = ust_zaman(mumlar, "1h", go)
        a = _bb40_kolu(mumlar, _bb(tp, int(p["bb40_n"]), 2.0), float(p["bb_d"]), float(p["c_d"]), float(p["t_d"]))
        hort = mumlar["hacim"].rolling(int(p["hacim_n"]), min_periods=int(p["hacim_n"])).mean().shift(1)
        b = ((kap < g.ema(kap, int(p["ema_n"]))) & (kap < float(p["bb_carpan"]) * bb20["alt"])
             & (mumlar["hacim"] < hort * float(p["hacim_k"])))
        sl_l, sl_s = _stoplar(mumlar, float(p["sl"]))
        return _bitir(cerceve(mumlar, (go_long > 0) & (a | b), False, sl_l, sl_s), asagi(kap, bb20["ust"]))


class _BinhClucKanca(_KancaTaban):
    """V5/V6/V8/MADV5 ortak: BB(kapanış,40,2s) + BB(tipik,20,2s), zarar-süre kilidi kancada."""

    def _bantlar(self, mumlar: pd.DataFrame) -> dict:
        kap = mumlar["kapanis"]
        bb20 = _bb(_tipik(mumlar), 20, 2.0)
        return {"kap": kap, "bb40": _bb(kap, 40, 2.0), "bb20": bb20, "ema_slow": g.ema(kap, 50),
                "hort": mumlar["hacim"].rolling(30, min_periods=30).mean().shift(1)}


class BinhClucV5B0449(_BinhClucKanca):
    """HAM:B001:449 (5m, long; CombinedBinHAndClucV5.py): (BinHV45 kolu BB(kapanış,40,2s) 0,008 / 0,0175 / 0,25 VE hacim > 0) VEYA
    (kapanış < EMA50 VE kapanış < 0,985 x BB(tipik,20,2) alt VE hacim < SMA30(hacim)[-1] x 20 VE hacim > 0); çıkış: kapanış > BB üst VE
    önceki kapanış > önceki BB üst VE hacim > 0, YALNIZ KÂRDA (sell_profit_only, offset %0,1). ROI %1,8; iz süren %1 (offset %2,5, yalnız
    offset sonrası). Stop: -0,99 -> ATR(14) x 3; custom_stoploss: açıkken > 300 dk VE zararda ise stop = kapanışın %1 altı (yalnız
    yukarı) kancada."""

    ad = "kapanis__binhcluc-v5-b0449"
    varsayilan_parametreler = {"sure_dk": 300.0, "kilit": 0.01}
    cikis_ayarlari = _ca({0: 0.018}, 5, (0.01, 0.025), yalniz_kar=True, kar_esik=0.1)

    def sinyaller(self, mumlar):
        b = self._bantlar(mumlar)
        kap, vol = b["kap"], mumlar["hacim"]
        a = _bb40_kolu(mumlar, b["bb40"], 0.008, 0.0175, 0.25) & (vol > 0)
        c = ((kap < b["ema_slow"]) & (kap < 0.985 * b["bb20"]["alt"]) & (vol < b["hort"] * 20) & (vol > 0))
        ust = b["bb20"]["ust"]
        cik = (kap > ust) & (kap.shift(1) > ust.shift(1)) & (vol > 0)
        self._sakla(kap=kap)
        self._tf = _tf_dk(mumlar)
        sl_l, sl_s = _stoplar(mumlar, None)
        return _bitir(cerceve(mumlar, a | c, False, sl_l, sl_s), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        p = self.parametreler
        return self._zarar_kilit(d, float(p["sure_dk"]), float(p["kilit"]))


class BinhClucV6B0451(_BinhClucKanca):
    """HAM:B001:451 (5m, long; CombinedBinHAndClucV6.py): 1h EMA50/200, SSL(20). Giriş (VEYA): (kapanış > 1h EMA200 VE EMA50 > EMA200 VE
    1h EMA50 > 1h EMA200 VE BinHV45 kolu 0,031 / 0,018 / 0,233 VE hacim > 0) VEYA (kapanış > EMA200 VE kapanış > 1h EMA200 VE kapanış <
    EMA50 VE kapanış < 0,993 x BB(tipik,20,2) alt VE hacim < SMA30(hacim)[-1] x 21 VE hacim > 0) VEYA (kapanış < EMA5 [kaynakta `sma_5`
    adıyla EMA(5)] VE 1h SSL yukarı > aşağı VE EMA50 > EMA200 VE 1h EMA50 > 1h EMA200 VE RSI(14) < 1h RSI - 43,276 VE hacim > 0).
    Çıkış: kapanış > BB üst VE önceki kapanış > önceki BB üst VE hacim > 0. Kaynakta confirm_trade_exit: son mum RSI(14) > 50 iken HER
    ÇIKIŞ reddedilir. Uyarlama: bu süzgeç sinyal çıkışına, ROI'ye ve iz süren stopa uygulanır (ROI %1,81 ve iz %1/offset %2,5 kancada
    yazıldı); zarar-süre stopu (> 300 dk VE zararda: kapanışın %1 altı, yalnız yukarı) ve ilk stop süzgeçsiz. Sinyal çıkışı yalnız kârda
    (offset %0,1)."""

    ad = "kapanis__binhcluc-v6-b0451"
    varsayilan_parametreler = {"sure_dk": 300.0, "kilit": 0.01, "roi": 0.0181, "iz": 0.01, "iz_offset": 0.025,
                               "rsi_sinir": 50.0, "ema_ust": 50, "ssl_n": 20}
    cikis_ayarlari = _ca(yalniz_kar=True, kar_esik=0.1)

    def sinyaller(self, mumlar):
        p = self.parametreler
        b = self._bantlar(mumlar)
        kap, vol = b["kap"], mumlar["hacim"]
        u1 = _ust_1h(mumlar, int(p["ssl_n"]))
        e50, e200 = g.ema(kap, 50), g.ema(kap, 200)
        rsi = g.rsi(kap, 14)
        a = ((kap > u1["ema200"]) & (e50 > e200) & (u1["ema50"] > u1["ema200"])
             & _bb40_kolu(mumlar, b["bb40"], 0.031, 0.018, 0.233) & (vol > 0))
        c = ((kap > e200) & (kap > u1["ema200"]) & (kap < b["ema_slow"]) & (kap < 0.993 * b["bb20"]["alt"])
             & (vol < b["hort"] * 21) & (vol > 0))
        d_ = ((kap < g.ema(kap, 5)) & (u1["ssl_up"] > u1["ssl_dn"]) & (e50 > e200) & (u1["ema50"] > u1["ema200"])
              & (rsi < u1["rsi"] - 43.276) & (vol > 0))
        ust = b["bb20"]["ust"]
        cik = (kap > ust) & (kap.shift(1) > ust.shift(1)) & (vol > 0) & (rsi <= float(p["rsi_sinir"]))
        self._sakla(kap=kap, rsi=rsi)
        self._tf = _tf_dk(mumlar)
        sl_l, sl_s = _stoplar(mumlar, None)
        return _bitir(cerceve(mumlar, a | c | d_, False, sl_l, sl_s), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        p = self.parametreler
        if self._zarar_kilit(d, float(p["sure_dk"]), float(p["kilit"])):
            return True
        if not self._dz("rsi", i) <= float(p["rsi_sinir"]):      # confirm_trade_exit: RSI > 50 (ya da NaN) iken çıkış yok
            return False
        kar = d.kar_yuzde / 100.0
        if kar >= float(p["roi"]):
            return True
        zirve = d.en_yuksek / d.giris_fiyati - 1.0
        return bool(zirve >= float(p["iz_offset"]) and d.kapanis <= d.en_yuksek * (1.0 - float(p["iz"])))


class BinhClucV8B0454(_BinhClucKanca):
    """HAM:B001:454 (5m, long; CombinedBinHAndClucV8.py): ortak koşul: (açılışın 2 bar en yükseği - kapanış)/kapanış < 0,12 VE
    (12 bar) < 0,28. 5 kol (VEYA): (1) kapanış > 1h EMA200 VE EMA50 > EMA200 VE 1h EMA50 > 1h EMA200 VE BinHV45 (0,031 / 0,021 / 0,264)
    VE hacim > 0; (2) kapanış > EMA200 VE > 1h EMA200 VE 1h EMA50 > 1h EMA100 VE 1h EMA50 > 1h EMA200 VE kapanış < EMA50 VE kapanış <
    0,992 x BB20 alt VE hacim < SMA30[-1] x 29; (3) kapanış < SMA5 VE 1h SSL yukarı > aşağı VE EMA50 > EMA200 VE 1h EMA50 > 1h EMA200 VE
    (144 bar) < 0,36 VE RSI < 1h RSI - 50,48 VE hacim > 0; (4) SMA200 > SMA200[-20] VE 1h SMA200 > 1h SMA200[-16 (5m satır)] VE (144 bar) <
    0,36 VE (açılışın 24 bar en düşüğü - kapanış)/kapanış > 0,01 VE 1h RSI > 67 VE RSI < 38,5 VE MFI(14) < 36 VE hacim > 0; (5) kapanış > 1h
    EMA100 VE 1h EMA50 > 1h EMA100 VE (144 bar) < 0,36 VE SMA4(hacim) x 2 > hacim VE EMA26 > EMA12 VE (EMA26-EMA12) > açılış x 0,02 VE
    önceki fark > açılış/100 VE kapanış < BB20 alt VE hacim > 0. Çıkış: (kapanış > BB üst 4 ardışık mum VE hacim > 0) VEYA (RSI > 80 VE
    hacim > 0), yalnız kârda (offset %0,1). ROI %1000 (yok). Stop -0,99 -> ATR(14) x 3; custom_stoploss (kancada): açıkken > 280 dk VE
    zararda VEYA (kâr < -%5 VE SMA200 hem 5m hem 1h düşüyor): stop = kapanışın %1 altı (yalnız yukarı). custom_sell (kancada): kâr > %14 VE
    RSI < 58; > %8 VE RSI < 56; > %4 VE RSI < 50; > %1 VE RSI < 50; 0 < kâr < %4 VE SMA200 düşüyor; 0,1 < kâr < 0,4 VE (maks fiyat - giriş
    fiyatı)/100 > kâr + 0,03; 0,02 < kâr < 0,1 VE aynı terim > kâr + 0,015. Not: son iki koşul kaynaktaki gibi MUTLAK fiyat farkını kullanır
    (fiyat ölçeğine bağlı; kaynak hatası, aynen korundu)."""

    ad = "kapanis__binhcluc-v8-b0454"
    varsayilan_parametreler = {"dip1": 0.12, "dip2": 0.28, "dip3": 0.36, "bb40_bbdelta": 0.031, "bb40_closedelta": 0.021,
                               "bb40_tail": 0.264, "bb20_close": 0.992, "bb20_hacim": 29.0, "rsi_fark": 50.48, "min_inc": 0.01,
                               "rsi_1h": 67.0, "rsi": 38.5, "mfi": 36.0, "hacim_1": 2.0, "ema_acilis": 0.02, "rsi_ana": 80.0,
                               "sure_dk": 280.0, "ek_esik": -0.05, "kilit": 0.01}
    cikis_ayarlari = _ca(yalniz_kar=True, kar_esik=0.1)

    def sinyaller(self, mumlar):
        p = self.parametreler
        b = self._bantlar(mumlar)
        kap, ac, vol = b["kap"], mumlar["acilis"], mumlar["hacim"]
        u1 = _ust_1h(mumlar, 20)
        e = {n: g.ema(kap, n) for n in (12, 26, 50, 200)}
        sma5, sma200 = g.sma(kap, 5), g.sma(kap, 200)
        rsi = g.rsi(kap, 14)
        mf = _mfi(mumlar["yuksek"], mumlar["dusuk"], kap, vol, 14)
        dec = (sma200 < sma200.shift(20)).astype(float)

        def dip(n):
            return (ac.rolling(n, min_periods=n).max() - kap) / kap

        ortak = (dip(2) < float(p["dip1"])) & (dip(12) < float(p["dip2"]))
        d144 = dip(144) < float(p["dip3"])
        alt = b["bb20"]["alt"]
        k1 = ((kap > u1["ema200"]) & (e[50] > e[200]) & (u1["ema50"] > u1["ema200"]) & ortak
              & _bb40_kolu(mumlar, b["bb40"], float(p["bb40_bbdelta"]), float(p["bb40_closedelta"]), float(p["bb40_tail"]))
              & (vol > 0))
        k2 = ((kap > e[200]) & (kap > u1["ema200"]) & (u1["ema50"] > u1["ema100"]) & (u1["ema50"] > u1["ema200"]) & ortak
              & (kap < b["ema_slow"]) & (kap < float(p["bb20_close"]) * alt) & (vol < b["hort"] * float(p["bb20_hacim"])))
        k3 = ((kap < sma5) & (u1["ssl_up"] > u1["ssl_dn"]) & (e[50] > e[200]) & (u1["ema50"] > u1["ema200"]) & ortak & d144
              & (rsi < u1["rsi"] - float(p["rsi_fark"])) & (vol > 0))
        k4 = ((sma200 > sma200.shift(20)) & (u1["sma200"] > u1["sma200"].shift(16)) & ortak & d144
              & ((ac.rolling(24, min_periods=24).min() - kap) / kap > float(p["min_inc"]))
              & (u1["rsi"] > float(p["rsi_1h"])) & (rsi < float(p["rsi"])) & (mf < float(p["mfi"])) & (vol > 0))
        k5 = ((kap > u1["ema100"]) & (u1["ema50"] > u1["ema100"]) & ortak & d144
              & (vol.rolling(4, min_periods=4).mean() * float(p["hacim_1"]) > vol) & (e[26] > e[12])
              & ((e[26] - e[12]) > ac * float(p["ema_acilis"])) & ((e[26].shift(1) - e[12].shift(1)) > ac / 100.0)
              & (kap < alt) & (vol > 0))
        ust = b["bb20"]["ust"]
        cik = (((kap > ust) & (kap.shift(1) > ust.shift(1)) & (kap.shift(2) > ust.shift(2)) & (kap.shift(3) > ust.shift(3))
                & (vol > 0)) | ((rsi > float(p["rsi_ana"])) & (vol > 0)))
        self._sakla(kap=kap, rsi=rsi, dec=dec, kosul2=dec * u1["sma200_dec"])
        self._tf = _tf_dk(mumlar)
        sl_l, sl_s = _stoplar(mumlar, None)
        return _bitir(cerceve(mumlar, k1 | k2 | k3 | k4 | k5, False, sl_l, sl_s), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        i = d.mum_indeksi
        if not self._var(i):
            return False
        p = self.parametreler
        if self._zarar_kilit(d, float(p["sure_dk"]), float(p["kilit"]), float(p["ek_esik"]), "kosul2"):
            return True
        kar = d.kar_yuzde / 100.0
        rsi = self._dz("rsi", i)
        fark = (d.en_yuksek - d.giris_fiyati) / 100.0          # kaynaktaki gibi mutlak fiyat farkı / 100
        return bool((kar > 0.14 and rsi < 58) or (kar > 0.08 and rsi < 56) or (kar > 0.04 and rsi < 50)
                    or (kar > 0.01 and rsi < 50) or (0 < kar < 0.04 and self._dz("dec", i) > 0.5)
                    or (0.1 < kar < 0.4 and fark > kar + 0.03) or (0.02 < kar < 0.1 and fark > kar + 0.015))


class BinhClucMadV5B0459(_BinhClucKanca):
    """HAM:B001:459 (5m, long; CombinedBinHClucAndMADV5.py): giriş (VEYA, hacim > 0): (kapanış > EMA200 VE > 1h EMA200 VE kapanış < EMA50 VE
    kapanış < 0,99 x BB20 alt VE hacim < SMA30[-1] x 21); (kapanış < EMA50 VE kapanış < 0,975 x BB20 alt VE hacim < SMA30[-1] x 20 VE hacim <
    önceki hacim x 4 VE 1h RSI < 15); (kapanış > EMA200 VE > 1h EMA200 VE EMA26 > EMA12 VE fark > açılış x 0,02 VE önceki fark > açılış/100 VE
    hacim < önceki hacim x 4 VE kapanış < BB20 alt); (EMA26 > EMA12 VE fark > açılış x 0,03 VE önceki fark > açılış/100 VE hacim < önceki hacim x
    4 VE kapanış < BB20 alt); (kapanış < EMA5 [kaynakta `sma_5` adıyla EMA(5)] VE 1h SSL yukarı > aşağı VE EMA50 > EMA200 VE 1h EMA50 > 1h EMA200
    VE RSI < 1h RSI - 43,276). Çıkış: kapanış > BB20 orta x 1,01 VE hacim > 0. ROI {0:.021, 40:.005}. Stop -0,99 -> ATR(14) x 3; custom_stoploss:
    açıkken > 240 dk VE zararda: stop = kapanışın %1 altı (yalnız yukarı), kancada."""

    ad = "kapanis__binhclucmad-v5-b0459"
    varsayilan_parametreler = {"sure_dk": 240.0, "kilit": 0.01}
    cikis_ayarlari = _ca({0: 0.021, 40: 0.005}, 5)

    def sinyaller(self, mumlar):
        b = self._bantlar(mumlar)
        kap, ac, vol = b["kap"], mumlar["acilis"], mumlar["hacim"]
        u1 = _ust_1h(mumlar, 20)
        e = {n: g.ema(kap, n) for n in (12, 26, 50, 200)}
        alt = b["bb20"]["alt"]
        ev = vol < vol.shift(1) * 4
        fark = e[26] - e[12]
        fark1 = e[26].shift(1) - e[12].shift(1)
        k1 = ((kap > e[200]) & (kap > u1["ema200"]) & (kap < b["ema_slow"]) & (kap < 0.99 * alt)
              & (vol < b["hort"] * 21) & (vol > 0))
        k2 = ((kap < b["ema_slow"]) & (kap < 0.975 * alt) & (vol < b["hort"] * 20) & ev & (u1["rsi"] < 15) & (vol > 0))
        k3 = ((kap > e[200]) & (kap > u1["ema200"]) & (e[26] > e[12]) & (fark > ac * 0.02) & (fark1 > ac / 100.0) & ev
              & (kap < alt) & (vol > 0))
        k4 = ((e[26] > e[12]) & (fark > ac * 0.03) & (fark1 > ac / 100.0) & ev & (kap < alt) & (vol > 0))
        k5 = ((kap < g.ema(kap, 5)) & (u1["ssl_up"] > u1["ssl_dn"]) & (e[50] > e[200]) & (u1["ema50"] > u1["ema200"])
              & (g.rsi(kap, 14) < u1["rsi"] - 43.276) & (vol > 0))
        cik = (kap > b["bb20"]["orta"] * 1.01) & (vol > 0)
        self._sakla(kap=kap)
        self._tf = _tf_dk(mumlar)
        sl_l, sl_s = _stoplar(mumlar, None)
        return _bitir(cerceve(mumlar, k1 | k2 | k3 | k4 | k5, False, sl_l, sl_s), cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        p = self.parametreler
        return self._zarar_kilit(d, float(p["sure_dk"]), float(p["kilit"]))


# ================================================================ E0V1E
class _E0v1e(_KancaTaban):
    """E0V1E: RSI4/RSI14/RSI20, SMA15, CTI(20) girişleri (buy_1, buy_new); çıkış sinyali yok, custom_exit kancada."""

    HACIM_SARTI = False
    varsayilan_parametreler = {"rsi_hizli": 65.0, "rsi_alt": 19.0, "sma15_oran": 0.961, "cti": -0.04, "yeni_rsi_hizli": 34.0,
                               "yeni_rsi_alt": 28.0, "yeni_sma15": 0.96, "fastx": 61.0, "cci_zarar": 112.0,
                               "cci_zarar_kar": -0.15, "ma_kisa": 120, "ma_uzun": 240, "sl": 0.25}

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        yk, ds = mumlar["yuksek"], mumlar["dusuk"]
        sma15, cti = g.sma(kap, 15), _cti(kap, 20)
        rsi, rsi_f, rsi_s = g.rsi(kap, 14), g.rsi(kap, 4), g.rsi(kap, 20)
        dusuyor = rsi_s < rsi_s.shift(1)
        al = ((dusuyor & (rsi_f < float(p["rsi_hizli"])) & (rsi > float(p["rsi_alt"])) & (kap < sma15 * float(p["sma15_oran"]))
               & (cti < float(p["cti"])))
              | (dusuyor & (rsi_f < float(p["yeni_rsi_hizli"])) & (rsi > float(p["yeni_rsi_alt"]))
                 & (kap < sma15 * float(p["yeni_sma15"])) & (cti < float(p["cti"]))))
        if self.HACIM_SARTI:
            al &= mumlar["hacim"] > 0
        self._sakla(kap=kap, yk=yk, fastk=_fastk(mumlar, 5), cci=b2.cci(yk, ds, kap, 20),
                    ma_k=g.sma(kap, int(p["ma_kisa"])), ma_u=g.sma(kap, int(p["ma_uzun"])))
        self._tf = _tf_dk(mumlar)
        sl_l, sl_s = _stoplar(mumlar, float(p["sl"]))
        return cerceve(mumlar, al, False, sl_l, sl_s)

    def _durum(self, d: PozisyonDurumu):
        """(kapanış, yüksek, fastk, cci, ma_kısa, ma_uzun, kâr, min_kâr, HOLD, HOLD1, tutulan_dk)."""
        i, bas = d.mum_indeksi, d.giris_mum_indeksi
        kv, mk, mu = self._kd["kap"], self._kd["ma_k"], self._kd["ma_u"]
        with np.errstate(invalid="ignore"):
            ust = (kv[bas:i + 1] > mk[bas:i + 1]) | (kv[bas:i + 1] > mu[bas:i + 1])
        return (d.kapanis, self._kd["yk"][i], self._kd["fastk"][i], self._kd["cci"][i], mk[i], mu[i], d.kar_yuzde / 100.0,
                d.en_dusuk / d.giris_fiyati - 1.0, bool(ust.any()), bool((~ust).any()), (i - bas) * self._tf)


class E0v1eSharpeB0205(_E0v1e):
    """HAM:B001:205 (5m, long; E0V1E_53_Sharpe.py): buy_1: RSI20 < önceki RSI20 VE RSI4 < 65 VE RSI14 > 19 VE kapanış < SMA15 x 0,961 VE CTI(20) <
    -0,04; buy_new: aynı ama RSI4 < 34, RSI14 > 28, SMA15 x 0,96 (hacim şartı yok). Çıkış sinyali yok; custom_exit (kancada): kâr > 0 VE
    StochF(5,3) fastk > 61; min kâr <= -%10 VE kâr > -%15 VE CCI(20) > 112; HOLD (işlem boyunca kapanış > MA120 VEYA > MA240 görüldü) VE
    kapanış < MA120 VE < MA240 VE min kâr <= -%5; HOLD1 (kapanış her iki MA'nın altında bir mum görüldü) VE yüksek > MA120 ya da MA240 VE
    açılıştan > 5 dk. ROI %100 (yok); stop -%25; iz süren %0,3 (offset %3, yalnız offset sonrası). MA = SMA."""

    ad = "kapanis__e0v1e-sharpe-b0205"
    cikis_ayarlari = _ca({0: 1.0}, 5, (0.003, 0.03))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        p = self.parametreler
        kap, yk, fk, cci, mk, mu, kar, minp, hold, hold1, dk = self._durum(d)
        return bool((kar > 0 and fk > float(p["fastx"]))
                    or (minp <= -0.10 and kar > float(p["cci_zarar_kar"]) and cci > float(p["cci_zarar"]))
                    or (hold and kap < mk and kap < mu and minp <= -0.05)
                    or (hold1 and (yk > mk or yk > mu) and dk > 5))


class E0v1e2B0206(_E0v1e):
    """HAM:B001:206 (5m, long; E0V1E__2.py): giriş 205 ile aynı koşullar (eşikler: RSI4 < 40, RSI14 > 42, SMA15 x 0,973, CTI < 0,69; buy_new
    34/28/0,96) VE hacim > 0. custom_exit (kancada): kâr > 0 VE fastk > 84; CCI(20) > 80 VE yüksek >= giriş fiyatı; min kâr <= -%15 VE kâr >
    -%15 VE CCI > 120; HOLD VE kapanış < MA120 VE < MA240 VE açılıştan > 12 dk; HOLD1 VE yüksek > MA120 ya da MA240 VE -%10 <= min kâr <= -%5.
    ROI %100 (yok); stop -%25 sabit (use_custom_stoploss=False); iz süren kapalı."""

    ad = "kapanis__e0v1e-2-b0206"
    HACIM_SARTI = True
    varsayilan_parametreler = {**_E0v1e.varsayilan_parametreler, "rsi_hizli": 40.0, "rsi_alt": 42.0, "sma15_oran": 0.973,
                               "cti": 0.69, "fastx": 84.0, "cci_zarar": 120.0, "cci_zarar_kar": -0.15, "cci_yuksek": 80.0}
    cikis_ayarlari = _ca({0: 1.0}, 5)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        if not self._var(d.mum_indeksi):
            return False
        p = self.parametreler
        kap, yk, fk, cci, mk, mu, kar, minp, hold, hold1, dk = self._durum(d)
        return bool((kar > 0 and fk > float(p["fastx"]))
                    or (cci > float(p["cci_yuksek"]) and yk >= d.giris_fiyati)
                    or (minp <= -0.15 and kar > float(p["cci_zarar_kar"]) and cci > float(p["cci_zarar"]))
                    or (hold and kap < mk and kap < mu and dk > 12)
                    or (hold1 and (yk > mk or yk > mu) and -0.10 <= minp <= -0.05))


# ================================================================ sınıf listesi, koşu listesi
def _p(sinif) -> dict:
    return dict(sinif.varsayilan_parametreler)


def _v(kaynak: str, sinif, tf: str) -> dict:
    return {"kimlik": f"{kaynak}#v1", "sinif": sinif.ad, "parametreler": _p(sinif), "tf": tf}


_SATIRLAR = [
    ("HAM:B001:69", AngleWaveCtB0069, "5m"), ("HAM:B001:156", AwAtrCtB0156, "15m"),
    ("HAM:B001:395", BbRpbTslB0395, "5m"), ("HAM:B001:399", BbRpbTslVwapB0399, "5m"),
    ("HAM:B001:469", BbRsiOptim2020B0469, "5m"), ("HAM:B001:470", BbRsiOptimB0470, "5m"),
    ("HAM:B001:506", GodCardB0506, "5m"), ("HAM:B001:533", Bbrsi1B0533, "5m"),
    ("HAM:B001:434", ClucHaNix5mB0434, "5m"), ("HAM:B001:440", ClucHaNixHhllB0440, "5m"),
    ("HAM:B001:547", FahmibahB0547, "5m"), ("HAM:B001:442", BinhCluc2021B0442, "5m"),
    ("HAM:B001:446", BinhClucV2B0446, "5m"), ("HAM:B001:449", BinhClucV5B0449, "5m"),
    ("HAM:B001:451", BinhClucV6B0451, "5m"), ("HAM:B001:454", BinhClucV8B0454, "5m"),
    ("HAM:B001:459", BinhClucMadV5B0459, "5m"), ("HAM:B001:205", E0v1eSharpeB0205, "5m"),
    ("HAM:B001:206", E0v1e2B0206, "5m"), ("HAM:B001:105", OverwatchB0105, "1h"),
    ("HAM:B001:221", ElB0221, "5m"), ("HAM:B001:558", ElliotV2B0558, "5m"),
    ("HAM:B001:561", ElliotV5HoB0561, "5m"), ("HAM:B001:666", MultiOffsetLamboB0666, "5m"),
    ("HAM:B001:673", NotAnotherSmaLiteB0673, "5m"), ("HAM:B001:694", SmaOfsetProtectB0694, "5m"),
]

SINIFLAR = [s for _, s, _ in _SATIRLAR]
VARYANTLAR = [_v(k, s, tf) for k, s, tf in _SATIRLAR]

KODLANAMADI = [
    {"kimlik": "HAM:B001:406",
     "neden": "giriş koşulunun zorunlu parçası is_btc_safe BTC/USDT 5m bilgi çifti (btc_diff, btc_5m, btc_1d) ister; motor tek sembollü "
              "mum verisiyle çalışır, ikinci sembol verisi yok. Ayrıca 1h Ichimoku(20,60,120,30) technical kütüphanesinin tanımıyla "
              "(chikou/leading_senkou) kaynak dosyada yok; uydurma çözüm yok"},
    {"kimlik": "HAM:B001:846",
     "neden": "sinyal göstergeleri finta kütüphanesinden (SQZMI, VFI(14), MFI, DMI): formülleri kaynak dosyada yok, uydurmadan birebir "
              "yazılamaz; ayrıca kaynak Freqtrade-özgü dinamik ROI (min_roi_reached override: rmi/ssl/candle trendi) ve SROC tabanlı "
              "custom_stoploss kullanıyor"},
    {"kimlik": "HAM:B001:847",
     "neden": "846 ile aynı sinyal çekirdeği (finta SQZMI/VFI/MFI/DMI tanımları kaynak dosyada yok) ve dinamik ROI + SROC custom_stoploss "
              "(CryptoFrogHO); uydurma çözüm yok"},
]
