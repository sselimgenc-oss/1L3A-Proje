"""D1 grubu (dış TradingView): skor/bileşik göstergeli stratejiler.

Confluence Rank, günlük kapanış karşılaştırma, EMA şerit yelpazesi, çok faktörlü z-skor ve "Dual Engine"
(EMA-MACD skoru ve ortalamaya dönüş) stratejileri. Hepsi OHLCV tabanlı, nedensel.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.dis._gosterge_d1 import gunluk_kapanis, kur, yuzdelik_sira
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji


def _kenet(x):
    return x.clip(lower=0.0, upper=1.0)


class ConfluenceRank(Strateji):
    """dis__confluence-rank: 4h. Beş bileşenli 0-100 skor; skor 85'i yukarı geçince giriş, 35'in altına inince çıkış.

    Kaynak: arsiv/strateji-sg/tv/pine/LcA4mcE6.pine (Confluence Rank Trend Strategy [Jayadev Rana]).
    Skor (long): trend (kapanış>EMA233: 10 + EMA55>EMA233: 10) + momentum (RSI 50->70: 0->20) + verimlilik (net hareket /
    toplam yol, 0.40'ta tam puan, 20) + oynaklık rejimi (ATR yüzdelik sırası 20-85 arasında tam 20) + katılım (yükselen
    mumda göreli hacim; 20). Short aynası. Giriş: skor `giris` eşiğini aşağıdan yukarı keser. Çıkış: kendi yönünün skoru
    `cikis` altına iner. Stop = giriş ∓ iz_atr x ATR.
    Uyarlama: Pine'daki kapanıştan izlenen 3 ATR stop, motorun ATR izleyen stopuyla (k=3, tepe/dip bazlı) yaklaşıklanır;
    risk yüzdesine bağlı pozisyon boyutu alınmadı (motor boyutlandırır). Hacim yoksa katılım 10 puan sabit (orijinaldeki gibi).
    Eski sonuç: kaldı: PF 1.96, Sharpe 1.28 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/conf_rank.json).
    """
    ad = "dis__confluence-rank"
    stil = "swing"
    varsayilan_parametreler = {"hizli": 55, "yavas": 233, "rsi_periyot": 14, "er_periyot": 20, "er_tam": 0.40,
                               "yuzdelik_n": 200, "vol_alt": 20.0, "vol_ust": 85.0, "hacim_n": 20,
                               "giris": 85.0, "cikis": 35.0, "atr_periyot": 14, "iz_atr": 3.0, "short": True}
    parametre_izgarasi = {"giris": [75.0, 85.0, 90.0], "cikis": [25.0, 35.0, 45.0], "iz_atr": [2.0, 3.0, 4.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0)

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ef, es = g.ema(k, int(p["hizli"])), g.ema(k, int(p["yavas"]))
        rsi = g.rsi(k, int(p["rsi_periyot"]))
        en = int(p["er_periyot"])
        chg = k - k.shift(en)
        yol = k.diff().abs().rolling(en, min_periods=en).sum()
        er = (chg.abs() / yol.where(yol > 0)).fillna(0.0)
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        pr = yuzdelik_sira(atr, int(p["yuzdelik_n"])).fillna(50.0)
        vma = g.sma(mumlar["hacim"], int(p["hacim_n"]))
        var_h = vma.fillna(0.0) > 0
        rel = (mumlar["hacim"] / vma.where(vma > 0)).fillna(0.0)
        lo, hi = p["vol_alt"], p["vol_ust"]
        vol_reg = pd.Series(20.0, index=k.index)
        vol_reg = vol_reg.mask(pr < lo, 20.0 * pr / lo)
        vol_reg = vol_reg.mask(pr > hi, 20.0 * _kenet((100.0 - pr) / (100.0 - hi)))
        trend_l = 10.0 * (k > es) + 10.0 * (ef > es)
        trend_s = 10.0 * (k < es) + 10.0 * (ef < es)
        mom_l, mom_s = 20.0 * _kenet((rsi - 50) / 20), 20.0 * _kenet((50 - rsi) / 20)
        eff_l = (20.0 * _kenet(er / p["er_tam"])).where(chg > 0, 0.0)
        eff_s = (20.0 * _kenet(er / p["er_tam"])).where(chg < 0, 0.0)
        part_l = (20.0 * _kenet(rel - 0.5)).where(k > a, 0.0).where(var_h, 10.0)
        part_s = (20.0 * _kenet(rel - 0.5)).where(k < a, 0.0).where(var_h, 10.0)
        sk_l = (trend_l + mom_l + eff_l + vol_reg + part_l).fillna(0.0)
        sk_s = (trend_s + mom_s + eff_s + vol_reg + part_s).fillna(0.0)
        isin = pd.Series(np.arange(len(k)) > max(int(p["yavas"]), int(p["yuzdelik_n"])), index=k.index)
        g_e = p["giris"]
        long_ok = isin & (sk_l >= g_e) & (sk_l.shift(1) < g_e)
        short_ok = isin & (sk_s >= g_e) & (sk_s.shift(1) < g_e) & ~long_ok & bool(p["short"])
        sd = p["iz_atr"] * atr
        return kur(mumlar, long_ok, short_ok, k - sd, k + sd, cikis_l=sk_l < p["cikis"], cikis_s=sk_s < p["cikis"])


class GunlukKapanis(Strateji):
    """dis__gunluk-kapanis: günlük kapanış karşılaştırması. Dünkü kapanış önceki günden yüksekse LONG, düşükse SHORT.

    Kaynak: arsiv/strateji-sg/tv/pine/XK8XbDhT.pine (Daily Close Comparison Strategy by ChartArt).
    Kural: fark = (dün - evvelki gün)/evvelki gün; fark > esik -> "al" durumu, fark < -esik -> "sat" durumu, arası önceki durum.
    Hep piyasada: durum değişince pozisyon döner.
    Uyarlama (NEDENSELLEŞTİRME): Pine'da security(tickerid,'D', close) gün İÇİNDE oluşan günlük kapanışı da okur (repaint);
    burada yalnız TAMAMLANMIŞ son iki günün kapanışı kullanılır (htf.ust_zaman: değer ertesi gün 00:00 UTC'den itibaren).
    Orijinalde stop yok -> ATR stop (stop_atr) eklendi. 1h/4h verisiyle çalışır (günlük veride doğrudan kaydırma).
    Eski sonuç: kaldı: PF 0.84, Sharpe -0.10 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/gunluk_kapanis.json).
    """
    ad = "dis__gunluk-kapanis"
    stil = "swing"
    varsayilan_parametreler = {"esik": 0.0, "atr_periyot": 14, "stop_atr": 3.0, "short": True}
    parametre_izgarasi = {"esik": [0.0, 0.005, 0.01], "stop_atr": [2.0, 3.0, 4.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        gk = gunluk_kapanis(mumlar)
        fark = (gk["dun"] - gk["onceki"]) / gk["onceki"]
        durum = pd.Series(np.where(fark > p["esik"], 1.0, np.where(fark < -p["esik"], 0.0, np.nan)), index=k.index)
        durum = durum.where(fark.notna()).ffill()
        al, sat = durum == 1.0, durum == 0.0
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        sd = p["stop_atr"] * atr
        return kur(mumlar, al, sat & bool(p["short"]), k - sd, k + sd, cikis_l=sat, cikis_s=al)


class EmaSeritYelpaze(Strateji):
    """dis__ema-serit-yelpaze: 4h. Beş EMA (8,13,21,34,55) yelpazesi AÇILIRKEN RSI ve hacim süzgecinde giriş.

    Kaynak: arsiv/strateji-sg/tv_eleme_dali/pine/X0F9OE4L.pine (EMA Ribbon Fan Angle Strategy).
    Eğim = (EMA - EMA[5])/EMA[5]*100. Long: tüm eğimler > 0 ve e8 > e13 > e21 > e34 > e55 (azalan sıra), fanScore = eğim8 -
    eğim55 > giris_esik, RSI in (50, 70), hacim > ortalama. Short aynası (RSI in (30, 50)). Stop = ATR(14) x stop_atr,
    hedef = hedef_r x R. Çıkış: yelpaze sırası bozulur veya fanScore cikis_esik altına iner ("fan compression").
    Uyarlama: yok (yalnız risk-yüzdesi boyutlandırma motora bırakıldı).
    Eski sonuç: kaldı: PF 1.00, Sharpe 0.21 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/ribbon_fan.json).
    """
    ad = "dis__ema-serit-yelpaze"
    stil = "swing"
    varsayilan_parametreler = {"e1": 8, "e2": 13, "e3": 21, "e4": 34, "e5": 55, "egim_n": 5,
                               "giris_esik": 0.8, "cikis_esik": 0.2, "rsi_periyot": 14, "rsi_min": 50.0,
                               "rsi_maks": 70.0, "hacim_n": 20, "hacim_k": 1.0, "atr_periyot": 14,
                               "stop_atr": 2.0, "hedef_r": 2.0, "short": True}
    parametre_izgarasi = {"giris_esik": [0.5, 0.8, 1.2], "stop_atr": [1.5, 2.0, 3.0], "hedef_r": [1.5, 2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        em = [g.ema(k, int(p[f"e{i}"])) for i in range(1, 6)]
        n = int(p["egim_n"])
        sl = [(e - e.shift(n)) / e.shift(n) * 100.0 for e in em]
        poz = (sl[0] > 0) & (sl[1] > 0) & (sl[2] > 0) & (sl[3] > 0) & (sl[4] > 0)
        neg = (sl[0] < 0) & (sl[1] < 0) & (sl[2] < 0) & (sl[3] < 0) & (sl[4] < 0)
        art = (sl[0] > sl[1]) & (sl[1] > sl[2]) & (sl[2] > sl[3]) & (sl[3] > sl[4])
        azl = (sl[0] < sl[1]) & (sl[1] < sl[2]) & (sl[2] < sl[3]) & (sl[3] < sl[4])
        skor = sl[0] - sl[4]
        rsi = g.rsi(k, int(p["rsi_periyot"]))
        hok = mumlar["hacim"] > g.sma(mumlar["hacim"], int(p["hacim_n"])) * p["hacim_k"]
        long_ok = poz & art & (skor > p["giris_esik"]) & (rsi > p["rsi_min"]) & (rsi < p["rsi_maks"]) & hok
        short_ok = (neg & azl & (skor < -p["giris_esik"]) & (rsi < 100 - p["rsi_min"])
                    & (rsi > 100 - p["rsi_maks"]) & hok & bool(p["short"]))
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        sd = p["stop_atr"] * atr
        r = p["hedef_r"]
        return kur(mumlar, long_ok, short_ok, k - sd, k + sd, k + r * sd, k - r * sd,
                   cikis_l=(~art) | (skor < p["cikis_esik"]), cikis_s=(~azl) | (skor > -p["cikis_esik"]))


class ZSkorCokFaktor(Strateji):
    """dis__zskor-cok-faktor: 4h. ROC, RSI ve hacim z-skorlarının uyarlamalı bileşiği sıfırı keserse giriş.

    Kaynak: arsiv/strateji-sg/tv/pine/W67tJltC.pine (Multi-Factor Adaptive Z-Score Strategy).
    Bileşik = 0.4*z(ROC14) + 0.3*z(RSI14) + 0.3*z(göreli hacim) (z: 100 mumluk ortalama/standart sapma). ATR yüzdelik
    sırasına göre 2-15 arası değişen EMA ile yumuşatılır (oynak = kısa). mod="sifir": bileşik 0'ı yukarı keserse long, aşağı
    keserse short; mod="esik": -1.5'i yukarı / +1.5'i aşağı keserse (eşikten dönüş). Çıkış: bileşik 0'ı ters yönde keser.
    Stop = ATR x stop_atr. Diverjans bölümü orijinalde yalnız çizimdir, alınmadı. Risk-yüzdeli boyutlandırma motora bırakıldı.
    Eski sonuç: kaldı: PF 1.13, Sharpe 0.88 (arsiv/strateji-sg/tv_eleme_dali/sonuclar/zscore.json).
    """
    ad = "dis__zskor-cok-faktor"
    stil = "swing"
    varsayilan_parametreler = {"z_periyot": 100, "mom_n": 14, "rsi_n": 14, "hacim_n": 20, "w_fiyat": 0.4, "w_rsi": 0.3,
                               "w_hacim": 0.3, "atr_n": 14, "atr_sira_n": 100, "min_yum": 2, "maks_yum": 15,
                               "mod": "sifir", "esik": 1.5, "stop_atr": 2.0, "short": True}
    parametre_izgarasi = {"z_periyot": [60, 100, 150], "mod": ["sifir", "esik"], "stop_atr": [1.5, 2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def _z(s: pd.Series, n: int) -> pd.Series:
        m = s.rolling(n, min_periods=n).mean()
        sd = s.rolling(n, min_periods=n).std(ddof=0)
        return ((s - m) / sd.where(sd > 0)).where(sd > 0, 0.0).where(m.notna())

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        zn = int(p["z_periyot"])
        roc = (k - k.shift(int(p["mom_n"]))) / k.shift(int(p["mom_n"])) * 100.0
        rsi = g.rsi(k, int(p["rsi_n"]))
        hr = mumlar["hacim"] / g.sma(mumlar["hacim"], int(p["hacim_n"]))
        ws = (p["w_fiyat"] + p["w_rsi"] + p["w_hacim"]) or 1.0
        bil = (self._z(roc, zn) * p["w_fiyat"] + self._z(rsi, zn) * p["w_rsi"] + self._z(hr, zn) * p["w_hacim"]) / ws
        atr = g.atr(y, d, k, int(p["atr_n"]))
        sira = yuzdelik_sira(atr, int(p["atr_sira_n"]))
        dlen = (p["maks_yum"] - (p["maks_yum"] - p["min_yum"]) * (sira / 100.0)).round().clip(lower=1)
        alfa = (2.0 / (dlen + 1)).to_numpy()
        b = bil.to_numpy()
        out = np.full(len(b), np.nan)
        prev = np.nan
        for i in range(len(b)):
            a_i = alfa[i] if not np.isnan(alfa[i]) else 2.0 / (5 + 1)
            if np.isnan(prev):
                v = b[i]
            else:
                v = prev + a_i * (b[i] - prev)
            out[i] = v
            prev = v
        sm = pd.Series(out, index=k.index)
        if p["mod"] == "esik":
            up, dn = (sm > -p["esik"]) & (sm.shift(1) <= -p["esik"]), (sm < p["esik"]) & (sm.shift(1) >= p["esik"])
        else:
            up, dn = (sm > 0) & (sm.shift(1) <= 0), (sm < 0) & (sm.shift(1) >= 0)
        sd = p["stop_atr"] * atr
        c_l = (sm < 0) & (sm.shift(1) >= 0)
        c_s = (sm > 0) & (sm.shift(1) <= 0)
        return kur(mumlar, up, dn & bool(p["short"]), k - sd, k + sd, cikis_l=c_l, cikis_s=c_s)


# ----------------------------------------------------------------------------- Dual Engine (EMA MACD)
def _htf_gunluk(mumlar, ema_n: int):
    """Önceki TAMAMLANMIŞ günün kapanışı ve günlük EMA (htf.ust_zaman)."""
    return ust_zaman(mumlar, "1d", lambda u: pd.DataFrame({"kap": u["kapanis"], "ema": g.ema(u["kapanis"], ema_n)}))


class EmaMacdIkili(Strateji):
    """dis__ema-macd-ikili: 1h. "Dual Engine" EMA-MACD skor motoru: skor >= 5 olunca LONG (short parametreli).

    Kaynak: arsiv/strateji-sg/tv/pine/f9xLZqpF.pine (EMA MACD Forecast Predictor - Dual Engine). Tahmin (forecast) ve
    uyarı bölümleri orijinalde yalnız gösterimdir, alınmadı. Varsayılan "EMA MACD Only" modu kodlandı (kaynakta Auto =
    <=15m ortalamaya dönüş, daha uzunda bu mod; ortalamaya dönüş ayrı: dis__ema-macd-ortalamaya-donus).
    Skor (-10..+10): EMA dizilimi (e9>e21 ve kapanış>e50: ±2), kapanış>e200 (±1), MACD(12,26,9) çizgi/sinyal+histogram (±2),
    MACD kesişimi (±1), RSI14 >55/<45 (±1), ADX>=20 ve DI yönü (±1), hacimli renkli mum (±1), günlük kapanış vs günlük EMA50 (±1).
    Giriş: skor ilk kez >= 5; filtreler: kapanış>EMA200 ve günlük trend uyumu, ADX>=20, kapanış-EMA9 <= 2 ATR, RSI<72.
    Stop = 3 ATR, hedef = stop mesafesi x 0.3 (orijinal rewardRisk=0.3), zaman çıkışı 5 mum, ters güçlü skorda çıkış.
    Uyarlama: günlük (HTF) trend önceki tamamlanmış günden alınır (nedensel). Orijinal varsayılan yalnız long
    (allowShorts=False); `short=True` aynayı açar. Seans/gün filtreleri ve günlük zarar kilidi alınmadı. Gün sonu zorunlu çıkış.
    Eski sonuç: yok (envanterde sonuç kaydı yok).
    """
    ad = "dis__ema-macd-ikili"
    stil = "daytrade"
    varsayilan_parametreler = {"giris_skor": 5, "adx_min": 20.0, "uzama_atr": 2.0, "rsi_maks": 72.0, "rsi_min": 28.0,
                               "stop_atr": 3.0, "odul_risk": 0.3, "zaman_cikisi": 5, "htf_ema": 50,
                               "atr_periyot": 14, "short": False, "seans_saat": 0.0}
    parametre_izgarasi = {"giris_skor": [4, 5, 6], "stop_atr": [2.0, 3.0, 4.0], "odul_risk": [0.3, 1.0, 2.0]}

    def cikis_var_mi(self) -> bool:
        return True   # hedef + zaman + ters skor + gün sonu

    def sinyaller(self, mumlar):
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        e1, e2, e3, e5 = g.ema(k, 9), g.ema(k, 21), g.ema(k, 50), g.ema(k, 200)
        m = g.macd(k, 12, 26, 9)
        rsi = g.rsi(k, 14)
        dx = g.adx(y, d, k, 14)
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        hv = g.sma(mumlar["hacim"], 20)
        v_boga = (mumlar["hacim"] > hv) & (k > a)
        v_ayi = (mumlar["hacim"] > hv) & (k < a)
        htf = _htf_gunluk(mumlar, int(p["htf_ema"]))
        h_boga = htf["ema"].notna() & (htf["kap"] > htf["ema"])
        h_ayi = htf["ema"].notna() & (htf["kap"] < htf["ema"])

        def isaret(boga, ayi, w):
            return w * boga.astype(int) - w * ayi.astype(int)
        skor = (isaret((e1 > e2) & (k > e3), (e1 < e2) & (k < e3), 2) + isaret(k > e5, k < e5, 1)
                + isaret((m["macd"] > m["sinyal"]) & (m["histogram"] > 0), (m["macd"] < m["sinyal"]) & (m["histogram"] < 0), 2)
                + isaret((m["macd"] > m["sinyal"]) & (m["macd"].shift(1) <= m["sinyal"].shift(1)),
                         (m["macd"] < m["sinyal"]) & (m["macd"].shift(1) >= m["sinyal"].shift(1)), 1)
                + isaret(rsi > 55, rsi < 45, 1)
                + isaret((dx["adx"] >= 20) & (dx["arti_di"] > dx["eksi_di"]), (dx["adx"] >= 20) & (dx["eksi_di"] > dx["arti_di"]), 1)
                + isaret(v_boga, v_ayi, 1) + isaret(h_boga, h_ayi, 1))
        e = int(p["giris_skor"])
        al, sat = skor >= e, skor <= -e
        al_ilk, sat_ilk = al & ~al.shift(1, fill_value=False), sat & ~sat.shift(1, fill_value=False)
        adx_ok = dx["adx"] >= p["adx_min"]
        long_ok = (al_ilk & (k > e5) & (h_boga | htf["ema"].isna()) & adx_ok
                   & ((k - e1) <= atr * p["uzama_atr"]) & (rsi < p["rsi_maks"]))
        short_ok = (sat_ilk & (k < e5) & (h_ayi | htf["ema"].isna()) & adx_ok
                    & ((e1 - k) <= atr * p["uzama_atr"]) & (rsi > p["rsi_min"]) & bool(p["short"]))
        sd = p["stop_atr"] * atr
        r = p["odul_risk"]
        return kur(mumlar, long_ok, short_ok, k - sd, k + sd, k + r * sd, k - r * sd,
                   cikis_l=sat_ilk, cikis_s=al_ilk, gun_sonu=True, seans_saat=p["seans_saat"],
                   zaman_cikisi=int(p["zaman_cikisi"]))


class EmaMacdOrtalamayaDonus(Strateji):
    """dis__ema-macd-ortalamaya-donus: 15m. "Dual Engine" ortalamaya dönüş modu: RSI(2) aşırı ve fiyat EMA40'tan 0.5 ATR uzakta.

    Kaynak: arsiv/strateji-sg/tv/pine/f9xLZqpF.pine (EMA MACD Forecast Predictor - Dual Engine; <=15m için "Auto" modu).
    Kural: kapanış < EMA40 - 0.5 ATR ve RSI(2) < 15 -> LONG (kapanış > EMA40 + 0.5 ATR ve RSI(2) > 85 -> SHORT).
    Trend süzgeci (orijinalde açık): long için kapanış > EMA200 ve günlük kapanış > günlük EMA50; short aynası.
    Stop = 2 ATR, hedef = girişteki EMA40 (ortalama), zaman çıkışı 12 mum.
    Uyarlama: günlük trend önceki tamamlanmış günden (nedensel). Orijinal varsayılan yalnız long (allowShorts=False);
    `short=True` aynayı açar. Seans filtresi alınmadı. Scalp (15m): gün sonu zorunlu çıkış yok (zaman çıkışı 12 mum).
    Eski sonuç: yok (envanterde sonuç kaydı yok).
    """
    ad = "dis__ema-macd-ortalamaya-donus"
    stil = "scalp"
    varsayilan_parametreler = {"ort_n": 40, "rsi_n": 2, "al_seviye": 15.0, "sat_seviye": 85.0, "sapma_atr": 0.5,
                               "stop_atr": 2.0, "zaman_cikisi": 12, "htf_ema": 50, "atr_periyot": 14, "short": False}
    parametre_izgarasi = {"al_seviye": [10.0, 15.0, 25.0], "sapma_atr": [0.3, 0.5, 1.0], "stop_atr": [1.5, 2.0, 3.0]}

    def cikis_var_mi(self) -> bool:
        return True   # hedef (ortalama) + zaman

    def sinyaller(self, mumlar):
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ort = g.ema(k, int(p["ort_n"]))
        rsi = g.rsi(k, int(p["rsi_n"]))
        atr = g.atr(y, d, k, int(p["atr_periyot"]))
        e5 = g.ema(k, 200)
        htf = _htf_gunluk(mumlar, int(p["htf_ema"]))
        h_boga = htf["ema"].isna() | (htf["kap"] > htf["ema"])
        h_ayi = htf["ema"].isna() | (htf["kap"] < htf["ema"])
        long_ok = (k < ort - p["sapma_atr"] * atr) & (rsi < p["al_seviye"]) & (k > e5) & h_boga
        short_ok = (k > ort + p["sapma_atr"] * atr) & (rsi > p["sat_seviye"]) & (k < e5) & h_ayi & bool(p["short"])
        sd = p["stop_atr"] * atr
        return kur(mumlar, long_ok, short_ok, k - sd, k + sd, ort, ort, zaman_cikisi=int(p["zaman_cikisi"]))
