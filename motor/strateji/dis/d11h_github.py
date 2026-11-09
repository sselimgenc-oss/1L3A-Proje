"""D11-H — GitHub kaynaklı 20 daytrade ailesinden 19'unun KODU (1'i kodlanmadı: bkz. stratejiler/kodlama_github_d11h.csv).
KOD KOPYALANMADI: kaynak repolardaki kural özetleri VERİDİR; kurallar kendi yapımızla sıfırdan yazıldı. Kaynak repo+dosya her
sınıfın docstring'inde. Hepsi nedensel (lookahead yok); sinyal bar kapanışında, dolum sonraki açılışta (motor).

Ortak uyarlamalar
  * Mutlak eşikler (fiyat birimli MACD/histogram, pip) ATR veya yüzdeye çevrildi; her sınıfta "VARSAYIM" olarak yazılı.
  * Stopu olmayan kaynaklara ATR stopu (stop_atr_k x ATR) ve 2R hedef eklendi (varsayım). Martingale/ekleme/DCA kodlanmadı.
  * Üst zaman dilimi değerleri htf.ust_zaman ile (yalnız kapanmış üst mumlar).

dis__cok-gosterge-teyit, dis__osilator-esik-and, dis__fraktal-ok-girisi, dis__gosterge-egim-esik, dis__hacim-govde-patlamasi,
dis__jake-ppo-vosc, dis__klinger-skoru, dis__linreg-mum-teyit, dis__ma-gunluk-pivot, dis__macd-hist-esik-onay,
dis__macd-seviye-mtf, dis__nw-zarf-rsi, dis__parabolik-ilk-kirmizi-short, dis__ppo-tsi-uo-esik, dis__spinning-top-rsi,
dis__ust-tf-ma-yon-kesisim, dis__vwap-basarisizlik-short, dis__x2-rsi-mtf, dis__zigzag-bacak
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.daytrade._ortak import onceki_seans_hlc, seans_kimligi
from motor.strateji.dis._gosterge_d2 import stoch_rsi
from motor.strateji.dis._gosterge_d3 import mfi
from motor.strateji.dis._gosterge_d10e import ut_bot
from motor.strateji.dis._gosterge_d1 import linreg
from motor.strateji.gostergeler_b2 import asagi_kesis, cci, gecis, hacim_osilatoru, yukari_kesis
from motor.strateji.htf import ust_zaman
from motor.strateji.pivotlar import fraktal_pivotlar, zigzag_pivotlar
from motor.strateji.temel import Strateji

from ._gosterge_d11h import (
    GOSTERGELER, MERKEZ, YONSUZ, gosterge_serisi, klinger, nw_zarf, parabolik_tetik, ppo, taban_cerceve, tsi, ultimate,
    vwap_basarisizlik_sinyali)

_ORTAK = {"yonler": "long", "stop_atr_k": 2.0, "atr_periyot": 14, "hedef_r": 2.0, "hedef_yuzde": 0.0,
          "zaman_cikisi": 0, "gun_sonu": 0}


class _Taban(Strateji):
    """Alt sınıf `kosullar(m)` yazar: {long, short, cikis_long, cikis_short, [stop_long, stop_short]}."""

    def kosullar(self, m: pd.DataFrame) -> dict:
        raise NotImplementedError

    def cikis_var_mi(self) -> bool:
        return True       # stop + (R/yüzde) hedef ve/veya cikis_long / cikis_short sinyali her zaman var

    def sinyaller(self, m: pd.DataFrame) -> pd.DataFrame:
        return taban_cerceve(m, self.parametreler, self.kosullar(m))


def _bos(m):
    return pd.Series(False, index=m.index)


# =============================================================================== 1
class CokGostergeTeyit(_Taban):
    """dis__cok-gosterge-teyit (daytrade, 1h) — ailesi: cok-gosterge-ayni-yon-teyidi.
    Kaynak: Gekko-Strategies (xFFFFF) `bestone` ailesi, `L1-Scalping`, `tulip-multi-strat` (kural özeti; kod kopyalanmadı).
    Kural (DURUM koşulu, durumun ilk gerçekleştiği mumda giriş): EMA(hizli) > EMA(yavas) VE Stokastik K > D VE MACD(12,26,9)
    ana çizgisi > 0 VE RSI > rsi_esik VE (adx_min > 0 ise) ADX > adx_min -> long. Short aynası (RSI < 100 - rsi_esik, EMA hızlı < yavaş,
    K < D, MACD < 0). Çıkış: EMA hızlı/yavaş ters sıralanırsa. Stop 2 ATR, hedef 2R.
    VARSAYIM: kaynak eşikleri (RSI 70/30, ADX 24.52) genetik algoritmayla bulunmuş kırılgan değerler; varsayılan RSI 55, ızgara
    50/55/70. L1-Scalping'in '3 MACD histogramı + EMA21>34>...>144 dizilimi' varyantı kodlanmadı (dizilim için dis__ema-serit-yelpaze)."""
    ad = "dis__cok-gosterge-teyit"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "ema_hizli": 9, "ema_yavas": 21, "stok_n": 14, "stok_d": 3,
                               "rsi_n": 14, "rsi_esik": 55.0, "adx_min": 0.0}
    parametre_izgarasi = {"ema_hizli": [5, 9, 13], "rsi_esik": [50.0, 55.0, 70.0], "adx_min": [0.0, 20.0, 25.0]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        eh, ey = g.ema(k, int(p["ema_hizli"])), g.ema(k, int(p["ema_yavas"]))
        st = g.stokastik(y, d, k, int(p["stok_n"]), int(p["stok_d"]))
        mc = g.macd(k)["macd"]
        r = g.rsi(k, int(p["rsi_n"]))
        adx_ok = pd.Series(True, index=m.index)
        if p["adx_min"] > 0:
            adx_ok = g.adx(y, d, k, 14)["adx"] > p["adx_min"]
        long_d = (eh > ey) & (st["k"] > st["d"]) & (mc > 0) & (r > p["rsi_esik"]) & adx_ok
        short_d = (eh < ey) & (st["k"] < st["d"]) & (mc < 0) & (r < 100.0 - p["rsi_esik"]) & adx_ok
        return {"long": gecis(long_d), "short": gecis(short_d), "cikis_long": eh < ey, "cikis_short": eh > ey}


# =============================================================================== 2
class OsilatorEsikAnd(_Taban):
    """dis__osilator-esik-and (daytrade, 1h) — ailesi: cok-osilator-esik-and.
    Kaynak: Gekko-Strategies (xFFFFF) `tulip-multi-custom.js` (kural özeti; kod kopyalanmadı; özet CCI/ADX eşiklerinde kesikti, kaynak
    dosya özeti: CCI<-150, ADX<24.52, ROC<0).
    Kural: AÇIK filtrelerin HEPSİ aynı anda doğruysa (durumun ilk mumunda) giriş. Long: Stokastik (stok_n, yavaş K=stok_k, D=stok_d)
    K ve D < stok_esik VE K >= D; RSI(rsi_n) < rsi_esik; StochRSI K < srsi_esik; opsiyonel (bayrak=1): CCI < -cci_esik, ADX < adx_esik
    (düşük ADX = yatay piyasa), ROC(roc_n) < 0. Short aynası (100 - eşik; CCI > +cci_esik; ROC > 0). Bayraklar: kullan_stok,
    kullan_rsi, kullan_srsi, kullan_cci, kullan_adx, kullan_roc. Çıkış: RSI 50'yi karşı yöne keserse; stop 2 ATR, hedef 1.5R.
    VARSAYIM: 'SMA sapması azalan değil' ve MACD trend filtreleri kodlanmadı; varsayılan açık filtreler: stok+rsi+srsi (kaynağın
    örnek eşikleri 20/45/15)."""
    ad = "dis__osilator-esik-and"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "hedef_r": 1.5, "stok_n": 50, "stok_k": 5, "stok_d": 2,
                               "stok_esik": 20.0, "rsi_n": 6, "rsi_esik": 45.0, "srsi_n": 16, "srsi_esik": 15.0,
                               "cci_n": 20, "cci_esik": 150.0, "adx_esik": 24.52, "roc_n": 10,
                               "kullan_stok": 1, "kullan_rsi": 1, "kullan_srsi": 1, "kullan_cci": 0, "kullan_adx": 0,
                               "kullan_roc": 0}
    parametre_izgarasi = {"stok_esik": [15.0, 20.0, 30.0], "rsi_esik": [35.0, 45.0, 55.0], "srsi_esik": [10.0, 15.0, 25.0]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        uzun, kisa = _bos(m) | True, _bos(m) | True
        if p["kullan_stok"]:
            ham = g.stokastik(y, d, k, int(p["stok_n"]), 1)["k"]
            kk = g.sma(ham, int(p["stok_k"]))
            dd = g.sma(kk, int(p["stok_d"]))
            uzun &= (kk < p["stok_esik"]) & (dd < p["stok_esik"]) & (kk >= dd)
            kisa &= (kk > 100 - p["stok_esik"]) & (dd > 100 - p["stok_esik"]) & (kk <= dd)
        r = g.rsi(k, int(p["rsi_n"]))
        if p["kullan_rsi"]:
            uzun &= r < p["rsi_esik"]
            kisa &= r > 100 - p["rsi_esik"]
        if p["kullan_srsi"]:
            sr = stoch_rsi(k, int(p["srsi_n"]), int(p["srsi_n"]), 3, 3)["k"]
            uzun &= sr < p["srsi_esik"]
            kisa &= sr > 100 - p["srsi_esik"]
        if p["kullan_cci"]:
            c_ = cci(y, d, k, int(p["cci_n"]))
            uzun &= c_ < -p["cci_esik"]
            kisa &= c_ > p["cci_esik"]
        if p["kullan_adx"]:
            a_ = g.adx(y, d, k, 14)["adx"] < p["adx_esik"]
            uzun &= a_
            kisa &= a_
        if p["kullan_roc"]:
            roc = k.pct_change(int(p["roc_n"]))
            uzun &= roc < 0
            kisa &= roc > 0
        r14 = g.rsi(k, int(p["rsi_n"]))
        return {"long": gecis(uzun), "short": gecis(kisa), "cikis_long": yukari_kesis(r14, 50.0),
                "cikis_short": asagi_kesis(r14, 50.0)}


# =============================================================================== 3
class FraktalOkGirisi(_Taban):
    """dis__fraktal-ok-girisi (daytrade, 1h) — ailesi: fraktal-ok-girisi.
    Kaynak: EA31337-strategies `Fractals/Stg_Fractals.mqh`, `Arrows` (kural özeti; kod kopyalanmadı).
    Kural: ONAYLI alt fraktal (dip) oluşunca long, üst fraktal (tepe) oluşunca short. Fraktal = k mum solundan KESİN, k mum sağından
    yüksek/eşit uç; onay k mum SONRA (gecikmeli, nedensel: pivotlar.fraktal_pivotlar). Fraktal yalnız onay mumunda sinyal verir.
    İsteğe bağlı trend süzgeci (trend_ema > 0: long için kapanış > EMA). Stop: stop_modu 'pivot' -> fraktal fiyatı -/+ 0.25 ATR (en çok
    stop_atr_k x ATR uzaklıkta), 'atr' -> stop_atr_k x ATR. Hedef 2R. Çıkış: karşı yön fraktal onayı.
    VARSAYIM: k=2 (klasik 5 mumluk fraktal); kaynakta stop yöntemi çerçeve sınıfında olduğundan stop/hedef bizim standart varsayımımız.
    Arrows'un ATR-MA eğim yardımcı çizgisi (periyot 7, ATR 50, eşik 2.0) kodlanmadı (ok = fraktal modu ile aynı)."""
    ad = "dis__fraktal-ok-girisi"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "fraktal_k": 2, "trend_ema": 0, "stop_modu": "pivot"}
    parametre_izgarasi = {"fraktal_k": [2, 3], "stop_atr_k": [1.5, 2.0, 3.0], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        if p["stop_modu"] not in ("pivot", "atr"):
            raise ValueError(f"stop_modu 'pivot' veya 'atr' olmalı: {p['stop_modu']!r}")
        k = m["kapanis"]
        t = fraktal_pivotlar(m["yuksek"], m["dusuk"], int(p["fraktal_k"]))
        uzun, kisa = t["yeni_dip"], t["yeni_tepe"]
        if p["trend_ema"]:
            e = g.ema(k, int(p["trend_ema"]))
            uzun, kisa = uzun & (k > e), kisa & (k < e)
        out = {"long": uzun, "short": kisa, "cikis_long": t["yeni_tepe"], "cikis_short": t["yeni_dip"]}
        if p["stop_modu"] == "pivot":
            a = g.atr(m["yuksek"], m["dusuk"], k, int(p["atr_periyot"]))
            out["stop_long"] = np.maximum(t["son_dip_fiyat"] - 0.25 * a, k - p["stop_atr_k"] * a)
            out["stop_short"] = np.minimum(t["son_tepe_fiyat"] + 0.25 * a, k + p["stop_atr_k"] * a)
        return out


# =============================================================================== 4
class GostergeEgimEsik(_Taban):
    """dis__gosterge-egim-esik (daytrade, 15m-1h) — ailesi: gosterge-egim-yuzde-esik (lider kararı: TEK genel sınıf, 33 kaynak satırı).
    Kaynaklar: EA31337-strategies (AC, AD, ADX, AMA, ASI, ATR, Bears/Bulls, BWMFI, Chaikin, DEMA, DPO, Force, Momentum, OBV, OsMA, MACD,
    RVI, StdDev, MA yön değişimi ... `Stg_*.mqh`), Gekko-Strategies (Bro-RSI, custom-fab-ao, ta_ema/trend_ema, ti_hma) — kural özeti; kod yok.
    Kural: seçilen göstergenin (parametre `gosterge`) son n_bar mumda SÜREKLİ artması ve toplam değişimin eşiği aşması -> long;
    sürekli azalması ve değişimin -eşik altında olması -> short. Değişim yüzdesi = 100 x (x_t - x_{t-n_bar}) / ref, ref = son 100 mumun
    |x| ortalaması (fiyat seviyeli göstergelerde ref ~ fiyat => gerçek yüzde; sıfır çevresinde salınanlarda ölçek-bağımsız oran).
    bolge='orta': yalnız göstergenin merkez değerinin zıt tarafında giriş (long için x < merkez; AC/AO/Force/DPO/RVI/Bears-Bulls için 0,
    RSI için 50, Momentum için 100) -- kaynaktaki 'sıfırın altında yükseliyor' kuralı; fiyat seviyeli göstergelerde (ema, hma, dema,
    kama) bolge='orta' fiyat koşuludur (long için kapanış < gösterge için DEĞİL; kama: düşük < AMA). ADX: eğim yukarı VE +DI > -DI long,
    -DI > +DI short (yönü DI verir). ATR/StdDev yönsüz: yön, kapanışın n_bar önceye göre yönünden alınır.
    Çıkış: ters yönde n_bar sürekli eğim. Stop 2 ATR, hedef yok (çıkış sinyali + stop). Seçenekler: GOSTERGELER (21).
    VARSAYIM: kaynak varsayılanları EA31337 'açma yöntemi/seviye' bit alanlarına bağlı; yön yalnız gösterge eğiminden alınır, eşikler yüzde."""
    ad = "dis__gosterge-egim-esik"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "hedef_r": 0.0, "yonler": "ls", "gosterge": "rsi", "gosterge_n": 14, "n_bar": 3,
                               "yuzde_esik": 1.0, "bolge": "yok"}
    parametre_izgarasi = {"gosterge": ["rsi", "ao", "ema"], "n_bar": [2, 3, 4], "yuzde_esik": [0.5, 1.0, 2.0]}

    def kosullar(self, m):
        p = self.parametreler
        ad = p["gosterge"]
        if ad not in GOSTERGELER:
            raise ValueError(f"Bilinmeyen gösterge: {ad!r} (seçenekler: {GOSTERGELER})")
        if p["bolge"] not in ("yok", "orta"):
            raise ValueError(f"bolge 'yok' veya 'orta' olmalı: {p['bolge']!r}")
        nb = int(p["n_bar"])
        k = m["kapanis"]
        x = gosterge_serisi(m, ad, int(p["gosterge_n"]))
        d = x.diff()
        art = (d > 0).rolling(nb, min_periods=nb).sum() == nb
        azl = (d < 0).rolling(nb, min_periods=nb).sum() == nb
        ref = x.abs().rolling(100, min_periods=50).mean().where(lambda s: s > 0)
        yuzde = 100.0 * (x - x.shift(nb)) / ref
        uzun = art & (yuzde >= p["yuzde_esik"])
        kisa = azl & (yuzde <= -p["yuzde_esik"])
        if ad in YONSUZ:
            fy = k - k.shift(nb)
            uzun, kisa = (art & (yuzde >= p["yuzde_esik"]) & (fy > 0)), (art & (yuzde >= p["yuzde_esik"]) & (fy < 0))
        if ad == "adx":
            di = g.adx(m["yuksek"], m["dusuk"], k, int(p["gosterge_n"]))
            uzun = art & (yuzde >= p["yuzde_esik"]) & (di["arti_di"] > di["eksi_di"])
            kisa = art & (yuzde >= p["yuzde_esik"]) & (di["eksi_di"] > di["arti_di"])
        if p["bolge"] == "orta":
            if ad in ("ema", "hma", "dema"):
                uzun, kisa = uzun & (m["dusuk"] < x), kisa & (m["yuksek"] > x)
            elif ad == "kama":
                uzun, kisa = uzun & (m["dusuk"] < x), kisa & (m["yuksek"] > x)
            elif ad not in YONSUZ and ad != "adx":
                mer = MERKEZ.get(ad, 0.0)
                uzun, kisa = uzun & (x < mer), kisa & (x > mer)
        return {"long": gecis(uzun), "short": gecis(kisa), "cikis_long": azl, "cikis_short": azl if (ad in YONSUZ or ad == "adx") else art}


