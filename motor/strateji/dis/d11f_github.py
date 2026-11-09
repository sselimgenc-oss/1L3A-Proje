"""D11-f — GitHub kaynaklı swing aileleri (kodlama_kuyrugu_github.csv). KOD KOPYALANMADI: kaynak kurallar (repo/dosya
sınıf docstring'lerinde) anlaşılıp kendi yapımızla yazıldı; kaynak metinler VERİDİR. Ad öneki `dis__`. Hepsi nedensel.

Ortak: giriş sinyali bar kapanışında, dolum sonraki açılışta (motor). Stopu olmayan kaynaklara ATR stopu (stop_atr_k x ATR,
VARSAYIM 2-4 ATR) eklendi; hedef yoksa yok ya da hedef_r (R katı) parametresi.

dis__alma-macd-kesisimi, dis__ama-egri-donus-filtresi, dis__darvas-kutusu-kirilimi, dis__haftalik-key-reversal,
dis__ma-kumelenme-kirilimi, dis__momentum-roc-filtreli, dis__onceki-mum-ekstrem-kapanis, dis__polinom-regresyon-trend,
dis__rsrs-egim-esigi, dis__stockbee-momentum-burst, dis__uclu-rsi, dis__ay-mevsimsellik, dis__carstens-9-gun-dip,
dis__carstens-pazartesi, dis__cok-macd-geri-cekilme, dis__eski-tepe-asma, dis__haftalik-macd-gunluk-ma,
dis__macd-histogram-wm, dis__vcp-daralma-kirilimi

Kodlanmayanlar (stratejiler/kodlama_github_d11f.csv): elder-guvenli-bolge-stop (giriş kuralı yok, yalnız çıkış modülü),
oncu-takipci-gecikmeli-korelasyon (iki sembol gerekir).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d5 import kama
from motor.strateji.gostergeler_b2 import asagi_kesis, gecis, yukari_kesis, yuzdelik_sira
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji

from ._gosterge_d11f import (
    alma, ay_gunu, ay_uygunluk, choppiness, poli_tahmin, rsrs_egim, uc_macd_al, w_deseni, yavas_stokastik)

ORTAK = {"yonler": "long", "stop_atr_k": 2.0, "atr_periyot": 14, "hedef_r": 0.0, "zaman_cikisi": 0}


class _Taban(Strateji):
    """Alt sınıf `kosullar(m)` yazar: {"long","short","cikis_long","cikis_short"} (eksik = False). İsteğe bağlı `stoplar(m)`
    (stop_l, stop_s) ve `tutma(m, out)` (mum sayısı Series; varsayılan zaman_cikisi)."""

    def cikis_var_mi(self) -> bool:
        return True

    def kosullar(self, m: pd.DataFrame) -> dict:
        raise NotImplementedError

    def stoplar(self, m):
        p = self.parametreler
        a = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_periyot"])) * p["stop_atr_k"]
        return m["kapanis"] - a, m["kapanis"] + a

    def tutma(self, m, out):
        z = int(self.parametreler.get("zaman_cikisi", 0))
        return pd.Series(float(z) if z > 0 else np.nan, index=m.index)

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        k = self.kosullar(m)
        idx = m.index
        bos = pd.Series(False, index=idx)

        def al(ad):
            s = k.get(ad)
            return bos if s is None else s.reindex(idx).fillna(False).astype(bool)

        yon = p["yonler"]
        long_ok = al("long") if yon in ("long", "ls") else bos
        short_ok = al("short") if yon in ("short", "ls") else bos
        sl, ss = self.stoplar(m)
        out = cerceve(m, long_ok, short_ok, sl, ss)
        r = float(p.get("hedef_r", 0.0))
        if r > 0:
            kap = m["kapanis"]
            gir = out["yon"] != 0
            risk = (kap - out["stop"]).abs()
            out.loc[gir, "hedef"] = (kap + out["yon"] * r * risk)[gir]
        out["cikis_long"] = al("cikis_long")
        out["cikis_short"] = al("cikis_short")
        tut = self.tutma(m, out)
        out["zaman_cikisi_mum"] = pd.Series(np.where(out["yon"] != 0, tut, np.nan), index=idx)
        return out


# ====================================================================================== 1
class AlmaMacdKesisimi(_Taban):
    """dis__alma-macd-kesisimi (swing, 1d) — kaynak: enzoampil/fastquant, examples/2020-10-26-user_defined_strategy.ipynb.
    Kural: kapanış ALMA(9, ofset 0.85, sigma 6) üstündeyken MACD çizgisi sinyal çizgisini yukarı keserse long; kapanış ALMA
    altına inince çık. Kaynakta short yok (yonler=ls aynalar). MACD(12,16,9) kaynak değeri. VARSAYIM: stop 2 ATR."""
    ad = "dis__alma-macd-kesisimi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "alma_n": 9, "alma_ofset": 0.85, "alma_sigma": 6.0,
                               "macd_hizli": 12, "macd_yavas": 16, "macd_sinyal": 9}
    parametre_izgarasi = {"alma_n": [9, 14, 21], "macd_yavas": [16, 26], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        a = alma(k, p["alma_n"], p["alma_ofset"], p["alma_sigma"])
        md = g.macd(k, int(p["macd_hizli"]), int(p["macd_yavas"]), int(p["macd_sinyal"]))
        yuk, asg = yukari_kesis(md["macd"], md["sinyal"]), asagi_kesis(md["macd"], md["sinyal"])
        return {"long": yuk & (k > a), "short": asg & (k < a), "cikis_long": k < a, "cikis_short": k > a}


# ====================================================================================== 2
class AmaEgriDonusFiltresi(_Taban):
    """dis__ama-egri-donus-filtresi (swing, 1d) — kaynak: fasiondog/hikyuu, hikyuu_cpp/hikyuu/trade_sys/signal/imp/
    SingleSignal.cpp ve SingleSignal2.cpp; hikyuu_hub sys/ama_fixed_count.
    Gösterge = Kaufman AMA(10,2,30). filtre = filtre_p (0.1) x son 20 barlık fark (diff) standart sapması.
    mod "tek" (SG_Single): AMA'nın 1, 2 ya da 3 bar öncesine göre artışı filtreyi aşarsa AL sinyali, düşüşü aşarsa SAT sinyali.
    mod "dip" (SG_Single2): AMA - önceki dip_n barın en düşüğü > filtre ise AL; önceki dip_n barın en yükseği - AMA > filtre ise SAT.
    AL sinyali yeni belirdiğinde long, SAT sinyali çıkış (yonler=ls ise short). VARSAYIM: dip_n=10, stop 3 ATR."""
    ad = "dis__ama-egri-donus-filtresi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "mod": "tek", "ama_n": 10, "ama_hizli": 2, "ama_yavas": 30,
                               "filtre_p": 0.1, "filtre_n": 20, "dip_n": 10}
    parametre_izgarasi = {"mod": ["tek", "dip"], "filtre_p": [0.05, 0.1, 0.2], "ama_n": [10, 20], "stop_atr_k": [2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        a = kama(m["kapanis"], int(p["ama_n"]), int(p["ama_hizli"]), int(p["ama_yavas"]))
        filtre = p["filtre_p"] * a.diff().rolling(int(p["filtre_n"]), min_periods=int(p["filtre_n"])).std()
        if p["mod"] == "tek":
            al = pd.concat([(a - a.shift(j)) > filtre for j in (1, 2, 3)], axis=1).any(axis=1)
            sat = pd.concat([(a.shift(j) - a) > filtre for j in (1, 2, 3)], axis=1).any(axis=1)
        else:
            n = int(p["dip_n"])
            al = (a - a.shift(1).rolling(n, min_periods=n).min()) > filtre
            sat = (a.shift(1).rolling(n, min_periods=n).max() - a) > filtre
        return {"long": gecis(al), "short": gecis(sat), "cikis_long": sat, "cikis_short": al}


# ====================================================================================== 3
class DarvasKutusuKirilimi(_Taban):
    """dis__darvas-kutusu-kirilimi (swing, 1d-4h) — kaynak: geraked/metatrader5, Indicators/DarvasBoxes.mq5.
    Kutu = en son ONAYLI pivot tepesi (üst) ve pivot dibi (alt); pivot_n mum sol ve sağ (güç 3), onay pivot_n mum gecikmeli.
    Yükseği önceki mumdaki kutu üstünü aşan ilk mum -> long; düşüğü kutu altını aşağı kıran ilk mum -> short (yonler=ls).
    Kaynakta stop/hedef yok: VARSAYIM stop_atr_k x ATR, iz süren stop 3 ATR (CikisAyarlari), karşı sinyal çıkış.
    'Yuvarlanma 1' (kaynak yumuşatma parametresi) kodlanmadı."""
    ad = "dis__darvas-kutusu-kirilimi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 2.5, "pivot_n": 3}
    parametre_izgarasi = {"pivot_n": [2, 3, 5], "stop_atr_k": [2.0, 3.0], "hedef_r": [0.0, 2.0, 3.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0)

    def kosullar(self, m):
        from motor.strateji.dis._gosterge_d9 import pivot_seviye
        n = int(self.parametreler["pivot_n"])
        ust = pivot_seviye(m["yuksek"], n, n, True)
        alt = pivot_seviye(m["dusuk"], n, n, False)
        gecerli = (ust > alt)
        yuk = gecis((m["yuksek"] > ust.shift(1)) & gecerli.shift(1, fill_value=False))
        asg = gecis((m["dusuk"] < alt.shift(1)) & gecerli.shift(1, fill_value=False))
        return {"long": yuk, "short": asg, "cikis_long": asg, "cikis_short": yuk}


# ====================================================================================== 5
class HaftalikKeyReversal(_Taban):
    """dis__haftalik-key-reversal (swing, 1w sinyal; işlem günlük) — kaynak: tradermonty/claude-trading-skills,
    skills/technical-analyst/references/contrarian-confirmation-checklist.md (Shapiro adım 3).
    Haftalık bar (htf.ust_zaman 1w, seanslı piyasa düzeltmeli; değer hafta kapandıktan sonraki Pazartesi'den itibaren).
    Aşağı key reversal (short): haftalık yüksek > önceki `pencere` haftanın yükseği VE haftalık kapanış < önceki haftanın dibi.
    Yukarı key reversal (long): ayna (haftalık düşük < önceki pencere haftanın düşüğü VE kapanış > önceki haftanın yükseği).
    COT 'kalabalık' koşulu yok (saf fiyat kuralı). Sinyal yeni haftanın ilk günlük mumunda bir kez. Kaynakta çıkış yok:
    VARSAYIM günlük ATR stopu + zaman_cikisi (gün, mum) çıkışı. Örneklem düşük."""
    ad = "dis__haftalik-key-reversal"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "pencere": 13, "zaman_cikisi": 20}
    parametre_izgarasi = {"pencere": [8, 13, 26], "stop_atr_k": [2.0, 3.0, 4.0], "zaman_cikisi": [10, 20, 40]}

    def kosullar(self, m):
        n = int(self.parametreler["pencere"])

        def haftalik(u):
            sat = (u["yuksek"] > u["yuksek"].shift(1).rolling(n, min_periods=n).max()) & (u["kapanis"] < u["dusuk"].shift(1))
            al = (u["dusuk"] < u["dusuk"].shift(1).rolling(n, min_periods=n).min()) & (u["kapanis"] > u["yuksek"].shift(1))
            gun = (u.index.tz_localize(None) if u.index.tz is not None else u.index).astype("datetime64[ns]").astype("int64")
            return pd.DataFrame({"sat": sat.astype(float), "al": al.astype(float), "hid": (gun // 86_400_000_000_000).astype(float)},
                                index=u.index)

        h = ust_zaman(m, "1w", haftalik)
        yeni = h["hid"] != h["hid"].shift(1)
        return {"long": (h["al"] == 1.0) & yeni, "short": (h["sat"] == 1.0) & yeni}


# ====================================================================================== 6
class MaKumelenmeKirilimi(_Taban):
    """dis__ma-kumelenme-kirilimi (swing, 1h-4h) — kaynak: chrisleekr/binance-trading-bot, docs/concepts/strategies/momentum.md
    (momentum:maCluster).
    SMA 20/50/100/200 en fazla `max_yayilim` (kapanışın oranı; (en yüksek - en düşük SMA)/kapanış) içinde toplanmışsa
    kümelenme. Önceki `kume_pencere` mumdan birinde kümelenme VE kapanış en yüksek SMA'yı aşağıdan yukarı kesti -> long.
    İsteğe bağlı: Choppiness(14) < choppiness_max (0 = kapalı), ATR/kapanış yüzdeliği (atr_yuzdelik_n=480 mum) <= atr_yuzdelik_max
    (1.0 = kapalı). Çıkış: 4 ATR iz süren stop (CikisAyarlari) ve başlangıç stopu stop_atr_k x ATR. Yalnız long (kaynak).
    VARSAYIM: kume_pencere=3; 'bir mum onay' kodlanmadı (sinyal zaten kapanış kesişiminde)."""
    ad = "dis__ma-kumelenme-kirilimi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 4.0, "max_yayilim": 0.01, "kume_pencere": 3,
                               "choppiness_max": 50.0, "atr_yuzdelik_n": 480, "atr_yuzdelik_max": 0.4}
    parametre_izgarasi = {"max_yayilim": [0.005, 0.01, 0.02], "choppiness_max": [0.0, 50.0, 62.0], "stop_atr_k": [3.0, 4.0, 5.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=4.0)

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        smalar = pd.concat([g.sma(k, n) for n in (20, 50, 100, 200)], axis=1)
        ust = smalar.max(axis=1, skipna=False)
        yayilim = (ust - smalar.min(axis=1, skipna=False)) / k
        kume = (yayilim <= p["max_yayilim"]).astype(float).where(yayilim.notna())
        kume_once = kume.shift(1).rolling(int(p["kume_pencere"]), min_periods=1).max() == 1.0
        kes = yukari_kesis(k, ust)
        ok = kume_once & kes
        if p["choppiness_max"] > 0:
            ok &= choppiness(m["yuksek"], m["dusuk"], k, 14) < p["choppiness_max"]
        if p["atr_yuzdelik_max"] < 1.0:
            a = g.atr(m["yuksek"], m["dusuk"], k, int(p["atr_periyot"])) / k
            ok &= yuzdelik_sira(a, int(p["atr_yuzdelik_n"])) <= p["atr_yuzdelik_max"]
        return {"long": ok}


# ====================================================================================== 7
class MomentumRocFiltreliUzunYonlu(_Taban):
    """dis__momentum-roc-filtreli — kaynak: whchien/ai-trader, ai_trader/backtesting/strategies/classic/momentum.py ve roc.py
    (ROCStochStrategy, ROCMAStrategy). Üç küçük varyant (mod), yalnız long.
      "momentum": Momentum(n) = kapanış - n bar önceki kapanış > 0 iken al (yeni belirince); kapanış SMA50 altına inince çık.
      "roc_stok": ROC(n) > 0 VE yavaş %K(14,3) < 20 -> al; ROC < 0 VE %K > 80 -> çık.
      "roc_ma":   ROC(n) > 0 iken SMA10 SMA30'u yukarı keserse al; ROC < 0 ya da SMA10 < SMA30 ise çık.
    n (roc_n; momentum modunda da periyot) kaynakta 14 / 12 / 12. VARSAYIM: stop 3 ATR, %K = ham %K'nın 3 SMA'sı."""
    ad = "dis__momentum-roc-filtreli"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "mod": "roc_stok", "roc_n": 12, "ma_cikis": 50}
    parametre_izgarasi = {"mod": ["momentum", "roc_stok", "roc_ma"], "roc_n": [8, 12, 20], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        n = int(p["roc_n"])
        roc = k / k.shift(n) - 1.0
        if p["mod"] == "momentum":
            return {"long": gecis(k - k.shift(n) > 0), "cikis_long": k < g.sma(k, int(p["ma_cikis"]))}
        if p["mod"] == "roc_stok":
            kk = g.stokastik(m["yuksek"], m["dusuk"], k, 14, 3)["d"]    # yavaş %K = ham %K'nın 3 SMA'sı
            return {"long": gecis((roc > 0) & (kk < 20.0)), "cikis_long": (roc < 0) & (kk > 80.0)}
        s10, s30 = g.sma(k, 10), g.sma(k, 30)
        return {"long": (roc > 0) & yukari_kesis(s10, s30), "cikis_long": (roc < 0) | (s10 < s30)}


# ====================================================================================== 8
class OncekiMumEkstremKapanis(_Taban):
    """dis__onceki-mum-ekstrem-kapanis — kaynak: github liste/notebook 'Dünkü dip altı kapanışta al, 3 çubuk tut, dünkü zirve
    üstü kapanışta short, 2 çubuk tut (PyBroker)'.
    Kapanış önceki mumun en düşüğünün altındaysa long, `tut_long` mum (3) tut; kapanış önceki mumun en yükseğinin üstündeyse
    short, `tut_short` mum (2) tut. Kaynaktaki limit emir fiyatı ve portföyün %25'i kodlanmadı (motor sonraki açılıştan
    girer; risk motor sınırlarıyla). VARSAYIM: stop 2 ATR (kaynakta stop yok)."""
    ad = "dis__onceki-mum-ekstrem-kapanis"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "tut_long": 3, "tut_short": 2}
    parametre_izgarasi = {"tut_long": [2, 3, 5], "tut_short": [1, 2, 3], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        k = m["kapanis"]
        return {"long": k < m["dusuk"].shift(1), "short": k > m["yuksek"].shift(1)}

    def tutma(self, m, out):
        p = self.parametreler
        return pd.Series(np.where(out["yon"] == 1, float(p["tut_long"]), float(p["tut_short"])), index=m.index)


# ====================================================================================== 9
class PolinomRegresyonTrend(_Taban):
    """dis__polinom-regresyon-trend (swing, 1d) — kaynak: TheSnowGuru/PyTrader..., Strategies/LinearRegression.py.
    Her mumda son `pencere` (252) kapanışa `derece` (3). derece polinom uydurulur, BİR ADIM ilerisi tahmin edilir (kayan pencere,
    nedensel; uç nokta kararsızlığı kaynakta da bilinen sorun). fark = (tahmin - kapanış)/kapanış; |fark| >= max_fark (%20)
    ise pozisyon yok (uç değer tahmini güvenilmez), aksi halde fark > min_fark long, fark < -min_fark short.
    Sinyal yeni belirince giriş; işaret ters dönünce / aralık dışına çıkınca çıkış. VARSAYIM: min_fark=0, stop 3 ATR."""
    ad = "dis__polinom-regresyon-trend"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "pencere": 252, "derece": 3,
                               "max_fark": 0.2, "min_fark": 0.0}
    parametre_izgarasi = {"pencere": [126, 189, 252], "derece": [2, 3], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        fark = poli_tahmin(k, int(p["pencere"]), int(p["derece"])) / k - 1.0
        ic = fark.abs() < p["max_fark"]
        yuk = ic & (fark > p["min_fark"])
        asg = ic & (fark < -p["min_fark"])
        return {"long": gecis(yuk), "short": gecis(asg), "cikis_long": ~yuk & fark.notna(), "cikis_short": ~asg & fark.notna()}


# ====================================================================================== 10
class RsrsEgimEsigi(_Taban):
    """dis__rsrs-egim-esigi (swing, 1d) — kaynak: whchien/ai-trader, strategies/classic/rsrs.py ve indicators.py (RSRS, NormRSRS);
    fasiondog/hikyuu RSRS_BETA. Eğim b: son n barda yüksek = a + b x düşük OLS eğimi.
    mod "ham": b > esik_al (0.8) ise al (yeni belirince), b < esik_cik (0.5) ise çık.
    mod "z": b'nin son z_n bardaki z-skoru kullanılır; esik_al None -> 0.7, esik_cik None -> -0.7 (standart RSRS eşikleri; VARSAYIM).
    Yalnız long, stop_atr_k x ATR (varsayım). Rotasyon (portföy) sürümü kodlanmadı (pf__rotasyon'a skor olarak eklenebilir)."""
    ad = "dis__rsrs-egim-esigi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "mod": "ham", "n": 20, "esik_al": None, "esik_cik": None, "z_n": 250}
    parametre_izgarasi = {"mod": ["ham", "z"], "n": [12, 20, 30], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        b = rsrs_egim(m["yuksek"], m["dusuk"], int(p["n"]))
        if p["mod"] == "z":
            zn = int(p["z_n"])
            b = (b - b.rolling(zn, min_periods=zn).mean()) / b.rolling(zn, min_periods=zn).std()
            al_e = 0.7 if p["esik_al"] is None else p["esik_al"]
            cik_e = -0.7 if p["esik_cik"] is None else p["esik_cik"]
        else:
            al_e = 0.8 if p["esik_al"] is None else p["esik_al"]
            cik_e = 0.5 if p["esik_cik"] is None else p["esik_cik"]
        return {"long": gecis(b > al_e), "cikis_long": b < cik_e}


# ====================================================================================== 11
class StockbeeMomentumBurst(_Taban):
    """dis__stockbee-momentum-burst (swing, 1d) — kaynak: tradermonty/claude-trading-skills, skills/stockbee-momentum-burst-screener/
    SKILL.md ve references/momentum_burst_methodology.md, entry_exit_rules.md.
    Tetik: mod "yuzde": kapanış/önceki kapanış - 1 >= burst (0.04); mod "atr" ($0.90 mutlak eşik yerine): kapanış - açılış >=
    burst_atr_k x ATR(önceki mum). Ek: hacim > önceki mum hacmi; önceki `taban_n` (3-20) mum 'taban': (en yüksek/en düşük - 1) <=
    taban_genislik (%15) ve ortalama (yüksek-düşük)/kapanış <= ort_aralik (%5); önceki 5 mumda tek günde <= -burst düşüş yok;
    kapanış tetik mumunun üst yarısında. Mutlak likidite tabanları (100k hacim, 5 USD fiyat) evrene özgü olduğu için atıldı.
    Stop = tetik mumunun dibi (risk en çok maks_risk=%10 ile sınırlı); çıkış: zaman_cikisi (3-5) mum sonra. Yalnız long."""
    ad = "dis__stockbee-momentum-burst"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "zaman_cikisi": 4, "mod": "yuzde", "burst": 0.04, "burst_atr_k": 1.5, "taban_n": 5,
                               "taban_genislik": 0.15, "ort_aralik": 0.05, "maks_risk": 0.10}
    parametre_izgarasi = {"burst": [0.03, 0.04, 0.05], "taban_n": [5, 10, 20], "zaman_cikisi": [3, 4, 5]}

    def stoplar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        sl = np.maximum(m["dusuk"], k * (1.0 - p["maks_risk"]))
        return sl, k * 2.0

    def kosullar(self, m):
        p = self.parametreler
        k, o, y, d, v = m["kapanis"], m["acilis"], m["yuksek"], m["dusuk"], m["hacim"]
        n = int(p["taban_n"])
        if p["mod"] == "atr":
            tetik = (k - o) >= p["burst_atr_k"] * g.atr(y, d, k, int(p["atr_periyot"])).shift(1)
        else:
            tetik = (k / k.shift(1) - 1.0) >= p["burst"]
        genislik = y.shift(1).rolling(n, min_periods=n).max() / d.shift(1).rolling(n, min_periods=n).min() - 1.0
        ort_ar = ((y - d) / k).shift(1).rolling(n, min_periods=n).mean()
        cokus_yok = k.pct_change().shift(1).rolling(5, min_periods=5).min() > -p["burst"]
        ok = tetik & (v > v.shift(1)) & (genislik <= p["taban_genislik"]) & (ort_ar <= p["ort_aralik"]) & cokus_yok \
            & (k >= d + 0.5 * (y - d))
        return {"long": ok}


# ====================================================================================== 12
class UcluRsi(_Taban):
    """dis__uclu-rsi — kaynak: whchien/ai-trader, strategies/classic/rsi.py (TripleRsiStrategy) ve indicators.py (TripleRSI).
    Al: RSI(uzun=120) > uzun_esik (55) VE RSI(orta=60) < orta_esik (75) VE RSI(kısa=20) son 3 mumda hep > kisa_esik (55) VE
    kısa RSI 2 mumda %2'den fazla yükselmiş (RSI/RSI[-2] - 1 > 0.02). Çıkış: kapanış SMA60 altında VE son giriş-sinyali
    olayından bu yana en az `min_bekleme` (60) mum geçmiş (kaynaktaki 'en az 60 gün tutulmuş' koşulunun durumsuz yaklaşığı:
    sinyal olayı pozisyon içindeyken tekrar oluşursa çıkış biraz gecikir). Yalnız long. VARSAYIM: stop 3 ATR."""
    ad = "dis__uclu-rsi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "uzun": 120, "orta": 60, "kisa": 20, "uzun_esik": 55.0,
                               "orta_esik": 75.0, "kisa_esik": 55.0, "yukselis": 0.02, "sma_n": 60, "min_bekleme": 60}
    parametre_izgarasi = {"uzun_esik": [50.0, 55.0, 60.0], "min_bekleme": [30, 60, 90], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        ru, ro, rk = g.rsi(k, int(p["uzun"])), g.rsi(k, int(p["orta"])), g.rsi(k, int(p["kisa"]))
        giris = (ru > p["uzun_esik"]) & (ro < p["orta_esik"]) & (rk.rolling(3, min_periods=3).min() > p["kisa_esik"]) \
            & ((rk / rk.shift(2) - 1.0) > p["yukselis"])
        olay = gecis(giris)
        # son olaydan bu yana geçen mum: olay mumunda 0
        sira = pd.Series(np.arange(len(k)), index=k.index, dtype=float)
        yas = sira - sira.where(olay).ffill()
        return {"long": olay, "cikis_long": (k < g.sma(k, int(p["sma_n"]))) & (yas >= p["min_bekleme"])}


# ====================================================================================== 13
class AyMevsimsellik(_Taban):
    """dis__ay-mevsimsellik (swing, GÜNLÜK mumlarla; kuyrukta 1mo) — kaynak: tradermonty/claude-trading-skills,
    skills/edge-candidate-agent/scripts/auto_detect_candidates.py (ay-yıl mevsimsel anomali). ARAŞTIRMA-ONLY: veri güdümlü.
    Her takvim ayı için AYNI ayın önceki yıllardaki aylık getirileri (ay sonu kapanış / önceki ay sonu kapanış - 1) YALNIZ GEÇMİŞ
    yıllardan hesaplanır (walk-forward; cari yıl hiç kullanılmaz). Örnek >= min_ornek (6), ortalama >= min_ort (%2.5) ve kazanma
    oranı >= min_kazanma (%60) ise o ay uygun; ayın İLK mumunda long, ayın `cikis_gunu`'ndan (takvim günü, varsayılan 28) itibaren
    çıkış (ay sonunu önceden bilmek gerekmesin diye takvim günü). Kaynak 'semboller o ayın adayı' diyor; tek sembol uyarlaması:
    bu sembolün kendi geçmişi. VARSAYIM: stop 3 ATR."""
    ad = "dis__ay-mevsimsellik"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "min_ornek": 6, "min_ort": 0.025, "min_kazanma": 0.6, "cikis_gunu": 28}
    parametre_izgarasi = {"min_ort": [0.015, 0.025, 0.035], "min_kazanma": [0.55, 0.6, 0.7], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        t = ay_uygunluk(m["kapanis"], int(p["min_ornek"]), p["min_ort"], p["min_kazanma"])
        return {"long": t["uygun"] & t["yeni_ay"], "cikis_long": ay_gunu(m.index) >= int(p["cikis_gunu"])}


# ====================================================================================== 14
class Carstens9GunDip(_Taban):
    """dis__carstens-9-gun-dip — kaynak: TheSnowGuru/PyTrader..., Strategies/Carstens_Illustration7.py (Carstens kitap örneği).
    Long: ATR(1) (günün gerçek aralığı) > ATR(9) (aralık genişlemesi) VE kapanış son `dip_n` (9) kapanışın en düşüğüne eşit/altında.
    Short: aynı oynaklık şartı ve kapanış son dip_n kapanışın en yükseğinde. `zaman_cikisi` (4) mum tut. Kaynaktaki İKİNCİ PİYASA
    teyidi (çapraz-sembol) tek grafik motorda YOK: kodlanmadı -> bu, kuralın teyitsiz yaklaşığıdır (ters/dönüş yönlü).
    VARSAYIM: kaynakta stop yok, stop 3 ATR."""
    ad = "dis__carstens-9-gun-dip"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "zaman_cikisi": 4, "dip_n": 9, "atr_uzun": 9}
    parametre_izgarasi = {"dip_n": [5, 9, 13], "zaman_cikisi": [3, 4, 6], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        n = int(p["dip_n"])
        gen = g.gercek_aralik(m["yuksek"], m["dusuk"], k) > g.atr(m["yuksek"], m["dusuk"], k, int(p["atr_uzun"]))
        return {"long": gen & (k <= k.rolling(n, min_periods=n).min()), "short": gen & (k >= k.rolling(n, min_periods=n).max())}


# ====================================================================================== 15
class CarstensPazartesi(_Taban):
    """dis__carstens-pazartesi — kaynak: TheSnowGuru/PyTrader..., Strategies/Carstens_Illustration3.py (Carstens kitap örneği).
    Pazartesi işlemi için sinyal bir önceki mumun kapanışında kurulur (sinyal_gunu=4: Cuma kapanışı; Quantiacs'ta Pazartesi
    sabahı son bilinen bar Cuma'dır). Koşul: son 4 kapanışın aralığı (en yüksek - en düşük) < aralik_k x ATR(4) VE son kapanış
    bir öncekinden DÜŞÜK -> long; YÜKSEK -> short (ters/dönüş yönlü). `zaman_cikisi` (1) mum sonra çıkış (kaynakta ertesi gün).
    Kripto (7/24) için sinyal_gunu=4 Cumartesi işlemi olur; seanslı piyasada Pazartesi. VARSAYIM: aralik_k=1.0, stop 2 ATR."""
    ad = "dis__carstens-pazartesi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "zaman_cikisi": 1, "sinyal_gunu": 4, "n": 4, "aralik_k": 1.0}
    parametre_izgarasi = {"aralik_k": [0.75, 1.0, 1.5], "zaman_cikisi": [1, 2, 3], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        n = int(p["n"])
        aralik = k.rolling(n, min_periods=n).max() - k.rolling(n, min_periods=n).min()
        dar = aralik < p["aralik_k"] * g.atr(m["yuksek"], m["dusuk"], k, n)
        gun = pd.Series(m.index.dayofweek, index=m.index) == int(p["sinyal_gunu"])
        return {"long": dar & gun & (k < k.shift(1)), "short": dar & gun & (k > k.shift(1))}


# ====================================================================================== 16
class CokMacdGeriCekilme(_Taban):
    """dis__cok-macd-geri-cekilme (swing, 3h-4h) — kaynak: geraked/metatrader5, Experts/2MACDSTO.mq5 ve Experts/3MACD.mq5.
    Yalnız saf giriş/SL/TP kuralı; kaynaktaki grid (hacim çarpanlı kademe ekleme) ve stopsuz ayar KODLANMADI.
    mod "2macdsto": MACD1(13,21) ve MACD2(34,144) ana çizgileri: 2 mum önce MACD2>0 ve MACD1<0 (üst trendde geri çekilme), önceki
    mumda yavaş %K(7,3,3) < 20 ve %K <= %D idi, bu mumda %K, %D'yi yukarı kesti -> long. Short ayna (MACD2<0, MACD1>0, %K>80).
    mod "3macd": MACD1(5,8), MACD2(13,21), MACD3(34,144); pencere (32) mum içinde kaynağın A/B desenleri (MACD3>0 ve MACD2 geri
    çekilme dibi, öncesinde MACD1 sıfır geçişi ve MACD2 tepesi ...). ters=True: kaynağın 'Reverse' ayarı (sinyal yönünü çevirir).
    SL: son stop_n (7) mumun dibi/zirvesi -/+ 0.1 ATR, en çok 5 ATR risk; hedef hedef_r x R (2macdsto 1, 3macd 2)."""
    ad = "dis__cok-macd-geri-cekilme"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "mod": "2macdsto", "ters": False, "hedef_r": 1.0, "stop_n": 7,
                               "pencere": 32}
    parametre_izgarasi = {"mod": ["2macdsto", "3macd"], "ters": [False, True], "hedef_r": [1.0, 1.5, 2.0], "stop_n": [7, 10]}

    def stoplar(self, m):
        from motor.strateji.gostergeler_b2 import swing_stop
        p = self.parametreler
        a = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_periyot"]))
        return swing_stop(m["yuksek"], m["dusuk"], m["kapanis"], a, int(p["stop_n"]), 0.1, 5.0)

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        if p["mod"] == "2macdsto":
            m1 = g.macd(k, 13, 21, 9)["macd"]
            m2 = g.macd(k, 34, 144, 9)["macd"]
            st = yavas_stokastik(m["yuksek"], m["dusuk"], k, 7, 3, 3)
            kk, dd = st["k"], st["d"]
            al = (m2.shift(2) > 0) & (m1.shift(2) < 0) & (kk.shift(1) < 20) & (kk.shift(1) <= dd.shift(1)) & (kk > dd)
            sat = (m2.shift(2) < 0) & (m1.shift(2) > 0) & (kk.shift(1) > 80) & (kk.shift(1) >= dd.shift(1)) & (kk < dd)
        else:
            a1 = g.macd(k, 5, 8, 9)["macd"].to_numpy()
            a2 = g.macd(k, 13, 21, 9)["macd"].to_numpy()
            a3 = g.macd(k, 34, 144, 9)["macd"].to_numpy()
            w = int(p["pencere"])
            al = pd.Series(uc_macd_al(a1, a2, a3, w), index=m.index)
            sat = pd.Series(uc_macd_al(-a1, -a2, -a3, w), index=m.index)
        if p["ters"]:
            al, sat = sat, al
        return {"long": al, "short": sat}


# ====================================================================================== 17
class EskiTepeAsma(_Taban):
    """dis__eski-tepe-asma — kaynak: whchien/ai-trader, strategies/classic/double_top.py ve indicators.py (DoubleTop). Adı 'Double Top'
    ama aslında eski tepeyi geri çekilme sonrası yukarı kıran bir boğa kırılımıdır.
    Tepe = `tepe_min` (30) ile `tepe_max` (55) mum önceki aralıktaki en yüksek kapanış. Sonrasında en az geri_cekilme (%5) düşüş
    (son tepe_min mumun [önceki mumlar] en düşük kapanışı <= tepe x (1 - geri_cekilme); basitleştirme). Kapanış tepeyi aşıyor, 60 mumun
    en yükseğinin %2 (yakin) içinde, SMA60 ve SMA120 üstünde, kısa hacim ortalaması (5) > uzun (20) ise long (yeni belirince).
    Çıkış: `zaman_cikisi` (30) mum veya kapanış SMA60 altı. Yalnız long. VARSAYIM: stop 3 ATR."""
    ad = "dis__eski-tepe-asma"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "zaman_cikisi": 30, "tepe_min": 30, "tepe_max": 55,
                               "geri_cekilme": 0.05, "yakin": 0.02}
    parametre_izgarasi = {"geri_cekilme": [0.03, 0.05, 0.08], "zaman_cikisi": [20, 30, 45], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, v = m["kapanis"], m["hacim"]
        a, b = int(p["tepe_min"]), int(p["tepe_max"])
        tepe = k.shift(a).rolling(b - a + 1, min_periods=b - a + 1).max()
        dip = k.shift(1).rolling(a, min_periods=a).min()
        ok = (dip <= tepe * (1.0 - p["geri_cekilme"])) & (k > tepe) & (k >= (1.0 - p["yakin"]) * k.rolling(60, min_periods=60).max()) \
            & (k > g.sma(k, 60)) & (k > g.sma(k, 120)) & (g.sma(v, 5) > g.sma(v, 20))
        return {"long": gecis(ok), "cikis_long": k < g.sma(k, 60)}


# ====================================================================================== 18
class HaftalikMacdGunlukMa(_Taban):
    """dis__haftalik-macd-gunluk-ma — kaynak: fasiondog/hikyuu, hikyuu/examples/notebook/en/Demo/Demo1.ipynb ve Demo2.ipynb.
    Haftalık MACD(12,26,9) (htf.ust_zaman 1w): geçerlilik = DIF > DEA. giris_mod "kesisim" (Demo1): DIF'in DEA'yı yukarı kestiği
    haftadan sonraki ilk günlük mumda long; "gecerlilik" (Demo2): haftalık geçerliyken günlük EMA12 EMA26'yı yukarı kesince long.
    cikis_mod "ma": günlük kapanış SMA(ma_n=20) altına inince; "ema": günlük EMA12 < EMA26 (ölüm çaprazı). Her iki modda
    haftalık geçerlilik bitince tam çıkış. KAYNAK KISMİ POZİSYON (nakdin %30-50'si; çıkışta yarısını sat, altın çaprazda geri al)
    MODELLENMEDİ: tek tam pozisyon, risk motor sınırı %1; kısmi/geri alım ekleme sayıldığı için kodlanmadı. Yalnız long.
    VARSAYIM: stop 3 ATR."""
    ad = "dis__haftalik-macd-gunluk-ma"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "giris_mod": "kesisim", "cikis_mod": "ma", "ma_n": 20}
    parametre_izgarasi = {"giris_mod": ["kesisim", "gecerlilik"], "cikis_mod": ["ma", "ema"], "ma_n": [20, 30], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]

        def haftalik(u):
            md = g.macd(u["kapanis"], 12, 26, 9)
            gec = (md["macd"] > md["sinyal"]) & md["sinyal"].notna()
            cap = gec & ~gec.shift(1, fill_value=False)
            gun = (u.index.tz_localize(None) if u.index.tz is not None else u.index).astype("datetime64[ns]").astype("int64")
            return pd.DataFrame({"gec": gec.astype(float), "cap": cap.astype(float), "hid": (gun // 86_400_000_000_000).astype(float)},
                                index=u.index)

        h = ust_zaman(m, "1w", haftalik)
        gecerli = h["gec"] == 1.0
        yeni = h["hid"] != h["hid"].shift(1)
        e12, e26 = g.ema(k, 12), g.ema(k, 26)
        if p["giris_mod"] == "kesisim":
            giris = (h["cap"] == 1.0) & yeni
        else:
            giris = gecerli & yukari_kesis(e12, e26)
        cik = (k < g.sma(k, int(p["ma_n"]))) if p["cikis_mod"] == "ma" else (e12 < e26)
        return {"long": giris, "cikis_long": cik | (h["gec"] == 0.0)}


# ====================================================================================== 19
class MacdHistogramWm(_Taban):
    """dis__macd-histogram-wm (swing, 1h-1d) — kaynak: Drakkar-Software/OctoBot, packages/tentacles/Evaluator/TA/momentum_evaluator/
    momentum.py (MACDMomentumEvaluator) ve Evaluator/Util/pattern_analysis/pattern_analysis.py. Kaynak sürekli skor üretir; biz
    ölçülebilir bir giriş kuralına çevirdik.
    Tanım: MACD(12,26,9) histogramının sıfır geçişleri arasındaki bir negatif dilimde İKİ DİP (yerel minimum; 1 mum gecikmeli
    onay) = W (alım); pozitif dilimde iki tepe = M (satım). Koşul: iki dip arasında histogram en az min_sicrama x |ilk dip| yükselmiş
    (dilimden çıkmadan) ve ikinci dip birinciden tol oranından fazla derin değil (yeni >= eski x (1 + tol)). Onay anında giriş.
    Çıkış: long için histogram pozitifte ilk düşüşe geçince; short için negatifte ilk yükselişe geçince. VARSAYIM: stop 3 ATR;
    tol ve min_sicrama (kaynakta belirsiz) parametre."""
    ad = "dis__macd-histogram-wm"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "stop_atr_k": 3.0, "hizli": 12, "yavas": 26, "sinyal": 9, "tol": 0.2,
                               "min_sicrama": 0.25}
    parametre_izgarasi = {"tol": [0.0, 0.2, 0.5], "min_sicrama": [0.1, 0.25, 0.5], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        h = g.macd(m["kapanis"], int(p["hizli"]), int(p["yavas"]), int(p["sinyal"]))["histogram"]
        return {"long": w_deseni(h, p["tol"], p["min_sicrama"]), "short": w_deseni(-h, p["tol"], p["min_sicrama"]),
                "cikis_long": (h > 0) & (h < h.shift(1)), "cikis_short": (h < 0) & (h > h.shift(1))}


# ====================================================================================== 21
class VcpDaralmaKirilimi(_Taban):
    """dis__vcp-daralma-kirilimi — kaynak: whchien/ai-trader, strategies/classic/vcp.py (VCPPattern) ve risk_averse.py.
    mod "vcp": son 5 mumun birinde hem hacim (SMA10/SMA60) hem fiyat std (10/60) oranı < daralma (0.7); kapanış 100 mumun en yüksek
    kapanışı (yeni belirince); hacim > 0.8 x SMA20(hacim); kapanış SMA250 üstünde; son 20 mumun dibi > 100 mum zirvesinin %70'i.
    (günlük işlem değeri > 2 milyon evrene özgü: atıldı.) Çıkış: kapanış SMA60 altı.
    mod "risk_averse": 4 koşul: ortalama mum oynaklığı ((yüksek-düşük)/kapanış, 20) < %8; son 5 mumda 100 mum zirvesi; hacim koşulu
    (mutlak 100k yerine SMA5(hacim) > SMA20(hacim); VARSAYIM); 60 mumluk aralık oranı (1 - en düşük/en yüksek) < 0.30. Hepsi
    doğruysa al (yeni belirince); en az 2 koşul bozulunca çık. Yalnız long. VARSAYIM: stop 3 ATR."""
    ad = "dis__vcp-daralma-kirilimi"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 3.0, "mod": "vcp", "daralma": 0.7, "zirve_n": 100, "trend_n": 250}
    parametre_izgarasi = {"mod": ["vcp", "risk_averse"], "daralma": [0.6, 0.7, 0.8], "stop_atr_k": [2.0, 3.0, 4.0]}

    def kosullar(self, m):
        p = self.parametreler
        k, y, d, v = m["kapanis"], m["yuksek"], m["dusuk"], m["hacim"]
        zn = int(p["zirve_n"])
        zirve = k.rolling(zn, min_periods=zn).max()
        if p["mod"] == "vcp":
            hv = g.sma(v, 10) / g.sma(v, 60)
            pv = k.rolling(10, min_periods=10).std() / k.rolling(60, min_periods=60).std()
            dar = ((hv < p["daralma"]) & (pv < p["daralma"])).astype(float).where(hv.notna() & pv.notna())
            dar5 = dar.rolling(5, min_periods=1).max() == 1.0
            ok = dar5 & (k >= zirve) & (v > 0.8 * g.sma(v, 20)) & (k > g.sma(k, int(p["trend_n"]))) \
                & (d.rolling(20, min_periods=20).min() > 0.7 * zirve)
            return {"long": gecis(ok), "cikis_long": k < g.sma(k, 60)}
        c1 = ((y - d) / k).rolling(20, min_periods=20).mean() < 0.08
        c2 = (k >= zirve).astype(float).where(zirve.notna()).rolling(5, min_periods=1).max() == 1.0
        c3 = g.sma(v, 5) > g.sma(v, 20)
        c4 = (1.0 - d.rolling(60, min_periods=60).min() / y.rolling(60, min_periods=60).max()) < 0.30
        bozuk = (~c1).astype(int) + (~c2).astype(int) + (~c3).astype(int) + (~c4).astype(int)
        gecerli = zirve.notna() & c4.notna()
        return {"long": gecis(c1 & c2 & c3 & c4), "cikis_long": (bozuk >= 2) & gecerli}
