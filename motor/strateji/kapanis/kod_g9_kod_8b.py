"""Kapanış turu, kodlama partisi g9_kod_8b (girdi: sonuclar/kapanis/kod_girdi/g9_kod_8b.csv, 14 kaynak satırı, HAM:B001).

Her sınıf, kaynak Freqtrade dosyasının (RoboticAutomations/freqtradestrategies) okunmasından kendi cümlelerimizle yazılmış bir
uyarlamadır; üçüncü taraf kodu kopyalanmadı, kaynak dosyalar çalıştırılmadı. Sinyal kapanmış mumdan, dolum sonraki açılıştan (motor).
Hepsi nedensel; üst zaman dilimi yalnız `motor.strateji.htf.ust_zaman` ile KAPANMIŞ mumdan alınır.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa ya da <= -%50 ise stop = kapanış -/+ 3 x ATR(14) (ön kayıt uyarlaması): 147, 148, 210, 616, 686, 889.
  Diğerlerinde kaynak yüzde stopu sinyal kapanışından hesaplanır.
- `minimal_roi` (dakika anahtarlı) -> `CikisAyarlari.azalan_roi` (mum = yukarı yuvarlanmış dakika / TF dakikası); "ROI 10" = %1000 =
  devre dışı kabul edilip boş bırakıldı (377, 616). Kâr kapanışta sınanır, çıkış sonraki açılışta (kaynakta mum içi).
- `trailing_stop` + offset -> `geri_cekilme_yuzde` (iz) + `geri_cekilme_min_kar_yuzde` (offset). `trailing_only_offset_is_reached`
  varsayılanı False olan satırlarda (607, 608) kaynak, offset öncesi stoploss mesafesiyle (%10) iz sürer; motorda tek iz var: yalnız
  offset sonrası iz (%2) + sabit %10 stop kuruldu (offset öncesi iz süren %10 yerine sabit %10: küçük fark).
- `custom_stoploss` (155, 842, 889) `pozisyon_cikisi` kancasında: kaynak Freqtrade'de stop yalnız yukarı çekilir (ratchet); kanca her
  kapanışta girişten beri hesaplanan stop seviyelerinin en yükseğini (önceki mumlardan) kapanışla karşılaştırır (kapanış bazlı).
- Kaynakta göstergeler TA-Lib/pandas_ta ile ısınır; burada motorun EMA/RSI/ATR tanımları kullanıldığından ilk mumlarda küçük fark olur.

Kaynak ile `kural_tam` özeti arasındaki farklarda KAYNAK dosya esas alındı:
- 210: kaynakta use_exit_signal = False -> sinyal çıkışı yok; eşikler .json hyperopt dosyasından (irm üst 1,643; alt -2,087), ROI tablosu
  ve iz süren aynı json'da (offset %3, iz %1,5, yalnız offset sonrası).
- 607/608: kaynakta can_short tanımlı değil (spot): short girişleri çalışmaz. Kısa kollar `kisa` parametresiyle (varsayılan 0) kodlu.
  608'de çıkış long için pfe_smooth < 0.
- 842: dosyada s3 dalı (buy_signal_3 = True) VAR (kural_tam "s3 dalı yok" diyordu); üç dal da kodlandı (`s3` parametresi 1).
  Sinyal çıkışı yok (use_sell_signal False), ROI 10 devre dışı, stop -%16 + custom_stoploss basamakları.
- 905: dosyada buy_wavetrend kullanılmıyor; çıkış koşulu rsi_ma [sell_rsil, sell_rsiu] bandında VE wave_t1_pc <= sell_wavetrend VE
  rsi_ma eğimi <= 0. Hyperopt json'ı yok: sınıf varsayılanları. ROI {0: %30,9; 60dk: -%1}: negatif basamak `azalan_roi`ye giremez,
  kancada (tutulan >= 1 mum ise kâr% >= -1 iken çık).
- 906: .json etkin: buy_rsil 17,857 / buy_rsiu 59,127 / sell_rsil 74,119 / sell_rsiu 72,996 (alt > üst: sinyal çıkışı imkânsız) /
  sell_wavetrend 0,594; ROI {0: %36,1; 3300dk: %10,4; 6532dk: %5,8; 31495dk: 0}; stop -%25,5. RSI periyodu 14 (populate_indicators).

KODLANAMADI: 661 (MSO): kaynakta it_osc/lt_osc, st_osc döngüsünden sonra kalan SON durum sözlüklerini (st_high/st_low) sabit okur
-> tüm-seri durumuna bağlı (lookahead); uydurma çözüm yok.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari, PozisyonDurumu
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.gostergeler_b2 import yukari_kesis as yukari
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import KancaDestek, roi_tablosu as _roi
from motor.strateji.temel import Strateji


# ---------------------------------------------------------------- yardımcılar
def _atr_mesafe(m: pd.DataFrame, n: int = 14, k: float = 3.0) -> pd.Series:
    return k * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], n)


def _bitir(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _tipik(m: pd.DataFrame) -> pd.Series:
    return (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0


def _minmax(x: pd.Series, n: int) -> pd.Series:
    lo, hi = x.rolling(n).min(), x.rolling(n).max()
    return (x - lo) / (hi - lo + 1e-9)


def _gfi(m: pd.DataFrame, pencere: int, sma_n: int, atr_n: int, yuzde_atr: bool) -> pd.Series:
    """Greed & Fear: momentum (kapanış - SMA)/SMA, volatilite ATR/kapanış, hacim duyarlılığı (yükselen-düşen mum hacmi oranı);
    her biri son `pencere` mumda min-max normalize, üçünün ortalaması."""
    kap = m["kapanis"]
    ma = g.sma(kap, sma_n)
    mom = (kap - ma) / ma
    vol = g.atr(m["yuksek"], m["dusuk"], kap, atr_n) / kap * (100.0 if yuzde_atr else 1.0)
    yuk = m["hacim"] * (kap > m["acilis"])
    dus = m["hacim"] * (kap < m["acilis"])
    toplam = (yuk + dus).replace(0, 1)
    duyarlilik = (yuk - dus) / toplam
    return (_minmax(mom, pencere) + _minmax(vol, pencere) + _minmax(duyarlilik, pencere)) / 3.0


def _kademeli_stop_seviyesi(d: PozisyonDurumu, kap: np.ndarray, seviye_fn):
    """Girişten (dahil) önceki mumlara kadar hesaplanan stop seviyelerinin en yükseği (stop yalnız yukarı çekilir)."""
    a, i = d.giris_mum_indeksi, d.mum_indeksi
    if i <= a or i > len(kap):
        return -np.inf
    j = np.arange(a, i)
    sev = seviye_fn(j, kap[a:i], d.tutulan_mum - (i - j))
    sev = sev[~np.isnan(sev)]
    return float(sev.max()) if sev.size else -np.inf


# ================================================================ B001:147
class GfiB0147(Strateji):
    """HAM:B001:147 (1h, long+short; kaynak strategies/moving-average/GnF.py): GFI = (momentum + volatilite + hacim duyarlılığı) / 3, her biri
    son 20 mumda min-max normalize (momentum = (kapanış - SMA20)/SMA20; volatilite = ATR(14)/kapanış; duyarlılık = (yükselen mum hacmi -
    düşen mum hacmi)/toplam). GFI > 0,7 -> long, GFI < 0,3 -> short; çıkış long için GFI < 0,3, short için GFI > 0,7. ROI yok, stop -%99
    -> ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__gfi-b0147", "swing"
    varsayilan_parametreler = {"pencere": 20, "sma_n": 20, "atr_n": 14, "gfi_ust": 0.7, "gfi_alt": 0.3, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        f = _gfi(mumlar, int(p["pencere"]), int(p["sma_n"]), int(p["atr_n"]), False)
        ust, alt = float(p["gfi_ust"]), float(p["gfi_alt"])
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, f > ust, f < alt, kap - mes, kap + mes)
        return _bitir(s, f < alt, f > ust)