# 5. aile (gunluk-yukselenler-tarama-1s-teyit) kodlanmadı: kesitsel tarama, tek grafikte karşılığı yok (veri_yok).

# =============================================================================== 6
class HacimGovdePatlamasi(_Taban):
    """dis__hacim-govde-patlamasi (daytrade, 1h) — ailesi: hacim-ve-govde-patlamasi-devam.
    Kaynak: Gekko-Strategies `momentum:impulse`, `loosai/oosai` (hacim patlaması); Jesse/Ccxt çerçevesi `InstantFluctuationsEvaluator` — kural özeti.
    Kural (patlama mumunun KENDİSİNDE giriş; dis__hacim-patlama-kirilimi gibi kırılım beklemez): kapanan mumun hacmi >
    hacim_k x ortalama hacim (son hacim_n mum, bu mum HARİÇ) VE gövde (|kapanış - açılış|) > govde_k x ATR(14) VE yönü mumun rengi:
    yeşil -> long, kırmızı -> short. loosai varyantı (hacim x fiyat gruplama) 'hacim_k' ile yaklaşıklanır.
    Çıkış: ATR iz süren stop (iz_k x ATR; kaynak 3 ATR) + başlangıç stopu 3 ATR; hedef yok.
    VARSAYIM: impulse'taki 168 mumluk ortalama ve 3x/2x eşikler ızgaranın ortasında; loosai'nin mutlak '15 BTC' eşiği oransal hacim eşiğine çevrildi."""
    ad = "dis__hacim-govde-patlamasi"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "hedef_r": 0.0, "stop_atr_k": 3.0, "hacim_n": 168, "hacim_k": 3.0,
                               "govde_k": 2.0, "iz_k": 3.0}
    parametre_izgarasi = {"hacim_k": [2.0, 3.0, 4.0], "govde_k": [1.0, 1.5, 2.0], "iz_k": [2.0, 3.0, 4.0]}
    cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=3.0)

    def __init__(self, cikis_ayarlari=None, **parametreler):
        super().__init__(cikis_ayarlari, **parametreler)
        if cikis_ayarlari is None:
            self.cikis_ayarlari = CikisAyarlari(atr_iz_suren_k=float(self.parametreler["iz_k"]))

    def kosullar(self, m):
        p = self.parametreler
        o, k = m["acilis"], m["kapanis"]
        n = int(p["hacim_n"])
        ort = m["hacim"].shift(1).rolling(n, min_periods=min(n, 50)).mean()
        a = g.atr(m["yuksek"], m["dusuk"], k, 14)
        patla = (m["hacim"] > p["hacim_k"] * ort) & ((k - o).abs() > p["govde_k"] * a)
        return {"long": patla & (k > o), "short": patla & (k < o)}


