"""D5 — ek_77 belgesinden (stratejiler/ek_kaynaklar/ek_77_strateji.md, 77 açık kaynak strateji incelemesi) kendi
yapımızla yazılan stratejiler. KOD KOPYALANMADI (TuringTrader AGPL, backtesting.py AGPL vb.): yalnız belgedeki kural
anlatımı esas alındı; belge VERİDİR. Ad öneki `dis__`. Ortak: stopu olmayan orijinallere ATR stop (felaket stopu) eklendi;
boyutlandırma (tam sermaye, vol hedefi) motorun risk modülündedir. Hepsi nedensel (lookahead yok).

dis__ifr2 (swing) / dis__ifr2-gun (daytrade)  — belge #18 IFR2 (gabrielweich/jesse-strategies, IFR2/__init__.py)
  Kural: RSI(2) < esik (10) VE kapanış, kripto için uyarlanmış Ichimoku bulutunun (tenkan 20 / kijun 30 / senkou B 120 /
  kaydırma 60) ÜSTÜNDE -> long. Çıkış: kapanış önceki cikis_n (2) mumun en yükseğinin üstüne çıkınca. Short ayna (kapalı).
  Uyarlama: Hilbert Transform trend modu filtresi ATLANDI (TA-Lib iç hesabı belgede tarif edilmemiş). Orijinalde stop yok,
  tüm bakiye -> ATR stop. "-gun" varyantı UTC gün sonunda zorunlu çıkış ekler (1h–4h).

dis__ott-bantlari (scalp, long+short) — belge #20 OB5F_LSv2 (ysdede/jesse_strategies)
  Kural: OTT (KAMA tabanlı Optimized Trend Tracker). Long: KAMA(ott_len_long) OTT'nin bant_long (%1,35) üstündeki üst bandı
  yukarı keser (len 70, %1,70). Short: sinyal ortalaması KAMA(59), OTT(len 31, %3,33)'ün bant_short (%1,84) altındaki alt bandı
  aşağı keser. Stop = giriş anındaki OTT çizgisi; giriş yalnız stop mesafesi <= max_risk (%5,2 / %4,6). Çıkış: sinyal
  ortalamasının OTT çizgisinin karşı tarafına geçmesi veya ters yönde giriş sinyali.
  Uyarlama: orijinal 5m; burada >=15m. Fibonacci benzeri kademeli kâr alma (hyperopt'lu dağılım indeksi) KODLANMADI (belgede
  dağılım yok); long için sinyal ortalaması = OTT'nin kendi KAMA'sı (belgede ayrı verilmemiş) varsayımı.

dis__sparta-whb (swing, yalnız short) — belge #21 Sparta Weak Hands Buster (Superalgos/Algorithmic-Trading-Plugins,
  Trading-Systems/Sparta-WHB-BTC-USDT.json), "Steep" stratejisi
  Kural (1h taban): art arda alti_n (3) kapanış Bollinger(20,2) ortasının altında; kapanış alt bandın altında; kanal_tf (2h)
  Bollinger ortası düşüyor; Bollinger standart sapması / fiyat sapma_min..sapma_max arasında; mum boyu / fiyat < mum_maks;
  taban + ust_tfler (2h,4h,8h,1d) %B ortalaması > pb_ort_esik (30, tam aşırı satım değil). Stop: BB ortasının stop_yuzde (%4)
  üstü. Çıkış: kapanış BB ortasının üstüne çıkınca. Hedef: orta - hedef_k x sapma (4).
  Uyarlama: belgedeki MUTLAK DOLAR eşikleri (sapma 200-1000 USD, mum < 750 USD) BTC'nin 2019-2020 fiyatına bağlıdır (belge
  bunu overfit işareti sayıyor) -> fiyata oranlı hale getirildi (varsayılan 8000 USD'ye karşılık: %2,5 / %12 / %9,4).
  Üst TF'ler htf.ust_zaman ile (yalnız kapanmış mumlar). Geçersiz (taban TF'ye bölünmeyen / küçük) üst TF'ler atlanır.
  ATLANDI: izleyen stop ve P1-P6 kademeli hedef sıkılaştırması (belgede aşama kuralları yok). Taban TF 1h önerilir (STRATEJI_TF).

dis__connors-etf (swing, 1d; 4h çalışır) — belge #24 Connors kısa vadeli ETF setleri (TuringTrader, BooksAndPubs/
  Connors_HighProbEtfTrading.cs; kitap: Connors-Alvarez "High Probability ETF Trading", 2009). `kural` parametresi:
  "r3": RSI(2) üst üste 3 kez düşmüş, 3 gün önceki RSI(2) < 60, bugünkü < 10 -> long; RSI(2) > 70 çık. Short ayna (100-eşik).
  "rsi4": RSI(4) < 25 -> long; RSI(4) > 55 çık (belgede "RSI(4)?" soru işaretli; RSI 25/75 setinin Connors'taki 4 periyodu
    kullanıldı, rsi_n ayarlı). Short: RSI(4) > 75, RSI(4) < 45 çık.
  "uc_gun": 3 gün üst üste düşen tepe VE dip -> long; kapanış > SMA(5) çık. Short ayna.
  Ortak SMA(trend_n=200) trend filtresi (long: kapanış üstünde, short: altında; 0 = kapalı). Orijinal stop yok -> ATR stop.
  ATLANDI: AGGRESSIVE_ON (ikinci yarım pozisyon ile ortalama düşürme: yasak).
  Not: swing__rsi-asiri-donus (rsi_periyot 2, bölgede, trend_ma 200) R3 ile YAKIN ama aynı değil (EMA filtresi, RSI 50 çıkışı,
  üç gün düşüş koşulu yok).

dis__tsmom (swing, 1d) — belge #28 TSMOM, Moskowitz-Ooi-Pedersen (JFE 2012); paperswithbacktest/awesome-systematic-trading
  static/strategies/time-series-momentum-effect.py
  Kural: AY SONU değerlendirme: lookback_ay (12) AY ÖNCEKİ kapanışa göre getiri > 0 -> long, < 0 -> short. İşaret yalnız ay
  sonlarında yenilenir; işaret dönünce çıkış (cikis_long/cikis_short). Geri bakış takvim ayıdır (DateOffset), mum sayısı değil
  (7/24 piyasada 252 mum 12 ay değildir). Ay sonu mumu: kapanışı sonraki aya denk gelen mum (süre yalnız geçmişten kestirilir).
  Uyarlama: portföy/vol hedefi (%10 yıllık, ters vol ağırlık, kaldıraç 4) KODLANMADI (büyüklük motorda); tek varlıkta ayrık
  işlem + ATR felaket stopu. Stopla çıkıldıktan sonra yeniden giriş bir sonraki ay sonunda.

dis__ibs-donus (swing, 1d) — belge #33 IBS ortalamaya dönüş (QuantConnect/Lean, Algorithm.Python/Alphas/
  GlobalEquityMeanReversionIBSAlpha.py)
  Kural: IBS = (kapanış - düşük) / (yüksek - düşük). IBS < alt (0,2) -> long; IBS > ust (0,8) -> çık. Short (kapalı): IBS > ust ->
  short, IBS < alt -> çık. Opsiyonel SMA(trend_n) filtresi. Orijinal: kesitsel (en düşük/yüksek 2 ETF) ve 1 gün süre, stop yok
  -> tek varlık eşik kuralı, maks_tutma (0=kapalı) ile gün sınırı, ATR stop. Sinyal kapanışta, dolum sonraki açılışta (belgenin
  uyardığı "kapanışta işlem" iyimserliği yok).

dis__dual-thrust (daytrade) — belge #36 Dual Thrust (letianzj/QuantResearch backtest/dual_thrust.py; je-suis-tm/quant-trading),
  #62 VIX Dual Thrust (QuantConnect/Lean VIXDualThrustAlpha.py) ve #67 TqSdk Dual Thrust bu stratejiyle BİRLEŞTİRİLDİ.
  Kural: ÖNCEKİ n TAMAMLANMIŞ seansın HH, LL, HC, LC değerleri; aralık = max(HH-LC, HC-LL). Seans açılışı O; üst tetik O+k1 x aralık,
  alt tetik O-k2 x aralık. Kapanış üst tetiği İLK kez aşınca long, alt tetiğin altına inince short; ters tetikte pozisyon çevrilir;
  seans sonunda çıkış. Seans: "utc_gun" veya "abd_hisse" (09:30-16:00 New York, d4 seans_cerceve; gece taşınmaz).
  BELGEDEKİ HATA DÜZELTİLDİ: orijinallerde aralık hesabına BUGÜNÜN barı da giriyordu (tetik bugünün tepe/dibi bilinerek
  hesaplanıyordu = lookahead); burada aralık yalnız önceki n seanstan gelir (özet seans başına alınıp shift(1) edilir).
  Uyarlama: always-in-the-market yerine seans içi çevirme + seans sonu çıkışı; ATR stop (orijinalde yok).

dis__r-breaker (daytrade) — belge #37 R-Breaker (letianzj/QuantResearch backtest/r_breaker.py; Saidenberg 1994)
  Kural: önceki seansın H/L/C'sinden P=(H+L+C)/3; R3=H+2(P-L) (kırılım al), R2=P+(H-L) (gözlem sat), R1=2P-L (dönüş sat),
  S1=2P-H (dönüş al), S2=P-(H-L) (gözlem al), S3=L-2(H-P) (kırılım sat). Kırılım: kapanış > R3 -> long, < S3 -> short.
  Dönüş: bugünün ÖNCEKİ mumlarının tepesi R2'yi aştı ve kapanış R1'in altına indi -> short; düşüğü S2'nin altına indi ve kapanış
  S1'in üstüne çıktı -> long. Ters sinyal açık pozisyonu çevirir; seans sonunda çıkış.
  BELGEDEKİ BELİRSİZLİK GİDERİLDİ: orijinalde "bugünün tepesi ve kapanışı aynı barda karşılaştırılıyor, sıralama belirsiz";
  burada gözlem koşulu yalnız mevcut mumdan ÖNCEKİ mumların tepesi/dibi ile kurulur. Orijinalde kullanılmayan stop_loss_price
  yerine ATR stop. `kollar`: ikisi | kirilim | donus.  Dönüş kolu klasik R-Breaker gibi pozisyonsuzken de giriş verir.

dis__gun-ici-donus (daytrade, 1h) — belge #61 Intraday FX Reversal (QuantConnect/Lean IntradayReversalCurrencyMarketsAlpha.py;
  LeBaron-Zhao "Intraday Foreign Exchange Reversals")
  Kural: yerel saatle [pencere_bas, pencere_bit) (10:00-15:00 New York) kapanan mumlarda: kapanış < SMA(5) x (1-esik) -> long,
  > SMA x (1+esik) -> short; yalnız durum DEĞİŞTİĞİNDE sinyal; pozisyon pencere sonunda (15:00) kapanır.
  Uyarlama: belgedeki tek yönlü karşılaştırma (SMA x 1,001'in altı/üstü, nötr bölge yok) simetrik +-esik bandına çevrildi.
  "abd_hisse" seansında saatler New York, "utc_gun"da UTC'dir (genel gün içi dönüş: XAU/WTI/kripto için pencere ayarlanır).

dis__e0v1en (scalp, 15m, yalnız long) — belge #16 E0V1EN (ssssi/freqtrade_strs, binance/dry_run/E0V1EN.py)
  Kural (buy_1): RSI(20) düşüyor, RSI(4) < 40, RSI(14) > 42, kapanış < SMA(15) x 0,973, CTI(20) < 0,69, 24 saatlik değişim
  -%15..+%50. (buy_new): RSI(4) < 34, RSI(14) > 28, kapanış < SMA(15) x 0,96, aynı CTI/24s/RSI(20) koşulları ("benzer" denen
  yer varsayım). Çıkış: hızlı stokastik %K > 84 veya CCI > 80. Zaman çıkışı zaman_cikisi mum. Stop: stop_yuzde (orijinal -%25 çok
  geniş; 15m için %6). Orijinal 5m -> 15m (24s = 96 mum).
  Uyarlama: custom_exit'teki "kâr > -%3 iken CCI" ve "7s/10s kâr eşikli zaman çıkışı" pozisyon kârına bakar (vektörel sinyalde
  yok) -> tek zaman çıkışı. CCI periyodu belgede yok (20 varsayım). Trailing stop (+%3 sonrası %0,2) CikisAyarlari ile verilebilir.

dis__ema50-200-geri (swing) — belge #71 krosenfeld7/pine_script_strategies (50_EMA+200_EMA/50_EMA+200_EMA_Long_Strategy.txt)
  Kural: son geri (3) mum içinde kapanış EMA50'yi yukarı kesti, mevcut mum yeşil ve EMA50'nin üstünde, EMA50 > EMA200; önceki
  geri mumda aynı sinyal yok -> long. Short ayna. Çıkış: %stop_yuzde stop, %hedef_yuzde hedef, zaman_cikisi (100) mum.
  BELGEDEKİ HATA DÜZELTİLDİ: orijinalde short koşulunun "önceki sinyal" kontrolü yanlışlıkla longCondition kullanıyordu; burada
  short kendi koşulunu kullanır.

Kodlanmayan / ayar olarak eklenen belge maddeleri:
  #14 CryptoFrog atlandı (kural belgede eksik: düzleştirilmiş HA dibi, SQZMI, VFI tanımsız; "any old SQZMI shit" notu).
  #60 JamesORB -> daytrade__orb ayarı (ek77:60). #62/#67 -> dis__dual-thrust ayarı (ek77:62). #36 -> ek77:36.
  #19 -> swing__donchian-kirilim ayarı (ek77:19). #17, #69, #72(SmaCross) mevcut ayarlarla aynı. #70, #73, #72(çok TF RSI) atlandı.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve, gun_sonu_uygula
from motor.strateji.dis._gosterge_d3 import hizli_stokastik
from motor.strateji.dis._gosterge_d4 import mum_gun_tahmin
from motor.strateji.dis._gosterge_d5 import (
    cti, gun_ici_cerceve, kama, onceki_seans_hlc, onceki_seanslar_ozeti, ott, seans_bilgi, yerel_saat_kapanis)
from motor.strateji.htf import ust_zaman
from motor.strateji.temel import Strateji
from motor.veri.depo import aralik_suresi

_NY = "America/New_York"


def _bos(index):
    return pd.Series(False, index=index)


def _bool(s, index):
    return s.reindex(index).fillna(False).astype(bool)


# =============================================================================== IFR2
class _Ifr2Taban(Strateji):
    varsayilan_parametreler = {
        "rsi_n": 2, "esik": 10.0, "tenkan": 20, "kijun": 30, "senkou_b": 120, "kayma": 60,
        "cikis_n": 2, "short": False, "stop_atr_k": 3.0, "atr_periyot": 14,
    }
    parametre_izgarasi = {
        "esik": [5.0, 10.0, 15.0],
        "cikis_n": [2, 3, 5],
        "stop_atr_k": [2.0, 3.0, 4.0],
    }
    _gun_sonu = False

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        r = g.rsi(k, int(p["rsi_n"]))
        bulut = b.ichimoku(y, d, int(p["tenkan"]), int(p["kijun"]), int(p["senkou_b"]), int(p["kayma"]))
        n = int(p["cikis_n"])
        onc_yuksek = y.shift(1).rolling(n, min_periods=n).max()
        onc_dusuk = d.shift(1).rolling(n, min_periods=n).min()
        long_ok = (r < p["esik"]) & (k > bulut["bulut_ust"])
        short_ok = ((r > 100.0 - p["esik"]) & (k < bulut["bulut_alt"])) if p["short"] else _bos(mumlar.index)
        a = g.atr(y, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        out = cerceve(mumlar, long_ok, short_ok, k - a, k + a)
        out["cikis_long"] = (k > onc_yuksek).fillna(False)
        out["cikis_short"] = (k < onc_dusuk).fillna(False)
        return gun_sonu_uygula(out, 0.0) if self._gun_sonu else out


class Ifr2(_Ifr2Taban):
    ad = "dis__ifr2"
    stil = "swing"


class Ifr2GunIci(_Ifr2Taban):
    ad = "dis__ifr2-gun"
    stil = "daytrade"
    _gun_sonu = True


# =============================================================================== OTT bantları
class OttBantlari(Strateji):
    ad = "dis__ott-bantlari"
    stil = "scalp"
    varsayilan_parametreler = {
        "ott_len_long": 70, "ott_pct_long": 1.70, "bant_long": 0.0135, "sinyal_len_long": 0, "max_risk_long": 5.2,
        "ott_len_short": 31, "ott_pct_short": 3.33, "bant_short": 0.0184, "sinyal_len_short": 59, "max_risk_short": 4.6,
        "long": True, "short": True,
    }
    parametre_izgarasi = {
        "ott_len_long": [50, 70, 90],
        "ott_pct_long": [1.0, 1.7, 2.5],
        "ott_pct_short": [2.0, 3.33, 5.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    @staticmethod
    def _taraf(kap, n, yuzde, sinyal_n):
        ma = kama(kap, int(n))
        hat = ott(ma, float(yuzde))
        sig = ma if int(sinyal_n) <= 0 else kama(kap, int(sinyal_n))
        return sig, hat

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        k = mumlar["kapanis"]
        sig_l, hat_l = self._taraf(k, p["ott_len_long"], p["ott_pct_long"], p["sinyal_len_long"])
        sig_s, hat_s = self._taraf(k, p["ott_len_short"], p["ott_pct_short"], p["sinyal_len_short"])
        long_kes = _bool(b.yukari_kesis(sig_l, hat_l * (1 + p["bant_long"])), mumlar.index)
        short_kes = _bool(b.asagi_kesis(sig_s, hat_s * (1 - p["bant_short"])), mumlar.index)
        risk_l = (k - hat_l) / k * 100.0
        risk_s = (hat_s - k) / k * 100.0
        long_ok = long_kes & (risk_l <= p["max_risk_long"]) if p["long"] else _bos(mumlar.index)
        short_ok = short_kes & (risk_s <= p["max_risk_short"]) if p["short"] else _bos(mumlar.index)
        out = cerceve(mumlar, long_ok, short_ok, hat_l, hat_s)
        out["cikis_long"] = _bool((sig_l < hat_l) | short_kes, mumlar.index)
        out["cikis_short"] = _bool((sig_s > hat_s) | long_kes, mumlar.index)
        return out


# =============================================================================== Sparta WHB
def _gecerli_ust_tfler(index, tfler, taban_s=None):
    kaynak_s = taban_s if taban_s is not None else pd.Series(index).diff().median()
    sonuc = []
    for tf in str(tfler).replace(" ", "").split(","):
        if not tf:
            continue
        try:
            s = aralik_suresi(tf)
        except ValueError:
            continue
        if s > kaynak_s and s % kaynak_s == pd.Timedelta(0):
            sonuc.append(tf)
    return sonuc


def _bb_tf(ust: pd.DataFrame, n: int, sapma: float) -> pd.DataFrame:
    bb = g.bollinger(ust["kapanis"], n, sapma)
    pb = (ust["kapanis"] - bb["alt"]) / (bb["ust"] - bb["alt"]).where(bb["ust"] != bb["alt"]) * 100.0
    onc = bb["orta"].shift(1)
    egim = (bb["orta"] < onc).astype(float).where(bb["orta"].notna() & onc.notna())
    return pd.DataFrame({"pb": pb, "dusus": egim})


class SpartaWhb(Strateji):
    ad = "dis__sparta-whb"
    stil = "swing"
    varsayilan_parametreler = {
        "bb_n": 20, "bb_sapma": 2.0, "alti_n": 3, "sapma_min": 0.025, "sapma_maks": 0.12, "mum_maks": 0.094,
        "kanal_tf": "2h", "ust_tfler": "2h,4h,8h,1d", "pb_ort_esik": 30.0,
        "stop_yuzde": 0.04, "hedef_k": 4.0,
    }
    parametre_izgarasi = {
        "stop_yuzde": [0.03, 0.04, 0.0525],
        "pb_ort_esik": [20.0, 30.0, 40.0],
        "hedef_k": [0.0, 3.0, 4.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = mumlar.index
        k, y, d = mumlar["kapanis"], mumlar["yuksek"], mumlar["dusuk"]
        n, sp = int(p["bb_n"]), float(p["bb_sapma"])
        bb = g.bollinger(k, n, sp)
        sd = (bb["ust"] - bb["orta"]) / sp
        taban_pb = (k - bb["alt"]) / (bb["ust"] - bb["alt"]).where(bb["ust"] != bb["alt"]) * 100.0
        ustler = _gecerli_ust_tfler(idx, p["ust_tfler"])
        pb_listesi = [taban_pb]
        for tf in ustler:
            pb_listesi.append(ust_zaman(mumlar, tf, lambda u: _bb_tf(u, n, sp))["pb"])
        pb_ort = pd.concat(pb_listesi, axis=1).mean(axis=1, skipna=False)
        kanal = str(p["kanal_tf"])
        if kanal not in ustler and ustler:
            kanal = ustler[0]
        if ustler:
            dusus = ust_zaman(mumlar, kanal, lambda u: _bb_tf(u, n, sp))["dusus"] == 1.0
        else:
            dusus = (bb["orta"] < bb["orta"].shift(1))
        alti = (k < bb["orta"]).astype(int).rolling(int(p["alti_n"]), min_periods=int(p["alti_n"])).sum() == int(p["alti_n"])
        oran = sd / k
        short_ok = (alti & (k < bb["alt"]) & dusus & (oran >= p["sapma_min"]) & (oran <= p["sapma_maks"])
                    & ((y - d) / k < p["mum_maks"]) & (pb_ort > p["pb_ort_esik"]))
        stop_s = bb["orta"] * (1 + p["stop_yuzde"])
        hedef_s = None
        if p["hedef_k"] > 0:
            hedef_s = np.minimum(bb["orta"] - p["hedef_k"] * sd, k * 0.998)
        out = cerceve(mumlar, _bos(idx), short_ok, pd.Series(np.nan, index=idx), stop_s, None, hedef_s)
        out["cikis_short"] = _bool(k > bb["orta"], idx)
        return out


# =============================================================================== Connors ETF setleri
class ConnorsEtf(Strateji):
    ad = "dis__connors-etf"
    stil = "swing"
    varsayilan_parametreler = {
        "kural": "r3", "trend_n": 200, "short": True,
        "r3_giris": 10.0, "r3_cikis": 70.0, "r3_onceki": 60.0,
        "rsi_n": 4, "rsi_giris": 25.0, "rsi_cikis": 55.0,
        "uc_ardisik": 3, "uc_cikis_sma": 5,
        "stop_atr_k": 4.0, "atr_periyot": 14,
    }
    parametre_izgarasi = {
        "kural": ["r3", "rsi4", "uc_gun"],
        "trend_n": [0, 200],
        "stop_atr_k": [2.5, 4.0, 6.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = mumlar.index
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        kural = p["kural"]
        if kural == "r3":
            r = g.rsi(k, 2)
            dus3 = (r < r.shift(1)) & (r.shift(1) < r.shift(2)) & (r.shift(2) < r.shift(3))
            yuk3 = (r > r.shift(1)) & (r.shift(1) > r.shift(2)) & (r.shift(2) > r.shift(3))
            long_ok = dus3 & (r.shift(3) < p["r3_onceki"]) & (r < p["r3_giris"])
            short_ok = yuk3 & (r.shift(3) > 100.0 - p["r3_onceki"]) & (r > 100.0 - p["r3_giris"])
            cikis_l, cikis_s = r > p["r3_cikis"], r < 100.0 - p["r3_cikis"]
        elif kural == "rsi4":
            r = g.rsi(k, int(p["rsi_n"]))
            long_ok, short_ok = r < p["rsi_giris"], r > 100.0 - p["rsi_giris"]
            cikis_l, cikis_s = r > p["rsi_cikis"], r < 100.0 - p["rsi_cikis"]
        elif kural == "uc_gun":
            m = int(p["uc_ardisik"])
            dus = ((y < y.shift(1)) & (d < d.shift(1))).astype(int).rolling(m, min_periods=m).sum() == m
            yuk = ((y > y.shift(1)) & (d > d.shift(1))).astype(int).rolling(m, min_periods=m).sum() == m
            long_ok, short_ok = dus, yuk
            s5 = g.sma(k, int(p["uc_cikis_sma"]))
            cikis_l, cikis_s = k > s5, k < s5
        else:
            raise ValueError("kural 'r3', 'rsi4' veya 'uc_gun' olmalı")
        if int(p["trend_n"]) > 0:
            trend = g.sma(k, int(p["trend_n"]))
            long_ok &= k > trend
            short_ok &= k < trend
        if not p["short"]:
            short_ok = _bos(idx)
        a = g.atr(y, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        out = cerceve(mumlar, long_ok, short_ok, k - a, k + a)
        out["cikis_long"] = _bool(cikis_l, idx)
        out["cikis_short"] = _bool(cikis_s, idx)
        return out


# =============================================================================== TSMOM
def ay_sonu_mumu(index: pd.DatetimeIndex) -> np.ndarray:
    """Mumun KAPANIŞ anı bir sonraki takvim ayına denk geliyorsa True. Mum süresi yalnız geçmişten kestirilir
    (şimdiye kadarki en küçük aralık); ilk mum False. Serinin geleceğine bağlı değildir."""
    n = len(index)
    if n < 2:
        return np.zeros(n, dtype=bool)
    idx = index.tz_convert("UTC") if index.tz is not None else index
    fark = ((idx[1:] - idx[:-1]) / pd.Timedelta(seconds=1)).to_numpy()
    sure = np.r_[np.nan, np.minimum.accumulate(fark)]
    gecerli = ~np.isnan(sure)
    kap = idx + pd.to_timedelta(np.where(gecerli, sure, 0.0), unit="s")
    ay = lambda t: (t.tz_localize(None) if t.tz is not None else t).to_period("M").asi8  # noqa: E731
    return (ay(kap) != ay(idx)) & gecerli


def gecmis_getiri(kapanis: pd.Series, ay: int) -> pd.Series:
    """Her mum için kapanış / (t - ay takvim ayı ve öncesindeki SON kapanış) - 1. Veri o tarihte başlamadıysa NaN."""
    idx = kapanis.index
    hedef = idx - pd.DateOffset(months=int(ay))
    poz = idx.searchsorted(hedef, side="right") - 1
    c = kapanis.to_numpy(dtype=float)
    ref = np.where(poz >= 0, c[np.clip(poz, 0, None)], np.nan)
    ref = np.where(hedef >= idx[0], ref, np.nan)
    return pd.Series(c / ref - 1.0, index=idx)


class Tsmom(Strateji):
    ad = "dis__tsmom"
    stil = "swing"
    varsayilan_parametreler = {"lookback_ay": 12, "short": True, "atr_k": 5.0, "atr_periyot": 14}
    parametre_izgarasi = {
        "lookback_ay": [3, 6, 12],
        "atr_k": [3.0, 5.0, 8.0],
        "short": [True, False],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = mumlar.index
        k = mumlar["kapanis"]
        ret = gecmis_getiri(k, int(p["lookback_ay"]))
        yenile = pd.Series(ay_sonu_mumu(idx), index=idx) & ret.notna()
        isaret = np.sign(ret).where(yenile).ffill()
        long_ok = yenile & (ret > 0)
        short_ok = (yenile & (ret < 0)) if p["short"] else _bos(idx)
        a = g.atr(mumlar["yuksek"], mumlar["dusuk"], k, int(p["atr_periyot"])) * p["atr_k"]
        out = cerceve(mumlar, long_ok, short_ok, k - a, k + a)
        out["cikis_long"] = _bool(isaret < 0, idx)
        out["cikis_short"] = _bool(isaret > 0, idx)
        return out


# =============================================================================== IBS
class IbsDonus(Strateji):
    ad = "dis__ibs-donus"
    stil = "swing"
    varsayilan_parametreler = {
        "alt": 0.2, "ust": 0.8, "trend_n": 0, "short": False, "maks_tutma": 0,
        "stop_atr_k": 3.0, "atr_periyot": 14,
    }
    parametre_izgarasi = {
        "alt": [0.1, 0.2, 0.3],
        "ust": [0.7, 0.8, 0.9],
        "stop_atr_k": [2.0, 3.0, 5.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = mumlar.index
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        ibs = (k - d) / (y - d).where(y != d)
        long_ok, short_ok = ibs < p["alt"], (ibs > p["ust"]) & bool(p["short"])
        if int(p["trend_n"]) > 0:
            trend = g.sma(k, int(p["trend_n"]))
            long_ok &= k > trend
            short_ok &= k < trend
        a = g.atr(y, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        out = cerceve(mumlar, long_ok, short_ok, k - a, k + a)
        out["cikis_long"] = _bool(ibs > p["ust"], idx)
        out["cikis_short"] = _bool(ibs < p["alt"], idx)
        if int(p["maks_tutma"]) > 0:
            out["zaman_cikisi_mum"] = pd.Series(np.where(out["yon"] != 0, float(p["maks_tutma"]), np.nan), index=idx)
        return out


# =============================================================================== Dual Thrust
class DualThrust(Strateji):
    ad = "dis__dual-thrust"
    stil = "daytrade"
    varsayilan_parametreler = {
        "n": 4, "k1": 0.5, "k2": 0.5, "seans": "utc_gun", "short": True, "stop_atr_k": 3.0, "atr_periyot": 14,
    }
    parametre_izgarasi = {
        "n": [3, 5, 10],
        "k1": [0.3, 0.5, 0.7],
        "stop_atr_k": [2.0, 3.0, 4.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def seviyeler(self, mumlar: pd.DataFrame):
        """-> (ust tetik, alt tetik, hazır) ; aralık yalnız önceki n seanstan gelir."""
        p = self.parametreler
        bilgi = seans_bilgi(mumlar, p["seans"])
        oz = onceki_seanslar_ozeti(mumlar, bilgi["sid"], bilgi["ici"], int(p["n"]))
        aralik = np.maximum(oz["hh"] - oz["lc"], oz["hc"] - oz["ll"])
        ac = bilgi["acilis"]
        hazir = bilgi["acilis_tamam"] & aralik.notna() & (aralik > 0)
        return ac + p["k1"] * aralik, ac - p["k2"] * aralik, hazir, bilgi

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        if p["seans"] not in ("utc_gun", "abd_hisse"):
            raise ValueError("seans 'abd_hisse' veya 'utc_gun' olmalı")
        idx = mumlar.index
        k = mumlar["kapanis"]
        ust, alt, hazir, bilgi = self.seviyeler(mumlar)
        long_t = hazir & (k > ust)
        short_t = hazir & (k < alt)
        long_ok = b.gecis(long_t)
        short_ok = b.gecis(short_t) if p["short"] else _bos(idx)
        a = g.atr(mumlar["yuksek"], mumlar["dusuk"], k, int(p["atr_periyot"])) * p["stop_atr_k"]
        return gun_ici_cerceve(mumlar, p["seans"], bilgi["c"], long_ok, short_ok, k - a, k + a,
                               cikis_long=short_t, cikis_short=long_t)


# =============================================================================== R-Breaker
class RBreaker(Strateji):
    ad = "dis__r-breaker"
    stil = "daytrade"
    varsayilan_parametreler = {
        "seans": "utc_gun", "kollar": "ikisi", "kirilim_k": 2.0, "short": True, "stop_atr_k": 2.5, "atr_periyot": 14,
    }
    parametre_izgarasi = {
        "kollar": ["ikisi", "kirilim", "donus"],
        "stop_atr_k": [1.5, 2.5, 4.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def seviyeler(self, mumlar: pd.DataFrame, bilgi: dict) -> pd.DataFrame:
        """Önceki seansın H/L/C'sinden: r3, r2, r1, s1, s2, s3 (+ pivot)."""
        hlc = onceki_seans_hlc(mumlar, bilgi["sid"], bilgi["ici"])
        h, l, c = hlc["h"], hlc["l"], hlc["c"]
        pv = (h + l + c) / 3.0
        kk = float(self.parametreler["kirilim_k"])
        return pd.DataFrame({
            "pivot": pv, "r3": h + kk * (pv - l), "r2": pv + (h - l), "r1": 2 * pv - l,
            "s1": 2 * pv - h, "s2": pv - (h - l), "s3": l - kk * (h - pv)}, index=mumlar.index)

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        if p["seans"] not in ("utc_gun", "abd_hisse"):
            raise ValueError("seans 'abd_hisse' veya 'utc_gun' olmalı")
        if p["kollar"] not in ("ikisi", "kirilim", "donus"):
            raise ValueError("kollar 'ikisi', 'kirilim' veya 'donus' olmalı")
        idx = mumlar.index
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        bilgi = seans_bilgi(mumlar, p["seans"])
        sid, ici = bilgi["sid"], bilgi["ici"]
        sv = self.seviyeler(mumlar, bilgi)
        # bugünün ÖNCEKİ mumlarının tepe/dibi (mevcut mum hariç: sıralama belirsizliği yok)
        gun_yuk = y.where(ici).groupby(sid).cummax().groupby(sid).shift(1)
        gun_dus = d.where(ici).groupby(sid).cummin().groupby(sid).shift(1)
        hazir = pd.Series(ici, index=idx) & sv["r3"].notna()
        long_k = hazir & (k > sv["r3"])
        short_k = hazir & (k < sv["s3"])
        long_d = hazir & (gun_dus <= sv["s2"]) & (k > sv["s1"])
        short_d = hazir & (gun_yuk >= sv["r2"]) & (k < sv["r1"])
        bos = _bos(idx)
        long_ok = (long_k if p["kollar"] != "donus" else bos) | (long_d if p["kollar"] != "kirilim" else bos)
        short_ok = (short_k if p["kollar"] != "donus" else bos) | (short_d if p["kollar"] != "kirilim" else bos)
        ters_short = short_ok          # short sinyali açık long'u çevirir (short kapalıysa yalnız long'u kapatır)
        if not p["short"]:
            short_ok = bos
        a = g.atr(y, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        return gun_ici_cerceve(mumlar, p["seans"], bilgi["c"], long_ok, short_ok, k - a, k + a,
                               cikis_long=ters_short, cikis_short=long_ok)


# =============================================================================== gün içi dönüş (saatlik)
class GunIciDonus(Strateji):
    ad = "dis__gun-ici-donus"
    stil = "daytrade"
    varsayilan_parametreler = {
        "seans": "abd_hisse", "sma_n": 5, "esik": 0.001, "pencere_bas": 10.0, "pencere_bit": 15.0,
        "short": True, "stop_atr_k": 3.0, "atr_periyot": 14,
    }
    parametre_izgarasi = {
        "sma_n": [3, 5, 8],
        "esik": [0.0005, 0.001, 0.002],
        "stop_atr_k": [2.0, 3.0, 4.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        if p["seans"] not in ("utc_gun", "abd_hisse"):
            raise ValueError("seans 'abd_hisse' veya 'utc_gun' olmalı")
        idx = mumlar.index
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        bilgi = seans_bilgi(mumlar, p["seans"])
        c = bilgi["c"]
        dur_s = c["dur_s"].to_numpy()
        hr = pd.Series(yerel_saat_kapanis(idx, dur_s, _NY if p["seans"] == "abd_hisse" else "UTC"), index=idx)
        dur_h = pd.Series(dur_s / 3600.0, index=idx)
        # sinyal mumunun kapanışı pencere içinde olmalı VE sonraki mum pencere bitişinden önce bitmeli
        giris_ok = (hr >= p["pencere_bas"]) & (hr <= p["pencere_bit"] - dur_h + 1e-9) & pd.Series(bilgi["ici"], index=idx)
        pencere_cik = (hr > p["pencere_bit"] - dur_h + 1e-9) & pd.Series(bilgi["ici"], index=idx)
        sma = g.sma(k, int(p["sma_n"]))
        long_durum = k < sma * (1 - p["esik"])
        short_durum = k > sma * (1 + p["esik"])
        long_ok = giris_ok & b.gecis(long_durum)
        short_ok = (giris_ok & b.gecis(short_durum)) if p["short"] else _bos(idx)
        a = g.atr(y, d, k, int(p["atr_periyot"])) * p["stop_atr_k"]
        return gun_ici_cerceve(mumlar, p["seans"], c, long_ok, short_ok, k - a, k + a,
                               cikis_long=pencere_cik, cikis_short=pencere_cik)


# =============================================================================== E0V1EN
class E0v1en(Strateji):
    ad = "dis__e0v1en"
    stil = "scalp"
    varsayilan_parametreler = {
        "rsi_uzun_n": 20, "rsi4_n": 4, "rsi14_n": 14, "rsi4_esik": 40.0, "rsi14_alt": 42.0, "sma_n": 15, "sma_k": 0.973,
        "yeni_rsi4": 34.0, "yeni_rsi14": 28.0, "yeni_sma_k": 0.96, "cti_n": 20, "cti_esik": 0.69,
        "gun_min": -0.15, "gun_maks": 0.50, "fastk_cikis": 84.0, "cci_n": 20, "cci_cikis": 80.0,
        "zaman_cikisi": 28, "stop_yuzde": 0.06,
    }
    parametre_izgarasi = {
        "sma_k": [0.96, 0.973, 0.985],
        "zaman_cikisi": [16, 28, 40],
        "stop_yuzde": [0.03, 0.06, 0.10],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = mumlar.index
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        r20 = g.rsi(k, int(p["rsi_uzun_n"]))
        r4, r14 = g.rsi(k, int(p["rsi4_n"])), g.rsi(k, int(p["rsi14_n"]))
        sma = g.sma(k, int(p["sma_n"]))
        c = cti(k, int(p["cti_n"]))
        gm = mum_gun_tahmin(idx)
        gun = k.pct_change(gm)
        ortak = (r20 < r20.shift(1)) & (c < p["cti_esik"]) & (gun > p["gun_min"]) & (gun < p["gun_maks"])
        buy1 = ortak & (r4 < p["rsi4_esik"]) & (r14 > p["rsi14_alt"]) & (k < sma * p["sma_k"])
        buy_new = ortak & (r4 < p["yeni_rsi4"]) & (r14 > p["yeni_rsi14"]) & (k < sma * p["yeni_sma_k"])
        fastk = hizli_stokastik(y, d, k, 5, 3)["k"]
        cci = b.cci(y, d, k, int(p["cci_n"]))
        long_ok = buy1 | buy_new
        out = cerceve(mumlar, long_ok, _bos(idx), k * (1 - p["stop_yuzde"]), pd.Series(np.nan, index=idx))
        out["cikis_long"] = _bool((fastk > p["fastk_cikis"]) | (cci > p["cci_cikis"]), idx)
        out["zaman_cikisi_mum"] = pd.Series(np.where(out["yon"] != 0, float(p["zaman_cikisi"]), np.nan), index=idx)
        return out


# =============================================================================== krosenfeld7 EMA50/200
class Ema50200Geri(Strateji):
    ad = "dis__ema50-200-geri"
    stil = "swing"
    varsayilan_parametreler = {
        "ema_orta": 50, "ema_uzun": 200, "geri": 3, "short": True,
        "stop_yuzde": 0.10, "hedef_yuzde": 0.10, "zaman_cikisi": 100,
    }
    parametre_izgarasi = {
        "stop_yuzde": [0.05, 0.10, 0.15],
        "hedef_yuzde": [0.05, 0.10, 0.15],
        "zaman_cikisi": [50, 100, 150],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        idx = mumlar.index
        a, k = mumlar["acilis"], mumlar["kapanis"]
        e1, e2 = g.ema(k, int(p["ema_orta"])), g.ema(k, int(p["ema_uzun"]))
        m = int(p["geri"])
        yuk_kes = _bool(b.yukari_kesis(k, e1), idx).astype(int).rolling(m, min_periods=1).max() > 0
        asa_kes = _bool(b.asagi_kesis(k, e1), idx).astype(int).rolling(m, min_periods=1).max() > 0
        ham_l = yuk_kes & (k > a) & (k > e1) & (e1 > e2)
        ham_s = asa_kes & (k < a) & (k < e1) & (e1 < e2)

        def yeni(ham):
            onceki = pd.concat([ham.shift(i, fill_value=False) for i in range(1, m + 1)], axis=1).any(axis=1)
            return ham & ~onceki

        long_ok = yeni(ham_l)
        short_ok = yeni(ham_s) if p["short"] else _bos(idx)
        out = cerceve(mumlar, long_ok, short_ok, k * (1 - p["stop_yuzde"]), k * (1 + p["stop_yuzde"]),
                      k * (1 + p["hedef_yuzde"]), k * (1 - p["hedef_yuzde"]))
        out["zaman_cikisi_mum"] = pd.Series(np.where(out["yon"] != 0, float(p["zaman_cikisi"]), np.nan), index=idx)
        return out
