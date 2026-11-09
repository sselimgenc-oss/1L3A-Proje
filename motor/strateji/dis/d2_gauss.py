"""D2 / Gauss kanalı aileleri (TradingView, TRADLEWARE ve RSI-Gauss-Velocity).

Üç strateji: `dis__gauss-stoch-btc`, `dis__gauss-stoch-eth`, `dis__rsi-gauss-velocity`.
Gauss filtresi / kanalı: bkz. `_gosterge_d2.gauss_kanal` (nedensel; Pine nz() gibi 0'dan başlar, ilk 3*per mum
ısınma sayılır ve sinyal verilmez).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis import _gosterge_d2 as gd
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.temel import Strateji


def _isinma(n: int, esik: int) -> pd.Series:
    return pd.Series(np.arange(n) >= esik)


class _GaussKanalStoch(Strateji):
    """Ortak çekirdek: Gauss kanalı kırılımı + StochRSI aşırı bölge süzgeci (4h).

    Long: filtre yükseliyor (filt > önceki), kapanış üst bandın üstünde ve StochRSI %K > k_ust veya < k_alt
    (+ ETH'de kapanış > SMA(sma_rejim) ve yeşil mum). Çıkış: kapanış üst bandın altına iner ya da filtre düşer.
    Stop: sinyal mumunun alt bandı (orijinalde her mum güncellenen alt band stopu; burada sinyal anındaki değer sabit).
    short=True: ayna (filtre düşüyor, kapanış alt bandın altında, %K < 100-k_ust veya > 100-k_alt, SMA altı,
    kırmızı mum; stop üst band; çıkış: kapanış alt bandın üstüne çıkar ya da filtre yükselir). Orijinal yalnız long.
    """
    stil = "swing"
    varsayilan_parametreler = {
        "per": 144, "kutup": 4, "carpan": 1.414, "stoch_uzunluk": 14, "rsi_uzunluk": 14,
        "k_ust": 80.0, "k_alt": 15.0, "sma_rejim": 0, "yesil_mum": False, "short": False,
    }
    parametre_izgarasi = {"per": [89, 144], "carpan": [1.414, 1.5, 2.0], "k_alt": [15.0, 25.0]}

    def cikis_var_mi(self) -> bool:
        return True   # bant altı / filtre dönüşü

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k, a = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], mumlar["acilis"]
        kn = gd.gauss_kanal(y, d, k, p["per"], p["kutup"], p["carpan"])
        filt, ust, alt = kn["filt"], kn["ust"], kn["alt"]
        sr = gd.stoch_rsi(k, p["rsi_uzunluk"], p["stoch_uzunluk"], 3, 3)["k"]
        hazir = _isinma(len(mumlar), 3 * p["per"]).set_axis(mumlar.index) & filt.notna()
        yukari, asagi = filt > filt.shift(1), filt < filt.shift(1)
        long_ok = hazir & yukari & (k > ust) & ((sr > p["k_ust"]) | (sr < p["k_alt"]))
        short_ok = hazir & asagi & (k < alt) & ((sr < 100 - p["k_ust"]) | (sr > 100 - p["k_alt"])) & bool(p["short"])
        if p["sma_rejim"]:
            sma = g.sma(k, p["sma_rejim"])
            long_ok &= k > sma
            short_ok &= k < sma
        if p["yesil_mum"]:
            long_ok &= k > a
            short_ok &= k < a
        sig = cerceve(mumlar, long_ok, short_ok, alt, ust)
        return gd.yonlu_cerceve(sig, (k < ust) | asagi, (k > alt) | yukari)


class GaussStochBtc(_GaussKanalStoch):
    """TRADLEWARE-Gaussian Channel + StochRSI BTC (4h swing, long).

    Kaynak: arsiv/strateji-sg/tv/pine/d1JxXpid.pine. Kural/uyarlama: sınıf docstring'i (çekirdek). Orijinal
    parametreler: 4 kutuplu Gauss, per=144, çarpan 1.414, StochRSI 14/14/3/3, eşikler 80 / 15 (BTC'de yükseltmek kötü),
    yeşil mum süzgeci kapalı, tamponsuz kırılım; alt bant stop; %100 sermaye (motor bunu risk bazlı boyutlar).
    TF belirtilmemiş, başlık BTC -> 4h seçildi. Tarih aralığı (2018-) girdileri kaldırıldı.
    Eski proje sonucu: kaldı: PF 1.80, Sharpe 1.42 (gauss_btc, 4h).
    """
    ad = "dis__gauss-stoch-btc"


class GaussStochEth(_GaussKanalStoch):
    """TRADLEWARE-Gaussian Channel ETH (4h swing, long).

    Kaynak: arsiv/strateji-sg/tv/pine/egTb7TgJ.pine. BTC sürümünden farkı: daha hızlı kanal (per=89, çarpan 1.5),
    alt eşik 25 (22-28 platosu), SMA200 (grafik TF'sinin 200 mumu; Pine yorumu "200 gün" ama kod chart TF kullanır)
    üstü boğa kapısı ve yeşil mum zorunluluğu. Diğer her şey çekirdekle aynı. TF belirtilmemiş, başlık ETH -> 4h.
    Eski proje sonucu: kaldı: PF 1.75, Sharpe 1.55 (gauss_eth, 4h).
    """
    ad = "dis__gauss-stoch-eth"
    varsayilan_parametreler = {**_GaussKanalStoch.varsayilan_parametreler,
                               "per": 89, "carpan": 1.5, "k_alt": 25.0, "sma_rejim": 200, "yesil_mum": True}
    parametre_izgarasi = {"per": [89, 144], "carpan": [1.5, 1.414, 2.0], "k_alt": [20.0, 25.0, 28.0]}


class RsiGaussVelocity(Strateji):
    """RSI-Gauss-Velocity-Strategy-WiP (1d swing, long).

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/T5kd1bJ2.pine.
    Kural: Gauss filtresi yükseliyor, kapanış üst bandın (filt + süzülmüş TR*1.414) üstünde ve StochRSI %K > %D ise long.
    Çıkış: kapanış üst bandı aşağı keser VEYA (filtre eğimi son 20 mum ortalamasından 1 sapma aşağıdaysa "tükenme" VE
    pozisyon kârda VE kapanış üst bandın altında/önceki üst bandın altında).
    Uyarlama: "pozisyon kârda" için sinyalde sanal bir pozisyon (sinyal kapanışı = giriş) izlenir; motorun gerçek
    girişinden bir mum farklı olabilir. Orijinalde stop yok -> ATR stop eklendi (stop_atr=3.0). short=True ayna kural
    (filtre düşüyor, kapanış alt bandın altı, %K < %D; çıkış alt bandı yukarı keser veya tükenme+kârda). Orijinal
    yalnız long; 2014 başlangıç tarihi girdisi kaldırıldı. TF belirtilmemiş -> 1d.
    Eski proje sonucu: kaldı: PF 3.58, Sharpe 1.19 (rsi_gauss, 1d).
    """
    ad = "dis__rsi-gauss-velocity"
    stil = "swing"
    varsayilan_parametreler = {"per": 144, "kutup": 4, "carpan": 1.414, "egim_pencere": 20,
                               "stop_atr": 3.0, "atr_periyot": 14, "short": False}
    parametre_izgarasi = {"per": [89, 144], "carpan": [1.0, 1.414, 2.0], "stop_atr": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        kn = gd.gauss_kanal(y, d, k, p["per"], p["kutup"], p["carpan"])
        filt, ust, alt = kn["filt"], kn["ust"], kn["alt"]
        sr = gd.stoch_rsi(k, 14, 14, 3, 3)
        egim = filt - filt.shift(1)
        w = p["egim_pencere"]
        tukenme = egim < (g.sma(egim, w) - gd.pine_stdev(egim, w))
        hazir = (_isinma(len(mumlar), 3 * p["per"]).set_axis(mumlar.index)) & filt.notna() & tukenme.notna()
        long_ok = (hazir & (egim > 0) & (k > ust) & (sr["k"] > sr["d"])).to_numpy()
        short_ok = (hazir & (egim < 0) & (k < alt) & (sr["k"] < sr["d"]) & bool(p["short"])).to_numpy()
        c, u, a_, t, eg = k.to_numpy(), ust.to_numpy(), alt.to_numpy(), tukenme.to_numpy(), egim.to_numpy()
        n = len(c)
        cikis_l = np.zeros(n, dtype=bool)
        cikis_s = np.zeros(n, dtype=bool)
        poz, giris = 0, np.nan
        for i in range(n):
            if poz == 1:
                kar = c[i] > giris
                alt_ = i > 0 and (c[i] < u[i] or c[i - 1] < u[i - 1])
                cikis_l[i] = (i > 0 and c[i] < u[i] and c[i - 1] >= u[i - 1]) or (t[i] and kar and alt_)
                if cikis_l[i]:
                    poz = 0
            elif poz == -1:
                kar = c[i] < giris
                ust_ = i > 0 and (c[i] > a_[i] or c[i - 1] > a_[i - 1])
                cikis_s[i] = (i > 0 and c[i] > a_[i] and c[i - 1] <= a_[i - 1]) or (t[i] and kar and ust_)
                if cikis_s[i]:
                    poz = 0
            if poz == 0:
                if long_ok[i]:
                    poz, giris = 1, c[i]
                elif short_ok[i]:
                    poz, giris = -1, c[i]
        a = g.atr(y, d, k, p["atr_periyot"])
        sig = cerceve(mumlar, long_ok, short_ok, k - p["stop_atr"] * a, k + p["stop_atr"] * a)
        return gd.yonlu_cerceve(sig, cikis_l, cikis_s)