# =============================================================================== 7
class JakePpoVosc(_Taban):
    """dis__jake-ppo-vosc (daytrade, 1h) — ailesi: jake-ppo-linreg-vosc-cci-bb.
    Kaynak: Gekko-Strategies (xFFFFF) `!WORKSOP/jake.js` (kural özeti; kod kopyalanmadı).
    LONG iki koldan biri (durumun ilk mumunda):
      A) Bollinger genişliği (üst-alt)/orta >= bbw_min VE hacim osilatörü (5,20) > 0 VE PPO histogramının değişim oranı
         (hist_t - hist_{t-1}) / |hist_{t-1}| > ppo_oran (varsayılan %40) VE hist artıyor.
      B) kapanış <= Bollinger orta bandı (kaynaktaki 'önceki short fiyatı' durum izi yerine VARSAYIM) VE hist artıyor VE hist >
         hist_alt (PPO % biriminde, kaynak -0.15) VE doğrusal regresyon (linreg, lr_n) eğimi (yüzde/mum) > egim_alt (kaynak -0.3) ve
         artıyor VE CCI(cci_n) son 3 mumda -120'nin altındaydı ve şimdi -100'ü yukarı kesti.
    Short kolu yok (kaynakta short = long'u KAPATMA). Çıkış: hedef %hedef_yuzde (kaynak %10), CCI 120'yi aşağı keserse (kaynak: kâr >= %3
    koşulu pozisyon bilgisi gerektirir -> VARSAYIM: koşulsuz), zaman çıkışı (kaynak 12 saat & kâr >= -%1 -> VARSAYIM: koşulsuz zaman_cikisi
    mum, 0=kapalı), stop 2 ATR.
    VARSAYIM: 'dar değil' mutlak 0.0001 eşiği yüzdeye çevrildi (bbw_min=0.01)."""
    ad = "dis__jake-ppo-vosc"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "hedef_r": 0.0, "hedef_yuzde": 0.10, "ppo_oran": 0.40, "bbw_min": 0.01, "lr_n": 25,
                               "egim_alt": -0.3, "hist_alt": -0.15, "cci_n": 20, "zaman_cikisi": 0}
    parametre_izgarasi = {"ppo_oran": [0.2, 0.4, 0.8], "hedef_yuzde": [0.03, 0.06, 0.10], "stop_atr_k": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        bb = g.bollinger(k, 20, 2.0)
        bbw = (bb["ust"] - bb["alt"]) / bb["orta"]
        hist = ppo(k)["hist"]
        onc = hist.shift(1)
        oran = (hist - onc) / onc.abs().where(onc != 0)
        vosc = hacim_osilatoru(m["hacim"], 5, 20)
        a_kol = (bbw >= p["bbw_min"]) & (vosc > 0) & (oran > p["ppo_oran"]) & (hist > onc)
        lr = linreg(k, int(p["lr_n"]))
        egim = 100.0 * (lr - lr.shift(1)) / k
        c_ = cci(y, d, k, int(p["cci_n"]))
        toparlandi = yukari_kesis(c_, -100.0) & (c_.shift(1).rolling(3, min_periods=1).min() < -120.0)
        b_kol = ((k <= bb["orta"]) & (hist > onc) & (hist > p["hist_alt"]) & (egim > p["egim_alt"])
                 & (egim > egim.shift(1)) & toparlandi)
        return {"long": gecis(a_kol | b_kol), "cikis_long": asagi_kesis(c_, 120.0)}


# =============================================================================== 8
class KlingerSkoru(_Taban):
    """dis__klinger-skoru (daytrade, 1h; kaynakta 30m/1h/4h) — ailesi: klinger-hacim-osilatoru-skoru.
    Kaynak: Jesse/OctoBot çerçevesi `KlingerOscillatorMomentumEvaluator`, `MoveSignalsStrategyEvaluator + SignalTradingMode` (kural özeti).
    Kural: Klinger notu = (KVO(kisa=34,uzun=55) - EMA13(KVO)) / son 100 mumun std'si, [-1, 1]'e kırpılır. Bollinger ağırlığı: %B (20,2);
    nota göre ayarlanır: skor_i = not_i x (1 + bb_etki x işaret(not_i) x (1 - 2 %B_i)) (alt banda yakın alış / üst banda yakın satış notu
    güçlenir; bb_etki=0 -> yalnız Klinger). Çoklu TF: işlem TF'si (ağırlık 1) + ust_tf (ağırlık ust_agirlik; '' = kapalı; yalnız kapanmış
    üst mumlar). Skor = ağırlıklı ortalama. Skor +esik'i yukarı keserse long, -esik'i aşağı keserse short; çıkış: skor 0'ı ters yöne keserse.
    Stop 2 ATR, hedef 2R.
    VARSAYIM: kaynak 30m(4)/1h(3)/4h(3) ağırlıklı; burada 1h + 4h. 'Doruk ulaşıldıysa çarpan 1' (kısmi tarif) kodlanmadı; kaynak eşiği |sinyal|>=0.15."""
    ad = "dis__klinger-skoru"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "kvo_kisa": 34, "kvo_uzun": 55, "kvo_sinyal": 13, "std_n": 100,
                               "bb_etki": 0.5, "ust_tf": "4h", "ust_agirlik": 1.0, "esik": 0.3}
    parametre_izgarasi = {"esik": [0.15, 0.3, 0.5], "bb_etki": [0.0, 0.5, 1.0], "ust_tf": ["", "4h"]}

    def _not(self, u: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kvo = klinger(u["yuksek"], u["dusuk"], u["kapanis"], u["hacim"], int(p["kvo_kisa"]), int(p["kvo_uzun"]))
        fark = kvo - kvo.ewm(span=int(p["kvo_sinyal"]), adjust=False, min_periods=int(p["kvo_sinyal"])).mean()
        sd = fark.rolling(int(p["std_n"]), min_periods=30).std(ddof=0).where(lambda s: s > 0)
        kn = (fark / sd).clip(-1.0, 1.0)
        bb = g.bollinger(u["kapanis"], 20, 2.0)
        pb = ((u["kapanis"] - bb["alt"]) / (bb["ust"] - bb["alt"]).where(bb["ust"] != bb["alt"])).clip(0.0, 1.0)
        skor = kn * (1.0 + p["bb_etki"] * np.sign(kn) * (1.0 - 2.0 * pb))
        return pd.DataFrame({"skor": skor})

    def kosullar(self, m):
        p = self.parametreler
        s0 = self._not(m)["skor"]
        if p["ust_tf"]:
            s1 = ust_zaman(m, p["ust_tf"], self._not)["skor"]
            w = float(p["ust_agirlik"])
            skor = (s0 + w * s1) / (1.0 + w)
        else:
            skor = s0
        e = float(p["esik"])
        return {"long": yukari_kesis(skor, e), "short": asagi_kesis(skor, -e),
                "cikis_long": asagi_kesis(skor, 0.0), "cikis_short": yukari_kesis(skor, 0.0)}


# =============================================================================== 9
class LinregMumTeyit(_Taban):
    """dis__linreg-mum-teyit (daytrade, 15m-1h) — ailesi: lineer-regresyon-mumlari-teyitli.
    Kaynak: MetaTrader/Pine paketi `LRCMACD`, `LRCUTB` (kural özeti; kod kopyalanmadı).
    Linear Regression Candles: açılış/yüksek/düşük/kapanış serilerinin her birinin son lr_n mumluk en küçük kareler doğrusunun SON noktası
    (LRC mumu). LRC sinyal çizgisi = SMA(LRC kapanış, sinyal_n). Long: LRC mumu yeşil (LRC kapanış > LRC açılış) VE LRC kapanış > sinyal
    çizgisi (durumun ilk mumunda) VE teyit: 'macd' -> MACD(34,144) ana çizgisi son 2 mumda > 0; 'utbot' -> son 3 mumda UT Bot al sinyali
    (anahtar 1, ATR 10). Short aynası (kırmızı mum, kapanış < sinyal, MACD < 0 / UT sat). Stop: son stop_n mumun dibi/zirvesi (kaynak 10;
    en çok 4 ATR), hedef hedef_r x R (VARSAYIM 2R). Çıkış: LRC mum rengi ters + sinyal çizgisi ters tarafta.
    VARSAYIM: LRC sinyal çizgisi SMA (kaynakta tip belirtilmemiş)."""
    ad = "dis__linreg-mum-teyit"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "lr_n": 11, "sinyal_n": 7, "teyit": "macd", "stop_n": 10,
                               "macd_hizli": 34, "macd_yavas": 144, "ut_anahtar": 1.0, "ut_atr": 10}
    parametre_izgarasi = {"lr_n": [8, 11, 15], "teyit": ["macd", "utbot"], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        if p["teyit"] not in ("macd", "utbot"):
            raise ValueError(f"teyit 'macd' veya 'utbot' olmalı: {p['teyit']!r}")
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        n = int(p["lr_n"])
        lo, lc = linreg(m["acilis"], n), linreg(k, n)
        sig = g.sma(lc, int(p["sinyal_n"]))
        yesil, kirmizi = lc > lo, lc < lo
        if p["teyit"] == "macd":
            mc = g.macd(k, int(p["macd_hizli"]), int(p["macd_yavas"]), 9)["macd"]
            tl = (mc > 0) & (mc.shift(1) > 0)
            ts = (mc < 0) & (mc.shift(1) < 0)
        else:
            a = g.atr(y, d, k, int(p["ut_atr"]))
            ut = ut_bot(k, a, float(p["ut_anahtar"]))
            tl = ut["al"].astype(float).rolling(3, min_periods=1).max() > 0
            ts = ut["sat"].astype(float).rolling(3, min_periods=1).max() > 0
        uzun = gecis(yesil & (lc > sig) & tl)
        kisa = gecis(kirmizi & (lc < sig) & ts)
        a14 = g.atr(y, d, k, int(p["atr_periyot"]))
        sn = int(p["stop_n"])
        return {"long": uzun, "short": kisa,
                "stop_long": np.maximum(d.rolling(sn, min_periods=sn).min(), k - 4.0 * a14),
                "stop_short": np.minimum(y.rolling(sn, min_periods=sn).max(), k + 4.0 * a14),
                "cikis_long": kirmizi & (lc < sig), "cikis_short": yesil & (lc > sig)}


# =============================================================================== 10
class MaGunlukPivot(_Taban):
    """dis__ma-gunluk-pivot (daytrade, 1h) — ailesi: ma-gunluk-pivot-kesisimi.
    Kaynak: EA31337-strategies `MA Cross Pivot`, `MA Cross Sup Res` (kural özeti; kod kopyalanmadı).
    Önceki TAMAMLANMIŞ seansın (UTC günü) H/L/C'sinden klasik pivot: P = (H+L+C)/3, R1 = 2P-L, S1 = 2P-H, R2 = P+(H-L), S2 = P-(H-L),
    R3 = H+2(P-L), S3 = L-2(H-P), R4 = R3+(H-L), S4 = S3-(H-L) (R4/S4 tanımı VARSAYIM; kaynak 4 seviye diyor). seviye_grubu: 'pivot' (P),
    'destek_direnc' (R1-R4 ve S1-S4), 'hepsi' (P + R + S). Long: MA(ma_n, ma_tipi) seviyelerden birini YUKARI keser (önceki mumda altındaydı)
    VE MA yükseliyor; short: MA seviyelerden birini AŞAĞI keser VE MA düşüyor. Stop 2 ATR, hedef 2R, gun_sonu=1 (seans sonu çıkış).
    ATLANDI: 'Retracement' varyantı (en yakın pivota uzaklık oranı eşiği kaynakta pip cinsinden)."""
    ad = "dis__ma-gunluk-pivot"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "gun_sonu": 1, "ma_n": 20, "ma_tipi": "ema", "seviye_grubu": "hepsi"}
    parametre_izgarasi = {"ma_n": [10, 20, 50], "seviye_grubu": ["pivot", "destek_direnc", "hepsi"], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        if p["seviye_grubu"] not in ("pivot", "destek_direnc", "hepsi"):
            raise ValueError(f"seviye_grubu hatalı: {p['seviye_grubu']!r}")
        if p["ma_tipi"] not in ("ema", "sma"):
            raise ValueError(f"ma_tipi 'ema' veya 'sma' olmalı: {p['ma_tipi']!r}")
        k = m["kapanis"]
        ma = (g.ema if p["ma_tipi"] == "ema" else g.sma)(k, int(p["ma_n"]))
        hlc = onceki_seans_hlc(m, seans_kimligi(m.index, 0.0))
        h, l, c = hlc["h"], hlc["l"], hlc["c"]
        pv = (h + l + c) / 3.0
        r = h - l
        r3 = h + 2 * (pv - l)
        s3 = l - 2 * (h - pv)
        seviyeler = {"p": pv, "r1": 2 * pv - l, "s1": 2 * pv - h, "r2": pv + r, "s2": pv - r, "r3": r3, "s3": s3,
                     "r4": r3 + r, "s4": s3 - r}
        sec = {"pivot": ["p"], "destek_direnc": [x for x in seviyeler if x != "p"], "hepsi": list(seviyeler)}[p["seviye_grubu"]]
        yuk, asg = _bos(m), _bos(m)
        for ad in sec:
            yuk |= yukari_kesis(ma, seviyeler[ad]).fillna(False)
            asg |= asagi_kesis(ma, seviyeler[ad]).fillna(False)
        return {"long": yuk & (ma > ma.shift(1)), "short": asg & (ma < ma.shift(1))}


# =============================================================================== 11
class MacdHistEsikOnay(_Taban):
    """dis__macd-hist-esik-onay (daytrade, 15m-1h) — ailesi: macd-hist-esik-osilator-onay.
    Kaynak: Gekko-Strategies (xFFFFF) `Pascal`, `MACD-CCI-RSI`, `MACD-MFI-ADX`, `RSI-MACD`, `L1-CCI_MACD` (kural özeti; kod kopyalanmadı).
    MACD(12,26,9) histogramı ATR'ye bölünerek normalize edilir (mutlak 0.025/0.005 eşikleri fiyat birimliydi -> VARSAYIM hist_esik x ATR).
    onay='rsi' (Pascal): hist > +e VE RSI < rsi_alt -> long; hist < -e VE RSI > rsi_ust -> short.
    onay='mfi' (MACD-MFI-ADX): hist > +e VE MFI(2) <= mfi_alt VE ADX < adx_max (yatay süzgeç; adx_max=0 kapalı) -> long; aynası short.
    onay='cci_trend' (MACD-CCI-RSI): hist > +e VE CCI(31) > 0 VE RSI < rsi_alt -> long; aynası short.
    onay='cci_ters' (L1-CCI_MACD): hist < -e VE CCI < -cci_esik -> long (aşırı satımdan dönüş); hist > +e VE CCI > cci_esik -> short.
    Girişler durum geçişinde. Stop 2 ATR, hedef 2R. Çıkış: histogram ters işaret."""
    ad = "dis__macd-hist-esik-onay"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "onay": "rsi", "hist_esik": 0.1, "rsi_n": 14, "rsi_alt": 40.0,
                               "mfi_alt": 20.0, "adx_max": 30.0, "cci_n": 31, "cci_esik": 100.0}
    parametre_izgarasi = {"onay": ["rsi", "mfi", "cci_trend", "cci_ters"], "hist_esik": [0.05, 0.1, 0.2],
                          "hedef_r": [1.5, 2.5]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        a = g.atr(y, d, k, 14)
        h = g.macd(k)["histogram"] / a
        e = float(p["hist_esik"])
        rs = g.rsi(k, int(p["rsi_n"]))
        ov = p["onay"]
        if ov == "rsi":
            uzun, kisa = (h > e) & (rs < p["rsi_alt"]), (h < -e) & (rs > 100 - p["rsi_alt"])
        elif ov == "mfi":
            mf = mfi(y, d, k, m["hacim"], 2)
            ok = (g.adx(y, d, k, 14)["adx"] < p["adx_max"]) if p["adx_max"] > 0 else pd.Series(True, index=m.index)
            uzun, kisa = (h > e) & (mf <= p["mfi_alt"]) & ok, (h < -e) & (mf >= 100 - p["mfi_alt"]) & ok
        elif ov == "cci_trend":
            c_ = cci(y, d, k, int(p["cci_n"]))
            uzun, kisa = (h > e) & (c_ > 0) & (rs < p["rsi_alt"]), (h < -e) & (c_ < 0) & (rs > 100 - p["rsi_alt"])
        elif ov == "cci_ters":
            c_ = cci(y, d, k, int(p["cci_n"]))
            uzun, kisa = (h < -e) & (c_ < -p["cci_esik"]), (h > e) & (c_ > p["cci_esik"])
        else:
            raise ValueError(f"onay 'rsi', 'mfi', 'cci_trend' veya 'cci_ters' olmalı: {ov!r}")
        return {"long": gecis(uzun), "short": gecis(kisa), "cikis_long": h < 0 if ov != "cci_ters" else h > 0,
                "cikis_short": h > 0 if ov != "cci_ters" else h < 0}


# =============================================================================== 12
class MacdSeviyeMtf(_Taban):
    """dis__macd-seviye-mtf (daytrade, 15m taban + 30m) — ailesi: macd-seviye-cok-zaman-dilimi.
    Kaynak: Gekko-Strategies (xFFFFF) `timeframes` (15/30dk MACD) (kural özeti; kod kopyalanmadı).
    Kaynak: 30 dk MACD 'lowCross' (-20) seviyesini yukarı keserse AL; 15 dk MACD 'highCross' (+20) seviyesini aşağı keserse SAT;
    stop %1.5 tampon, kâr oranı 1.5. Burada: taban TF (15m) MACD'si ve ust_tf (varsayılan 30m, yalnız kapanmış mumlar) MACD'si ATR'ye
    bölünerek normalize edilir (mutlak ±20 fiyat birimliydi -> VARSAYIM seviye_atr x ATR). Long: ÜST TF MACD -seviye_atr'yi YUKARI keser.
    Çıkış long: ALT (taban) TF MACD +seviye_atr'yi AŞAĞI keser (kaynak 'sat'). yonler='ls' ise short aynası (üst TF +seviye aşağı;
    çıkış: taban TF -seviye yukarı). Stop: stop_yuzde (kaynak %1.5) ve hedef hedef_r x R (kaynak 1.5)."""
    ad = "dis__macd-seviye-mtf"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "ust_tf": "30m", "seviye_atr": 0.6, "stop_yuzde": 0.015, "hedef_r": 1.5}
    parametre_izgarasi = {"seviye_atr": [0.3, 0.6, 1.0], "stop_yuzde": [0.01, 0.015, 0.02], "hedef_r": [1.0, 1.5, 2.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        s = float(p["seviye_atr"])

        def f(u):
            a = g.atr(u["yuksek"], u["dusuk"], u["kapanis"], 14)
            return pd.DataFrame({"x": g.macd(u["kapanis"])["macd"] / a})
        alt = f(m)["x"]
        ust = ust_zaman(m, p["ust_tf"], f)["x"]
        sy = float(p["stop_yuzde"])
        return {"long": yukari_kesis(ust, -s), "short": asagi_kesis(ust, s),
                "cikis_long": asagi_kesis(alt, s), "cikis_short": yukari_kesis(alt, -s),
                "stop_long": k * (1 - sy), "stop_short": k * (1 + sy)}


# =============================================================================== 13
class NwZarfRsi(_Taban):
    """dis__nw-zarf-rsi (daytrade, 2h; 1h-4h) — ailesi: nadaraya-watson-zarfi-rsi.
    Kaynak: geraked/metatrader5 `Experts/NWERSIASF.mq5` (kural özeti; kod kopyalanmadı).
    Zarf: SADECE NEDENSEL (tek yanlı) Nadaraya-Watson: tahmin_t = Gauss ağırlıklı (bant h) son pencere kapanışı ortalaması; zarf =
    tahmin -/+ carpan x SMA(|kapanış - tahmin|, 100). Merkezli çekirdek yeniden çizer -> kullanılmadı; tek yanlı tahmin sonradan değişmez.
    LONG: 2 mum önceki düşük, o mumdaki alt zarfın altına inmiş VE son mum yeşil VE kapanış zarf orta çizgisinin (tahmin) altında VE 2 mum
    önceki RSI(5) < rsi_alt. SHORT aynası (yüksek > üst zarf, kırmızı mum, kapanış > orta, RSI(5) > 100 - rsi_alt).
    Stop: stop_atr_k x ATR (kaynak: ATR SL Finder ATR14 x 0.75 ofsetli çizgi -> VARSAYIM 1.5 ATR); hedef 1.5R (kaynak). Kaynaktaki
    'aynı sembolde son girişten >= 4 mum' kuralı motorun tek pozisyonuyla örtüşür; grid/martingale kısımları kodlanmadı."""
    ad = "dis__nw-zarf-rsi"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "stop_atr_k": 1.5, "hedef_r": 1.5, "nw_h": 8.0, "nw_pencere": 60,
                               "carpan": 3.0, "rsi_n": 5, "rsi_alt": 30.0, "gecikme": 2}
    parametre_izgarasi = {"nw_h": [6.0, 8.0, 12.0], "carpan": [2.0, 3.0, 4.0], "rsi_alt": [25.0, 30.0, 35.0]}

    def kosullar(self, m):
        p = self.parametreler
        o, y, d, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        z = nw_zarf(k, float(p["nw_h"]), int(p["nw_pencere"]), float(p["carpan"]))
        gk = int(p["gecikme"])
        r = g.rsi(k, int(p["rsi_n"])).shift(gk)
        uzun = (d.shift(gk) < z["alt"].shift(gk)) & (k > o) & (k < z["orta"]) & (r < p["rsi_alt"])
        kisa = (y.shift(gk) > z["ust"].shift(gk)) & (k < o) & (k > z["orta"]) & (r > 100 - p["rsi_alt"])
        return {"long": uzun, "short": kisa}


# =============================================================================== 14
class ParabolikIlkKirmiziShort(_Taban):
    """dis__parabolik-ilk-kirmizi-short (daytrade, 5m; yalnız ABD hisse seansı) — ailesi: parabolik-hisse-short-ilk-kirmizi-mum.
    Kaynak: platform kural notları 'Parabolik short: ilk kırmızı 5dk mum dibi' ve '5dk açılış aralığı dibi (ORL) kırılımı' (kural özeti).
    GÜN SÜZGECİ (yalnız önceki tamamlanmış günlerin verisi; UTC günü = seans): 5 günlük getiri >= getiri_esik (kaynak %30 büyük hisse /
    %100 küçük) VE son kapanış SMA20'nin yuzde_sma (%25) üstünde VE >= atr_sma x günlük ATR(14) (kaynak 4 ATR) VE son yesil_gun (3) gün
    üst üste yeşil (kapanış > açılış) VE son günün hacmi >= hacim_k (1.5) x SMA20(hacim). TETİK (gün içi, günde en çok bir short):
    tetik='ilk_kirmizi': seansın ilk kırmızı 5dk mumu belirlenir; sonraki bir mumun kapanışı o mumun DİBİNİN altında biterse short; öncesinde
    kapanış o mumun TEPESİNİN üstünde biterse gün geçersiz (kaynak). tetik='orl': ilk orl_mum mumun dibi; kapanış altında biterse short.
    Stop: tetik mumunun tepesi (orl: seans tepesi) + tampon_atr x ATR; hedef hedef_r x R (VARSAYIM 2R); seans sonu çıkış (gun_sonu=1).
    UYARI: kaynak 'yalnız parabolik küçük/orta hisse'; Mag7 evreninde süzgeç neredeyse hiç tetiklenmez (sıfır işlem beklenen). Giriş
    kaynaktaki 'dip - 0.05' limit emri yerine kapanış-sonrası-açılış dolumu (motor)."""
    ad = "dis__parabolik-ilk-kirmizi-short"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "short", "gun_sonu": 1, "tetik": "ilk_kirmizi", "orl_mum": 1,
                               "getiri_esik": 0.30, "yuzde_sma": 0.25, "atr_sma": 4.0, "yesil_gun": 3, "hacim_k": 1.5,
                               "tampon_atr": 0.1}
    parametre_izgarasi = {"tetik": ["ilk_kirmizi", "orl"], "getiri_esik": [0.15, 0.30, 0.50], "hedef_r": [1.5, 2.0, 3.0]}

    def gun_filtresi(self, m, seans):
        p = self.parametreler
        grp = m.groupby(seans)
        gun = pd.DataFrame({"o": grp["acilis"].first(), "h": grp["yuksek"].max(), "l": grp["dusuk"].min(),
                            "c": grp["kapanis"].last(), "v": grp["hacim"].sum()})
        atr_g = g.atr(gun["h"], gun["l"], gun["c"], 14)
        sma = g.sma(gun["c"], 20)
        ret5 = gun["c"] / gun["c"].shift(5) - 1.0
        yg = int(p["yesil_gun"])
        yesil = ((gun["c"] > gun["o"]).astype(int).rolling(yg, min_periods=yg).sum() == yg)
        ok = ((ret5 >= p["getiri_esik"]) & (gun["c"] > sma * (1 + p["yuzde_sma"]))
              & ((gun["c"] - sma) >= p["atr_sma"] * atr_g) & yesil & (gun["v"] >= p["hacim_k"] * g.sma(gun["v"], 20)))
        return ok.shift(1, fill_value=False).reindex(seans).to_numpy()      # yalnız önceki tamamlanmış gün

    def kosullar(self, m):
        p = self.parametreler
        if p["tetik"] not in ("ilk_kirmizi", "orl"):
            raise ValueError(f"tetik 'ilk_kirmizi' veya 'orl' olmalı: {p['tetik']!r}")
        seans = seans_kimligi(m.index, 0.0)
        uygun = self.gun_filtresi(m, seans)
        a = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_periyot"]))
        sig, stop = parabolik_tetik(m, seans, uygun, p["tetik"], int(p["orl_mum"]), float(p["tampon_atr"]), a)
        return {"short": pd.Series(sig, index=m.index), "stop_short": pd.Series(stop, index=m.index)}


