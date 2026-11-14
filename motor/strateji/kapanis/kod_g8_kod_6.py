"""Kapanış turu kodlama partisi g8_kod_6 (girdi: sonuclar/kapanis/kod_girdi/g8_kod_6.csv, 39 kaynak satırı).

Hepsi HAM:X005:* (trend / ortalamaya dönüş listesi). Her kaynak satır için bir sınıf (ya da `KODLANAMADI` kaydı) vardır.
Kurallar `kural_tam` metninden kendi cümlelerimizle yazıldı; üçüncü taraf kodu kopyalanmadı. Sinyal kapanmış mumdan, dolum
sonraki açılıştan (motor); gelecek verisi yok. Üst zaman dilimi yalnız `motor.strateji.htf.ust_zaman` ile KAPANMIŞ mumdan.

Ortak uyarlamalar (satır notlarında tekrar edilmez):
- Kaynak stopu yoksa (ya da <= -%50 ise) stop = kapanış -/+ 3 x ATR(14) (ön kayıt uyarlaması).
- Kaynak yüzde stopu / hedefi sinyal kapanışından hesaplanır (dolum sonraki açılıştan).
- Freqtrade `minimal_roi` tablosu (dakika anahtarlı) `CikisAyarlari.azalan_roi` ile: mum sayısı = yukarı yuvarlanmış dakika /
  TF dakikası (aynı muma düşen basamakta büyük dakikalı olan geçerli). Tek basamaklı ROI (zaman yok) de `azalan_roi = ((0, yüzde),)`
  (`RoiTek` karışımı).
- Freqtrade yüzde iz süren stop (574, 577, 578) ve zirveden geri çekilme (635, 643...) strateji kancasıyla (`pozisyon_cikisi`,
  kod_g8_modul.tepe_geri_cekilme): zirve = giriş sonrası en yüksek HIGH, çıkış eşiği zirve fiyatının %'si, kapanışta kontrol.
- Kaynak çıkışı kapanış bazlıysa sınıfın kendi `cikis_long` / `cikis_short` sinyaliyle ya da pozisyon bilinçli modülle yazıldı.
- 1w / 1M satırları (606, 639, 655) 1d mumlarla koşulur (VARYANTLAR tf = "1d"): haftalık değerler `htf.ust_zaman("1w")` ile yalnız
  kapanmış haftadan, karar yeni haftanın ilk günü; aylık (606) ay sonu günlük kapanışlarından (karar ay sonu kapanışı).

Arşiv eşleşmesi (kural d): X005:594 kuralı `kapanis__rsi2-sma5-s0253` (kod_g8_kod_3) ile birebir aynı yapıdadır (RSI(2) eşiği
10); yeni sınıf yazılmadı, VARYANTLAR o sınıfın adıyla ve eşik 10 ile kaydedildi.

KODLANAMADI: 580, 585 (portföy ağırlık stratejisi). 573, 584, 629, 643, 644 pozisyon bilinçli modülle `kod_g8_modul.py`'ye taşındı.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b2
from motor.strateji._gosterge_d11j import hma as _hma
from motor.strateji._gosterge_d11j import mfi as _mfi
from motor.strateji._gosterge_d11j import wma as _wma
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d3 import td_sayim as _td_sayim
from motor.strateji.dis._gosterge_d10a import connors_rsi as _connors_rsi
from motor.strateji.cikislar import PozisyonDurumu
from motor.strateji.htf import ust_zaman
from motor.strateji.kapanis.kod_g8_modul import (KancaDestek, ParametreliCikis, RoiTek, ay_sonu_bayragi, hafta_degerleri,
                                                  tepe_geri_cekilme)
from motor.strateji.temel import Strateji

yukari = b2.yukari_kesis
asagi = b2.asagi_kesis


# ---------------------------------------------------------------- yardımcılar
def _roi(tablo: dict, tf_dk: float) -> tuple:
    """{dakika: oran} -> ((mum, kâr%), ...). Aynı muma düşen basamaklarda büyük dakikalı olan geçerli."""
    d = {}
    for dk in sorted(tablo):
        d[int(math.ceil(dk / tf_dk))] = round(float(tablo[dk]) * 100.0, 6)
    return tuple(sorted(d.items()))


def _atr3(m: pd.DataFrame, p: dict) -> pd.Series:
    return float(p["atr_k"]) * g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_n"]))


def _atr_sma(m: pd.DataFrame, n: int) -> pd.Series:
    """Gerçek aralığın basit ortalaması."""
    return g.gercek_aralik(m["yuksek"], m["dusuk"], m["kapanis"]).rolling(n, min_periods=n).mean()


def _bitir(sonuc: pd.DataFrame, cikis_long=None, cikis_short=None) -> pd.DataFrame:
    if cikis_long is not None:
        sonuc["cikis_long"] = pd.Series(cikis_long, index=sonuc.index).fillna(False).astype(bool)
    if cikis_short is not None:
        sonuc["cikis_short"] = pd.Series(cikis_short, index=sonuc.index).fillna(False).astype(bool)
    return sonuc


def _once(x: pd.Series) -> pd.Series:
    """Koşulu bir mum geriye alır (önceki mumdaki durum)."""
    return x.shift(1, fill_value=False).astype(bool)


def _ma(seri: pd.Series, n: int, tip: str = "sma") -> pd.Series:
    return g.ema(seri, n) if str(tip).lower() == "ema" else g.sma(seri, n)


def _tipik(m: pd.DataFrame) -> pd.Series:
    return (m["yuksek"] + m["dusuk"] + m["kapanis"]) / 3.0


def _stop_sinirla(kap: pd.Series, stop: pd.Series, atr_mesafe: pd.Series, yon: int) -> pd.Series:
    """Kaynak stopu giriş fiyatının %50'sinden uzaksa (fiilen stopsuz) ATR uyarlaması (ön kayıt politikası)."""
    uzak = (kap - stop) / kap if yon == 1 else (stop - kap) / kap
    return stop.where(uzak < 0.5, kap - yon * atr_mesafe)


def _cmo(kap: pd.Series, n: int) -> pd.Series:
    """Chande momentum osilatörü, TA-Lib biçimi (Wilder yumuşatma): 2 x RSI(n) - 100."""
    return 2.0 * g.rsi(kap, n) - 100.0


def _cti(kap: pd.Series, n: int) -> pd.Series:
    """Correlation Trend Indicator: son n kapanışın zaman indeksiyle Pearson korelasyonu (-1..1)."""
    a = kap.to_numpy(dtype=float)
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        x = np.arange(n, dtype=float)
        xc = x - x.mean()
        w = sliding_window_view(a, n)
        yc = w - w.mean(axis=1, keepdims=True)
        pay = yc @ xc
        payda = np.sqrt((yc ** 2).sum(axis=1) * (xc ** 2).sum())
        with np.errstate(divide="ignore", invalid="ignore"):
            out[n - 1:] = pay / payda
    out[~np.isfinite(out)] = np.nan
    return pd.Series(out, index=kap.index)