# ================================================================ B001:148
class GfiHacimB0148(Strateji):
    """HAM:B001:148 (1h, long+short; kaynak strategies/moving-average/GnF_V2.py): 147'deki GFI (volatilite = NATR(14) = ATR/kapanış x 100;
    min-max sonrası fark yok) + her iki giriş yönünde ek süzgeç: hacim > SMA(hacim, 50). Çıkışlar aynı (long GFI < 0,3; short GFI > 0,7,
    hacim süzgeci çıkışta yok). Stop -%99 -> ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__gfi-hacim-b0148", "swing"
    varsayilan_parametreler = {"pencere": 20, "sma_n": 20, "atr_n": 14, "gfi_ust": 0.7, "gfi_alt": 0.3, "hacim_n": 50,
                               "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        f = _gfi(mumlar, int(p["pencere"]), int(p["sma_n"]), int(p["atr_n"]), True)
        ust, alt = float(p["gfi_ust"]), float(p["gfi_alt"])
        hac = mumlar["hacim"] > g.sma(mumlar["hacim"], int(p["hacim_n"]))
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, (f > ust) & hac, (f < alt) & hac, kap - mes, kap + mes)
        return _bitir(s, f < alt, f > ust)


# ================================================================ B001:155
def _zl_trend(m: pd.DataFrame, n: int, mult: float) -> pd.DataFrame:
    """Zero-lag EMA + volatilite bandı trendi: zlema = EMA(kapanış + (kapanış - kapanış[lag]), n), lag = (n-1)//2; volatilite =
    mult x en yüksek(ATR(n), 3n); kapanış > önceki üst bant -> +1, < önceki alt bant -> -1, aksi halde önceki trend."""
    kap = m["kapanis"]
    lag = (n - 1) // 2
    zl = g.ema(kap + (kap - kap.shift(lag)), n)
    vol = g.atr(m["yuksek"], m["dusuk"], kap, n).rolling(n * 3).max() * mult
    ust, alt = zl + vol, zl - vol
    t = pd.Series(0.0, index=m.index)
    t[kap > ust.shift(1)] = 1.0
    t[kap < alt.shift(1)] = -1.0
    t = t.replace(0.0, np.nan).ffill().fillna(0.0)
    return pd.DataFrame({"trend": t, "vol": vol})


class ZeroLagB0155(KancaDestek, Strateji):
    """HAM:B001:155 (1h, long; kaynak strategies/moving-average/ZeroLag.py): her TF (1h, 4h, 1d) için zero-lag trend (uzunluk 21, çarpan
    1,2). Giriş: bu üç trendden herhangi birinin +1'e DÖNÜŞÜ (önceki 1h satırda +1 değildi) VE hacim > 0 (4h/1d yalnız KAPANMIŞ mumdan,
    htf.ust_zaman). Çıkış: aynı TF'lerden herhangi birinde -1'e dönüş. Stop: sabit -%10 ve custom_stoploss = kapanış - 0,5 x volatilite(1h)
    (yalnız yukarı çekilir; kancada kapanış bazlı)."""

    ad, stil = "kapanis__zerolag-b0155", "swing"
    varsayilan_parametreler = {"uzunluk": 21, "carpan": 1.2, "sl": 0.10, "vol_k": 0.5}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        n, mult = int(p["uzunluk"]), float(p["carpan"])
        kap = mumlar["kapanis"]
        var = mumlar["hacim"] > 0
        h1 = _zl_trend(mumlar, n, mult)
        h4 = ust_zaman(mumlar, "4h", lambda u: _zl_trend(u, n, mult)[["trend"]])["trend"]
        d1 = ust_zaman(mumlar, "1d", lambda u: _zl_trend(u, n, mult)[["trend"]])["trend"]
        al = pd.Series(False, index=mumlar.index)
        cik = pd.Series(False, index=mumlar.index)
        for t in (h1["trend"], h4, d1):
            al |= (t == 1) & (t.shift(1) != 1) & var
            cik |= (t == -1) & (t.shift(1) != -1) & var
        sl, k = float(p["sl"]), float(p["vol_k"])
        stop = np.maximum(kap * (1 - sl), kap - k * h1["vol"])
        self._sakla(kapanis=kap.to_numpy(), vol=h1["vol"].to_numpy())
        s = cerceve(mumlar, al, False, stop, kap * 2.0)
        return _bitir(s, cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        p = self.parametreler
        k = float(p["vol_k"])
        vol = self._kd["vol"]
        kap = self._kd["kapanis"]
        sev = _kademeli_stop_seviyesi(d, kap, lambda j, kp, tut: kp - k * vol[j])
        sev = max(sev, d.giris_fiyati * (1 - float(p["sl"])))
        return d.kapanis <= sev


# ================================================================ B001:210
def _irm(m: pd.DataFrame) -> pd.Series:
    """Piyasa dönüş indeksi: ivme değişimi (kapanış farkının farkı) x çekiç - ivme değişimi x kayan yıldız + hacim sapması (20 mum z-skoru)."""
    ac, yu, du, kap, hac = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"], m["hacim"]
    ivme = kap.diff().diff()
    aralik = yu - du
    cekic = ((kap > ac) & (aralik > 2 * (ac - du)) & ((kap - ac) / (0.001 + aralik) > 0.6)).astype(float)
    yildiz = ((kap < ac) & (aralik > 2 * (yu - kap)) & ((ac - kap) / (0.001 + aralik) > 0.6)).astype(float)
    sapma = (hac - hac.rolling(20).mean()) / hac.rolling(20).std()
    return ivme * cekic - ivme * yildiz + sapma


_IRM_ROI = {0: 0.5, 60: 0.45, 120: 0.4, 240: 0.3, 360: 0.25, 720: 0.2, 1440: 0.15, 2880: 0.1, 3600: 0.05, 7200: 0.02}


class IrmB0210(Strateji):
    """HAM:B001:210 (1h, long+short; kaynak strategies/rsi-momentum/InnovativeReversalStrategy.py + .json): IRM > 1,643 -> long, IRM < -2,087
    -> short (json değerleri). Sinyal çıkışı YOK (use_exit_signal False). ROI tablosu (json) azalan_roi, iz süren %1,5 (offset %3, yalnız
    offset sonrası). Stop -%99 -> ATR(14)x3 (uyarlama). Kaldıraç (leverage_input) alınmadı."""

    ad, stil = "kapanis__irm-b0210", "swing"
    varsayilan_parametreler = {"irm_ust": 1.643, "irm_alt": -2.087, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi(_IRM_ROI, 60), geri_cekilme_yuzde=1.5, geri_cekilme_min_kar_yuzde=3.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        irm = _irm(mumlar)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        return cerceve(mumlar, irm > float(p["irm_ust"]), irm < float(p["irm_alt"]), kap - mes, kap + mes)


# ================================================================ B001:377
class MinmaxB0377(Strateji):
    """HAM:B001:377 (1h, long; kaynak dosya dirty LA/from-repo/uncategorized/Minmax.py, geleceksiz dilim sürümü): her mum j için önceki 500
    mumluk dilim (j-500..j-1); dilimin sondan ikinci mumu (j-2) kapanış bazında yerel dip ise (kendinden önceki 100 kapanıştan KÜÇÜK ve
    sonraki mumdan küçük; order=100, kenar kırpmalı) j mumunda long; yerel tepe ise çıkış (sell_signal). ilk 500 mumda sinyal yok.
    ROI {0: 10} (%1000) devre dışı; stop -%5. (Kaynağın yorumlu tüm-seri/lookahead bloğu kapalı, kullanılmadı.)"""

    ad, stil = "kapanis__minmax-b0377", "swing"
    varsayilan_parametreler = {"dilim": 500, "order": 100, "sl": 0.05}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        o = int(p["order"])
        c2, c1 = kap.shift(2), kap.shift(1)
        yeterli = pd.Series(np.arange(len(kap)) >= int(p["dilim"]), index=kap.index)
        dip = (c2 < kap.rolling(o).min().shift(3)) & (c2 < c1) & yeterli
        tepe = (c2 > kap.rolling(o).max().shift(3)) & (c2 > c1) & yeterli
        sl = float(p["sl"])
        s = cerceve(mumlar, dip, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, tepe)


# ================================================================ B001:607 / 608 (GKD)
def _hurst(kap: pd.Series, period: int) -> pd.Series:
    """Hurst (R/S): önceki `period` log getirisi (mevcut mum hariç); pencere eksikse 0,5; r veya s sıfırsa varyans yolu; [0,1] kırpılı."""
    lr = np.log(kap / kap.shift(1)).to_numpy()
    h = np.full(len(lr), np.nan)
    for i in range(period, len(lr)):
        w = lr[i - period:i]
        w = w[~np.isnan(w)]
        if len(w) < period:
            h[i] = 0.5
            continue
        sapma = np.cumsum(w - w.mean())
        r = sapma.max() - sapma.min()
        s = w.std(ddof=1)
        if s == 0 or r == 0 or np.isnan(s) or np.isnan(r):
            var = w.var(ddof=1)
            h[i] = float(np.clip(0.5 + np.log(var) / (2 * np.log(period)), 0, 1)) if var > 0 else 0.5
            continue
        h[i] = float(np.clip(np.log(r / s) / np.log(period), 0, 1))
    return pd.Series(h, index=kap.index)


def _pfe(kap: pd.Series, period: int) -> pd.Series:
    """Polarize fraktal verimlilik: 100 x sqrt(fark^2 + n^2) / sum(sqrt(adım^2 + 1)); işaret net fark yönünde; ilk n mumda 0."""
    fark = kap - kap.shift(period)
    dogru = np.sqrt(fark ** 2 + period ** 2)
    yol = np.sqrt(kap.diff() ** 2 + 1.0).rolling(period).sum()
    v = 100.0 * dogru / yol
    v = v.where(fark >= 0, -v)
    v.iloc[:period] = 0.0
    return v


def _gkd_bant(m: pd.DataFrame, baz_n: int, atr_n: int, kmin: float, kmax: float):
    kap = m["kapanis"]
    baz = g.ema(kap, baz_n)
    fark = baz.diff()
    atr = g.atr(m["yuksek"], m["dusuk"], kap, atr_n)
    ic = (kap >= baz - atr * kmin) & (kap <= baz + atr * kmax)
    return fark > 0, fark < 0, ic


_GKD_ROI = {0: 0.05, 60: 0.03, 120: 0.01}


class GkdHurstB0607(Strateji):
    """HAM:B001:607 (1h, long [+short `kisa`]; kaynak strategies/gkd/GKD_HurstExponent.py): Hurst(64, önceki 64 log getiri, R/S) EMA(5) ile
    yumuşatılır; long: hurst_smooth > 0,55 VE EMA(20) eğimi > 0 VE kapanış [EMA20 - 0,2 ATR(14), EMA20 + 1,0 ATR(14)] bandında; çıkış
    hurst_smooth < 0,25. ROI {0: %5; 60dk: %3; 120dk: %1}; iz süren %2 (offset %3); stop -%10. Kaynakta can_short tanımsız: short yalnız
    `kisa`=1 ile (aynı koşulların aşağı eğimli hali)."""

    ad, stil = "kapanis__gkd-hurst-b0607", "swing"
    varsayilan_parametreler = {"hurst_n": 64, "yumusat": 5, "esik": 0.55, "cikis_esik": 0.25, "baz_n": 20, "atr_n": 14,
                               "bant_min": 0.2, "bant_max": 1.0, "sl": 0.10, "kisa": 0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi(_GKD_ROI, 60), geri_cekilme_yuzde=2.0, geri_cekilme_min_kar_yuzde=3.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        hs = g.ema(_hurst(kap, int(p["hurst_n"])), int(p["yumusat"]))
        yuk, dus, ic = _gkd_bant(mumlar, int(p["baz_n"]), int(p["atr_n"]), float(p["bant_min"]), float(p["bant_max"]))
        guclu = hs > float(p["esik"])
        kisa = bool(p["kisa"])
        sl = float(p["sl"])
        zayif = hs < float(p["cikis_esik"])
        s = cerceve(mumlar, guclu & yuk & ic, (guclu & dus & ic) if kisa else False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, zayif, zayif if kisa else None)


class GkdPfeB0608(Strateji):
    """HAM:B001:608 (1h, long [+short `kisa`]; kaynak strategies/gkd/GKD_PFE.py): PFE(10) EMA(5) ile yumuşatılır; long: pfe_smooth > 30 VE
    EMA(20) eğimi > 0 VE kapanış [EMA20 - 0,5 ATR(14), EMA20 + 2,0 ATR(14)] bandında; long çıkışı pfe_smooth < 0 (kısa kol: < -30 giriş,
    > 0 çıkış, yalnız `kisa`=1). ROI {0: %5; 60dk: %3; 120dk: %1}; iz süren %2 (offset %3); stop -%10. Kaynakta can_short tanımsız."""

    ad, stil = "kapanis__gkd-pfe-b0608", "swing"
    varsayilan_parametreler = {"pfe_n": 10, "yumusat": 5, "al_esik": 30.0, "sat_esik": -30.0, "baz_n": 20, "atr_n": 14,
                               "bant_min": 0.5, "bant_max": 2.0, "sl": 0.10, "kisa": 0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi(_GKD_ROI, 60), geri_cekilme_yuzde=2.0, geri_cekilme_min_kar_yuzde=3.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ps = g.ema(_pfe(kap, int(p["pfe_n"])), int(p["yumusat"]))
        yuk, dus, ic = _gkd_bant(mumlar, int(p["baz_n"]), int(p["atr_n"]), float(p["bant_min"]), float(p["bant_max"]))
        kisa = bool(p["kisa"])
        sl = float(p["sl"])
        s = cerceve(mumlar, (ps > float(p["al_esik"])) & yuk & ic,
                    ((ps < float(p["sat_esik"])) & dus & ic) if kisa else False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, ps < 0, (ps > 0) if kisa else None)


# ================================================================ B001:616
class HeikinSmaB0616(Strateji):
    """HAM:B001:616 (1h, long; kaynak strategies/heikin-ashi/heikin.py): hclose = (a + y + d + k)/4; hopen = (açılış[t-2] + kapanış[t-2])/2
    (kaynaktaki 'gerçek HA değil' tanımı); emac = SMA(hclose, 6), emao = SMA(hopen, 6). emao < emac -> long (durum, her mumda);
    emao > emac -> çıkış. ROI {0: 10} devre dışı; stop -%99 -> ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__heikin-sma-b0616", "swing"
    varsayilan_parametreler = {"sma_n": 6, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        hclose = (mumlar["acilis"] + mumlar["yuksek"] + mumlar["dusuk"] + kap) / 4.0
        hopen = (mumlar["acilis"].shift(2) + kap.shift(2)) / 2.0
        n = int(p["sma_n"])
        emac, emao = g.sma(hclose, n), g.sma(hopen, n)
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, emao < emac, False, kap - mes, kap + mes)
        return _bitir(s, emao > emac)