# =============================================================================== 15
class PpoTsiUoEsik(_Taban):
    """dis__ppo-tsi-uo-esik (daytrade, 1h) — ailesi: ppo-tsi-uo-esik-birlesimi.
    Kaynak: Gekko-Strategies (xFFFFF) `PPO-TSI`, `PPO-TSI-RSI`, `varPPO`, `STI-DEMA` (kural özeti; kod kopyalanmadı).
    PPO(12,26,9) histogramı (yüzde birimli, ölçekten bağımsız). Kaynak mantığı: TSI(13,25) aşırı bölgesi + histogram işareti.
    varyant='tsi': TSI < -tsi_esik VE hist < -hist_esik -> long; TSI > +tsi_esik VE hist > +hist_esik -> short (kaynak: 'TSI>25 ve hist>0.025 short').
    varyant='tsi_rsi': tsi koşulu + RSI(14) < rsi_alt (long) / > 100 - rsi_alt (short) (kaynak 'RSI>70 varyantı').
    varyant='uo': Ultimate Oscillator < uo_alt (30) VE hist < -hist_esik -> long; UO > 100 - uo_alt VE hist > hist_esik -> short.
    Girişler durum geçişinde. Çıkış: TSI sıfırı karşı yöne keser. Stop 2 ATR, hedef 2R.
    VARSAYIM: varPPO'nun 'eşikleri histograma ±120 ağırlıkla kaydırma' formülü ve STI-DEMA (DEMA yüzde farkı + STC kalıcılığı) kaynak koduna
    bağlı ve belirsiz olduğundan kodlanmadı; uo varyantı sabit eşikli sadeleştirmedir."""
    ad = "dis__ppo-tsi-uo-esik"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "varyant": "tsi", "tsi_esik": 25.0, "hist_esik": 0.025, "rsi_alt": 30.0,
                               "uo_alt": 30.0}
    parametre_izgarasi = {"varyant": ["tsi", "tsi_rsi", "uo"], "tsi_esik": [15.0, 25.0, 35.0], "hist_esik": [0.0, 0.025, 0.1]}

    def kosullar(self, m):
        p = self.parametreler
        y, d, k = m["yuksek"], m["dusuk"], m["kapanis"]
        h = ppo(k)["hist"]
        t = tsi(k, 25, 13)
        e, te = float(p["hist_esik"]), float(p["tsi_esik"])
        v = p["varyant"]
        if v in ("tsi", "tsi_rsi"):
            uzun, kisa = (t < -te) & (h < -e), (t > te) & (h > e)
            if v == "tsi_rsi":
                r = g.rsi(k, 14)
                uzun, kisa = uzun & (r < p["rsi_alt"]), kisa & (r > 100 - p["rsi_alt"])
        elif v == "uo":
            u = ultimate(y, d, k)
            uzun, kisa = (u < p["uo_alt"]) & (h < -e), (u > 100 - p["uo_alt"]) & (h > e)
        else:
            raise ValueError(f"varyant 'tsi', 'tsi_rsi' veya 'uo' olmalı: {v!r}")
        return {"long": gecis(uzun), "short": gecis(kisa), "cikis_long": yukari_kesis(t, 0.0), "cikis_short": asagi_kesis(t, 0.0)}


