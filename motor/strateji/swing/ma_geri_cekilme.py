"""swing__ma-geri-cekilme: trendde hareketli ortalamaya geri çekilme + sıçrama mumu.

Kaynak kartlar: ladha, sharpe, penn, make, velez, graham, kratter (x2).
Ortak çekirdek: trend var (uzun MA'nın üstünde; MA hizalı) -> fiyat 10/20/50 MA bölgesine çekilir ->
dönüş/sıçrama mumu -> trend yönünde giriş. Short: ayna (sharpe, velez, graham).
Çıkış (ladha, kratter): MA'nın karşı tarafında kapanış -> `cikis`.
Kanonik kural ile çelişki: "ADX>=30" yalnızca kratter kartında; zorunlu değil, `adx_esik` ile isteğe bağlı (0=kapalı).
"Hacim düşük" ve "ölü kedi" filtreleri kodlanmadı.

Varsayımlar (kitapta olmayan): temas = son `geri_n` mumda (şu an dahil) dip <= MA + temas_atr*ATR;
sıçrama mumu = yönde kapanan mum (kapanış>açılış) ve kapanış > MA ve kapanış > önceki mumun zirvesi;
trend = kapanış > trend_ma (SMA) ve MA > trend_ma; stop = geri çekilme dibi (son geri_n mum) - stop_tampon_atr*ATR
(kartlar: "giriş mumu dibinin/MA'nın biraz altı, backtest 1-2 ATR"); hedef = hedef_r * R (0 ise NaN; kitapta 2-3R).

d11j EK MOD (varsayılan "klasik" = eski davranış; ızgaraya girmez; kaynak aile uc-ema-dizilim-geri-cekilme-fraktal, geraked/metatrader5 3MAF.mq5):
mod="uclu_hiza": EMA(hiza1=60) > EMA(hiza2=350) > EMA(hiza3=600) hizası; sinyal mumunun düşüğü EMA(hiza3)'ün üstünde ve EMA(hiza1)'in altında
(EMA bandına geri çekilme); 2 mum önce aşağı Williams fraktalı (5 mumluk dip; sağ 2 mum onayı = sinyal anında bilinir) -> long. Stop: mum düşüğü EMA(hiza2)'nin
üstündeyse EMA(hiza2), değilse EMA(hiza3); hedef = hedef_r*R (kaynak 1.5). Short ayna (hiza ters, yüksek bandın içinde, yukarı fraktal). Kaynaktaki
Grid (kademe ekleme, martingale benzeri), IgnoreSL ve SL<100 puan filtresi KODLANMADI. Çıkış: yalnız stop/hedef (bu modda `cikis` üretilmez); hedef_r
verilmezse yalnız stop kalır -> ayar kaydında hedef_r=1.5 verilmelidir. trend_ma/adx_esik/ma_periyot bu modda kullanılmaz.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.swing._ortak import sinyal_cercevesi
from motor.strateji.temel import Strateji


class MaGeriCekilme(Strateji):
    ad = "swing__ma-geri-cekilme"
    stil = "swing"
    varsayilan_parametreler = {
        "ma_periyot": 20, "ma_tipi": "ema",
        "trend_ma": 200,          # SMA; 0: trend filtresi yok
        "geri_n": 5, "temas_atr": 0.0,
        "adx_esik": 0.0, "adx_periyot": 14,    # 0: ADX filtresi kapalı
        "atr_periyot": 14, "stop_tampon_atr": 0.5,
        "hedef_r": 0.0,           # 0: hedef yok (NaN)
        "short": True,
        "mod": "klasik", "hiza1": 60, "hiza2": 350, "hiza3": 600,
    }
    parametre_izgarasi = {
        "ma_periyot": [10, 20, 50],
        "stop_tampon_atr": [0.25, 0.5, 1.0],
        "hedef_r": [0.0, 2.0, 3.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        if p["mod"] == "uclu_hiza":
            return self._uclu_hiza(mumlar)
        if p["mod"] != "klasik":
            raise ValueError(f"Bilinmeyen mod: {p['mod']}")
        ma = (g.ema if p["ma_tipi"] == "ema" else g.sma)(k, p["ma_periyot"])
        atr = g.atr(y, d, k, p["atr_periyot"])
        n = p["geri_n"]
        tol = p["temas_atr"] * atr

        temas_long = (d <= ma + tol).rolling(n, min_periods=n).max().astype(bool)
        temas_short = (y >= ma - tol).rolling(n, min_periods=n).max().astype(bool)
        long_ok = temas_long & (k > ma) & (k > a) & (k > y.shift(1))
        short_ok = temas_short & (k < ma) & (k < a) & (k < d.shift(1)) & bool(p["short"])
        if p["trend_ma"]:
            tr = g.sma(k, p["trend_ma"])
            long_ok &= (k > tr) & (ma > tr)
            short_ok &= (k < tr) & (ma < tr)
        if p["adx_esik"]:
            ax = g.adx(y, d, k, p["adx_periyot"])["adx"]
            yuk = (ax > p["adx_esik"]) & (ax > ax.shift(1))
            long_ok &= yuk
            short_ok &= yuk
        gecerli = atr.notna() & ma.notna()
        long_ok &= gecerli
        short_ok &= gecerli

        stop_l = d.rolling(n, min_periods=n).min() - p["stop_tampon_atr"] * atr
        stop_s = y.rolling(n, min_periods=n).max() + p["stop_tampon_atr"] * atr
        if p["hedef_r"]:
            h_l = k + p["hedef_r"] * (k - stop_l)
            h_s = k - p["hedef_r"] * (stop_s - k)
        else:
            h_l = h_s = None
        cikis = (((k < ma) & (k.shift(1) >= ma.shift(1))) |
                 ((k > ma) & (k.shift(1) <= ma.shift(1)))) & gecerli
        return sinyal_cercevesi(mumlar.index, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis)

    def _uclu_hiza(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        e1, e2, e3 = (g.ema(k, int(p[a])) for a in ("hiza1", "hiza2", "hiza3"))
        atr = g.atr(y, d, k, p["atr_periyot"])
        dip2 = d.shift(2)
        tepe2 = y.shift(2)
        fr_dip = (dip2 < d.shift(3)) & (dip2 < d.shift(4)) & (dip2 < d.shift(1)) & (dip2 < d)
        fr_tepe = (tepe2 > y.shift(3)) & (tepe2 > y.shift(4)) & (tepe2 > y.shift(1)) & (tepe2 > y)
        gecerli = atr.notna() & e3.notna()
        long_ok = (e1 > e2) & (e2 > e3) & (d > e3) & (d < e1) & fr_dip & gecerli
        short_ok = (e1 < e2) & (e2 < e3) & (y < e3) & (y > e1) & fr_tepe & gecerli & bool(p["short"])
        stop_l = pd.Series(np.where(d > e2, e2, e3), index=k.index)
        stop_s = pd.Series(np.where(y < e2, e2, e3), index=k.index)
        if p["hedef_r"]:
            h_l = k + p["hedef_r"] * (k - stop_l)
            h_s = k - p["hedef_r"] * (stop_s - k)
        else:
            h_l = h_s = None
        return sinyal_cercevesi(mumlar.index, long_ok, short_ok, stop_l, stop_s, h_l, h_s)

    def cikis_var_mi(self) -> bool:
        """MA'nın karşı tarafında kapanış `cikis` üretir (her zaman)."""
        return True