def _siegel_uc(kap: pd.Series, n: int) -> pd.Series:
    """Son n kapanışa Siegel tekrarlı medyan doğrusu (hiyerarşik kesişim); değer = doğrunun son noktası
    (kesişim + eğim x (n-1)). Nedensel: her satır yalnız kendi penceresini görür."""
    a = kap.to_numpy(dtype=float)
    out = np.full(len(a), np.nan)
    if len(a) >= n:
        w = sliding_window_view(a, n)
        x = np.arange(n, dtype=float)
        dx = x[None, :] - x[:, None]
        np.fill_diagonal(dx, np.nan)
        dy = w[:, None, :] - w[:, :, None]
        with np.errstate(divide="ignore", invalid="ignore"):
            egim_i = np.nanmedian(dy / dx[None, :, :], axis=2)
        egim = np.median(egim_i, axis=1)
        kesis = np.median(w - egim[:, None] * x[None, :], axis=1)
        sonuc = kesis + egim * (n - 1)
        sonuc[np.isnan(w).any(axis=1)] = np.nan
        out[n - 1:] = sonuc
    return pd.Series(out, index=kap.index)


class _Taban(Strateji):
    stil = "swing"
    parametre_izgarasi = {}

    def cikis_var_mi(self) -> bool:
        return True


_ATR = {"atr_n": 14, "atr_k": 3.0}


# ================================================================ X005:561
class Yuksek20TemasS0561(_Taban):
    """HAM:X005:561 (1d, long): gün yükseği son 20 günün (bugün dahil) en yüksek yükseğine eşit/üstündeyse (yeni 20 günlük
    zirve) long; 2 bar sonra zaman çıkışı. Pozisyon yokken (motor açık pozisyonda yeni girişi atlar).
    Uyarlama: kaynak aynı gün kapanışında (MOC) doluyor, bizde sonraki açılış; stop yok -> ATR(14)x3."""

    ad = "kapanis__yuksek20-temas-s0561"
    varsayilan_parametreler = {"yuksek_n": 20, **_ATR}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=2)

    def sinyaller(self, m):
        p = self.parametreler
        n = int(p["yuksek_n"])
        kap = m["kapanis"]
        gir = m["yuksek"] >= m["yuksek"].rolling(n, min_periods=n).max()
        r = _atr3(m, p)
        return cerceve(m, gir, False, kap - r, kap + r)


# ================================================================ X005:567
class CmcWinnerS0567(_Taban):
    """HAM:X005:567 (15m, long): bir önceki mumda CCI(14) < -100 VE MFI(14) < 20 VE CMO(14) < -50 -> long; bir önceki mumda
    CCI > 100 VE MFI > 80 VE CMO > 50 -> çık. ROI: girişten 0-20 dk %5, 20-30 dk %3, 30-40 dk %2, >= 40 dk %0 (kârda çık);
    stop -%5. CMO TA-Lib biçimi (Wilder). Uyarlama yok (kaynak stopu var)."""

    ad = "kapanis__cmc-winner-s0567"
    varsayilan_parametreler = {"cci_n": 14, "mfi_n": 14, "cmo_n": 14, "stop_yuzde": 0.05}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.05, 20: 0.03, 30: 0.02, 40: 0.0}, 15))

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        cci = b2.cci(h, d, k, int(p["cci_n"]))
        mfi = _mfi(h, d, k, m["hacim"], int(p["mfi_n"]))
        cmo = _cmo(k, int(p["cmo_n"]))
        gir = _once((cci < -100) & (mfi < 20) & (cmo < -50))
        cik = _once((cci > 100) & (mfi > 80) & (cmo > 50))
        sl = float(p["stop_yuzde"])
        return _bitir(cerceve(m, gir, False, k * (1 - sl), k * (1 + sl)), cik)


# ================================================================ X005:570
class TdSayimGunSonusuzS0570(_Taban):
    """HAM:X005:570 (1h, long): TD alım kurulumu sayımı > 8 (9. ve sonrası) VE 8./9. mum düşüğü 6./7. mum düşüğünün altında
    -> long; çıkış satış sayımı > 8 ya da satış aşması (8./9. mum yükseği 6./7. yükseğini aşar). Stop giriş kapanışının %5
    altı. Sayım `dis._gosterge_d3.td_sayim` (geri 4, n 9). Arşivdeki TdSequential'dan fark: UTC gün sonu zorunlu çıkışı YOK."""

    ad = "kapanis__td-sayim-gunsonusuz-s0570"
    varsayilan_parametreler = {"geri": 4, "n": 9, "stop_yuzde": 0.05}

    def sinyaller(self, m):
        p = self.parametreler
        n = int(p["n"])
        t = _td_sayim(m["yuksek"], m["dusuk"], m["kapanis"], int(p["geri"]), n)
        ix = m.index
        alis = pd.Series(np.asarray(t["alis"]) > n - 1, index=ix)
        satis = pd.Series(np.asarray(t["satis"]) > n - 1, index=ix)
        asma_alt = pd.Series(np.asarray(t["asma_alt"], dtype=bool), index=ix)
        asma_ust = pd.Series(np.asarray(t["asma_ust"], dtype=bool), index=ix)
        k = m["kapanis"]
        sl = float(p["stop_yuzde"])
        return _bitir(cerceve(m, asma_alt & alis, False, k * (1 - sl), k * (1 + sl)), asma_ust | satis)


# ================================================================ X005:571
class EmaOranBandiS0571(_Taban):
    """HAM:X005:571 (5m, long): EMA(12)/EMA(26) - 1 değeri [-0,01416; -0,01176] aralığındayken long. Sinyal çıkışı yok
    (kaynaktaki çıkış koşulu hiç doğru olmaz); çıkış ROI tablosu: 0 dk %21,3; 27 dk %9,9; 60 dk %3; 164 dk %0. Stop -%31,8."""

    ad = "kapanis__ema-oran-bant-s0571"
    varsayilan_parametreler = {"ema_h": 12, "ema_y": 26, "oran_alt": -0.01416, "oran_ust": -0.01176, "stop_yuzde": 0.318}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.213, 27: 0.099, 60: 0.03, 164: 0.0}, 5))

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        oran = g.ema(k, int(p["ema_h"])) / g.ema(k, int(p["ema_y"])) - 1.0
        gir = (oran >= float(p["oran_alt"])) & (oran <= float(p["oran_ust"]))
        sl = float(p["stop_yuzde"])
        return cerceve(m, gir, False, k * (1 - sl), k * (1 + sl))


# ================================================================ X005:572
class Cci72Rsi36S0572(_Taban):
    """HAM:X005:572 (15m, long): CCI(72) < -175 VE RSI(36) < 90 -> long; çıkış CCI(66) > -106 VE RSI(45) > 88. ROI 0 dk %27,1;
    33 dk %8,5; 64 dk %4,1; 244 dk %0; stop -%34,338. RSI Wilder (standart)."""

    ad = "kapanis__cci72-rsi36-s0572"
    varsayilan_parametreler = {"cci_g": 72, "cci_g_esik": -175.0, "rsi_g": 36, "rsi_g_esik": 90.0,
                               "cci_c": 66, "cci_c_esik": -106.0, "rsi_c": 45, "rsi_c_esik": 88.0, "stop_yuzde": 0.34338}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.271, 33: 0.085, 64: 0.041, 244: 0.0}, 15))

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        gir = (b2.cci(h, d, k, int(p["cci_g"])) < float(p["cci_g_esik"])) & (g.rsi(k, int(p["rsi_g"])) < float(p["rsi_g_esik"]))
        cik = (b2.cci(h, d, k, int(p["cci_c"])) > float(p["cci_c_esik"])) & (g.rsi(k, int(p["rsi_c"])) > float(p["rsi_c_esik"]))
        sl = float(p["stop_yuzde"])
        return _bitir(cerceve(m, gir, False, k * (1 - sl), k * (1 + sl)), cik)