# =============================================================================== 16
class SpinningTopRsi(_Taban):
    """dis__spinning-top-rsi (daytrade, 1h) — ailesi: spinning-top-rsi-ea31337.
    Kaynak: EA31337-strategies `Pinbar/Stg_Pinbar.mqh` (kural özeti; kod kopyalanmadı).
    Spinning top tanımı (ölçülebilir): gövde <= govde_oran x aralık VE üst fitil >= fitil_oran x aralık VE alt fitil >= fitil_oran x aralık
    VE aralık >= min_aralik_atr x ATR (gürültü dojilerini ele). Long: spinning top VE RSI(14) < rsi_esik (kaynak 1.6 x 20 = 32). Short:
    spinning top VE RSI > 100 - rsi_esik. 'Yöntem bitleri' ek süzgeçleri: atr_filtre 'artan' (ATR > önceki ATR) / 'azalan' / 'yok';
    cci_filtre=1: long için CCI(14) < -cci_esik, short için > +cci_esik (kaynak 18 x seviye ~ ölçeksiz; VARSAYIM 100).
    Stop 2 ATR, hedef 2R (kaynak stop yöntemi çerçevede; VARSAYIM). Çıkış: stop/hedef + RSI 50'yi geçince."""
    ad = "dis__spinning-top-rsi"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "govde_oran": 0.3, "fitil_oran": 0.25, "min_aralik_atr": 0.5,
                               "rsi_n": 14, "rsi_esik": 32.0, "atr_filtre": "yok", "cci_filtre": 0, "cci_esik": 100.0}
    parametre_izgarasi = {"rsi_esik": [25.0, 32.0, 40.0], "atr_filtre": ["yok", "artan", "azalan"], "cci_filtre": [0, 1]}

    def kosullar(self, m):
        p = self.parametreler
        if p["atr_filtre"] not in ("yok", "artan", "azalan"):
            raise ValueError(f"atr_filtre 'yok', 'artan' veya 'azalan' olmalı: {p['atr_filtre']!r}")
        o, y, d, k = m["acilis"], m["yuksek"], m["dusuk"], m["kapanis"]
        a = g.atr(y, d, k, 14)
        ar = (y - d).where(y > d)
        govde = (k - o).abs()
        uf, af = y - np.maximum(o, k), np.minimum(o, k) - d
        st = ((govde <= p["govde_oran"] * ar) & (uf >= p["fitil_oran"] * ar) & (af >= p["fitil_oran"] * ar)
              & (ar >= p["min_aralik_atr"] * a))
        r = g.rsi(k, int(p["rsi_n"]))
        uzun, kisa = st & (r < p["rsi_esik"]), st & (r > 100 - p["rsi_esik"])
        if p["atr_filtre"] == "artan":
            uzun, kisa = uzun & (a > a.shift(1)), kisa & (a > a.shift(1))
        elif p["atr_filtre"] == "azalan":
            uzun, kisa = uzun & (a < a.shift(1)), kisa & (a < a.shift(1))
        if p["cci_filtre"]:
            c_ = cci(y, d, k, 14)
            uzun, kisa = uzun & (c_ < -p["cci_esik"]), kisa & (c_ > p["cci_esik"])
        return {"long": uzun, "short": kisa, "cikis_long": yukari_kesis(r, 50.0) & (r.shift(1) < 50),
                "cikis_short": asagi_kesis(r, 50.0)}


