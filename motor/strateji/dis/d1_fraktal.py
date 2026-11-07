"""D1 grubu (dış TradingView): fraktal/pivot/yapı tabanlı stratejiler.

ChartArt fraktal kırılımı, Alligator+fraktal trend takibi, pivot ters stop-giriş, Swing-VWAP "Golden Trident" ve
Elliott 5 dalga. Pivotlar yalnız ONAY mumunda bilinir (nedensel).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis._gosterge_d1 import alligator_dis, kur, yuzdelik_sira
from motor.strateji.pivotlar import fraktal_pivotlar
from motor.strateji.temel import Strateji


def _son_olay_degeri(deger: pd.Series, olay: pd.Series, geri: int = 0) -> pd.Series:
    """Pine valuewhen(olay, deger, geri): olayın `geri`. önceki gerçekleşmesindeki değer (0 = en son)."""
    ev = deger[olay.fillna(False).astype(bool)]
    return ev.shift(geri).reindex(deger.index).ffill() if geri else ev.reindex(deger.index).ffill()


class FraktalKirilimChartArt(Strateji):
    """dis__fraktal-kirilim-chartart: son 3 fraktal tepe ortalaması yükselirken fiyat son fraktali kırarsa LONG.

    Kaynak: arsiv/strateji-sg/tv/pine/EjLwVtgp.pine (Fractal Breakout Strategy by ChartArt).
    Kural: fraktal tepe = 5 mumluk merkez tepe (high[2] diğer 4'ten yüksek). Fraktal fiyatı = o fraktalin ONAY mumundaki hl2
    (Pine'ın valuewhen(.., price, 1) davranışı korundu: önceki-bir gerçekleşme). Ortalama = son `ort_uzunluk` (3 veya 2) fraktal
    fiyatı; trend = ortalama bir önceki mumdan büyük; kırılım = bir önceki mumun hl2'si > son fraktal fiyatı (no-repainting
    seçeneği açık). Giriş: trend ve kırılım. Çıkış: `n_zaman` mum önce trend vardı ve şimdi yok.
    Uyarlama: orijinal yalnız long ve stopsuz -> ATR stop (stop_atr) eklendi. `short=True` ayna kurar (fraktal dipler, ortalama
    düşüyor, hl2[1] < son fraktal fiyatı). Varsayılan yalnız long.
    Eski sonuç: kaldı: PF 1.29, Sharpe 0.97 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/fractal_brk.json).
    """
    ad = "dis__fraktal-kirilim-chartart"
    stil = "swing"
    varsayilan_parametreler = {"n_zaman": 3, "ort_uzunluk": 3, "atr_periyot": 14, "stop_atr": 2.5, "short": False}
    parametre_izgarasi = {"n_zaman": [2, 3, 5], "ort_uzunluk": [2, 3], "stop_atr": [2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def _yon(self, fiyat, h, l, ust: bool):
        p = self.parametreler
        if ust:
            fr = (h.shift(2) > h.shift(3)) & (h.shift(2) > h.shift(4)) & (h.shift(2) > h.shift(1)) & (h.shift(2) > h)
        else:
            fr = (l.shift(2) < l.shift(3)) & (l.shift(2) < l.shift(4)) & (l.shift(2) < l.shift(1)) & (l.shift(2) < l)
        fp = _son_olay_degeri(fiyat, fr, geri=1)
        if int(p["ort_uzunluk"]) == 3:
            ort = (fp.shift(1) + fp.shift(2) + fp.shift(3)) / 3.0
        else:
            ort = (fp.shift(1) + fp.shift(2)) / 2.0
        trend = (ort > ort.shift(1)) if ust else (ort < ort.shift(1))
        kirilim = (fiyat.shift(1) > fp) if ust else (fiyat.shift(1) < fp)
        giris = trend & kirilim
        cikis = trend.shift(int(p["n_zaman"]), fill_value=False).astype(bool) & ~trend
        return giris, cikis

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        hl2 = (y + d) / 2.0
        gl, cl = self._yon(hl2, y, d, True)
        gs, cs = self._yon(hl2, y, d, False)
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        sd = p["stop_atr"] * atr
        return kur(mumlar, gl, gs & bool(p["short"]), k - sd, k + sd, cikis_l=cl, cikis_s=cs)


def _seviye_kesisi(seri: np.ndarray, yeni: np.ndarray, fiyat: np.ndarray, ust: bool):
    """Fraktal seviyesi: yeni onaylı pivot seviyeyi değiştirir; fiyat seviyeyi keserse seviye silinir (Skyrexio/Fractal Sky).
    Dönen: (seviye[i] (mum sonu), kesis[i]). Kesişim Pine ta.crossover: seri[i] > L[i-1] ve seri[i-1] <= L[i-2]."""
    n = len(seri)
    L = np.full(n, np.nan)
    kes = np.zeros(n, dtype=bool)
    for i in range(n):
        if i >= 2 and not np.isnan(L[i - 1]) and not np.isnan(L[i - 2]):
            if ust:
                kes[i] = seri[i] > L[i - 1] and seri[i - 1] <= L[i - 2]
            else:
                kes[i] = seri[i] < L[i - 1] and seri[i - 1] >= L[i - 2]
        if yeni[i]:
            L[i] = fiyat[i]
        elif kes[i]:
            L[i] = np.nan
        else:
            L[i] = L[i - 1] if i else np.nan
    return L, kes


class FraktalAlligatorSky(Strateji):
    """dis__fraktal-alligator-sky: Alligator dişi üstünde yukarı fraktal kırılımı (düşük oynaklıkta); stop %3 ya da aşağı fraktal.

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/IqUET4xO.pine (Fractal Breakout Trend Following Strategy).
    Kural: son onaylı yukarı fraktal tepe seviyesi Alligator dişinin (SMMA(hl2,8), 5 mum geri) ÜSTÜNDEYSE etkin; ATR(13)
    yüzdelik sırasının (52 mum) 5 mumluk ortalaması <= atr_esik (düşük oynaklık) iken fiyat seviyeyi yukarı kırarsa long. Çıkış:
    fiyat etkin (dişin altındaki) son aşağı fraktalin altına iner (Pine'daki dinamik stopun sinyal karşılığı) veya sabit %3 stop.
    Uyarlama: orijinal giriş fraktal seviyesinde "stop-al" emridir; burada kırılan mumun kapanışında sinyal, sonraki açılışta piyasa
    emri. Dinamik stop max(giriş*0.97, aşağı fraktal) motorda tek sabit stop olamadığından ikiye bölündü: sabit stop %3 + aşağı fraktal
    kırılımında `cikis`. Orijinal yalnız long; `short=True` ayna kurar (dişin altındaki aşağı fraktal kırılımı), varsayılan kapalı.
    Eski sonuç: kaldı: PF 0.94, Sharpe -0.52 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/fractal_sky.json).
    """
    ad = "dis__fraktal-alligator-sky"
    stil = "swing"
    varsayilan_parametreler = {"atr_n": 13, "atr_geri": 52, "atr_ort": 5, "atr_esik": 50.0, "stop_yuzde": 3.0,
                               "short": False}
    parametre_izgarasi = {"atr_esik": [30.0, 50.0, 70.0], "atr_ort": [3, 5, 8], "stop_yuzde": [2.0, 3.0, 5.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        pv = fraktal_pivotlar(y, d, 2)
        dis = alligator_dis(y, d)
        atr = g.atr(y, d, k, int(p["atr_n"]))
        norm = yuzdelik_sira(atr, int(p["atr_geri"]))
        ort = norm.rolling(int(p["atr_ort"]), min_periods=int(p["atr_ort"])).mean()
        sakin = (ort <= p["atr_esik"]).shift(1, fill_value=False)
        # yukarı fraktal seviyesi (long)
        Lu, ku = _seviye_kesisi(y.to_numpy(float), pv["yeni_tepe"].to_numpy(), pv["son_tepe_fiyat"].to_numpy(), True)
        Lu = pd.Series(Lu, index=k.index)
        etkin_u = (Lu >= dis).shift(1, fill_value=False) & Lu.shift(1).notna()
        long_ok = pd.Series(ku, index=k.index) & etkin_u & sakin
        # aşağı fraktal seviyesi (short)
        Ld, kd = _seviye_kesisi(d.to_numpy(float), pv["yeni_dip"].to_numpy(), pv["son_dip_fiyat"].to_numpy(), False)
        Ld = pd.Series(Ld, index=k.index)
        etkin_d = (Ld <= dis).shift(1, fill_value=False) & Ld.shift(1).notna()
        short_ok = pd.Series(kd, index=k.index) & etkin_d & sakin & bool(p["short"])
        # çıkış: etkin karşı fraktal kırılımı
        dip_etkin = pv["son_dip_fiyat"].where(pv["son_dip_fiyat"] <= dis).ffill().shift(1)
        tepe_etkin = pv["son_tepe_fiyat"].where(pv["son_tepe_fiyat"] >= dis).ffill().shift(1)
        s = p["stop_yuzde"] / 100.0
        return kur(mumlar, long_ok, short_ok, k * (1 - s), k * (1 + s),
                   cikis_l=d < dip_etkin, cikis_s=y > tepe_etkin)


class PivotTersStop(Strateji):
    """dis__pivot-ters-stop: onaylı pivot tepesinin üstüne stop-al, pivot dibinin altına stop-sat; hep piyasada.

    Kaynak: arsiv/strateji-sg/tv/pine/kzp8e4X3.pine (Monthly Returns in PineScript Strategies; mantık "PivRev").
    Kural: pivot tepe (sol 2, sağ 1 mum) onaylanınca "long bekliyor" durumu açılır; fiyat bu pivot tepeyi yukarı aşınca long
    girilir (durum kapanır). Pivot dip için short aynası. Ters sinyal pozisyonu döndürür.
    Uyarlama: Pine stop emri aşıldığı mum İÇİNDE dolar; burada aşıldığı mumun kapanışında sinyal, sonraki açılışta piyasa emri.
    Orijinalde stop yok (ters emir tek çıkış) -> long için stop son pivot dibi (short için son pivot tepesi); geçersizse
    (fiyatın yanlış tarafında) ATR stop (stop_atr). Ters pivot kırılımı `cikis`tir.
    Eski sonuç: kaldı: PF 2.24, Sharpe 2.45 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/pivot_rev.json).
    d11j EK (varsayılan "kirilim" = eski davranış; ızgaraya girmez; kaynak aile pivot-onayli-ters-stop, customPivotJbk): giris="olusum" ->
    giriş pivotun ONAYLANDIĞI mumda (tepe onayında long, dip onayında short; onay `sag` mum gecikmeli, nedensel), kırılım beklenmez;
    ters onay `cikis`. stop_yuzde>0 ise stop girişten %stop_yuzde (kaynak 5), hedef_yuzde>0 ise hedef girişten %hedef_yuzde (kaynak 4)
    (0: eski stop/hedef kuralı). Kaynak pivotu sol 4, sağ 2 mumla tanımlar.
    """
    ad = "dis__pivot-ters-stop"
    stil = "swing"
    varsayilan_parametreler = {"sol": 2, "sag": 1, "atr_periyot": 14, "stop_atr": 2.5, "short": True,
                               "giris": "kirilim", "stop_yuzde": 0.0, "hedef_yuzde": 0.0}
    parametre_izgarasi = {"sol": [2, 3, 4], "sag": [1, 2], "stop_atr": [2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        sol, sag = int(p["sol"]), int(p["sag"])
        mh, ml = y.shift(sag), d.shift(sag)
        tepe = (mh > y.shift(sag + 1).rolling(sol, min_periods=sol).max()) & (mh >= y.rolling(sag, min_periods=sag).max())
        dip = (ml < d.shift(sag + 1).rolling(sol, min_periods=sol).min()) & (ml <= d.rolling(sag, min_periods=sag).min())
        hfiyat = mh.where(tepe).ffill()
        lfiyat = ml.where(dip).ffill()
        yh, yl = y.to_numpy(float), d.to_numpy(float)
        hp, lp = hfiyat.to_numpy(), lfiyat.to_numpy()
        tp, dp = tepe.to_numpy(), dip.to_numpy()
        n = len(yh)
        le = se = False
        tl = np.zeros(n, dtype=bool)
        ts = np.zeros(n, dtype=bool)
        for i in range(n):
            if i:
                if le and not np.isnan(hp[i - 1]) and yh[i] > hp[i - 1]:
                    tl[i] = True
                if se and not np.isnan(lp[i - 1]) and yl[i] < lp[i - 1]:
                    ts[i] = True
            if tp[i]:
                le = True
            elif tl[i]:
                le = False
            if dp[i]:
                se = True
            elif ts[i]:
                se = False
        tl, ts = pd.Series(tl, index=k.index), pd.Series(ts & ~tl, index=k.index)
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        stop_l = lfiyat.where(lfiyat < k, k - p["stop_atr"] * atr)
        stop_s = hfiyat.where(hfiyat > k, k + p["stop_atr"] * atr)
        hedef_l = hedef_s = None
        if p["giris"] == "olusum":
            tl = pd.Series(tepe.fillna(False).to_numpy(dtype=bool), index=k.index)
            ts = pd.Series(dip.fillna(False).to_numpy(dtype=bool), index=k.index) & ~tl
        elif p["giris"] != "kirilim":
            raise ValueError(f"Bilinmeyen giris: {p['giris']}")
        if p["stop_yuzde"] > 0:
            stop_l, stop_s = k * (1 - p["stop_yuzde"] / 100.0), k * (1 + p["stop_yuzde"] / 100.0)
        if p["hedef_yuzde"] > 0:
            hedef_l, hedef_s = k * (1 + p["hedef_yuzde"] / 100.0), k * (1 - p["hedef_yuzde"] / 100.0)
        return kur(mumlar, tl, ts & bool(p["short"]), stop_l, stop_s, hedef_l, hedef_s, cikis_l=ts, cikis_s=tl)


class GoldenTrident(Strateji):
    """dis__golden-trident: Swing yapısı (30 mumluk en yüksek/en düşük) yönü + EMA200 + aralık süzgeci; yön dönünce çıkış.

    Kaynak: arsiv/strateji-sg/tv/pine/Eq4kPrrJ.pine (Golden Trident | Swing-Anchored VWAP Trend System).
    Kural: son `swing_n` mumun en yükseği en son görülmüşse yön = +1 (son en düşük daha eskiyse), aksi -1. Long: yön +1, kapanış
    > EMA200 ve son `chop_n` mumun aralığı > ATR x 0.8 (yatay piyasa süzgeci); sinyal koşulun False->True geçişidir. Yön -1'e
    dönünce long kapanır. Felaket stopu = giriş - 8 x ATR(14). Çapalı VWAP yalnız çizimdir (sinyalde kullanılmaz), alınmadı.
    Uyarlama: orijinal yalnız long (allowShort=False); `short=True` ayna kurar (yön -1, kapanış < EMA200). TF 4h varsayıldı
    (kaynak altın, TF belirtmiyor); gün sonu çıkışı yok.
    Eski sonuç: ön elemeyi geçti, test sonucu yok.
    """
    ad = "dis__golden-trident"
    stil = "swing"
    varsayilan_parametreler = {"swing_n": 30, "ema_n": 200, "chop_n": 20, "aralik_k": 0.8, "atr_periyot": 14,
                               "stop_atr": 8.0, "short": False}
    parametre_izgarasi = {"swing_n": [20, 30, 50], "ema_n": [100, 200, 300], "stop_atr": [6.0, 8.0, 10.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        sn = int(p["swing_n"])
        pos = pd.Series(np.arange(len(k), dtype=float), index=k.index)
        hi = (y == y.rolling(sn, min_periods=sn).max())
        lo = (d == d.rolling(sn, min_periods=sn).min())
        ph = pos.where(hi).ffill().fillna(0.0)
        pl = pos.where(lo).ffill().fillna(0.0)
        yon = pd.Series(np.where(ph > pl, 1, -1), index=k.index)
        ema = g.ema(k, int(p["ema_n"]))
        cn = int(p["chop_n"])
        atr_c = g.atr(y, d, k, cn)
        aralik_ok = (y.rolling(cn, min_periods=cn).max() - d.rolling(cn, min_periods=cn).min()) > atr_c * p["aralik_k"]
        long_c = (yon == 1) & (k > ema) & aralik_ok
        short_c = (yon == -1) & (k < ema) & aralik_ok
        yeni_l = long_c & ~long_c.shift(1, fill_value=False)
        yeni_s = short_c & ~short_c.shift(1, fill_value=False)
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        sd = p["stop_atr"] * atr
        return kur(mumlar, yeni_l, yeni_s & bool(p["short"]), k - sd, k + sd, cikis_l=yon == -1, cikis_s=yon == 1)


class ElliottItki(Strateji):
    """dis__elliott-itki: ZigZag'da 5 dalgalı itki bitince tersine (Reversal) veya dalga-4 geri çekilişinde trend yönünde (Wave 5) giriş.

    Kaynak: arsiv/strateji-sg/tv/pine/rvBgD3aP.pine (Elliott Wave Impulse Strategy | Wave 5 & Reversal Entries).
    ZigZag: pivot tepe/dip (sol `zz`, sağ 1 mum; 1 mum sonra onaylı) dönüşümlü nokta listesi (aynı yönde daha uç pivot son noktayı
    günceller). Reversal: son 6 noktada itki (dalga-3 en kısa değil, p5>p3, p2>p0, p4>p1) ve boyu >= min_imp x ATR ise tersine
    giriş, stop = p5 ± tampon x ATR, hedef = itkinin tgt_fib kadarı geri dönüş. Wave 5: son 5 noktada dalga-4 geri çekilişi dalga-3'ün
    [min_ret4, maks_ret4] aralığındaysa trend yönünde giriş, stop = p4 ± tampon x ATR, hedef = p4 + dalga-1 x w5_uzama. Ödül/risk >= min_rr
    ve zaman stopu `maks_mum`. mod: "Reversal", "Wave 5" veya "Both".
    Uyarlama: Pine'daki giriş/çıkış (kapanış fiyatı, sonraki mumda dolum) aynıdır; risk-yüzdeli boyutlandırma motora bırakıldı.
    Pine'ın ZigZag'ı pivot tepeleri/dipleri aynı mumda ikisini de görebilir; burada önce tepe sonra dip işlenir (orijinal sıra).
    Eski sonuç: kaldı: PF 0.90, Sharpe -0.55 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/elliott.json).
    """
    ad = "dis__elliott-itki"
    stil = "swing"
    varsayilan_parametreler = {"zz": 5, "tgt_fib": 0.5, "w5_uzama": 1.0, "min_ret4": 0.236, "maks_ret4": 0.618,
                               "min_imp": 1.5, "tampon": 0.2, "min_rr": 1.0, "maks_mum": 100, "atr_periyot": 14,
                               "mod": "Both", "yon": "Both"}
    parametre_izgarasi = {"zz": [4, 5, 7], "tgt_fib": [0.382, 0.5, 0.618], "min_imp": [1.0, 1.5, 2.0]}

    def cikis_var_mi(self) -> bool:
        return True   # hedef + zaman stopu

    @staticmethod
    def _itki(p0, p1, p2, p3, p4, p5, d):
        if d == 1:
            w1, w3, w5 = p1 - p0, p3 - p2, p5 - p4
            return w3 != min(w1, w3, w5) and p5 > p3 and p2 > p0 and p4 > p1
        w1, w3, w5 = p0 - p1, p2 - p3, p4 - p5
        return w3 != min(w1, w3, w5) and p3 > p5 and p0 > p2 and p1 > p4

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(y, d, k, int(p["atr_periyot"])).to_numpy()
        h, l, c = y.to_numpy(float), d.to_numpy(float), k.to_numpy(float)
        n = len(h)
        zz = int(p["zz"])
        zy: list = []
        zdir = 0
        yon = np.zeros(n, dtype="int64")
        stop = np.full(n, np.nan)
        hedef = np.full(n, np.nan)
        for t in range(zz + 2, n):
            cc = t - 1
            ph = h[cc] if (h[cc] > h[cc - zz:cc].max() and h[cc] >= h[t]) else np.nan
            pl = l[cc] if (l[cc] < l[cc - zz:cc].min() and l[cc] <= l[t]) else np.nan
            flipped = False
            if not np.isnan(ph):
                if zdir < 1:
                    zy.insert(0, ph)
                    zdir = 1
                    flipped = True
                elif ph > zy[0]:
                    zy[0] = ph
            if not np.isnan(pl):
                if zdir > -1:
                    zy.insert(0, pl)
                    zdir = -1
                    flipped = True
                elif pl < zy[0]:
                    zy[0] = pl
            del zy[8:]
            if not flipped or np.isnan(atr[t]) or t <= 50:
                continue
            a = atr[t]
            sdir, sstop, stgt, simp = 0, np.nan, np.nan, np.nan
            dd = 1 if zdir == -1 else -1
            if p["mod"] != "Wave 5" and len(zy) >= 7:
                p0, p1, p2, p3, p4, p5 = zy[6], zy[5], zy[4], zy[3], zy[2], zy[1]
                if self._itki(p0, p1, p2, p3, p4, p5, dd):
                    diff = abs(p5 - p0)
                    sdir = -1 if dd == 1 else 1
                    sstop = p5 + p["tampon"] * a if dd == 1 else p5 - p["tampon"] * a
                    stgt = p5 + (-1.0 if dd == 1 else 1.0) * diff * p["tgt_fib"]
                    simp = diff
            if sdir == 0 and p["mod"] != "Reversal" and len(zy) >= 5:
                p4, p3, p2, p1, p0 = zy[0], zy[1], zy[2], zy[3], zy[4]
                if dd == 1:
                    w1, w3 = p1 - p0, p3 - p2
                    ret = (p3 - p4) / w3 if w3 > 0 else np.nan
                    ok = w3 > w1 and w1 > 0 and p2 > p0 and p4 > p1 and p["min_ret4"] <= ret <= p["maks_ret4"]
                else:
                    w1, w3 = p0 - p1, p2 - p3
                    ret = (p4 - p3) / w3 if w3 > 0 else np.nan
                    ok = w3 > w1 and w1 > 0 and p0 > p2 and p1 > p4 and p["min_ret4"] <= ret <= p["maks_ret4"]
                if ok:
                    sdir = dd
                    sstop = p4 - p["tampon"] * a if dd == 1 else p4 + p["tampon"] * a
                    stgt = p4 + w1 * p["w5_uzama"] if dd == 1 else p4 - w1 * p["w5_uzama"]
                    simp = w3
            if sdir == 0 or np.isnan(simp) or simp < p["min_imp"] * a:
                continue
            risk = (sstop - c[t]) if sdir == -1 else (c[t] - sstop)
            odul = (c[t] - stgt) if sdir == -1 else (stgt - c[t])
            if not (risk > 0 and odul > 0 and odul / risk >= p["min_rr"]):
                continue
            if p["yon"] == "Long Only" and sdir == -1 or p["yon"] == "Short Only" and sdir == 1:
                continue
            yon[t], stop[t], hedef[t] = sdir, sstop, stgt
        yon_s = pd.Series(yon, index=k.index)
        stop_s = pd.Series(stop, index=k.index)
        hedef_s = pd.Series(hedef, index=k.index)
        return kur(mumlar, yon_s == 1, yon_s == -1, stop_s, stop_s, hedef_s, hedef_s, zaman_cikisi=int(p["maks_mum"]))
