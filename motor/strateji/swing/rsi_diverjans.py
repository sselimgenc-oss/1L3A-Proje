"""swing__rsi-diverjans: fiyat-RSI (veya CCI) diverjansı + teyit ile dönüş girişi. Stil alt sınıfı: scalp/rsi_diverjans.py.

Pivotlar `pivotlar.fraktal_pivotlar` (k=pivot_k) ile NEDENSEL bulunur: pivot ancak k mum sonra (onay mumunda) bilinir.
Boğa diverjansı (long): bu mumda yeni dip pivotu ONAYLANDI, son dip fiyatı < önceki dip fiyatı (daha düşük dip), osilatör
son dipte > önceki dipte (daha yüksek dip), iki pivot arası <= max_aralik mum, ve osilatör dipte aşırı bölgede
(RSI <= bolge_rsi; CCI <= -bolge_cci). bb_sart=True: dip mumunun dibi o mumda alt Bollinger bandının altında (singhal kartı).
Ayı diverjansı ayna (daha yüksek tepe, daha düşük osilatör tepesi). Diverjans bulunduktan sonra `teyit_n` mum içinde TEYİT
gelince giriş (bir diverjans en çok bir giriş): teyit="ema": kapanış > EMA(teyit_ema=21) ve yükseliş mumu (kapanış>açılış);
teyit="mum": yükseliş mumu ve kapanış önceki mumun zirvesinin üstünde (short ayna); teyit="yok": diverjans onay mumunda
giriş (Jordan/Johnson kartları teyit tanımlamaz). Fiyat diverjans dibinin altına inerse
diverjans geçersiz. Stop: diverjans dibi/tepesi -/+ stop_tampon_atr*ATR, risk <= stop_max_atr ATR. Hedef: hedef_tipi="r" ->
hedef_r*R; "orta_bant" -> SMA(bb_periyot) (girişin doğru tarafında değilse sinyal düşer). Çıkış: hedef veya ters diverjans
oluşumu (`cikis`, yön-bağımsız: herhangi bir diverjans onayı).
osilator="cci": CCI(rsi_periyot) kullanılır (kart scalp__cci-ayrisma__busiere: -100 altında yükselen dipler; "fiyat trend
oluşturmuyor" şartı kodlanmadı).
Kaynak kartlar: swing: swing__rsi-ayrisma__sharpe (21 EMA onayı), swing__rsi-farklilik__jordan, swing__rsi-sapma__johnson (teyitsiz),
swing__ssto-uyumsuzluk__crane (SSTO, 2-3 tekrar+RD; KODLANMADI), swing__obv-fiyat-farkliligi__boxer (OBV; KODLANMADI),
swing__macd-uyumsuzluk__penn (MACD histogram, yalnız short; KODLANMADI), daytrade__rsi-mw-pozisyonel__singhal (W/M yapısı;
diverjansın yaklaşığı olarak), swing__rsi-basarisizlik-salinimi__johnson (başarısızlık salınımı; KODLANMADI);
scalp: daytrade__rsi-diverjans-bollinger-1dk__singhal (bb_sart), scalp__cci-ayrisma__busiere (osilator="cci"),
scalp__rsi-diverjans-filtreli__carson (tescilli gösterge; fraktal diverjansla yaklaşık).
Varsayımlar: kitaplarda pivot tanımı/pencere yok -> fraktal k; teyit ve stop kitap yönlerinden (21 EMA / dip altı).
Negatif kanıt: aile kaydında yok; arşiv §3 osilatör dönüş/ortalamaya dönüş denemeleri başarısız; Sharpe'ın uyarısı: diverjans
düzeltmelerde de oluşur (filtre yok).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.pivotlar import fraktal_pivotlar
from motor.strateji.temel import Strateji


def _pivot_osc(osc: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Pivot pozisyon indeksindeki osilatör değeri (idx NaN ise NaN)."""
    out = np.full(len(idx), np.nan)
    ok = ~np.isnan(idx)
    out[ok] = osc[idx[ok].astype(int)]
    return out