# =============================================================================== 17
class UstTfMaYonKesisim(_Taban):
    """dis__ust-tf-ma-yon-kesisim (daytrade, 15m-1h) — ailesi: ust-tf-ma-yon-filtreli-ma-kesisimi.
    Kaynak: freqtrade `InformativeSample`; çerçeve örnekleri `Demo2` (5m SMA kesişimi + 1sa SMA yönü) ve `SmaOf2` (SMA5/20 kesişimi + 1sa EMA20/25
    rejimi); EA31337 `MA Cross Timeframe` (kural özeti; kod kopyalanmadı).
    Kural: TABAN TF'de hızlı MA yavaş MA'yı yukarı keser VE ÜST TF'de (ust_tf, yalnız kapanmış mumlar) hızlı MA > yavaş MA (yön filtresi,
    ust_hizli / ust_yavas) -> long. Short: aşağı kesişim VE üst TF hızlı < yavaş. Çıkış: taban TF'de ters kesişim. Stop 2 ATR, hedef yok
    (kesişimle çıkış) -- hedef_r > 0 verilirse R hedefi eklenir. ma_tipi 'sma'/'ema' (hem taban hem üst TF).
    ATLANDI: SmaOf2'nin 'ATR tepe/dip uzaklığı' koşulu (kaynakta eşik belirsiz). dis/swing ma-kesisim yalnız AYNI TF'de trend_ma süzgeci taşır."""
    ad = "dis__ust-tf-ma-yon-kesisim"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "hedef_r": 0.0, "hizli": 5, "yavas": 20, "ma_tipi": "sma",
                               "ust_tf": "1h", "ust_hizli": 20, "ust_yavas": 50}
    parametre_izgarasi = {"hizli": [5, 9, 13], "yavas": [20, 34, 50], "ust_tf": ["1h", "2h", "4h"]}

    def kosullar(self, m):
        p = self.parametreler
        if p["ma_tipi"] not in ("ema", "sma"):
            raise ValueError(f"ma_tipi 'ema' veya 'sma' olmalı: {p['ma_tipi']!r}")
        ma = g.ema if p["ma_tipi"] == "ema" else g.sma
        k = m["kapanis"]
        hz, yv = ma(k, int(p["hizli"])), ma(k, int(p["yavas"]))

        def f(u):
            return pd.DataFrame({"h": ma(u["kapanis"], int(p["ust_hizli"])), "y": ma(u["kapanis"], int(p["ust_yavas"]))})
        ust = ust_zaman(m, p["ust_tf"], f)
        yuk = (hz > yv) & (hz.shift(1) <= yv.shift(1))
        asg = (hz < yv) & (hz.shift(1) >= yv.shift(1))
        return {"long": yuk & (ust["h"] > ust["y"]), "short": asg & (ust["h"] < ust["y"]), "cikis_long": asg, "cikis_short": yuk}