# ================================================================ B001:686
class GovdeKirmiziB0686(Strateji):
    """HAM:B001:686 (4h, long; kaynak strategies/moving-average/RobotradingBody.py): gövde = |kapanış - açılış|; kırmızı mum (açılış > kapanış)
    VE gövde > 3 x SMA(gövde, 100) VE hacim > 0 -> long (durum, her mumda); çıkış: yeşil mum (kapanış > açılış) VE hacim > 0.
    ROI {0: %90} (azalan_roi); stop -%99 -> ATR(14)x3 (uyarlama)."""

    ad, stil = "kapanis__govde-kirmizi-b0686", "swing"
    varsayilan_parametreler = {"carpan": 3, "sma_n": 100, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=((0, 90.0),))

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, ac = mumlar["kapanis"], mumlar["acilis"]
        govde = (kap - ac).abs()
        esik = g.sma(govde, int(p["sma_n"])) * int(p["carpan"])
        var = mumlar["hacim"] > 0
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        s = cerceve(mumlar, (ac > kap) & (govde > esik) & var, False, kap - mes, kap + mes)
        return _bitir(s, (kap > ac) & var)


# ================================================================ B001:842
class ApolloB0842(KancaDestek, Strateji):
    """HAM:B001:842 (1h, long; kaynak strategies/schism-hyperion/apollo.py): üç giriş dalından biri (VEYA), hacim > 0:
    s1: VWMACD < sinyali VE düşük < EMA240 VE kapanış > EMA240 VE EMA5, EMA10'u yukarı keser VE EMA3 < EMA50.
    s2: (SMA50 - 4,236 x ATR14) alt bandı (SMA49 - 3 x std64) bandını yukarı keser VE kapanış < 2 x EMA50 (kaynaktaki ofset -1 işlemi).
    s3: düşük < Bollinger(tipik fiyat, 20, 3s) alt bandı VE düşük > EMA240.
    Sinyal çıkışı yok; ROI devre dışı; stop -%16 + custom_stoploss basamakları (kâr >%3: kapanışın %1 altı; >%6: %2; >%10: %3; >%20: %4;
    zarar <= -%10 ve 60 saat sonra: kayıp/1,75; zarar <= -%8 ve 120 saat sonra: kayıp/1,70; yalnız yukarı çekilir) kancada."""

    ad, stil = "kapanis__apollo-b0842", "swing"
    varsayilan_parametreler = {"s1": 1, "s2": 1, "s3": 1, "sl": 0.16}
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def _mesafe(kar: np.ndarray, saat: np.ndarray) -> np.ndarray:
        d = np.select(
            [kar > 0.2, kar > 0.1, kar > 0.06, kar > 0.03, (kar <= -0.10) & (saat > 60), (kar <= -0.08) & (saat > 120)],
            [0.04, 0.03, 0.02, 0.01, np.abs(kar) / 1.75, np.abs(kar) / 1.70], default=np.nan)
        return d

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap, dus, yuk, hac = mumlar["kapanis"], mumlar["dusuk"], mumlar["yuksek"], mumlar["hacim"]
        e = {n: g.ema(kap, n) for n in (3, 5, 10, 50, 240)}
        vw_hizli = g.ema(hac * kap, 12) / g.ema(hac, 12)
        vw_yavas = g.ema(hac * kap, 26) / g.ema(hac, 26)
        vwmacd = vw_hizli - vw_yavas
        sinyal = g.ema(vwmacd, 9)
        var = hac > 0
        s1 = ((vwmacd < sinyal) & (dus < e[240]) & (kap > e[240]) & yukari(e[5], e[10]) & (e[3] < e[50]) & var)
        fib = g.sma(kap, 50) - g.atr(yuk, dus, kap, 14) * 4.236
        bb = g.sma(kap, 49) - kap.rolling(64).std(ddof=0) * 3
        s2 = yukari(fib, bb) & (kap < 2.0 * e[50]) & var
        tp = _tipik(mumlar)
        alt3 = tp.rolling(20).mean() - 3.0 * tp.rolling(20).std()
        s3 = (dus < alt3) & (dus > e[240]) & var
        al = pd.Series(False, index=mumlar.index)
        for acik, kosul in ((p["s1"], s1), (p["s2"], s2), (p["s3"], s3)):
            if acik:
                al |= kosul
        sl = float(p["sl"])
        self._sakla(kapanis=kap.to_numpy())
        return cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        giris = d.giris_fiyati

        def seviye(j, kp, tutulan):
            dist = self._mesafe(kp / giris - 1.0, tutulan.astype(float))
            return kp * (1.0 - dist)

        sev = _kademeli_stop_seviyesi(d, self._kd["kapanis"], seviye)
        return d.kapanis <= sev


