"""swing__uc-cubuklu-net-hat: Stowell/Bulkowski "üç çubuklu net çizgi" ile trend değişimi kırılımı.

Yorum (kart metni belirsiz, burada şöyle kodlandı): fraktal pivot (k=pivot_k, nedensel) ile en son ONAYLI dip, ondan sonra
oluşan düşüş bacağının tabanıdır (bar 1). Net çizgi (yukarı dönüş) = bar 1 ve solundaki cubuk_n-1 çubuğun en yükseği
(üç çubuklu: bar1 + 2 çubuk solda). Aşağı dönüş ayna: son onaylı TEPE ve çevresindeki cubuk_n çubuğun en düşüğü.
Long: son onaylı pivot bir DİP (son dip, son tepeden sonra), kapanış net çizgiyi aşağıdan yukarı keser, pivot onayından
beri en çok max_bekle mum geçti, ve (sma_filtre>0 ise) kapanış > SMA(sma_filtre) (kart: 50 günlük SMA filtresi). Short ayna.
Stop: bar 1'in (pivot dibi / tepesi) dışı -/+ stop_tampon_atr*ATR (kart: son düşüğün 1 kuruş altı), risk <= stop_max_atr ATR.
Çıkış: karşı yönlü net çizgi kırılımı (`cikis`, yön-bağımsız: her iki yönün kırılımı). Hedef yok (NaN; hedef_r>0 ise R katı).
Kaynak kartlar: daytrade__uc-cubuklu-net-hat-trend-degisimi__bulkowski (1D, 50g SMA filtresi, ertesi açılışta giriş, karşı yön çıkış);
daytrade__guppy-cbl-kademeli-giris__bulkowski (CBL geri sayım çizgisi + kademeli giriş: KODLANMADI, ayrı mekanik).
Varsayımlar: "üç çubuk" sayımı ve eşit çubukların yok sayılması fraktal pivot + pencere maksimumu ile yaklaşıldı; Bulkowski yazar tek başına
sistem olmadığını söyler. Haftalık/aylık üst filtre (kart önerisi) kodlanmadı.
Negatif kanıt: aile kaydında yok; tek yazar; arşivde tek kurallı trend/kırılım sistemleri zayıf (arsiv/OZET.md §3).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.pivotlar import fraktal_pivotlar
from motor.strateji.temel import Strateji


class UcCubukluNetHat(Strateji):
    ad = "swing__uc-cubuklu-net-hat"
    stil = "swing"
    varsayilan_parametreler = {
        "pivot_k": 3, "cubuk_n": 3, "max_bekle": 20, "sma_filtre": 50,
        "stop_tampon_atr": 0.1, "stop_max_atr": 4.0, "hedef_r": 0.0, "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "pivot_k": [2, 3, 5],
        "cubuk_n": [3, 4],
        "sma_filtre": [0, 50],
        "max_bekle": [10, 30],
    }

    def cikis_var_mi(self) -> bool:
        return True   # karşı yönlü net çizgi kırılımı

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = len(k)
        atr = g.atr(y, d, k, p["atr_periyot"])
        pv = fraktal_pivotlar(y, d, int(p["pivot_k"]))
        cn = int(p["cubuk_n"])
        ust_net = y.rolling(cn, min_periods=cn).max().to_numpy()     # t'de biten cn çubuğun zirvesi
        alt_net = d.rolling(cn, min_periods=cn).min().to_numpy()

        def al(dizi, idx):
            out = np.full(n, np.nan)
            ok = ~np.isnan(idx)
            out[ok] = dizi[idx[ok].astype(int)]
            return out

        di, ti = pv["son_dip_idx"].to_numpy(), pv["son_tepe_idx"].to_numpy()
        net_yukari = pd.Series(al(ust_net, di), index=k.index)       # son dipte biten pencerenin zirvesi
        net_asagi = pd.Series(al(alt_net, ti), index=k.index)        # son tepede biten pencerenin dibi
        pos = np.arange(n)
        with np.errstate(invalid="ignore"):
            dip_son = (di > np.nan_to_num(ti, nan=-1.0))
            tepe_son = (ti > np.nan_to_num(di, nan=-1.0))
            dip_taze = (pos - pv["son_dip_onay_idx"].to_numpy()) <= p["max_bekle"]
            tepe_taze = (pos - pv["son_tepe_onay_idx"].to_numpy()) <= p["max_bekle"]
        long_ok = b.yukari_kesis(k, net_yukari) & dip_son & dip_taze
        short_ok = b.asagi_kesis(k, net_asagi) & tepe_son & tepe_taze & bool(p["short"])
        if p["sma_filtre"]:
            sma = g.sma(k, int(p["sma_filtre"]))
            long_ok, short_ok = long_ok & (k > sma), short_ok & (k < sma)
        gecerli = atr.notna()
        long_ok, short_ok = long_ok & gecerli, short_ok & gecerli
        tampon = p["stop_tampon_atr"] * atr
        stop_l = np.maximum(pv["son_dip_fiyat"] - tampon, k - p["stop_max_atr"] * atr)
        stop_s = np.minimum(pv["son_tepe_fiyat"] + tampon, k + p["stop_max_atr"] * atr)
        h_l, h_s = b.hedef_r_ile(k, stop_l, stop_s, p["hedef_r"])
        cikis = ((b.yukari_kesis(k, net_yukari) & dip_son) | (b.asagi_kesis(k, net_asagi) & tepe_son)) & gecerli
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis)
