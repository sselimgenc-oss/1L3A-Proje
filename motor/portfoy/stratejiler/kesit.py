"""Kesitsel long/short ve göreceli güç stratejileri: KesitLS, GoreceliGuc, WqAlfa."""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.portfoy.stratejiler.ortak import (HEPSI, HISSE, ORTAK_PARAMETRELER, PfTemel, Takvim, degisim_satirlari,
                                             dongusel_hedef, en_iyi_k, ema_gun, sma_gun, tetik_satirlari)


def _asimetri(x: np.ndarray) -> float:
    x = x[~np.isnan(x)]
    if len(x) < 20:
        return np.nan
    m, s = x.mean(), x.std()
    return float((x > m + 2 * s).sum() - (x < m - 2 * s).sum())


class KesitLS(PfTemel):
    """Kesitsel faktör, piyasa nötr long/short (ya da long-only/ters) — KMN ve awesome faktör ailesi.

    Kaynaklar: KMN (arsiv/strateji-sg/backtest/momentum.py + momentum_sinyal.py: 14 günde bir, 14g riske göre
    düzeltilmiş getiri, en güçlü K long / en zayıf K short, ters-vol ağırlık, her taraf %50), awesome: 12 aylık döngü,
    52 hafta zirvesi, düşük beta (BAB), kalıntı momentum, getiri asimetrisi, küçük ölçek, kısa vadeli dönüş, momentum
    1/1, 3/3, 5/5, momentum+yüksek volatilite, tutarlı momentum, çarpıklık.

    Kural: yeniden dengeleme satırında sembolleri skora göre sırala; en iyi k long, en kötü k short (bacak başı brüt
    `brut`/2); eşit ya da ters-vol ağırlık; bir sembol iki bacakta olamaz. k_etkin = min(k, n//2) (n = geçerli sembol
    sayısı; k büyüğü küçük evrene sığdırır). mod="long": yalnız long bacak (brüt = brut); mod="ters": bacaklar yer değiştirir.
    skor:
      getiri       kapanış[t-atla]/kapanış[t-lookback]-1 (12-1 momentum: lookback 365, atla 30)
      risk_ayarli  günlük getirinin ort/std'si (KMN, §3.1)
      artik        referansa (BTC; yoksa evren ortalaması) göre kalıntı getirinin ort/std'si (beta: 90g kayan, bir gün
                   gecikmeli -> nedensel)
      zirve        kapanış / lookback günlük en yüksek kapanış (52 hafta zirvesine yakınlık)
      carpiklik    -çarpıklık (düşük çarpıklık long)
      asimetri     -(ort+2sd üstü gün sayısı - ort-2sd altı gün sayısı)
      hacim        -(30g ortalama dolar hacmi) (küçük ölçek vekili: piyasa değeri verisi yok)
      beta         -beta (referansa göre lookback günlük; BAB; beta ölçekleme yok)
      donus        long: -(lookback günlük getiri) (en kötü), short: lookback2 günlük getiri (en iyi)
      tutarli      lookback (atla) ve lookback2 getirisinin İKİSİNDE de üst/alt üçte bir (kesit sırası) -> long/short
    vol_filtre="yuksek": yalnız volatilitesi kesit medyanının üstündeki yarıda sırala (momentum + yüksek volatilite).
    Uyarlama / sapmalar: "3 dilim"/"6 dilim" (örtüşen alt portföyler) kodlanmadı, tek portföy kullanılır; beta ölçekleme
    yok; evren 3-13 enstrüman (kaynaklar 25-30 coin) -> sonuçlar çok daha gürültülüdür. Kaynakta KMN'nin N=15 / N=7 sonuçları
    çöküyordu; küçük evrende de aynı beklenir.
    """

    ad = "pf__kesit_ls"
    min_sembol = 2
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": HEPSI, "skor": "risk_ayarli", "lookback_gun": 14, "atla_gun": 0,
        "lookback2_gun": 30, "k": 2, "takvim": "14", "mod": "notr", "agirlik": "ters_vol", "vol_filtre": "yok",
        "vol_gun": 30, "brut": 1.0, "ref_sembol": "BTCUSDT"}
    parametre_izgarasi = {"lookback_gun": [14, 30, 90], "k": [1, 2, 3], "takvim": ["7", "14", "30"]}

    def ek_semboller(self):
        return (self.parametreler["ref_sembol"],) if self.parametreler["skor"] in ("artik", "beta") else ()

    def _piyasa(self, tk, ev):
        ref = self.parametreler["ref_sembol"]
        r = tk.getiri()
        if ref and ref in r.columns:
            return r[ref]
        return r[list(ev)].mean(axis=1)

    def _skorlar(self, ev, tk) -> tuple:
        p = self.parametreler
        kolon = list(ev)
        s, L, A = p["skor"], p["lookback_gun"], p["atla_gun"]
        r = tk.getiri()
        if s == "getiri":
            sk = tk.mom(L, A)
        elif s == "risk_ayarli":
            x = r.shift(A)
            sk = x.rolling(L, min_periods=max(5, L // 2)).mean() / x.rolling(L, min_periods=max(5, L // 2)).std()
        elif s in ("artik", "beta"):
            m = self._piyasa(tk, ev)
            cov = r.rolling(90, min_periods=60).cov(m)
            beta = cov.div(m.rolling(90, min_periods=60).var(), axis=0)
            if s == "beta":
                bb = r.rolling(L, min_periods=max(30, L // 2)).cov(m).div(
                    m.rolling(L, min_periods=max(30, L // 2)).var(), axis=0)
                sk = -bb
            else:
                res = r - beta.shift(1).mul(m, axis=0)
                x = res.shift(A)
                sk = x.rolling(L, min_periods=max(5, L // 2)).mean() / x.rolling(L, min_periods=max(5, L // 2)).std()
        elif s == "zirve":
            sk = tk.kap / tk.kap.rolling(L, min_periods=int(L * 0.8)).max()
        elif s == "carpiklik":
            sk = -r.rolling(L, min_periods=max(20, int(L * 0.8))).skew()
        elif s == "asimetri":
            sk = -r.rolling(L, min_periods=max(20, int(L * 0.8))).apply(_asimetri, raw=True)
        elif s == "hacim":
            dv = (tk.panel("hacim", True) * tk.kap)
            sk = -dv.rolling(30, min_periods=20).mean()
        elif s == "donus":
            return -tk.mom(L), tk.mom(p["lookback2_gun"])
        elif s == "tutarli":
            return tk.mom(L, A), tk.mom(p["lookback2_gun"])
        else:
            raise ValueError(f"bilinmeyen skor: {s}")
        return sk, -sk

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        ax = tk.eksen
        ref = p["ref_sembol"] if p["skor"] in ("artik", "beta") else ""
        u, kk = self._skorlar(ev, tk)
        U = tk.eksene(u[kolon]).to_numpy(dtype=float)
        K = tk.eksene(kk[kolon]).to_numpy(dtype=float)
        V = tk.eksene(tk.vol(p["vol_gun"])[kolon]).to_numpy(dtype=float)
        dis = np.array([c == ref for c in kolon])       # referansın kendisi sıralanmaz
        gecerli = (np.isfinite(U) & np.isfinite(K) & ~dis).sum(axis=1) >= 2
        tetik = tetik_satirlari(ax, p["takvim"], gecerli)
        mod, brut = p["mod"], p["brut"]

        def bacak(adaylar, kolonlar, sk, k, yon, pay):
            if not adaylar:
                return {}
            sec = en_iyi_k(pd.Series(sk, index=kolonlar)[adaylar], k)
            if p["agirlik"] == "ters_vol":
                v = pd.Series(V_i, index=kolonlar)[sec].clip(lower=0.003)
                if v.notna().all():
                    iv = 1.0 / v
                    return {c: yon * pay * float(w) for c, w in (iv / iv.sum()).items()}
            return {c: yon * pay / len(sec) for c in sec}

        def agirlik(i):
            nonlocal V_i
            V_i = V[i]
            ok = np.isfinite(U[i]) & np.isfinite(K[i]) & ~dis
            if p["vol_filtre"] == "yuksek" and ok.sum() >= 2:
                med = np.nanmedian(np.where(ok, V[i], np.nan))
                ok = ok & (V[i] >= med)
            idx = [c for c, o in zip(kolon, ok) if o]
            n = len(idx)
            if p["skor"] == "tutarli":
                if n < 3:
                    return {}
                a = pd.Series(U[i], index=kolon)[idx].rank(pct=True)
                b = pd.Series(K[i], index=kolon)[idx].rank(pct=True)
                q = max(n // 3, 1)
                uz = [c for c in en_iyi_k(a, q) if c in en_iyi_k(b, q)]
                ks = [c for c in en_iyi_k(a, q, False) if c in en_iyi_k(b, q, False)]
                if mod == "long":
                    ks = []
                w = {c: brut * (1.0 if mod == "long" else 0.5) / len(uz) for c in uz} if uz else {}
                if ks:
                    w.update({c: -brut * 0.5 / len(ks) for c in ks})
                return w
            if mod == "long":
                ke = min(p["k"], n)
                return bacak(idx, kolon, U[i], ke, 1.0, brut) if ke >= 1 else {}
            ke = min(p["k"], n // 2)
            if ke < 1:
                return {}
            uz_sk, ks_sk = (U[i], K[i]) if mod == "notr" else (K[i], U[i])
            w = bacak(idx, kolon, uz_sk, ke, 1.0, brut / 2)
            kalan = [c for c in idx if c not in w]
            w.update(bacak(kalan, kolon, ks_sk, ke, -1.0, brut / 2))
            return w

        V_i = None
        return dongusel_hedef(ax, kolon, tetik, agirlik)


class GoreceliGuc(PfTemel):
    """Göreceli güç (RS) seçimi: geri çekilmede alım ya da RS dönüşü + fiyat kırılımı.

    Kaynaklar: kart swing__goreceli-guc__ladha (göreceli güçle en güçlü seçilip geri çekilmede alınır),
    kart daytrade__goreceli-guc-donus-kirilim__bulkowski (hisse/endeks oranı dönüşü + kırılım filtresi).
    RS_i = kapanış_i / endeks (endeks = ref_sembol ya da "" ise evrenin eşit ağırlıklı günlük getiri bileşiği,
    nedensel). S&P 500 evrende yok -> evren ortalaması ya da BTC/XAU vekili.
    mod="geri_cekilme": RS getirisi (RS[t]/RS[t-rs_gun]-1) sıralamasında ilk k ise ve kapanış > SMA(trend_sma) ve kapanış
      <= EMA(pb_ema) (geri çekilme) -> long; sıralamada ilk cikis_rank'ten düşünce ya da kapanış < SMA(trend_sma) -> çık.
    mod="donus_kirilim": RS, SMA(rs_sma) üstüne son rs_pencere günde çıktıysa (dönüş) VE kapanış önceki kirilim_gun
      günün en yüksek kapanışını aştıysa (kırılım) -> long; RS < SMA(rs_sma) olunca çık. En çok k pozisyon.
    Uyarlama: kartlar tek-sembol/kural metni; günlük 1d, evrene taşındı; kart parametreleri belirsiz olduğundan
    standart değerler kullanıldı (tahmin: yazarın tam sayıları kartta yok).
    """

    ad = "pf__goreceli_guc"
    min_sembol = 2
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": HEPSI, "mod": "geri_cekilme", "ref_sembol": "", "rs_gun": 90, "k": 3,
        "cikis_rank": 5, "trend_sma": 50, "pb_ema": 10, "rs_sma": 50, "rs_pencere": 10, "kirilim_gun": 20}
    parametre_izgarasi = {"mod": ["geri_cekilme", "donus_kirilim"], "rs_gun": [30, 90, 180], "k": [1, 2, 3]}

    def ek_semboller(self):
        return (self.parametreler["ref_sembol"],)

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        ax = tk.eksen
        kap = tk.kap
        r = tk.getiri()
        if p["ref_sembol"]:
            endeks = kap[p["ref_sembol"]]
        else:
            endeks = (1.0 + r[kolon].mean(axis=1).fillna(0.0)).cumprod()
        rs = kap[kolon].div(endeks, axis=0)
        sm = sma_gun(kap[kolon], p["trend_sma"])
        D = lambda df: tk.eksene(df).to_numpy()
        KAP, SM = D(kap[kolon]), D(sm)
        if p["mod"] == "geri_cekilme":
            skor = D(rs / rs.shift(p["rs_gun"]) - 1.0)
            EM = D(ema_gun(kap[kolon], p["pb_ema"]))
        elif p["mod"] == "donus_kirilim":
            rsm = sma_gun(rs, p["rs_sma"])
            ust = (rs > rsm)
            donus = ust & ~ust.shift(1, fill_value=False).astype(bool)
            donus_son = donus.astype(float).rolling(p["rs_pencere"], min_periods=1).max() > 0
            zirve = kap[kolon].shift(1).rolling(p["kirilim_gun"], min_periods=p["kirilim_gun"]).max()
            RSU, RSM_OK = D(ust), D(rsm.notna())
            DON, KIR = D(donus_son), D(kap[kolon] > zirve)
            skor = D(rs / rs.shift(p["rs_gun"]) - 1.0)
        else:
            raise ValueError("mod geri_cekilme ya da donus_kirilim olmalı")
        n, m = KAP.shape
        k = int(p["k"])
        tut = np.zeros(m, dtype=bool)
        w = np.full((n, m), np.nan)
        onceki = np.zeros(m)
        for i in range(n):
            sc = skor[i]
            if not np.isfinite(sc).any():
                continue
            sirali = en_iyi_k(pd.Series(sc, index=kolon), m)
            if p["mod"] == "geri_cekilme":
                for j, c in enumerate(kolon):
                    if tut[j]:
                        sira = sirali.index(c) if c in sirali else 999
                        if sira >= p["cikis_rank"] or not (KAP[i, j] > SM[i, j]):
                            tut[j] = False
                for c in sirali[:k]:
                    j = kolon.index(c)
                    if (not tut[j] and tut.sum() < k and np.isfinite(SM[i, j]) and KAP[i, j] > SM[i, j]
                            and np.isfinite(EM[i, j]) and KAP[i, j] <= EM[i, j]):
                        tut[j] = True
            else:
                for j in range(m):
                    if tut[j] and RSM_OK[i, j] and not RSU[i, j]:
                        tut[j] = False
                for c in sirali:
                    j = kolon.index(c)
                    if (not tut[j] and tut.sum() < k and RSM_OK[i, j] and RSU[i, j] and DON[i, j] and KIR[i, j]):
                        tut[j] = True
            satir = tut.astype(float) / k
            if not np.array_equal(satir, onceki):
                w[i] = satir
                onceki = satir
        return pd.DataFrame(w, index=ax, columns=kolon)


class WqAlfa(PfTemel):
    """WorldQuant 101 Formulaic Alphas — seçili kesitsel alfalar, DÜZELTİLMİŞ kesitsel sıralama.

    Kaynak: yli188/WorldQuant_alpha101_code, Kakushadze "101 Formulaic Alphas". Kaynak koddaki hata: rank() zaman
    ekseni boyunca yüzdelik sıra alıyordu (look-ahead). Burada rank YALNIZ KESİTTE (aynı gün, semboller arası,
    axis=1) hesaplanır; zaman serisi fonksiyonları (delta, correlation) yalnız geçmişe bakar.
    alfa: 101 ((kapanış-açılış)/((yüksek-düşük)+0.001)), 12 (sign(delta(hacim,1)) * -delta(kapanış,1)),
          33 (rank(-(1-açılış/kapanış))), 6 (-correlation(açılış, hacim, 10)), 41 (sqrt(yüksek*düşük) - vwap).
    vwap = (yüksek+düşük+kapanış)/3 vekili (kaynak da OHLCV'den türetir). Pozisyon/çıkış kaynakta tanımsızdır:
    rank-nötr ağırlık w_i = (rank_i - ort rank) / sum|rank_i - ort rank| x brut, `takvim`de dengelenir
    (varsayılan günlük; kaynak: ortalama tutma 0.6-6.4 gün). Evren 3-13 enstrüman: istatistiksel güç düşük.
    """

    ad = "pf__wq_alfa"
    min_sembol = 3
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": HEPSI, "alfa": 101, "takvim": "D", "brut": 1.0}
    parametre_izgarasi = {"alfa": [101, 12, 33, 6, 41], "takvim": ["D", "3", "W"]}

    def _alfa(self, tk, kolon):
        a = self.parametreler["alfa"]
        o, h, l, c = (tk.panel(x, False)[kolon] for x in ("acilis", "yuksek", "dusuk", "kapanis"))
        v = tk.panel("hacim", False)[kolon]
        if a == 101:
            return (c - o) / ((h - l) + 0.001)
        if a == 12:
            return np.sign(v.diff()) * (-c.diff())
        if a == 33:
            return (-(1.0 - o / c)).rank(axis=1, pct=True)
        if a == 6:
            return -o.rolling(10, min_periods=10).corr(v)
        if a == 41:
            return np.sqrt(h * l) - (h + l + c) / 3.0
        raise ValueError(f"desteklenmeyen alfa: {a}")

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        al = self._alfa(tk, kolon)
        rk = al.rank(axis=1, pct=True)                     # KESİTSEL sıra (axis=1)
        sayi = al.notna().sum(axis=1)
        rk = rk.where(sayi >= 3)
        merk = rk.sub(rk.mean(axis=1), axis=0)
        w = merk.div(merk.abs().sum(axis=1), axis=0) * p["brut"]
        W = tk.eksene(w).to_numpy(dtype=float)
        gecerli = np.isfinite(W).any(axis=1)
        tetik = tetik_satirlari(tk.eksen, p["takvim"], gecerli)
        return dongusel_hedef(tk.eksen, kolon, tetik,
                              lambda i: {c: (0.0 if not np.isfinite(W[i, j]) else W[i, j]) for j, c in enumerate(kolon)})
