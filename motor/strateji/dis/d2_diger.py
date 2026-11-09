"""D2 / tek tek TradingView stratejileri: NORN WEAVE, Trend Analysis, SHM, VP Value-Area, OBS hacim şoku, XAU EMA-ATR.

`dis__norn-weave`, `dis__trend-analysis`, `dis__shm-wma`, `dis__vp-deger-alani`, `dis__obs-hacim-soku`, `dis__xau-ema-atr`.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.dis import _gosterge_d2 as gd
from motor.strateji.daytrade._ortak import cerceve, gun_sonu_uygula, seans_kimligi
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji


class NornWeave(Strateji):
    """NORN WEAVE ᚠ FEHU (4h swing, long+short).

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/teYPT1m0.pine.
    Kural: EMA(58) yükseliyor (short: düşüyor), Dow yapısı yukarı (kapanış son pivot (13) tepeyi aşınca trend +1;
    son pivot dibin altına inince -1) ve ADX(14) > 20.5 ise giriş. Çıkışlar: %10 sabit stop; kâr %5.5'e çıkınca stop
    girişe çekilir (başabaş; R cinsinden 0.55R, CikisAyarlari.basabas_r_esigi); trend yön değiştirince çıkış; hedef
    ATR(50)*3.8 katları (orijinalde 3 kademe %30'ar).
    Uyarlama: 3 kademeli kısmi çıkış TEK hedefe indirildi (hedef_kademe, varsayılan 2 = ATR(50)*3.8*2). Footprint delta
    süzgeci (request.footprint, OHLCV dışı veri) KALDIRILDI. TF belirtilmemiş -> 4h. Eski proje sonucu: sonuç yok.
    """
    ad = "dis__norn-weave"
    stil = "swing"
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=0.55)
    varsayilan_parametreler = {"ema_n": 58, "atr_carpan": 3.8, "atr_n": 50, "stop_yuzde": 10.0, "adx_esik": 20.5,
                               "swing_n": 13, "hedef_kademe": 2, "short": True}
    parametre_izgarasi = {"ema_n": [34, 58], "adx_esik": [15.0, 20.5, 25.0], "hedef_kademe": [1, 2, 3]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ema = g.ema(k, p["ema_n"])
        adx = g.adx(y, d, k, 14)["adx"]
        sh = gd.pivot_yuksek(y, p["swing_n"]).ffill().to_numpy()
        sl_ = gd.pivot_dusuk(d, p["swing_n"]).ffill().to_numpy()
        c = k.to_numpy()
        trend = np.zeros(len(c), dtype="int64")
        t = 0
        for i in range(len(c)):
            if not np.isnan(sh[i]) and c[i] > sh[i] and t != 1:
                t = 1
            if not np.isnan(sl_[i]) and c[i] < sl_[i] and t != -1:
                t = -1
            trend[i] = t
        trend = pd.Series(trend, index=k.index)
        trend_ok = adx > p["adx_esik"]
        long_c = (ema > ema.shift(1)) & (trend == 1) & trend_ok
        short_c = (ema < ema.shift(1)) & (trend == -1) & trend_ok & bool(p["short"])
        atr = g.atr(y, d, k, p["atr_n"]) * p["atr_carpan"] * p["hedef_kademe"]
        f = p["stop_yuzde"] / 100.0
        sig = cerceve(mumlar, long_c, short_c, k * (1 - f), k * (1 + f), k + atr, k - atr)
        return gd.yonlu_cerceve(sig, trend == -1, trend == 1)


class TrendAnalysis(Strateji):
    """Trend Analysis Strategy (4h swing, long+short).

    Kaynak: arsiv/strateji-sg/tv/pine/Z8EhgIzs.pine.
    Kural: "Trend Tracker" = WMA(TR,14)*2.2 ile SuperTrend benzeri çizgi (long modda max(dn) yükselir, kapanış çizginin
    altına inince yön -1 ve çizgi üst banda geçer). Trend skoru 6 bileşenin toplamı (±1): tracker yönü, kapanış > denge
    (HMA(linreg(close,55),9)), denge eğimi, RSI > 50, RSI > RSI ortalaması, +DI > -DI. |skor|/6 >= %50 ise süzgeç geçer.
    Giriş: trend dönüşünde (veya "geç giriş": aynı trendin ilk 10 mumunda, süzgeç sonradan geçerse bir kez) yön
    yönünde. Stop = tracker çizgisi (yanlış tarafta ise 2*ATR); hedef R katı; 1.5R'de stop girişe çekilir
    (basabas_r_esigi=1.5, orijinal "TP1 sonrası başabaş"); ters trend dönüşünde çıkış.
    Uyarlama: üç kademeli kısmi çıkış (1.5R/2.5R/3.5R %33'er) TEK hedefe indirildi (hedef_r, varsayılan 2.5); MTF süzgeci,
    konsolidasyon bölgesi, ADX/RSI/hacim süzgeçleri (varsayılan kapalıydı) dahil edilmedi. TF belirtilmemiş -> 4h.
    Eski proje sonucu: sonuç yok.
    """
    ad = "dis__trend-analysis"
    stil = "swing"
    cikis_ayarlari = CikisAyarlari(basabas_r_esigi=1.5)
    varsayilan_parametreler = {"takip_atr_n": 14, "takip_carpan": 2.2, "min_skor": 50.0, "gec_giris": True,
                               "gec_pencere": 10, "hedef_r": 2.5, "atr_stop_carpan": 2.0, "short": True}
    parametre_izgarasi = {"takip_carpan": [1.8, 2.2, 3.0], "min_skor": [34.0, 50.0, 67.0], "hedef_r": [1.5, 2.5, 3.5]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = len(k)
        a_w = gd.wma(g.gercek_aralik(y, d, k), p["takip_atr_n"]).to_numpy()
        up, dn = y.to_numpy() + a_w * p["takip_carpan"], d.to_numpy() - a_w * p["takip_carpan"]
        c = k.to_numpy()
        trk = np.full(n, np.nan)
        yon = np.ones(n, dtype="int64")
        cur, dr = np.nan, 1
        for i in range(n):
            if np.isnan(a_w[i]):
                yon[i] = dr
                continue
            if np.isnan(cur):
                cur = dn[i]
            elif dr == 1:
                cur = max(cur, dn[i])
                if c[i] < cur:
                    dr, cur = -1, up[i]
            else:
                cur = min(cur, up[i])
                if c[i] > cur:
                    dr, cur = 1, dn[i]
            trk[i], yon[i] = cur, dr
        eq = gd.hma(gd.linreg(k, 55), 9)
        r = g.rsi(k, 14)
        rm = g.sma(r, 14)
        di = g.adx(y, d, k, 14)
        skor = (pd.Series(yon, index=k.index) + np.where(k > eq, 1, -1) + np.where(eq > eq.shift(1), 1, -1)
                + np.where(r > 50, 1, -1) + np.where(r > rm, 1, -1) + np.where(di["arti_di"] > di["eksi_di"], 1, -1))
        gecerli = (eq.notna() & rm.notna() & di["arti_di"].notna() & pd.Series(~np.isnan(trk), index=k.index)).to_numpy()
        yuzde = (skor / 6.0 * 100.0).to_numpy()
        pas_l, pas_s = yuzde >= p["min_skor"], yuzde <= -p["min_skor"]
        al = np.zeros(n, dtype=bool)
        sat = np.zeros(n, dtype=bool)
        sinyalli, baslangic = False, 0
        for i in range(1, n):
            ay = gecerli[i] and yon[i] == -1 and yon[i - 1] == 1
            bf = gecerli[i] and yon[i] == 1 and yon[i - 1] == -1
            if bf or ay:
                sinyalli, baslangic = False, i
            pencere = i - baslangic <= p["gec_pencere"]
            ad_l = gecerli[i] and yon[i] == 1 and (bf or (p["gec_giris"] and not sinyalli and pencere))
            ad_s = gecerli[i] and yon[i] == -1 and (ay or (p["gec_giris"] and not sinyalli and pencere))
            b_sig = ad_l and pas_l[i] and not sinyalli
            s_sig = ad_s and pas_s[i] and not sinyalli
            al[i], sat[i] = b_sig, s_sig
            if b_sig or s_sig:
                sinyalli = True
        idx = k.index
        a14 = g.atr(y, d, k, 14)
        trk_s = pd.Series(trk, index=idx)
        stop_l = trk_s.where(trk_s < k, k - p["atr_stop_carpan"] * a14)
        stop_s = trk_s.where(trk_s > k, k + p["atr_stop_carpan"] * a14)
        yon_s = pd.Series(yon, index=idx)
        sig = cerceve(mumlar, pd.Series(al, index=idx), pd.Series(sat & bool(p["short"]), index=idx), stop_l, stop_s,
                      k + p["hedef_r"] * (k - stop_l), k - p["hedef_r"] * (stop_s - k))
        bf_s = (yon_s == 1) & (yon_s.shift(1) == -1)
        af_s = (yon_s == -1) & (yon_s.shift(1) == 1)
        return gd.yonlu_cerceve(sig, af_s, bf_s)


class ShmWma(Strateji):
    """Sovereign Horizon Matrix (SHM) v8.0 (4h swing, long+short).

    Kaynak: arsiv/strateji-sg/tv/pine/wVNfdkHu.pine.
    Kural (varsayılan "Baseline Only" modu): ohlc4 üzerinde hızlı WMA(63) ve makro WMA(510). Kapanış (gövde) ya da yüksek/düşük
    (fitil) bu çizgilerden birini yukarı keserse (short: aşağı) tetik. Tetik + kapanış > SMA(41) + günlük RSI(33) 42-48
    arasında (short: 46-52) ise giriş (RSI ohlc4, günlük). Stop = tetik mumunun düşüğü * (1 - %3) (short: yüksek * 1.03).
    Orijinalde seçili çıkış "candle-close trail %77.2" fiilen devre dışıdır (pik kapanışın %77'si altı); bu yüzden çıkış =
    stop veya ters tetik (pozisyon çevirme).
    Uyarlama: günlük RSI `request.security(..., rsi[1])` yerine htf.ust_zaman ile NEDENSEL yapıldı: önceki günün (D-1)
    RSI'si, D+1 günü boyunca kullanılır (Pine'ın [1]'i zaten bir gün geri; burada kapanış hizalaması da bir gün geri, yani
    en fazla bir gün daha gecikir, lookahead yok). B&R modları ve Supertrend bağlantısı (varsayılan kapalı) dahil edilmedi.
    TF belirtilmemiş (eski proje 1h denemiş); WMA(510) ve günlük RSI nedeniyle 4h seçildi. Eski proje sonucu: ön elemeyi
    geçti, test sonucu yok.
    """
    ad = "dis__shm-wma"
    stil = "swing"
    varsayilan_parametreler = {"hizli": 63, "yavas": 510, "filtre_sma": 41, "rsi_n": 33, "rsi_filtre": True,
                               "uzun_rsi_min": 42.0, "uzun_rsi_max": 48.0, "kisa_rsi_min": 46.0, "kisa_rsi_max": 52.0,
                               "fitil_tetik": True, "sl_yuzde": 3.0, "short": True}
    parametre_izgarasi = {"hizli": [34, 63], "sl_yuzde": [2.0, 3.0, 5.0], "rsi_filtre": [True, False]}

    def cikis_var_mi(self) -> bool:
        return True   # ters tetikte çevirme

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a_, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        src = (a_ + y + d + k) / 4.0
        fw, sw = gd.wma(src, p["hizli"]), gd.wma(src, p["yavas"])
        fma = g.sma(src, p["filtre_sma"])
        if p["rsi_filtre"]:
            rsi_g = ust_zaman(mumlar, "1d", lambda u: pd.DataFrame(
                {"r": g.rsi((u["acilis"] + u["yuksek"] + u["dusuk"] + u["kapanis"]) / 4.0, p["rsi_n"]).shift(1)}))["r"]
            uzun_ok = (rsi_g >= p["uzun_rsi_min"]) & (rsi_g <= p["uzun_rsi_max"])
            kisa_ok = (rsi_g <= p["kisa_rsi_max"]) & (rsi_g >= p["kisa_rsi_min"])
        else:
            uzun_ok = kisa_ok = pd.Series(True, index=k.index)
        tl = gd.kesis_yukari(k, fw) | gd.kesis_yukari(k, sw)
        ts = gd.kesis_asagi(k, fw) | gd.kesis_asagi(k, sw)
        if p["fitil_tetik"]:
            tl = tl | gd.kesis_yukari(y, fw) | gd.kesis_yukari(y, sw)
            ts = ts | gd.kesis_asagi(d, fw) | gd.kesis_asagi(d, sw)
        valid = fw.notna() & sw.notna() & fma.notna()
        long_c = tl & (k > fma) & uzun_ok & valid
        short_c = ts & (k < fma) & kisa_ok & valid
        f = p["sl_yuzde"] / 100.0
        sig = cerceve(mumlar, long_c, short_c & bool(p["short"]), d * (1 - f), y * (1 + f))
        return gd.yonlu_cerceve(sig, short_c, long_c)


def _hacim_profili(yuksek, dusuk, hacim, satir: int, va_yuzde: float):
    """Satır sayısı `satir` olan hacim profili: (poc, vah, val). Her mumun hacmi kapsadığı satırlara eşit bölünür.
    Not: orijinal Pine'da VA genişletme yönü adlandırması ters kalmıştı (VAH/VAL yer değiştiriyordu); burada
    VAH = değer alanının ÜST, VAL = ALT sınırı olarak düzeltildi."""
    pl, ph = float(np.min(dusuk)), float(np.max(yuksek))
    adim = (ph - pl) / satir
    if not adim > 0:
        return np.nan, np.nan, np.nan
    r0 = np.clip(np.floor((dusuk - pl) / adim), 0, satir - 1).astype(int)
    r1 = np.clip(np.floor((yuksek - pl) / adim), 0, satir - 1).astype(int)
    pay = hacim / (r1 - r0 + 1)
    fark = np.zeros(satir + 1)
    np.add.at(fark, r0, pay)
    np.add.at(fark, r1 + 1, -pay)
    satirlar = np.cumsum(fark)[:satir]
    poc = int(np.argmax(satirlar))
    hedef = satirlar.sum() * va_yuzde / 100.0
    toplam = satirlar[poc]
    alt, ust = poc - 1, poc + 1
    while toplam < hedef and (alt >= 0 or ust < satir):
        va = satirlar[alt] if alt >= 0 else -1.0
        vu = satirlar[ust] if ust < satir else -1.0
        if va < 0 and vu < 0:
            break
        if vu >= va:
            toplam += vu
            ust += 1
        else:
            toplam += va
            alt -= 1
    return pl + (poc + 0.5) * adim, pl + ust * adim, pl + (alt + 1) * adim   # ust: son dahil satırın üstü (ust-1 dahil)


class VpDegerAlani(Strateji):
    """VP Value-Area Reversion & Breakout (1h daytrade).

    Kaynak: arsiv/strateji-sg/tv/pine/1OnkbAiE.pine.
    Kural: son `lookback` (20) günün (tamamlanmış UTC günleri; bugün hariç) hacim profili (60 satır) -> POC, değer alanı
    (%70) VAH/VAL. Fade short: önceki mumun yükseği VAH üstüne çıkmış, bu kapanış VAH altına dönmüş, kapanış < önceki kapanış ve
    RSI(14) >= 60 ise short; fade long ayna (VAL, RSI <= 40). Breakout long: kapanış VAH'ı yukarı keser ve hacim > 1.5*SMA20
    hacim; short: VAL aşağı. Stop: fade için min(low - 0.6*ATR, son pivot (5) dibi), breakout için min(VAH - 1.2*ATR,
    pivot dibi) (short aynası). Hedef: fade -> POC; breakout -> 1.8R. `mod`: "ikisi" | "fade" | "kirilim".
    Uyarlama: HVN bölge hedefleri ve çıplak POC hedefleri (kırılımın birincil hedefi) kaldırıldı, sabit 1.8R kullanıldı;
    haftalık profil seçeneği yok (yalnız günlük); fade hedefi (POC) fiyatın yanlış tarafındaysa sinyal atılır. Orijinal
    Pine'da VAH/VAL etiketleri satır yönü yüzünden tersti; düzeltildi (bkz. `_hacim_profili`). Profil yalnız bitmiş günlerden
    üretildiği için günün ilk mumunda bile geleceğe bakmaz. UTC gün sonu zorunlu çıkış (1h). Çıkış: stop/hedef + gün sonu.
    Eski proje sonucu: sonuç yok (envanterde boş).
    """
    ad = "dis__vp-deger-alani"
    stil = "daytrade"
    varsayilan_parametreler = {"lookback": 20, "satir": 60, "va_yuzde": 70.0, "hacim_k": 1.5, "hacim_n": 20,
                               "rsi_n": 14, "rsi_ob": 60.0, "rsi_os": 40.0, "pivot_n": 5, "atr_n": 14,
                               "stop_atr": 1.2, "hedef_r": 1.8, "mod": "ikisi", "short": True}
    parametre_izgarasi = {"lookback": [10, 20], "hacim_k": [1.2, 1.5, 2.0], "mod": ["ikisi", "fade", "kirilim"]}

    def cikis_var_mi(self) -> bool:
        return True

    def _seviyeler(self, mumlar, seans):
        p = self.parametreler
        y, d, h = (mumlar[c].to_numpy(dtype=float) for c in ("yuksek", "dusuk", "hacim"))
        gunler, baslangic = np.unique(seans, return_index=True)           # seans artan sıralıdır
        bitis = np.r_[baslangic[1:], len(seans)]
        poc = np.full(len(seans), np.nan)
        vah = np.full(len(seans), np.nan)
        val = np.full(len(seans), np.nan)
        for j in range(1, len(gunler)):
            j0 = max(0, j - p["lookback"])
            a, b = baslangic[j0], baslangic[j]                              # bugünden önceki son `lookback` gün
            pc, vh, vl = _hacim_profili(y[a:b], d[a:b], h[a:b], p["satir"], p["va_yuzde"])
            poc[baslangic[j]:bitis[j]], vah[baslangic[j]:bitis[j]], val[baslangic[j]:bitis[j]] = pc, vh, vl
        return (pd.Series(poc, index=mumlar.index), pd.Series(vah, index=mumlar.index),
                pd.Series(val, index=mumlar.index))

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k, h = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], mumlar["hacim"]
        seans = seans_kimligi(mumlar.index)
        poc, vah, val = self._seviyeler(mumlar, seans)
        r = g.rsi(k, p["rsi_n"])
        a = g.atr(y, d, k, p["atr_n"])
        hl = pd.Series(gd.pivot_dusuk(d, p["pivot_n"])).ffill()
        hh = pd.Series(gd.pivot_yuksek(y, p["pivot_n"])).ffill()
        hv = h > g.sma(h, p["hacim_n"]) * p["hacim_k"]
        var = poc.notna() & vah.notna() & val.notna() & r.notna() & a.notna()
        fade_s = var & (y.shift(1) > vah) & (k < vah) & (k < k.shift(1)) & (r >= p["rsi_ob"])
        fade_l = var & (d.shift(1) < val) & (k > val) & (k > k.shift(1)) & (r <= p["rsi_os"])
        kir_l = var & gd.kesis_yukari(k, vah) & hv
        kir_s = var & gd.kesis_asagi(k, val) & hv
        fade_ok, kir_ok = p["mod"] != "kirilim", p["mod"] != "fade"
        fade_l, fade_s, kir_l, kir_s = fade_l & fade_ok, fade_s & fade_ok, kir_l & kir_ok, kir_s & kir_ok
        st_kl = np.minimum(vah - p["stop_atr"] * a, hl.fillna(vah - p["stop_atr"] * a))
        st_fl = np.minimum(d - p["stop_atr"] * a * 0.5, hl.fillna(d - p["stop_atr"] * a * 0.5))
        st_ks = np.maximum(val + p["stop_atr"] * a, hh.fillna(val + p["stop_atr"] * a))
        st_fs = np.maximum(y + p["stop_atr"] * a * 0.5, hh.fillna(y + p["stop_atr"] * a * 0.5))
        stop_l = pd.Series(np.where(kir_l, st_kl, st_fl), index=k.index)
        stop_s = pd.Series(np.where(kir_s, st_ks, st_fs), index=k.index)
        long_c, short_c = (fade_l | kir_l), (fade_s | kir_s) & bool(p["short"])
        hedef_l = pd.Series(np.where(kir_l, k + p["hedef_r"] * (k - stop_l), poc), index=k.index)
        hedef_s = pd.Series(np.where(kir_s, k - p["hedef_r"] * (stop_s - k), poc), index=k.index)
        long_c &= hedef_l > k
        short_c &= hedef_s < k
        sig = cerceve(mumlar, long_c, short_c, stop_l, stop_s, hedef_l, hedef_s)
        return gun_sonu_uygula(sig)


class ObsHacimSoku(Strateji):
    """OBS Volume Spike Reaction Fade [NQ] (15m scalp, long+short).

    Kaynak: arsiv/strateji-sg/tv/pine/fmPC9fWd.pine.
    Kural: tepki mumu = hacim >= 3*SMA20(hacim), mum aralığı >= 3*önceki 30 mumun ortalama aralığı, mum aralığı >=
    min_aralik_atr*ATR ve son 3 mumda hacim şoku yok. Şok mumunu FADE et: düşüş mumu (kapanış < açılış) ise long,
    yükseliş mumu ise short. Stop = şok mumunun ucundan (long: low) 1.25*aralık ötede; hedef = mum ortası (aralığın %50'si).
    Uyarlama: orijinal NQ vadeli, 1 dakikalık, Chicago saatli (RTH/ETH, Asya/Londra/haber süzgeçleri, seans kenarı atlama,
    sabit "super fib" seviyeleri, nokta cinsinden min aralık=20) ve LİMİT emirleriyle (şok mumunun ucunun 0.25*aralık dışına
    limit alış/satış, 60 dk TTL) çalışır. 1L3A motoru limit emri vermediği için giriş sonraki mum açılışıdır ve yön zaten
    mum rengiyle belirlenir (iki limit yerine tek yön); nokta bazlı filtreler ATR'ye, seans süzgeçleri kaldırıldı. Hedefin
    yanlış tarafında kalan sinyaller atılır. 15m seçildi (scalp min 15m).
    Eski proje sonucu: KESİN ELEME (NQ 1-5 dk geçmişi yok, scalper).
    """
    ad = "dis__obs-hacim-soku"
    stil = "scalp"
    varsayilan_parametreler = {"hacim_k": 3.0, "hacim_n": 20, "aralik_k": 3.0, "aralik_n": 30, "min_aralik_atr": 1.5,
                               "atr_n": 14, "kume_n": 3, "stop_k": 1.25, "hedef_oran": 0.5, "short": True}
    parametre_izgarasi = {"hacim_k": [2.5, 3.0, 4.0], "aralik_k": [2.0, 3.0], "stop_k": [1.0, 1.25, 1.75]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a_, y, d, k, h = (mumlar[c] for c in ("acilis", "yuksek", "dusuk", "kapanis", "hacim"))
        ort_h = g.sma(h, p["hacim_n"])
        sok = h >= p["hacim_k"] * ort_h
        aralik = y - d
        onceki_ort = g.sma(aralik, p["aralik_n"]).shift(1)
        atr = g.atr(y, d, k, p["atr_n"])
        kume = pd.Series(False, index=k.index)
        for j in range(1, p["kume_n"] + 1):
            kume |= sok.shift(j, fill_value=False)
        tepki = sok & (aralik >= p["aralik_k"] * onceki_ort) & (aralik >= p["min_aralik_atr"] * atr) & ~kume & atr.notna()
        long_c = tepki & (k < a_)
        short_c = tepki & (k > a_) & bool(p["short"])
        hedef_l = d + p["hedef_oran"] * aralik
        hedef_s = y - p["hedef_oran"] * aralik
        long_c &= k < hedef_l
        short_c &= k > hedef_s
        return cerceve(mumlar, long_c, short_c, d - p["stop_k"] * aralik, y + p["stop_k"] * aralik, hedef_l, hedef_s)


class XauEmaAtr(Strateji):
    """XAU Clear EMA ATR Strategy TP SL Voice V6 (15m scalp, long+short).

    Kaynak: arsiv/strateji-sg/tv/pine/zudiHFjK.pine.
    Kural: EMA21 > EMA50 iken kapanış EMA21'i aşağıdan yukarı kesince long (EMA21 < EMA50 iken aşağı kesince short);
    stop = 1.5*ATR(14); orijinalde 5 hedef (0.7R, 1.2R, 1.8R, 2.5R, 3.5R; her biri pozisyonun %20'si). Zıt sinyal pozisyonu
    çevirir.
    Uyarlama: 5 kademeli çıkış TEK hedefe indirildi (hedef_r, varsayılan 1.8R = TP3, kademelerin ortası); zıt sinyalde çıkış
    (yönlü). Sesli uyarılar yok. 15m (envanter notu).
    Eski proje sonucu: KESİN ELEME (altın gün içi geçmişi yetersizdi; burada Binance XAU perp verisiyle yeniden test edilir).
    """
    ad = "dis__xau-ema-atr"
    stil = "scalp"
    varsayilan_parametreler = {"hizli": 21, "yavas": 50, "atr_n": 14, "stop_atr": 1.5, "hedef_r": 1.8, "short": True}
    parametre_izgarasi = {"hedef_r": [0.7, 1.2, 1.8, 2.5, 3.5], "stop_atr": [1.0, 1.5, 2.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ef, es = g.ema(k, p["hizli"]), g.ema(k, p["yavas"])
        al = (ef > es) & (k > ef) & (k.shift(1) <= ef.shift(1))
        sat = (ef < es) & (k < ef) & (k.shift(1) >= ef.shift(1))
        a = g.atr(y, d, k, p["atr_n"])
        sl, ss = k - p["stop_atr"] * a, k + p["stop_atr"] * a
        sig = cerceve(mumlar, al, sat & bool(p["short"]), sl, ss,
                      k + p["hedef_r"] * (k - sl), k - p["hedef_r"] * (ss - k))
        return gd.yonlu_cerceve(sig, sat, al)