# ================================================================ X005:574
class Rsi4Ema100S0574(KancaDestek, _Taban):
    """HAM:X005:574 (1h, long): RSI(4) 15'i yukarı keser (önceki < 15 <= şimdi) VE mum düşüğü > EMA(100) -> long; çıkış RSI(4)
    85'i yukarı keserse ya da mum düşüğü < EMA(100) olursa. Stop giriş kapanışının %10 altı, iz süren: giriş sonrası zirve fiyatın (en
    yüksek HIGH) %10 altına kapanış inerse çık (kanca). Trailing offset kaynakta yazılı değil: offset yok (varsayım)."""

    ad = "kapanis__rsi4-ema100-s0574"
    varsayilan_parametreler = {"rsi_n": 4, "alt": 15.0, "ust": 85.0, "ema_n": 100, "stop_yuzde": 0.10}

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return tepe_geri_cekilme(d, float(self.parametreler["stop_yuzde"]) * 100.0)

    def sinyaller(self, m):
        p = self.parametreler
        k, d = m["kapanis"], m["dusuk"]
        r = g.rsi(k, int(p["rsi_n"]))
        ema = g.ema(k, int(p["ema_n"]))
        a, u = float(p["alt"]), float(p["ust"])
        gir = ((r.shift(1) < a) & (r >= a) & (d > ema)).fillna(False)
        cik = (((r.shift(1) < u) & (r >= u)) | (d < ema)).fillna(False)
        sl = float(p["stop_yuzde"])
        return _bitir(cerceve(m, gir, False, k * (1 - sl), k * (1 + sl)), cik)


# ================================================================ X005:576
class VwapDipS0576(RoiTek, _Taban):
    """HAM:X005:576 (5m, long): kayan VWAP(20; tipik fiyat x hacim) - 1 x std(VWAP, 20) alt bandı altında kapanış VE son 4 mumun
    en yüksek açılışından kapanışa düşüş > %4 VE CTI(20) < -0,8 VE RSI(14) < 35 VE RSI(84) < 60 VE RSI(112) < 60 -> long.
    Sinyal çıkışı yok; ROI +%2 (azalan_roi); stop -%15.
    Uyarlama: düşüş oranı en yüksek açılışa göre; bant std'si VWAP serisinin 20 mumluk örnek std'si (ddof=1)."""

    ad = "kapanis__vwap-dip-s0576"
    varsayilan_parametreler = {"vwap_n": 20, "vwap_k": 1.0, "dusus_mum": 4, "dusus_esik": 0.04, "cti_n": 20, "cti": -0.8,
                               "rsi14": 35.0, "rsi84": 60.0, "rsi112": 60.0, "roi": 0.02, "stop_yuzde": 0.15}

    def sinyaller(self, m):
        p = self.parametreler
        k, v = m["kapanis"], m["hacim"]
        n = int(p["vwap_n"])
        vwap = (_tipik(m) * v).rolling(n, min_periods=n).sum() / v.rolling(n, min_periods=n).sum().where(lambda x: x > 0)
        alt = vwap - float(p["vwap_k"]) * vwap.rolling(n, min_periods=n).std()
        ac_max = m["acilis"].rolling(int(p["dusus_mum"]), min_periods=int(p["dusus_mum"])).max()
        dusus = (ac_max - k) / ac_max > float(p["dusus_esik"])
        gir = ((k < alt) & dusus & (_cti(k, int(p["cti_n"])) < float(p["cti"])) & (g.rsi(k, 14) < float(p["rsi14"]))
               & (g.rsi(k, 84) < float(p["rsi84"])) & (g.rsi(k, 112) < float(p["rsi112"])))
        sl = float(p["stop_yuzde"])
        return cerceve(m, gir, False, k * (1 - sl), k * (1 + sl))


# ================================================================ X005:577
class DonchianAgirlikliBbS0577(KancaDestek, _Taban):
    """HAM:X005:577 (5m, long): Donchian(52) alt bandı - ağırlıklı Bollinger(20, 2 sigma, tipik fiyat) alt bandı farkı sıfırı
    yukarı keser VE mum yeşil VE kapanış < Parabolik SAR(0,02/0,2; o mumun SAR değeri) VE ADX(14) > 25 VE +DI >= -DI -> long.
    Sinyal çıkışı yok. ROI 0 dk %27,8; 39 dk %8,7; 124 dk %3,8; 135 dk %0; stop -%33,3; kâr %21,2'yi geçince iz süren %17,2 (kanca: zirve kârı >= %21,2 iken kapanış, zirve fiyatın (en yüksek HIGH) %17,2 altına inerse çık).
    Uyarlama: ağırlıklı Bollinger = orta bant lineer ağırlıklı (WMA) tipik fiyat, sapma tipik fiyatın 20 mumluk örnek std'si
    (ddof=1); kaynak formülü yeniden doğrulanmalı (satır notu). +DM >= -DM, Wilder +DI >= -DI ile ifade edildi."""

    ad = "kapanis__donchian-agirlikli-bb-s0577"
    varsayilan_parametreler = {"donchian_n": 52, "bb_n": 20, "bb_k": 2.0, "adx_n": 14, "adx_esik": 25.0,
                               "sar_adim": 0.02, "sar_maks": 0.2, "stop_yuzde": 0.333}
    cikis_ayarlari = CikisAyarlari(azalan_roi=_roi({0: 0.278, 39: 0.087, 124: 0.038, 135: 0.0}, 5))

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return tepe_geri_cekilme(d, 17.2, 21.2)

    def sinyaller(self, m):
        p = self.parametreler
        h, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        tp = _tipik(m)
        n = int(p["bb_n"])
        wbb_alt = _wma(tp, n) - float(p["bb_k"]) * tp.rolling(n, min_periods=n).std()
        fark = d.rolling(int(p["donchian_n"]), min_periods=int(p["donchian_n"])).min() - wbb_alt
        kesis = yukari(fark, 0.0)
        sar = g.psar(h, d, float(p["sar_adim"]), float(p["sar_maks"]))["sar"].shift(1)
        ax = g.adx(h, d, k, int(p["adx_n"]))
        gir = kesis & (k > m["acilis"]) & (k < sar) & (ax["adx"] > float(p["adx_esik"])) & (ax["arti_di"] >= ax["eksi_di"])
        sl = float(p["stop_yuzde"])
        return cerceve(m, gir, False, k * (1 - sl), k * (1 + sl))


# ================================================================ X005:578
class SlowPotatoS0578(KancaDestek, _Taban):
    """HAM:X005:578 (5m, long): düşük <= SMA(düşük, 1440) -> long; çıkış yüksek >= SMA(yüksek, 1440). SMA mevcut mumu içerir,
    sinyal kapanmış mumdan. Kâr %3'ü geçince %2 iz süren stop (kanca: zirve kârı >= %3 iken kapanış zirve fiyatın %2 altına inerse); ROI etkisiz.
    Uyarlama: kaynak fiilen stopsuz (-%99) -> ATR(14)x3 felaket stopu; iz stop ofset koşulu kaynakta belirsiz, 'kâr > %3'ten
    sonra %2' diye okundu."""

    ad = "kapanis__slowpotato-s0578"
    varsayilan_parametreler = {"sma_n": 1440, **_ATR}

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return tepe_geri_cekilme(d, 2.0, 3.0)

    def sinyaller(self, m):
        p = self.parametreler
        n = int(p["sma_n"])
        k = m["kapanis"]
        gir = m["dusuk"] <= g.sma(m["dusuk"], n)
        cik = m["yuksek"] >= g.sma(m["yuksek"], n)
        r = _atr3(m, p)
        return _bitir(cerceve(m, gir, False, k - r, k + r), cik)