class RsiDiverjans(Strateji):
    ad = "swing__rsi-diverjans"
    stil = "swing"
    varsayilan_parametreler = {
        "osilator": "rsi", "rsi_periyot": 14, "pivot_k": 3, "max_aralik": 60,
        "bolge_rsi": 50.0, "bolge_cci": 100.0, "bb_sart": False, "bb_periyot": 20,
        "teyit": "ema", "teyit_ema": 21, "teyit_n": 5,
        "stop_tampon_atr": 0.25, "stop_max_atr": 4.0, "hedef_tipi": "r", "hedef_r": 2.0,
        "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "pivot_k": [3, 5, 8],
        "rsi_periyot": [9, 14],
        "teyit": ["ema", "mum"],
        "hedef_tipi": ["r", "orta_bant"],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = len(k)
        if p["osilator"] == "rsi":
            osc = g.rsi(k, int(p["rsi_periyot"]))
            dip_bolge = lambda v: v <= p["bolge_rsi"]
            tepe_bolge = lambda v: v >= 100.0 - p["bolge_rsi"]
        elif p["osilator"] == "cci":
            osc = b.cci(y, d, k, int(p["rsi_periyot"]))
            dip_bolge = lambda v: v <= -p["bolge_cci"]
            tepe_bolge = lambda v: v >= p["bolge_cci"]
        else:
            raise ValueError(f"Bilinmeyen osilator: {p['osilator']}")
        atr = g.atr(y, d, k, p["atr_periyot"])
        bb = g.bollinger(k, int(p["bb_periyot"]), 2.0)
        pv = fraktal_pivotlar(y, d, int(p["pivot_k"]))
        o = osc.to_numpy()
        o_dip, o_dip0 = _pivot_osc(o, pv["son_dip_idx"].to_numpy()), _pivot_osc(o, pv["onceki_dip_idx"].to_numpy())
        o_tepe, o_tepe0 = _pivot_osc(o, pv["son_tepe_idx"].to_numpy()), _pivot_osc(o, pv["onceki_tepe_idx"].to_numpy())
        with np.errstate(invalid="ignore"):
            boga = (pv["yeni_dip"].to_numpy()
                    & (pv["son_dip_fiyat"] < pv["onceki_dip_fiyat"]).to_numpy()
                    & (o_dip > o_dip0) & dip_bolge(o_dip)
                    & ((pv["son_dip_idx"] - pv["onceki_dip_idx"]).to_numpy() <= p["max_aralik"]))
            ayi = (pv["yeni_tepe"].to_numpy()
                   & (pv["son_tepe_fiyat"] > pv["onceki_tepe_fiyat"]).to_numpy()
                   & (o_tepe < o_tepe0) & tepe_bolge(o_tepe)
                   & ((pv["son_tepe_idx"] - pv["onceki_tepe_idx"]).to_numpy() <= p["max_aralik"]))
        if p["bb_sart"]:
            di = pv["son_dip_idx"].to_numpy()
            ti = pv["son_tepe_idx"].to_numpy()
            dmum = np.where(np.isnan(di), 0, di).astype(int)
            tmum = np.where(np.isnan(ti), 0, ti).astype(int)
            boga &= d.to_numpy()[dmum] < bb["alt"].to_numpy()[dmum]
            ayi &= y.to_numpy()[tmum] > bb["ust"].to_numpy()[tmum]
        gecerli = (atr.notna() & osc.notna()).to_numpy()
        boga &= gecerli
        ayi &= gecerli & bool(p["short"])
        # teyit
        ema = g.ema(k, int(p["teyit_ema"])).to_numpy()
        kn, an, yn, dn = k.to_numpy(), a.to_numpy(), y.to_numpy(), d.to_numpy()
        if p["teyit"] == "ema":
            tey_l = (kn > ema) & (kn > an)
            tey_s = (kn < ema) & (kn < an)
        elif p["teyit"] == "yok":
            tey_l = tey_s = np.ones(n, dtype=bool)
        elif p["teyit"] == "mum":
            yo = np.r_[np.nan, yn[:-1]]
            do = np.r_[np.nan, dn[:-1]]
            tey_l = (kn > an) & (kn > yo)
            tey_s = (kn < an) & (kn < do)
        else:
            raise ValueError(f"Bilinmeyen teyit: {p['teyit']}")
        sd, st = pv["son_dip_fiyat"].to_numpy(), pv["son_tepe_fiyat"].to_numpy()
        long_ok = np.zeros(n, dtype=bool)
        short_ok = np.zeros(n, dtype=bool)
        yapi_dip = np.full(n, np.nan)
        yapi_tepe = np.full(n, np.nan)
        son_l = son_s = -1
        dip_f = tepe_f = np.nan
        bekle_l = bekle_s = False
        tn = int(p["teyit_n"])
        for t in range(n):
            if boga[t]:
                son_l, dip_f, bekle_l = t, sd[t], True
            if ayi[t]:
                son_s, tepe_f, bekle_s = t, st[t], True
            if bekle_l:
                if t - son_l > tn or dn[t] < dip_f:
                    bekle_l = False
                elif tey_l[t]:
                    long_ok[t], yapi_dip[t], bekle_l = True, dip_f, False
            if bekle_s:
                if t - son_s > tn or yn[t] > tepe_f:
                    bekle_s = False
                elif tey_s[t]:
                    short_ok[t], yapi_tepe[t], bekle_s = True, tepe_f, False
        idx = k.index
        long_ok, short_ok = pd.Series(long_ok, index=idx), pd.Series(short_ok, index=idx)
        tampon = p["stop_tampon_atr"] * atr
        stop_l = np.maximum(pd.Series(yapi_dip, index=idx) - tampon, k - p["stop_max_atr"] * atr)
        stop_s = np.minimum(pd.Series(yapi_tepe, index=idx) + tampon, k + p["stop_max_atr"] * atr)
        if p["hedef_tipi"] == "orta_bant":
            h_l = h_s = bb["orta"]
            long_ok &= h_l > k
            short_ok &= h_s < k
        elif p["hedef_tipi"] == "r":
            h_l, h_s = b.hedef_r_ile(k, stop_l, stop_s, p["hedef_r"])
        else:
            raise ValueError(f"Bilinmeyen hedef_tipi: {p['hedef_tipi']}")
        cikis = pd.Series(boga | ayi, index=idx)
        return cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, cikis)
