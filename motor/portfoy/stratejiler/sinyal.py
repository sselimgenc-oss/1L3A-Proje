"""Çok sembollü sinyal stratejileri: referans/rejim filtreli long, BTC çekirdek + hedge, RSI çiftleri, IBS dönüşü.

Hepsi günlük (1d), takvim günü pencereli (bkz. ortak.py); pozisyon durumları ileri doğru simüle edilir (nedensel) ve
yalnız durum değişen satırlarda emir üretilir.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.portfoy.stratejiler.ortak import (HEPSI, KRIPTO, ORTAK_PARAMETRELER, PfTemel, degisim_satirlari, ema_gun,
                                             sma_gun)
from motor.strateji import gostergeler as gst


def _linreg_son(seri: pd.DataFrame, n: int) -> pd.DataFrame:
    """Pine linreg(src, n, 0): n barlık en küçük kareler doğrusunun SON noktası (nedensel)."""
    x = np.arange(n, dtype=float)
    xm = x.mean()
    sxx = ((x - xm) ** 2).sum()

    def f(y):
        ym = y.mean()
        b = ((x - xm) * (y - ym)).sum() / sxx
        return ym + b * (n - 1 - xm)

    return seri.rolling(n, min_periods=n).apply(f, raw=True)


def _rsi_tablo(kap: pd.DataFrame, n: int) -> pd.DataFrame:
    return pd.DataFrame({c: gst.rsi(kap[c], n) for c in kap.columns})


class ReferansFiltreliLong(PfTemel):
    """Referans (piyasa/rejim) filtreli trend/momentum long — iki kaynak tek sınıfta.

    Kaynaklar: tv: Crypto momentum strategy (echepata; LazyBear Squeeze Momentum) ve tv: 3% max drawdown - Nasdaq
    benzeri (finnick1111; SPY/QQQ EMA koşullu QQQ long).
    giris="sikisma" (kripto momentum): val = linreg(kapanış - ort(ort(en yüksek yüksek, en düşük düşük), SMA(kapanış)), 20);
      slope = val - val[2]; slope negatiften pozitife DÖNÜNCE (crossover) VE kapanış > EMA(ema_gun) VE EMA eğimi > 0 VE
      referans (ref_sembol; "" = evren eşit ağırlıklı endeksi) kapanışı > EMA(ref_ema) ve EMA eğimi > 0 ise long;
      slope pozitiften negatife dönünce (crossunder) çık. (Kaynakta CRYPTOCAP:TOTAL yerine BTC referansı.)
    giris="ema" (makro/Nasdaq): referans kapanışı son ref_gun günde EMA(ref_ema) üstünde, sembol kapanışı EMA(ema_hizli) ve
      EMA(ema_gun) üstünde, ve son 3 kapanış üst üste düşüş değil -> long; çıkış: sembol kapanışı < EMA(ema_gun) VE referans
      kapanışı < SMA(7). Kaynaktaki ADX>16, SPX ATH/çöküş/BTC yardımcı kolları ve makro ayrıntılar kodlanmadı (belirsiz /
      veri yok); QQQ/SPY yerine hisse sepeti + evren endeksi vekili. Başlangıç %3.5 stopu `iz_stop_yuzde` (iz süren sıkılaşır).
    Ağırlık: aktif her sembol brut/len(semboller). Yeniden dengeleme durum değişince (olay tabanlı).
    """

    ad = "pf__ref_filtreli_long"
    min_sembol = 1
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": KRIPTO, "ref_sembol": "BTCUSDT", "giris": "sikisma",
                               "ema_gun": 50, "ema_hizli": 10, "ref_ema": 50, "ref_gun": 4, "sikisma_gun": 20,
                               "brut": 1.0}
    parametre_izgarasi = {"giris": ["sikisma", "ema"], "ema_gun": [21, 50, 100], "ref_ema": [21, 50, 100]}

    def ek_semboller(self):
        return (self.parametreler["ref_sembol"],)

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        ax = tk.eksen
        kap = tk.kap[kolon]
        if p["ref_sembol"]:
            ref = tk.kap[p["ref_sembol"]]
        else:
            ref = (1.0 + tk.getiri()[kolon].mean(axis=1).fillna(0.0)).cumprod()
        reftbl = pd.DataFrame({c: ref for c in kolon})
        ref_ema = ref.ewm(span=p["ref_ema"], adjust=False, min_periods=p["ref_ema"]).mean()
        ema = ema_gun(kap, p["ema_gun"])
        if p["giris"] == "sikisma":
            n = p["sikisma_gun"]
            hh = tk.panel("yuksek", True)[kolon].rolling(n, min_periods=n).max()
            ll = tk.panel("dusuk", True)[kolon].rolling(n, min_periods=n).min()
            ort = ((hh + ll) / 2.0 + kap.rolling(n, min_periods=n).mean()) / 2.0
            val = _linreg_son(kap - ort, n)
            slope = val - val.shift(2)
            pos = slope > 0
            co = pos & ~pos.shift(1, fill_value=False).astype(bool) & slope.shift(1).notna()
            cu = (slope < 0) & ~(slope.shift(1) < 0)
            refok = ((ref > ref_ema) & (ref_ema.diff() > 0)).fillna(False)
            giris = co & (kap > ema) & (ema.diff() > 0) & pd.DataFrame({c: refok for c in kolon})
            cikis = cu
        elif p["giris"] == "ema":
            e_h = ema_gun(kap, p["ema_hizli"])
            ref_ust = ((ref > ref_ema).astype(float).rolling(p["ref_gun"], min_periods=p["ref_gun"]).min() > 0)
            dusus3 = (kap.diff() < 0) & (kap.diff().shift(1) < 0) & (kap.diff().shift(2) < 0)
            giris = (kap > e_h) & (kap > ema) & ~dusus3 & pd.DataFrame({c: ref_ust for c in kolon})
            ref_zayif = ref < ref.rolling(7, min_periods=7).mean()
            cikis = (kap < ema) & pd.DataFrame({c: ref_zayif for c in kolon})
        else:
            raise ValueError("giris sikisma ya da ema olmalı")
        G = tk.eksene(giris.fillna(False)).to_numpy(dtype=bool)
        C = tk.eksene(cikis.fillna(False)).to_numpy(dtype=bool)
        n_, m = G.shape
        tut = np.zeros(m, dtype=bool)
        w = np.zeros((n_, m))
        for i in range(n_):
            tut = np.where(tut, ~C[i], G[i])
            w[i] = tut * (p["brut"] / len(p["semboller"]))
        return degisim_satirlari(pd.DataFrame(w, index=ax, columns=kolon))


class BtcHedge(PfTemel):
    """BTC long çekirdek + SMA altı hedge.

    Kaynak: kural: BTC long çekirdek + SMA50 altı hedge (1h) (kurallar.py qd_btc_hedge: "sürekli 1 long + SMA50 altında
    1 short (hedge) = net: SMA50 üstünde long, altında düz"); hedge enstrümanı kaynakta tanımsız (kullanıcı kararı).
    Kural: kapanış >= SMA(sma_gun) iken çekirdek long (cekirdek_agirlik). Altında: hedge_sembol "" ise çekirdek ile aynı
    sembolde hedge = net düz (çekirdek kapanır); hedge_sembol dolu ise (ETHUSDT / DK_XAU / DK_WTI) çekirdek long KALIR ve
    hedge sembolü -hedge_orani*cekirdek_agirlik short açılır. Hedge enstrümanı seçimi OOS görülerek yapılmadı: üç seçenek de
    aday ayardır (karar kullanıcıda). 1h SMA50 -> günlük SMA(sma_gun) uyarlaması.
    """

    ad = "pf__btc_hedge"
    min_sembol = 1
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": ("BTCUSDT", "ETHUSDT", "DK_XAU", "DK_WTI"),
                               "cekirdek": "BTCUSDT", "hedge_sembol": "", "sma_gun": 50, "hedge_orani": 1.0,
                               "cekirdek_agirlik": 1.0}
    parametre_izgarasi = {"sma_gun": [30, 50, 100], "hedge_sembol": ["", "ETHUSDT", "DK_XAU"], "hedge_orani": [0.5, 1.0]}

    def uygun_mu(self, mevcut):
        mevcut = set(mevcut)
        p = self.parametreler
        return (p["cekirdek"] in mevcut and p["cekirdek"] in p["semboller"]
                and (not p["hedge_sembol"] or (p["hedge_sembol"] in mevcut and p["hedge_sembol"] in p["semboller"])))

    def _hedef(self, ev, tk):
        p = self.parametreler
        if p["cekirdek"] not in ev or (p["hedge_sembol"] and p["hedge_sembol"] not in ev):
            raise ValueError("pf__btc_hedge: cekirdek/hedge_sembol evrende yok")
        kolon = list(ev)
        c = tk.kap[p["cekirdek"]]
        sm = c.rolling(p["sma_gun"], min_periods=p["sma_gun"]).mean()
        ust = tk.eksene(c >= sm).fillna(False).to_numpy(dtype=bool)
        hazir = tk.eksene(sm.notna()).fillna(False).to_numpy(dtype=bool)
        w = np.zeros((len(tk.eksen), len(kolon)))
        jc = kolon.index(p["cekirdek"])
        for i in range(len(w)):
            if not hazir[i]:
                continue
            if ust[i]:
                w[i, jc] = p["cekirdek_agirlik"]
            elif p["hedge_sembol"]:
                w[i, jc] = p["cekirdek_agirlik"]
                w[i, kolon.index(p["hedge_sembol"])] = -p["hedge_orani"] * p["cekirdek_agirlik"]
        return degisim_satirlari(pd.DataFrame(w, index=tk.eksen, columns=kolon))


class RsiCift(PfTemel):
    """BTC + hedef sembol RSI eşiklerinin BİRLİKTE sağlanmasında long, hedef RSI > cikis_rsi'de çıkış.

    Kaynak: freqtrade multi_tf (BTC + ETH RSI) — arsiv/algo-sg/dis_kaynak/ft/strategies/multi_tf.py. Orijinal giriş:
    BTC/ETH-BTC/hızlı RSI'ları ve 30dk/1s RSI'ları aynı anda düşük (btc_rsi_1h<35, kendi rsi<30, ...); çıkış rsi>70.
    Uyarlama: çok zaman dilimli koşullar günlüğe indirildi: giriş = RSI(hedef) < esik_hedef VE RSI(ref) < esik_ref; çıkış =
    RSI(hedef) > cikis_rsi. Hedef semboller `semboller` (ref hariç), ağırlık brut/len(semboller). Ortalamaya dönüş.
    """

    ad = "pf__rsi_cift"
    min_sembol = 1
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": ("ETHUSDT", "SOLUSDT"), "ref_sembol": "BTCUSDT",
                               "rsi_gun": 14, "esik_hedef": 30.0, "esik_ref": 35.0, "cikis_rsi": 70.0, "brut": 1.0}
    parametre_izgarasi = {"rsi_gun": [7, 14, 21], "esik_hedef": [25.0, 30.0, 40.0], "esik_ref": [35.0, 45.0, 50.0]}

    def ek_semboller(self):
        return (self.parametreler["ref_sembol"],)

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        r = _rsi_tablo(tk.kap, p["rsi_gun"])
        R = tk.eksene(r[kolon]).to_numpy(dtype=float)
        Rref = tk.eksene(r[p["ref_sembol"]]).to_numpy(dtype=float)
        n, m = R.shape
        tut = np.zeros(m, dtype=bool)
        w = np.zeros((n, m))
        for i in range(n):
            gir = (R[i] < p["esik_hedef"]) & (Rref[i] < p["esik_ref"])
            cik = R[i] > p["cikis_rsi"]
            tut = np.where(tut, ~cik, gir)
            w[i] = tut * (p["brut"] / len(p["semboller"]))
        return degisim_satirlari(pd.DataFrame(w, index=tk.eksen, columns=kolon))


class RsiTarama(PfTemel):
    """RSI aşırı satımdan dönüş + trend onayı ile varlık seçimi (tarama).

    Kaynak: kart swing__rsi-70-30-secim__graham ("RSI 30 altındaki adaylardan, RSI 50 üstü trend onayıyla seçim").
    Kural: aday = son `pencere` günde RSI en az bir kez < 30 (aşırı satım). Onay = RSI şimdi > 50 (trend onayı). Aday+onay
    olan semboller arasından son pencere RSI minimumu en düşük (en derin aşırı satımdan dönen) en çok k sembol long;
    RSI > cikis_rsi ya da onay kaybı (RSI < 50) çıkış. Kart belirsizliği (tek varlık da olabilir): çok varlıklı tarama
    olarak yorumlandı. Eşikler karttan (30/50/70), pencere ve k tahmindir.
    """

    ad = "pf__rsi_tarama"
    min_sembol = 2
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": HEPSI, "rsi_gun": 14, "asiri_satim": 30.0, "onay": 50.0,
                               "cikis_rsi": 70.0, "pencere": 10, "k": 3}
    parametre_izgarasi = {"rsi_gun": [7, 14, 21], "pencere": [5, 10, 20], "k": [1, 2, 3]}

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        r = _rsi_tablo(tk.kap[kolon], p["rsi_gun"])
        minr = r.rolling(p["pencere"], min_periods=p["pencere"]).min()
        R, MIN = tk.eksene(r).to_numpy(dtype=float), tk.eksene(minr).to_numpy(dtype=float)
        n, m = R.shape
        tut = np.zeros(m, dtype=bool)
        w = np.zeros((n, m))
        k = int(p["k"])
        for i in range(n):
            for j in range(m):
                if tut[j] and not (R[i, j] <= p["cikis_rsi"] and R[i, j] >= p["onay"]):
                    tut[j] = False
            aday = [(MIN[i, j], j) for j in range(m) if (not tut[j]) and np.isfinite(R[i, j]) and np.isfinite(MIN[i, j])
                    and MIN[i, j] < p["asiri_satim"] and p["onay"] < R[i, j] <= p["cikis_rsi"]]
            for _, j in sorted(aday):
                if tut.sum() < k:
                    tut[j] = True
            w[i] = tut / k
        return degisim_satirlari(pd.DataFrame(w, index=tk.eksen, columns=kolon))


class IbsDonus(PfTemel):
    """Dip-IBS ortalamaya dönüşü, iki bacaklı çıkış (LliterH Mean Reversion Setup), sembol başına bağımsız.

    Kaynak: tv: Mean Reversion Setup LliterH (arsiv/strateji-sg/tv_eleme_dali/pine/6XPbhz9C.pine).
    Giriş: kapanış < EnYüksek(yuksek, 10) - 2.5*SMA(yuksek-dusuk, 25) VE IBS=(kapanış-düşük)/(yüksek-düşük) < 0.3 VE
    kapanış > SMA(50) (rejim). Çıkış "iki bacak" = POZİSYONUN İKİ YARISI: bacak 1 (%50) kapanış > önceki gün yükseği olunca
    kapanır; bacak 2 (%50) ATR iz süren stopla (tepe kapanıştan trail_k*ATR) kapanır; sert stop atr_k(=2)*ATR. (Kaynağın
    "iki bacak" belirsizliği -> pine kaynağından doğrulandı: iki ÇIKIŞ bacağı, iki enstrüman değil.) Ağırlık: giriş
    başına brut/len(semboller); bir sembol bir kez açılır (pyramiding yok).
    """

    ad = "pf__ibs_donus"
    min_sembol = 1
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": HEPSI, "tepe_gun": 10, "aralik_gun": 25, "carpan": 2.5,
                               "ibs_max": 0.3, "rejim_sma": 50, "trail_k": 1.5, "brut": 1.0, "atr_k": 2.0}
    parametre_izgarasi = {"carpan": [1.5, 2.0, 2.5], "ibs_max": [0.2, 0.3, 0.4], "rejim_sma": [50, 100, 200]}

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        h = tk.panel("yuksek", False)[kolon]
        l = tk.panel("dusuk", False)[kolon]
        kap = tk.kap[kolon]
        thr = h.rolling(p["tepe_gun"], min_periods=p["tepe_gun"]).max() - p["carpan"] * (h - l).rolling(
            p["aralik_gun"], min_periods=p["aralik_gun"]).mean()
        ibs = ((kap - l) / (h - l).replace(0, np.nan)).where(h > l, 0.0)
        giris = (kap < thr) & (ibs < p["ibs_max"]) & (kap > sma_gun(kap, p["rejim_sma"]))
        onceki_yuksek = h.shift(1)
        mom_cik = kap > onceki_yuksek
        from motor.portfoy.temel import atr_tablosu
        atr = atr_tablosu({c: tk.veriler[c] for c in kolon}, p["atr_periyot"], ileri_doldur=True)
        G = tk.eksene(giris.fillna(False)).to_numpy(dtype=bool)
        M = tk.eksene(mom_cik.fillna(False)).to_numpy(dtype=bool)
        K = tk.eksene(kap).to_numpy(dtype=float)
        A = atr.reindex(tk.eksen).ffill().to_numpy(dtype=float)
        n, m = G.shape
        durum = np.zeros(m)          # 0 yok, 1 tam, 0.5 yarım
        tepe = np.full(m, np.nan)
        w = np.zeros((n, m))
        pay = p["brut"] / len(p["semboller"])
        for i in range(n):
            for j in range(m):
                if durum[j] > 0:
                    tepe[j] = np.nanmax([tepe[j], K[i, j]])
                    if np.isfinite(A[i, j]) and K[i, j] <= tepe[j] - p["trail_k"] * A[i, j]:
                        durum[j] = 0.0
                    elif durum[j] == 1.0 and M[i, j]:
                        durum[j] = 0.5
                elif G[i, j] and np.isfinite(A[i, j]):
                    durum[j] = 1.0
                    tepe[j] = K[i, j]
            w[i] = durum * pay
        return degisim_satirlari(pd.DataFrame(w, index=tk.eksen, columns=kolon))
