"""Long-only rotasyon / tahsis aileleri (karar 23): Rotasyon, SabitSepet, TrendSepet, Kanarya.

Tüm geri bakışlar takvim günüdür (bkz. ortak.py). Nakit/T-bill/tahvil gereken kollarda nakit = pozisyonsuz; evrende
olmayan varlıklar (SPY, ACWX, AGG, VWO, BND ...) için en yakın vekil ya da kol düşürme ilgili sınıf docstring'inde
belgelidir.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.strateji import _gosterge_d11j as j
from motor.portfoy.stratejiler.ortak import (EMTIA, HEPSI, HISSE, KRIPTO, ORTAK_PARAMETRELER, PfTemel, Takvim,
                                             dongusel_hedef, en_iyi_k, sma_gun, tetik_satirlari)


def _regresyon_skoru(kap: pd.DataFrame, gun: int) -> pd.DataFrame:
    """Clenow: log fiyat doğrusal regresyon eğimi, yıllıklandırılmış ((exp(eğim*365)-1)) x R². Nedensel (pencere t'de biter)."""
    x = np.arange(gun, dtype=float)
    xm = x - x.mean()
    sxx = float((xm ** 2).sum())

    def f(y):
        ym = y - y.mean()
        syy = float((ym ** 2).sum())
        if syy <= 0:
            return np.nan
        sxy = float((xm * ym).sum())
        egim = sxy / sxx
        r2 = sxy * sxy / (sxx * syy)
        return (np.exp(egim * 365.0) - 1.0) * r2

    return np.log(kap).rolling(gun, min_periods=gun).apply(f, raw=True)


class Rotasyon(PfTemel):
    """Kesitsel momentum / rotasyon, long-only (rotasyon ailesi: lookback, top-K, yeniden dengeleme sıklığı, mutlak
    momentum filtresi, rejim filtresi, trend filtresi, ağırlıklandırma, iz süren stop).

    Kaynaklar (portfoy_adaylari.csv): MomentumRegimeBasket15mFast (nateemma), Antonacci GEM, Faber 5-sınıf rotasyonu,
    QuantConnect ETF Global Rotation, Clenow momentum tarayıcısı, kural: momentum top-4/top-5/top-3, ters-vol/düşük vol
    sepetleri, awesome: 6 ay / 365g momentum rotasyonu, BTC/ETH eşli geçiş, aqt momentum rotasyonu (%15 iz).

    Kural: her yeniden dengeleme satırında (kapanış, sonraki açılışta dolar) skor hesaplanır; filtrelerden geçen
    (trend_sma: kapanış > SMA; mutlak: skor > 0; gap_filtre: son 90 günde |açılış/önceki kapanış-1| <= gap; rejim:
    rejim_sembol kapanışı > SMA(rejim_sma), değilse tümü nakit) semboller arasından en iyi k seçilir
    (cikis_rank > k ise mevcut tutulan, sıralamada cikis_rank içinde kalıyorsa tutulur = histerezis). Ağırlık eşit
    (1/k; k'dan az seçilirse kalanı nakit) ya da ters-vol (aynı toplam brüt). Seçilmeyenler 0'a çekilir.

    skor: "getiri" (kapanış[t-atla]/kapanış[t-lookback]-1), "agirlikli" ((w1*mom(l1)+w2*mom(l2))/(w1+w2), QC MOMP
    düzeltmesi: yüzde, fiyat farkı DEĞİL), "w13612" (12*1ay+4*3ay+2*6ay+1*12ay), "regresyon" (Clenow eğim x R²),
    "risk_ayarli" (günlük getiri ort/std), "dusuk_vol" (-std), "kompozit" (0.5*m20+0.3*m60+0.2*m120-0.5*std20).
    d11j EK skorlar (varsayılan değişmez; yeni modlar ızgarada yok, ayar kaydıyla denenir): "bb_uzaklik" = kapanış / Bollinger üst bandı(lookback_gun,
    bb_sapma) - 1 (>0: üst bandın üstünde kapatanlar aday = mutlak filtre; en uzak olan seçilir; ai-trader çoklu Bollinger rotasyonu; alt bandın
    altındakiler zaten skor<0 olarak seçilmez; %99 ağırlık ayrıntısı kodlanmadı), "hacim" = lookback_gun günlük ortalama dolar hacmi (hacim*kapanış;
    sıralama ölçütü; mutlak filtre bu skor için devre dışıdır). ek_filtre="triple_rsi": yalnız Triple RSI (20/60/120; _gosterge_d11j.triple_rsi_ok)
    süzgecinden geçen semboller aday (ai-trader Triple RSI rotasyonu: süzgeçten geçenler içinden hacme göre ilk k). Kaynaktaki "çift aylarda ayın 5'i"
    takvimi yerine mevcut `takvim` (örn. "M") kullanılır = yaklaşık.

    d12b EK (151 §4.6; varsayılan değişmez, ızgarada yok): agirlik="getiri_vol" -> seçilenlerde ağırlık ∝ R/σ, R = kapanış[t-atla]/
    kapanış[t-lookback]-1 (skor ne olursa olsun), σ = vol_gun günlük getiri std (en az 0.003); yalnız R>0 olanlar ağırlık alır
    (long-only: kitaptaki negatif R/σ short kodlanmadı), toplam ters_vol ile aynı (seçilen/k); hiçbiri R>0 değilse nakit.

    Uyarlama: ETF'ler -> evrendeki semboller (GEM: SPY/ACWX -> hisse sepeti+XAU, AGG -> XAU kolu, BIL -> nakit;
    Faber 5-sınıf -> BTC, MSFT, XAU, WTI, COPPER temsilcileri). 15m/1s/4s yeniden dengeleme günlüğe indirilmiştir.
    """

    ad = "pf__rotasyon"
    min_sembol = 2
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": HEPSI, "skor": "getiri", "lookback_gun": 90, "atla_gun": 0, "lookback2_gun": 90,
        "agirlik1": 100.0, "agirlik2": 75.0, "k": 2, "takvim": "M", "mutlak": True, "trend_sma": 0, "rejim_sembol": "",
        "rejim_sma": 100, "gap_filtre": 0.0, "agirlik": "esit", "cikis_rank": 0, "vol_gun": 60,
        "bb_sapma": 2.0, "ek_filtre": ""}
    parametre_izgarasi = {"lookback_gun": [30, 90, 180], "k": [1, 2, 3], "takvim": ["W", "M", "Q"]}

    def ek_semboller(self):
        return (self.parametreler["rejim_sembol"],)

    def _skor(self, tk: Takvim) -> pd.DataFrame:
        p = self.parametreler
        s, L = p["skor"], p["lookback_gun"]
        if s == "getiri":
            return tk.mom(L, p["atla_gun"])
        if s == "agirlikli":
            w1, w2 = p["agirlik1"], p["agirlik2"]
            return (w1 * tk.mom(L) + w2 * tk.mom(p["lookback2_gun"])) / (w1 + w2)
        if s == "w13612":
            return 12 * tk.mom(30) + 4 * tk.mom(91) + 2 * tk.mom(182) + tk.mom(365)
        if s == "regresyon":
            return _regresyon_skoru(tk.kap, L)
        if s == "risk_ayarli":
            r = tk.getiri().shift(p["atla_gun"])
            return r.rolling(L, min_periods=max(5, L // 2)).mean() / r.rolling(L, min_periods=max(5, L // 2)).std()
        if s == "dusuk_vol":
            return -tk.vol(L)
        if s == "kompozit":
            return 0.5 * tk.mom(20) + 0.3 * tk.mom(60) + 0.2 * tk.mom(120) - 0.5 * tk.vol(20)
        if s == "bb_uzaklik":
            ort = tk.kap.rolling(L, min_periods=L).mean()
            sd = tk.kap.rolling(L, min_periods=L).std(ddof=0)
            return tk.kap / (ort + p["bb_sapma"] * sd) - 1.0
        if s == "hacim":
            return (tk.panel("hacim", False) * tk.kap).rolling(L, min_periods=max(5, L // 2)).mean()
        raise ValueError(f"bilinmeyen skor: {s}")

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        ax = tk.eksen
        S = tk.eksene(self._skor(tk)[kolon]).to_numpy(dtype=float)
        V = tk.eksene(tk.vol(p["vol_gun"])[kolon]).to_numpy(dtype=float)
        R = (tk.eksene(tk.mom(p["lookback_gun"], p["atla_gun"])[kolon]).to_numpy(dtype=float)
             if p["agirlik"] == "getiri_vol" else None)
        trend = np.ones(S.shape, dtype=bool)
        if p["trend_sma"] > 0:
            sm = sma_gun(tk.kap[kolon], p["trend_sma"])
            trend = (tk.eksene(tk.kap[kolon] > sm).to_numpy(dtype=bool)
                     & tk.eksene(sm.notna()).to_numpy(dtype=bool))
        gap_ok = np.ones(S.shape, dtype=bool)
        if p["gap_filtre"] > 0:
            ac = tk.panel("acilis")[kolon]
            gap = (ac / tk.kap[kolon].shift(1) - 1.0).abs()
            gmax = gap.rolling(90, min_periods=1).max()
            gap_ok = tk.eksene(gmax <= p["gap_filtre"]).fillna(False).to_numpy(dtype=bool)
        if p["ek_filtre"] == "triple_rsi":
            trs = tk.eksene(j.triple_rsi_ok(tk.kap[kolon])).fillna(False).to_numpy(dtype=bool)
            gap_ok = gap_ok & trs
        elif p["ek_filtre"]:
            raise ValueError(f"bilinmeyen ek_filtre: {p['ek_filtre']}")
        rejim_ok = np.ones(len(ax), dtype=bool)
        rejim_hazir = np.ones(len(ax), dtype=bool)
        if p["rejim_sembol"]:
            rk = tk.kap[p["rejim_sembol"]]
            rs = rk.rolling(p["rejim_sma"], min_periods=p["rejim_sma"]).mean()
            rejim_ok = tk.eksene(rk > rs).fillna(False).to_numpy(dtype=bool)
            rejim_hazir = tk.eksene(rs.notna()).fillna(False).to_numpy(dtype=bool)
        gecerli = np.isfinite(S).any(axis=1) & rejim_hazir
        tetik = tetik_satirlari(ax, p["takvim"], gecerli)
        mutlak = p["mutlak"] and p["skor"] not in ("dusuk_vol", "hacim")
        k = int(p["k"])
        onceki: list = []

        def agirlik(i):
            nonlocal onceki
            if not rejim_ok[i]:
                onceki = []
                return {}
            elig = np.isfinite(S[i]) & trend[i] & gap_ok[i]
            if mutlak:
                elig &= S[i] > 0
            s = pd.Series(S[i], index=kolon)[elig]
            sirali = en_iyi_k(s, len(s))
            sec = sirali[:k]
            if p["cikis_rank"] > k:
                tut = [c for c in onceki if c in sirali[:p["cikis_rank"]]][:k]
                sec = tut + [c for c in sirali if c not in tut][:k - len(tut)]
            onceki = list(sec)
            if not sec:
                return {}
            if p["agirlik"] == "getiri_vol":
                v = pd.Series(V[i], index=kolon)[sec].clip(lower=0.003)
                rr = pd.Series(R[i], index=kolon)[sec]
                oran = (rr / v).where(rr > 0)
                if oran.notna().sum() == 0:
                    return {}
                oran = oran.fillna(0.0)
                return (oran / oran.sum() * len(sec) / k).to_dict()
            if p["agirlik"] == "ters_vol":
                v = pd.Series(V[i], index=kolon)[sec].clip(lower=0.003)
                if v.isna().any():
                    return {c: 1.0 / k for c in sec}
                iv = 1.0 / v
                return (iv / iv.sum() * len(sec) / k).to_dict()
            return {c: 1.0 / k for c in sec}

        return dongusel_hedef(ax, kolon, tetik, agirlik)


class SabitSepet(PfTemel):
    """Sabit / eşit / ters-vol ağırlıklı long sepet; takvimle ya da SAPMA eşiğiyle yeniden dengeleme.

    Kaynaklar: kural: Endeks BTC/ETH/SOL eşit +-%5 sapma; Eşit ağırlık (aylık); Rebalance sabit BTC.5/ETH.3/SOL.2 (4h);
    Ters volatilite ağırlık (aylık); awesome: Yeniden dengeleme primi (günlük dengelenen eşit ağırlık bacağı).

    Kural: hedef ağırlıklar geçerli (fiyatı olan) sembollerde: eşit (1/n), sabit (`agirliklar`, semboller sırasıyla,
    geçerli olanlara yeniden normalize) ya da ters-vol. Yeniden dengeleme: takvim ("yok" = takvimle değil) VE/VEYA
    sapma > 0 ise fiili (fiyatla kayan, nedensel simüle edilen) ağırlıklardan biri hedeften mutlak `sapma` kadar
    uzaklaşınca; geçerli sembol kümesi değişince de dengelenir.
    Uyarlama: 4 saatlik dengeleme günlüğe indirilmiştir (portföy koşusu 1d). "Yeniden dengeleme primi" ölçümü bir
    strateji değil karşılaştırmadır: burada günlük dengelenen bacak (takvim="D") sağlanır; prim, aynı sepetin
    takvim="M"/"yok" sürümüyle karşılaştırılarak okunur.

    d11j EK ağırlık şemaları (varsayılan değişmez; ızgarada yok, ayar kaydıyla denenir): agirlik="hrp" (Hiyerarşik Risk Paritesi: korelasyon
    mesafesi, tek bağlantılı kümeleme, özyinelemeli ters-varyans bölme), "min_var" (long-only global minimum varyans, aktif küme yöntemi),
    "mvo" (long-only teğet/maks. Sharpe: w ~ inv(Kov) x ortalama getiri; ortalama getirisi <= 0 olanlar elenir, hepsi <= 0 ise nakit).
    Kovaryans/ortalama son `kov_gun` takvim gününün günlük getirisinden (t'de biter, nedensel); pencerede yeterli verisi (>= %70) olmayan
    semboller o dengelemede ağırlıksız kalır; 2'den az uygun sembol varsa eşit ağırlık. scipy yok: Chan etkin sınır, Kelly (F=C^-1 M) ve
    kısıtlı/kısıtsız genel optimizasyon KODLANMADI; MVO girdisi (beklenen getiri) gürültülüdür. Korelasyon kümeleme ile temsilci seçimi kodlanmadı.
    """

    ad = "pf__sabit_sepet"
    min_sembol = 2
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": KRIPTO, "agirlik": "esit", "agirliklar": (),
                               "takvim": "M", "sapma": 0.0, "vol_gun": 60, "brut": 1.0, "kov_gun": 120}
    parametre_izgarasi = {"agirlik": ["esit", "ters_vol"], "takvim": ["D", "W", "M"], "sapma": [0.0, 0.05, 0.10]}

    def _opt_agirlik(self, RET, poz, maske):
        p = self.parametreler
        L = int(p["kov_gun"])
        pencere = RET[max(0, poz - L + 1):poz + 1]
        yeterli = maske & (np.isfinite(pencere).sum(axis=0) >= max(20, int(0.7 * L)))
        if yeterli.sum() < 2:
            return maske.astype(float)
        alt = pd.DataFrame(pencere[:, yeterli])
        cov = alt.cov().to_numpy()
        if not np.isfinite(cov).all():
            return maske.astype(float)
        if p["agirlik"] == "hrp":
            w = j.hrp_agirlik(cov)
        elif p["agirlik"] == "min_var":
            w = j.min_varyans_agirlik(cov)
        else:
            w = j.maks_sharpe_agirlik(cov, alt.mean().to_numpy())
        raw = np.zeros(len(maske))
        raw[yeterli] = w
        return raw

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        ax = tk.eksen
        K = tk.eksene(tk.kap[kolon]).to_numpy(dtype=float)
        V = tk.eksene(tk.vol(p["vol_gun"])[kolon]).to_numpy(dtype=float)
        gecerli_m = np.isfinite(K)
        sabit = None
        if p["agirlik"] == "sabit":
            if len(p["agirliklar"]) != len(p["semboller"]):
                raise ValueError("agirlik='sabit' için agirliklar semboller ile aynı uzunlukta olmalı")
            sabit = dict(zip(p["semboller"], p["agirliklar"]))
        if p["agirlik"] == "ters_vol":
            gecerli_m = gecerli_m & np.isfinite(V)
        opt = p["agirlik"] in ("hrp", "min_var", "mvo")
        if opt:
            RET = tk.getiri()[kolon].to_numpy(dtype=float)
            gun_poz = tk.gun.get_indexer(ax)
        gecerli = gecerli_m.any(axis=1)
        takvim_tetik = np.zeros(len(ax), dtype=bool) if str(p["takvim"]) == "yok" else tetik_satirlari(ax, p["takvim"], gecerli)
        h = np.full((len(ax), len(kolon)), np.nan)
        hedef_w = None
        cur = None
        onceki_maske = None
        for i in range(len(ax)):
            if not gecerli[i]:
                continue
            maske = gecerli_m[i]
            tetik = takvim_tetik[i] or hedef_w is None or (onceki_maske is not None and (maske != onceki_maske).any())
            if cur is not None and not tetik and p["sapma"] > 0 and i > 0:
                r = np.where(maske & gecerli_m[i - 1], K[i] / K[i - 1] - 1.0, 0.0)
                cur = cur * (1.0 + r)
                tp = cur.sum()
                cur = cur / tp if tp > 0 else cur
                tetik = bool(np.nanmax(np.abs(cur - hedef_w)) > p["sapma"])
            elif cur is not None and not tetik and i > 0:
                r = np.where(maske & gecerli_m[i - 1], K[i] / K[i - 1] - 1.0, 0.0)
                cur = cur * (1.0 + r)
                tp = cur.sum()
                cur = cur / tp if tp > 0 else cur
            if tetik:
                if p["agirlik"] == "sabit":
                    raw = np.array([sabit.get(c, 0.0) for c in kolon]) * maske
                elif p["agirlik"] == "ters_vol":
                    raw = np.where(maske, 1.0 / np.clip(np.nan_to_num(V[i], nan=1.0), 0.003, None), 0.0)
                elif opt:
                    raw = self._opt_agirlik(RET, gun_poz[i], maske)
                else:
                    raw = maske.astype(float)
                tp = raw.sum()
                hedef_w = raw / tp if tp > 0 else raw
                cur = hedef_w.copy()
                h[i] = hedef_w * p["brut"]
            onceki_maske = maske
        return pd.DataFrame(h, index=ax, columns=kolon)


class TrendSepet(PfTemel):
    """Varlık başına SMA trend filtreli sepet (Faber GTAA / Ivy / 300g SMA trend takibi).

    Kaynaklar: Varlık dağılımı paketi (Faber GTAA, Ivy; pyTAA), awesome: Trend takibi (kapanış > 300g SMA, eşit ağırlık).
    Kural: her yeniden dengelemede (aylık: kaynakta ay sonu kapanışı) kapanış > SMA(sma_gun) olan semboller tutulur.
    nakitli=True (GTAA): her varlık sabit 1/n (n = geçerli sembol sayısı) -> SMA altındakinin payı NAKİT (pozisyonsuz);
    nakitli=False: SMA üstündekiler eşit paylaşır (toplam 1). Faber'in "10 aylık SMA" ~ 300 takvim günü.
    Uyarlama: ETF sepetleri -> evren; kanarya/VAA/DAA parçaları `pf__kanarya` sınıfındadır.
    """

    ad = "pf__trend_sepet"
    min_sembol = 2
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": HEPSI, "sma_gun": 300, "takvim": "M", "nakitli": True}
    parametre_izgarasi = {"sma_gun": [100, 200, 300], "takvim": ["W", "M", "Q"], "nakitli": [True, False]}

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        kap = tk.kap[kolon]
        sm = sma_gun(kap, p["sma_gun"])
        ust = tk.eksene(kap > sm).fillna(False).to_numpy(dtype=bool)
        hazir = tk.eksene(sm.notna()).fillna(False).to_numpy(dtype=bool)
        tetik = tetik_satirlari(tk.eksen, p["takvim"], hazir.any(axis=1))

        def agirlik(i):
            tut = ust[i] & hazir[i]
            n = int(hazir[i].sum()) if p["nakitli"] else int(tut.sum())
            if n == 0:
                return {}
            return {c: 1.0 / n for c, t in zip(kolon, tut) if t}

        return dongusel_hedef(tk.eksen, kolon, tetik, agirlik)


class Kanarya(PfTemel):
    """Keller VAA / DAA (kanarya evreni) savunmacı tahsis.

    Kaynaklar: Keller DAA (TuringTrader Keller_DAA.cs), Keller VAA (pyTAA; varlık dağılımı paketi).
    Kural: 13612W momentum (12*1ay+4*3ay+2*6ay+1*12ay; takvim günü 30/91/182/365). Aylık.
      mod="daa": kanarya = `kanarya` sembolleri (evrende olanlar; B = bulunan sayı). b = momentumu negatif kanarya sayısı;
        nakit payı CF = min(1, floor(b*T/B)/T); riskli pay (1-CF) en yüksek momentumlu t = round((1-CF)*T) riskli varlığa
        eşit dağılır (T = `T`).
      mod="vaa": kanarya = riskli evrenin kendisi; n = momentumu negatif riskli sayısı; CF = min(1, n/vaa_b);
        riskli pay en iyi `ust_k` riskli varlığa eşit.
      Nakit payı: `guvenli` sembollerden momentumu en yüksek (pozitifse) olana gider, yoksa NAKİT (pozisyonsuz).
    Uyarlama (belgelenmiş vekiller): VWO/BND kanaryaları evrende yok -> kanarya = BTCUSDT + DK_COPPER (risk iştahı
    vekilleri; seçimde OOS görülmedi); korunma ETF'leri (SHY/IEF/LQD) -> DK_XAU ya da nakit. Kripto-only evrende kanarya
    yalnız BTC olur. Kipnis KDA (min-varyans) kodlanmadı.
    """

    ad = "pf__kanarya"
    min_sembol = 2
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": HEPSI, "mod": "daa", "kanarya": ("BTCUSDT", "DK_COPPER"),
                               "guvenli": ("DK_XAU",), "T": 6, "vaa_b": 4, "ust_k": 3, "takvim": "M"}
    parametre_izgarasi = {"mod": ["daa", "vaa"], "T": [3, 6], "ust_k": [2, 3, 5], "takvim": ["M", "Q"]}

    def ek_semboller(self):
        return ()

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        mom = (12 * tk.mom(30) + 4 * tk.mom(91) + 2 * tk.mom(182) + tk.mom(365))[kolon]
        M = tk.eksene(mom).to_numpy(dtype=float)
        guvenli = [c for c in p["guvenli"] if c in kolon]
        riskli = [c for c in kolon if c not in guvenli]
        if not riskli:
            raise ValueError("pf__kanarya: riskli sembol yok")
        kanarya = [c for c in p["kanarya"] if c in kolon] if p["mod"] == "daa" else riskli
        j_r = [kolon.index(c) for c in riskli]
        j_k = [kolon.index(c) for c in kanarya]
        j_g = [kolon.index(c) for c in guvenli]
        hazir = np.isfinite(M[:, j_r]).any(axis=1)
        if j_k:
            hazir &= np.isfinite(M[:, j_k]).all(axis=1)
        tetik = tetik_satirlari(tk.eksen, p["takvim"], hazir)

        def agirlik(i):
            m = M[i]
            if p["mod"] == "daa":
                B = max(len(j_k), 1)
                b = int((m[j_k] < 0).sum()) if j_k else 0
                cf = min(1.0, np.floor(b * p["T"] / B) / p["T"])
                t = int(round((1.0 - cf) * p["T"]))
            else:
                n = int((m[j_r][np.isfinite(m[j_r])] < 0).sum())
                cf = min(1.0, n / p["vaa_b"])
                t = int(p["ust_k"])
            w: dict = {}
            if t > 0 and cf < 1.0:
                s = pd.Series(m[j_r], index=riskli)
                sec = en_iyi_k(s, t)
                for c in sec:
                    w[c] = (1.0 - cf) / len(sec)
            if cf > 0 and j_g:
                g = pd.Series(m[j_g], index=guvenli)
                gs = en_iyi_k(g, 1)
                if gs and g[gs[0]] > 0:
                    w[gs[0]] = w.get(gs[0], 0.0) + cf
            return w

        return dongusel_hedef(tk.eksen, kolon, tetik, agirlik)


class Gem(Rotasyon):
    """Tek varlık %100 çift momentum (Antonacci GEM / QC ETF Global Rotation / BTC-ETH eşli geçiş), savunma kolu.

    Kaynaklar: Antonacci GEM (TuringTrader), QuantConnect ETF Global Rotation, awesome: Eşli geçiş BTC/ETH (90g, çeyreklik).
    Kural: her yeniden dengelemede riskli semboller (semboller - savunma) arasından skoru (getiri / agirlikli) en yüksek
    TEK sembol seçilir (göreceli momentum). Seçilenin skoru > 0 değilse (mutlak momentum) savunma kolu: `savunma`
    sembollerinden skoru en yüksek ve > 0 olan; yoksa NAKİT (pozisyonsuz). Tek varlıkta %100 (motor %1 risk/3x ile kırpar).
    Uyarlama: SPY/ACWX -> riskli evren (hisse sepeti+kripto), BIL (T-bill) -> nakit = pozisyonsuz, AGG -> DK_XAU savunma
    kolu (evrende tahvil yok; altın en yakın savunmacı vekil, bunun tahvil olmadığı belgelenmiştir). QC kodundaki MOM
    (fiyat farkı) hatası düzeltildi: yüzde getiri (MOMP) kullanılır -> fiyat düzeyi sıralamayı bozmaz.
    """

    ad = "pf__gem"
    min_sembol = 2
    varsayilan_parametreler = {**Rotasyon.varsayilan_parametreler, "savunma": ("DK_XAU",), "skor": "getiri",
                               "lookback_gun": 365, "takvim": "M", "k": 1}
    parametre_izgarasi = {"lookback_gun": [90, 180, 365], "takvim": ["M", "Q"], "skor": ["getiri", "agirlikli"]}

    def uygun_mu(self, mevcut):
        ev = self.etkin_semboller(mevcut)
        riskli = [s for s in ev if s not in self.parametreler["savunma"]]
        return len(riskli) >= 1 and len(ev) >= 2

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        sav = [c for c in kolon if c in p["savunma"]]
        risk = [c for c in kolon if c not in sav]
        if not risk:
            raise ValueError("pf__gem: riskli sembol yok")
        S = tk.eksene(self._skor(tk)[kolon]).to_numpy(dtype=float)
        j_r = [kolon.index(c) for c in risk]
        j_s = [kolon.index(c) for c in sav]
        gecerli = np.isfinite(S[:, j_r]).any(axis=1)
        tetik = tetik_satirlari(tk.eksen, p["takvim"], gecerli)

        def agirlik(i):
            sr = pd.Series(S[i, j_r], index=risk)
            en = en_iyi_k(sr, 1)
            if en and (sr[en[0]] > 0 or not p["mutlak"]):
                return {en[0]: 1.0}
            if j_s:
                ss = pd.Series(S[i, j_s], index=sav)
                g = en_iyi_k(ss, 1)
                if g and ss[g[0]] > 0:
                    return {g[0]: 1.0}
            return {}

        return dongusel_hedef(tk.eksen, kolon, tetik, agirlik)