# ================================================================ B001:889
class NormalizerB0889(KancaDestek, Strateji):
    """HAM:B001:889 (1h, long; kaynak strategies/uncategorized/NormalizerStrategy.py): pct_sum = 9 min-max normalizasyonun toplamı, her biri
    (kapanış - son L+1 kapanışın en düşüğü)/(en yüksek - en düşük), L = 13, 21, 34, 55, 89, 144, 233, 377, 610 (ilk L mumda 0; en yüksek = en
    düşükse boş sayılır). pct_sum < 0,2 VE hacim > 0 -> long; pct_sum > 8 VE hacim > 0 -> çıkış, yalnız kârda (kâr > %0,1). ROI %18
    (ignore_roi_if_buy_signal: o mumda giriş sinyali varsa ROI yok sayılır -> kancada); iz süren %1 (offset %1,5, yalnız offset sonrası);
    custom_stoploss: kâr < 0 ve 300 dk (>= 6 mum) sonra kapanışın %1 altı stop (yalnız yukarı çekilir; kancada). Stop -%99 -> ATR(14)x3
    (uyarlama)."""

    ad, stil = "kapanis__normalizer-b0889", "swing"
    varsayilan_parametreler = {"pencereler": (13, 21, 34, 55, 89, 144, 233, 377, 610), "al_esik": 0.2, "sat_esik": 8.0,
                               "roi": 0.18, "zarar_dk_mum": 6, "zarar_stop": 0.01, "atr_n": 14, "atr_k": 3.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(yalniz_karda_cikis=True, yalniz_karda_min_kar_yuzde=0.1,
                                   geri_cekilme_yuzde=1.0, geri_cekilme_min_kar_yuzde=1.5)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        pozisyon = np.arange(len(kap))
        toplam = pd.Series(0.0, index=kap.index)
        for lb in p["pencereler"]:
            lo, hi = kap.rolling(lb + 1).min(), kap.rolling(lb + 1).max()
            norm = ((kap - lo) / (hi - lo)).where(pozisyon >= lb, 0.0)
            toplam += norm.fillna(0.0)
        var = mumlar["hacim"] > 0
        al = (toplam < float(p["al_esik"])) & var
        cik = (toplam > float(p["sat_esik"])) & var
        mes = _atr_mesafe(mumlar, int(p["atr_n"]), float(p["atr_k"]))
        self._sakla(kapanis=kap.to_numpy(), al=al.to_numpy())
        s = cerceve(mumlar, al, False, kap - mes, kap + mes)
        return _bitir(s, cik)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        p = self.parametreler
        if d.kar_yuzde >= float(p["roi"]) * 100.0 and not self._kd["al"][d.mum_indeksi]:
            return True
        giris, mum, oran = d.giris_fiyati, int(p["zarar_dk_mum"]), float(p["zarar_stop"])

        def seviye(j, kp, tutulan):
            return np.where((kp < giris) & (tutulan >= mum), kp * (1.0 - oran), np.nan)

        return d.kapanis <= _kademeli_stop_seviyesi(d, self._kd["kapanis"], seviye)


# ================================================================ B001:905 / 906
class _DalgaRsi(Strateji):
    """pcb20 / tacos ortak kuralı: ap = (y + d + k + a)/4; esa = EMA(10, ap); d = EMA(10, |ap - esa|); ci = (ap - esa)/(0,015 d);
    wave_t1 = EMA(21, ci); wave_t2 = SMA(4, wave_t1); t1_pc = yuvarlak(100 x (t1 - t1[1])/|t1|, 2); rsi_ma = EMA(5, RSI(14)).
    Giriş (durum): t1 >= t2 VE buy_rsil <= rsi_ma <= buy_rsiu VE rsi_ma eğimi (fark) > 0. Çıkış: t1_pc <= sell_wavetrend VE
    sell_rsil <= rsi_ma <= sell_rsiu VE rsi_ma eğimi <= 0."""

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        kap = mumlar["kapanis"]
        ap = 0.25 * (mumlar["yuksek"] + mumlar["dusuk"] + kap + mumlar["acilis"])
        esa = g.ema(ap, 10)
        d = g.ema((ap - esa).abs(), 10)
        t1 = g.ema((ap - esa) / (0.015 * d), 21)
        t2 = g.sma(t1, 4)
        t1_pc = ((t1 - t1.shift(1)) / t1.abs() * 100.0).round(2)
        rsi_ma = g.ema(g.rsi(kap, int(p["rsi_n"])), 5)
        egim = rsi_ma.diff()
        al = ((t1 >= t2) & (rsi_ma <= float(p["buy_rsiu"])) & (rsi_ma >= float(p["buy_rsil"])) & (egim > 0))
        cik = ((t1_pc <= float(p["sell_wt"])) & (rsi_ma >= float(p["sell_rsil"])) & (rsi_ma <= float(p["sell_rsiu"]))
               & (egim <= 0))
        sl = float(p["sl"])
        s = cerceve(mumlar, al, False, kap * (1 - sl), kap * (1 + sl))
        return _bitir(s, cik)


class Pcb20B0905(_DalgaRsi):
    """HAM:B001:905 (6h, long; kaynak strategies/wavetrend/pcb20.py, .json yok -> sınıf varsayılanları): bkz. _DalgaRsi. buy_rsil 40, buy_rsiu 50,
    sell_rsil 70, sell_rsiu 80, sell_wavetrend 0. ROI {0: %30,9; 60dk: -%1}: ilk basamak azalan_roi, negatif basamak kancada (tutulan >= 1 mum
    ise kâr% >= -1 iken çık). Stop -%1,5."""

    ad, stil = "kapanis__dalga-rsi-b0905", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "buy_rsil": 40.0, "buy_rsiu": 50.0, "sell_rsil": 70.0, "sell_rsiu": 80.0,
                               "sell_wt": 0.0, "sl": 0.015, "negatif_roi_mum": 1, "negatif_roi": 1.0}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=((0, 30.9),))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        p = self.parametreler
        return d.tutulan_mum >= int(p["negatif_roi_mum"]) and d.kar_yuzde >= -float(p["negatif_roi"])


