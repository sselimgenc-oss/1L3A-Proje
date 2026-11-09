"""D4 sistematik stratejiler: Carver tarzı EWMAC trendi (swing) ve gün içi momentum / trend-day (daytrade).

KOD KOPYALANMADI (pysystemtrade GPL): yalnız kamuya açık kurallar kendi yapımızla yazıldı.

dis__ewmac-carver  (swing, 4h ve 1d)
  Kaynak: Robert Carver, *Systematic Trading* (2015), *Leveraged Trading* (2019) ve qoppac.blogspot.com yazıları (EWMAC).
  Kural: ham tahmin = (EWMA_hızlı - EWMA_yavaş) / (fiyat x günlük getiri std'si); her varyant Carver'ın yayımlanmış sabit ölçeğiyle
    (2/8:10.6, 4/16:7.5, 8/32:5.3, 16/64:3.75, 32/128:2.65, 64/256:1.87) ortalama |tahmin| ~10 olacak biçimde ölçeklenir, +-20'ye
    kırpılır; kombine tahmin = seçili varyantların ortalaması x çeşitlendirme çarpanı (1.3, sabit), tekrar +-20. Sabit ölçek
    kullanıldığı için lookahead yoktur. Std = günlük getirilerin üstel std'si (span 25 gün).
  Zaman dilimi: varyant adları GÜN cinsindendir. 1d'de doğrudan; 4h'de EMA/std aralıkları gün x günlük_mum (kripto 6) mum olur
    ve mum getiri std'si sqrt(günlük_mum) ile günlük eşdeğere çevrilir (gun_mum 0 = ilk 200 mum aralığından otomatik).
  Uyarlama (motor stoplu, sabit %1 riskli AYRIK işlem yapar): tahmin > +esik -> long, < -esik -> short (short parametreli, açık).
    Çıkış: long, tahmin < cikis_esik olunca; short, tahmin > -cikis_esik olunca (varsayılan 0 = işaret dönünce). Stop: Carver'da
    stop YOKTUR; burada motorun zorunlu kıldığı FELAKET stopu k x ATR (varsayılan 5; ızgara 3/5/8). Stopla çıkıldıktan sonra
    tahmin hâlâ eşiğin ötesindeyse bir sonraki mumda yeniden giriş sinyali oluşur.
  ALINMADI: sürekli pozisyon ayarlama (tahminle orantılı büyüklük), volatilite hedefli boyutlandırma, tahmin ağırlık/IDM tahmini,
    uzun vadeli vol harmanı, pozisyon atalet (buffer) bölgesi. Büyüklük motorun risk modülündedir.
  EWMAC + FUNDING CARRY varyantı ATLANDI: Strateji.sinyaller(mumlar) yalnız mumları alır, funding motora (backtest(funding=...))
    gider; stratejiye geçmez. Motoru değiştirmemek için kodlanmadı.

dis__trend-gun-ici  (daytrade)
  Kaynak: Ernie Chan, *Algorithmic Trading* (2013) gün içi momentum bölümü; Gao, Han, Li, Zhou (2018) "Market intraday momentum"
    (seans başı getirisi son saatin getirisini öngörür).
  Kural: seans açılışından karar anına kadarki getiri r = kapanış/seans_açılışı - 1. |r| eşiği aşarsa karar mumunda (kapanışı
    seans kapanışından giris_dk dakika önce veya daha erken olan SON mum) r yönünde giriş (sonraki açılışta dolum), seans sonunda
    zorunlu çıkış. Eşik: "sigma" modunda esik_k x (önceki gecmis_gun seansın aynı aralık getirisi std'si; bugün dahil değil),
    "sabit" modunda esik_sabit. Stop k x ATR.
  Seans: "abd_hisse" = 09:30-16:00 America/New_York (zoneinfo; Mart/Kasım DST geçişinde UTC karşılığı kayar, UTC indeksten
    nedensel), "utc_gun" = UTC günü (24 saat piyasalar; gun_sonu_uygula ile uyumlu: günün son mumunda çıkış).
  Atlanan günler: açılış mumu eksik/geç başlıyorsa (tatil, veri deliği) ya da karar mumu yoksa (erken kapanış) o gün giriş yok.
    Gece pozisyonu taşınmaz.
  DİKKAT (dolum): motor çıkışı sinyal mumunu izleyen AÇILIŞTA yapar. abd_hisse'de seans sonrası mum yoksa son mumun çıkışı ertesi
    günün açılışına kayardı; bu yüzden çıkış, kapanıştan bir mum ÖNCE (son mumun açılışında) yapılır. Karar mumu bu çıkış
    penceresine denk gelirse (giris_dk <= mum süresi; örn. 1h mumda giris_dk 30/60, 30m mumda giris_dk 30) o gün gece taşımamak
    için giriş YAPILMAZ: abd_hisse'de 15m (30/60 dk) ve 30m (60 dk) kullanın. utc_gun'da mumlar kesintisiz olduğundan çıkış tam
    gün sonu açılışındadır.
  ALINMADI: seans içi ek giriş, açılış boşluğu (gap) varyantı, hacim süzgeci.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.dis._gosterge_d4 import (
    birlesik_tahmin, mum_gun_tahmin, seans_cerceve, varyantlari_coz)
from motor.strateji.temel import Strateji


class EwmacCarver(Strateji):
    ad = "dis__ewmac-carver"
    stil = "swing"
    varsayilan_parametreler = {
        "varyantlar": "16/64+32/128+64/256", "esik": 5.0, "cikis_esik": 0.0, "cesit_carpani": 1.3,
        "std_gun": 25, "gun_mum": 0, "short": True, "atr_k": 5.0, "atr_periyot": 14,
    }
    parametre_izgarasi = {
        "varyantlar": ["2/8+4/16+8/32", "16/64+32/128", "32/128+64/256"],
        "esik": [3.0, 5.0, 10.0],
        "atr_k": [3.0, 5.0, 8.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def tahmin(self, mumlar: pd.DataFrame) -> pd.Series:
        p = self.parametreler
        gm = mum_gun_tahmin(mumlar.index, int(p["gun_mum"]))
        return birlesik_tahmin(mumlar["kapanis"], varyantlari_coz(p["varyantlar"]), gm,
                               float(p["cesit_carpani"]), int(p["std_gun"]))

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        f = self.tahmin(mumlar)
        kap = mumlar["kapanis"]
        a = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_periyot"])) * p["atr_k"]
        long_ok = f > p["esik"]
        short_ok = (f < -p["esik"]) if p["short"] else pd.Series(False, index=mumlar.index)
        out = cerceve(mumlar, long_ok, short_ok, kap - a, kap + a)
        out["cikis_long"] = (f < p["cikis_esik"]).fillna(False)
        out["cikis_short"] = (f > -p["cikis_esik"]).fillna(False)
        return out


class TrendGunIci(Strateji):
    ad = "dis__trend-gun-ici"
    stil = "daytrade"
    varsayilan_parametreler = {
        "seans": "utc_gun", "giris_dk": 60, "esik_modu": "sigma", "esik_k": 1.0, "esik_sabit": 0.01,
        "gecmis_gun": 20, "short": True, "stop_atr_k": 3.0, "atr_periyot": 14,
    }
    parametre_izgarasi = {
        "esik_modu": ["sigma", "sabit"],
        "esik_k": [0.5, 1.0],
        "giris_dk": [30, 60],
        "stop_atr_k": [2.0, 3.0, 4.0],
    }

    def cikis_var_mi(self) -> bool:
        return True

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        if p["esik_modu"] not in ("sigma", "sabit"):
            raise ValueError("esik_modu 'sigma' veya 'sabit' olmalı")
        idx = mumlar.index
        kap = mumlar["kapanis"]
        c = seans_cerceve(idx, p["seans"], p["giris_dk"])
        ici = c["seans_ici"].to_numpy()
        sid = c["sid"].to_numpy()
        ac_ref = mumlar["acilis"].where(ici).groupby(sid).transform("first")
        r = kap / ac_ref - 1.0
        # açılış mumu zamanında başlamadıysa (eksik/geç açılış) o gün atlanır
        acilis_tamam = (c["ac_gecikme_s"] < c["dur_s"]).to_numpy()
        karar = c["karar"].to_numpy() & acilis_tamam & r.notna().to_numpy()
        tekrar = pd.Series(sid).where(karar).duplicated().to_numpy()
        karar = pd.Series(karar & ~tekrar, index=idx)          # seans başına tek karar

        if p["esik_modu"] == "sigma":
            n = int(p["gecmis_gun"])
            sigma = r[karar].rolling(n, min_periods=n).std().shift(1)      # yalnız ÖNCEKİ seansların getirisi
            esik = (sigma * p["esik_k"]).reindex(idx)
        else:
            esik = pd.Series(float(p["esik_sabit"]), index=idx)
        long_ok = karar & (r > esik)
        short_ok = (karar & (r < -esik)) if p["short"] else pd.Series(False, index=idx)

        a = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["atr_periyot"])) * p["stop_atr_k"]
        if p["seans"] == "utc_gun":
            return cerceve(mumlar, long_ok, short_ok, kap - a, kap + a, gun_sonu=True, seans_saat=0.0)
        # abd_hisse: çıkış son mumun açılışında (bkz. modül açıklaması); seans dışı mumlarda da çık
        dur = pd.to_timedelta(c["dur_s"].to_numpy(), unit="s")
        kapanis_utc = pd.DatetimeIndex(c["kapanis_utc"])
        bar_kap = pd.DatetimeIndex(c["bar_kapanis"])
        gecerli = ~np.isnan(c["dur_s"].to_numpy())
        erken = np.asarray(bar_kap >= (kapanis_utc - dur))
        cik = pd.Series((erken | ~ici) & gecerli, index=idx)
        long_ok &= ~cik
        short_ok &= ~cik
        return cerceve(mumlar, long_ok, short_ok, kap - a, kap + a, cikis=cik)
