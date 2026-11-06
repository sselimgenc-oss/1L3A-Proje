"""D2 / "Smart Money" (SMC/ICT) ve yapı-kırılımı aileleri (TradingView).

`dis__smc-pro-btc`, `dis__smc-ob-fvg-sweep`, `dis__tomukas-smc`, `dis__smart-trend-bos`.
Hepsi durumlu (ileri-yürüyen) döngülerdir; t. mum kapanışında yalnız geçmişi kullanır. Pivotlar ta.pivothigh gibi
`n` mum gecikmeyle onaylanır. HTF yapısı `htf.ust_zaman` ile yalnız kapanmış üst mumlardan gelir.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.dis import _gosterge_d2 as gd
from motor.strateji.daytrade._ortak import cerceve, gun_sonu_uygula
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji
from motor.veri.depo import aralik_suresi


def _ust_yapi(mumlar: pd.DataFrame, aralik: str, n: int) -> np.ndarray:
    """Yapı trendini (+1/-1/0) `aralik` TF'sinde hesaplayıp grafik TF'sine kapanış sonrası hizalar (lookahead yok)."""
    kaynak = pd.Series(mumlar.index).diff().median()
    if kaynak == aralik_suresi(aralik):
        return gd.yapi_trendi(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], n).to_numpy()
    s = ust_zaman(mumlar, aralik, lambda u: pd.DataFrame(
        {"t": gd.yapi_trendi(u["yuksek"], u["dusuk"], u["kapanis"], n).astype(float)}))["t"]
    return s.fillna(0.0).to_numpy().astype("int64")


class SmcProBtc(Strateji):
    """SMC Pro BTC - ICT Order Blocks & FVG [DOE] (15m scalp).

    Kaynak: arsiv/strateji-sg/tv/pine/QMvHkvdQ.pine.
    Kural (long): HTF(4h) ve MTF(1h) yapı trendi yukarı (kapanış son onaylı pivot tepeyi aşmış), son 20 mumda likidite
    süpürme (low < son pivot dip ve close > o dip), fiyat bir BOS sonrası bulunan yükseliş order block'unda (son 15 mumdaki
    son düşüş mumu) ya da yükseliş FVG'sinde (low > high[2], ortası yükseliş mumu), yükseliş mumu kapanışı ise long.
    Stop = bölge dibi * (1 - %0.3); hedef = 2R. Short ayna. Seçici mod (secici=True): ayrıca fiyat son salınım aralığının
    ilk %80'inde (long) / son %80'inde (short) olmalı. Uyarlama: Pine'ın request.security'si htf.ust_zaman ile
    nedensel yapıldı; grafik TF'si 15m (≤ 1h MTF olmalı; scalp min 15m). Çıkış = stop/hedef (hedef sabit 2R).
    Eski proje sonucu: sonuç yok (envanterde boş).
    """
    ad = "dis__smc-pro-btc"
    stil = "scalp"
    varsayilan_parametreler = {"swing_n": 10, "ob_geri": 15, "supurme_pencere": 20, "rr": 2.0, "sl_tampon": 0.3,
                               "pd_esik": 0.80, "secici": False, "htf": "4h", "mtf": "1h", "short": True}
    parametre_izgarasi = {"swing_n": [8, 10, 14], "rr": [1.5, 2.0, 3.0], "secici": [False, True]}

    def cikis_var_mi(self) -> bool:
        return True   # sabit R hedefi

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = (mumlar[c].to_numpy(dtype=float) for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        n = len(k)
        L = p["swing_n"]
        htf = _ust_yapi(mumlar, p["htf"], L)
        mtf = _ust_yapi(mumlar, p["mtf"], L)
        ph = gd.pivot_yuksek(mumlar["yuksek"], L).to_numpy()
        pl = gd.pivot_dusuk(mumlar["dusuk"], L).to_numpy()
        sh = pd.Series(ph).ffill().to_numpy()
        sl_ = pd.Series(pl).ffill().to_numpy()
        long_ok = np.zeros(n, dtype=bool)
        short_ok = np.zeros(n, dtype=bool)
        st_l = np.full(n, np.nan)
        st_s = np.full(n, np.nan)
        bs_boga = bs_ayi = 10 ** 6
        obb_top = obb_bot = obs_top = obs_bot = np.nan
        obb_v = obs_v = False
        fb_top = fb_bot = fs_top = fs_bot = np.nan
        fb_v = fs_v = False
        buf = p["sl_tampon"] / 100.0
        for i in range(n):
            boga_sup = (not np.isnan(sl_[i])) and d[i] < sl_[i] and k[i] > sl_[i]
            ayi_sup = (not np.isnan(sh[i])) and y[i] > sh[i] and k[i] < sh[i]
            bs_boga = 0 if boga_sup else bs_boga + 1
            bs_ayi = 0 if ayi_sup else bs_ayi + 1
            bos_u = i > 0 and not np.isnan(sh[i]) and k[i] > sh[i] and k[i - 1] <= sh[i - 1]
            bos_d = i > 0 and not np.isnan(sl_[i]) and k[i] < sl_[i] and k[i - 1] >= sl_[i - 1]
            if bos_u:
                for j in range(1, p["ob_geri"] + 1):
                    if i - j >= 0 and k[i - j] < a[i - j]:
                        obb_top, obb_bot, obb_v = y[i - j], d[i - j], True
                        break
            if bos_d:
                for j in range(1, p["ob_geri"] + 1):
                    if i - j >= 0 and k[i - j] > a[i - j]:
                        obs_top, obs_bot, obs_v = y[i - j], d[i - j], True
                        break
            if obb_v and k[i] < obb_bot:
                obb_v = False
            if obs_v and k[i] > obs_top:
                obs_v = False
            if i >= 2 and d[i] > y[i - 2] and k[i - 1] > a[i - 1]:
                fb_top, fb_bot, fb_v = d[i], y[i - 2], True
            if i >= 2 and y[i] < d[i - 2] and k[i - 1] < a[i - 1]:
                fs_top, fs_bot, fs_v = d[i - 2], y[i], True
            if fb_v and k[i] < fb_bot:
                fb_v = False
            if fs_v and k[i] > fs_top:
                fs_v = False
            in_bob = obb_v and d[i] <= obb_top and k[i] >= obb_bot
            in_obs = obs_v and y[i] >= obs_bot and k[i] <= obs_top
            in_fb = fb_v and d[i] <= fb_top and k[i] >= fb_bot
            in_fs = fs_v and y[i] >= fs_bot and k[i] <= fs_top
            disk_ok = prem_ok = True
            if p["secici"]:
                if np.isnan(sh[i]) or np.isnan(sl_[i]):
                    disk_ok = prem_ok = False
                else:
                    r = sh[i] - sl_[i]
                    disk_ok = k[i] < sl_[i] + r * p["pd_esik"]
                    prem_ok = k[i] > sh[i] - r * p["pd_esik"]
            if (htf[i] == 1 and mtf[i] == 1 and bs_boga <= p["supurme_pencere"] and (in_bob or in_fb)
                    and k[i] > a[i] and disk_ok):
                long_ok[i] = True
                st_l[i] = (obb_bot if in_bob else fb_bot) * (1 - buf)
            if (p["short"] and htf[i] == -1 and mtf[i] == -1 and bs_ayi <= p["supurme_pencere"]
                    and (in_obs or in_fs) and k[i] < a[i] and prem_ok):
                short_ok[i] = True
                st_s[i] = (obs_top if in_obs else fs_top) * (1 + buf)
        idx = mumlar.index
        kap = mumlar["kapanis"]
        sl, ss = pd.Series(st_l, index=idx), pd.Series(st_s, index=idx)
        return cerceve(mumlar, long_ok, short_ok, sl, ss,
                       kap + p["rr"] * (kap - sl), kap - p["rr"] * (ss - kap))


class SmcObFvgSweep(Strateji):
    """SMC Strategy - OB + FVG + Liquidity Sweep (1h daytrade).

    Kaynak: arsiv/strateji-sg/tv/pine/jSNZ1CmV.pine.
    Kural (long): pivot (5) tepesini kapanışla aşan, gövdesi >= 1.2*ATR "yer değiştirme" mumlu BOS; ondan önceki <= 30 mumda
    sellenmiş (kısa süre önce likidite havuzu dibinin altına iğne atıp üstünde kapanan) bir sweep varsa onaylı; son 15 mumdaki
    son düşüş mumu = order block (OB). Bu OB'ye 20 mum içinde dokunulursa (retest) dokunma mumu kapanışında long
    (onay modu "yok"). Stop = OB dibi - 0.1*ATR; hedef = 2R; fiyat 1R'ye ulaşınca stop girişe çekilir
    (CikisAyarlari.basabas_r_esigi=1.0). Short ayna.
    Uyarlama: HTF yanlılığı ve FVG birleşimi (varsayılan kapalıydı) ve havuz-hedef modu (hedef R-katı kullanıldı) dahil
    edilmedi; pozisyon boyutlandırma (risk %1 / max %25) motora bırakıldı; UTC gün sonu zorunlu çıkış eklendi (1h).
    Eski proje sonucu: sonuç yok (envanterde boş).
    """
    ad = "dis__smc-ob-fvg-sweep"
    stil = "daytrade"
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=1.0)
    varsayilan_parametreler = {"swing_n": 5, "ob_geri": 15, "yer_degistirme": 1.2, "atr_periyot": 14,
                               "havuz_max": 15, "havuz_yas": 300, "sweep_zaman_asimi": 30, "dokunma_zaman_asimi": 20,
                               "onay_zaman_asimi": 10, "ob_tampon_atr": 0.1, "rr": 2.0, "retest": True,
                               "onay": "yok", "short": True}
    parametre_izgarasi = {"swing_n": [5, 8], "rr": [1.5, 2.0, 3.0], "yer_degistirme": [0.0, 1.2], "onay": ["yok", "ob_ustu"]}

    def cikis_var_mi(self) -> bool:
        return True   # sabit R hedefi + gün sonu

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = (mumlar[c].to_numpy(dtype=float) for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        n = len(k)
        L = p["swing_n"]
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], p["atr_periyot"]).to_numpy()
        ph = gd.pivot_yuksek(mumlar["yuksek"], L).to_numpy()
        pl = gd.pivot_dusuk(mumlar["dusuk"], L).to_numpy()
        long_ok = np.zeros(n, dtype=bool)
        short_ok = np.zeros(n, dtype=bool)
        st_l = np.full(n, np.nan)
        st_s = np.full(n, np.nan)
        sh = sl_ = np.nan
        trend = 0
        havuz_h, havuz_l = [], []                  # (fiyat, mum_no)
        arm_l = arm_s = False
        arm_l_bar = arm_s_bar = -10 ** 9
        f_b = dict(top=np.nan, bot=np.nan, bar=-10 ** 9, armed=False, touched=False, retest_high=np.nan, touch_bar=-10 ** 9)
        f_s = dict(top=np.nan, bot=np.nan, bar=-10 ** 9, armed=False, touched=False, retest_low=np.nan, touch_bar=-10 ** 9)
        onay = p["onay"]
        for i in range(n):
            sh_onceki, sl_onceki = sh, sl_
            if not np.isnan(ph[i]):
                sh = ph[i]
                havuz_h.append((ph[i], i - L))
                if len(havuz_h) > p["havuz_max"]:
                    havuz_h.pop(0)
            if not np.isnan(pl[i]):
                sl_ = pl[i]
                havuz_l.append((pl[i], i - L))
                if len(havuz_l) > p["havuz_max"]:
                    havuz_l.pop(0)
            if np.isnan(atr[i]):
                continue
            govde = abs(k[i] - a[i])
            disp_u = govde >= atr[i] * p["yer_degistirme"] and k[i] > a[i]
            disp_d = govde >= atr[i] * p["yer_degistirme"] and k[i] < a[i]
            bos_u = (not np.isnan(sh)) and i > 0 and k[i] > sh and k[i - 1] <= sh_onceki and disp_u
            bos_d = (not np.isnan(sl_)) and i > 0 and k[i] < sl_ and k[i - 1] >= sl_onceki and disp_d
            if bos_u:
                trend = 1
            if bos_d:
                trend = -1
            havuz_h = [(q, b) for q, b in havuz_h if i - b <= p["havuz_yas"]]
            havuz_l = [(q, b) for q, b in havuz_l if i - b <= p["havuz_yas"]]
            sup_h = sup_l = False
            for j in range(len(havuz_h) - 1, -1, -1):
                if y[i] > havuz_h[j][0] and k[i] < havuz_h[j][0]:
                    sup_h = True
                    havuz_h.pop(j)
                    break
            for j in range(len(havuz_l) - 1, -1, -1):
                if d[i] < havuz_l[j][0] and k[i] > havuz_l[j][0]:
                    sup_l = True
                    havuz_l.pop(j)
                    break
            if sup_l and trend <= 0:
                arm_l, arm_l_bar = True, i
            if sup_h and trend >= 0:
                arm_s, arm_s_bar = True, i
            if arm_l and i - arm_l_bar > p["sweep_zaman_asimi"]:
                arm_l = False
            if arm_s and i - arm_s_bar > p["sweep_zaman_asimi"]:
                arm_s = False
            if bos_d:
                arm_l = False
            if bos_u:
                arm_s = False
            long_conf = bos_u and arm_l
            short_conf = bos_d and arm_s
            giris_l = giris_s = False
            ob_l = ob_s = None
            if long_conf:
                for j in range(1, p["ob_geri"] + 1):
                    if i - j >= 0 and k[i - j] < a[i - j]:
                        ob_l = (y[i - j], d[i - j])
                        break
                if ob_l is not None:
                    f_b.update(top=ob_l[0], bot=ob_l[1], bar=i, armed=True, touched=False, retest_high=np.nan)
            if short_conf:
                for j in range(1, p["ob_geri"] + 1):
                    if i - j >= 0 and k[i - j] > a[i - j]:
                        ob_s = (y[i - j], d[i - j])
                        break
                if ob_s is not None:
                    f_s.update(top=ob_s[0], bot=ob_s[1], bar=i, armed=True, touched=False, retest_low=np.nan)
            if bos_d:
                f_b.update(armed=False, touched=False)
            if bos_u:
                f_s.update(armed=False, touched=False)
            if f_b["armed"]:
                if i - f_b["bar"] > p["dokunma_zaman_asimi"]:
                    f_b["armed"] = False
                elif y[i] >= f_b["bot"] and d[i] <= f_b["top"]:
                    f_b.update(armed=False, touched=True, retest_high=y[i], touch_bar=i)
            if f_s["armed"]:
                if i - f_s["bar"] > p["dokunma_zaman_asimi"]:
                    f_s["armed"] = False
                elif d[i] <= f_s["top"] and y[i] >= f_s["bot"]:
                    f_s.update(armed=False, touched=True, retest_low=d[i], touch_bar=i)
            bot_stop = top_stop = np.nan
            if f_b["touched"]:
                if i - f_b["touch_bar"] > p["onay_zaman_asimi"]:
                    f_b["touched"] = False
                else:
                    gv = abs(k[i] - a[i])
                    alt_fitil = min(a[i], k[i]) - d[i]
                    ok = {"yok": True,
                          "ret_mumu": k[i] > a[i] and alt_fitil > gv * 1.2,
                          "yutan": k[i] > a[i] and i > 0 and k[i - 1] < a[i - 1] and a[i] <= k[i - 1] and k[i] >= a[i - 1],
                          "ob_ustu": k[i] > f_b["top"],
                          "ret_kirilim": k[i] > f_b["retest_high"]}[onay]
                    if ok:
                        giris_l, bot_stop = True, f_b["bot"]
                        f_b.update(touched=False)
            if f_s["touched"]:
                if i - f_s["touch_bar"] > p["onay_zaman_asimi"]:
                    f_s["touched"] = False
                else:
                    gv = abs(k[i] - a[i])
                    ust_fitil = y[i] - max(a[i], k[i])
                    ok = {"yok": True,
                          "ret_mumu": k[i] < a[i] and ust_fitil > gv * 1.2,
                          "yutan": k[i] < a[i] and i > 0 and k[i - 1] > a[i - 1] and a[i] >= k[i - 1] and k[i] <= a[i - 1],
                          "ob_ustu": k[i] < f_s["bot"],
                          "ret_kirilim": k[i] < f_s["retest_low"]}[onay]
                    if ok:
                        giris_s, top_stop = True, f_s["top"]
                        f_s.update(touched=False)
            if not p["retest"]:
                giris_l, giris_s = long_conf and ob_l is not None, short_conf and ob_s is not None
                bot_stop = ob_l[1] if giris_l else np.nan
                top_stop = ob_s[0] if giris_s else np.nan
            if giris_l:
                long_ok[i] = True
                st_l[i] = bot_stop - atr[i] * p["ob_tampon_atr"]
                f_b.update(top=np.nan, bot=np.nan, bar=-10 ** 9, armed=False, touched=False)
            if giris_s and p["short"]:
                short_ok[i] = True
                st_s[i] = top_stop + atr[i] * p["ob_tampon_atr"]
                f_s.update(top=np.nan, bot=np.nan, bar=-10 ** 9, armed=False, touched=False)
        idx = mumlar.index
        kap = mumlar["kapanis"]
        sl, ss = pd.Series(st_l, index=idx), pd.Series(st_s, index=idx)
        sig = cerceve(mumlar, long_ok, short_ok, sl, ss,
                      kap + p["rr"] * (kap - sl), kap - p["rr"] * (ss - kap))
        return gun_sonu_uygula(sig)


class TomukasSmc(Strateji):
    """Tomukas Elite SMC (1h daytrade).

    Kaynak: arsiv/strateji-sg/tv/pine/83hmaEOQ.pine.
    Kural (long): seans içinde (12:00-21:00 UTC = 08:00-17:00 UTC-4; DST yok sayıldı), ADX(14) > 20 ve kapanış > EMA200
    iken: pivot (5) dibinin altına iğne atıp üstünde kapanan, güçlü alt fitilli (close > orta ve alt gövde/fitil > 1.5) bir
    "sweep"; ardından kapanışın son pivot tepeyi aşması (MSS) ve o mumda low > high[2] ise FVG [high[2], low]; sonraki
    mumlardan biri FVG'ye (low <= fvgTop ve low >= fvgBot) dokununca long. Stop = sweep dibi; ilk hedef 1R'de pozisyonun
    %50'si kapanır ve stop girişe çekilir (kismi=((1.0, 0.5),), başabaş 1R); kalan: karşı yönde sweep ya da kapanış < EMA200
    ile çıkış. Short ayna.
    Uyarlama: `fvg_min_yuzde` orijinalde (0.1) yalnız kutu çizimini etkiliyordu, sinyali değil; burada gerçek süzgeçtir,
    varsayılan 0.0 (= orijinal davranış). UTC gün sonu zorunlu çıkış eklendi (1h). ADX Wilder (RMA) ile aynı.
    Eski proje sonucu: ön elemeyi geçti, test sonucu yok.
    """
    ad = "dis__tomukas-smc"
    stil = "daytrade"
    cikis_ayarlari = CikisAyarlari(kismi=((1.0, 0.5),), basabas_r_esigi=1.0)
    varsayilan_parametreler = {"ema_n": 200, "adx_n": 14, "adx_esik": 20.0, "swing_n": 5, "fvg_min_yuzde": 0.0,
                               "seans_bas": 12.0, "seans_son": 21.0, "short": True}
    parametre_izgarasi = {"swing_n": [3, 5, 8], "adx_esik": [15.0, 20.0, 25.0], "fvg_min_yuzde": [0.0, 0.1]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = (mumlar[c].to_numpy(dtype=float) for c in ("acilis", "yuksek", "dusuk", "kapanis"))
        n = len(k)
        ema = g.ema(mumlar["kapanis"], p["ema_n"]).to_numpy()
        adx = g.adx(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], p["adx_n"])["adx"].to_numpy()
        saat = (mumlar.index.hour + mumlar.index.minute / 60.0).to_numpy()
        seans = (saat >= p["seans_bas"]) & (saat < p["seans_son"])
        ph = gd.pivot_yuksek(mumlar["yuksek"], p["swing_n"]).to_numpy()
        pl = gd.pivot_dusuk(mumlar["dusuk"], p["swing_n"]).to_numpy()
        long_ok = np.zeros(n, dtype=bool)
        short_ok = np.zeros(n, dtype=bool)
        st_l = np.full(n, np.nan)
        st_s = np.full(n, np.nan)
        tip_seri = np.zeros(n, dtype="int64")
        last_ph = last_pl = np.nan
        tip, ekstrem = 0, np.nan
        mss = False
        ftop = fbot = np.nan
        for i in range(n):
            if not np.isnan(ph[i]):
                last_ph = ph[i]
            if not np.isnan(pl[i]):
                last_pl = pl[i]
            orta = (y[i] + d[i]) / 2.0
            boga_ret = k[i] > orta and (k[i] - d[i]) > (y[i] - k[i]) * 1.5
            ayi_ret = k[i] < orta and (y[i] - k[i]) > (k[i] - d[i]) * 1.5
            sweep_l = (not np.isnan(last_pl)) and d[i] < last_pl and k[i] > last_pl and boga_ret
            sweep_h = (not np.isnan(last_ph)) and y[i] > last_ph and k[i] < last_ph and ayi_ret
            if sweep_l:
                tip, ekstrem = 1, d[i]
            if sweep_h:
                tip, ekstrem = -1, y[i]
            if sweep_l or sweep_h:
                mss = False
                ftop = fbot = np.nan
            if tip == 1 and not mss and not np.isnan(last_ph):
                if k[i] > last_ph and last_ph > ekstrem:
                    mss = True
                    if i >= 2 and d[i] > y[i - 2] and (d[i] - y[i - 2]) / y[i - 2] * 100.0 >= p["fvg_min_yuzde"]:
                        ftop, fbot = d[i], y[i - 2]
            if tip == -1 and not mss and not np.isnan(last_pl):
                if k[i] < last_pl and last_pl < ekstrem:
                    mss = True
                    if i >= 2 and y[i] < d[i - 2] and (d[i - 2] - y[i]) / y[i] * 100.0 >= p["fvg_min_yuzde"]:
                        ftop, fbot = d[i - 2], y[i]
            gecerli = mss and (not np.isnan(ftop)) and (not np.isnan(adx[i])) and adx[i] > p["adx_esik"] and seans[i]
            if gecerli and tip == 1 and k[i] > ema[i] and d[i] <= ftop and d[i] >= fbot:
                long_ok[i], st_l[i] = True, ekstrem
                ftop = fbot = np.nan
            elif gecerli and tip == -1 and p["short"] and k[i] < ema[i] and y[i] >= fbot and y[i] <= ftop:
                short_ok[i], st_s[i] = True, ekstrem
                ftop = fbot = np.nan
            if not np.isnan(ftop):
                if tip == 1 and k[i] < fbot:
                    ftop = fbot = np.nan
                elif tip == -1 and k[i] > ftop:
                    ftop = fbot = np.nan
            tip_seri[i] = tip
        idx = mumlar.index
        sig = cerceve(mumlar, long_ok, short_ok, pd.Series(st_l, index=idx), pd.Series(st_s, index=idx))
        ema_s = pd.Series(ema, index=idx)
        kap = mumlar["kapanis"]
        sig = gd.yonlu_cerceve(sig, (pd.Series(tip_seri, index=idx) == -1) | (kap < ema_s),
                               (pd.Series(tip_seri, index=idx) == 1) | (kap > ema_s))
        return gun_sonu_uygula(sig)


class SmartTrendBos(Strateji):
    """Smart Trend Strategy | julzALGO (1h daytrade).

    Kaynak: arsiv/strateji-sg/tv/pine/Sg2qyDDe.pine.
    Kural (long): KAMA(ER 20, hızlı 5, yavaş 30) serisine Kalman süzgeci (süreç gürültüsü 1e-4, ölçüm 0.01) uygulanır;
    süzgeç yükselirse trend +1. Pivot (10) tepe/dip kırılımları: kapanışla son pivot tepeyi aşmak = BOS (yapı trendi
    zaten yukarıysa) veya CHoCH (yapı trendi aşağıdan dönüyorsa). Trend +1 iken, trigger mumu (trend dönüşü, BOS veya
    CHoCH) ve son `senkron` mum içinde trend dönüşü ile BOS ya da CHoCH birlikte görülmüşse long. Stop = kapanış - 3*ATR(14);
    hedef long 2R, short 1R. Short ayna; zıt sinyal pozisyonu kapatır/çevirir (yönlü çıkış).
    Uyarlama: 7 günlük "backtest penceresi" girdisi kaldırıldı; pozisyon boyutlandırma motora bırakıldı; yalnız ATR stop
    modu (yapı/yüzde stop modları yok). 1h seçildi (belirtilmemiş; eski proje de 1h); UTC gün sonu zorunlu çıkış eklendi.
    Eski proje sonucu: ön elemeyi geçti, test sonucu yok.
    """
    ad = "dis__smart-trend-bos"
    stil = "daytrade"
    varsayilan_parametreler = {"er_n": 20, "hizli": 5, "yavas": 30, "surec_gurultu": 0.0001, "olcum_gurultu": 0.01,
                               "pivot_n": 10, "senkron": 10, "onay_modu": 0, "atr_periyot": 14, "stop_atr": 3.0,
                               "long_rr": 2.0, "short_rr": 1.0, "short": True}
    parametre_izgarasi = {"pivot_n": [7, 10, 14], "senkron": [5, 10], "long_rr": [1.5, 2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = (mumlar[c].to_numpy(dtype=float) for c in ("yuksek", "dusuk", "kapanis"))
        n = len(k)
        # KAMA + Kalman
        degisim = np.abs(k - np.r_[np.full(p["er_n"], np.nan), k[:-p["er_n"]]]) if n > p["er_n"] else np.full(n, np.nan)
        fark = np.abs(np.diff(k, prepend=np.nan))
        vol = pd.Series(fark).rolling(p["er_n"], min_periods=p["er_n"]).sum().to_numpy()
        er = np.where(np.isnan(degisim) | np.isnan(vol), 0.0, np.where(vol == 0, 0.0, degisim / np.where(vol == 0, 1, vol)))
        hs, ys = 2.0 / (p["hizli"] + 1.0), 2.0 / (p["yavas"] + 1.0)
        sc = (er * (hs - ys) + ys) ** 2
        kama = np.empty(n)
        kal = np.empty(n)
        pp = 1.0
        for i in range(n):
            kama[i] = k[i] if i == 0 else kama[i - 1] + sc[i] * (k[i] - kama[i - 1])
            pp += p["surec_gurultu"]
            kg = pp / (pp + p["olcum_gurultu"])
            kal[i] = kama[i] if i == 0 else kal[i - 1] + kg * (kama[i] - kal[i - 1])
            pp = (1.0 - kg) * pp
        trend = np.zeros(n, dtype="int64")
        for i in range(n):
            prev = trend[i - 1] if i else 0
            trend[i] = 1 if (i and kal[i] > kal[i - 1]) else (-1 if (i and kal[i] < kal[i - 1]) else prev)
        boga_flip = (trend == 1) & (np.r_[0, trend[:-1]] != 1)
        ayi_flip = (trend == -1) & (np.r_[0, trend[:-1]] != -1)
        # yapı
        ph = gd.pivot_yuksek(mumlar["yuksek"], p["pivot_n"]).to_numpy()
        pl = gd.pivot_dusuk(mumlar["dusuk"], p["pivot_n"]).to_numpy()
        son_h = son_l = np.nan
        h_alindi = l_alindi = False
        yapi = 0
        bos_u = np.zeros(n, dtype=bool)
        bos_d = np.zeros(n, dtype=bool)
        cho_u = np.zeros(n, dtype=bool)
        cho_d = np.zeros(n, dtype=bool)
        for i in range(n):
            if not np.isnan(ph[i]):
                son_h, h_alindi = ph[i], False
            if not np.isnan(pl[i]):
                son_l, l_alindi = pl[i], False
            kir_u = (not np.isnan(son_h)) and (not h_alindi) and i > 0 and k[i] > son_h and k[i - 1] <= son_h
            kir_d = (not np.isnan(son_l)) and (not l_alindi) and i > 0 and k[i] < son_l and k[i - 1] >= son_l
            cho_u[i] = kir_u and yapi == -1
            cho_d[i] = kir_d and yapi == 1
            bos_u[i] = kir_u and not cho_u[i]
            bos_d[i] = kir_d and not cho_d[i]
            if kir_u:
                h_alindi, yapi = True, 1
            if kir_d:
                l_alindi, yapi = True, -1

        def yakin(bayrak_a, bayrak_b):
            """İki olayın son görüldüğü mum arası fark <= senkron (ikisi de görülmüşse)."""
            ia = pd.Series(np.where(bayrak_a, np.arange(n), np.nan)).ffill().to_numpy()
            ib = pd.Series(np.where(bayrak_b, np.arange(n), np.nan)).ffill().to_numpy()
            return (~np.isnan(ia)) & (~np.isnan(ib)) & (np.abs(ia - ib) <= p["senkron"])

        m = p["onay_modu"]
        tamam_u = {0: yakin(boga_flip, bos_u) | yakin(boga_flip, cho_u), 1: yakin(boga_flip, bos_u),
                   2: yakin(boga_flip, cho_u), 3: yakin(boga_flip, bos_u) & yakin(boga_flip, cho_u)}[m]
        tamam_d = {0: yakin(ayi_flip, bos_d) | yakin(ayi_flip, cho_d), 1: yakin(ayi_flip, bos_d),
                   2: yakin(ayi_flip, cho_d), 3: yakin(ayi_flip, bos_d) & yakin(ayi_flip, cho_d)}[m]
        long_c = (trend == 1) & tamam_u & (boga_flip | bos_u | cho_u)
        short_c = (trend == -1) & tamam_d & (ayi_flip | bos_d | cho_d)
        idx = mumlar.index
        kap = mumlar["kapanis"]
        a = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, p["atr_periyot"])
        sl, ss = kap - p["stop_atr"] * a, kap + p["stop_atr"] * a
        sig = cerceve(mumlar, pd.Series(long_c, index=idx), pd.Series(short_c & bool(p["short"]), index=idx), sl, ss,
                      kap + p["long_rr"] * (kap - sl), kap - p["short_rr"] * (ss - kap))
        sig = gd.yonlu_cerceve(sig, pd.Series(short_c, index=idx), pd.Series(long_c, index=idx))
        return gun_sonu_uygula(sig)