class TacosB0906(_DalgaRsi):
    """HAM:B001:906 (1d, long; kaynak strategies/wavetrend/tacos.py + tacos.json, json etkin): bkz. _DalgaRsi. buy_rsil 17,857, buy_rsiu 59,127,
    sell_rsil 74,119, sell_rsiu 72,996 (alt > üst: çıkış sinyali imkânsız), sell_wavetrend 0,594. ROI {0: %36,1; 3300dk: %10,4; 6532dk: %5,8;
    31495dk: 0} (1d mum: 0, 3, 5, 22). Stop -%25,5."""

    ad, stil = "kapanis__dalga-rsi-b0906", "swing"
    varsayilan_parametreler = {"rsi_n": 14, "buy_rsil": 17.857, "buy_rsiu": 59.127, "sell_rsil": 74.119, "sell_rsiu": 72.996,
                               "sell_wt": 0.594, "sl": 0.255}
    parametre_izgarasi = {}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.361, 3300: 0.104, 6532: 0.058, 31495: 0.0}, 1440))


# ================================================================ koşu listesi
def _p(sinif) -> dict:
    return dict(sinif.varsayilan_parametreler)


def _v(kaynak: str, no: int, sinif, tf: str, parametreler: dict | None = None) -> dict:
    return {"kimlik": f"{kaynak}#v{no}", "sinif": sinif.ad,
            "parametreler": _p(sinif) if parametreler is None else parametreler, "tf": tf}