# =============================================================================== 18
class VwapBasarisizlikShort(_Taban):
    """dis__vwap-basarisizlik-short (daytrade, 5m; seans içi) — ailesi: vwap-basarisizligi-lower-high-short.
    Kaynak: platform kural notu 'Parabolik short: VWAP başarısızlığı (first crack + lower high)' (kural özeti; özet stop/hedefte kesikti).
    VWAP = seans (UTC günü) içi kümülatif hacim ağırlıklı tipik fiyat. Aşamalar: (1) 'ilk çatlak': en az min_mum mum geçmiş, en az min_ust
    mum VWAP üstünde kapanmış (zirveden gelen), bir önceki mum VWAP üstünde bu mum altında kapanır; (2) geri test: kapanış VWAP'a/üstüne döner;
    (3) daha düşük tepe: kapanış tekrar VWAP altına iner VE geri test tepesi < çatlağa kadarki seans zirvesi x (1 - lh_tolerans) -> SHORT.
    Kapanış zirveyi aşarsa kurulum geçersiz (reddedilir). Seans başına en çok bir short. Stop = geri test tepesi + tampon_atr x ATR; hedef
    hedef_r x R (VARSAYIM 2R); seans sonu çıkış. dis__vwap-reclaim (VWAP geri kazanma, ters kurulum) ve daytrade__vwap-donus'tan farklı.
    VARSAYIM: min_mum=6, min_ust=3, lh_tolerans=%0.1 (kaynak sayısal eşik vermiyor)."""
    ad = "dis__vwap-basarisizlik-short"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "short", "gun_sonu": 1, "min_mum": 6, "min_ust": 3, "lh_tolerans": 0.001,
                               "tampon_atr": 0.2}
    parametre_izgarasi = {"min_ust": [2, 3, 5], "lh_tolerans": [0.0, 0.001, 0.003], "hedef_r": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        seans = seans_kimligi(m.index, 0.0)
        vw = g.vwap_seans(m["yuksek"], m["dusuk"], m["kapanis"], m["hacim"], seans)["vwap"]
        a = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(p["atr_periyot"]))
        sig, stop = vwap_basarisizlik_sinyali(m, seans, vw, a, int(p["min_mum"]), int(p["min_ust"]), float(p["lh_tolerans"]),
                                              float(p["tampon_atr"]))
        return {"short": pd.Series(sig, index=m.index), "stop_short": pd.Series(stop, index=m.index)}