# ================================================================ X005:582
class IkiDipSma20S0582(_Taban):
    """HAM:X005:582 (6h, long): kapanış > SMA(20) VE mum düşüğü önceki iki mumun düşüklerinin ikisinden de düşük -> long; çıkış
    kapanış önceki iki mumun yüklerinin ikisinden de yüksek. Stop yok -> ATR(14)x3 (uyarlama)."""

    ad = "kapanis__sma20-iki-dip-s0582"
    varsayilan_parametreler = {"sma_n": 20, "geri": 2, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        geri = int(p["geri"])
        k = m["kapanis"]
        dus_onceki = m["dusuk"].shift(1).rolling(geri, min_periods=geri).min()
        yuk_onceki = m["yuksek"].shift(1).rolling(geri, min_periods=geri).max()
        gir = (k > g.sma(k, int(p["sma_n"]))) & (m["dusuk"] < dus_onceki)
        r = _atr3(m, p)
        return _bitir(cerceve(m, gir, False, k - r, k + r), k > yuk_onceki)


# ================================================================ X005:583
class MmmS0583(_Taban):
    """HAM:X005:583 (1h, long): kapanış > SMA(kapanış, 30) VE kapanış < SMA(düşük, 3) -> long; çıkış kapanış > SMA(yüksek, 3).
    Stop yok -> ATR(14)x3 (uyarlama). TF 1h sonuç dosyasından (kaynak kodda TF yok)."""

    ad = "kapanis__mmm-s0583"
    varsayilan_parametreler = {"trend_n": 30, "alt_n": 3, "ust_n": 3, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        gir = (k > g.sma(k, int(p["trend_n"]))) & (k < g.sma(m["dusuk"], int(p["alt_n"])))
        r = _atr3(m, p)
        return _bitir(cerceve(m, gir, False, k - r, k + r), k > g.sma(m["yuksek"], int(p["ust_n"])))


# ================================================================ X005:586
class Rsi2UcGunDusenS0586(_Taban):
    """HAM:X005:586 (1d, long): kapanış > SMA(200) VE RSI(2)[t-2] < 65 VE RSI(2)[t-1] < RSI(2)[t-2] VE RSI(2)[t] < RSI(2)[t-1]
    (3. günün kapanışı) -> long; çıkış RSI(2) > 75. Stop yok -> ATR(14)x3 (uyarlama)."""

    ad = "kapanis__rsi2-3gun-dusen-s0586"
    varsayilan_parametreler = {"rsi_n": 2, "baslangic": 65.0, "cikis": 75.0, "trend_ma": 200, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        gir = ((k > g.sma(k, int(p["trend_ma"]))) & (r.shift(2) < float(p["baslangic"]))
               & (r.shift(1) < r.shift(2)) & (r < r.shift(1)))
        rr = _atr3(m, p)
        return _bitir(cerceve(m, gir, False, k - rr, k + rr), r > float(p["cikis"]))


# ================================================================ X005:600
class KumoIzS0600(_Taban):
    """HAM:X005:600 (1d, iki yön): kapanış Kumo (Ichimoku 9/26/52/26, bulut nedensel) üst sınırının üstündeyse long, alt sınırının
    altındaysa short (pozisyon açıkken yeni sinyal yok: motor). Çıkış yalnız bulut kenarını izleyen stop: long için bulutun alt
    kenarı, short için üst kenarı.
    Uyarlama: izleyen stop kapanış bazlı `cikis_long` (kapanış < o günkü bulut alt kenarı) / `cikis_short` ile yazıldı; ek
    olarak giriş anında bulut kenarı sabit stop (kaynak stopu; mesafe >= %50 ise ATR(14)x3)."""

    ad = "kapanis__kumo-iz-s0600"
    varsayilan_parametreler = {"tenkan": 9, "kijun": 26, "senkou_b": 52, "kaydirma": 26, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        ic = b2.ichimoku(m["yuksek"], m["dusuk"], int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]), int(p["kaydirma"]))
        ust, alt = ic["bulut_ust"], ic["bulut_alt"]
        r = _atr3(m, p)
        stop_l = _stop_sinirla(k, alt, r, 1)
        stop_s = _stop_sinirla(k, ust, r, -1)
        return _bitir(cerceve(m, k > ust, k < alt, stop_l, stop_s), k < alt, k > ust)


# ================================================================ X005:606
class AylikSma10Rsi2S0606(_Taban):
    """HAM:X005:606 (1M; 1d mumlarla, iki yön): aylık barlar = ay sonu günlük kapanışları (takvimde ertesi gün başka ay: yalnız zaman
    damgasından, gelecek yok); sinyal ay SONU kapanışında, dolum sonraki açılış (yeni ayın ilk günü). Kapanış > SMA(10 ay) VE RSI(2, aylık
    kapanışlardan) > 80 -> long; kapanış < SMA(10 ay) VE RSI(2) > 30 -> short (kısa şart kaynakta böyle yazılı); kapanış hareketli
    ortalamanın karşı tarafına geçince çık (ay sonu kapanışında). Uyarlama: HO tipi SMA varsayıldı; stop yok -> ATR(14)x3 (günlük)."""

    ad = "kapanis__aylik-sma10-rsi2-s0606"
    varsayilan_parametreler = {"sma_ay": 10, "rsi_n": 2, "long_esik": 80.0, "short_esik": 30.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        ay_sonu = ay_sonu_bayragi(m.index)
        aylik = k[ay_sonu]
        sma = pd.Series(np.nan, index=m.index)
        r = pd.Series(np.nan, index=m.index)
        sma[ay_sonu] = g.sma(aylik, int(p["sma_ay"]))
        r[ay_sonu] = g.rsi(aylik, int(p["rsi_n"]))
        rr = _atr3(m, p)
        return _bitir(cerceve(m, ay_sonu & (k > sma) & (r > float(p["long_esik"])),
                              ay_sonu & (k < sma) & (r > float(p["short_esik"])), k - rr, k + rr),
                      ay_sonu & (k < sma), ay_sonu & (k > sma))


# ================================================================ X005:608
class Ma5DusenGunlerS0608(_Taban):
    """HAM:X005:608 (1d, iki yön): long: kapanış > SMA(ma_uzun) VE kapanış < SMA(5) VE son 5 kapanışın en az 4'ü bir önceki
    kapanıştan düşük -> long; çıkış kapanış > SMA(5). Short ayna (kapanış < SMA(ma_uzun), > SMA(5), son 5'in en az 4'ü
    yükseliş; çıkış kapanış < SMA(5)). ma_uzun: 200 (metin) ve 220 (AFL kodu) iki varyant. Stop yok -> ATR(14)x3 (uyarlama).
    Uyarlama: 'düşük kapanış' = bir önceki kapanıştan düşük; '4'ünde' = en az 4."""

    ad = "kapanis__ma5-dusen-gunler-s0608"
    varsayilan_parametreler = {"ma_uzun": 200, "ma_kisa": 5, "pencere": 5, "adet": 4, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        pen, adet = int(p["pencere"]), int(p["adet"])
        uzun, kisa = g.sma(k, int(p["ma_uzun"])), g.sma(k, int(p["ma_kisa"]))
        dus = (k < k.shift(1)).astype(float).rolling(pen, min_periods=pen).sum() >= adet
        yuk = (k > k.shift(1)).astype(float).rolling(pen, min_periods=pen).sum() >= adet
        rr = _atr3(m, p)
        return _bitir(cerceve(m, (k > uzun) & (k < kisa) & dus, (k < uzun) & (k > kisa) & yuk, k - rr, k + rr),
                      k > kisa, k < kisa)


# ================================================================ X005:611
class PazartesiDusSalitS0611(_Taban):
    """HAM:X005:611 (1d, long): UTC Pazartesi mumu kapanış < 0,99 x açılış VE kapanış > SMA(200) (bir önceki bar) -> Salı açılışında
    al (Pazartesi kapanış sinyali, sonraki açılış); çıkış kapanış > kapanış[2] ya da 10 bar. Stop yok -> ATR(14)x3 (uyarlama).
    Sepet kısıtı (maks 10 pozisyon, ROC sıralaması) tek varlık kuralını değiştirmediği için uygulanmadı."""

    ad = "kapanis__pazartesi-dus-s0611"
    varsayilan_parametreler = {"esik": 0.01, "sma_n": 200, "cikis_gecikme": 2, **_ATR}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=10)

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        pazartesi = pd.Series(m.index.dayofweek == 0, index=m.index)
        gir = pazartesi & (k < (1 - float(p["esik"])) * m["acilis"]) & (k > g.sma(k, int(p["sma_n"])).shift(1))
        r = _atr3(m, p)
        return _bitir(cerceve(m, gir, False, k - r, k + r), k > k.shift(int(p["cikis_gecikme"])))


# ================================================================ X005:621
class TenkanKijunDonS0621(_Taban):
    """HAM:X005:621 (1h, iki yön, dur-ve-dön): Tenkan = (HH9+LL9)/2, Kijun = (HH26+LL26)/2; Tenkan Kijun'u yukarı keserse long
    (açık short kapanır), aşağı keserse short. Bulut ve Senkou kaydırması YOK. Her zaman piyasada: ters kesişim sinyali
    karşı pozisyonu `cikis_*` ile kapatır, aynı açılışta yeni yön girilir. Stop yok -> ATR(14)x3 felaket stopu (uyarlama)."""

    ad = "kapanis__tk-kesisim-don-s0621"
    varsayilan_parametreler = {"tenkan": 9, "kijun": 26, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        n1, n2 = int(p["tenkan"]), int(p["kijun"])
        ten = (m["yuksek"].rolling(n1, min_periods=n1).max() + m["dusuk"].rolling(n1, min_periods=n1).min()) / 2.0
        kij = (m["yuksek"].rolling(n2, min_periods=n2).max() + m["dusuk"].rolling(n2, min_periods=n2).min()) / 2.0
        al, sat = yukari(ten, kij), asagi(ten, kij)
        r = _atr3(m, p)
        return _bitir(cerceve(m, al, sat, k - r, k + r), sat, al)


# ================================================================ X005:625
class IcuMaS0625(_Taban):
    """HAM:X005:625 (1d, long): ICU_MA(t) = son 5 kapanışa Siegel tekrarlı medyan doğrusunun (hiyerarşik kesişim, x = 0..4) son
    noktası; kapanış ICU_MA'yı aşağıdan yukarı keserse long, yukarıdan aşağı keserse kapat (T kapanış sinyali, T+1 açılış).
    Siegel tahmincisi kendi kodumuzla (scipy yok). Stop yok -> ATR(14)x3 (uyarlama)."""

    ad = "kapanis__icu-ma-s0625"
    varsayilan_parametreler = {"N": 5, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        icu = _siegel_uc(k, int(p["N"]))
        r = _atr3(m, p)
        return _bitir(cerceve(m, yukari(k, icu), False, k - r, k + r), asagi(k, icu))


# ================================================================ X005:626
class VmHmaS0626(_Taban):
    """HAM:X005:626 (1d, long): sinyal = [HMA(kapanış,50) / HMA(kapanış,50)[3]] x [HMA(hacim,5) / HMA(hacim,100)]; eşik = 1,125
    eğer SMA(kapanış,5) > SMA(kapanış,90), değilse 1,275; sinyal > eşik -> long, sinyal <= eşik -> çık.
    Uyarlama: SMA5/SMA90 serisi kapanıştan (tek yorum); stop yok -> ATR(14)x3."""

    ad = "kapanis__vm-hma-s0626"
    varsayilan_parametreler = {"hma_fiyat": 50, "geri": 3, "hma_hacim_k": 5, "hma_hacim_u": 100, "sma_k": 5, "sma_u": 90,
                               "esik_yukari": 1.125, "esik_asagi": 1.275, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k, v = m["kapanis"], m["hacim"].astype(float)
        hf = _hma(k, int(p["hma_fiyat"]))
        hu = _hma(v, int(p["hma_hacim_u"])).where(lambda x: x != 0)
        sinyal = (hf / hf.shift(int(p["geri"]))) * (_hma(v, int(p["hma_hacim_k"])) / hu)
        esik = pd.Series(np.where(g.sma(k, int(p["sma_k"])) > g.sma(k, int(p["sma_u"])),
                                  float(p["esik_yukari"]), float(p["esik_asagi"])), index=m.index)
        r = _atr3(m, p)
        return _bitir(cerceve(m, sinyal > esik, False, k - r, k + r), sinyal <= esik)


# ================================================================ X005:630
class ValueAreaSkorS0630(_Taban):
    """HAM:X005:630 (1h, iki yön): va = -(kapanış - VWAP60) / ATR(14, SMA TR); hv = hacim / SMA(hacim,20) - 1;
    mr = -z(kapanış, 40) (örnek std, ddof=1); her biri [-3,3] kırpılır; skor = kırp(1,1 va + 0,4 hv + 0,4 mr, [-3,3]).
    skor >= 0,85 long, <= -0,85 short; |skor| < 0,25 pozisyonu kapat; arası mevcut pozisyon korunur (karşı yön eşiği karşı
    pozisyonu da kapatıp yön değiştirir). VWAP60 = tipik fiyat x hacim 60 mumluk toplamı / hacim toplamı. Stop yok -> ATR(14)x3."""

    ad = "kapanis__va-skor-s0630"
    varsayilan_parametreler = {"va_pencere": 60, "atr_sma": 14, "z_pencere": 40, "hacim_pencere": 20,
                               "w_va": 1.1, "w_hv": 0.4, "w_mr": 0.4, "giris": 0.85, "cikis": 0.25, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k, v = m["kapanis"], m["hacim"].astype(float)
        n = int(p["va_pencere"])
        vwap = (_tipik(m) * v).rolling(n, min_periods=n).sum() / v.rolling(n, min_periods=n).sum().where(lambda x: x > 0)
        va = (-(k - vwap) / _atr_sma(m, int(p["atr_sma"])).where(lambda x: x > 0)).clip(-3, 3)
        hv = (v / g.sma(v, int(p["hacim_pencere"])).where(lambda x: x > 0) - 1.0).clip(-3, 3)
        zn = int(p["z_pencere"])
        z = (k - g.sma(k, zn)) / k.rolling(zn, min_periods=zn).std(ddof=1).where(lambda x: x > 0)
        mr = (-z).clip(-3, 3)
        skor = (float(p["w_va"]) * va + float(p["w_hv"]) * hv + float(p["w_mr"]) * mr).clip(-3, 3)
        e = float(p["giris"])
        long_ok, short_ok = skor >= e, skor <= -e
        kapat = skor.abs() < float(p["cikis"])
        r = _atr3(m, p)
        s = cerceve(m, long_ok, short_ok, k - r, k + r, cikis=kapat)
        return _bitir(s, short_ok, long_ok)


# ================================================================ X005:631
class AralikKanalS0631(_Taban):
    """HAM:X005:631 (5m, iki yön): giriş çizgileri: üst = önceki 5 barın en yükseği + 1,6 x önceki 5 barın ortalama (yüksek-düşük)
    aralığı; alt = önceki 5 barın en düşüğü - 1,6 x aynı ortalama. Bar yüksek > üst -> long; bar düşük < alt -> short.
    Long çıkış kapanış < alt çizgi, short çıkış kapanış > üst çizgi (ters sinyalde dön). Stop = karşı kanal çizgisi, en fazla
    ATR(14)x3 uzaklıkta (felaket). Uyarlama: kaynak emri bar içi tetikler; burada kapanmış mum sinyali + sonraki açılış.
    Çıkış kanalındaki 'tampon' giriş tamponu (1,6 x ort. aralık) ile aynı alındı (cikis_n = 5)."""

    ad = "kapanis__aralik-kanal-s0631"
    varsayilan_parametreler = {"giris_n": 5, "cikis_n": 5, "aralik_k": 1.6, "aralik_n": 5, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        an, gn, cn = int(p["aralik_n"]), int(p["giris_n"]), int(p["cikis_n"])
        tampon = float(p["aralik_k"]) * (h - d).shift(1).rolling(an, min_periods=an).mean()
        ust = h.shift(1).rolling(gn, min_periods=gn).max() + tampon
        alt = d.shift(1).rolling(cn, min_periods=cn).min() - tampon
        r = _atr3(m, p)
        stop_l = np.maximum(alt, k - r)
        stop_s = np.minimum(ust, k + r)
        return _bitir(cerceve(m, h > ust, d < alt, stop_l, stop_s), k < alt, k > ust)


# ================================================================ X005:633
class BbDonusH4S0633(_Taban):
    """HAM:X005:633 (1h, iki yön): LONG: önceki kapanış <= önceki BB(20,2) alt bant VE kapanış > alt bant VE (RSI(14) < 35 ya da
    önceki RSI < 35) VE son KAPANMIŞ H4 RSI(14) >= 30 VE ATR(14) < 2 x SMA(ATR(14), 50). SHORT ayna (üst bant, RSI > 65, H4 RSI
    <= 70). Çıkış: kapanış >= BB orta (long) / <= orta (short) ya da 24 bar zaman çıkışı. Stop giriş -/+ 2 x ATR(14); kâr
    1 x ATR olunca stop girişe çekilir (risk = 2 ATR -> `basabas_r_esigi` 0,5). Pozisyon varken yeni giriş yok (motor).
    Uyarlama: H4 RSI yalnız kapanmış H4 mumundan (`ust_zaman`; kaynak açık H4'ü sızdırıyor)."""

    ad = "kapanis__bb-donus-h4-s0633"
    varsayilan_parametreler = {"bb_n": 20, "bb_k": 2.0, "rsi_n": 14, "rsi_alt": 35.0, "rsi_ust": 65.0, "h4_long_min": 30.0,
                               "h4_short_max": 70.0, "atr_n": 14, "atr_sl_k": 2.0, "vol_ma": 50, "vol_filtre": 2.0}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=24, basabas_r_esigi=0.5)

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        bb = g.bollinger(k, int(p["bb_n"]), float(p["bb_k"]))
        rsi = g.rsi(k, int(p["rsi_n"]))
        h4 = ust_zaman(m, "4h", lambda u: g.rsi(u["kapanis"], int(p["rsi_n"])))
        atr = g.atr(m["yuksek"], m["dusuk"], k, int(p["atr_n"]))
        sakin = atr < float(p["vol_filtre"]) * g.sma(atr, int(p["vol_ma"]))
        long_ok = ((k.shift(1) <= bb["alt"].shift(1)) & (k > bb["alt"]) & ((rsi < float(p["rsi_alt"])) | (rsi.shift(1) < float(p["rsi_alt"])))
                   & (h4 >= float(p["h4_long_min"])) & sakin)
        short_ok = ((k.shift(1) >= bb["ust"].shift(1)) & (k < bb["ust"]) & ((rsi > float(p["rsi_ust"])) | (rsi.shift(1) > float(p["rsi_ust"])))
                    & (h4 <= float(p["h4_short_max"])) & sakin)
        r = float(p["atr_sl_k"]) * atr
        return _bitir(cerceve(m, long_ok, short_ok, k - r, k + r), k >= bb["orta"], k <= bb["orta"])


# ================================================================ X005:634
class IchimokuBulutKirilimS0634(_Taban):
    """HAM:X005:634 (1h, iki yön): önceki kapanış bulut tepesinin üstünde değilken kapanış (26 bar kaydırılmış, nedensel)
    Senkou A/B bulut tepesinin üstüne çıkar VE Tenkan(9) > Kijun(26) -> long; bulut tabanının altına inip Tenkan < Kijun ->
    short. Long çıkış kapanış bulut tabanının altında, short çıkış bulut tepesinin üstünde; 120 bar zaman çıkışı; stop
    giriş -/+ 2,5 x ATR(14), lehte iz süren (`atr_iz_suren_k` 2,5; kaynakta fiyat/bar içi stop)."""

    ad = "kapanis__ichimoku-bulut-kirilim-s0634"
    varsayilan_parametreler = {"tenkan": 9, "kijun": 26, "senkou_b": 52, "kaydirma": 26, "atr_n": 14, "atr_k": 2.5}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=2.5, atr_periyot=14, zaman_cikisi_mum=120)

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        ic = b2.ichimoku(m["yuksek"], m["dusuk"], int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]), int(p["kaydirma"]))
        ust, alt = ic["bulut_ust"], ic["bulut_alt"]
        long_ok = (k.shift(1) <= ust.shift(1)) & (k > ust) & (ic["tenkan"] > ic["kijun"])
        short_ok = (k.shift(1) >= alt.shift(1)) & (k < alt) & (ic["tenkan"] < ic["kijun"])
        r = _atr3(m, p)
        return _bitir(cerceve(m, long_ok, short_ok, k - r, k + r), k < alt, k > ust)


# ================================================================ X005:635
class Crsi2S0635(KancaDestek, _Taban):
    """HAM:X005:635 (1d, long): ConnorsRSI(2, 2, 100) < 10 VE kapanış > SMA(200) VE hacim > 1,5 x SMA(hacim, 20) -> long. Çıkış
    CRSI > 70 ya da kapanış < SMA(200) ya da 5 gün (zaman çıkışı) ya da zirveden %5 geri çekilme (kanca: giriş sonrası en yüksek HIGH'ın %5 altı).
    Stop giriş kapanışının %8 altı. CRSI = `dis._gosterge_d10a.connors_rsi` (RSI + seri RSI + 100 günlük yüzdelik sıra)/3.
    Fiyat/piyasa değeri tarama filtreleri hisse evrenine özgü, uygulanmadı."""

    ad = "kapanis__crsi2-s0635"
    varsayilan_parametreler = {"rsi_n": 2, "seri_n": 2, "sira_n": 100, "giris": 10.0, "cikis": 70.0, "trend_sma": 200,
                               "hacim_n": 20, "hacim_k": 1.5, "stop_yuzde": 0.08}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=5)

    def pozisyon_cikisi(self, d: PozisyonDurumu) -> bool:
        return tepe_geri_cekilme(d, 5.0)

    def sinyaller(self, m):
        p = self.parametreler
        k, v = m["kapanis"], m["hacim"]
        crsi = _connors_rsi(k, int(p["rsi_n"]), int(p["seri_n"]), int(p["sira_n"]))
        sma = g.sma(k, int(p["trend_sma"]))
        gir = (crsi < float(p["giris"])) & (k > sma) & (v > float(p["hacim_k"]) * g.sma(v, int(p["hacim_n"])))
        sl = float(p["stop_yuzde"])
        return _bitir(cerceve(m, gir, False, k * (1 - sl), k * (1 + sl)), (crsi > float(p["cikis"])) | (k < sma))


# ================================================================ X005:638
class Rsi2Esik5Sma10S0638(_Taban):
    """HAM:X005:638 (1d, long): kapanış > SMA(200) VE RSI(2) <= 5 -> long; çıkış kapanış > SMA(10) ya da 20 işlem günü sonunda;
    stop giriş - 2,5 x ATR(14) (kaynak stopu)."""

    ad = "kapanis__rsi2-5-sma10-s0638"
    varsayilan_parametreler = {"rsi_n": 2, "esik": 5.0, "trend_ma": 200, "cikis_sma": 10, "atr_n": 14, "atr_k": 2.5}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=20)

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        gir = (k > g.sma(k, int(p["trend_ma"]))) & (g.rsi(k, int(p["rsi_n"])) <= float(p["esik"]))
        r = _atr3(m, p)
        return _bitir(cerceve(m, gir, False, k - r, k + r), k > g.sma(k, int(p["cikis_sma"])))


# ================================================================ X005:639
class Weinstein40HaftaS0639(_Taban):
    """HAM:X005:639 (1w; tamamlanmış haftalık barlar, 1d mumlarla, long): geçen hafta kapanış <= SMA(40 hafta) ve bu hafta kapanış > SMA(40) ->
    long; haftalık kapanış < SMA(40) -> çık. Haftalık değerler `htf.ust_zaman('1w')` ile kapanmış haftadan, karar yeni haftanın ilk günü.
    Stop yok -> ATR(14)x3 (günlük; ayrı iz stop değil, uyarlama). Hisse kesitsel sıralaması/hacim önceliği uygulanmadı (tek varlık SMA40)."""

    ad = "kapanis__weinstein40-s0639"
    varsayilan_parametreler = {"sma_hafta": 40, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        n = int(p["sma_hafta"])

        def fonk(u):
            kw = u["kapanis"]
            sma = g.sma(kw, n)
            return pd.DataFrame({"kw": kw, "sma": sma, "yukari": yukari(kw, sma).astype(float)})

        w, yeni = hafta_degerleri(m, fonk)
        k = m["kapanis"]
        r = _atr3(m, p)
        return _bitir(cerceve(m, yeni & (w["yukari"] == 1.0), False, k - r, k + r), yeni & (w["kw"] < w["sma"]))


# ================================================================ X005:640
class Macd525UzaklikS0640(_Taban):
    """HAM:X005:640 (1d, long): MACD(5,25,9) çizgisi sinyali yukarı keser VE son 20 günde (bugün dahil) 이격도 = kapanış / SMA(15)
    x 100 en az bir kez <= 85 olmuşsa long; çıkış MACD ölü kesişimi ya da 30 işlem günü. Stop yok -> ATR(14)x3 (uyarlama)."""

    ad = "kapanis__macd525-uzaklik-s0640"
    varsayilan_parametreler = {"hizli": 5, "yavas": 25, "sinyal": 9, "disp_n": 15, "disp_esik": 85.0, "disp_geri": 20, **_ATR}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=30)

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        mc = g.macd(k, int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))
        disp = k / g.sma(k, int(p["disp_n"])) * 100.0
        geri = int(p["disp_geri"])
        dusuk_oldu = disp.rolling(geri, min_periods=geri).min() <= float(p["disp_esik"])
        r = _atr3(m, p)
        return _bitir(cerceve(m, yukari(mc["macd"], mc["sinyal"]) & dusuk_oldu, False, k - r, k + r),
                      asagi(mc["macd"], mc["sinyal"]))


# ================================================================ X005:649
class KeltnerDurumS0649(_Taban):
    """HAM:X005:649 (1d, iki yön): kapanış < EMA(20) - 2 x ATR(14) ise ertesi gün long; kapanış > EMA(20) + 2 x ATR(14) ise
    ertesi gün short; kapanış bant içine döndüğü günün ertesinde pozisyon sıfırlanır (durum bazlı). Stop yok -> ATR(14)x3."""

    ad = "kapanis__keltner-durum-s0649"
    varsayilan_parametreler = {"ema": 20, "bant_atr_n": 14, "bant_k": 2.0, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        orta = g.ema(k, int(p["ema"]))
        band = float(p["bant_k"]) * g.atr(m["yuksek"], m["dusuk"], k, int(p["bant_atr_n"]))
        alt, ust = orta - band, orta + band
        r = _atr3(m, p)
        return _bitir(cerceve(m, k < alt, k > ust, k - r, k + r), k >= alt, k <= ust)


# ================================================================ X005:651
class DonchianYuksekDusukS0651(_Taban):
    """HAM:X005:651 (1d, long): kapanış ya da gün düşüğü 20 günlük en düşük seviyeye (düşüklerin 20 günlük minimumu, bugün dahil)
    eşit/altındaysa ertesi açılışta al; kapanış ya da gün yükseği 20 günlük en yüksek seviyeye (yüksek kanalı) dokunursa ertesi
    açılışta sat. Stop yok -> ATR(14)x3 (uyarlama)."""

    ad = "kapanis__donchian-yuksek-dusuk-s0651"
    varsayilan_parametreler = {"alt_n": 20, "ust_n": 20, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k, h, d = m["kapanis"], m["yuksek"], m["dusuk"]
        an, un = int(p["alt_n"]), int(p["ust_n"])
        alt = d.rolling(an, min_periods=an).min()
        ust = h.rolling(un, min_periods=un).max()
        r = _atr3(m, p)
        return _bitir(cerceve(m, (d <= alt) | (k <= alt), False, k - r, k + r), (h >= ust) | (k >= ust))


# ================================================================ X005:653
class SdDonusS0653(_Taban):
    """HAM:X005:653 (1d, iki yön): SD = std(günlük kapanış farkı, 756 gün, ddof=0); konum = (kapanış - SMA8) / SD. Long: dünkü konum
    < -1,5 ve bugün >= -1,5; short: dünkü > +1,5 ve bugün <= +1,5. Çıkış: kapanış SMA8'e ulaşınca (long: kapanış >= SMA8, short:
    <=). Stop: giriş anındaki SMA8 -/+ 2,5 x SD (kaynak stopu; mesafe >= %50 ise ATR(14)x3).
    Uyarlama: hedef (SMA8) kapanışla ve güncel SMA8 ile sınanır (giriş anında sabitlenmez; kaynak notu: yorum)."""

    ad = "kapanis__sd-donus-s0653"
    varsayilan_parametreler = {"sma_n": 8, "sd_n": 756, "giris": 1.5, "stop_sd": 2.5, **_ATR}

    def sinyaller(self, m):
        p = self.parametreler
        k = m["kapanis"]
        sma = g.sma(k, int(p["sma_n"]))
        sn = int(p["sd_n"])
        sd = k.diff().rolling(sn, min_periods=sn).std(ddof=0).where(lambda x: x > 0)
        konum = (k - sma) / sd
        e = float(p["giris"])
        long_ok = (konum.shift(1) < -e) & (konum >= -e)
        short_ok = (konum.shift(1) > e) & (konum <= e)
        r = _atr3(m, p)
        stop_l = _stop_sinirla(k, sma - float(p["stop_sd"]) * sd, r, 1)
        stop_s = _stop_sinirla(k, sma + float(p["stop_sd"]) * sd, r, -1)
        return _bitir(cerceve(m, long_ok, short_ok, stop_l, stop_s), k >= sma, k <= sma)


# ================================================================ X005:655
class YillikZirveKirilimS0655(ParametreliCikis):
    """HAM:X005:655 (1w; haftalık barlar, 1d mumlarla, long): haftalık kapanış > önceki 52 haftanın en yüksek kapanışı -> yeni haftanın ilk
    gününde sinyal (haftalık kapanış bilinir), dolum sonraki açılış (pozisyon yokken: motor). Çıkış: hedef giriş fiyatının 4 katı (+%300;
    kapanış bazlı: `azalan_roi = ((0, 300),)`), haftalık kapanış önceki 24 haftanın en düşük dibinin altına inerse (iz süren çıkış,
    `cikis_long`), stop giriş fiyatının %30 altı. Haftalık değerler `htf.ust_zaman('1w')` ile kapanmış haftadan.
    YAKLAŞIK: kaynak stopu kapanış bazlı (haftalık kapanış giriş x 0,70); burada sinyal kapanışından %30 bar içi sert stop (motor
    stopu sabit); hedef kapanış bazlı birebir (azalan_roi)."""

    ad = "kapanis__52h-zirve-kirilim-s0655"
    varsayilan_parametreler = {"zirve_hafta": 52, "dip_hafta": 24, "stop_yuzde": 0.30, "hedef": 3.0}

    @staticmethod
    def _cikis(p: dict) -> CikisAyarlari:
        return CikisAyarlari(azalan_roi=((0, round(float(p["hedef"]) * 100.0, 6)),))

    def sinyaller(self, m):
        p = self.parametreler
        zn, dn = int(p["zirve_hafta"]), int(p["dip_hafta"])

        def fonk(u):
            kw = u["kapanis"]
            return pd.DataFrame({"kw": kw, "zirve": kw.shift(1).rolling(zn, min_periods=zn).max(),
                                 "dip": u["dusuk"].shift(1).rolling(dn, min_periods=dn).min()})

        w, yeni = hafta_degerleri(m, fonk)
        k = m["kapanis"]
        sl = float(p["stop_yuzde"])
        return _bitir(cerceve(m, yeni & (w["kw"] > w["zirve"]), False, k * (1 - sl), k * (1 + sl)), yeni & (w["kw"] < w["dip"]))


SINIFLAR = [Yuksek20TemasS0561, CmcWinnerS0567, TdSayimGunSonusuzS0570, EmaOranBandiS0571, Cci72Rsi36S0572, Rsi4Ema100S0574,
            VwapDipS0576, DonchianAgirlikliBbS0577, SlowPotatoS0578, IkiDipSma20S0582, MmmS0583, Rsi2UcGunDusenS0586,
            KumoIzS0600, AylikSma10Rsi2S0606, Ma5DusenGunlerS0608, PazartesiDusSalitS0611, TenkanKijunDonS0621, IcuMaS0625,
            VmHmaS0626, ValueAreaSkorS0630, AralikKanalS0631, BbDonusH4S0633, IchimokuBulutKirilimS0634, Crsi2S0635,
            Rsi2Esik5Sma10S0638, Weinstein40HaftaS0639, Macd525UzaklikS0640, KeltnerDurumS0649, DonchianYuksekDusukS0651,
            SdDonusS0653, YillikZirveKirilimS0655]


def _v(kaynak: str, no: int, sinif, tf: str, **parametre) -> dict:
    return {"kimlik": f"HAM:X005:{kaynak}#v{no}", "sinif": sinif.ad,
            "parametreler": {**sinif.varsayilan_parametreler, **parametre}, "tf": tf}


VARYANTLAR = [
    _v("561", 1, Yuksek20TemasS0561, "1d"),
    _v("567", 1, CmcWinnerS0567, "15m"),
    _v("570", 1, TdSayimGunSonusuzS0570, "1h"),
    _v("571", 1, EmaOranBandiS0571, "5m"),
    _v("572", 1, Cci72Rsi36S0572, "15m"),
    _v("574", 1, Rsi4Ema100S0574, "1h"),
    _v("576", 1, VwapDipS0576, "5m"),
    _v("577", 1, DonchianAgirlikliBbS0577, "5m"),
    _v("578", 1, SlowPotatoS0578, "5m"),
    _v("582", 1, IkiDipSma20S0582, "6h"),
    _v("583", 1, MmmS0583, "1h"),
    _v("586", 1, Rsi2UcGunDusenS0586, "1d"),
    # X005:594 (K6_STANDART: MA=SMA) = arşivdeki kod_g8_kod_3.Rsi2Sma5S0253 ile aynı kural yapısı (eşik 10); sınıf onun adıyla.
    {"kimlik": "HAM:X005:594#v1", "sinif": "kapanis__rsi2-sma5-s0253",
     "parametreler": {"rsi_n": 2, "rsi_ust": 10.0, "trend_n": 200, "kisa_n": 5, "atr_n": 14, "atr_k": 3.0}, "tf": "1d"},
    _v("600", 1, KumoIzS0600, "1d"),
    _v("606", 1, AylikSma10Rsi2S0606, "1d"),
    _v("608", 1, Ma5DusenGunlerS0608, "1d", ma_uzun=200),
    _v("608", 2, Ma5DusenGunlerS0608, "1d", ma_uzun=220),
    _v("611", 1, PazartesiDusSalitS0611, "1d"),
    _v("621", 1, TenkanKijunDonS0621, "1h"),
    _v("625", 1, IcuMaS0625, "1d"),
    _v("626", 1, VmHmaS0626, "1d"),
    _v("630", 1, ValueAreaSkorS0630, "1h"),
    _v("631", 1, AralikKanalS0631, "5m"),
    _v("633", 1, BbDonusH4S0633, "1h"),
    _v("634", 1, IchimokuBulutKirilimS0634, "1h"),
    _v("635", 1, Crsi2S0635, "1d"),
    _v("638", 1, Rsi2Esik5Sma10S0638, "1d"),
    _v("639", 1, Weinstein40HaftaS0639, "1d"),
    _v("640", 1, Macd525UzaklikS0640, "1d"),
    _v("649", 1, KeltnerDurumS0649, "1d"),
    _v("651", 1, DonchianYuksekDusukS0651, "1d"),
    _v("653", 1, SdDonusS0653, "1d"),
    dict(_v("655", 1, YillikZirveKirilimS0655, "1d"), yaklasik=True),
]

KODLANAMADI = [
    # 573, 584, 629, 643, 644: kod_g8_modul.py (pozisyon bilinçli modül/kanca).
    {"kimlik": "HAM:X005:580",
     "neden": "portföy ağırlık stratejisi: OLMAR hedef ağırlık simpleksi (tüm sembollerin fiyat/SMA20 vektörü, simpleks "
              "izdüşümü, günlük yeniden dengeleme) tek varlıklı Strateji.sinyaller sözleşmesine sığmaz; portföy sınıfı "
              "(motor/portfoy/stratejiler, PfTemel) arayüzü bu talimatın kapsamında değil"},
    {"kimlik": "HAM:X005:585",
     "neden": "portföy ağırlık stratejisi: ay sonu kesitsel en düşük IBS'li 1 varlığa %100 ağırlık (tüm sembolleri sıralama, "
              "aylık yeniden dengeleme) tek varlıklı sinyal sözleşmesine sığmaz; portföy sınıfı arayüzü talimat kapsamında değil"},
]