SINIFLAR = [GfiB0147, GfiHacimB0148, ZeroLagB0155, IrmB0210, MinmaxB0377, GkdHurstB0607, GkdPfeB0608, HeikinSmaB0616,
            GovdeKirmiziB0686, ApolloB0842, NormalizerB0889, Pcb20B0905, TacosB0906]

VARYANTLAR = [
    _v("HAM:B001:147", 1, GfiB0147, "1h"),
    _v("HAM:B001:148", 1, GfiHacimB0148, "1h"),
    _v("HAM:B001:155", 1, ZeroLagB0155, "1h"),
    _v("HAM:B001:210", 1, IrmB0210, "1h"),
    _v("HAM:B001:377", 1, MinmaxB0377, "1h"),
    _v("HAM:B001:607", 1, GkdHurstB0607, "1h"),
    _v("HAM:B001:608", 1, GkdPfeB0608, "1h"),
    _v("HAM:B001:616", 1, HeikinSmaB0616, "1h"),
    _v("HAM:B001:686", 1, GovdeKirmiziB0686, "4h"),
    _v("HAM:B001:842", 1, ApolloB0842, "1h"),
    _v("HAM:B001:889", 1, NormalizerB0889, "1h"),
    _v("HAM:B001:905", 1, Pcb20B0905, "6h"),
    _v("HAM:B001:906", 1, TacosB0906, "1d"),
]

KODLANAMADI = [
    {"kimlik": "HAM:B001:661",
     "neden": "lookahead: MSO.py'de it_osc/lt_osc, st_osc döngüsü bittikten sonraki SON st_high/st_low durum sözlüklerini sabit okur "
              "(tüm-seri durumu); geleceksiz kodlanabilecek bir yorum yok, uydurma çözüm yapılmadı."},
]