# =============================================================================== 19
class X2RsiMtf(_Taban):
    """dis__x2-rsi-mtf (daytrade, 1h) — ailesi: x2-rsi-cift-zaman-dilimi.
    Kaynak: Gekko-Strategies (xFFFFF) `!WORKSOP/x2_rsi.js` (kaynak okundu; kod kopyalanmadı).
    Kural (ters/aşırı bölge dönüşü): 'üst' RSI (ust_tf, yalnız kapanmış mumlar; kaynakta interval+5 ve eşikler low+3 / high-5) en son hangi
    aşırı bölgeye girdiyse o yönde kalır (YAPIŞKAN yön: yüksek bölgeye girince 'yüksek', alçak bölgeye girene dek) -- kaynaktaki gerçek
    davranış. Alt (taban TF) RSI(rsi_n) yüksek eşiğin (ust_esik) üstünde `kalici` mum sürerse ve üst yön 'yüksek' ise SHORT (bölge başına
    bir kez); alt RSI alçak eşiğin (100 - ust_esik) altında kalici mum sürerse ve üst yön 'alçak' ise LONG. Çıkış: alt RSI 50'yi karşı
    yöne keser. Stop 2 ATR, hedef 2R.
    VARSAYIM: kaynak ayarları (eşik/kalıcılık) özet dışında: varsayılan 70/30, kalici=1, ust_tf=4h; üst eşikler kaynaktaki gibi
    kaydırılır (alçak +3, yüksek -5)."""
    ad = "dis__x2-rsi-mtf"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "rsi_n": 14, "ust_rsi_n": 14, "ust_tf": "4h", "ust_esik": 70.0,
                               "kalici": 1}
    parametre_izgarasi = {"ust_tf": ["2h", "4h"], "ust_esik": [65.0, 70.0, 75.0], "kalici": [1, 2, 3]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        ur = ust_zaman(m, p["ust_tf"], lambda u: pd.DataFrame({"r": g.rsi(u["kapanis"], int(p["ust_rsi_n"]))}))["r"]
        yuksek_e, alcak_e = float(p["ust_esik"]), 100.0 - float(p["ust_esik"])
        ust_yuksek = ur > (yuksek_e - 5.0)
        ust_alcak = ur < (alcak_e + 3.0)
        yon = pd.Series(np.where(ust_yuksek, 1.0, np.where(ust_alcak, -1.0, np.nan)), index=m.index)
        yon = yon.ffill().where(ur.notna())            # yapışkan yön
        n = int(p["kalici"])
        y_say = ((r > yuksek_e).astype(int).rolling(n, min_periods=n).sum() == n)
        a_say = ((r < alcak_e).astype(int).rolling(n, min_periods=n).sum() == n)
        return {"short": gecis(y_say & (yon == 1)), "long": gecis(a_say & (yon == -1)),
                "cikis_long": yukari_kesis(r, 50.0), "cikis_short": asagi_kesis(r, 50.0)}


# =============================================================================== 20
class ZigzagBacak(_Taban):
    """dis__zigzag-bacak (daytrade, 1h) — ailesi: zigzag-bacak-devami.
    Kaynak: EA31337-strategies `ZigZag/Stg_ZigZag.mqh` (kural özeti; kod kopyalanmadı).
    Kaynak ZigZag yeniden çizer ('son 5 barda üst pivot var, alt pivot yok => yukarı bacak sürüyor'). NEDENSEL karşılık: zigzag
    pivotları yalnız ATR eşiği kadar ters hareketle ONAYLANIR (pivotlar.zigzag_pivotlar, esik_k x ATR); onay mumunda pivot bilinir.
    Yukarı bacak = son onaylı pivot bir DİP'tir (onay_dip > onay_tepe); long koşulu: bu onaydan beri en çok `pencere` mum geçti VE kapanış
    > dip fiyatı. Aşağı bacak aynası. Bacak başına ilk koşul mumunda giriş (durum geçişi). Çıkış: karşı yön pivot onayı (kaynak: kapama
    yoksa karşı açma koşulu çıkış). Stop 2 ATR, hedef yok (çıkış sinyali + stop); hedef_r > 0 verilirse R hedefi.
    VARSAYIM: kaynak derinlik 2 / sapma 1 / geri adım 1 yerine ATR eşiği (esik_k=2 ATR); yön mantığı zayıf (kaynak notu) — bacak DEVAMI oynanır."""
    ad = "dis__zigzag-bacak"
    stil = "daytrade"
    varsayilan_parametreler = {**_ORTAK, "yonler": "ls", "hedef_r": 0.0, "esik_k": 2.0, "pencere": 3}
    parametre_izgarasi = {"esik_k": [1.5, 2.0, 3.0], "pencere": [1, 3, 5], "stop_atr_k": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        p = self.parametreler
        k = m["kapanis"]
        t = zigzag_pivotlar(m["yuksek"], m["dusuk"], k, int(p["atr_periyot"]), float(p["esik_k"]))
        i = pd.Series(np.arange(len(m), dtype=float), index=m.index)
        od, ot = t["son_dip_onay_idx"], t["son_tepe_onay_idx"]
        pen = float(p["pencere"])
        yukari = od.notna() & (ot.isna() | (od > ot)) & ((i - od) < pen) & (k > t["son_dip_fiyat"])
        asagi = ot.notna() & (od.isna() | (ot > od)) & ((i - ot) < pen) & (k < t["son_tepe_fiyat"])
        return {"long": gecis(yukari), "short": gecis(asagi), "cikis_long": t["yeni_tepe"], "cikis_short": t["yeni_dip"]}
